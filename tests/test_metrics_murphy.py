"""Descomposición de Murphy (CORP/PAV) y Diebold-Mariano para el banco de pruebas del rediseño."""
import numpy as np
import pytest

from qf.eval.metrics import diebold_mariano, murphy, pav


def test_pav_es_monotona_y_promedia_bloques_violadores():
    assert pav(np.array([1.0, 0.0, 1.0, 1.0])).tolist() == [0.5, 0.5, 1.0, 1.0]
    rng = np.random.default_rng(1)
    out = pav(rng.random(500))
    assert np.all(np.diff(out) >= -1e-12)


def test_murphy_suma_exacta_y_casos_limite():
    rng = np.random.default_rng(7)
    p = rng.random(4000)
    y = (rng.random(4000) < p).astype(float)
    for score in ("brier", "log"):
        d = murphy(p, y, score=score)
        assert d["score"] == pytest.approx(d["unc"] - d["dsc"] + d["mcb"], abs=1e-12)
        assert d["mcb"] >= 0 and d["dsc"] >= 0
    # bien calibrado: descalibración casi nula; la climatología no discrimina nada
    assert murphy(p, y)["mcb"] < 0.003
    clima = murphy(np.full(4000, y.mean()), y)
    assert clima["dsc"] == pytest.approx(0, abs=1e-12) and clima["mcb"] == pytest.approx(0, abs=1e-12)
    # un pronóstico descalibrado (todo multiplicado por 0,5) tiene MCB claramente mayor
    assert murphy(p * 0.5, y)["mcb"] > 0.03


def test_diebold_mariano_por_bloques():
    rng = np.random.default_rng(3)
    a = rng.normal(1.0, 0.3, 3000)
    igual = diebold_mariano(a, a + rng.normal(0, 0.01, 3000), bloques=np.arange(3000) // 10)
    assert abs(igual["t"]) < 3
    peor = diebold_mariano(a + 0.05, a, bloques=np.arange(3000) // 10)
    assert peor["delta"] == pytest.approx(0.05) and peor["t"] > 5 and peor["ic95"][0] > 0
