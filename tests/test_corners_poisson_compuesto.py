import numpy as np

from qf.eval.corners_poisson_compuesto import cdf_polya_aeppli


def test_polya_aeppli_suma_uno_y_respeta_media_y_phi():
    media, phi = 10.0, 1.175
    cdf = cdf_polya_aeppli(media, phi, kmax=120)
    pmf = np.diff(np.r_[0.0, cdf])
    k = np.arange(len(pmf))
    assert abs(cdf[-1] - 1) < 1e-9
    m = float((k * pmf).sum())
    v = float(((k - m) ** 2 * pmf).sum())
    assert abs(m - media) < 1e-6
    assert abs(v / m - phi) < 1e-6


def test_matriz_sarmanov_es_distribucion_y_omega_cero_es_independencia():
    from qf.eval.marcadores_sarmanov import matriz
    m = matriz("sarmanov", 1.5, 1.1, 1.0)
    assert abs(m.sum() - 1) < 1e-12 and (m >= 0).all()
    assert np.allclose(matriz("sarmanov", 1.5, 1.1, 0.0), matriz("ind", 1.5, 1.1))


def test_matriz_1t_con_choque_comun_suma_uno_y_k_infinito_es_independencia():
    from qf.eval.primer_tiempo_por_liga import matriz_1t
    m = matriz_1t(1.4, 1.1, 20.0)
    assert abs(m.sum() - 1) < 1e-12
    assert m[1:, 1:].sum() > matriz_1t(1.4, 1.1, np.inf)[1:, 1:].sum()      # correlación positiva: más «ambos»
