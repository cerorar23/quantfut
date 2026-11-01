"""Exportador de tenis y lector de su salida pública; sin acceso web a originales.

El exportador corre en el host con lectura de los sellos existentes. La API solo
lee su JSON público, con campos permitidos y caducidad, en el volumen ya existente.
No importa el motor ni ejecuta cálculos de predicción.
"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import time

UTC = timezone.utc
# Un partido de tenis dura horas: pasado este margen sin resultado oficial la fuente lo dejó sin cerrar.
NO_RESULT_AFTER = timedelta(hours=36)


def _utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _prob(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 < value < 1


def _checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _results(root, now, fixture_root=None):
    events = {}
    for receipt_path in sorted((Path(fixture_root) if fixture_root else root / "fixtures").glob("*/receipt.json")):
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("method") != "get_fixtures" or receipt.get("http_status") != 200:
                continue
            if _utc(receipt["received_at"]) > now:
                continue
            body = (receipt_path.parent / "response.json").read_bytes()
            if hashlib.sha256(body).hexdigest() != receipt["sha256"]:
                continue
            for row in json.loads(body).get("result") or []:
                key = str(row["event_key"])
                if key not in events or receipt["received_at"] > events[key][0]:
                    events[key] = (receipt["received_at"], row)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return events


def _row_start(row):
    try:
        return _utc(f"{row['event_date']}T{row.get('event_time') or '00:00'}:00Z")
    except (KeyError, TypeError, ValueError, AttributeError):
        return None


def _closed_set(a, b):
    return (max(a, b) == 6 and min(a, b) <= 4) or (max(a, b) == 7 and min(a, b) in (5, 6))


def _closed_sets(row):
    """Sets terminados del marcador oficial y si el resto del marcador es el set en curso; None si no se entiende."""
    try:
        sets = [(int(float(s["score_first"])), int(float(s["score_second"]))) for s in sorted(row.get("scores") or [], key=lambda s: int(s["score_set"]))]
    except (KeyError, TypeError, ValueError):
        return None
    closed = []
    for a, b in sets:
        if not _closed_set(a, b):
            break
        closed.append((a, b))
    return closed, len(sets) - len(closed)


def _outcome(contract, row, best_of):
    """win/loss/push de un contrato con las reglas del motor (retiro: lo no jugado se devuelve); None si no se puede liquidar."""
    status = row.get("event_status")
    if status == "Walk Over":
        return "push"
    found = _closed_sets(row)
    if found is None:
        return None
    closed, open_sets = found
    kind, selection, line = contract.get("kind"), contract.get("selection"), contract.get("line")
    wins_a = sum(a > b for a, b in closed)
    wins_b = len(closed) - wins_a
    if status == "Finished":
        needed = best_of // 2 + 1
        if open_sets or max(wins_a, wins_b) != needed or min(wins_a, wins_b) >= needed or (wins_a > wins_b) != (row.get("event_winner") == "First Player"):
            return None
    elif status == "Retired":
        if open_sets > 1:
            return None
    else:
        return None
    if kind == "set_winner":
        number = contract.get("set_number") or 0
        if number < 1:
            return None
        if len(closed) < number:
            return "push"
        a, b = closed[number - 1]
        value = (a - b) * (1 if selection == "A" else -1)
    elif status == "Retired":
        return None if kind == "tiebreak" else "push"
    elif kind == "tiebreak":
        value = 1 if any(max(a, b) == 7 and min(a, b) == 6 for a, b in closed) == (selection == "yes") else -1
    elif kind == "sets_total" and isinstance(line, (int, float)):
        value = (len(closed) - line) * (1 if selection == "over" else -1)
    elif kind == "sets_handicap" and isinstance(line, (int, float)):
        value = (wins_a - wins_b if selection == "A" else wins_b - wins_a) + line
    elif kind in ("games_total", "games_handicap") and isinstance(line, (int, float)):
        games_a, games_b = sum(a for a, _ in closed), sum(b for _, b in closed)
        if kind == "games_total":
            value = (games_a + games_b - line) * (1 if selection == "over" else -1)
        else:
            value = (games_a - games_b if selection == "A" else games_b - games_a) + line
    else:
        return None
    return "push" if abs(value) < 1e-12 else "win" if value > 0 else "loss"


def projection(root, now=None, fixture_root=None):
    now = now or datetime.now(UTC)
    root = Path(root)
    if not (root / "predictions").is_dir():
        return dict(sport="tenis", state="unavailable", events=[], problems=0)
    results, events, problems = _results(root, now, fixture_root), [], 0
    for path in (root / "predictions").glob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            digest = value.pop("payload_sha256")
            if value.get("schema") != "tennis-intake-sealed-v1" or _checksum(value) != digest:
                raise ValueError("Invalid seal")
            start, sealed = _utc(value["provider_start"]), _utc(value["sealed_at"])
            if sealed >= start or sealed > now:
                raise ValueError("Invalid publication time")
            if not now - timedelta(days=7) <= start <= now + timedelta(days=7):
                continue
            forecast = value["forecast"]
            players, p = forecast["players"], forecast["winner"]["final_winner"]
            if len(players) != 2 or not _prob(p):
                raise ValueError("Invalid forecast")
            row = results.get(str(value["event_key"]), (None, {}))[1]
            state = row.get("event_status")
            finished = start <= now and state in ("Finished", "Retired") and row.get("event_winner") in ("First Player", "Second Player")
            cancelled = state == "Cancelled"
            walkover = state == "Walk Over"
            shown = start
            row_start = _row_start(row)
            if not (finished or cancelled or walkover) and row_start is not None and row_start > start:
                shown = row_start
            best_of = value["rules"].get("best_of") or 3
            returned = cancelled or walkover or (finished and state == "Retired" and not (_closed_sets(row) or ([], 0))[0])
            actual = int(row["event_winner"] == "First Player") if finished else None
            winner_outcome = "push" if returned else ("win" if (p >= .5) == bool(actual) else "loss") if finished else None
            markets = [dict(id="winner", label="Ganador del partido", selection=players[0] if p >= .5 else players[1], probability=p if p >= .5 else 1-p,
                            price=None, reference="Probabilidad del motor", outcome=winner_outcome)]
            # Solo probabilidades y contratos de la publicación sellada; nunca los coeficientes internos.
            for index, market in enumerate(forecast.get("markets", [])):
                contract, probabilities = market.get("contract", {}), market.get("probabilities", {})
                kind, selection, line = contract.get("kind"), contract.get("selection"), contract.get("line")
                labels = {"games_total": "Juegos totales", "sets_total": "Sets totales", "games_handicap": "Hándicap de juegos", "sets_handicap": "Hándicap de sets", "set_winner": "Ganador de set", "tiebreak": "Tie-break"}
                if kind not in labels or not _prob(probabilities.get("win")):
                    continue
                side = {"A": players[0], "B": players[1], "over": "Más de", "under": "Menos de", "yes": "Sí", "no": "No"}.get(selection)
                if side is None:
                    continue
                text = f"{side} {line:g}" if isinstance(line, (int, float)) and math.isfinite(line) else side
                label = labels[kind] + (f" · set {contract['set_number']}" if contract.get("set_number") else "")
                markets.append(dict(id=f"{kind}-{index}", label=label, selection=text, probability=probabilities["win"], price=None,
                                    reference="Probabilidad del motor; cuota no publicada", push_probability=probabilities.get("push", 0),
                                    outcome="push" if cancelled else _outcome(contract, row, best_of) if finished or walkover else None))
            status = ("finished" if finished or walkover else "cancelled" if cancelled else "scheduled" if shown > now
                      else "no_result" if now - shown > NO_RESULT_AFTER else "awaiting_result")
            events.append(dict(id=str(value["event_key"]), sport="tenis", home=players[0], away=players[1],
                start=shown.isoformat() if shown != start else value["provider_start"],
                league=f"{value['circuit']} · {value['tournament']}", surface=value["rules"]["surface"], sealed_at=value["sealed_at"], seal=digest,
                status=status, markets=markets, score=row.get("event_final_result") if finished else None, actionable=False))
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            problems += 1
    events.sort(key=lambda event: (event["start"], event["id"]))
    return dict(sport="tenis", state="ok" if not problems else "partial", generated_at=now.isoformat(), events=events, problems=problems)


def read_public_feed(path, now=None):
    now = now or datetime.now(UTC)
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if value.get("state") not in ("ok", "partial") or not isinstance(value.get("events"), list):
            raise ValueError("Feed unavailable")
        generated = _utc(value["generated_at"])
        if generated > now + timedelta(minutes=5) or now - generated > timedelta(hours=2):
            return dict(sport="tenis", state="stale", events=[], problems=0)
        events = []
        for event in value["events"]:
            if not isinstance(event.get("seal"), str) or len(event["seal"]) != 64 or not event.get("home") or not event.get("away"):
                continue
            clean = {k: event.get(k) for k in ("id", "sport", "home", "away", "start", "league", "surface", "sealed_at", "seal", "status", "score")}
            clean["actionable"] = False
            clean["markets"] = [{k: m.get(k) for k in ("id", "label", "selection", "probability", "price", "reference", "push_probability", "outcome")}
                                for m in event.get("markets", []) if _prob(m.get("probability")) and m.get("price") is None]
            if clean["markets"] and clean["sport"] == "tenis":
                events.append(clean)
        return dict(sport="tenis", state=value["state"], generated_at=value["generated_at"], events=events, problems=value.get("problems", 0))
    except (OSError, ValueError, KeyError, TypeError):
        return dict(sport="tenis", state="unavailable", events=[], problems=0)


@lru_cache(maxsize=2)
def _cached(path, minute):
    return read_public_feed(path)


def public_data():
    path = os.environ.get("QF_TENNIS_PUBLIC_FEED", "/srv/quantfut/artifacts/public-sports/tennis.json")
    return _cached(path, int(time.time() // 60))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--fixtures", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(projection(args.root, fixture_root=args.fixtures), ensure_ascii=False, allow_nan=False))
