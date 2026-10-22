"""
Córners de cada equipo repartidos por la supremacía del Motor A (2026-10-22).

El favorito saca más córners; el modelo anterior lo ignoraba. Lo que estas
pruebas fijan: la dirección y el tamaño del efecto, que el total no cambia, que
sin supremacía todo queda como antes y que la supremacía sale solo del modelo
propio y solo si conoce a los dos equipos.
"""
from __future__ import annotations

import math

import pytest

from qf.model import estadisticas_mercado as em
from qf.publish import escalera_datos as ed

LAM = (5.2, 4.3)


def test_sin_supremacia_nada_cambia():
    for mercado, lado, linea in (("corners_home", "over", 3.5), ("corners_away", "under", 4.5)):
        base = em.prob_total(LAM[0] if mercado == "corners_home" else LAM[1],
                             em.PARAMETROS["corners_equipo"]["phi"], linea)[lado]
        assert em.prob(mercado, LAM, lado, linea) == pytest.approx(base)
        assert em.prob(mercado, LAM, lado, linea, None) == pytest.approx(base)


def test_el_favorito_saca_mas_corners_y_el_rival_menos():
    fuerte = math.log(2.4 / 0.7)          # local muy favorito
    assert em.media_equipo("corners_home", LAM, fuerte) > LAM[0]
    assert em.media_equipo("corners_away", LAM, fuerte) < LAM[1]
    debil = -fuerte
    assert em.media_equipo("corners_home", LAM, debil) < LAM[0]
    assert em.media_equipo("corners_away", LAM, debil) > LAM[1]
    # Tamaño: con s = log(2,4/0,7) ≈ 1,23 el local sube del orden de un 25 %.
    assert 1.15 < em.media_equipo("corners_home", LAM, fuerte) / LAM[0] < 1.35


def test_la_probabilidad_sigue_a_la_media():
    s = math.log(2.0 / 0.9)
    assert em.prob("corners_home", LAM, "over", 4.5, s) > em.prob("corners_home", LAM, "over", 4.5, 0.0)
    assert em.prob("corners_away", LAM, "under", 4.5, s) > em.prob("corners_away", LAM, "under", 4.5, 0.0)


def test_el_total_no_cambia_con_la_supremacia():
    for s in (None, -1.0, 0.0, 1.3):
        assert em.prob("corners", LAM, "under", 11.5, s) == pytest.approx(em.prob("corners", LAM, "under", 11.5))


def test_visitante_mas_de_3_5_y_4_5_fuera_de_las_lineas():
    assert ("over", 3.5) not in em.LINEAS_HABILITADAS["corners_away"]
    assert ("over", 4.5) not in em.LINEAS_HABILITADAS["corners_away"]


def test_la_supremacia_sale_del_modelo_propio(monkeypatch):
    monkeypatch.setattr(ed, "query_one", lambda sql, p: {"home_lambda": 2.0, "away_lambda": 0.8, "conocido": "true"})
    assert ed.supremacia_modelo("m1") == pytest.approx(math.log(2.0 / 0.8))
    # Equipo desconocido: no hay contexto, se usa el reparto anterior.
    monkeypatch.setattr(ed, "query_one", lambda sql, p: {"home_lambda": 0.3, "away_lambda": 3.0, "conocido": "false"})
    assert ed.supremacia_modelo("m1") is None
    monkeypatch.setattr(ed, "query_one", lambda sql, p: None)
    assert ed.supremacia_modelo("m1") is None
    monkeypatch.setattr(ed, "query_one", lambda sql, p: {"home_lambda": 0, "away_lambda": 1.0, "conocido": None})
    assert ed.supremacia_modelo("m1") is None
