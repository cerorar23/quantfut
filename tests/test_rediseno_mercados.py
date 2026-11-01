"""Probabilidades y liquidación de los mercados pedidos por el titular (líneas asiáticas con devolución incluidas)."""
import numpy as np
import pytest

from qf.eval.rediseno_mercados import adelgazar, liquidar, matrices_mitades, prob_linea


def test_linea_entera_devuelve_y_media_no():
    soporte = np.arange(6); pmf = np.array([[0.1, 0.2, 0.3, 0.2, 0.1, 0.1]])
    g, d = prob_linea(pmf, soporte, 2.0, "menos")
    assert g[0] == pytest.approx(0.3) and d[0] == pytest.approx(0.3)  # 0 o 1 gana, 2 devuelve
    g, d = prob_linea(pmf, soporte, 2.5, "mas")
    assert g[0] == pytest.approx(0.4) and d[0] == 0
    assert liquidar(np.array([2, 1, 3]), 2.0, "menos").tolist() == ["devuelve", "gana", "pierde"]


def test_mitades_suman_el_total_y_adelgazado():
    m1, m2 = matrices_mitades(np.array([1.5]), np.array([1.0]), 0.45)
    assert m1.sum() == pytest.approx(1, abs=1e-6) and m2.sum() == pytest.approx(1, abs=1e-6)
    # goles esperados de la primera parte = 45 % del total
    g = np.arange(m1.shape[1])
    assert (m1[0].sum(1) * g).sum() == pytest.approx(0.675, abs=1e-3)
    # adelgazar una Poisson(4) con s = 0,35 da Poisson(1,4)
    from scipy.stats import poisson
    p = poisson.pmf(np.arange(30), 4.0)[None, :]
    q = adelgazar(p, 0.35)
    assert q[0, :5] == pytest.approx(poisson.pmf(np.arange(5), 1.4), abs=1e-6)


def test_props_solo_usan_partidos_anteriores_y_bn():
    import pandas as pd
    from qf.eval.rediseno_jugadores import kappa_nb, p_mas, previos
    n = 30
    j = pd.DataFrame({"jugador_id": [7] * n, "posicion": ["F"] * n, "titular": [True] * n, "minutos": [90.0] * n,
                      "kickoff_utc": pd.date_range("2024-01-01", periods=n, freq="7D", tz="UTC"),
                      "tiros_puerta": [2.0] * (n - 1) + [10.0], "tiros_totales": [3.0] * n, "pases_acertados": [40.0] * n,
                      "faltas_recibidas": [1.0] * n, "goles": [0.0] * n, "xg": [np.nan] * n, "tarjeta": [0.0] * n})
    out = previos(j, "2024-03-01")
    assert out["m_tiros_puerta"].iloc[-1] == pytest.approx(out["m_tiros_puerta"].iloc[-2], rel=0.05)  # el 10 no entra
    rng = np.random.default_rng(1)
    m = np.full(20000, 50.0); y = rng.negative_binomial(20, 20 / 70, 20000)
    assert kappa_nb(y.astype(float), m) == pytest.approx(20, rel=0.15)
    assert p_mas(np.array([1.0]), 0.5)[0] == pytest.approx(1 - np.exp(-1))


def test_platt_corrige_una_probabilidad_inflada():
    from qf.eval.rediseno_jugadores import platt
    rng = np.random.default_rng(3)
    verdad = rng.uniform(0.05, 0.6, 20000)
    y = (rng.uniform(size=verdad.size) < verdad).astype(float)
    inflada = np.clip(verdad * 1.3, 0, 0.99)
    f = platt(inflada, y)
    assert f(inflada).mean() == pytest.approx(y.mean(), abs=0.01)
