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


def _eventos(payload: dict) -> list:
    hechos = ((payload.get("content") or {}).get("matchFacts") or {})
    eventos = hechos.get("events")
    eventos = eventos.get("events") if isinstance(eventos, dict) else None
    return eventos if isinstance(eventos, list) else []


def _es_descanso(e: dict) -> bool:
    return e.get("type") == "Half" and e.get("halfStrShort") == "HT"


def _tarjetas_cronologia(payload: dict):
    """((amarillas), (rojas)) de jugadores según la cronología, o None si no es fiable.

    Sin las del cuerpo técnico (cardDescription «coach»); la doble amarilla cuenta como roja, igual
    que el bloque de estadísticas. Sin descanso en la cronología o con un tipo desconocido, None.
    """
    eventos = _eventos(payload)
    if not any(_es_descanso(e) for e in eventos):
        return None
    amarillas, rojas = [0, 0], [0, 0]
    for e in eventos:
        if e.get("type") != "Card" or (e.get("cardDescription") or {}).get("localizedKey") == "coach":
            continue
        if not isinstance(e.get("isHome"), bool):
            return None
        lado = 0 if e["isHome"] else 1
        if e.get("card") == "Yellow":
            amarillas[lado] += 1
        elif e.get("card") in ("Red", "YellowRed"):
            rojas[lado] += 1
        else:
            return None
    return tuple(amarillas), tuple(rojas)


def _descanso(payload: dict, goles_local: int, goles_visita: int):
    for e in _eventos(payload):
        if _es_descanso(e):
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
    # En Argentina, Brasil y parte de México (2026) FotMob deja las amarillas del bloque a [0, 0] (a veces con
    # la roja bien) aunque la cronología trae cada tarjeta (medido el 25-oct-2026): con las amarillas a cero
    # manda la cronología, también para las rojas, para que el total salga de una sola cuenta.
    if out["home_yellow"] == 0 and out["away_yellow"] == 0:
        (out["home_yellow"], out["away_yellow"]), (out["home_red"], out["away_red"]) = (
            _tarjetas_cronologia(payload) or ((None, None), (None, None)))
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


TARJETAS = ("home_yellow", "away_yellow", "home_red", "away_red")


def reparar_tarjetas(c, rollback: bool = False) -> dict:
    """Corrige las tarjetas que el bloque a cero de FotMob dejó en `matches` antes del arreglo de `extraer`.

    Solo partidos cuyas tarjetas rellenó FotMob y que siguen con las amarillas a cero. Lee el mismo original que se
    usó (misma página y hora de captura, del archivo histórico o de `fotmob_original`) y aplica la cronología a las
    cuatro; si no es fiable, vuelven a NULL (un cero que no consta no se conserva). `rollback=True` es el ensayo.
    """
    from psycopg import Rollback

    informe = {"candidatos": 0, "corregidos": 0, "a_null": 0, "sin_cambio": 0, "sin_original": 0, "cambios": []}
    ceros = "m.home_yellow = 0 AND m.away_yellow = 0"
    with c.transaction():
        filas = c.execute(f"""
            SELECT m.match_id, m.home_red, m.away_red,
                   COALESCE((SELECT h.raw_payload_gzip FROM historical_football_matches h
                             WHERE h.provider = %(p)s AND h.match_id = m.match_id
                               AND h.source_match_id = e.source_match_id AND h.captured_at = e.captured_at LIMIT 1),
                            (SELECT o.payload_gz FROM fotmob_original o
                             WHERE o.match_id = m.match_id AND o.fotmob_match_id = e.source_match_id
                               AND o.capturado_en = e.captured_at ORDER BY o.id DESC LIMIT 1)) AS gz
            FROM matches m JOIN matches_enriquecimiento e
              ON e.match_id = m.match_id AND e.campo = 'home_yellow' AND e.provider = %(p)s
            WHERE {ceros} ORDER BY m.kickoff_utc""", {"p": PROVIDER}).fetchall()
        for f in filas:
            informe["candidatos"] += 1
            if f["gz"] is None:
                informe["sin_original"] += 1
                continue
            try:
                payload = json.loads(gzip.decompress(bytes(f["gz"])))
            except (OSError, ValueError):
                informe["sin_original"] += 1
                continue
            cronologia = _tarjetas_cronologia(payload)
            if cronologia == ((0, 0), (f["home_red"], f["away_red"])):
                informe["sin_cambio"] += 1
                continue
            valores = (*cronologia[0], *cronologia[1]) if cronologia else (None,) * 4
            sets = ", ".join(f"{k} = %s" for k in TARJETAS)
            c.execute(f"""UPDATE matches m SET {sets} WHERE m.match_id = %s AND {ceros}
                           AND m.home_red IS NOT DISTINCT FROM %s AND m.away_red IS NOT DISTINCT FROM %s""",
                      (*valores, f["match_id"], f["home_red"], f["away_red"]))
            informe["corregidos" if cronologia else "a_null"] += 1
            informe["cambios"].append({"match_id": f["match_id"], **dict(zip(TARJETAS, valores))})
        if rollback:
            raise Rollback()
    return informe


def huecos_xg(c, desde: str) -> list[dict]:
    """Partidos terminados sin la pareja de xG, por competición. Solo lectura."""
    return c.execute("""
        SELECT league_id, count(*) AS terminados,
               count(*) FILTER (WHERE home_xg IS NULL OR away_xg IS NULL) AS sin_xg
        FROM matches WHERE status = 'finished' AND kickoff_utc >= %s
        GROUP BY league_id HAVING count(*) FILTER (WHERE home_xg IS NULL OR away_xg IS NULL) > 0
        ORDER BY sin_xg DESC""", (desde,)).fetchall()


def main(argv=None):
    import argparse

    from ..db import conn
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--desde", default="2024-01-01")
    p.add_argument("--aplicar", action="store_true", help="sin esto es un ensayo que se revierte")
    p.add_argument("--reparar-tarjetas", action="store_true",
                   help="corrige las tarjetas a cero del bloque de FotMob (ver reparar_tarjetas)")
    args = p.parse_args(argv)
    with conn() as c:
        if args.reparar_tarjetas:
            informe = reparar_tarjetas(c, rollback=not args.aplicar)
        else:
            informe = aplicar(c, desde=args.desde, rollback=not args.aplicar)
    print(json.dumps(informe, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
