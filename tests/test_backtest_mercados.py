import numpy as np
import pandas as pd

from qf.eval import backtest_mercados as b


def _tabla(p, y, mercado="over_2.5", liga="x"):
    n = len(p)
    return pd.DataFrame({"liga": liga, "evento": range(n), "mercado": mercado, "seleccion": "over",
                         "prob": p, "resultado": y, "esperado": np.nan, "real": np.nan})


def test_wilson_inferior_de_casos_conocidos():
    assert abs(b.wilson_inferior(50, 100) - 0.4038) < 1e-3
    assert np.isnan(b.wilson_inferior(0, 0))
    assert b.wilson_inferior(100, 100) > 0.96


def test_el_complemento_de_un_over_bajo_es_un_under_alto():
    # p(over) = 0,2 -> el lado «menos de» tiene 0,8 y acierta cuando el over no ocurre
    t = _tabla([0.2] * 10, [0.0] * 8 + [1.0] * 2)
    a = b.alta_probabilidad(t, set())
    assert a["n_alta"] == 10 and abs(a["predicha"] - 0.8) < 1e-9 and abs(a["real"] - 0.8) < 1e-9
    assert a["mercados"][0]["lado"] == "complemento"


def test_promesa_incumplida_no_aprueba_y_cumplida_si():
    rng = np.random.default_rng(1)
    n = 400
    p = np.full(n, 0.80)
    bien = _tabla(p, (rng.random(n) < 0.80).astype(float))
    mal = _tabla(p, (rng.random(n) < 0.68).astype(float))
    assert b.veredicto_familia(b.alta_probabilidad(bien, set())) == "APRUEBA"
    assert b.veredicto_familia(b.alta_probabilidad(mal, set())) == "NO_APRUEBA"


def test_poca_muestra_no_se_aprueba_aunque_acierte_todo():
    a = b.alta_probabilidad(_tabla([0.9] * 40, [1.0] * 40), set())
    assert a["n_alta"] == 40 and b.veredicto_familia(a) == "SIN_MUESTRA"


def test_a2_saca_el_mercado_que_incumple_aunque_la_familia_pase():
    rng = np.random.default_rng(2)
    n = 300
    bueno = _tabla(np.full(n, 0.8), (rng.random(n) < 0.8).astype(float), "over_1.5")
    malo = _tabla(np.full(60, 0.8), (rng.random(60) < 0.6).astype(float), "btts")
    t = pd.concat([bueno, malo], ignore_index=True)
    a = b.alta_probabilidad(t, set())
    assert "btts|directo" in b.mercados_fuera(a) and "over_1.5|directo" not in b.mercados_fuera(a)


def test_los_mercados_excluyentes_no_generan_complemento():
    t = pd.DataFrame({"liga": "x", "evento": [1, 1, 1], "mercado": "1x2", "seleccion": ["home", "draw", "away"],
                      "prob": [0.8, 0.12, 0.08], "resultado": [1.0, 0.0, 0.0], "esperado": np.nan, "real": np.nan})
    s = b.lados(t, {"1x2"})
    assert len(s) == 3 and (s["lado"] == "directo").all()


def _por_partido(n_partidos, lineas, p, real, rng):
    """Cada partido aporta varias líneas con el MISMO desenlace (correlación total): el n real son los partidos."""
    filas = []
    for e in range(n_partidos):
        y = float(rng.random() < real)
        for k in range(lineas):
            filas.append({"liga": "x", "evento": e, "mercado": f"over_{k}", "seleccion": "over",
                          "prob": p, "resultado": y, "esperado": np.nan, "real": np.nan})
    return pd.DataFrame(filas)


def test_franja_detecta_la_sobrepromesa_y_no_marca_la_promesa_cumplida():
    rng = np.random.default_rng(5)
    mal = b.bandas(_por_partido(300, 5, 0.78, 0.66, rng), set())
    assert mal[0]["banda"] == "0.75-0.80" and mal[0]["estado"] == "SOBREPROMETE"
    bien = b.bandas(_por_partido(2500, 2, 0.78, 0.78, np.random.default_rng(6)), set())
    assert bien[0]["estado"] == "CUMPLE" and abs(bien[0]["promesa"]) < 0.03
    # con pocos partidos la misma calibración perfecta NO basta para aprobar: el intervalo no cabe en 0,05
    poca = b.bandas(_por_partido(150, 2, 0.78, 0.78, np.random.default_rng(6)), set())
    assert poca[0]["estado"] in ("INCIERTO", "CUMPLE")


def test_el_ic_por_partido_es_mas_ancho_que_el_de_lineas_independientes():
    # 100 partidos x 20 líneas iguales: Wilson por líneas daría ±0,02; por partidos es mucho mayor
    rng = np.random.default_rng(8)
    t = _por_partido(100, 20, 0.80, 0.80, rng)
    f = b.bandas(t, set())[1]
    assert (f["ic_sup"] - f["ic_inf"]) > 0.05 and f["partidos"] == 100 and f["lineas"] == 2000


def test_franjas_sin_muestra_no_se_aprueban():
    f = b.bandas(_por_partido(20, 3, 0.95, 0.95, np.random.default_rng(9)), set())
    assert f[3]["estado"] == "SIN_MUESTRA" and f[0]["lineas"] == 0


def test_gana_a_cero_suma_con_el_empate_a_cero_y_liquida_bien():
    oos = pd.DataFrame({"match_id": ["a", "b", "c"], "lam": [1.6, 1.6, 1.6], "mu": [1.1, 1.1, 1.1], "rho": [-0.03] * 3,
                        "home_goals": [2, 0, 1], "away_goals": [0, 0, 1]})
    t = b.gana_a_cero(oos)
    loc, vis = t[t["mercado"] == "gana_a_cero_local"], t[t["mercado"] == "gana_a_cero_visitante"]
    assert loc["resultado"].tolist() == [1.0, 0.0, 0.0] and vis["resultado"].tolist() == [0.0, 0.0, 0.0]
    assert ((loc["prob"] > 0) & (loc["prob"] < 0.5)).all()
    # P(local a cero) + P(visitante a cero) + P(0-0) + P(ambos marcan) = 1 (con la corrección tau): se comprueba el orden de magnitud
    assert 0.2 < float(loc["prob"].iloc[0]) + float(vis["prob"].iloc[0]) < 0.6
