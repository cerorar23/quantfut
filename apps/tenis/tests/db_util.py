"""Ayudas de las pruebas de base de tenis: cada prueba crea un esquema aislado y lo borra al terminar."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

RAIZ_DB = Path(__file__).resolve().parents[1] / "db"
MIGRACIONES = [
    "0001_catalogos.sql",
    "0002_evidencia.sql",
    "0003_inmutabilidad.sql",
    "0004_lectura_pit.sql",
    "0006_sellado.sql",
    "0007_semillas.sql",
]
MIGRACION_ROLES = "0005_roles.sql"

# Sustitución de nombres de esquema: `tenis.`, `tenis_op.`, `SCHEMA tenis`... No toca `tenis-motor:` ni `tenis_captura`.
_PATRON_ESQUEMA = re.compile(r"\btenis(_op)?(?=[.;,\s)]|$)")


def sql_de(nombre: str, esquema: str, esquema_op: str) -> str:
    """Texto de una migración con el esquema de la prueba en lugar de `tenis`."""
    texto = (RAIZ_DB / nombre).read_text(encoding="utf-8")
    return _PATRON_ESQUEMA.sub(lambda m: esquema_op if m.group(1) else esquema, texto)


def ts(texto: str) -> datetime:
    """Instante con zona a partir de 'AAAA-MM-DD' o 'AAAA-MM-DDTHH:MM:SSZ' (UTC si no lleva zona)."""
    if "T" not in texto:
        texto += "T00:00:00"
    if texto.endswith("Z"):
        texto = texto[:-1] + "+00:00"
    dt = datetime.fromisoformat(texto)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def nuevo_recibo(db, fuente="sofascore", recibido="2026-01-05", retro=False) -> int:
    sha = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    return db.execute(
        "INSERT INTO recibo (fuente, recurso, recibido_en, estado_http, sha256, ruta_objeto, bytes, lote, retro) "
        "VALUES (%s, 'prueba', %s, 200, %s, %s, 10, 'prueba', %s) RETURNING recibo_id",
        (fuente, ts(recibido), sha, f"objetos/{sha[:2]}/{sha}.json.gz", retro),
    ).fetchone()[0]


def insertar(db, sentencia: str, parametros=()) -> int:
    """Inserta y devuelve la primera columna de la fila (el id sustituto)."""
    return db.execute(sentencia, parametros).fetchone()[0]


def cargar_minimo(db) -> dict:
    """Un mundo mínimo válido: torneo, edición, cuatro jugadores, un partido con todas sus tablas de evidencia.

    Todas las filas son no retro y de 2026-01-05, salvo lo que cada prueba añada. La edición termina
    el lunes 2026-03-02. El partido futuro se programa para 2099 (sellable)."""
    r = nuevo_recibo(db, "sofascore", "2026-01-05")
    rm = nuevo_recibo(db, "propline", "2026-01-05")
    d = {"recibo": r}
    d["torneo"] = insertar(db, "INSERT INTO torneo (circuito, clave, nombre, categoria, fuente, recibo_id, recibido_en) "
                               "VALUES ('atp', 'roland-garros', 'Roland Garros', 'GS', 'sofascore', %s, %s) RETURNING torneo_id",
                           (r, ts("2026-01-05")))
    d["sede"] = insertar(db, "INSERT INTO sede (clave, ciudad, pais, huso_iana, lat, lon, altitud_m, fuente, recibo_id, recibido_en) "
                             "VALUES ('paris-rg', 'Paris', 'FRA', 'Europe/Paris', 48.846900, 2.252600, 35.0, 'sofascore', %s, %s) "
                             "RETURNING sede_id", (r, ts("2026-01-05")))
    d["edicion"] = insertar(db, "INSERT INTO edicion (torneo_id, temporada, lunes_semana, superficie, indoor, sede_id, "
                                "fuente, recibo_id, recibido_en) VALUES (%s, 2026, '2026-03-02', 'clay', false, %s, "
                                "'sofascore', %s, %s) RETURNING edicion_id",
                            (d["torneo"], d["sede"], r, ts("2026-01-05")))
    jugadores = []
    for _ in range(4):
        jugadores.append(insertar(db, "INSERT INTO jugador (circuito, recibo_id, recibido_en) VALUES ('atp', %s, %s) "
                                      "RETURNING jugador_id", (r, ts("2026-01-05"))))
    d["jugadores"] = sorted(jugadores)
    a, b, _, _ = d["jugadores"]
    db.execute("INSERT INTO jugador_asercion (jugador_id, campo, valor, fuente, recibo_id, recibido_en) "
               "VALUES (%s, 'mano', 'D', 'sofascore', %s, %s)", (a, r, ts("2026-01-05")))
    db.execute("INSERT INTO jugador_alias (fuente, id_fuente, jugador_id, metodo, recibo_id, recibido_en) "
               "VALUES ('sofascore', 'sf-1', %s, 'id_exacto', %s, %s)", (a, r, ts("2026-01-05")))
    d["partido"] = insertar(db, "INSERT INTO partido (edicion_id, ronda, jugador_1, jugador_2, mejor_de, fuente, "
                                "recibo_id, recibido_en) VALUES (%s, 'R32', %s, %s, 3, 'sofascore', %s, %s) "
                                "RETURNING partido_id", (d["edicion"], a, b, r, ts("2026-01-05")))
    db.execute("INSERT INTO programa (partido_id, inicio_programado_utc, tipo_hora, pista, estado, fuente, recibo_id, "
               "recibido_en) VALUES (%s, '2099-01-01T12:00:00Z', 'fija', 'Court 1', 'programado', 'sofascore', %s, %s)",
               (d["partido"], r, ts("2026-01-05")))
    db.execute("INSERT INTO resultado (partido_id, estado, ganador, sets, sets_completos, duracion_min, fuente, "
               "recibo_id, recibido_en) VALUES (%s, 'completado', 1, %s, 2, 90, 'sofascore', %s, %s)",
               (d["partido"], Jsonb([[6, 3, None, None], [6, 4, None, None]]), r, ts("2026-01-05")))
    db.execute("INSERT INTO estadistica (partido_id, lado, aces, puntos_saque, primeros_dentro, primeros_ganados, "
               "segundos_ganados, fuente, recibo_id, recibido_en) VALUES (%s, 1, 7, 60, 40, 30, 12, 'sofascore', %s, %s)",
               (d["partido"], r, ts("2026-01-05")))
    db.execute("INSERT INTO estadistica (partido_id, lado, aces, puntos_saque, primeros_dentro, primeros_ganados, "
               "segundos_ganados, fuente, recibo_id, recibido_en) VALUES (%s, 2, 2, 58, 35, 20, 10, 'sofascore', %s, %s)",
               (d["partido"], r, ts("2026-01-05")))
    db.execute("INSERT INTO juego_pbp (partido_id, set_n, juego_n, sacador, puntos, es_tiebreak, fuente, recibo_id, "
               "recibido_en) VALUES (%s, 1, 1, 1, 'SSRS', false, 'sofascore', %s, %s)", (d["partido"], r, ts("2026-01-05")))
    d["ranking"] = insertar(db, "INSERT INTO ranking (circuito, fecha_publicacion, jugador_id, posicion, puntos, origen, "
                                "fuente, recibo_id, recibido_en) VALUES ('atp', '2026-03-02', %s, 5, 4000, "
                                "'oficial_capturado', 'sofascore', %s, %s) RETURNING ranking_id",
                            (a, r, ts("2026-01-05")))
    db.execute("INSERT INTO precio_mercado (recibo_id, evento_fuente, partido_id, casa, mercado, periodo, linea, lado, "
               "cuota_decimal, clase_cierre, fuente, recibido_en) VALUES (%s, 'ev-1', %s, 'pinnacle', 'ganador', "
               "'completo', NULL, '1', 1.850, 'a', 'propline', %s)", (rm, d["partido"], ts("2026-01-05")))
    db.execute("INSERT INTO enlace_evento (fuente, evento_fuente, partido_id, metodo, recibo_id, recibido_en) "
               "VALUES ('propline', 'ev-1', %s, 'id_exacto', %s, %s)", (d["partido"], rm, ts("2026-01-05")))
    db.execute("INSERT INTO sin_resolver (fuente, id_fuente, nombre_fuente, motivo, contexto, recibo_id, recibido_en) "
               "VALUES ('sofascore', 'x-9', 'Nombre Raro', 'sin_candidato', '{}', %s, %s)", (r, ts("2026-01-05")))
    sha = hashlib.sha256(b"artefacto de prueba").hexdigest()
    db.execute("INSERT INTO artefacto (sha256, tipo, version_modelo) VALUES (%s, 'modelo', 'v1')", (sha,))
    db.execute("INSERT INTO artefacto_activo (sha256, aprobado_en_chat, imagen) VALUES (%s, 'chat 2026-11-05', "
               "'tenis-motor:v1')", (sha,))
    d["pronostico"] = sellar(db, d["partido"], "v1", ts("2026-01-05"))
    return d


def sellar(db, partido, version_modelo, corte, datos="d1", entradas=None, distribucion=None, referencia=None) -> str:
    """Llama a la función de sellado y devuelve el hash."""
    return db.execute(
        "SELECT sellar_pronostico(%s, %s, %s, %s, %s, %s, %s)",
        (partido, version_modelo, datos, corte,
         Jsonb(entradas if entradas is not None else {"ratings": {"a": 0.25}}),
         Jsonb(distribucion if distribucion is not None else {"p_1": 0.6, "p_2": 0.4}),
         Jsonb(referencia if referencia is not None else {})),
    ).fetchone()[0]


def _canon(valor) -> str:
    """Serialización canónica documentada en 0006 (json_canonico), reproducida en Python."""
    if isinstance(valor, dict):
        partes = [json.dumps(k, ensure_ascii=False) + ":" + _canon(valor[k])
                  for k in sorted(valor, key=lambda s: s.encode("utf-8"))]
        return "{" + ",".join(partes) + "}"
    if isinstance(valor, list):
        return "[" + ",".join(_canon(x) for x in valor) + "]"
    if valor is None:
        return "null"
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, str):
        return json.dumps(valor, ensure_ascii=False)
    if isinstance(valor, (int, float)):
        return repr(valor)
    raise TypeError(type(valor))


def _instante(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def hash_esperado(fila: dict, previo: str) -> str:
    """Recalcula el hash de un sello a partir de sus columnas (independiente de la función SQL)."""
    cuerpo = [fila["partido_id"], fila["version_modelo"], fila["version_datos"], _instante(fila["corte"]),
              _instante(fila["sellado_en"]), fila["entradas"], fila["distribucion"],
              fila["referencia_mercado"], previo]
    return hashlib.sha256(_canon(cuerpo).encode("utf-8")).hexdigest()


# Tablas de evidencia que la inmutabilidad debe cubrir (además se recorre el catálogo, ver tests).
TABLAS_EVIDENCIA_ESPERADAS = {
    "fuente", "recibo", "jugador", "jugador_asercion", "jugador_alias", "torneo", "sede", "edicion",
    "partido", "programa", "resultado", "estadistica", "juego_pbp", "ranking", "precio_mercado",
    "enlace_evento", "sin_resolver", "artefacto", "artefacto_activo", "pronostico",
}
