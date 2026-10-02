"""Auditoría de cobertura 1X2 point-in-time; nunca modifica cuotas ni picks.

`first_seen` es la primera terna completa que QuantFut observó, NO la hora
real de apertura del mercado. API-Football separa cuándo se publicó el precio
(`provider_updated_at`) de cuándo llegó a nuestro sistema (`fetched_at`).
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median

from ..db import query


def summarize(rows: list[dict], fixture_counts: dict[str, int]) -> list[dict]:
    """Una observación completa por partido, fuente y casa, la más temprana."""
    first: dict[tuple[str, str, str], dict] = {}
    for row in rows:
        observed = row["observed_at"]
        kickoff = row["kickoff_utc"]
        provider_at = row["provider_at"]
        if observed >= kickoff or (provider_at is not None and provider_at > observed):
            continue
        key = (row["match_id"], row["source"], row["bookmaker"])
        if key not in first or observed < first[key]["observed_at"]:
            first[key] = row

    grouped: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for row in first.values():
        grouped[(row["league_id"], row["source"], row["bookmaker"])].append(row)

    output = []
    for (league, source, bookmaker), group in sorted(grouped.items()):
        lead = [(r["kickoff_utc"] - r["observed_at"]).total_seconds() / 3600
                for r in group]
        age = [(r["observed_at"] - r["provider_at"]).total_seconds() / 3600
               for r in group if r["provider_at"] is not None]
        denominator = fixture_counts.get(league, 0)
        output.append({
            "league_id": league,
            "source": source,
            "bookmaker": bookmaker,
            "matches_with_complete_1x2": len(group),
            "fixtures": denominator,
            "coverage_pct": round(100 * len(group) / denominator, 1)
            if denominator else None,
            "first_seen_lead_hours_median": round(median(lead), 2),
            "first_seen_at_least_72h": sum(hours >= 72 for hours in lead),
            "provider_age_at_first_seen_hours_median": round(median(age), 2)
            if age else None,
            "first_seen_utc_min": min(r["observed_at"] for r in group).isoformat(),
        })
    return output


def run(days: int = 30, now: datetime | None = None) -> dict:
    """Lee calendario y ternas completas desde Postgres, sin coste de API."""
    if days <= 0:
        raise ValueError("days debe ser positivo")
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    end = now + timedelta(days=1)
    fixture_counts = {
        row["league_id"]: row["fixtures"] for row in query(
            """SELECT league_id, count(*) AS fixtures FROM matches
               WHERE kickoff_utc >= %s AND kickoff_utc < %s
               GROUP BY league_id""", (start, end))
    }
    rows = query(
        """WITH complete AS (
             SELECT m.match_id, m.league_id, m.kickoff_utc,
                    s.source, s.bookmaker, s.captured_at AS observed_at,
                    NULL::timestamptz AS provider_at
             FROM odds_snapshots s JOIN matches m USING (match_id)
             WHERE s.market = 'h2h' AND s.captured_at < m.kickoff_utc
               AND m.kickoff_utc >= %s AND m.kickoff_utc < %s
             GROUP BY m.match_id, m.league_id, m.kickoff_utc,
                      s.source, s.bookmaker, s.captured_at
             HAVING count(DISTINCT s.selection) = 3 AND min(s.price) > 1
             UNION ALL
             SELECT m.match_id, m.league_id, m.kickoff_utc,
                    'api_football' AS source, s.bookmaker,
                    min(s.fetched_at) AS observed_at,
                    s.provider_updated_at AS provider_at
             FROM af_odds_snapshots s JOIN matches m USING (match_id)
             WHERE s.market = 'h2h' AND s.fetched_at < m.kickoff_utc
               AND m.kickoff_utc >= %s AND m.kickoff_utc < %s
             GROUP BY m.match_id, m.league_id, m.kickoff_utc,
                      s.bookmaker, s.provider_updated_at
             HAVING count(DISTINCT s.selection) = 3 AND min(s.price) > 1
           ) SELECT * FROM complete""", (start, end, start, end)
    )
    return {"period_start_utc": start.isoformat(),
            "period_end_utc": end.isoformat(),
            "meaning": "first_seen es primera terna observada, no apertura real",
            "by_league_source_book": summarize(rows, fixture_counts)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    print(json.dumps(run(args.days), ensure_ascii=False, indent=2))
