import numpy as np
import pytest

from nba.v2 import recalibracion as rc


def partidos(n=20000, escala_verdadera=1.0, sigma=13.0, semilla=0):
    rng = np.random.default_rng(semilla)
    mu_modelo = rng.normal(0, 6, n)                                   # lo que el modelo cree
    margen = escala_verdadera * mu_modelo + rng.normal(0, sigma, n)   # la verdad separa más (o menos) los partidos que el modelo
    return mu_modelo, (margen > 0).astype(float)


def test_con_un_modelo_calibrado_la_escala_es_uno():
    mu, y = partidos()
    assert rc.ajustar_escala(mu, 13.0, y) == pytest.approx(1.0, abs=0.1)


@pytest.mark.parametrize("verdadera", [1.3, 0.7])
def test_la_escala_recupera_cuanto_se_subestima_o_sobreestima(verdadera):
    mu, y = partidos(escala_verdadera=verdadera)
    assert rc.ajustar_escala(mu, 13.0, y) == pytest.approx(verdadera, abs=0.12)


def test_la_logistica_lleva_la_pendiente_a_uno_y_no_empeora_la_log_perdida():
    mu, y = partidos(escala_verdadera=1.4)
    p = rc.p_ganador(mu, 13.0)
    a, b = rc.ajustar_logistica(p, y)
    p2 = rc.aplicar_logistica(p, a, b)
    from nba.v2.evaluacion import logloss, pendiente_calibracion
    assert b > 1.1 and pendiente_calibracion(p2, y)[0] == pytest.approx(1.0, abs=0.05) and logloss(p2, y) < logloss(p, y)


def test_extremos_y_entradas_invalidas():
    p = rc.p_ganador(np.array([-1e6, 0.0, 1e6]), 13.0)
    assert p[0] > 0 and p[2] < 1 and p[1] == pytest.approx(0.5)             # nunca 0 ni 1 exactos
    assert rc.aplicar_logistica([0.0, 1.0], 0.0, 1.0).min() > 0
    with pytest.raises(ValueError):
        rc.ajustar_escala(np.zeros(10), 13.0, np.zeros(10))                  # muy pocos partidos
    with pytest.raises(ValueError):
        rc.ajustar_escala(np.full(200, np.nan), 13.0, np.zeros(200))
    with pytest.raises(ValueError):
        rc.ajustar_escala(np.zeros(200), 0.0, np.zeros(200))
