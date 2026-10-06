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


def _ou(name, lineas):
    """bet 5 con {línea: (over, under)}."""
    vals = []
    for ln, (o, u) in lineas.items():
        vals += [{"value": f"Over {ln}", "odd": o}, {"value": f"Under {ln}", "odd": u}]
    return {"name": name, "bets": [{"id": 5, "name": "Goals Over/Under", "values": vals}]}


def test_goles_de_pinnacle_todas_las_lineas_y_de_blandas_solo_las_de_la_linea():
    rows = parse(_resp([
        _ou("Pinnacle", {1.5: ("1.24", "4.11"), 2.75: ("1.96", "1.89"), 5.5: ("15.0", "1.01")}),
        _ou("Bet365", {1.5: ("1.22", "4.00"), 2.25: ("1.60", "2.30"), 4.5: ("5.00", "1.15")}),
        _ou("Marathonbet", {1.5: ("1.25", "4.20")}),
    ]), "m1", KO)
    tot = {(r[2], r[4], r[8]) for r in rows if r[3] == "totals"}
    assert tot == {("pinnacle", s, ln) for ln in (1.5, 2.75, 5.5) for s in ("over", "under")} | \
                  {("bet365", s, ln) for ln in (1.5, 4.5) for s in ("over", "under")}


def test_goles_solo_pares_completos_y_cuotas_validas():
    bk = {"name": "Pinnacle", "bets": [{"id": 5, "values": [
        {"value": "Over 2.5", "odd": "1.90"},                       # sin under
        {"value": "Over 3.5", "odd": "2.90"}, {"value": "Under 3.5", "odd": "1.00"},
        {"value": "Over 1.5", "odd": "1.25"}, {"value": "Under 1.5", "odd": "4.10"},
        {"value": "Más de 0.5", "odd": "1.05"},                     # formato raro
    ]}]}
    tot = [(r[4], r[8]) for r in parse(_resp([bk]), "m1", KO) if r[3] == "totals"]
    assert sorted(tot) == [("over", 1.5), ("under", 1.5)]
