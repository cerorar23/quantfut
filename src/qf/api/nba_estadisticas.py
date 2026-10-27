"""Estadísticas de partidos de NBA para la ventana de la web (forma, cara a cara y clasificación).

Esta API solo LEE el JSON público que el host escribe con `nba.web_stats` (apps/nba, marcadores finales ya validados);
no calcula nada, no consulta la red y no ve cohortes, modelos ni sellos. Un feed vencido o con números no finitos se descarta
completo: la web dice que no hay estadísticas en vez de enseñar datos viejos o rotos.
"""
from __future__ import annotations

import json
import math
import os
import time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

UTC = timezone.utc
MAX_AGE_HOURS = 6
DEFAULT_FEED = "/srv/quantfut/artifacts/public-sports/nba_stats.json"


def _finite(value):
    if isinstance(value, dict):
        return all(_finite(v) for v in value.values())
    if isinstance(value, list):
        return all(_finite(v) for v in value)
    return not (isinstance(value, float) and not math.isfinite(value))


def _valid(event):
    return (isinstance(event, dict) and isinstance(event.get("teams"), list) and len(event["teams"]) == 2
            and all(isinstance(t, dict) and isinstance(t.get("form"), dict) for t in event["teams"])
            and isinstance(event.get("h2h"), dict) and isinstance(event["h2h"].get("matches"), list) and _finite(event))


def read_feed(path, now=None):
    now = now or datetime.now(UTC)
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        generated = datetime.fromisoformat(value["generated_at"].replace("Z", "+00:00")).astimezone(UTC)
        if generated > now + timedelta(minutes=5) or now - generated > timedelta(hours=MAX_AGE_HOURS):
            return {"state": "stale", "events": {}}
        events = {str(k): v for k, v in value["events"].items() if _valid(v)}
        return {"state": "ok", "generated_at": value["generated_at"], "source": str(value.get("source") or "NBA.com"), "events": events}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {"state": "unavailable", "events": {}}


@lru_cache(maxsize=2)
def _cached(path, minute):
    return read_feed(path)


def public_event(event_id):
    path = os.environ.get("QF_NBA_STATS_FEED", DEFAULT_FEED)
    feed = _cached(path, int(time.time() // 60))
    event = feed["events"].get(str(event_id))
    return None if event is None else {"state": feed["state"], "generated_at": feed["generated_at"], "source": feed["source"], **event}
