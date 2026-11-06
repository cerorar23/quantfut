"""Piezas del modelo contra cálculos independientes: tabla de M̄_f frente al simulador exacto, pieza P en un mundo
binomial conocido, unión C, recalibración y Elo."""
import math

import numpy as np
import pandas as pd
import pytest

from tenis.modelo import datos as dm
from tenis.modelo import tabla
from tenis.modelo.linea_base import elo
from tenis.modelo.puntos import PsiP, filtrar_p
from tenis.modelo.recalibracion import ajustar_pendiente, aplicar, por_temporada
from tenis.modelo.sintetico import LBAR, RHO_EPS, SIGMA_EPS, mundo, tablas_prueba
from tenis.modelo.union import unir
from tenis.simulador.formato import Formato
from tenis.simulador.mezcla import Incertidumbre, prob_ganar


@pytest.mark.parametrize("f", range(len(dm.FORMATOS)))
def test_tabla_frente_al_simulador_exacto(f):
    """Error de la tabla < 1e-6 frente a `mezcla.prob_ganar` en puntos fuera de la rejilla (todos los formatos)."""
    tb = tablas_prueba()[(f, 0)]
    inc, fm = Incertidumbre(SIGMA_EPS, RHO_EPS), Formato(*dm.FORMATOS[f])
    rhos = np.random.default_rng(f).uniform(-1.2, 1.2, 12) + 0.00377
    for r in rhos[:4]:
        exacto = prob_ganar(float(tabla.expit(LBAR + r)), float(tabla.expit(LBAR - r)), fm, inc)
        assert abs(math.exp(tb.log_m(r)[0]) - exacto) < 1e-6
    assert tabla.error_tabla(tb, LBAR, fm, inc, rhos) < 1e-6
    # con incertidumbre de parámetros: convolución 1-D frente a la cuadratura 2-D fina del simulador
    assert tabla.error_con_v(tb, LBAR, fm, inc, [(0.1, 0.01), (-0.3, 0.06)], q=61) < 1e-6


def test_tabla_simetrica_y_derivadas_coherentes():
    tb = tablas_prueba()[(0, 0)]
    for r in (-0.7, -0.1, 0.0, 0.33):
        for v in (0.0, 0.03, 0.5):
            assert abs(tb.prob(r, v) + tb.prob(-r, v) - 1) < 1e-14
        h = 1e-5
        l0, l1, l2 = tb.log_m(r)
        assert abs((tb.log_m(r + h)[0] - tb.log_m(r - h)[0]) / (2 * h) - l1) < 1e-5
        assert abs((tb.log_m(r + h)[1] - tb.log_m(r - h)[1]) / (2 * h) - l2) < 1e-3
    assert tb.prob(0.0, 0.2) == 0.5


def test_pieza_p_recupera_el_saque_de_un_mundo_binomial():
    """Mundo con p de saque verdadera por jugador: el filtro P ordena a los jugadores y Ŝ está cerca de la suma real."""
    p, e = mundo(n_jugadores=20, n_semanas=60, semilla=31)
    d = dm.preparar(p, e, "atp", 2030)
    rng = np.random.default_rng(31)
    alfa = rng.normal(0, 0.25, d.n_jugadores)
    filas = []
    for r in d.p.itertuples():
        for lado, (a, b) in ((1, (r.j1, r.j2)), (2, (r.j2, r.j1))):
            q = 1 / (1 + np.exp(-(0.5 + alfa[a])))
            filas.append({"partido_key": r.partido_key, "lado": lado, "puntos_saque": 80,
                          "puntos_saque_ganados": int(rng.binomial(80, q)),
                          "visible_desde": r.corte_utc + pd.Timedelta(days=2)})
    from tenis.modelo.puntos import observaciones
    obs = observaciones(d, pd.DataFrame(filas))
    psi = PsiP(0.25, 0.05, 0.01, 0.01, 0.01, (1.0, 1.0, 1.0, 1.0), 0.05, 0.0, 0.01)
    ll, s_hat, lbar = filtrar_p(d, obs, psi, (2010, 2030))
    assert math.isfinite(ll) and np.all(np.abs(np.array(lbar) - 0.5) < 0.15)
    real = np.array([1 / (1 + np.exp(-(0.5 + alfa[a]))) + 1 / (1 + np.exp(-(0.5 + alfa[b])))
                     for a, b in zip(d.p.j1, d.p.j2)])
    tarde = d.p.corte_ns.to_numpy() > d.p.corte_ns.quantile(0.7)
    assert np.corrcoef(s_hat[tarde], real[tarde])[0, 1] > 0.8
    assert np.mean(np.abs(s_hat[tarde] - real[tarde])) < 0.05


def test_union_reproduce_pi_y_rechaza_lo_inalcanzable():
    for f in (0, 4):
        u = unir(1.25, 0.70, f, SIGMA_EPS, RHO_EPS, 0.02)
        assert abs(u.pi_logrado - 0.70) < 1e-8 and abs(u.p_a + u.p_b - 1.25) < 1e-12 and u.p_a > u.p_b
    with pytest.raises(ValueError):
        unir(0.06, 0.999999, 0, SIGMA_EPS, RHO_EPS, 0.02)


def test_recalibracion_recupera_la_pendiente_y_solo_usa_temporadas_previas():
    rng = np.random.default_rng(41)
    x = rng.normal(0, 1.2, 40000)
    p = 1 / (1 + np.exp(-x))
    y = (rng.random(len(x)) < 1 / (1 + np.exp(-0.8 * x))).astype(int)
    assert abs(ajustar_pendiente(p, y) - 0.8) < 0.03
    assert abs(aplicar(np.array([0.5]), 0.7)[0] - 0.5) < 1e-15
    temp = np.repeat([2017, 2018, 2019], [20000, 15000, 5000])
    y_mal = y.copy(); y_mal[temp == 2019] = 1 - y_mal[temp == 2019]     # la temporada evaluada no debe influir
    a, ba = por_temporada(temp, p, y, np.ones(len(y), bool), [2019], 2012)
    b, bb = por_temporada(temp, p, y_mal, np.ones(len(y), bool), [2019], 2012)
    assert ba == bb


def test_elo_simetrico_y_por_bloques():
    p, e = mundo(semilla=51)
    d = dm.preparar(p, e, "atp", 2030)
    pe = elo(d)["p_elo"]
    assert np.all(pe[d.p.corte_ns == d.p.corte_ns.min()] == 0.5)
    from test_modelo_propiedades import intercambiar
    d2 = dm.preparar(*intercambiar(p, e), "atp", 2030)
    np.testing.assert_allclose(elo(d2)["p_elo"], 1 - pe, atol=1e-12)
