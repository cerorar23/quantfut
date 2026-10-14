"""Competiciones retiradas por decisión del titular, incluso en archivos viejos."""

RETIRED_LEAGUES = frozenset({'cl.primera', 'br.serie_b'})


def require_supported_league(league_id):
    if league_id in RETIRED_LEAGUES:
        raise ValueError('retired_league:' + league_id)
