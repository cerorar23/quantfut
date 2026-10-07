"""Qué picks recibe quién. Una sola consulta para `/v1/picks` (servicio) y
`/app/v1/picks` (clientes): el recorte por tier se hace aquí, en el servidor,
nunca ocultando en el cliente lo que ya se envió."""
from __future__ import annotations

from ..db import query


def picks_for_tiers(tiers: tuple[str, ...], limit: int = 20, offset: int = 0) -> list[dict]:
    return query(
        """SELECT p.pick_id, p.match_id, p.market, p.selection, p.line,
                  p.model_prob, p.advised_price, p.bookmaker, p.edge_pct,
                  p.stake_units, p.tier, p.published_at,
                  p.fair_prob, p.min_price, p.odds_source, p.odds_as_of,
                  m.kickoff_utc, m.league_id,
                  th.canonical_name AS local, ta.canonical_name AS visitante
           FROM picks p
           JOIN matches m USING (match_id)
           JOIN teams th ON th.team_id = m.home_team_id
           JOIN teams ta ON ta.team_id = m.away_team_id
           WHERE m.kickoff_utc > now() AND p.tier = ANY(%s)
           ORDER BY p.edge_pct DESC
           LIMIT %s OFFSET %s""",
        (list(tiers), limit, offset),
    )
