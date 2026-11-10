import numpy as np

from qf.eval.favoritos_dia import dispersion


def _z(choque: float, seed: int = 5) -> float:
    rng = np.random.default_rng(seed)
    dias = np.repeat(np.arange(600), 5)
    p = np.full(len(dias), 0.75)
    # `choque`: probabilidad de que el día entero se mueva a la vez
    umbral = np.where(np.repeat(rng.uniform(size=600) < choque, 5), 0.5, 0.75)
    falla = rng.uniform(size=len(dias)) >= umbral
    return dispersion(dias, p, falla)


def test_dispersion_vale_uno_sin_correlacion_y_sube_con_choques_de_dia():
    assert 0.9 < _z(0.0) < 1.1
    assert _z(0.3) > 1.1
