"""Lectura masiva (solo lectura) de la evidencia de tenis para la exportación PIT.

Se leen las tablas COMPLETAS con `recibo.retro` y las prioridades de la fuente, en una transacción READ ONLY con la zona
horaria de la sesión en UTC. La lógica de visibilidad NO se aplica aquí: la reimplementa `visibilidad.py` por conjunto
y se compara con las funciones `*_a_las` de la base (pruebas y `verificar_contra_puerta`).
Nunca se leen los campos prohibidos de SofaScore (ranking «de hoy», firstToServe, h2h, team_streaks): no existen en la
evidencia (se quedan en el original) y aquí solo se leen columnas nombradas.
"""
import io
import re
from contextlib import contextmanager

import pandas as pd
import psycopg
from psycopg import sql

ESQUEMA = re.compile(r"^[a-z_][a-z0-9_]*$")

CONSULTAS = {
    "jugador": "SELECT jugador_id, circuito FROM jugador",
    "torneo": "SELECT torneo_id, circuito, clave, nombre, categoria, fuente FROM torneo",
    "sede": "SELECT sede_id, huso_iana FROM sede",
    "edicion": """SELECT e.edicion_id, e.torneo_id, e.temporada, e.lunes_semana, e.fecha_fin, e.sede_id, e.superficie,
                         e.indoor, e.por_equipos, e.fuente, e.recibido_en, e.visible_desde, r.retro,
                         f.prioridad_calendario AS prio
                  FROM edicion e JOIN recibo r ON r.recibo_id = e.recibo_id JOIN fuente f ON f.fuente = e.fuente""",
    "partido": """SELECT p.partido_id, p.edicion_id, p.ronda, p.jugador_1, p.jugador_2, p.mejor_de, p.entrada_1,
                         p.entrada_2, p.fuente, p.recibido_en, p.visible_desde, r.retro
                  FROM partido p JOIN recibo r ON r.recibo_id = p.recibo_id""",
    "programa": """SELECT x.programa_id, x.partido_id, x.inicio_programado_utc, x.tipo_hora, x.fuente, x.recibido_en,
                          x.visible_desde, r.retro, f.prioridad_calendario AS prio
                   FROM programa x JOIN recibo r ON r.recibo_id = x.recibo_id JOIN fuente f ON f.fuente = x.fuente""",
    "resultado": """SELECT x.resultado_id, x.partido_id, x.estado, x.ganador, x.retira, x.sets::text AS sets,
                           x.sets_completos, x.duracion_min, x.fuente, x.recibido_en, x.visible_desde, r.retro,
                           f.prioridad_resultado AS prio
                    FROM resultado x JOIN recibo r ON r.recibo_id = x.recibo_id JOIN fuente f ON f.fuente = x.fuente""",
    "estadistica": """SELECT x.estadistica_id, x.partido_id, x.lado, x.aces, x.dobles_faltas, x.puntos_saque,
                             x.primeros_dentro, x.primeros_ganados, x.segundos_ganados, x.juegos_saque, x.bp_salvados,
                             x.bp_afrontados, x.fuente, x.recibido_en, x.visible_desde, r.retro,
                             f.prioridad_resultado AS prio
                      FROM estadistica x JOIN recibo r ON r.recibo_id = x.recibo_id JOIN fuente f ON f.fuente = x.fuente""",
    "ranking": """SELECT x.ranking_id, x.circuito, x.fecha_publicacion, x.jugador_id, x.posicion, x.puntos, x.origen,
                         x.fuente, x.recibido_en, x.visible_desde, r.retro, f.prioridad_resultado AS prio
                  FROM ranking x JOIN recibo r ON r.recibo_id = x.recibo_id JOIN fuente f ON f.fuente = x.fuente""",
    "nacimiento": """SELECT a.asercion_id, a.jugador_id, a.valor, a.fuente, a.recibido_en, r.retro,
                            f.prioridad_calendario AS prio
                     FROM jugador_asercion a JOIN recibo r ON r.recibo_id = a.recibo_id JOIN fuente f ON f.fuente = a.fuente
                     WHERE a.campo = 'fecha_nacimiento'""",
}
INSTANTES = ("recibido_en", "visible_desde", "inicio_programado_utc")
FECHAS = ("lunes_semana", "fecha_fin", "fecha_publicacion")
BOOLEANOS = ("retro", "indoor", "por_equipos")
ENTEROS_NULABLES = ("ganador", "retira", "sets_completos", "duracion_min", "aces", "dobles_faltas", "puntos_saque",
                    "primeros_dentro", "primeros_ganados", "segundos_ganados", "juegos_saque", "bp_salvados",
                    "bp_afrontados", "puntos", "sede_id")


@contextmanager
def conexion_lectura(dsn: str, esquema: str):
    """Conexión en una transacción READ ONLY, search_path al esquema y zona UTC. Nunca escribe."""
    if not ESQUEMA.match(esquema):
        raise ValueError("nombre de esquema no válido")
    with psycopg.connect(dsn, autocommit=False) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute(sql.SQL("SET LOCAL search_path TO {}, public").format(sql.Identifier(esquema)))
        conn.execute("SET LOCAL TIME ZONE 'UTC'")
        try:
            yield conn
        finally:
            conn.rollback()


def _copiar(conn, consulta: str) -> pd.DataFrame:
    buf = io.BytesIO()
    with conn.cursor().copy(f"COPY ({consulta}) TO STDOUT WITH (FORMAT csv, HEADER true)") as cp:
        for bloque in cp:
            buf.write(bloque)
    buf.seek(0)
    df = pd.read_csv(buf, dtype=str, keep_default_na=False, na_values=[""])
    for c in df.columns:
        if c in INSTANTES:
            df[c] = pd.to_datetime(df[c], utc=True, format="ISO8601")
        elif c in FECHAS:
            df[c] = pd.to_datetime(df[c], format="%Y-%m-%d")
        elif c in BOOLEANOS:
            df[c] = df[c].map({"t": True, "f": False}).astype("boolean")
        elif c.endswith("_id") or c in ("temporada", "mejor_de", "lado", "posicion", "prio") or c in ENTEROS_NULABLES:
            df[c] = pd.to_numeric(df[c]).astype("Int64")
    return df


def leer_todo(conn) -> dict[str, pd.DataFrame]:
    """Todas las tablas que necesita la exportación (dict nombre → DataFrame)."""
    return {nombre: _copiar(conn, q) for nombre, q in CONSULTAS.items()}


def max_recibido(conn) -> str | None:
    """Fecha de corte de los datos: el `recibido_en` más reciente de la evidencia de partidos."""
    fila = conn.execute("SELECT max(recibido_en) FROM recibo").fetchone()
    return fila[0].isoformat() if fila and fila[0] else None
