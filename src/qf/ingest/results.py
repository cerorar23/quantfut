"""
Cierre de partidos terminados. MÓDULO BLOQUEANTE DE LA FASE 1.

Era el hueco que hacía que toda la infraestructura de credibilidad no llegara
a funcionar: nada marcaba los partidos nuevos como 'finished' ni escribía sus
goles, así que settle_pending() nunca disparaba, no había CLV y v_track_record
quedaba vacía para siempre.

Desde el 25-oct-2026 los resultados salen del archivo de PropLine
(`propline_partidos.resultados`); este módulo conserva el punto de entrada
`close_recent`, la anulación de picks de partidos aplazados y la lista de
huérfanos.

Dos detalles que importan:

1. `result_recorded_at` se escribe SIEMPRE. Es lo que te permite demostrar que
   el resultado se conoció después del pick, y lo que usa check_leakage().

2. Los partidos aplazados se marcan, no se borran. Un pick sobre un partido
   aplazado se liquida como 'void', no como pérdida.
"""
from __future__ import annotations

import logging

from ..db import execute, query

log = logging.getLogger(__name__)


def close_recent(hours_back: int = 72) -> dict:
    """
    Cierra los partidos cuyo kickoff ya pasó y que siguen marcados como
    scheduled. Se ejecuta varias veces al día.
    """
    from .propline_partidos import resultados
    return resultados(hours_back=hours_back)


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
        """SELECT m.match_id, m.league_id, m.kickoff_utc, m.status
           FROM matches m JOIN leagues l ON l.league_id = m.league_id AND l.active
           WHERE m.status IN ('scheduled', 'live')
             AND m.kickoff_utc < now() - interval '6 hours'
             AND m.kickoff_utc > now() - make_interval(days => %s)
           ORDER BY m.kickoff_utc""",
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
