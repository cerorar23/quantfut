"""Aplanado y liquidación de los mercados de primera mitad para ModelEvaluator."""
import numpy as np
import pandas as pd
import pytest

from qf.eval.evaluacion_primer_tiempo import (MERCADOS_EXCLUYENTES_1T, filas_primer_tiempo,
                                              tabla_primer_tiempo)
from qf.eval.evaluador import ModelEvaluator
from qf.model.primer_tiempo import PROPORCION_1T, probs


def _f(h, a, lam=1.5, mu=1.2):
    return pd.DataFrame(filas_primer_tiempo(1, lam, mu, h, a))


def _res(df, mercado, seleccion=None):
    g = df[df["mercado"] == mercado]
    if seleccion is not None:
        g = g[g["seleccion"] == seleccion]
    assert len(g) == 1
    return g.iloc[0]["resultado"]


def test_liquidacion_un_gol_del_local():
    df = _f(1, 0)
    assert _res(df, "gol_1t_si") == 1 and _res(df, "ambos_1t_si") == 0
    assert _res(df, "mas_1_5_1t") == 0
    assert _res(df, "ganador_1t", "local") == 1 and _res(df, "ganador_1t", "empate") == 0


def test_liquidacion_empate_con_goles():
    df = _f(1, 1)
    assert _res(df, "ambos_1t_si") == 1 and _res(df, "mas_1_5_1t") == 1
    assert _res(df, "ganador_1t", "empate") == 1


def test_liquidacion_cero_a_cero():
    df = _f(0, 0)
    assert _res(df, "gol_1t_si") == 0 and _res(df, "mas_1_5_1t") == 0
    assert _res(df, "ganador_1t", "empate") == 1


def test_ganador_suma_uno_y_coincide_con_el_modelo():
    df = _f(0, 2)
    g = df[df["mercado"] == "ganador_1t"]
    assert g["prob"].sum() == pytest.approx(1.0) and g["resultado"].sum() == 1
    esperado = probs(1.5, 1.2)
    assert _res(df, "ganador_1t", "visita") == 1
    assert df[df["mercado"] == "gol_1t_si"].iloc[0]["prob"] == pytest.approx(esperado["gol_1t_si"])
    assert (df[(df["mercado"] == "ganador_1t") & (df["seleccion"] == "local")].iloc[0]["prob"]
            == pytest.approx(esperado["ganador_1t_local"]))


def test_filas_rmse_con_goles_esperados_de_1t():
    df = _f(1, 0, lam=2.0, mu=1.0)
    t = df[df["mercado"] == "goles_1t_total"].iloc[0]
    assert t["esperado"] == pytest.approx(PROPORCION_1T[0] * 2.0 + PROPORCION_1T[1] * 1.0)
    assert t["real"] == 1 and np.isnan(t["prob"])
    assert df[df["mercado"] == "goles_1t_local"].iloc[0]["esperado"] == pytest.approx(PROPORCION_1T[0] * 2.0)


def test_partido_sin_marcador_de_1t_se_omite():
    p = pd.DataFrame({"evento": [1, 2], "lam": [1.5, 1.5], "mu": [1.2, 1.2],
                      "goles_1t_local": [1, np.nan], "goles_1t_visitante": [0, np.nan]})
    t = tabla_primer_tiempo(p)
    assert set(t["evento"]) == {1} and t.attrs["cobertura"]["sin_dato"] == 1


def test_calibrado_sobre_datos_generados_por_el_mismo_proceso_y_evaluador():
    rng = np.random.default_rng(2)
    n = 3000
    lam, mu = rng.uniform(0.9, 2.2, n), rng.uniform(0.7, 1.9, n)
    p = pd.DataFrame({"evento": range(n), "lam": lam, "mu": mu,
                      "goles_1t_local": rng.poisson(PROPORCION_1T[0] * lam),
                      "goles_1t_visitante": rng.poisson(PROPORCION_1T[1] * mu)})
    t = tabla_primer_tiempo(p)
    for m in ("gol_1t_si", "ambos_1t_si", "mas_1_5_1t"):
        g = t[t["mercado"] == m]
        assert abs(g["prob"].mean() - g["resultado"].mean()) < 0.03, m
    res = ModelEvaluator(t, mercados_excluyentes=MERCADOS_EXCLUYENTES_1T).evaluar()
    assert res.loc["ganador_1t", "n"] == n and np.isfinite(res.loc["goles_1t_total", "rmse"])
