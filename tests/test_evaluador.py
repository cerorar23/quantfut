"""ModelEvaluator: métricas de precisión pura por mercado (sin ROI ni cuotas)."""
import math

import numpy as np
import pandas as pd
import pytest

from qf.eval.evaluador import ModelEvaluator


def _df():
    return pd.DataFrame({
        "mercado": ["over25"] * 4,
        "prob": [0.8, 0.6, 0.3, 0.1],
        "resultado": [1, 0, 0, 0],
    })


def test_brier_binario_calculo_manual():
    res = ModelEvaluator(_df()).evaluar()
    esperado = np.mean([(0.8 - 1) ** 2, 0.6 ** 2, 0.3 ** 2, 0.1 ** 2])
    assert res.loc["over25", "brier"] == pytest.approx(esperado)


def test_log_loss_binario_calculo_manual():
    res = ModelEvaluator(_df()).evaluar()
    esperado = -np.mean([math.log(0.8), math.log(0.4), math.log(0.7), math.log(0.9)])
    assert res.loc["over25", "log_loss"] == pytest.approx(esperado)


def test_log_loss_penaliza_99_que_falla_sin_infinito():
    df = pd.DataFrame({"mercado": ["m"], "prob": [1.0], "resultado": [0]})
    ll = ModelEvaluator(df).evaluar().loc["m", "log_loss"]
    assert np.isfinite(ll) and ll > 20  # el recorte EPS evita inf pero castiga fuerte


def test_accuracy_umbral_medio():
    res = ModelEvaluator(_df()).evaluar()
    # predice 1,1,0,0 contra 1,0,0,0 -> 3/4
    assert res.loc["over25", "accuracy"] == pytest.approx(0.75)


def test_metricas_por_mercado_independientes():
    df = pd.concat([_df(), pd.DataFrame({
        "mercado": ["btts"] * 2, "prob": [0.9, 0.2], "resultado": [1, 0]})])
    res = ModelEvaluator(df).evaluar()
    assert set(res.index) == {"over25", "btts"}
    assert res.loc["btts", "n"] == 2
    assert res.loc["btts", "accuracy"] == 1.0


def test_rmse_goles_solo_donde_hay_valor_real():
    df = pd.DataFrame({
        "mercado": ["goles_total"] * 3 + ["over25"],
        "prob": [np.nan, np.nan, np.nan, 0.5],
        "resultado": [np.nan, np.nan, np.nan, 1],
        "esperado": [2.0, 3.0, 1.0, np.nan],
        "real": [3, 3, 3, np.nan],
    })
    res = ModelEvaluator(df).evaluar()
    assert res.loc["goles_total", "rmse"] == pytest.approx(math.sqrt((1 + 0 + 4) / 3))
    assert np.isnan(res.loc["goles_total", "brier"])
    assert np.isnan(res.loc["over25", "rmse"])


def test_accuracy_1x2_por_argmax_de_cada_evento():
    df = pd.DataFrame({
        "evento": [1, 1, 1, 2, 2, 2],
        "mercado": ["1x2"] * 6,
        "seleccion": ["H", "D", "A"] * 2,
        "prob": [0.5, 0.3, 0.2, 0.2, 0.3, 0.5],
        "resultado": [1, 0, 0, 0, 1, 0],
    })
    res = ModelEvaluator(df, mercados_excluyentes={"1x2"}).evaluar()
    assert res.loc["1x2", "accuracy"] == pytest.approx(0.5)  # acierta evento 1, falla 2
    assert res.loc["1x2", "n"] == 2  # eventos, no filas


def test_columnas_faltantes_error_claro():
    with pytest.raises(ValueError, match="mercado"):
        ModelEvaluator(pd.DataFrame({"prob": [0.5], "resultado": [1]}))


def test_probabilidad_fuera_de_rango_error():
    df = pd.DataFrame({"mercado": ["m"], "prob": [1.2], "resultado": [1]})
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        ModelEvaluator(df)


def test_resumen_global_pondera_por_filas():
    r = ModelEvaluator(_df()).resumen()
    assert r["n"] == 4 and "brier" in r and "log_loss" in r


# --- línea base de frecuencia, skill, RMSE base y tramos --------------------------------
def test_binario_linea_base_de_frecuencia_y_skill():
    res = ModelEvaluator(_df()).evaluar().loc["over25"]       # y = 1,0,0,0 -> tasa 0,25
    assert res["tasa_real"] == pytest.approx(0.25)
    assert res["prob_media"] == pytest.approx(np.mean([0.8, 0.6, 0.3, 0.1]))
    assert res["brier_base"] == pytest.approx(0.25 * 0.75)
    assert res["log_loss_base"] == pytest.approx(-(0.25 * math.log(0.25) + 0.75 * math.log(0.75)))
    assert res["accuracy_base"] == pytest.approx(0.75)         # siempre «no»
    assert res["brier_skill"] == pytest.approx(1 - res["brier"] / res["brier_base"])
    assert res["log_loss_skill"] == pytest.approx(1 - res["log_loss"] / res["log_loss_base"])


def test_excluyente_linea_base_multiclase():
    # 4 eventos: H, H, D, A -> frecuencias 0,5 / 0,25 / 0,25
    filas = []
    for ev, real in enumerate(["H", "H", "D", "A"]):
        for sel, p in (("H", 0.5), ("D", 0.25), ("A", 0.25)):
            filas.append({"evento": ev, "mercado": "1x2", "seleccion": sel, "prob": p,
                          "resultado": float(sel == real)})
    r = ModelEvaluator(pd.DataFrame(filas), mercados_excluyentes={"1x2"}).evaluar().loc["1x2"]
    assert r["brier_base"] == pytest.approx(1 - (0.25 + 0.0625 + 0.0625))
    assert r["log_loss_base"] == pytest.approx(-(0.5 * math.log(0.5) + 2 * 0.25 * math.log(0.25)))
    assert r["accuracy_base"] == pytest.approx(0.5)
    assert r["brier_skill"] == pytest.approx(0.0, abs=1e-12)   # el modelo ES la frecuencia


def test_excluyente_con_selecciones_variables_no_inventa_linea_base():
    filas = [
        {"evento": 1, "mercado": "mx", "seleccion": "a", "prob": 0.6, "resultado": 1.0},
        {"evento": 1, "mercado": "mx", "seleccion": "otro", "prob": 0.4, "resultado": 0.0},
        {"evento": 2, "mercado": "mx", "seleccion": "b", "prob": 0.7, "resultado": 0.0},
        {"evento": 2, "mercado": "mx", "seleccion": "otro", "prob": 0.3, "resultado": 1.0},
    ]
    r = ModelEvaluator(pd.DataFrame(filas), mercados_excluyentes={"mx"}).evaluar().loc["mx"]
    assert np.isnan(r["brier_base"]) and np.isnan(r["brier_skill"])


def test_rmse_base_es_la_desviacion_de_la_serie():
    df = pd.DataFrame({"mercado": ["g"] * 4, "prob": np.nan, "resultado": np.nan,
                       "esperado": [2.0, 2.0, 2.0, 2.0], "real": [0.0, 2.0, 2.0, 4.0]})
    r = ModelEvaluator(df).evaluar().loc["g"]
    assert r["rmse_base"] == pytest.approx(math.sqrt(2.0))      # std poblacional de la serie
    assert r["rmse_skill"] == pytest.approx(1 - r["rmse"] / r["rmse_base"])


def test_tramos_separan_por_fecha_y_no_mezclan():
    df = _df().assign(fecha=pd.to_datetime(["2022-10-01", "2023-01-01", "2025-08-01", "2026-01-01"], utc=True))
    out = ModelEvaluator(df).evaluar_tramos({
        "viejo": (None, pd.Timestamp("2025-07-01", tz="UTC")),
        "limpio": (pd.Timestamp("2025-07-01", tz="UTC"), None)})
    assert out["viejo"].loc["over25", "n"] == 2 and out["limpio"].loc["over25", "n"] == 2
    assert out["limpio"].loc["over25", "brier"] == pytest.approx(np.mean([0.3 ** 2, 0.1 ** 2]))


def test_tramos_exige_columna_fecha():
    with pytest.raises(ValueError, match="fecha"):
        ModelEvaluator(_df()).evaluar_tramos({"a": (None, None)})
