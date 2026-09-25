"""
Captura de cuotas 1X2 de API-Football: la fuente de las casas donde apuestan
los suscriptores (Bet365, Betano, 1xBet, William Hill), con Pinnacle en la
misma respuesta.

Consultado el 2026-09-23 (`/odds/bookmakers` y `/odds` por competición): de 33
casas del catálogo solo 9 cotizan nuestras competiciones, y esas 9 aparecen en
12 de 13. Betway, 888sport, Betcris y Sportingbet están en el catálogo con cero
partidos.

LÍMITES DEL PROVEEDOR, que condicionan cómo se usa
--------------------------------------------------
- Actualiza cada competición de golpe cada varias horas (medido: 2 h en MLS,
  19 h en Liga MX). No sirve como cierre: el cierre sigue saliendo de The Odds
  API. Sirve para DECIDIR con precios de 24-72 h antes.
- Solo guarda 7 días. Lo que no se capture a tiempo se pierde.
- Una sola marca `update` por partido para todas las casas: la casa blanda y
  Pinnacle de la misma respuesta tienen la misma antigüedad, que es lo que
  permite compararlas. Nunca comparar una casa de aquí con el Pinnacle de The
  Odds API: edades distintas fabrican ventajas falsas.
- No se sabe si su Bet365 o su Betano son el precio de la web mexicana o el
  internacional.

Se guarda en `af_odds_snapshots`, no en `odds_snapshots` (ver db/016).
Una petición por partido dentro del horizonte.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from ..db import executemany, query
from . import api_football as af

log = logging.getLogger(__name__)

HORIZON = timedelta(hours=72)
MATCH_WINNER = 1
SELECTIONS = {"Home": "home", "Draw": "draw", "Away": "away"}


def bookmaker_key(name: str) -> str:
    """'William Hill' -> 'william_hill', '1xBet' -> '1xbet'."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def parse(response: list[dict], match_id: str, kickoff: datetime) -> list[tuple]:
    """
    Filas para `af_odds_snapshots`. Solo casas con el 1X2 completo y cuotas
    válidas: un grupo incompleto no se puede de-vigar ni comparar.
    """
    rows = []
    for item in response:
        updated = datetime.fromisoformat(item["update"])
        mins = int((kickoff - updated).total_seconds() // 60)
        fid = int(item["fixture"]["id"])
        for bk in item.get("bookmakers", []):
            if not bk.get("name"):
                continue
            for bet in bk.get("bets", []):
                if bet.get("id") != MATCH_WINNER:
                    continue
                q = {}
                for v in bet.get("values", []):
                    sel = SELECTIONS.get(v.get("value"))
                    try:
                        price = float(v.get("odd"))
                    except (TypeError, ValueError):
                        continue
                    if sel and price > 1.0:
                        q[sel] = price
                if set(q) != set(SELECTIONS.values()):
                    continue
                book = bookmaker_key(bk["name"])
                rows += [(match_id, fid, book, "h2h", s, p, updated, mins)
                         for s, p in q.items()]
    return rows


def _pending(now: datetime) -> list[dict]:
    return query(
        """SELECT m.match_id, m.kickoff_utc,
                  (m.external_ids ->> 'api_football')::int AS fixture_id
           FROM matches m
           JOIN leagues l ON l.league_id = m.league_id
           WHERE m.status = 'scheduled' AND l.active
             AND m.external_ids ? 'api_football'
             AND m.kickoff_utc BETWEEN %s AND %s
           ORDER BY m.kickoff_utc""",
        (now, now + HORIZON),
    )


def run_once() -> dict:
    now = datetime.now(timezone.utc)
    pending = _pending(now)
    calls = rows_new = with_odds = 0
    meta: dict = {}
    for m in pending:
        try:
            resp, meta = af.get("odds", {"fixture": m["fixture_id"], "bet": MATCH_WINNER})
            calls += 1
        except af.PlanError:
            raise
        except Exception as exc:  # noqa: BLE001
            log.error("Cuotas de %s: %s", m["match_id"], exc)
            continue
        rows = parse(resp, m["match_id"], m["kickoff_utc"])
        if not rows:
            continue
        with_odds += 1
        rows_new += executemany(
            """INSERT INTO af_odds_snapshots
                 (match_id, af_fixture_id, bookmaker, market, selection, price,
                  provider_updated_at, mins_to_kickoff)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (match_id, bookmaker, market, selection,
                            provider_updated_at) DO NOTHING""",
            rows,
        )
    if meta:
        af.check_quota(meta)
    result = {"fixtures": len(pending), "calls": calls, "with_odds": with_odds,
              "rows_new": rows_new, "quota_remaining": meta.get("quota_remaining")}
    af.record_health("af_odds", rows_new, calls > 0 or not pending, result)
    log.info("Cuotas API-Football: %s", result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(run_once())
