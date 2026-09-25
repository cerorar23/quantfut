"""
Selección "casa blanda contra precio sharp" (publish/picks.py).

Lo que fijan estos tests, en el orden en que el criterio lo decide:
  - el snapshot viejo, sin Pinnacle o sin consenso suficiente no produce nada;
  - Pinnacle apartado del consenso no es referencia;
  - solo casas de la lista blanca, con los nombres unificados entre fuentes;
  - el stake sale del edge ESPERADO al cierre (× persistencia), no del bruto;
  - la cuota mínima publicada deja el edge justo en el umbral;
  - una casa con persistencia medida nula se registra pero no se publica.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from qf.config import settings
from qf.model.devig import devig
from qf.publish import picks as pk

NOW = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)
PIN = {"home": 2.00, "draw": 3.40, "away": 4.00}
NORMAL = {"home": 1.95, "draw": 3.30, "away": 3.90}


def _snap(age_h=1.0, **books):
    base = {"pinnacle": PIN, "marathonbet": NORMAL, "betvictor": NORMAL}
    base.update(books)
    return pk.Snapshot("api_football", NOW - timedelta(hours=age_h), base)


def _fair_home():
    return float(devig([PIN[s] for s in pk.SEL], settings.devig_method)[0])


def test_nombres_unificados_entre_fuentes():
    assert pk.canonical_book("onexbet") == "1xbet"
    assert pk.canonical_book("williamhill") == "william_hill"
    assert pk.canonical_book("sport888") == "888sport"
    assert pk.canonical_book("Bet365") == "bet365"


def test_casa_de_la_lista_por_encima_del_justo_es_oferta():
    ofs = pk.offers(_snap(**{"1xbet": {"home": 2.20, "draw": 3.20, "away": 3.70}}), NOW)
    assert [(o.book, o.selection) for o in ofs] == [("1xbet", "home")]
    o = ofs[0]
    assert o.raw_edge == pytest.approx((2.20 * _fair_home() - 1) * 100)
    assert o.expected_edge == pytest.approx(o.raw_edge * pk.PERSISTENCE["1xbet"])


def test_casa_fuera_de_la_lista_no_cuenta():
    ofs = pk.offers(_snap(coolbet={"home": 2.30, "draw": 3.20, "away": 3.70}), NOW)
    assert ofs == [], "Coolbet paga más, pero los suscriptores no apuestan ahí"


def test_por_debajo_del_umbral_no_es_oferta():
    precio = (1 + (settings.soft_min_edge_pct - 0.5) / 100) / _fair_home()
    ofs = pk.offers(_snap(bet365={"home": precio, "draw": 3.2, "away": 3.7}), NOW)
    assert ofs == []


def test_la_cuota_minima_deja_el_edge_en_el_umbral():
    o = pk.offers(_snap(**{"1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7}}), NOW)[0]
    assert (o.min_price * o.fair_prob - 1) * 100 == pytest.approx(settings.soft_min_edge_pct)
    assert o.min_price < o.price


def test_snapshot_viejo_no_decide():
    viejo = settings.soft_quote_max_age_hours + 1
    s = _snap(age_h=viejo, **{"1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7}})
    assert pk.offers(s, NOW) == []


def test_sin_pinnacle_no_hay_precio_justo():
    s = _snap(**{"1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7}})
    del s.books["pinnacle"]
    assert pk.offers(s, NOW) == []


def test_sin_consenso_suficiente_no_se_puede_verificar_la_referencia():
    s = pk.Snapshot("api_football", NOW, {
        "pinnacle": PIN, "1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7}})
    assert pk.offers(s, NOW) == []


def test_pinnacle_apartado_del_consenso_no_es_referencia():
    raro = {"home": 1.60, "draw": 4.00, "away": 6.00}
    s = pk.Snapshot("api_football", NOW, {
        "pinnacle": raro, "marathonbet": NORMAL, "betvictor": NORMAL,
        "1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7}})
    assert pk.offers(s, NOW) == []


def test_los_exchanges_no_cuentan_como_consenso():
    s = pk.Snapshot("api_football", NOW, {
        "pinnacle": PIN, "betfair": NORMAL, "matchbook": NORMAL,
        "1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7}})
    assert pk.offers(s, NOW) == [], "solo queda 1xbet como casa: consenso insuficiente"


def test_casa_sin_medir_usa_la_persistencia_de_poblacion():
    o = pk.offers(_snap(betano={"home": 2.20, "draw": 3.2, "away": 3.7}), NOW)[0]
    assert o.persistence == pk.UNMEASURED_PERSISTENCE


def _pred():
    return {"match_id": "m1", "prediction_id": "p1", "league_id": "mx.liga_mx",
            "kickoff_utc": NOW + timedelta(hours=30),
            "markets": {"1x2": {"home": 0.61, "draw": 0.22, "away": 0.17}}}


def test_find_candidates_une_fuentes_y_el_modelo_solo_es_diagnostico(monkeypatch):
    af = _snap(**{"1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7},
                  "william_hill": {"home": 2.25, "draw": 3.2, "away": 3.7}})
    toa = pk.Snapshot("the_odds_api", NOW - timedelta(hours=2),
                      {"pinnacle": PIN, "unibet_eu": NORMAL, "betsson": NORMAL,
                       "1xbet": {"home": 2.15, "draw": 3.2, "away": 3.7}})
    monkeypatch.setattr(pk, "_af_snapshot", lambda m, now: af)
    monkeypatch.setattr(pk, "_odds_api_snapshot", lambda m, now: toa)
    cands = pk.find_candidates(_pred(), NOW)
    assert {(c.best_book, c.odds_source) for c in cands} == {
        ("1xbet", "api_football"), ("william_hill", "api_football"),
        ("1xbet", "the_odds_api")}
    assert all(c.model_prob == 0.61 for c in cands)
    assert cands[0].best_book == "1xbet", "ordena por edge ESPERADO, no bruto"
    wh = next(c for c in cands if c.best_book == "william_hill")
    assert wh.raw_edge > cands[0].raw_edge and wh.stake_units == 0.0


# ---------------------------------------------------------------------------
# Goles y hándicap (2026-09-25): mismo criterio, por línea
# ---------------------------------------------------------------------------

OU_PIN = {2.5: {"over": 1.95, "under": 1.95}, 3.5: {"over": 3.20, "under": 1.36}}
OU_OTRA = {2.5: {"over": 1.90, "under": 1.90}, 3.5: {"over": 3.10, "under": 1.33}}


def _snap_lineas(market="totals", pin=OU_PIN, otra=OU_OTRA, **blandas):
    lines = {}
    for ln in pin:
        lines[(market, ln)] = {"pinnacle": pin[ln], "marathonbet": otra[ln],
                               "betvictor": otra[ln]}
    for book, por_linea in blandas.items():
        for ln, q in por_linea.items():
            lines.setdefault((market, ln), {})[book] = q
    return pk.Snapshot("api_football", NOW - timedelta(hours=1), {}, lines)


def test_goles_por_encima_del_justo_en_la_linea_principal_es_oferta():
    ofs = pk.offers(_snap_lineas(bet365={2.5: {"over": 2.10, "under": 1.75}}), NOW)
    assert [(o.book, o.market, o.selection, o.line) for o in ofs] == [
        ("bet365", "totals", "over", 2.5)]
    fair = float(devig([1.95, 1.95], settings.devig_method)[0])
    assert ofs[0].raw_edge == pytest.approx((2.10 * fair - 1) * 100)


def test_solo_la_linea_principal_de_pinnacle():
    """
    The Odds API solo da el cierre de Pinnacle en su línea principal. Una
    oferta en 3,5 no tendría cierre contra el que medirse: no se registra.
    """
    ofs = pk.offers(_snap_lineas(bet365={3.5: {"over": 3.60, "under": 1.30}}), NOW)
    assert ofs == []


def test_la_linea_principal_es_la_mas_equilibrada_de_pinnacle():
    pin = {2.25: {"over": 1.62, "under": 2.40}, 2.75: {"over": 2.02, "under": 1.88}}
    otra = {2.25: {"over": 1.58, "under": 2.35}, 2.75: {"over": 1.97, "under": 1.84}}
    ofs = pk.offers(_snap_lineas(pin=pin, otra=otra,
                                 betano={2.75: {"over": 2.25, "under": 1.70},
                                         2.25: {"over": 1.80, "under": 2.10}}), NOW)
    assert {o.line for o in ofs} == {2.75}


def test_handicap_la_oferta_lleva_la_linea_propia_del_lado():
    pin = {-0.5: {"home": 2.69, "away": 1.50}}
    otra = {-0.5: {"home": 2.60, "away": 1.47}}
    ofs = pk.offers(_snap_lineas("spreads", pin, otra,
                                 betano={-0.5: {"home": 2.62, "away": 1.62}}), NOW)
    assert [(o.book, o.market, o.selection, o.line) for o in ofs] == [
        ("betano", "spreads", "away", 0.5)], "visitante +0,5, no −0,5"


def test_sin_consenso_en_esa_linea_no_hay_oferta():
    s = pk.Snapshot("api_football", NOW, {}, {("totals", 2.5): {
        "pinnacle": OU_PIN[2.5], "bet365": {"over": 2.10, "under": 1.75}}})
    assert pk.offers(s, NOW) == []


def test_pinnacle_apartado_del_consenso_en_la_linea_no_es_referencia():
    raro = {2.5: {"over": 1.60, "under": 2.45}}
    ofs = pk.offers(_snap_lineas(pin=raro, otra={2.5: OU_OTRA[2.5]},
                                 bet365={2.5: {"over": 2.10, "under": 1.75}}), NOW)
    assert ofs == []


def test_group_reparte_1x2_y_lineas_y_empareja_el_handicap():
    t = NOW - timedelta(hours=1)
    rows = [
        {"bookmaker": "Pinnacle", "market": "h2h", "selection": "home", "line": None, "price": 2.0, "ts": t},
        {"bookmaker": "Pinnacle", "market": "totals", "selection": "over", "line": 2.5, "price": 1.95, "ts": t},
        {"bookmaker": "Pinnacle", "market": "spreads", "selection": "home", "line": -0.5, "price": 2.69, "ts": t},
        {"bookmaker": "Pinnacle", "market": "spreads", "selection": "away", "line": 0.5, "price": 1.50, "ts": t},
    ]
    s = pk._group(rows, "api_football", "ts")
    assert s.books == {"pinnacle": {"home": 2.0}}
    assert s.lines[("totals", 2.5)] == {"pinnacle": {"over": 1.95}}
    assert s.lines[("spreads", -0.5)] == {"pinnacle": {"home": 2.69, "away": 1.50}}


def test_find_candidates_de_goles_con_diagnostico_del_modelo(monkeypatch):
    snap = _snap_lineas(bet365={2.5: {"over": 2.10, "under": 1.75}})
    monkeypatch.setattr(pk, "_af_snapshot", lambda m, now: snap)
    monkeypatch.setattr(pk, "_odds_api_snapshot", lambda m, now: None)
    pred = {**_pred(), "markets": {**_pred()["markets"],
                                   "expected_goals": {"home": 1.5, "away": 1.2}}}
    (c,) = pk.find_candidates(pred, NOW)
    assert (c.market, c.selection, c.line) == ("totals", "over", 2.5)
    assert c.label == "totals over 2.5"
    assert 0.4 < c.model_prob < 0.6, "diagnóstico con los goles esperados del modelo"


def test_select_daily_descarta_stake_nulo_y_deja_uno_por_partido(monkeypatch):
    af = _snap(**{"1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7},
                  "william_hill": {"home": 2.25, "draw": 3.2, "away": 3.7}})
    monkeypatch.setattr(pk, "_af_snapshot", lambda m, now: af)
    monkeypatch.setattr(pk, "_odds_api_snapshot", lambda m, now: None)
    picks = pk.select_daily([_pred()], NOW)
    assert len(picks) == 1
    p = picks[0]
    assert p.best_book == "1xbet" and p.stake_units > pk.MIN_STAKE_UNITS
    assert p.min_price is not None and p.odds_as_of == af.as_of
