"""Motor C del rediseño: regresión binomial negativa para córners y tarjetas."""
import numpy as np
import pytest

from qf.model.conteos import RegresionNB, pmf_suma


def test_recupera_coeficientes_y_dispersion():
    rng = np.random.default_rng(0)
    n = 6000
    x = rng.normal(size=(n, 1))
    mu = np.exp(1.5 + 0.3 * x[:, 0])
    kappa = 8.0
    y = rng.negative_binomial(kappa, kappa / (kappa + mu))
    m = RegresionNB().fit(x, y)
    assert m.beta[0] == pytest.approx(1.5, abs=0.03) and m.beta[1] == pytest.approx(0.3, abs=0.03)
    assert m.kappa == pytest.approx(kappa, rel=0.25)
    p = m.pmf(x[:3], 40)
    assert np.allclose(p.sum(1), 1, atol=1e-6)


def test_dispersion_variable_y_suma_de_dos_lados():
    rng = np.random.default_rng(1)
    n = 6000
    x = rng.normal(size=(n, 1)); z = np.abs(rng.normal(size=(n, 1)))
    mu = np.exp(1.0 + 0.2 * x[:, 0]); kappa = np.exp(2.5 - 1.0 * z[:, 0])
    y = rng.negative_binomial(kappa, kappa / (kappa + mu))
    fija = RegresionNB().fit(x, y)
    variable = RegresionNB().fit(x, y, z)
    assert variable.nll(x, y, z) < fija.nll(x, y) - 20
    a, b = np.array([[0.2, 0.8, 0.0]]), np.array([[0.5, 0.5, 0.0]])
    assert pmf_suma(a, b)[0, :4] == pytest.approx([0.1, 0.5, 0.4, 0.0])
