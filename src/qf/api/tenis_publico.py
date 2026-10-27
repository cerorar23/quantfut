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
            finished = start <= now and row.get("event_status") in ("Finished", "Retired") and row.get("event_winner") in ("First Player", "Second Player")
            actual = int(row["event_winner"] == "First Player") if finished else None
            markets = [dict(id="winner", label="Ganador del partido", selection=players[0] if p >= .5 else players[1], probability=p if p >= .5 else 1-p,
                            price=None, reference="Probabilidad del motor", outcome=("win" if (p >= .5) == bool(actual) else "loss") if finished else None)]
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
                                    reference="Probabilidad del motor; cuota no publicada", push_probability=probabilities.get("push", 0), outcome=None))
            events.append(dict(id=str(value["event_key"]), sport="tenis", home=players[0], away=players[1], start=value["provider_start"],
                league=f"{value['circuit']} · {value['tournament']}", surface=value["rules"]["surface"], sealed_at=value["sealed_at"], seal=digest,
                status="finished" if finished else "scheduled" if start > now else "awaiting_result", markets=markets,
                score=row.get("event_final_result") if finished else None, actionable=False))
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
