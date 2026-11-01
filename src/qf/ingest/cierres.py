"""Inserción del cierre 1X2 de Pinnacle de un partido en `odds_snapshots` (lo usa `cierres_odds_api`)."""
from __future__ import annotations


def insertar_cierre(c, match_id: str, kickoff, precios: dict, captured_at=None,
                    book_updated_at=None, source: str = "football_data") -> int:
    """
    Inserta la terna 1X2 de cierre de Pinnacle de un partido, salvo que ya tenga un cierre de
    Pinnacle de cualquier fuente: la comprobación va DENTRO del INSERT porque `odds_snapshots`
    no admite DELETE y dos ejecuciones no deben pisarse. Devuelve las filas insertadas (0 o 3).
    """
    captured_at = captured_at or kickoff
    mins = max(0, int((kickoff - captured_at).total_seconds() // 60))
    return c.execute(
        """INSERT INTO odds_snapshots (match_id, bookmaker, market, selection, line, price, captured_at,
                                       mins_to_kickoff, window_tag, source, book_updated_at)
           SELECT %s, 'pinnacle', 'h2h', v.sel, NULL, v.price, %s, %s, 'close', %s, %s
           FROM (VALUES ('home', %s::real), ('draw', %s::real), ('away', %s::real)) AS v(sel, price)
           WHERE NOT EXISTS (SELECT 1 FROM odds_snapshots o WHERE o.match_id = %s
                             AND o.bookmaker = 'pinnacle' AND o.market = 'h2h' AND o.window_tag = 'close')""",
        (match_id, captured_at, mins, source, book_updated_at, precios["home"], precios["draw"],
         precios["away"], match_id)).rowcount
