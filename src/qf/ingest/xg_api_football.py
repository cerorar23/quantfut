"""xG de API-Football: primera pareja válida, con fecha real de recepción.

Se aprovecha la respuesta del cierre sin llamadas adicionales. Un job diario
reconsulta terminados sin xG durante 35 días, con tope y reserva de cuota.
No revisa ni reemplaza valores ya capturados o del histórico anterior.
"""
from __future__ import annotations

import argparse
import json
import logging
import math

from ..db import conn, execute, query
from . import api_football as af
from .salud import record_health

log = logging.getLogger(__name__)
LOCK_ID = 61012026


def extract_xg(response: list, home_id: int, away_id: int):
    """Exige ambos equipos y valores finitos no negativos; null no es cero."""
    if home_id is None or away_id is None or home_id == away_id:
        return None
    values = {}
    for block in response or []:
        team_id = block.get("team", {}).get("id")
        if team_id not in (home_id, away_id):
            continue
        if team_id in values:
            return None
        raw = [s.get("value") for s in block.get("statistics", [])
               if s.get("type") == "expected_goals"]
        if len(raw) != 1 or isinstance(raw[0], bool):
            return None
        try:
            value = float(raw[0])
        except (ValueError, TypeError):
            return None
        if not math.isfinite(value) or value < 0:
            return None
        values[team_id] = value
    if len(values) != 2:
        return None
    return values[home_id], values[away_id]


def record_capture(match_id: str, response: list, home_id: int, away_id: int) -> int:
    """Congela la primera observación; el timestamp lo pone Postgres ahora."""
    pair = extract_xg(response, home_id, away_id)
    execute("UPDATE matches SET xg_api_checked_at = now() WHERE match_id = %s",
            (match_id,))
    if pair is None:
        return 0
    return execute(
        """UPDATE matches SET home_xg = %s, away_xg = %s,
                  xg_recorded_at = now(), xg_source = 'api_football'
           WHERE match_id = %s AND status = 'finished'
             AND home_xg IS NULL AND away_xg IS NULL""",
        (*pair, match_id),
    )


def quota_available(meta: dict) -> bool:
    """No consume la reserva del 15% del plan; desconocida => no reconsulta."""
    try:
        remaining = int(meta["quota_remaining"])
        limit = int(meta["quota_limit"])
        return limit > 0 and remaining > math.ceil(limit * 0.15)
    except (KeyError, TypeError, ValueError):
        return False


def _run(days: int, limit: int) -> dict:
    rows = query(
        """SELECT m.match_id, m.external_ids ->> 'api_football' AS af_id,
                  th.af_team_id AS home_af, ta.af_team_id AS away_af
           FROM matches m JOIN leagues l USING (league_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE m.status = 'finished' AND l.model_enabled
             AND m.home_xg IS NULL AND m.away_xg IS NULL
             AND m.external_ids ? 'api_football'
             AND th.af_team_id IS NOT NULL AND ta.af_team_id IS NOT NULL
             AND m.kickoff_utc > now() - make_interval(days => %s)
             AND (m.xg_api_checked_at IS NULL OR
                  m.xg_api_checked_at < now() - interval '20 hours')
           ORDER BY m.xg_api_checked_at NULLS FIRST, m.kickoff_utc DESC
           LIMIT %s""", (days, limit))
    report = {"candidates": len(rows), "requests": 0, "captured": 0,
              "missing": 0, "errors": 0, "quota_stopped": False}
    if not rows:
        return report
    # Status no lee datos personales ni envía alertas; solo presupuesto.
    _, meta = af.get("status")
    if not quota_available(meta):
        report["quota_stopped"] = True
        return report
    for row in rows:
        if not quota_available(meta):
            report["quota_stopped"] = True
            break
        # También se espacian los fallos de red/proveedor.
        execute("UPDATE matches SET xg_api_checked_at = now() WHERE match_id = %s",
                (row["match_id"],))
        report["requests"] += 1
        try:
            response, meta = af.get("fixtures/statistics", {"fixture": row["af_id"]})
        except Exception:  # noqa: BLE001
            report["errors"] += 1
            log.warning("Consulta xG fallida: %s", row["match_id"], exc_info=True)
            # Sin presupuesto actualizado tras un fallo, no seguir consumiendo.
            break
        captured = record_capture(row["match_id"], response,
                                  row["home_af"], row["away_af"])
        report["captured"] += captured
        report["missing"] += int(not captured)
    return report


def run(days: int = 35, limit: int = 100) -> dict:
    if days < 1 or not 1 <= limit <= 500:
        raise ValueError("days debe ser positivo y limit estar entre 1 y 500")
    with conn() as connection:
        locked = connection.execute("SELECT pg_try_advisory_lock(%s) AS locked",
                                    (LOCK_ID,)).fetchone()["locked"]
        if not locked:
            return {"skipped": "otra captura xG está en marcha"}
        try:
            report = _run(days, limit)
            record_health("xg_api_football", report["captured"],
                             report["errors"] == 0 and not report["quota_stopped"], report)
            return report
        finally:
            connection.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=35)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    result = run(args.days, args.limit)
    print(json.dumps(result))
    if result.get("errors") or result.get("quota_stopped"):
        raise SystemExit(1)
