"""Pruebas unitarias para la prueba preregistrada de presión (§E.4)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "ops"))
from prueba_presion import (
    agregar_por_jugador_temporada,
    calcular_residuos_partido,
    emparejar_temporadas_consecutivas,
)


def test_calcular_residuos_partido_sintetico():
    # Jugador 1 afronta 10 bp, salva 7; en total saca 60 ptos y gana 40
    # Fuera de bp: saca 50 ptos, gana 33 -> p_tilde = 33/50 = 0.66
    # residuo = 7 - 10 * 0.66 = 0.4
    df_saque = pd.DataFrame([
        {
            "partido_key": "P1",
            "lado": 1,
            "jugador_id": 101,
            "puntos_saque": 60,
            "puntos_saque_ganados": 40,
            "bp_salvados": 7,
            "bp_afrontados": 10,
        }
    ])
    df_partidos = pd.DataFrame([
        {"partido_key": "P1", "corte_utc": "2023-01-01", "circuito": "atp", "temporada": 2023}
    ])

    res = calcular_residuos_partido(df_saque, df_partidos, hasta_temporada=2024)
    assert len(res) == 1
    assert abs(res.iloc[0]["residuo"] - 0.4) < 1e-6


def test_emparejar_temporadas_consecutivas():
    df_ag = pd.DataFrame([
        {"circuito": "atp", "jugador_id": 1, "temporada": 2020, "bp_tot": 60, "res_std": 1.2},
        {"circuito": "atp", "jugador_id": 1, "temporada": 2021, "bp_tot": 70, "res_std": 0.8},
        {"circuito": "atp", "jugador_id": 1, "temporada": 2023, "bp_tot": 80, "res_std": -0.5},  # no consecutiva (salta 2022)
        {"circuito": "atp", "jugador_id": 2, "temporada": 2020, "bp_tot": 55, "res_std": -1.0},
    ])
    pares = emparejar_temporadas_consecutivas(df_ag)
    assert len(pares) == 1
    assert pares.iloc[0]["temporada"] == 2020
    assert pares.iloc[0]["temp_sig"] == 2021
    assert pares.iloc[0]["res_std"] == 1.2
    assert pares.iloc[0]["res_sig"] == 0.8
