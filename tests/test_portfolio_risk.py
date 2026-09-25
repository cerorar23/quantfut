"""
Verificación del riesgo de portafolio con correlación.

Lo que esto tiene que demostrar: que 12 picks correlacionados se miden como
MÁS arriesgados que 12 independientes con el mismo stake. La suma bruta de
stakes —el tope que había antes— no distingue entre esos dos casos, y es
exactamente la diferencia entre un mal día y un día que te saca del negocio.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest

from qf.config import settings
from qf.publish.picks import (
    CORR_BASE,
    CORR_CAP,
    Candidate,
    apply_portfolio_limits,
    correlation,
    portfolio_sigma,
)

KO = datetime(2026, 5, 1, tzinfo=timezone.utc)


def mk(match_id: str, league: str = "mx.liga_mx", market: str = "h2h",
       selection: str = "home", price: float = 2.0, stake: float = 1.0,
       market_prob: float = 0.5) -> Candidate:
    return Candidate(
        match_id=match_id, prediction_id=f"p_{match_id}", market=market,
        selection=selection, line=None, model_prob=market_prob + 0.05,
        best_price=price, best_book="pinnacle", market_prob=market_prob,
        raw_edge=5.0, shrunk_edge=3.0, stake_units=stake,
        kickoff_utc=KO + timedelta(hours=1), label="x", league_id=league,
    )


# ---------------------------------------------------------------------------
# Matriz de correlación
# ---------------------------------------------------------------------------

def test_riesgo_de_modelo_comun_nunca_es_cero():
    """
    Dos picks de ligas y mercados distintos NO son independientes: salen del
    mismo modelo. Si esto diera 0, el sistema creería que puede diversificar
    su propio sesgo repartiendo entre ligas.
    """
    a = mk("m1", league="eng.premier", market="h2h", selection="home")
    b = mk("m2", league="mx.liga_mx", market="totals", selection="over")
    assert correlation(a, b) == pytest.approx(CORR_BASE)
    assert correlation(a, b) > 0


def test_misma_liga_correlaciona_mas_que_distinta():
    a = mk("m1", league="mx.liga_mx", market="h2h", selection="home")
    misma = mk("m2", league="mx.liga_mx", market="totals", selection="over")
    otra = mk("m3", league="eng.premier", market="totals", selection="over")
    assert correlation(a, misma) > correlation(a, otra)


def test_mismo_mercado_y_direccion_correlaciona_mas():
    a = mk("m1", league="eng.premier", market="totals", selection="over")
    igual = mk("m2", league="esp.laliga", market="totals", selection="over")
    opuesto = mk("m3", league="esp.laliga", market="totals", selection="under")
    assert correlation(a, igual) > correlation(a, opuesto)


def test_correlacion_tiene_tope():
    a = mk("m1", league="mx.liga_mx", market="totals", selection="over")
    b = mk("m2", league="mx.liga_mx", market="totals", selection="over")
    assert correlation(a, b) <= CORR_CAP


# ---------------------------------------------------------------------------
# Sigma del portafolio
# ---------------------------------------------------------------------------

def test_sigma_de_una_sola_apuesta_es_la_formula_conocida():
    """sigma = stake * cuota * sqrt(p(1-p))"""
    c = mk("m1", price=2.5, stake=1.5, market_prob=0.4)
    esperado = 1.5 * 2.5 * math.sqrt(0.4 * 0.6)
    assert portfolio_sigma([c]) == pytest.approx(esperado, rel=1e-9)


def test_portafolio_vacio_no_rompe():
    assert portfolio_sigma([]) == 0.0
    assert apply_portfolio_limits([]) == []


def test_picks_correlacionados_miden_mas_riesgo_que_diversificados():
    """El test central: misma exposición bruta, riesgo distinto."""
    concentrado = [
        mk(f"m{i}", league="mx.liga_mx", market="totals", selection="over")
        for i in range(8)
    ]
    diversificado = [
        mk(f"m{i}", league=f"liga_{i}", market="h2h",
           selection="home" if i % 2 else "away")
        for i in range(8)
    ]
    assert sum(p.stake_units for p in concentrado) == \
           sum(p.stake_units for p in diversificado)

    s_conc = portfolio_sigma(concentrado)
    s_div = portfolio_sigma(diversificado)
    assert s_conc > s_div, (
        f"El lote concentrado no mide más riesgo: {s_conc:.3f} vs {s_div:.3f}"
    )


def test_sigma_correlacionada_supera_a_la_independiente():
    """Comprobación contra la raíz de la suma de cuadrados (caso ρ=0)."""
    picks = [mk(f"m{i}", league="mx.liga_mx") for i in range(6)]
    indep = math.sqrt(sum((p.stake_units * p.best_price *
                           math.sqrt(p.market_prob * (1 - p.market_prob))) ** 2
                          for p in picks))
    assert portfolio_sigma(picks) > indep


# ---------------------------------------------------------------------------
# Escalado
# ---------------------------------------------------------------------------

def test_no_escala_cuando_esta_dentro_de_los_topes():
    picks = [mk("m1", stake=0.3), mk("m2", league="eng.premier", stake=0.2)]
    antes = [p.stake_units for p in picks]
    apply_portfolio_limits(picks)
    assert [p.stake_units for p in picks] == antes


def test_respeta_el_tope_de_exposicion_bruta():
    picks = [mk(f"m{i}", league=f"liga_{i}", stake=3.0) for i in range(10)]
    apply_portfolio_limits(picks)
    bruto = sum(p.stake_units for p in picks)
    assert bruto <= settings.max_daily_exposure + 0.05


def test_respeta_el_tope_de_riesgo_correlacionado():
    picks = [
        mk(f"m{i}", league="mx.liga_mx", market="totals", selection="over",
           stake=2.0, price=3.0)
        for i in range(12)
    ]
    apply_portfolio_limits(picks)
    assert portfolio_sigma(picks) <= settings.max_portfolio_risk + 0.05


def test_un_lote_concentrado_se_recorta_mas_que_uno_diversificado():
    """
    La consecuencia práctica de todo esto: con la misma exposición bruta
    pedida, el lote correlacionado acaba con stakes más pequeños.
    """
    concentrado = [
        mk(f"c{i}", league="mx.liga_mx", market="totals", selection="over",
           stake=1.5, price=3.0)
        for i in range(10)
    ]
    diversificado = [
        mk(f"d{i}", league=f"liga_{i}", market="h2h",
           selection="home" if i % 2 else "away", stake=1.5, price=3.0)
        for i in range(10)
    ]
    apply_portfolio_limits(concentrado)
    apply_portfolio_limits(diversificado)

    assert sum(p.stake_units for p in concentrado) < \
           sum(p.stake_units for p in diversificado)


def test_usa_la_probabilidad_del_mercado_no_la_del_modelo():
    """
    Medir el riesgo con la probabilidad del propio modelo lo subestima cuando
    el modelo está sobreconfiado, que es el caso por defecto.
    """
    c = mk("m1", price=2.0, stake=1.0, market_prob=0.5)
    c.model_prob = 0.95        # modelo eufórico
    # sigma debe salir de market_prob=0.5, no de 0.95
    assert portfolio_sigma([c]) == pytest.approx(2.0 * math.sqrt(0.25), rel=1e-9)
