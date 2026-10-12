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

import json
import logging
from datetime import datetime, timedelta, timezone

from ..db import execute, query
from . import api_football as af
from .estadisticas import arbitro, normalizar_estadisticas
from .estadisticas_jugador import capturar as capturar_jugadores

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


def close_recent(hours_back: int = 72, with_stats: bool = True,
                 leagues: list[str] | None = None) -> dict:
    """
    Cierra los partidos cuyo kickoff ya pasó y que siguen marcados como
    scheduled. Se ejecuta varias veces al día.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    pending = query(
        """SELECT m.match_id, m.league_id, m.kickoff_utc,
                  m.external_ids ->> 'api_football' AS af_id,
                  -- Jugadores solo con modelo y captura completa (db/052).
                  (l.model_enabled AND l.captura_completa) AS captura_jugadores,
                  th.af_team_id AS home_af, ta.af_team_id AS away_af
           FROM matches m
           JOIN leagues l ON l.league_id = m.league_id
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE m.status IN ('scheduled', 'live', 'postponed')
             AND m.kickoff_utc < now() - interval '105 minutes'
             AND m.kickoff_utc > %s
             AND m.external_ids ? 'api_football'
             AND (%s::text[] IS NULL OR m.league_id = ANY(%s))""",
        (since, leagues, leagues),
    )
    if not pending:
        af.record_health("results", 0, True, {"note": "nada pendiente"})
        return {"closed": 0, "voided": 0, "still_open": 0}

    by_id = {r["af_id"]: r for r in pending}
    ids = list(by_id.keys())
    closed = voided = still_open = jugadores = 0

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

            home_af = fx["teams"]["home"]["id"]
            away_af = fx["teams"]["away"]["id"]

            stats, completas = {}, None
            if with_stats:
                try:
                    sresp, smeta = af.get("fixtures/statistics", {"fixture": af_id})
                    stats = _stats_map(sresp)
                    # La respuesta ENTERA para las fichas de la web (posesión,
                    # faltas, tarjetas…): la misma petición, 0 llamadas más.
                    completas = normalizar_estadisticas(sresp, home_af, away_af)
                except Exception:  # noqa: BLE001
                    stats = {}

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
                     home_yellow = COALESCE(%s, home_yellow),
                     away_yellow = COALESCE(%s, away_yellow),
                     home_red = COALESCE(%s, home_red),
                     away_red = COALESCE(%s, away_red),
                     referee = COALESCE(%s, referee),
                     stats = COALESCE(%s::jsonb, stats),
                     result_recorded_at = now()
                   WHERE match_id = %s""",
                (_num(goals.get("home")), _num(goals.get("away")),
                 _num(ht.get("home")), _num(ht.get("away")),
                 _num(hs.get("Total Shots")), _num(as_.get("Total Shots")),
                 _num(hs.get("Shots on Goal")), _num(as_.get("Shots on Goal")),
                 _num(hs.get("Corner Kicks")), _num(as_.get("Corner Kicks")),
                 # El proveedor manda null por cero tarjetas: con estadísticas, es 0.
                 (_num(hs.get("Yellow Cards")) or 0) if hs else None,
                 (_num(as_.get("Yellow Cards")) or 0) if as_ else None,
                 (_num(hs.get("Red Cards")) or 0) if hs else None,
                 (_num(as_.get("Red Cards")) or 0) if as_ else None,
                 arbitro(fx["fixture"].get("referee")),
                 json.dumps(completas) if completas and any(completas.values()) else None,
                 row["match_id"]),
            )
            closed += 1
            # Fuerza por jugador (db/035): una petición más, solo en ligas con
            # modelo y captura completa. Un fallo aquí no debe dejar el
            # partido sin cerrar.
            if row["captura_jugadores"]:
                try:
                    capturar_jugadores(row["match_id"], int(af_id),
                                       row["home_af"], row["away_af"])
                    jugadores += 1
                except Exception as exc:  # noqa: BLE001
                    log.warning("Estadísticas por jugador de %s: %s",
                                row["match_id"], exc)

    # Encadenar la liquidación: cerrar un partido sin liquidar sus picks deja
    # el track record desactualizado hasta el siguiente cron.
    settled = {}
    if closed:
        from ..eval.clv import settle_pending
        settled = settle_pending()

    result = {"closed": closed, "voided": voided, "still_open": still_open,
              "jugadores": jugadores, "settled": settled}
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
