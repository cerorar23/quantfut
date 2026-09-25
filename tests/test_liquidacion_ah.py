"""
Liquidación del hándicap asiático.

En una línea de cuarto el stake se parte en dos mitades. La mitad ganada cobra
a cuota, la empujada se DEVUELVE (1, no la cuota) y la perdida no devuelve
nada. Aplicar un multiplicador único sobre la cuota pagaba la mitad empujada a
cuota: medio-ganada y medio-perdida solo cuadraban a 2,00. Estos tests fijan
el beneficio por unidad a 1,90 y a 2,00, donde el error y el acierto
coincidían.
"""
from __future__ import annotations

import pytest

from qf.eval.clv import _settle_outcome, settle_profit


def _ah(selection: str, line: float, hg: int, ag: int, price: float):
    outcome, win, push = _settle_outcome("spreads", selection, line, hg, ag)
    return outcome, settle_profit(1.0, price, win, push)


# (selección, línea, goles local, goles visitante, outcome, beneficio a 1,90,
#  beneficio a 2,00)
CASOS_CUARTO = [
    ("home", -0.25, 1, 0, "win",       0.90,  1.00),
    ("home", -0.75, 2, 1, "half_win",  0.45,  0.50),
    ("away", +0.25, 1, 1, "half_win",  0.45,  0.50),
    ("home", -0.25, 1, 1, "half_loss", -0.50, -0.50),
    ("home", -1.25, 2, 1, "half_loss", -0.50, -0.50),
    ("home", -0.25, 0, 1, "loss",      -1.00, -1.00),
    ("away", +0.75, 0, 2, "win",       0.90,  1.00),
]


@pytest.mark.parametrize("sel,line,hg,ag,outcome,p190,p200", CASOS_CUARTO)
def test_lineas_de_cuarto(sel, line, hg, ag, outcome, p190, p200):
    o, profit = _ah(sel, line, hg, ag, 1.90)
    assert o == outcome
    assert profit == pytest.approx(p190, abs=1e-12)
    assert _ah(sel, line, hg, ag, 2.00)[1] == pytest.approx(p200, abs=1e-12)


def test_media_ganada_a_190_no_es_el_multiplicador_075():
    # Regresión explícita del bug: 0,75 × 1,90 − 1 = +0,425.
    _, profit = _ah("home", -0.75, 2, 1, 1.90)
    assert profit == pytest.approx(0.5 * 1.90 + 0.5 - 1.0)
    assert profit != pytest.approx(0.75 * 1.90 - 1.0)


def test_media_perdida_a_190_no_es_el_multiplicador_025():
    # Regresión explícita del bug: 0,25 × 1,90 − 1 = −0,525.
    _, profit = _ah("home", -0.25, 1, 1, 1.90)
    assert profit == pytest.approx(-0.50)
    assert profit != pytest.approx(0.25 * 1.90 - 1.0)


@pytest.mark.parametrize("sel,line,hg,ag", [
    ("home", 0.0, 1, 1),
    ("away", 0.0, 2, 2),
    ("home", -1.0, 2, 1),
    ("away", +1.0, 2, 1),
    ("home", +2.0, 0, 2),
])
@pytest.mark.parametrize("price", [1.90, 2.00, 3.50])
def test_empuje_de_linea_entera_devuelve_el_stake(sel, line, hg, ag, price):
    o, profit = _ah(sel, line, hg, ag, price)
    assert o == "push"
    assert profit == pytest.approx(0.0, abs=1e-12)


def test_lineas_enteras_y_medias_sin_empuje():
    assert _ah("home", -1.0, 3, 1, 1.90) == ("win", pytest.approx(0.90))
    assert _ah("home", -1.0, 1, 1, 1.90) == ("loss", pytest.approx(-1.00))
    assert _ah("away", +0.5, 1, 1, 1.90) == ("win", pytest.approx(0.90))
    assert _ah("home", -0.5, 1, 1, 1.90) == ("loss", pytest.approx(-1.00))


def test_el_stake_escala_el_beneficio():
    _, win, push = _settle_outcome("spreads", "home", -0.75, 2, 1)
    assert settle_profit(2.5, 1.90, win, push) == pytest.approx(2.5 * 0.45)


@pytest.mark.parametrize("market,sel,line,hg,ag,outcome,profit", [
    ("h2h", "home", None, 2, 1, "win", 0.90),
    ("h2h", "draw", None, 2, 1, "loss", -1.00),
    ("totals", "over", 2.0, 1, 1, "push", 0.0),
    ("totals", "under", 2.5, 1, 1, "win", 0.90),
    ("team_totals_home", "over", 1.0, 1, 0, "push", 0.0),
    ("btts", "yes", None, 1, 1, "win", 0.90),
    ("double_chance", "X2", None, 2, 1, "loss", -1.00),
])
def test_resto_de_mercados_no_cambia(market, sel, line, hg, ag, outcome, profit):
    o, win, push = _settle_outcome(market, sel, line, hg, ag)
    assert o == outcome
    assert settle_profit(1.0, 1.90, win, push) == pytest.approx(profit, abs=1e-12)
