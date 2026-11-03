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
    return pk.Snapshot("the_odds_api", NOW - timedelta(hours=age_h), base)


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
    ofs = pk.offers(_snap(nordicbet={"home": 2.30, "draw": 3.20, "away": 3.70}), NOW)
    assert ofs == [], "NordicBet paga más, pero los suscriptores no apuestan ahí"


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


def test_find_candidates_el_modelo_solo_es_diagnostico(monkeypatch):
    toa = pk.Snapshot("the_odds_api", NOW - timedelta(hours=2),
                      {"pinnacle": PIN, "unibet_eu": NORMAL, "betsson": NORMAL,
                       "1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7},
                       "william_hill": {"home": 2.25, "draw": 3.2, "away": 3.7}})
    monkeypatch.setattr(pk, "persistencias", lambda: dict(pk.PERSISTENCE))
    monkeypatch.setattr(pk, "_odds_api_snapshot", lambda m, now: toa)
    cands = pk.find_candidates(_pred(), NOW)
    assert {(c.best_book, c.odds_source) for c in cands} == {
        ("1xbet", "the_odds_api"), ("william_hill", "the_odds_api")}
    assert all(c.model_prob == 0.61 for c in cands)
    assert cands[0].best_book == "1xbet", "ordena por edge ESPERADO, no bruto"
    wh = next(c for c in cands if c.best_book == "william_hill")
    assert wh.raw_edge > cands[0].raw_edge and wh.stake_units == 0.0


def test_select_daily_descarta_stake_nulo_y_deja_uno_por_partido(monkeypatch):
    snap = _snap(**{"1xbet": {"home": 2.20, "draw": 3.2, "away": 3.7},
                    "william_hill": {"home": 2.25, "draw": 3.2, "away": 3.7}})
    monkeypatch.setattr(pk, "persistencias", lambda: dict(pk.PERSISTENCE))
    monkeypatch.setattr(pk, "_odds_api_snapshot", lambda m, now: snap)
    picks = pk.select_daily([_pred()], NOW)
    assert len(picks) == 1
    p = picks[0]
    assert p.best_book == "1xbet" and p.stake_units > pk.MIN_STAKE_UNITS
    assert p.min_price is not None and p.odds_as_of == snap.as_of


# ---------------------------------------------------------------------------
# Persistencia recalibrada con la sombra (regla fijada 2026-09-28)
# ---------------------------------------------------------------------------

def test_sin_muestra_la_persistencia_es_la_previa():
    assert pk.mezclar(0.13, 0, None, None) == 0.13
    assert pk.mezclar(0.13, 5, 3.0, 0.0) == 0.13     # edge nulo: no se divide


def test_pocos_partidos_casi_no_la_mueven_y_muchos_si():
    # Bet365: previa 0,13; la sombra mide EV 1,0 sobre edge 3,0 -> 0,333.
    poco = pk.mezclar(0.13, 5, 1.0, 3.0)
    mucho = pk.mezclar(0.13, 400, 1.0, 3.0)
    assert 0.13 < poco < 0.145
    assert 0.29 < mucho < 1 / 3


def test_la_medida_se_acota_entre_cero_y_uno():
    assert pk.mezclar(0.5, 100, -4.0, 3.0) == 0.25        # EV negativo -> 0
    assert pk.mezclar(0.5, 100, 9.0, 3.0) == 0.75         # >1 -> 1


def test_la_persistencia_mide_la_primera_oferta_por_partido(monkeypatch):
    sqls = []

    def q(sql, params=()):
        sqls.append(sql)
        return [{"book": "coolbet", "n": 100, "ev": 3.0, "edge": 6.0}]

    monkeypatch.setattr(pk, "query", q)
    vigente = pk.persistencias()
    assert "DISTINCT ON (o.match_id, o.book)" in sqls[0]
    assert vigente["coolbet"] == round((100 * 0.5 + 100 * pk.UNMEASURED_PERSISTENCE) / 200, 4)
    assert vigente["bet365"] == pk.PERSISTENCE["bet365"]
