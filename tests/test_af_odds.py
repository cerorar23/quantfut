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
    _, fid, book, market, _, _, updated, mins = rows[0]
    assert (fid, book, market) == (1550966, "bet365", "h2h")
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
