"""Aplanado y liquidación de los mercados de goles para ModelEvaluator."""
import numpy as np
import pandas as pd
import pytest

from qf.eval.evaluacion_goles import MERCADOS_EXCLUYENTES, filas_goles, tabla_goles
from qf.eval.evaluador import ModelEvaluator


def _filas(gh, ga, lam=1.5, mu=1.2, rho=-0.05):
    return pd.DataFrame(filas_goles(1, lam, mu, rho, gh, ga))


def _una(df, mercado, seleccion=None):
    g = df[df["mercado"] == mercado]
    if seleccion is not None:
        g = g[g["seleccion"] == seleccion]
    assert len(g) == 1, (mercado, seleccion, len(g))
    return g.iloc[0]


def test_1x2_liquida_la_seleccion_que_ocurrio():
    df = _filas(2, 1)
    assert _una(df, "1x2", "home")["resultado"] == 1
    assert _una(df, "1x2", "draw")["resultado"] == 0
    assert _una(df, "1x2", "away")["resultado"] == 0


@pytest.mark.parametrize("gh,ga", [(0, 0), (2, 1), (1, 3), (9, 0), (5, 5)])
def test_excluyentes_suman_uno_y_un_solo_acierto(gh, ga):
    df = _filas(gh, ga)
    for mercado in MERCADOS_EXCLUYENTES:
        g = df[df["mercado"] == mercado]
        assert g["prob"].sum() == pytest.approx(1.0, abs=1e-9), mercado
        assert g["resultado"].sum() == 1, mercado


def test_marcador_fuera_del_top_va_a_otro():
    df = _filas(9, 0)
    assert _una(df, "marcador_exacto", "otro")["resultado"] == 1


def test_totales_por_linea():
    df = _filas(2, 1)
    assert _una(df, "over_2.5")["resultado"] == 1
    assert _una(df, "over_3.5")["resultado"] == 0
    assert _una(df, "local_over_1.5")["resultado"] == 1
    assert _una(df, "visitante_over_0.5")["resultado"] == 1
    assert _una(df, "visitante_over_1.5")["resultado"] == 0


def test_btts_y_doble_oportunidad():
    df = _filas(2, 0)
    assert _una(df, "btts")["resultado"] == 0
    assert _una(df, "doble_oportunidad", "1X")["resultado"] == 1
    assert _una(df, "doble_oportunidad", "X2")["resultado"] == 0


def test_hcp_linea_entera_con_push_se_anula():
    assert np.isnan(_una(_filas(2, 1), "ah_-1.0")["resultado"])  # dif 1: devuelve
    assert _una(_filas(3, 1), "ah_-1.0")["resultado"] == 1


def test_hcp_cuarto_de_linea_reparte_el_resultado():
    assert _una(_filas(1, 1), "ah_-0.25")["resultado"] == 0   # media pierde, media devuelve
    assert _una(_filas(1, 1), "ah_0.25")["resultado"] == 1    # media gana, media devuelve
    assert _una(_filas(2, 1), "ah_-0.75")["resultado"] == 1   # media devuelve, media gana
    assert _una(_filas(1, 1), "ah_-0.75")["resultado"] == 0   # pierde las dos mitades


def test_filas_de_rmse_con_goles_esperados_y_reales():
    df = _filas(2, 1, lam=1.5, mu=1.2)
    t = _una(df, "goles_total")
    assert t["esperado"] == pytest.approx(2.7) and t["real"] == 3
    assert np.isnan(t["prob"])
    assert _una(df, "goles_local")["real"] == 2
    assert _una(df, "goles_visitante")["esperado"] == pytest.approx(1.2)


def test_tabla_goles_y_evaluador_de_punta_a_punta():
    partidos = pd.DataFrame({
        "evento": [1, 2], "lam": [1.5, 1.1], "mu": [1.1, 1.0], "rho": [-0.05, -0.05],
        "goles_local": [2, 0], "goles_visitante": [1, 0]})
    res = ModelEvaluator(tabla_goles(partidos),
                         mercados_excluyentes=MERCADOS_EXCLUYENTES).evaluar()
    assert res.loc["1x2", "n"] == 2
    assert res.loc["over_2.5", "n"] == 2
    assert np.isfinite(res.loc["goles_total", "rmse"])


def test_modelo_sobre_datos_simulados_de_si_mismo_esta_calibrado():
    rng = np.random.default_rng(7)
    n = 2500
    lam = rng.uniform(0.8, 2.2, n)
    mu = rng.uniform(0.6, 1.8, n)
    partidos = pd.DataFrame({
        "evento": range(n), "lam": lam, "mu": mu, "rho": 0.0,
        "goles_local": rng.poisson(lam), "goles_visitante": rng.poisson(mu)})
    t = tabla_goles(partidos)
    for mercado in ("over_2.5", "btts", "ah_-0.5"):
        g = t[t["mercado"] == mercado]
        assert abs(g["prob"].mean() - g["resultado"].mean()) < 0.03, mercado
    rmse = ModelEvaluator(t).evaluar().loc["goles_total", "rmse"]
    assert rmse == pytest.approx(np.sqrt((lam + mu).mean()), rel=0.05)  # sd de Poisson suma
