"""Estadísticas de jugadores de tenis para la ventana de Tenis de la web.

Todo sale de respuestas ya recibidas de API-Tennis (`get_players`, `get_standings`, `get_H2H`); este módulo
solo las resume. No consulta la red ni conoce la clave: el exportador del host
(`scripts/publicar_tenis_estadisticas.py`) hace las llamadas y escribe el JSON público que la API lee.

Qué NO hay, porque API-Tennis no lo trae: cuotas históricas (no se puede separar «como favorito» de
«como no favorito»), mano hábil, estatura, peso ni pista cubierta. No se inventan ni se aproximan.
"""
from __future__ import annotations

import json
import math
import os
import re
import time
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

UTC = timezone.utc
SURFACES = ("hard", "clay", "grass")
WINDOWS = (30, 90, 360)
FORM_MATCHES = 10
H2H_MATCHES = 6
RANKING_SEASONS = 6
MAX_AGE_HOURS = 14


def _int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _day(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _record(won, lost):
    won, lost = won or 0, lost or 0
    total = won + lost
    return {"won": won, "lost": lost, "rate": round(won / total, 4) if total else None}


def _sets(row):
    """Marcadores por set [(a, b), ...] del primer y segundo jugador del partido."""
    sets = []
    for item in row.get("scores") or []:
        a, b = _int(item.get("score_first")), _int(item.get("score_second"))
        if a is not None and b is not None:
            sets.append((a, b))
    return sets


def _round_stage(text):
    """Primeras rondas, rondas avanzadas o final, a partir del texto de API-Tennis."""
    text = str(text or "")
    found = re.search(r"1/(\d+)-finals", text)
    if found:
        return "avanzada" if int(found.group(1)) <= 8 else "inicial"
    if re.search(r"\bfinal\b", text, re.I) and "semi" not in text.lower():
        return "avanzada"
    if re.search(r"round|qualif|1st|2nd", text, re.I):
        return "inicial"
    return None


def match_summary(row, player_key):
    """Un partido terminado de `player_key`, o None si no es de individuales o no se completó."""
    if "singles" not in str(row.get("event_type_type", "")).lower():
        return None
    if row.get("event_status") not in ("Finished", "Retired") or row.get("event_winner") not in ("First Player", "Second Player"):
        return None
    first = row.get("first_player_key") == player_key
    if not first and row.get("second_player_key") != player_key:
        return None
    won = (row["event_winner"] == "First Player") == first
    sets = [pair for pair in _sets(row) if pair != (0, 0)]     # API-Tennis rellena con 0-0 los sets que no se jugaron
    mine = [(a, b) if first else (b, a) for a, b in sets]
    return {
        "date": str(row.get("event_date", ""))[:10],
        "won": won,
        "opponent": row.get("event_second_player") if first else row.get("event_first_player"),
        "opponent_key": row.get("second_player_key") if first else row.get("first_player_key"),
        "tournament": row.get("tournament_name"),
        "round": str(row.get("tournament_round") or "").split(" - ", 1)[-1] or None,
        "stage": _round_stage(row.get("tournament_round")),
        "qualification": str(row.get("event_qualification")) == "True",
        "score": " ".join(f"{a}-{b}" for a, b in mine) or None,
        "sets": len(sets),
        "tiebreak": any(max(a, b) == 7 and min(a, b) == 6 for a, b in sets),
        "retired": row.get("event_status") == "Retired",
        # Un partido suspendido o con retirada a medias no dice nada de cuántos sets suele durar un encuentro.
        "complete": row.get("event_status") == "Finished" and len(sets) >= 2,
    }


def form(results, player_key, today):
    """Forma reciente a partir de los últimos partidos que entrega API-Tennis (hasta 10)."""
    matches = [m for m in (match_summary(r, player_key) for r in results or []) if m and _day(m["date"])]
    matches.sort(key=lambda m: m["date"], reverse=True)
    matches = matches[:FORM_MATCHES]
    if not matches:
        return None
    windows = {}
    for days in WINDOWS:
        inside = [m for m in matches if (today - _day(m["date"])).days <= days]
        windows[str(days)] = dict(_record(sum(m["won"] for m in inside), sum(not m["won"] for m in inside)), matches=len(inside))
    streak = 0
    for m in matches:
        if streak == 0:
            streak = 1 if m["won"] else -1
        elif (streak > 0) == m["won"]:
            streak += 1 if m["won"] else -1
        else:
            break
    weights = [FORM_MATCHES - i for i in range(len(matches))]
    index = round(100 * sum(w for w, m in zip(weights, matches) if m["won"]) / sum(weights))

    def stage(name):
        picked = [m for m in matches if m["stage"] == name]
        return dict(_record(sum(m["won"] for m in picked), sum(not m["won"] for m in picked)), matches=len(picked))

    qual = [m for m in matches if m["qualification"]]
    full = [m for m in matches if m["complete"]]
    return {
        "matches": matches, "windows": windows, "streak": streak, "index": index,
        "complete_matches": len(full),
        "over_2_5_sets": round(sum(m["sets"] >= 3 for m in full) / len(full), 4) if full else None,
        "tiebreaks": round(sum(m["tiebreak"] for m in full) / len(full), 4) if full else None,
        "stages": {"inicial": stage("inicial"), "avanzada": stage("avanzada")},
        "qualification": dict(_record(sum(m["won"] for m in qual), sum(not m["won"] for m in qual)), matches=len(qual)),
    }


def _age(birthday, today):
    try:
        born = datetime.strptime(str(birthday), "%d.%m.%Y").date()
    except ValueError:
        return None
    years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return years if 14 <= years <= 60 else None


def profile(player_key, players_response, standing, results, today):
    """Perfil de un jugador: clasificación, temporada, superficies, historial de ranking y forma."""
    info = (players_response or [{}])[0] if isinstance(players_response, list) else (players_response or {})
    singles = [s for s in info.get("stats") or [] if str(s.get("type", "")).lower() == "singles" and _int(s.get("season"))]
    singles.sort(key=lambda s: _int(s["season"]), reverse=True)
    this_year = singles[0] if singles and _int(singles[0]["season"]) == today.year else None
    surfaces = {}
    for name in SURFACES:
        career_won = sum(_int(s.get(f"{name}_won")) or 0 for s in singles)
        career_lost = sum(_int(s.get(f"{name}_lost")) or 0 for s in singles)
        season = _record(_int((this_year or {}).get(f"{name}_won")), _int((this_year or {}).get(f"{name}_lost"))) if this_year else None
        surfaces[name] = {"career": _record(career_won, career_lost), "season": season}
    history = [{"season": _int(s["season"]), "rank": _int(s.get("rank")), "titles": _int(s.get("titles")) or 0,
                **_record(_int(s.get("matches_won")), _int(s.get("matches_lost")))} for s in singles[:RANKING_SEASONS]]
    return {
        "key": player_key,
        "name": info.get("player_full_name") or info.get("player_name"),
        "country": info.get("player_country") or None,
        "age": _age(info.get("player_bday"), today),
        "rank": standing.get("place") if standing else None,
        "points": _int(standing.get("points")) if standing else None,
        "movement": standing.get("movement") if standing else None,
        "season": ({"season": _int(this_year["season"]), "titles": _int(this_year.get("titles")) or 0,
                    **_record(_int(this_year.get("matches_won")), _int(this_year.get("matches_lost")))} if this_year else None),
        "career": _record(sum(_int(s.get("matches_won")) or 0 for s in singles), sum(_int(s.get("matches_lost")) or 0 for s in singles)),
        "surfaces": surfaces,
        "ranking_history": history,
        "form": form(results, player_key, today),
    }


def head_to_head(rows, first_key, second_key):
    meetings = [m for m in (match_summary(r, first_key) for r in rows or []) if m and m["opponent_key"] == second_key]
    meetings.sort(key=lambda m: m["date"], reverse=True)
    return {"first_wins": sum(m["won"] for m in meetings), "second_wins": sum(not m["won"] for m in meetings),
            "matches": meetings[:H2H_MATCHES]}


def build_event(fixture, players, standings, h2h_response, today):
    """Estadísticas de un partido. `players` = {key: respuesta de get_players}; `standings` = {key: fila de clasificación}."""
    first, second = fixture["first_player_key"], fixture["second_player_key"]
    result = (h2h_response or {}).get("result") or {}
    return {
        "event_id": str(fixture["event_key"]), "surface": fixture.get("surface"), "circuit": fixture.get("circuit"),
        "players": [profile(first, players.get(first), standings.get(first), result.get("firstPlayerResults"), today),
                    profile(second, players.get(second), standings.get(second), result.get("secondPlayerResults"), today)],
        "h2h": head_to_head(result.get("H2H"), first, second),
    }


# ---- lectura del JSON público (lo que sirve la API) ---------------------------------------------

def _finite(value):
    if isinstance(value, dict):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return not (isinstance(value, float) and not math.isfinite(value))


def read_feed(path, now=None):
    now = now or datetime.now(UTC)
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        generated = datetime.fromisoformat(value["generated_at"].replace("Z", "+00:00")).astimezone(UTC)
        if generated > now + timedelta(minutes=5) or now - generated > timedelta(hours=MAX_AGE_HOURS):
            return {"state": "stale", "events": {}}
        events = {str(k): v for k, v in value["events"].items() if isinstance(v, dict) and isinstance(v.get("players"), list)
                  and len(v["players"]) == 2 and _finite(v)}
        return {"state": "ok", "generated_at": value["generated_at"], "events": events}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {"state": "unavailable", "events": {}}


@lru_cache(maxsize=2)
def _cached(path, minute):
    return read_feed(path)


def public_event(event_id):
    path = os.environ.get("QF_TENNIS_STATS_FEED", "/srv/quantfut/artifacts/public-sports/tennis_stats.json")
    feed = _cached(path, int(time.time() // 60))
    event = feed["events"].get(str(event_id))
    return None if event is None else {"state": feed["state"], "generated_at": feed["generated_at"], "source": "API-Tennis", **event}
