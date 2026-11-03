"""SportsAPIPro (SofaScore) -> respuesta de `get_fixtures` de API-Tennis, para el motor de tenis (T2).

API-Tennis vence y no se renueva. El motor (`tennis_engine.state_capture.TennisStateCapture`) acepta un `transport`
inyectable y lee `result[]` con `event_key`, `first/second_player_key`, `tournament_key`, `event_status`, `scores`…
Este módulo convierte un partido de SofaScore a ese formato para que el resto del motor no cambie.

Tres cosas se mantienen idénticas a lo que ya conoce el motor, usando la tabla de `tenis_equivalencias`:
  * `event_key`: el de API-Tennis si el partido ya se emparejó (los forecasts sellados esperan su resultado con él);
    si no, 9.000.000.000 + id de SofaScore.
  * `first/second_player_key`: el `player_key` de API-Tennis (historia Elo y estados) si el jugador está en la tabla;
    si no, 9.000.000.000 + id de SofaScore, que entra sin historia. En un partido ya emparejado se respeta quién era
    «primero» y quién «segundo».
  * `tournament_key`: el de API-Tennis (así se resuelve la sede); si no, 9.000.000.000 + utid, sin sede.

Solo biblioteca estándar. Sin peticiones: recibe los eventos ya descargados.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SINTETICO = 9_000_000_000
TIPOS = {"ATP": "Atp Singles", "WTA": "Wta Singles"}
CLAVE_TOUR = {"265": "ATP", "266": "WTA"}


def indice(raiz) -> dict:
    """Tablas de equivalencia de `tenis_equivalencias` listas para convertir."""
    db = sqlite3.connect("file:%s?mode=ro" % (Path(raiz) / "index.sqlite").resolve().as_posix(), uri=True)
    db.row_factory = sqlite3.Row
    por_ss = {}
    for r in db.execute("SELECT sofascore_id, player_key, partidos FROM equivalencias ORDER BY partidos"):
        por_ss.setdefault(r["sofascore_id"], []).append(r["player_key"])
    jugadores = {k: v[-1] for k, v in por_ss.items() if len(set(v)) == 1}       # ambiguo -> sintético
    torneos = {}
    for r in db.execute("SELECT utid, tournament_key, nombre_at FROM torneos ORDER BY partidos"):
        torneos[r["utid"]] = (r["tournament_key"], r["nombre_at"])
    partidos = {r["sofascore_event"]: dict(r) for r in db.execute(
        "SELECT event_key, sofascore_event, first_key, second_key, directo FROM partidos_emparejados")}
    db.close()
    return {"jugadores": jugadores, "torneos": torneos, "partidos": partidos}


def estado(e: dict) -> str:
    tipo = ((e.get("status") or {}).get("type") or "").lower()
    desc = ((e.get("status") or {}).get("description") or "").lower()
    if tipo == "finished":
        if "retire" in desc:
            return "Retired"
        if "walk" in desc:
            return "Walk Over"
        return "Finished"
    if tipo == "inprogress":
        n = sum(1 for i in range(1, 6) if (e.get("homeScore") or {}).get("period%d" % i) is not None)
        return "Set %d" % min(max(n, 1), 5)
    if tipo in ("canceled", "cancelled"):
        return "Cancelled"
    if tipo in ("postponed", "interrupted", "delayed"):
        return "Interrupted"
    return ""


DESEMPATE = False  # API-Tennis anota los puntos del desempate solo en algunos partidos: enteros simples (47 vs 46 de 60)


def juegos(e: dict, invertido: bool) -> list[dict]:
    """Juegos por set como los da API-Tennis: un set con desempate lleva los puntos de este («7.9» / «6.7»);
    sin ningún set queda `0 - 0`."""
    casa, fuera = (e.get("homeScore") or {}), (e.get("awayScore") or {})
    a, b = (fuera, casa) if invertido else (casa, fuera)

    def marca(lado, i):
        x, d = lado.get("period%d" % i), lado.get("period%dTieBreak" % i)
        return None if x is None else (str(x) if d is None or not DESEMPATE else "%s.%s" % (x, d))
    out = []
    for i in range(1, 6):
        x, y = marca(a, i), marca(b, i)
        if x is None and y is None:
            continue
        out.append({"score_first": x if x is not None else "0", "score_second": y if y is not None else "0",
                    "score_set": str(i)})
    return out or [{"score_first": "0", "score_second": "0", "score_set": "1"}]


def convertir(e: dict, ix: dict) -> dict | None:
    """Un partido individual ATP/WTA de SofaScore -> una fila de `get_fixtures`. None si no es de esos circuitos."""
    circuito = ((e.get("tournament") or {}).get("category") or {}).get("name")
    if circuito not in TIPOS or "Doubles" in (e["tournament"].get("name") or ""):
        return None
    conocido = ix["partidos"].get(e["id"])
    home, away = e["homeTeam"], e["awayTeam"]
    clave = lambda j: ix["jugadores"].get(j["id"], SINTETICO + j["id"])
    if conocido and conocido["first_key"] is not None:
        invertido = not conocido["directo"]
        primero, segundo = (away, home) if invertido else (home, away)
        k1, k2 = conocido["first_key"], conocido["second_key"]
    else:
        invertido, primero, segundo = False, home, away
        k1, k2 = clave(primero), clave(segundo)
    inicio = datetime.fromtimestamp(e["startTimestamp"], timezone.utc)
    utid = ((e["tournament"].get("uniqueTournament") or {}).get("id"))
    tk, nombre_at = ix["torneos"].get(utid, (SINTETICO + (utid or 0), None))
    nombre = nombre_at or re.split(r",", e["tournament"].get("name") or "")[0].strip()
    st = estado(e)
    c, f = (e.get("homeScore") or {}), (e.get("awayScore") or {})
    sets_a, sets_b = (f.get("current"), c.get("current")) if invertido else (c.get("current"), f.get("current"))
    ganador = e.get("winnerCode")
    if ganador in (1, 2):
        ganador = "First Player" if (ganador == 1) != invertido else "Second Player"
    else:
        ganador = None
    ronda = ((e.get("roundInfo") or {}).get("name")) or ""
    return {
        "event_key": conocido["event_key"] if conocido else SINTETICO + e["id"],
        "event_date": inicio.date().isoformat(), "event_time": inicio.strftime("%H:%M"),
        "event_first_player": primero.get("shortName") or primero["name"], "first_player_key": k1,
        "event_second_player": segundo.get("shortName") or segundo["name"], "second_player_key": k2,
        "event_final_result": ("%s - %s" % (sets_a, sets_b)) if st in ("Finished", "Retired") and sets_a is not None else "-",
        "event_winner": ganador if st in ("Finished", "Retired", "Walk Over") else None,
        "event_status": st, "event_type_type": TIPOS[circuito],
        "tournament_name": nombre, "tournament_key": tk,
        "tournament_round": ("%s %s - %s" % (circuito, nombre, ronda)).strip(" -"),
        "tournament_season": str((e.get("season") or {}).get("year") or inicio.year)[:4],
        "event_live": "1" if st.startswith("Set ") else "0", "event_qualification": "False",
        "scores": juegos(e, invertido), "sofascore_event": e["id"],
    }


def respuesta(eventos: list[dict], ix: dict, tipo: str, desde: str, hasta: str) -> bytes:
    """Cuerpo `{"success": 1, "result": [...]}` con los partidos del circuito `tipo` (265/266) entre las fechas."""
    circuito = CLAVE_TOUR[tipo]
    filas = {}
    for e in eventos:
        if ((e.get("tournament") or {}).get("category") or {}).get("name") != circuito:
            continue
        f = convertir(e, ix)
        if f and desde <= f["event_date"] <= hasta:
            filas[f["event_key"]] = f
    orden = sorted(filas.values(), key=lambda r: (r["event_date"], r["event_time"], r["event_key"]))
    return json.dumps({"success": 1, "result": orden}, ensure_ascii=False).encode("utf-8")


def comparar(convertido: dict, real: dict) -> dict:
    """Campo a campo contra la fila de API-Tennis del mismo partido (validación)."""
    def juegos_de(r):
        s = r.get("scores")
        if isinstance(s, str):
            s = eval_lista(s)
        return [(x.get("score_first"), x.get("score_second")) for x in s or []]
    return {
        "estado": convertido["event_status"] == real.get("event_status"),
        "ganador": convertido["event_winner"] == (real.get("event_winner") or None),
        "resultado": convertido["event_final_result"] == real.get("event_final_result"),
        "juegos": juegos_de(convertido) == juegos_de(real),
        "fecha_hora": (convertido["event_date"], convertido["event_time"]) == (real.get("event_date"), real.get("event_time")),
        "jugadores": (convertido["first_player_key"], convertido["second_player_key"]) ==
                     (real.get("first_player_key"), real.get("second_player_key")),
        "torneo": convertido["tournament_key"] == real.get("tournament_key"),
    }


def eval_lista(texto: str):
    import ast
    try:
        return ast.literal_eval(texto)
    except (ValueError, SyntaxError):
        return []


def resumen(comparaciones: list[dict]) -> dict:
    n = len(comparaciones)
    return {"partidos": n, **{k: sum(c[k] for c in comparaciones) for k in (comparaciones[0] if comparaciones else {})}}
