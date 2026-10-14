"""Pasa a `matches` lo ya archivado de FotMob (F0 de la spec 2026-10-14).

Solo rellena columnas en NULL, nunca inventa un valor ausente y nunca sobrescribe.
La procedencia de cada campo queda en `matches_enriquecimiento`.
"""
from __future__ import annotations

import gzip
import json
import math
from collections import Counter

# columna_local, columna_visita, clave en `statistics`, ¿entero?
CAMPOS_PARES = {
    "amarillas": ("home_yellow", "away_yellow", "yellow_cards", True),
    "rojas": ("home_red", "away_red", "red_cards", True),
    "corners": ("home_corners", "away_corners", "corners", True),
    "tiros": ("home_shots", "away_shots", "total_shots", True),
    "tiros_puerta": ("home_shots_target", "away_shots_target", "ShotsOnTarget", True),
    "xgot": ("home_xgot", "away_xgot", "expected_goals_on_target", False),
}


def _numero(valor) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if not math.isfinite(valor) or valor < 0:
        return None
    return float(valor)


def _par(statistics: dict, clave: str, entero: bool):
    """(local, visita) válidos los dos, o (None, None): nunca una mitad."""
    valor = (statistics or {}).get(clave)
    if not isinstance(valor, (list, tuple)) or len(valor) != 2:
        return None, None
    a, b = _numero(valor[0]), _numero(valor[1])
    if a is None or b is None:
        return None, None
    if entero:
        if a != int(a) or b != int(b):
            return None, None
        return int(a), int(b)
    return a, b


def _descanso(payload: dict, goles_local: int, goles_visita: int):
    hechos = ((payload.get("content") or {}).get("matchFacts") or {})
    eventos = hechos.get("events")
    eventos = eventos.get("events") if isinstance(eventos, dict) else None
    for e in eventos or []:
        if e.get("type") == "Half" and e.get("halfStrShort") == "HT":
            h, a = e.get("homeScore"), e.get("awayScore")
            validos = all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (h, a))
            if validos and h <= goles_local and a <= goles_visita:
                return h, a
    return None, None


def _info(payload: dict) -> dict:
    return (((payload.get("content") or {}).get("matchFacts") or {}).get("infoBox")) or {}


def _texto(valor) -> str | None:
    if isinstance(valor, str) and valor.strip() and len(valor.strip()) <= 160:
        return valor.strip()
    return None


def _estadio(payload: dict) -> dict | None:
    bruto = _info(payload).get("Stadium")
    nombre = _texto((bruto or {}).get("name")) if isinstance(bruto, dict) else None
    if not nombre:
        return None
    lat, lon = bruto.get("lat"), bruto.get("long")
    en_rango = (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
                and not isinstance(lat, bool) and not isinstance(lon, bool)
                and -90 <= lat <= 90 and -180 <= lon <= 180)
    capacidad = bruto.get("capacity")
    return {"name": nombre, "city": _texto(bruto.get("city")), "country": _texto(bruto.get("country")),
            "lat": float(lat) if en_rango else None, "lon": float(lon) if en_rango else None,
            "capacity": int(capacidad) if isinstance(capacidad, int) and not isinstance(capacidad, bool)
            and capacidad > 0 else None,
            "surface": _texto(bruto.get("surface"))}


def extraer(payload: dict, statistics: dict, goles_local: int, goles_visita: int) -> dict:
    """Campos validados de un original FotMob. Dato ausente o inválido: None."""
    out: dict = {}
    for local, visita, clave, entero in CAMPOS_PARES.values():
        out[local], out[visita] = _par(statistics, clave, entero)
    out["home_goals_ht"], out["away_goals_ht"] = _descanso(payload, goles_local, goles_visita)
    arbitro = _info(payload).get("Referee")
    out["referee_fotmob"] = _texto(arbitro.get("text")) if isinstance(arbitro, dict) else None
    out["estadio"] = _estadio(payload)
    return out


PROVIDER = "fotmob"
COLUMNAS_MATCHES = [c for par in CAMPOS_PARES.values() for c in par[:2]] + [
    "home_goals_ht", "away_goals_ht", "referee_fotmob"]
LOTE = 200


def huecos(c, desde: str) -> dict:
    """Partidos terminados desde `desde` con el dato incompleto."""
    return dict(c.execute("""
        SELECT count(*) FILTER (WHERE home_yellow IS NULL OR away_yellow IS NULL) AS amarillas,
               count(*) FILTER (WHERE home_red IS NULL OR away_red IS NULL) AS rojas,
               count(*) FILTER (WHERE referee IS NULL AND referee_fotmob IS NULL) AS arbitro,
               count(*) FILTER (WHERE home_goals_ht IS NULL OR away_goals_ht IS NULL) AS descanso,
               count(*) FILTER (WHERE home_shots IS NULL OR away_shots IS NULL) AS tiros,
               count(*) FILTER (WHERE home_shots_target IS NULL OR away_shots_target IS NULL) AS tiros_puerta,
               count(*) FILTER (WHERE home_corners IS NULL OR away_corners IS NULL) AS corners,
               count(*) FILTER (WHERE home_xgot IS NULL OR away_xgot IS NULL) AS xgot,
               count(*) FILTER (WHERE stadium_id IS NULL) AS sede
        FROM matches WHERE status = 'finished' AND kickoff_utc >= %s""", (desde,)).fetchone())


def _estadio_id(c, estadio: dict, captured_at) -> tuple[int, bool]:
    fila = c.execute("""INSERT INTO estadios (name, city, country, lat, lon, capacity, surface, source, first_seen_at)
                        VALUES (%(name)s, %(city)s, %(country)s, %(lat)s, %(lon)s, %(capacity)s, %(surface)s,
                                %(source)s, %(visto)s)
                        ON CONFLICT (name, city, country) DO NOTHING RETURNING stadium_id""",
                     {**estadio, "source": PROVIDER, "visto": captured_at}).fetchone()
    if fila:
        return fila["stadium_id"], True
    return c.execute("""SELECT stadium_id FROM estadios WHERE name = %s
                        AND city IS NOT DISTINCT FROM %s AND country IS NOT DISTINCT FROM %s""",
                     (estadio["name"], estadio["city"], estadio["country"])).fetchone()["stadium_id"], False


def aplicar(c, desde: str = "2024-01-01", rollback: bool = False) -> dict:
    """Rellena solo NULL desde el archivo. `rollback=True` es el ensayo: mide y revierte."""
    from psycopg import Rollback

    informe = {"visitados": 0, "rellenados": Counter(), "estadios_nuevos": 0, "omitidos": Counter()}
    with c.transaction():
        informe["antes"] = huecos(c, desde)
        faltan = " OR ".join(f"m.{k} IS NULL" for k in COLUMNAS_MATCHES)
        pendientes = c.execute(f"""
            SELECT h.source_match_id FROM historical_football_matches h JOIN matches m USING (match_id)
            WHERE h.provider = %s AND h.mapping_status IN ('matched','created') AND m.status = 'finished'
              AND m.kickoff_utc >= %s AND (m.stadium_id IS NULL OR {faltan})
            ORDER BY m.kickoff_utc""", (PROVIDER, desde)).fetchall()
        ids = [r["source_match_id"] for r in pendientes]
        columnas = ", ".join("m." + k for k in COLUMNAS_MATCHES)
        for i in range(0, len(ids), LOTE):
            filas = c.execute(f"""
                SELECT h.source_match_id, h.captured_at, h.raw_payload_gzip, h.statistics,
                       h.home_goals AS h_hg, h.away_goals AS h_ag, m.match_id, m.home_goals, m.away_goals,
                       m.stadium_id, {columnas}
                FROM historical_football_matches h JOIN matches m USING (match_id)
                WHERE h.provider = %s AND h.source_match_id = ANY(%s)""", (PROVIDER, ids[i:i + LOTE])).fetchall()
            for f in filas:
                informe["visitados"] += 1
                if (f["h_hg"], f["h_ag"]) != (f["home_goals"], f["away_goals"]):
                    informe["omitidos"]["marcador_distinto"] += 1
                    continue
                try:
                    payload = json.loads(gzip.decompress(bytes(f["raw_payload_gzip"])))
                except (OSError, ValueError):
                    informe["omitidos"]["original_ilegible"] += 1
                    continue
                datos = extraer(payload, f["statistics"], f["home_goals"], f["away_goals"])
                nuevos = {k: datos[k] for k in COLUMNAS_MATCHES if f[k] is None and datos[k] is not None}
                if f["stadium_id"] is None and datos["estadio"]:
                    sid, creado = _estadio_id(c, datos["estadio"], f["captured_at"])
                    nuevos["stadium_id"] = sid
                    informe["estadios_nuevos"] += creado
                if not nuevos:
                    continue
                sets = ", ".join(f"{k} = COALESCE({k}, %({k})s)" for k in nuevos)
                c.execute(f"UPDATE matches SET {sets} WHERE match_id = %(match_id)s",
                          {**nuevos, "match_id": f["match_id"]})
                for campo in nuevos:
                    informe["rellenados"][campo] += 1
                    c.execute("""INSERT INTO matches_enriquecimiento
                                 (match_id, campo, provider, source_match_id, captured_at)
                                 VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                              (f["match_id"], campo, PROVIDER, f["source_match_id"], f["captured_at"]))
        informe["despues"] = huecos(c, desde)
        if rollback:
            raise Rollback()
    informe["rellenados"] = dict(informe["rellenados"])
    informe["omitidos"] = dict(informe["omitidos"])
    return informe
