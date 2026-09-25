"""
Inversión del precio de mercado a intensidades.

Lo que hay que demostrar son tres cosas, y la tercera es la que evita el uso
peligroso del módulo:

  1. Ida y vuelta exacta: precificar unas lambdas y volver a invertirlas tiene
     que devolver las mismas.
  2. Rechazo de la entrada con margen: si se le pasan probabilidades implícitas
     crudas, el margen de la casa acabaría dentro de las intensidades y todo
     lo derivado saldría inflado sin dar ningún error.
  3. Aviso cuando la familia NO puede representar el precio. Fijados los dos
     goles esperados, la probabilidad de empate queda determinada; un mercado
     que cotice un empate fuera de ese rango no tiene ningún (lambda, mu) que
     lo reproduzca, y el módulo tiene que decirlo en vez de devolver el ajuste
     menos malo como si tal cosa.
"""
from __future__ import annotations

import pytest

from qf.model.devig import devig
from qf.model.market_anchor import RESIDUAL_OK, anchor_from_consensus, market_lambdas
from qf.model.pricing import market_1x2, market_totals, score_matrix


@pytest.mark.parametrize("lam,mu,rho", [
    (1.90, 0.68, 0.00),
    (1.35, 1.35, -0.05),
    (3.40, 0.60, 0.00),
    (0.90, 1.80, -0.10),
])
def test_ida_y_vuelta(lam, mu, rho):
    p = market_1x2(score_matrix(lam, mu, rho, 12))
    f = market_lambdas(p["home"], p["draw"], p["away"], rho)
    assert f.usable
    assert f.lam == pytest.approx(lam, abs=1e-3)
    assert f.mu == pytest.approx(mu, abs=1e-3)


def test_los_totales_no_mueven_un_mercado_coherente():
    """Con 1X2 el sistema ya está exactamente identificado."""
    lam, mu, rho = 1.72, 1.11, -0.04
    m = score_matrix(lam, mu, rho, 12)
    p = market_1x2(m)
    solo = market_lambdas(p["home"], p["draw"], p["away"], rho)
    con = market_lambdas(p["home"], p["draw"], p["away"], rho,
                         totals={2.5: market_totals(m, 2.5)["over"]})
    assert con.usable
    assert con.lam == pytest.approx(solo.lam, abs=1e-3)
    assert con.mu == pytest.approx(solo.mu, abs=1e-3)


def test_rechaza_probabilidades_con_margen():
    """Cuotas crudas de una casa: suman más de 1. Es el error caro."""
    precios = [1.80, 3.60, 4.50]
    crudas = [1 / x for x in precios]
    assert sum(crudas) > 1.0
    with pytest.raises(ValueError, match="de-vig"):
        market_lambdas(*crudas)

    limpias = devig(precios, "shin")
    f = market_lambdas(*limpias)
    assert f.usable


def test_avisa_cuando_la_familia_no_llega():
    """Empate del 10% con local y visitante iguales: no existe tal (lambda, mu)."""
    f = market_lambdas(0.45, 0.10, 0.45)
    assert not f.usable
    assert f.residual > RESIDUAL_OK

    normal = market_lambdas(0.39, 0.22, 0.39)
    assert normal.usable


def test_consenso_incompleto_devuelve_none():
    assert anchor_from_consensus({}) is None
    assert anchor_from_consensus({"home": 0.5, "away": 0.5}) is None
    assert anchor_from_consensus({"home": 0.45, "draw": 0.27, "away": 0.28}) is not None
