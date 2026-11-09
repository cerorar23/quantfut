"""Competiciones retiradas por decisión del titular, incluso en archivos viejos."""

# Chile y Brasil B (13-oct-2026): borradas por completo (db/063).
# Ligue 2 y Superliga danesa (25-oct-2026): fuera de los motores porque PropLine no las cotiza;
# su historial sellado se conserva (db/086), pero ningún archivo vuelve a importarlas.
# Serie B, LaLiga 2, Allsvenskan y Super League suiza (db/088) se retiraron el 25-oct y el titular las
# reactivó el 8-nov-2026 (db/105): PropLine ya las cotiza y SofaScore trae xG de todas.
RETIRED_LEAGUES = frozenset({'cl.primera', 'br.serie_b', 'fr.ligue_2', 'dk.superliga'})


def require_supported_league(league_id):
    if league_id in RETIRED_LEAGUES:
        raise ValueError('retired_league:' + league_id)
