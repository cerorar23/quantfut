"""
Cierre de partidos terminados. MÓDULO BLOQUEANTE DE LA FASE 1.

Era el hueco que hacía que toda la infraestructura de credibilidad no llegara
a funcionar: nada marcaba los partidos nuevos como 'finished' ni escribía sus
goles, así que settle_pending() nunca disparaba, no había CLV y v_track_record
quedaba vacía para siempre.

Dos detalles que importan:

1. `result_recorded_at` se escribe SIEMPRE. Es lo que te permite demostrar que
   el resultado se conoció después del pick, y lo que usa check_leakage().

2. Los partidos aplazados se marcan, no se borran. Un pick sobre un partido
   aplazado se liquida como 'void', no como pérdida.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from ..db import execute, query
from . import api_football as af

log = logging.getLogger(__name__)

FINISHED = {"FT", "AET", "PEN"}
VOIDED = {"PST", "CANC", "ABD", "AWD", "WO", "SUSP"}


def _stats_map(stats_block: list) -> dict[int, dict]:
    """Convierte el bloque de estadísticas de API-Football a {team_id: {...}}."""
    out: dict[int, dict] = {}
    for team_stats in stats_block or []:
        tid = team_stats["team"]["id"]
        d = {}
        for item in team_stats.get("statistics", []):
            d[item["type"]] = item["value"]
        out[tid] = d
    return out


def _num(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = v.rstrip("%")
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None


def close_recent(hours_back: int = 72, with_stats: bool = True) -> dict:
    """
    Cierra los partidos cuyo kickoff ya pasó y que siguen marcados como
    scheduled. Se ejecuta varias veces al día.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    pending = query(
        """SELECT match_id, league_id, kickoff_utc,
                  external_ids ->> 'api_football' AS af_id
           FROM matches
           WHERE status IN ('scheduled', 'live', 'postponed')
             AND kickoff_utc < now() - interval '105 minutes'
             AND kickoff_utc > %s
             AND external_ids ? 'api_football'""",
        (since,),
    )
    if not pending:
        af.record_health("results", 0, True, {"note": "nada pendiente"})
        return {"closed": 0, "voided": 0, "still_open": 0}

    by_id = {r["af_id"]: r for r in pending}
    ids = list(by_id.keys())
    closed = voided = still_open = 0

    # API-Football acepta hasta 20 ids por llamada
    for chunk_start in range(0, len(ids), 20):
        chunk = ids[chunk_start:chunk_start + 20]
        params = {"ids": "-".join(chunk), "timezone": "UTC"}
        try:
            resp, meta = af.get("fixtures", params)
            af.check_quota(meta)
        except Exception as exc:  # noqa: BLE001
            log.error("Fallo al consultar resultados: %s", exc)
            continue

        for fx in resp:
            af_id = str(fx["fixture"]["id"])
            row = by_id.get(af_id)
            if not row:
                continue
            short = fx["fixture"]["status"]["short"]

            if short in VOIDED:
                execute("UPDATE matches SET status='postponed' WHERE match_id=%s",
                        (row["match_id"],))
                _void_picks(row["match_id"])
                voided += 1
                continue

            if short not in FINISHED:
                still_open += 1
                continue

            goals = fx.get("goals", {})
            score = fx.get("score", {})
            ht = score.get("halftime", {}) or {}

            stats = {}
            if with_stats:
                try:
                    sresp, smeta = af.get("fixtures/statistics", {"fixture": af_id})
                    stats = _stats_map(sresp)
                except Exception:  # noqa: BLE001
                    stats = {}

            home_af = fx["teams"]["home"]["id"]
            away_af = fx["teams"]["away"]["id"]
            hs, as_ = stats.get(home_af, {}), stats.get(away_af, {})

            execute(
                """UPDATE matches SET
                     status = 'finished',
                     home_goals = %s, away_goals = %s,
                     home_goals_ht = %s, away_goals_ht = %s,
                     home_shots = COALESCE(%s, home_shots),
                     away_shots = COALESCE(%s, away_shots),
                     home_shots_target = COALESCE(%s, home_shots_target),
                     away_shots_target = COALESCE(%s, away_shots_target),
                     home_corners = COALESCE(%s, home_corners),
                     away_corners = COALESCE(%s, away_corners),
                     result_recorded_at = now()
                   WHERE match_id = %s""",
                (_num(goals.get("home")), _num(goals.get("away")),
                 _num(ht.get("home")), _num(ht.get("away")),
                 _num(hs.get("Total Shots")), _num(as_.get("Total Shots")),
                 _num(hs.get("Shots on Goal")), _num(as_.get("Shots on Goal")),
                 _num(hs.get("Corner Kicks")), _num(as_.get("Corner Kicks")),
                 row["match_id"]),
            )
            closed += 1

    # Encadenar la liquidación: cerrar un partido sin liquidar sus picks deja
    # el track record desactualizado hasta el siguiente cron.
    settled = {}
    if closed:
        from ..eval.clv import settle_pending
        settled = settle_pending()

    result = {"closed": closed, "voided": voided, "still_open": still_open,
              "settled": settled}
    af.record_health("results", closed, True, result)
    log.info("Cierre de partidos: %s", result)
    return result


def _void_picks(match_id: str) -> None:
    """Un pick sobre un partido aplazado se anula, no se cuenta como pérdida."""
    execute(
        """INSERT INTO pick_results (pick_id, outcome, profit_units)
           SELECT pick_id, 'void', 0
           FROM picks WHERE match_id = %s
           ON CONFLICT (pick_id) DO NOTHING""",
        (match_id,),
    )


def find_orphans(days: int = 14) -> list[dict]:
    """
    Partidos que llevan demasiado tiempo abiertos. Si esta lista crece, algo
    está roto en la ingesta y no te vas a enterar por ningún error.
    """
    return query(
        """SELECT match_id, league_id, kickoff_utc, status
           FROM matches
           WHERE status IN ('scheduled', 'live')
             AND kickoff_utc < now() - interval '6 hours'
             AND kickoff_utc > now() - make_interval(days => %s)
           ORDER BY kickoff_utc""",
        (days,),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(close_recent())
    orphans = find_orphans()
    if orphans:
        print(f"\nATENCIÓN: {len(orphans)} partidos huérfanos (pasaron hace "
              f">6h y siguen abiertos):")
        for o in orphans[:10]:
            print("  ", o["match_id"], o["kickoff_utc"])
