"""Inflación diagonal (Karlis y Ntzoufras 2003/2005) y simulación de Kelly del rediseño."""
import numpy as np
import pytest

from qf.model.inflacion_diagonal import InflacionDiagonal
from qf.eval.rediseno_kelly import kelly_semana


def test_recupera_la_inflacion_en_el_1_1():
    rng = np.random.default_rng(0)
    n = 8000
    lam, mu = rng.uniform(0.9, 2.0, n), rng.uniform(0.7, 1.6, n)
    hg, ag = rng.poisson(lam), rng.poisson(mu)
    extra = rng.random(n) < 0.08
    hg[extra] = 1; ag[extra] = 1  # 8 % de 1-1 «extra», como Serie A 91/92
    m = InflacionDiagonal().fit(lam, mu, 0.0, hg, ag)
    assert m.p == pytest.approx(0.08, abs=0.02)
    assert m.theta[1] > 0.8
    sin = InflacionDiagonal().fit(lam, mu, 0.0, rng.poisson(lam), rng.poisson(mu))
    assert sin.p < 0.01  # sin inflación real no inventa empates
    pr = m.probs_1x2(lam[:5], mu[:5], 0.0)
    assert np.allclose(pr.sum(1), 1)


def test_kelly_no_apuesta_sin_ventaja_y_reparte_con_ventaja():
    # misma probabilidad que el mercado sin margen y cuota con margen: ninguna apuesta
    p = np.array([[0.5, 0.3, 0.2]]); cuota = 1 / (p * 1.05)
    assert kelly_semana(p, cuota, fraccion=0.25).sum() == 0
    # ventaja clara en el local: apuesta solo ahí, con la fracción de Kelly
    p2 = np.array([[0.6, 0.25, 0.15]]); cuota2 = np.array([[2.0, 4.0, 7.0]])
    f = kelly_semana(p2, cuota2, fraccion=0.25)
    assert f[0, 0] == pytest.approx(0.25 * (0.6 * 2.0 - 1) / (2.0 - 1)) and f[0, 1:].sum() == 0
