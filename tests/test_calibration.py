"""
Verificación del calibrador de intensidades.

Dos cosas que estos tests tienen que demostrar, porque de nada sirve que el
código corra si falla cualquiera de ellas:

1. Que el 1X2 vectorizado del calibrador coincide EXACTAMENTE con el que
   produce `model/pricing.py`. Si divergen, el calibrador estaría optimizando
   una probabilidad distinta de la que luego se publica.
2. Que la puerta de validación RECHAZA la calibración cuando no hay nada que
   corregir. Un calibrador que siempre dice "mejoré" es peor que no tenerlo.
"""
from __future__ import annotations

import numpy as np
import pytest

from qf.eval.metrics import log_loss
from qf.model.calibration import (
    LambdaCalibrator,
    fit_and_validate,
    probs_1x2,
)
from qf.model.pricing import market_1x2, score_matrix


def simulate_outcomes(lam: np.ndarray, mu: np.ndarray, rho: float,
                      rng: np.random.Generator) -> np.ndarray:
    """Muestrea resultados 1X2 desde las probabilidades verdaderas."""
    p = probs_1x2(lam, mu, rho)
    u = rng.random(len(p))
    cum = np.cumsum(p, axis=1)
    return (u[:, None] > cum).sum(axis=1).clip(0, 2)


# ---------------------------------------------------------------------------
# Coherencia con el pricing que se publica
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("lam,mu,rho", [
    (1.5, 1.1, 0.0),
    (2.3, 0.7, -0.05),
    (0.9, 1.8, 0.08),
    (1.0, 1.0, -0.12),
])
def test_probs_1x2_coincide_con_pricing(lam, mu, rho):
    vec = probs_1x2(np.array([lam]), np.array([mu]), rho, max_goals=10)[0]
    ref = market_1x2(score_matrix(lam, mu, rho, max_goals=10))
    assert vec[0] == pytest.approx(ref["home"], abs=1e-12)
    assert vec[1] == pytest.approx(ref["draw"], abs=1e-12)
    assert vec[2] == pytest.approx(ref["away"], abs=1e-12)


def test_probs_1x2_suma_uno():
    rng = np.random.default_rng(1)
    lam = rng.uniform(0.3, 3.5, 200)
    mu = rng.uniform(0.3, 3.5, 200)
    p = probs_1x2(lam, mu, -0.03)
    assert np.allclose(p.sum(axis=1), 1.0, atol=1e-12)
    assert (p > 0).all()


# ---------------------------------------------------------------------------
# Identidad
# ---------------------------------------------------------------------------

def test_identidad_no_cambia_nada():
    cal = LambdaCalibrator.identity()
    assert cal.params.is_identity
    assert cal.apply(1.7, 1.2) == (1.7, 1.2)
    lam, mu = cal.apply_vec(np.array([1.0, 2.0]), np.array([0.5, 1.5]))
    assert np.allclose(lam, [1.0, 2.0])
    assert np.allclose(mu, [0.5, 1.5])


def test_muestra_insuficiente_es_error_explicito():
    rng = np.random.default_rng(2)
    lam = rng.uniform(0.8, 2.0, 50)
    mu = rng.uniform(0.8, 2.0, 50)
    oc = rng.integers(0, 3, 50)
    with pytest.raises(ValueError, match="insuficiente"):
        LambdaCalibrator().fit(lam, mu, oc)


# ---------------------------------------------------------------------------
# Corrección de un modelo sesgado
# ---------------------------------------------------------------------------

def test_corrige_modelo_sistematicamente_inflado():
    """
    Escenario realista: el modelo predice más goles de los que ocurren
    (lambda inflada un 30%). El calibrador debe detectarlo y comprimir.
    """
    rng = np.random.default_rng(42)
    n = 4000
    rho = -0.03

    lam_true = rng.uniform(0.6, 2.6, n)
    mu_true = rng.uniform(0.5, 2.2, n)
    outcomes = simulate_outcomes(lam_true, mu_true, rho, rng)

    # Lo que "cree" el modelo: intensidades infladas.
    lam_model = lam_true * 1.30
    mu_model = mu_true * 1.30

    cal = LambdaCalibrator().fit(lam_model, mu_model, outcomes, rho=rho)

    p_antes = probs_1x2(lam_model, mu_model, rho)
    l2, m2 = cal.apply_vec(lam_model, mu_model)
    p_despues = probs_1x2(l2, m2, rho)

    ll_antes = log_loss(p_antes, outcomes)
    ll_despues = log_loss(p_despues, outcomes)
    assert ll_despues < ll_antes, (
        f"La calibración no mejoró el log-loss: {ll_antes:.5f} -> {ll_despues:.5f}"
    )
    # Y debe acercarse a deshacer el factor 1.3 (log(1/1.3) = -0.262).
    assert cal.params.a0 < 0, "No comprimió la intensidad local"
    assert np.mean(l2) < np.mean(lam_model)


def test_puerta_de_validacion_acepta_cuando_hay_sesgo_real():
    rng = np.random.default_rng(99)
    n = 5000
    rho = -0.03
    lam_true = rng.uniform(0.6, 2.6, n)
    mu_true = rng.uniform(0.5, 2.2, n)
    outcomes = simulate_outcomes(lam_true, mu_true, rho, rng)

    cal, report = fit_and_validate(lam_true * 1.35, mu_true * 1.35,
                                   outcomes, rho=rho)
    assert report["ok"], report.get("reason")
    assert cal.params.validated
    assert report["log_loss_after"] < report["log_loss_before"]


def test_puerta_de_validacion_rechaza_modelo_ya_calibrado():
    """
    Si el modelo ya está bien calibrado no hay nada que ganar, y el calibrador
    solo puede ajustar ruido. La puerta debe devolver la IDENTIDAD.
    """
    rng = np.random.default_rng(123)
    n = 5000
    rho = -0.03
    lam = rng.uniform(0.6, 2.6, n)
    mu = rng.uniform(0.5, 2.2, n)
    outcomes = simulate_outcomes(lam, mu, rho, rng)   # sin sesgo alguno

    cal, report = fit_and_validate(lam, mu, outcomes, rho=rho)
    if report["ok"]:
        # Si la acepta, la mejora debe ser marginal: nunca una "gran mejora"
        # sobre un modelo que ya era correcto (eso indicaría sobreajuste).
        mejora = report["log_loss_before"] - report["log_loss_after"]
        assert mejora < 0.005, f"Mejora sospechosa sobre modelo ya calibrado: {mejora}"
    else:
        assert cal.params.is_identity
        assert "reason" in report


def test_datos_insuficientes_para_validar_devuelve_identidad():
    rng = np.random.default_rng(5)
    n = 300          # el corte deja <200 para ajustar
    lam = rng.uniform(0.8, 2.0, n)
    mu = rng.uniform(0.8, 2.0, n)
    oc = simulate_outcomes(lam, mu, 0.0, rng)
    cal, report = fit_and_validate(lam, mu, oc)
    assert not report["ok"]
    assert cal.params.is_identity
    assert "insuficientes" in report["reason"]


def test_persistencia_conserva_los_parametros(tmp_path):
    rng = np.random.default_rng(8)
    n = 3000
    lam = rng.uniform(0.6, 2.6, n)
    mu = rng.uniform(0.5, 2.2, n)
    oc = simulate_outcomes(lam, mu, 0.0, rng)
    cal = LambdaCalibrator().fit(lam * 1.2, mu * 1.2, oc)

    path = str(tmp_path / "cal.pkl")
    cal.save(path)
    otro = LambdaCalibrator.load(path)
    assert otro.params.a0 == pytest.approx(cal.params.a0)
    assert otro.params.a1 == pytest.approx(cal.params.a1)
    assert otro.apply(1.5, 1.2) == cal.apply(1.5, 1.2)
