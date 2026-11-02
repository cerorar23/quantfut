"""Archivo de BetsAPI: líneas asiáticas (incluidas las de cuarto), emparejamiento y carrera de córners."""
import numpy as np
import pandas as pd
import pytest

from qf.eval import rediseno_betsapi as B


def test_lineas_y_liquidacion_de_cuarto():
    assert B.lineas("9.5,10") == [9.5, 10.0] and B.lineas("2.5") == [2.5] and B.lineas(None) == []
    assert B.liquidar_total(11, [9.5, 10.0], "mas") == "gana"
    assert B.liquidar_total(10, [9.5, 10.0], "mas") == "devuelve"  # media apuesta ganada, media devuelta
    assert B.liquidar_total(9, [9.5, 10.0], "mas") == "pierde"
    assert B.liquidar_total(9, [9.5, 10.0], "menos") == "gana"
    assert B.liquidar_total(2, [2.0], "menos") == "devuelve"


def test_handicap_del_local_y_del_visitante():
    assert B.liquidar_handicap(2, [-1.5], "home") == "gana"
    assert B.liquidar_handicap(1, [-1.5], "away") == "gana"  # el visitante tiene +1,5
    assert B.liquidar_handicap(1, [-1.0], "home") == "devuelve"
    assert B.liquidar_handicap(1, [-0.5, -1.0], "home") == "devuelve"  # gana la media de −0,5, devuelve la de −1
    assert B.liquidar_handicap(0, [-0.5, -1.0], "home") == "pierde"


def test_probabilidades_de_linea_con_distribucion():
    pmf = np.array([0.1, 0.2, 0.3, 0.2, 0.2])
    assert B.p_total(pmf, [2.5], "mas") == pytest.approx(0.4)
    assert B.p_total(pmf, [2.0, 2.5], "mas") == pytest.approx(0.4)  # gana todo solo si supera 2,5
    dif = np.array([0.2, 0.5, 0.3]); sop = np.array([-1, 0, 1])
    assert B.p_handicap(dif, sop, [-0.5], "home") == pytest.approx(0.3)
    assert B.p_handicap(dif, sop, [-0.5], "away") == pytest.approx(0.7)


def test_emparejar_por_hora_marcador_y_nombres():
    partidos = pd.DataFrame({"match_id": ["a", "b"], "league_id": ["gb.premier_league"] * 2,
                             "kickoff_utc": pd.to_datetime(["2025-08-16 14:00", "2025-08-16 14:00"], utc=True),
                             "home_name": ["Manchester City", "Wolverhampton Wanderers"], "away_name": ["Tottenham", "Brighton"],
                             "home_goals": [0, 0], "away_goals": [0, 0]})
    ev = pd.DataFrame({"bid": [1], "liga": ["gb_premier_league"], "kickoff": [int(pd.Timestamp("2025-08-16 14:00", tz="UTC").timestamp())],
                       "home": ["Man City"], "away": ["Tottenham"], "gl_h": [0.0], "gl_a": [0.0]})
    p = B.emparejar(ev, partidos)
    assert p.loc[0, "match_id"] == "a" and p.loc[0, "con_marcador"]


def test_instantaneas_usan_solo_cuotas_prepartido_con_antelacion():
    tk = pd.DataFrame({"bid": [1] * 4, "mercado": ["1x2"] * 4, "t": [100.0, 5000.0, 6000.0, 7000.0],
                       "minuto": [np.nan, np.nan, np.nan, 30.0], "home_od": [2.0, 1.9, 1.8, 1.1]})
    k = pd.Series({1: 7200})
    # con 7.200 s de saque y 3.600 s de antelación solo vale lo capturado hasta el segundo 3.600: el tick de 100 s
    assert B.instantaneas(tk, k, 3600)["home_od"].iloc[0] == 2.0
    assert B.instantaneas(tk, k, 0)["home_od"].iloc[0] == 1.8  # al cierre: último prepartido, sin el tick en vivo


def test_carrera_de_corners_desde_la_serie_en_vivo():
    v = pd.DataFrame({"t": [1, 2, 3, 4], "minuto": [5.0, 12.0, 20.0, 30.0], "corners_vivo": ["1-0", "2-1", "3-2", "3-3"]})
    assert B.llegada_carrera(v, 3) == "home" and B.llegada_carrera(v, 5) is None
    v2 = pd.DataFrame({"t": [1, 2], "minuto": [5.0, 40.0], "corners_vivo": ["1-0", "3-3"]})
    assert B.llegada_carrera(v2, 3) is None  # los dos cruzaron entre dos lecturas


def test_gana_y_pierde_de_handicap_suman_uno_en_media_linea():
    dif = np.array([0.1, 0.2, 0.3, 0.2, 0.2]); sop = np.array([-2, -1, 0, 1, 2])
    for ls in ([-1.5], [0.5], [-0.5]):
        g = B.p_handicap(dif, sop, ls, "home")
        p = B.p_handicap(dif, sop, ls, "away")  # el rival gana = el local pierde
        assert g + p == pytest.approx(1)
    assert B.p_handicap(dif, sop, [-1.0], "home") + B.p_handicap(dif, sop, [-1.0], "away") == pytest.approx(0.8)  # 0,2 devuelve
