"""Pruebas ABSURDAS del modelo (plan K.2 S3): deben rechazarse o comportarse en el límite."""
import math

import numpy as np
import pandas as pd
import pytest

from tenis.modelo import datos as dm
from tenis.modelo import estado as est
from tenis.modelo.fatiga import DIA_NS, fatiga, termino
from tenis.modelo.parametros import Psi, softplus
from tenis.modelo.rating import filtrar
from tenis.modelo.sintetico import mundo, psi_prueba, tablas_prueba
from tenis.modelo.union import unir


def correr(p, e, psi=None):
    d = dm.preparar(p, e, "atp", 2030)
    return d, filtrar(d, psi or psi_prueba(), tablas_prueba())


def test_jugador_sin_historia_ni_ranking_no_se_pronostica_ni_actualiza():
    p, e = mundo(semilla=1)
    clave = p.partido_key.iloc[0]
    p.loc[p.partido_key == clave, "rank_1"] = np.nan          # jugador nuevo (semana 0) sin ranking
    d, s = correr(p, e)
    i = int(np.flatnonzero(d.p.partido_key == clave)[0])
    assert s.motivo[i] == "sin_historia_ni_ranking" and math.isnan(s.pi[i])
    # su resultado no movió a nadie: igual que si el partido no existiera
    d2, s2 = correr(p[p.partido_key != clave], e[e.partido_key != clave])
    resto = d.p.partido_key != clave
    np.testing.assert_allclose(s.pi[resto.to_numpy()], s2.pi, rtol=0, atol=0, equal_nan=True)
    assert (pd.Series(s.motivo).value_counts().get("sin_historia_ni_ranking", 0)) >= 1


def test_tres_anios_de_inactividad_dan_mas_varianza():
    psi = psi_prueba()
    v = [[0.01 if i == j else 0.0 for j in range(5)] for i in range(5)]
    corto = est.var_dir(v, 30 * DIA_NS, psi, 1.0, 2)
    largo = est.var_dir(v, 3 * 365 * DIA_NS, psi, 1.0, 2)
    sin_inact = est.var_dir(v, 3 * 365 * DIA_NS, psi_prueba(tau_inact=0.0), 1.0, 2)
    assert largo > sin_inact > corto


def test_diferencia_de_theta_enorme_da_pi_en_el_intervalo_abierto():
    tab = tablas_prueba()[(0, 2)]
    for rho in (-1e9, -50.0, -3.0, 3.0, 50.0, 1e9):
        for v in (0.0, 0.05, 5.0, 1e6):
            pi = tab.prob(rho, v)
            assert 0.0 < pi < 1.0 and math.isfinite(pi)
    p, e = mundo(semilla=2)
    p["rank_1"], p["rank_2"] = 1.0, 1e9                     # prior absurdo por ranking
    _, s = correr(p, e, psi_prueba(b_rank=-50.0))
    ok = np.isfinite(s.pi)
    assert ok.any() and np.all((s.pi[ok] > 0) & (s.pi[ok] < 1))


def test_fatiga_cero_no_tiene_efecto():
    assert termino(0.0, 0.0, (5.0, 9.0), 100.0) == 0.0
    assert fatiga([], 10**18, 0.75) == 0.0
    p, e = mundo(semilla=3)                                   # semanas separadas: F = 0 siempre
    _, s1 = correr(p, e, psi_prueba(phi=(0.0, 0.0)))
    _, s2 = correr(p, e, psi_prueba(phi=(3.0, 7.0)))
    np.testing.assert_array_equal(s1.pi, s2.pi)
    assert np.nanmax(np.r_[s1.f1, s1.f2]) == 0.0


def test_phi_negativo_imposible():
    with pytest.raises(ValueError):
        psi_prueba(phi=(-0.01, 0.0))
    with pytest.raises(ValueError):
        termino(10.0, 0.0, (-1.0, 0.0), 0.0)
    assert all(softplus(u) >= 0.0 for u in np.linspace(-800, 800, 401))


def test_walkover_y_retirada_no_actualizan_el_rating():
    p, e = mundo(semilla=4)
    claves = p.partido_key.iloc[[0, 5]].tolist()
    e2 = e.copy()
    e2.loc[e2.partido_key == claves[0], ["estado", "actualiza_rating", "minutos_1", "minutos_2"]] = ["walkover", False, np.nan, np.nan]
    e2.loc[e2.partido_key == claves[1], ["estado", "actualiza_rating"]] = ["retirada", False]
    d, s = correr(p, e2)
    # igual que un mundo en el que esos dos resultados nunca llegaron
    _, s_sin = correr(p, e[~e.partido_key.isin(claves)])
    np.testing.assert_allclose(s.pi, s_sin.pi, rtol=0, atol=0, equal_nan=True)


def test_minutos_faltantes_dan_fatiga_desconocida_y_no_cero():
    corte = 10 * DIA_NS
    assert fatiga([(corte - DIA_NS, float("nan"), False)], corte, 0.75) is None
    assert fatiga([(corte - DIA_NS, float("nan"), True)], corte, 0.75) == 0.0          # walkover: 0 conocido
    assert fatiga([(corte - 5 * DIA_NS, float("nan"), False)], corte, 0.75) == 0.0     # fuera de las 96 h
    p, e = mundo(semilla=5)
    # el jugador del primer partido de la semana 1 juega un previo (sin minutos) 1 día antes de su corte
    fila = p[p.partido_key.str.startswith("X001")].iloc[0]
    previo = e.iloc[[0]].copy()
    previo["partido_key"], previo["jugador_1"], previo["minutos_1"], previo["minutos_2"] = "PREVIO", fila.jugador_1, np.nan, np.nan
    previo["visible_resultado_utc"] = fila.corte_utc - pd.Timedelta(days=1)
    previo["jugador_2"] = 99999
    d, s = correr(p, pd.concat([e, previo], ignore_index=True))
    i = int(np.flatnonzero(d.p.partido_key == fila.partido_key)[0])
    assert s.fat_desc[i] and math.isnan(s.f1[i])


def test_formato_desconocido_no_se_pronostica():
    p, e = mundo(semilla=6)
    clave = p.partido_key.iloc[3]
    p.loc[p.partido_key == clave, "formato_decisivo"] = "desconocido"
    d, s = correr(p, e)
    i = int(np.flatnonzero(d.p.partido_key == clave)[0])
    assert s.motivo[i] == "formato_desconocido" and math.isnan(s.pi[i])
    assert dm.indice_formato(4, "tiebreak_7") == -1 and dm.indice_formato(3, "supertiebreak_10") == -1
    with pytest.raises(ValueError):
        unir(1.25, 0.6, -1, 0.22, -0.45, 0.01)


def test_id_de_jugador_no_es_un_rasgo():
    """Renumerar los ids (invirtiendo su orden) no cambia NINGUNA probabilidad: el id es solo una clave."""
    p, e = mundo(semilla=7)
    _, s = correr(p, e)
    mapa = {i: 10**6 - 3 * i for i in np.unique(np.r_[p.jugador_1, p.jugador_2])}
    p2, e2 = p.copy(), e.copy()
    for df in (p2, e2):
        df["jugador_1"], df["jugador_2"] = df.jugador_1.map(mapa), df.jugador_2.map(mapa)
    _, s2 = correr(p2, e2)
    np.testing.assert_array_equal(s.pi, s2.pi)


def test_psi_rechaza_valores_absurdos():
    with pytest.raises(ValueError):
        psi_prueba(kappa=(1.0, 1.0, 1.2, 1.0))                 # κ_Hard ≠ 1
    with pytest.raises(ValueError):
        psi_prueba(tau_theta=-0.1)
    with pytest.raises(ValueError):
        psi_prueba(lam=0.0)
    assert isinstance(psi_prueba(), Psi)
