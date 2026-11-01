"""
Ráfagas de cuotas para medir la latencia de las casas blandas (idea 3, 3B).

Cada 5 minutos, para las ligas de `settings.rafagas_ligas` con algún partido
entre T-6 h y T-15 min, una consulta de 1X2 con `bookmakers=` (≤10 casas: 1
crédito). `last_update` da el momento exacto de cada cambio, así que 5 min
bastan para fechar cuándo reaccionó cada casa.

Escribe en `odds_rafagas` y `rafagas_log` (db/038), NUNCA en `odds_snapshots`:
las ventanas, la sombra y el cierre no deben ver estas capturas. Una fila por
cambio de precio; el registro de consultas dice hasta cuándo seguía vigente.

Se detiene sola al llegar a `rafagas_max_creditos_mes` (el plan se renueva el
día 1). Diseño y medida fijados en harness/tareas.md, idea 3.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from ..config import settings
from ..db import execute, executemany, query, query_one
from .odds_worker import last_update, match_events, match_meta

log = logging.getLogger(__name__)

ANTES = timedelta(hours=6)
MIN_LEAD = timedelta(minutes=15)


def creditos_del_mes(now: datetime) -> int:
    inicio = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    row = query_one("SELECT COALESCE(sum(credits), 0) AS n FROM rafagas_log "
                    "WHERE captured_at >= %s", (inicio,))
    return int(row["n"])


def coste_previsto() -> int:
    """The Odds API cobra 1 crédito por cada 10 casas y mercado."""
    return max(1, -(-len(settings.rafagas_casas) // 10))


def _objetivos(now: datetime) -> dict[str, list[str]]:
    """{sport_key: [match_id, ...]} con partido entre T-6 h y T-15 min."""
    rows = query(
        """SELECT m.match_id, l.odds_api_key
           FROM matches m JOIN leagues l ON l.league_id = m.league_id
           WHERE m.status = 'scheduled' AND l.odds_api_key IS NOT NULL
             AND l.league_id = ANY(%s)
             AND m.kickoff_utc BETWEEN %s AND %s""",
        (list(settings.rafagas_ligas), now + MIN_LEAD, now + ANTES))
    out: dict[str, list[str]] = {}
    for r in rows:
        out.setdefault(r["odds_api_key"], []).append(r["match_id"])
    return out


def _fetch(sport_key: str) -> tuple[list[dict], int]:
    with httpx.Client(timeout=30) as c:
        r = c.get(f"{settings.odds_api_base}/sports/{sport_key}/odds", params={
            "apiKey": settings.odds_api_key, "markets": "h2h",
            "bookmakers": ",".join(settings.rafagas_casas),
            "oddsFormat": "decimal", "dateFormat": "iso"})
        r.raise_for_status()
        try:
            coste = int(r.headers.get("x-requests-last") or 1)
        except ValueError:
            coste = 1
        return r.json(), coste


def filas(ev: dict, match_id: str, now: datetime) -> list[tuple]:
    """Una fila por casa y selección del 1X2, fechada con su `last_update`."""
    home, away = ev.get("home_team"), ev.get("away_team")
    out = []
    for bk in ev.get("bookmakers", []):
        for mk in bk.get("markets", []):
            if mk.get("key") != "h2h":
                continue
            updated = last_update(mk, bk)
            if updated is None:
                continue
            for oc in mk.get("outcomes", []):
                price = oc.get("price")
                if price is None or price <= 1.0:
                    continue
                sel = ("home" if oc.get("name") == home
                       else "away" if oc.get("name") == away else "draw")
                out.append((match_id, bk["key"], sel, float(price), updated, now))
    return out


def run_once(now: datetime | None = None) -> dict:
    if getattr(settings, "odds_provider", "the_odds_api") == "propline":
        return {"consultas": 0, "source": "propline", "reason": "shared_hourly_capture"}
    now = now or datetime.now(timezone.utc)
    tope = settings.rafagas_max_creditos_mes
    objetivos = _objetivos(now) if tope > 0 else {}
    if not objetivos:
        return {"consultas": 0}
    gastados = creditos_del_mes(now)
    consultas = escritas = 0
    for sport_key, match_ids in objetivos.items():
        if gastados + coste_previsto() > tope:
            log.warning("Ráfagas: tope de %d créditos alcanzado (%d gastados)",
                        tope, gastados)
            break
        try:
            events, coste = _fetch(sport_key)
        except Exception as exc:  # noqa: BLE001
            log.error("Ráfaga %s: %s", sport_key, exc)
            continue
        consultas += 1
        gastados += coste
        execute("INSERT INTO rafagas_log (sport_key, captured_at, credits, match_ids) "
                "VALUES (%s, %s, %s, %s)", (sport_key, now, coste, match_ids))
        rows = [f for ev, mid in match_events(events, match_meta(match_ids))
                for f in filas(ev, mid, now)]
        escritas += executemany(
            """INSERT INTO odds_rafagas (match_id, bookmaker, selection, price,
                                         book_updated_at, first_seen_at)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id, bookmaker, selection, book_updated_at) DO NOTHING""",
            rows)
    result = {"consultas": consultas, "filas_nuevas": escritas,
              "creditos_mes": gastados, "tope": tope}
    log.info("Ráfagas: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run_once())
