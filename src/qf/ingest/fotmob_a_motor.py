"""Pasa a tablas con clave `match_id` el contexto del archivo FotMob (db/075).

Una sola pasada sobre `historical_football_matches` (provider='fotmob'): por cada partido enlazado
saca del original comprimido el contexto (ronda, ida/vuelta, árbitro, asistencia, entrenadores, valor del
once, clima), los jugadores de la alineación con su valor de mercado y la lista de no disponibles.

Reglas:
- Un dato ausente o inválido queda NULL, nunca 0 ni un valor inventado.
- Solo se inserta (ON CONFLICT DO NOTHING): repetir la carga no cambia nada.
- Los identificadores de jugador son de FotMob; no se mezclan con los de API-Football.
- El clima de FotMob lleva la hora a la que lo midió. Solo `clima_en_partido` indica que cae entre 1 h antes
  y 3 h después del saque; fuera de esa ventana es el clima de cuando se guardó la página y no se debe usar.
- Todo se guardó después del partido (`recibido_en`); las bajas son una reconstrucción, no lo sabido antes.
"""
from __future__ import annotations

import gzip
import json
import logging
import math
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

VENTANA_CLIMA = (timedelta(hours=-1), timedelta(hours=3))
LOTE = 200


def _num(v, entero: bool = False, minimo: float | None = 0.0):
    """Número finito (y no negativo salvo que se pida otra cosa), o None."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if not math.isfinite(v) or (minimo is not None and v < minimo):
        return None
    return int(round(v)) if entero else float(v)


def _texto(v) -> str | None:
    return v.strip() if isinstance(v, str) and v.strip() else None


def _fecha(v) -> datetime | None:
    if not isinstance(v, str):
        return None
    try:
        d = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else None


def _jugador(p: dict, lado: str, titular: bool) -> dict | None:
    pid = _num(p.get("id"), entero=True)
    if pid is None or pid <= 0:
        return None
    rating = ((p.get("performance") or {}).get("rating"))
    return {"side": lado, "jugador_id": pid, "nombre": _texto(p.get("name")), "titular": titular,
            "posicion_id": _num(p.get("positionId"), entero=True),
            "posicion_habitual_id": _num(p.get("usualPlayingPositionId"), entero=True),
            "camiseta": _texto(str(p["shirtNumber"])) if p.get("shirtNumber") is not None else None,
            "edad": _num(p.get("age"), entero=True),
            "valor_mercado": _num(p.get("marketValue"), entero=True),
            "rating": _num(rating)}


def _baja(p: dict, lado: str) -> dict | None:
    pid = _num(p.get("id"), entero=True)
    if pid is None or pid <= 0:
        return None
    u = p.get("unavailability") or {}
    return {"side": lado, "jugador_id": pid, "nombre": _texto(p.get("name")),
            "edad": _num(p.get("age"), entero=True),
            "posicion_id": _num(p.get("positionId"), entero=True),
            "valor_mercado": _num(p.get("marketValue"), entero=True),
            "tipo": _texto(u.get("type")), "lesion_id": _num(u.get("injuryId"), entero=True),
            "regreso_texto": _texto(u.get("expectedReturn")),
            "regreso_fecha": _fecha(u.get("expectedReturnDate"))}


def extraer(payload: dict, kickoff: datetime) -> dict:
    """Contexto, jugadores y bajas de un original de FotMob. No toca la base."""
    general = payload.get("general") or {}
    cabecera = (payload.get("header") or {}).get("status") or {}
    contenido = payload.get("content") or {}
    caja = ((contenido.get("matchFacts") or {}).get("infoBox")) or {}
    torneo = caja.get("Tournament") or {}
    arbitro = caja.get("Referee") or {}
    estadio = caja.get("Stadium") or {}
    alin = contenido.get("lineup") or {}

    p = {"ronda": _texto(torneo.get("round")) or _texto(general.get("matchRound")),
         "ronda_nombre": _texto(torneo.get("roundName")) or _texto(general.get("leagueRoundName")),
         "ida_vuelta": caja.get("legInfo") if isinstance(caja.get("legInfo"), (dict, list)) else None,
         "perdedor_global": _texto(cabecera.get("whoLostOnAggregated")),
         "arbitro": _texto(arbitro.get("text")), "arbitro_pais": _texto(arbitro.get("country")),
         "asistencia": _num(caja.get("Attendance"), entero=True),
         "estadio": _texto(estadio.get("name"))}

    jugadores, bajas = [], []
    for lado, clave in (("home", "homeTeam"), ("away", "awayTeam")):
        eq = alin.get(clave) or {}
        sufijo = "local" if lado == "home" else "visita"
        coach = eq.get("coach") or {}
        p["formacion_" + sufijo] = _texto(eq.get("formation"))
        p["rating_" + sufijo] = _num(eq.get("rating"))
        p["valor_xi_" + sufijo] = _num(eq.get("totalStarterMarketValue"), entero=True)
        p["edad_xi_" + sufijo] = _num(eq.get("averageStarterAge"))
        p["entrenador_" + sufijo + "_id"] = _num(coach.get("id"), entero=True)
        p["entrenador_" + sufijo] = _texto(coach.get("name"))
        for lista, titular in ((eq.get("starters"), True), (eq.get("subs"), False)):
            for x in lista if isinstance(lista, list) else []:
                j = _jugador(x, lado, titular) if isinstance(x, dict) else None
                if j:
                    jugadores.append(j)
        for x in eq.get("unavailable") if isinstance(eq.get("unavailable"), list) else []:
            b = _baja(x, lado) if isinstance(x, dict) else None
            if b:
                bajas.append(b)

    w = contenido.get("weather") if isinstance(contenido.get("weather"), dict) else {}
    actualizado = _fecha(w.get("lastUpdated"))
    desfase = (actualizado - kickoff) if actualizado else None
    p.update({
        "clima_temperatura_c": _num(w.get("temperature"), minimo=None),
        "clima_viento": _num(w.get("windSpeed")), "clima_direccion": _texto(w.get("windDirectionCardinal")),
        "clima_humedad": _num(w.get("relativeHumidity")), "clima_precipitacion": _num(w.get("precipitation")),
        "clima_nubosidad": _num(w.get("cloudCover")), "clima_descripcion": _texto(w.get("description")),
        "clima_api": _texto(w.get("apiUsed")), "clima_actualizado": actualizado,
        "clima_desfase_horas": None if desfase is None else desfase.total_seconds() / 3600,
        "clima_en_partido": None if desfase is None else VENTANA_CLIMA[0] <= desfase <= VENTANA_CLIMA[1]})
    if p["clima_temperatura_c"] is None:  # sin temperatura no hay medición utilizable
        p["clima_en_partido"] = None if actualizado is None else False
    return {"partido": p, "jugadores": jugadores, "bajas": bajas}


COLS_PARTIDO = ("ronda", "ronda_nombre", "ida_vuelta", "perdedor_global", "arbitro", "arbitro_pais",
                "asistencia", "estadio", "formacion_local", "formacion_visita", "rating_local", "rating_visita",
                "valor_xi_local", "valor_xi_visita", "edad_xi_local", "edad_xi_visita",
                "entrenador_local_id", "entrenador_local", "entrenador_visita_id", "entrenador_visita",
                "clima_temperatura_c", "clima_viento", "clima_direccion", "clima_humedad",
                "clima_precipitacion", "clima_nubosidad", "clima_descripcion", "clima_api",
                "clima_actualizado", "clima_desfase_horas", "clima_en_partido")
COLS_JUGADOR = ("side", "jugador_id", "nombre", "titular", "posicion_id", "posicion_habitual_id",
                "camiseta", "edad", "valor_mercado", "rating")
COLS_BAJA = ("side", "jugador_id", "nombre", "edad", "posicion_id", "valor_mercado", "tipo", "lesion_id",
             "regreso_texto", "regreso_fecha")

_SQL_PARTIDO = (
    "INSERT INTO fotmob_partido (match_id, source_match_id, raw_sha256, recibido_en, "
    + ", ".join(COLS_PARTIDO) + ") VALUES (%s, %s, %s, %s, " + ", ".join(["%s"] * len(COLS_PARTIDO))
    + ") ON CONFLICT (match_id) DO NOTHING")
_SQL_JUGADOR = (
    "INSERT INTO fotmob_jugador_partido (match_id, " + ", ".join(COLS_JUGADOR) + ") VALUES (%s, "
    + ", ".join(["%s"] * len(COLS_JUGADOR)) + ") ON CONFLICT DO NOTHING")
_SQL_BAJA = (
    "INSERT INTO fotmob_baja (match_id, " + ", ".join(COLS_BAJA) + ") VALUES (%s, "
    + ", ".join(["%s"] * len(COLS_BAJA)) + ") ON CONFLICT DO NOTHING")

_SQL_PENDIENTES = """
    SELECT h.match_id, h.source_match_id, h.raw_sha256, h.captured_at, h.raw_payload_gzip, m.kickoff_utc
    FROM historical_football_matches h JOIN matches m USING (match_id)
    WHERE h.provider = 'fotmob' AND h.match_id IS NOT NULL AND h.match_id > %s
      AND NOT EXISTS (SELECT 1 FROM fotmob_partido p WHERE p.match_id = h.match_id)
    ORDER BY h.match_id LIMIT %s"""


def _json(v):
    from psycopg.types.json import Jsonb
    return None if v is None else Jsonb(v)


def cargar(c, limite: int | None = None, confirmar: bool = False) -> dict:
    """Procesa los partidos aún sin cargar, por lotes ordenados por `match_id`.

    Con `confirmar` cada lote se confirma al terminar (un fallo no pierde lo anterior y repetir retoma);
    sin él nada se confirma y el llamador revierte (ensayo).
    """
    r = {"partidos": 0, "jugadores": 0, "bajas": 0, "sin_original": 0, "con_clima_en_partido": 0}
    ultimo = ""
    while limite is None or r["partidos"] < limite:
        pedir = LOTE if limite is None else min(LOTE, limite - r["partidos"])
        filas = c.execute(_SQL_PENDIENTES, (ultimo, pedir)).fetchall()
        if not filas:
            break
        with c.cursor() as w:
            for fila in filas:
                ultimo = fila["match_id"]
                try:
                    payload = json.loads(gzip.decompress(fila["raw_payload_gzip"]))
                except (OSError, ValueError, TypeError):
                    r["sin_original"] += 1
                    continue
                x = extraer(payload, fila["kickoff_utc"])
                p = x["partido"]
                w.execute(_SQL_PARTIDO, (fila["match_id"], fila["source_match_id"], fila["raw_sha256"],
                                         fila["captured_at"],
                                         *[_json(p[k]) if k == "ida_vuelta" else p[k] for k in COLS_PARTIDO]))
                if x["jugadores"]:
                    w.executemany(_SQL_JUGADOR, [(fila["match_id"], *[j[k] for k in COLS_JUGADOR])
                                                 for j in x["jugadores"]])
                if x["bajas"]:
                    w.executemany(_SQL_BAJA, [(fila["match_id"], *[b[k] for k in COLS_BAJA])
                                              for b in x["bajas"]])
                r["partidos"] += 1
                r["jugadores"] += len(x["jugadores"])
                r["bajas"] += len(x["bajas"])
                r["con_clima_en_partido"] += 1 if p["clima_en_partido"] else 0
        if confirmar:
            c.commit()
        log.info("fotmob_a_motor: %s", r)
    return r


def main(argv=None) -> None:
    import argparse

    from ..db import conn

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limite", type=int, default=None, help="máximo de partidos de esta pasada")
    ap.add_argument("--aplicar", action="store_true", help="sin esto es un ensayo que se revierte")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    with conn() as c:
        res = cargar(c, a.limite, confirmar=a.aplicar)
        if not a.aplicar:
            c.rollback()
    print(json.dumps({**res, "aplicado": a.aplicar}, indent=1))


if __name__ == "__main__":
    main()
