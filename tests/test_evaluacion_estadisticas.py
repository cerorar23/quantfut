"""Aplanado y liquidación de córners (punto en el tiempo) para ModelEvaluator."""
import numpy as np
import pandas as pd
import pytest

from qf.eval.evaluacion_estadisticas import tabla_estadistica
from qf.eval.evaluador import ModelEvaluator


def _liga(n=240, seed=3, media_local=5.5, media_visit=4.5):
    rng = np.random.default_rng(seed)
    equipos = [f"E{i}" for i in range(8)]
    filas = []
    for k in range(n):
        h, a = rng.choice(len(equipos), 2, replace=False)
        filas.append({
            "evento": k,
            "fecha": pd.Timestamp("2022-01-01", tz="UTC") + pd.Timedelta(days=k // 4),
            "local": equipos[h], "visitante": equipos[a],
            "valor_local": int(rng.poisson(media_local)),
            "valor_visit": int(rng.poisson(media_visit))})
    return pd.DataFrame(filas)


def test_no_hay_prediccion_antes_del_calentamiento():
    t = tabla_estadistica(_liga())
    ids = set(t["evento"])
    assert 0 not in ids and 5 not in ids        # sin historial suficiente
    assert max(ids) > 200                        # y sí hacia el final


def test_liquidacion_over_y_filas_rmse():
    liga = _liga()
    t = tabla_estadistica(liga)
    ev = int(t["evento"].iloc[-1])
    real = liga.loc[liga["evento"] == ev].iloc[0]
    total = real["valor_local"] + real["valor_visit"]
    fila = t[(t["evento"] == ev) & (t["mercado"] == "corners_over_9.5")].iloc[0]
    assert fila["resultado"] == float(total > 9.5)
    rm = t[(t["evento"] == ev) & (t["mercado"] == "corners_total")].iloc[0]
    assert rm["real"] == total and rm["esperado"] > 0 and np.isnan(rm["prob"])
    loc = t[(t["evento"] == ev) & (t["mercado"] == "corners_local_over_4.5")].iloc[0]
    assert loc["resultado"] == float(real["valor_local"] > 4.5)


def test_punto_en_el_tiempo_ni_el_propio_resultado_ni_el_futuro_mueven_la_prediccion():
    liga = _liga()
    base = tabla_estadistica(liga)
    ev = int(base["evento"].iloc[-1])
    alterada = liga.copy()
    alterada.loc[alterada["evento"] == ev, ["valor_local", "valor_visit"]] = [30, 30]
    nueva = tabla_estadistica(alterada)
    a = base[base["evento"] == ev].set_index(["mercado", "seleccion"])["prob"]
    b = nueva[nueva["evento"] == ev].set_index(["mercado", "seleccion"])["prob"]
    pd.testing.assert_series_equal(a, b)  # el propio resultado no entra
    # y un partido posterior no cambia las predicciones anteriores
    corte = liga[liga["evento"] < ev]
    previo = tabla_estadistica(corte)
    comun = base[base["evento"] < ev].reset_index(drop=True)
    pd.testing.assert_frame_equal(comun[["evento", "mercado", "prob"]],
                                  previo[["evento", "mercado", "prob"]])


def test_desde_solo_recorta_lo_que_se_emite_no_lo_que_se_aprende():
    liga = _liga()
    todo = tabla_estadistica(liga)
    corte = pd.Timestamp("2022-02-15", tz="UTC")
    recortado = tabla_estadistica(liga, desde=corte)
    ids = set(recortado["evento"])
    assert ids and ids < set(todo["evento"])
    a = todo[todo["evento"].isin(ids)].reset_index(drop=True)
    pd.testing.assert_frame_equal(a[["evento", "mercado", "prob"]],
                                  recortado[["evento", "mercado", "prob"]])


def test_partido_sin_dato_de_corners_se_omite_sin_romper():
    liga = _liga()
    liga.loc[liga["evento"] == 100, ["valor_local", "valor_visit"]] = np.nan
    t = tabla_estadistica(liga)
    assert 100 not in set(t["evento"])
    assert t.attrs["cobertura"]["sin_dato"] == 1


def test_calibracion_sobre_datos_generados_por_el_mismo_proceso():
    liga = _liga(n=1500, seed=11, media_local=5.2, media_visit=4.8)
    t = tabla_estadistica(liga)
    g = t[t["mercado"] == "corners_over_9.5"]
    assert abs(g["prob"].mean() - g["resultado"].mean()) < 0.05
    res = ModelEvaluator(t).evaluar()
    assert res.loc["corners_total", "rmse"] == pytest.approx(np.sqrt(10.0), rel=0.1)


# --- tarjetas: solo total (el modelo no tiene mercados de tarjetas por equipo) -------------
def _liga_tarjetas(n=600, seed=5):
    liga = _liga(n=n, seed=seed, media_local=2.0, media_visit=2.0)
    rng = np.random.default_rng(seed + 1)
    arbitros = np.where(np.arange(n) % 5 == 0, "R1", np.where(np.arange(n) % 2 == 0, "R2", "R3"))
    liga["arbitro"] = arbitros
    duros = liga["arbitro"] == "R1"
    liga.loc[duros, "valor_local"] = rng.poisson(4.5, duros.sum())
    liga.loc[duros, "valor_visit"] = rng.poisson(4.5, duros.sum())
    return liga


def test_tarjetas_emite_total_y_rmse_pero_no_lineas_por_equipo():
    t = tabla_estadistica(_liga_tarjetas(), mercado="cards")
    m = set(t["mercado"])
    assert "cards_over_4.5" in m and "cards_total" in m and "cards_local" in m
    assert not any(x.startswith(("cards_local_over", "cards_visitante_over")) for x in m)


def test_tarjetas_el_arbitro_duro_sube_la_media_esperada():
    liga = _liga_tarjetas()
    con = tabla_estadistica(liga, mercado="cards")
    sin = tabla_estadistica(liga.drop(columns="arbitro"), mercado="cards")
    esp = lambda t: t[t["mercado"] == "cards_total"].set_index("evento")["esperado"]  # noqa: E731
    duros = set(liga.loc[liga["arbitro"] == "R1", "evento"])
    e_con, e_sin = esp(con), esp(sin)
    ev_duros = [e for e in e_con.index if e in duros and e > 400]
    ev_resto = [e for e in e_con.index if e not in duros and e > 400]
    assert e_con[ev_duros].mean() > 1.25 * e_con[ev_resto].mean()
    assert e_sin[ev_duros].mean() < 1.1 * e_sin[ev_resto].mean()


def test_tarjetas_punto_en_el_tiempo_con_arbitro():
    liga = _liga_tarjetas()
    base = tabla_estadistica(liga, mercado="cards")
    ev = int(base["evento"].iloc[-1])
    alt = liga.copy()
    alt.loc[alt["evento"] == ev, ["valor_local", "valor_visit"]] = [20, 20]
    nueva = tabla_estadistica(alt, mercado="cards")
    pd.testing.assert_series_equal(
        base[base["evento"] == ev].set_index("mercado")["prob"],
        nueva[nueva["evento"] == ev].set_index("mercado")["prob"])
