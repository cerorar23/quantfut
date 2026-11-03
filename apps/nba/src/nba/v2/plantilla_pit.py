"""Plantilla de un partido en un corte (punto en el tiempo): quién puede jugar, su último parte oficial y sus últimos partidos.

Misma regla de visibilidad que `pit.instantanea`: solo partidos de fecha ANTERIOR a la del pronosticado; las filas `reconstruido` se
aceptan por fecha del partido y las `posterior` exigen `recibido_en <= corte`. El parte oficial (`estado_disponibilidad`, fuente
`nba_oficial`) es el último con `recibido_en <= corte`. Candidatos de un equipo: quienes jugaron en sus últimos 10 partidos y cuyo último
partido jugado fue con ese equipo, más los nombrados en el parte cuyo último equipo es este; se exigen al menos 5 partidos jugados.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta, UTC
import hashlib
import json

from .pit import Instantanea

VENTANA_EQUIPO = 10
V = 30                                    # partidos de historia por jugador
MIN_PARTIDOS = 5
MINUTOS_MAXIMOS = 60.0                  # un partido con más de 60 minutos de un jugador es un dato corrupto
DIAS_ATRAS = 2200                       # el modelo validado usa los últimos 30 partidos sin límite de edad (todo el archivo desde 2021)
METRICAS = ("minutos", "puntos", "rebotes", "asistencias", "triples_anotados")

Q_PLANTEL = """
SELECT DISTINCT d.entidad_id FROM nba.dato d JOIN nba.metrica m ON m.metrica_id = d.metrica_id AND m.nombre = 'minutos'
JOIN nba.dato t ON t.partido_id = d.partido_id AND t.entidad_id = d.entidad_id AND t.valor = %(equipo)s
JOIN nba.metrica mt ON mt.metrica_id = t.metrica_id AND mt.nombre = 'equipo_del_jugador'
WHERE d.partido_id = ANY(%(pids)s) AND d.fase = 'final' AND d.valor > 0
  AND (d.pit = 'reconstruido' OR d.recibido_en <= %(corte)s) AND (t.pit = 'reconstruido' OR t.recibido_en <= %(corte)s)
"""

Q_PARTE = """
SELECT DISTINCT ON (d.entidad_id) d.entidad_id, d.etiqueta
FROM nba.dato d JOIN nba.metrica m ON m.metrica_id = d.metrica_id AND m.nombre = 'estado_disponibilidad'
WHERE d.partido_id = %(partido)s AND d.fuente = 'nba_oficial' AND d.recibido_en <= %(corte)s
ORDER BY d.entidad_id, d.recibido_en DESC, d.dato_id DESC
"""

Q_ULTIMO_EQUIPO = """
SELECT DISTINCT ON (t.entidad_id) t.entidad_id, t.valor::bigint
FROM nba.dato t JOIN nba.metrica mt ON mt.metrica_id = t.metrica_id AND mt.nombre = 'equipo_del_jugador'
JOIN nba.entidad e ON e.entidad_id = t.partido_id
WHERE t.entidad_id = ANY(%(jug)s) AND e.fecha_juego_et < %(fecha)s AND (t.pit = 'reconstruido' OR t.recibido_en <= %(corte)s)
  AND EXISTS (SELECT 1 FROM nba.dato dm JOIN nba.metrica mm ON mm.metrica_id = dm.metrica_id AND mm.nombre = 'minutos'
              WHERE dm.partido_id = t.partido_id AND dm.entidad_id = t.entidad_id AND dm.valor > 0 AND dm.fase = 'final')
ORDER BY t.entidad_id, e.fecha_juego_et DESC, t.dato_id DESC
"""

Q_HISTORIA = """
SELECT d.entidad_id, e.fecha_juego_et, d.partido_id, m.nombre, d.valor, f.prioridad, d.recibido_en, d.dato_id
FROM nba.dato d JOIN nba.metrica m ON m.metrica_id = d.metrica_id JOIN nba.entidad e ON e.entidad_id = d.partido_id
JOIN nba.fuente f ON f.fuente = d.fuente
WHERE d.entidad_id = ANY(%(jug)s) AND m.nombre = ANY(%(metricas)s) AND d.fase = 'final' AND d.periodo = 0
  AND e.fecha_juego_et < %(fecha)s AND e.fecha_juego_et >= %(desde)s AND (d.pit = 'reconstruido' OR d.recibido_en <= %(corte)s)
"""


@dataclass(frozen=True)
class JugadorPlantilla:
    id: int
    nombre: str
    estado: str | None
    minutos: tuple                         # de más antiguo a más reciente
    stats: tuple                           # una tupla (puntos, rebotes, asistencias, triples) por partido


@dataclass(frozen=True)
class Plantilla:
    partido_id: int
    corte: object
    lados: dict                            # {"local": (JugadorPlantilla, ...), "visitante": (...)}
    version_datos: str


def plantilla(db, inst: Instantanea) -> Plantilla:
    corte, fecha = inst.corte, inst.fecha
    equipos = db.execute("SELECT (atributos->>'local')::bigint, (atributos->>'visitante')::bigint FROM nba.entidad WHERE entidad_id = %s",
                         (inst.partido_id,)).fetchone()
    por_lado = {"local": (equipos[0], inst.local), "visitante": (equipos[1], inst.visitante)}
    parte = dict(db.execute(Q_PARTE, {"partido": inst.partido_id, "corte": corte}).fetchall())
    plantel = {}
    for lado, (eq_id, tri) in por_lado.items():
        pids = [h[1] for h in inst.historia if tri in (h[2], h[3])][-VENTANA_EQUIPO:]
        ids = {r[0] for r in db.execute(Q_PLANTEL, {"equipo": eq_id, "pids": pids, "corte": corte}).fetchall()} if pids else set()
        plantel[lado] = ids
    candidatos = set().union(*plantel.values()) | set(parte)
    if not candidatos:
        return Plantilla(inst.partido_id, corte, {"local": (), "visitante": ()}, hashlib.sha256(b"[]").hexdigest())
    ultimo = dict(db.execute(Q_ULTIMO_EQUIPO, {"jug": sorted(candidatos), "fecha": fecha, "corte": corte}).fetchall())
    crudo = defaultdict(dict)                    # (jugador, partido) -> {métrica: (prioridad, -recibido, -dato_id, valor)}
    fechas = {}
    for jug, f, pid, nombre, valor, prio, rec, dato_id in db.execute(
            Q_HISTORIA, {"jug": sorted(candidatos), "metricas": list(METRICAS), "fecha": fecha, "desde": fecha - timedelta(days=DIAS_ATRAS),
                         "corte": corte}).fetchall():
        clave = (prio, -rec.timestamp(), -dato_id)
        actual = crudo[(jug, pid)].get(nombre)
        if actual is None or clave < actual[0]:
            crudo[(jug, pid)][nombre] = (clave, valor)
        fechas[(jug, pid)] = f
    partidos_de = defaultdict(list)
    for (jug, pid), mets in crudo.items():
        if "minutos" in mets and mets["minutos"][1] is not None and 0 < mets["minutos"][1] <= MINUTOS_MAXIMOS:     # minutos corruptos: el partido no cuenta
            partidos_de[jug].append((fechas[(jug, pid)], pid, mets))
    nombres = dict(db.execute("SELECT entidad_id, nombre FROM nba.entidad WHERE entidad_id = ANY(%s)", (sorted(candidatos),)).fetchall())
    lados = {}
    for lado, (eq_id, tri) in por_lado.items():
        jugadores = []
        for jug in sorted(candidatos):
            if ultimo.get(jug) != eq_id or len(partidos_de[jug]) < MIN_PARTIDOS:
                continue
            if jug not in plantel[lado] and jug not in parte:
                continue
            juegos = sorted(partidos_de[jug], key=lambda x: (x[0], x[1]))[-V:]
            stats = tuple(tuple(float(m[n][1]) if n in m and m[n][1] is not None else float("nan")      # estadística ausente = desconocida, nunca 0
                                for n in ("puntos", "rebotes", "asistencias", "triples_anotados"))
                          for _, _, m in juegos)
            jugadores.append(JugadorPlantilla(jug, nombres.get(jug) or str(jug), parte.get(jug), tuple(float(m["minutos"][1]) for _, _, m in juegos), stats))
        lados[lado] = tuple(jugadores)
    huella = hashlib.sha256(json.dumps([[l, j.id, j.estado, j.minutos, j.stats] for l, js in sorted(lados.items()) for j in js],
                                       separators=(",", ":")).encode()).hexdigest()
    return Plantilla(inst.partido_id, corte, lados, huella)
