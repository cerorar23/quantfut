"""
Valor esperado contra el cierre SIN margen.

`clv_pct` compara la cuota tomada con la de cierre CON margen, y el margen lo
infla. Lo que decide la puerta es `price * p_cierre_justa - 1`, con la
probabilidad sacada de un único snapshot sharp y del grupo complementario
completo. Estos tests fijan el emparejamiento de cada mercado.
"""
from __future__ import annotations

import pytest

from qf.config import settings
from qf.eval.clv import ev_close_pct, fair_close_prob
from qf.model.devig import devig

H2H = {("home", None): 2.00, ("draw", None): 3.50, ("away", None): 4.00}


def test_h2h_usa_el_grupo_de_tres():
    esperado = devig([2.00, 3.50, 4.00], settings.devig_method)
    for i, sel in enumerate(("home", "draw", "away")):
        assert fair_close_prob("h2h", sel, None, H2H) == pytest.approx(esperado[i])


def test_la_cuota_justa_vale_cero_y_la_del_cierre_con_margen_pierde():
    p = fair_close_prob("h2h", "home", None, H2H)
    assert ev_close_pct(1.0 / p, p) == pytest.approx(0.0, abs=1e-9)
    assert ev_close_pct(2.00, p) < 0, "tomar el propio cierre sharp es pagar su margen"


def test_grupo_incompleto_no_se_mide():
    sin_empate = {k: v for k, v in H2H.items() if k[0] != "draw"}
    assert fair_close_prob("h2h", "home", None, sin_empate) is None


def test_totales_misma_linea():
    q = {("over", 2.5): 1.90, ("under", 2.5): 1.95, ("over", 3.5): 3.10}
    p_over = fair_close_prob("totals", "over", 2.5, q)
    p_under = fair_close_prob("totals", "under", 2.5, q)
    assert p_over + p_under == pytest.approx(1.0)
    assert fair_close_prob("totals", "over", 3.5, q) is None, "falta el under de 3,5"


def test_handicap_empareja_con_la_linea_opuesta():
    q = {("home", -0.5): 1.95, ("away", 0.5): 1.90,
         ("home", 0.5): 1.40}
    p_home = fair_close_prob("spreads", "home", -0.5, q)
    p_away = fair_close_prob("spreads", "away", 0.5, q)
    assert p_home + p_away == pytest.approx(1.0)
    assert fair_close_prob("spreads", "home", 0.5, q) is None, \
        "local +0,5 necesita visitante -0,5, no el visitante +0,5"


def test_mercados_sin_precio_sharp_no_se_miden():
    assert fair_close_prob("btts", "yes", None, {("yes", None): 1.8,
                                                  ("no", None): 2.0}) is None
    assert fair_close_prob("double_chance", "1X", None, H2H) is None
