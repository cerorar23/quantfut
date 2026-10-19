"""El diagnóstico de córners no se deja engañar por picks correlacionados ni por un modelo mal calibrado."""
import numpy as np
import pandas as pd
import pytest

from qf.eval import corners_diagnostico as cd


def test_prob_lado_suma_uno_y_crece_con_la_media():
    m = np.array([8.0, 10.0, 12.0])
    bajo, alto = cd.prob_lado(m, 10.5, "under"), cd.prob_lado(m, 10.5, "over")
    assert np.allclose(bajo + alto, 1.0)
    assert bajo[0] > bajo[1] > bajo[2]                    # más córners esperados, menos probable el «menos de»


def test_un_modelo_calibrado_sale_calibrado_en_la_tabla():
    rng = np.random.default_rng(0)
    media = rng.uniform(8.0, 12.0, 30000)
    phi = 1.175
    r = media / (phi - 1.0)
    real = rng.negative_binomial(r, r / (r + media))
    t = cd.tabla_calibracion(pd.DataFrame({"pred": media, "real": real}))
    assert len(t) >= 3 and t["dif"].abs().max() < 0.02


def test_un_modelo_con_la_media_corrida_se_nota():
    rng = np.random.default_rng(1)
    media = rng.uniform(8.0, 12.0, 30000)
    phi = 1.175
    r = (media + 1.0) / (phi - 1.0)                       # la realidad trae 1 córner más de lo que prevé el modelo
    real = rng.negative_binomial(r, r / (r + media + 1.0))
    t = cd.tabla_calibracion(pd.DataFrame({"pred": media, "real": real}))
    assert t[t["lado"] == "under"]["dif"].mean() < -0.03


def test_picks_del_mismo_partido_inflan_el_error_estandar():
    rng = np.random.default_rng(2)
    partidos = np.repeat(np.arange(150), 4)               # 4 picks por partido, 150 partidos
    gana_partido = rng.random(150) < 0.7
    ind = cd.error_estandar_por_partido(pd.Series(partidos), pd.Series(np.repeat(gana_partido, 4)))
    assert ind["picks"] == 600 and ind["partidos"] == 150
    assert ind["inflacion"] == pytest.approx(2.0, rel=0.15)   # perfectamente correlacionados: el doble de error
    indep = cd.error_estandar_por_partido(pd.Series(np.arange(600)), pd.Series(rng.random(600) < 0.7))
    assert indep["inflacion"] == pytest.approx(1.0, rel=0.15)  # independientes: igual que el binomial
