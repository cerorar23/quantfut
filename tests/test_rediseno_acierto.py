"""Acierto de los pronósticos más probables del día: lo que importa si el producto publica «el más probable»."""
import numpy as np
import pandas as pd
import pytest

from qf.eval.rediseno_acierto import calibracion_alta, mas_probable, seleccion_diaria


def test_seleccion_diaria_toma_el_porcentaje_mas_probable_de_cada_dia():
    c = pd.DataFrame({"dia": ["a"] * 10 + ["b"] * 10, "prob": np.r_[np.linspace(0.5, 0.95, 10), np.linspace(0.4, 0.9, 10)],
                      "acierto": [0] * 9 + [1] + [0] * 8 + [1, 1]})
    r = seleccion_diaria(c, coberturas=(0.1, 0.2))
    fila = r.set_index("cobertura").loc[0.1]
    assert fila["n"] == 2 and fila["acierto"] == 1.0  # el más probable de cada día
    assert r.set_index("cobertura").loc[0.2, "n"] == 4


def test_mas_probable_y_calibracion():
    p = np.array([[0.6, 0.3, 0.1], [0.2, 0.3, 0.5]])
    prob, opcion = mas_probable(p)
    assert prob.tolist() == [0.6, 0.5] and opcion.tolist() == [0, 2]
    rng = np.random.default_rng(0)
    q = rng.uniform(0.6, 0.95, 20000)
    cal = calibracion_alta(q, (rng.random(20000) < q).astype(int))
    assert (cal["observado"] - cal["anunciado"]).abs().max() < 0.02
