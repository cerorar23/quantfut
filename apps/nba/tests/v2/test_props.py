import numpy as np
import pytest

from nba.v2 import props


def test_pmf_suma_uno_y_tiene_la_media_pedida():
    muestras = np.full((3, 5), 30.0)
    pmf = props.pmf_mezcla(np.array([0.5, 0.2, 0.1]), muestras, alfa=0.1, techo=120)
    assert pmf.sum(axis=1) == pytest.approx(1.0, abs=1e-6)
    assert (pmf * np.arange(121)).sum(axis=1) == pytest.approx([15.0, 6.0, 3.0], abs=0.01)


def test_mezcla_de_minutos_ensancha_la_distribucion():
    fijo = props.pmf_mezcla(np.array([0.5]), np.full((1, 5), 30.0), 0.05, 80)[0]
    mezcla = props.pmf_mezcla(np.array([0.5]), np.array([[10.0, 20.0, 30.0, 40.0, 50.0]]), 0.05, 80)[0]
    k = np.arange(81)
    var = lambda p: (p * k * k).sum() - ((p * k).sum()) ** 2  # noqa: E731
    assert (fijo * k).sum() == pytest.approx((mezcla * k).sum(), abs=0.01) and var(mezcla) > var(fijo)


def test_prob_mas_de_es_monotona_acotada_y_reparte_el_empate():
    pmf = props.pmf_mezcla(np.array([0.4, 0.4]), np.full((2, 5), 30.0), 0.1, 80)
    p = props.prob_mas_de(pmf, np.array([10.5, 14.5]))
    assert p[0] > p[1] and 0.001 <= p[1] <= p[0] <= 0.999
    entera = props.prob_mas_de(pmf[:1], np.array([12.0]))[0]
    assert props.prob_mas_de(pmf[:1], np.array([11.5]))[0] > entera > props.prob_mas_de(pmf[:1], np.array([12.5]))[0]
    extremo = props.prob_mas_de(pmf[:1], np.array([500.0]))[0]
    assert extremo == 0.001                                               # nunca 0 exacto


def test_alfa_y_pit_recuperan_una_binomial_negativa_simulada():
    rng = np.random.default_rng(0)
    mu, alfa = np.full(40000, 6.0), 0.25
    n = 1 / alfa
    y = rng.negative_binomial(n, n / (n + mu))
    est = props.estimar_alfa(mu, y.astype(float))
    assert est == pytest.approx(alfa, abs=0.03)
    pmf = props.pmf_mezcla(mu[:1], np.full((1, 1), 1.0) * 6.0 / mu[0] * 1.0, alfa, 60)
    pit = props.pit_aleatorio(np.repeat(pmf, len(y), axis=0), y.astype(float))
    assert np.mean((pit > 0.1) & (pit < 0.9)) == pytest.approx(0.8, abs=0.01)


def test_tasa_se_encoge_hacia_el_prior_con_poca_evidencia():
    m = np.array([[np.nan] * 28 + [30.0, 30.0]])
    s = np.array([[[np.nan] * 28 + [30.0, 30.0]]])                        # 1 pt por minuto observado
    prior = np.array([[0.4]])
    poca = props.tasa_por_minuto(m, s, prior, k=300.0, decaimiento=1.0)[0, 0]
    mucha = props.tasa_por_minuto(m, s, prior, k=1.0, decaimiento=1.0)[0, 0]
    assert 0.4 < poca < mucha < 1.0


def test_prior_por_nivel_y_niveles_de_rol():
    me = np.array([5.0, 12.0, 35.0, 36.0])
    prior = props.prior_por_nivel(me, np.array([10.0, 20.0, 30.0, 30.0]), np.array([[1.0], [4.0], [24.0], [18.0]]))
    assert list(props.nivel(me)) == [0, 1, 5, 5] and prior[5, 0] == pytest.approx(42 / 60) and prior[1, 0] == pytest.approx(0.2)
