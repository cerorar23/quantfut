"""
Parseo de cuotas de API-Football. Lo que fijan: la marca de tiempo es la del
proveedor (no la de captura), solo entra el 1X2 completo, y las casas quedan
con una clave estable.
"""
from __future__ import annotations

from datetime import datetime, timezone

from qf.ingest.af_odds import bookmaker_key, parse

KO = datetime(2026, 9, 26, 1, 0, tzinfo=timezone.utc)


def _resp(bookmakers, update="2026-09-23T20:00:00+00:00"):
    return [{"fixture": {"id": 1550966}, "update": update, "bookmakers": bookmakers}]


def _bk(name, home="2.10", draw="3.30", away="3.60", bet_id=1):
    return {"name": name, "bets": [{"id": bet_id, "name": "Match Winner", "values": [
        {"value": "Home", "odd": home}, {"value": "Draw", "odd": draw},
        {"value": "Away", "odd": away}]}]}


def test_claves_de_casa_estables():
    assert bookmaker_key("William Hill") == "william_hill"
    assert bookmaker_key("1xBet") == "1xbet"
    assert bookmaker_key("Bet365") == "bet365"


def test_la_hora_es_la_del_proveedor_y_los_minutos_salen_de_ella():
    rows = parse(_resp([_bk("Bet365")]), "m1", KO)
    assert len(rows) == 3
    _, fid, book, market, _, _, updated, mins, line = rows[0]
    assert (fid, book, market, line) == (1550966, "bet365", "h2h", None)
    assert updated == datetime(2026, 9, 23, 20, tzinfo=timezone.utc)
    assert mins == 53 * 60


def test_solo_1x2_completo_y_valido():
    rows = parse(_resp([
        _bk("Pinnacle"),
        _bk("Betano", draw="n/a"),
        _bk("1xBet", away="1.00"),
        _bk("Bet365", bet_id=5),
        {"name": None, "bets": []},
    ]), "m1", KO)
    assert {r[2] for r in rows} == {"pinnacle"}


def test_respuesta_vacia_no_produce_filas():
    assert parse([], "m1", KO) == []


# ---------------------------------------------------------------------------
# Goles y hándicap (2026-09-25). Formato copiado de una respuesta real de
# Cruz Azul–Toluca: `bet` 5 "Goals Over/Under" y 4 "Asian Handicap".
# ---------------------------------------------------------------------------

def _bet(bet_id, name, values):
    return {"id": bet_id, "name": name,
            "values": [{"value": v, "odd": o} for v, o in values]}


def _por(rows):
    return {(r[3], r[4], r[8]): r[5] for r in rows}


def test_goles_por_linea_con_el_par_completo():
    rows = parse(_resp([{"name": "Pinnacle", "bets": [_bet(5, "Goals Over/Under", [
        ("Over 2.5", "1.65"), ("Under 2.5", "2.28"),
        ("Over 2.75", "1.80"), ("Under 2.75", "2.05"),
        ("Over 3.5", "2.52")])]}]), "m1", KO)
    assert _por(rows) == {
        ("totals", "over", 2.5): 1.65, ("totals", "under", 2.5): 2.28,
        ("totals", "over", 2.75): 1.80, ("totals", "under", 2.75): 2.05,
    }, "Over 3.5 sin su Under no se puede de-vigar: fuera"


def test_el_handicap_del_visitante_lleva_su_propia_linea():
    """
    API-Football etiqueta las dos patas con la línea del LOCAL: 'Home -1' a
    4,39 y 'Away -1' a 1,23 son local −1 y visitante +1 (el favorito a 1,23
    solo tiene sentido con +1). Guardar 'Away -1' como −1 invertiría cada
    hándicap y el cierre de The Odds API (visitante +1) nunca casaría.
    """
    rows = parse(_resp([{"name": "Pinnacle", "bets": [_bet(4, "Asian Handicap", [
        ("Home -1", "4.39"), ("Away -1", "1.23"),
        ("Home +0", "1.93"), ("Away +0", "1.94"),
        ("Home +0.25", "1.64")])]}]), "m1", KO)
    assert _por(rows) == {
        ("spreads", "home", -1.0): 4.39, ("spreads", "away", 1.0): 1.23,
        ("spreads", "home", 0.0): 1.93, ("spreads", "away", 0.0): 1.94,
    }


def test_solo_se_capturan_1x2_goles_y_handicap_del_partido():
    rows = parse(_resp([{"name": "Bet365", "bets": [
        _bet(6, "Goals Over/Under First Half", [("Over 1.5", "2.38"), ("Under 1.5", "1.53")]),
        _bet(19, "Asian Handicap First Half", [("Home -0.5", "3.00"), ("Away -0.5", "1.38")]),
        _bet(57, "Home Corners Over/Under", [("Over 5.5", "1.91"), ("Under 5.5", "1.80")]),
    ]}]), "m1", KO)
    assert rows == []
