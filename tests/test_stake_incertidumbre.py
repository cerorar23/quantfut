"""
Stake encogido por la incertidumbre de la persistencia (idea 5, 2026-10-03).

Lo que fijan: el factor de Baker y McHale, su error típico mezclado con los
mismos pesos que la persistencia, y que el factor cambia cuánto se apuesta
pero no qué candidato es publicable ("stake sí, muestra no").
"""
from __future__ import annotations

import math

import pytest

from qf.publish import picks as pk


def test_factor_de_baker_y_mchale():
    assert pk.factor_incertidumbre(0.72, 0.17) == pytest.approx(0.947, abs=1e-3)
    assert pk.factor_incertidumbre(0.13, 0.15) == pytest.approx(0.429, abs=1e-3)
    assert pk.factor_incertidumbre(0.0, 0.1) == 0.0
    assert pk.factor_incertidumbre(-0.15, 0.25) == 0.0


def test_sin_sombra_el_error_es_la_previa():
    assert pk.mezclar_se(0.15, 0, None, None) == 0.15
    assert pk.mezclar_se(0.15, 10, 4.0, 0.0) == 0.15


def test_el_error_se_mezcla_con_los_pesos_de_la_persistencia():
    # 100 partidos medidos con sd(ev)=5 y edge medio 4 -> SE medida 0,125.
    se = pk.mezclar_se(0.31, 100, 5.0, 4.0)
    assert se == pytest.approx(math.sqrt((100 * 0.125) ** 2 + (100 * 0.31) ** 2) / 200)
    assert se < 0.31, "medir reduce la incertidumbre"


def test_factores_sin_sombra_salen_de_la_previa(monkeypatch):
    monkeypatch.setattr(pk, "query", lambda sql, params=(): [])
    k = pk.factores()
    assert k["1xbet"] == pytest.approx(0.947, abs=1e-3)
    assert k["bet365"] == pytest.approx(0.429, abs=1e-3)
    assert k["william_hill"] == 0.0
    assert pk.factor_sin_medir() == pytest.approx(0.42 ** 2 / (0.42 ** 2 + 0.31 ** 2))


def test_una_casa_medida_en_la_sombra_tiene_su_propio_factor(monkeypatch):
    monkeypatch.setattr(pk, "query", lambda sql, params=(): [
        {"book": "coolbet", "n": 100, "ev": 3.0, "sd_ev": 5.0, "edge": 6.0}])
    k = pk.factores()
    rho = (100 * 0.5 + 100 * pk.UNMEASURED_PERSISTENCE) / 200
    se = pk.mezclar_se(pk.UNMEASURED_PERSISTENCE_SE, 100, 5.0, 6.0)
    assert k["coolbet"] == round(pk.factor_incertidumbre(rho, se), 4)


def _cand(mid: str, stake: float, kelly: float) -> pk.Candidate:
    return pk.Candidate(
        match_id=mid, prediction_id=None, market="h2h", selection="home", line=None,
        model_prob=None, best_price=2.2, best_book="bet365", market_prob=0.48,
        raw_edge=5.6, shrunk_edge=0.7, stake_units=stake, kickoff_utc=None,
        label="h2h home", stake_kelly_units=kelly)


def test_lo_publicable_se_decide_sin_el_factor(monkeypatch):
    cands = {"a": [_cand("a", 0.03, 0.08)], "b": [_cand("b", 0.04, 0.04)]}
    monkeypatch.setattr(pk, "find_candidates", lambda pred, now=None: cands[pred["match_id"]])
    elegidos = pk.select_daily([{"match_id": "a"}, {"match_id": "b"}])
    assert [c.match_id for c in elegidos] == ["a"], \
        "a entra por su Kelly sin factor (0,08) aunque publique 0,03; b no"
    assert elegidos[0].stake_units == 0.03
