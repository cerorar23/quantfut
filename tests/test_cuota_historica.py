"""Cuotas históricas de BetsAPI y API-Football para `futbol.cuota_historica` (db/101)."""
import numpy as np
import pandas as pd
import pytest

from qf.ingest import cuota_historica as C


def _ticks():
    filas = []
    # partido 1, córners: 3 precios prepartido (uno a más de 60 min, dos dentro de la hora previa) y dos en vivo
    for t, linea, o, u, minuto, ss2 in [(1000, "9.5", 1.9, 1.9, np.nan, None), (6000, "10", 1.8, 2.0, np.nan, None),
                                        (7000, "9.5,10", 1.85, 1.95, np.nan, None), (9000, "8.5", 3.1, 1.35, 67.0, "3-5"),
                                        (9300, "8.5", 2.9, 1.4, 70.0, "3-5"), (9900, "9.5", 2.0, 1.8, 75.0, "4-5")]:
        filas.append({"bid": 1, "mercado": "corners", "t": float(t), "minuto": minuto, "marcador": None, "corners_vivo": ss2,
                      "linea": linea, "home_od": np.nan, "draw_od": np.nan, "away_od": np.nan, "over_od": o, "under_od": u})
    filas.append({"bid": 1, "mercado": "ah", "t": 6500.0, "minuto": np.nan, "marcador": None, "corners_vivo": None,
                  "linea": "-0.5,-1", "home_od": 1.9, "draw_od": np.nan, "away_od": 2.0, "over_od": np.nan, "under_od": np.nan})
    filas.append({"bid": 1, "mercado": "1x2", "t": 6600.0, "minuto": np.nan, "marcador": None, "corners_vivo": None,
                  "linea": None, "home_od": 1.5, "draw_od": 4.0, "away_od": 6.0, "over_od": np.nan, "under_od": np.nan})
    return pd.DataFrame(filas)


def test_linea_media_de_cuartos():
    assert C.linea_media("9.5") == 9.5 and C.linea_media("9.5,10") == 9.75 and C.linea_media("-0.5,-1") == -0.75
    assert C.linea_media(None) is None and C.linea_media("") is None and C.linea_media("x") is None


def test_momentos_betsapi_elige_apertura_t60_cierre_y_vivo():
    kick = pd.Series({1: 8000})  # el saque es en el segundo 8.000: T-60 = segundo 4.400
    m = C.momentos_betsapi(_ticks(), kick)
    c = m[m["mercado"] == "corners"].set_index("momento")
    assert c.loc["apertura", "t"] == 1000 and c.loc["t60", "t"] == 1000  # solo el primero tiene ≥ 60 min
    assert c.loc["cierre", "t"] == 7000
    assert c.loc["vivo_65_70", "t"] == 9300 and c.loc["vivo_65_70", "corners_vivo"] == "3-5"  # la última entre 65 y 70
    assert not (m[m["momento"] != "vivo_65_70"]["t"] >= 8000).any()  # nada en vivo en los prepartido


def test_filas_betsapi_mapea_mercados_lineas_y_signo_del_visitante():
    kick = pd.Series({1: 8000})
    puente = pd.DataFrame({"bid": [1], "match_id": ["it.serie_a:2026:a-b:20261001"]})
    f = C.filas_betsapi(_ticks(), kick, puente)
    ah = f[(f["mercado"] == "spreads") & (f["momento"] == "cierre")].set_index("seleccion")
    assert ah.loc["home", "linea"] == -0.75 and ah.loc["away", "linea"] == 0.75  # línea propia de cada selección
    assert ah.loc["home", "linea_texto"] == "-0.5,-1"
    h2h = f[f["mercado"] == "h2h"]
    assert set(h2h["seleccion"]) == {"home", "draw", "away"} and h2h["linea"].isna().all() and h2h["linea_texto"].isna().all()
    assert f["retroactiva"].all() and f["recibido_en"].isna().all() and (f["cuota"] > 1).all()
    viv = f[f["momento"] == "vivo_65_70"]
    assert set(viv["mercado"]) == {"corners"} and (viv["minuto_juego"] == 70).all() and (viv["minutos_al_saque"] < 0).all()


def test_filas_api_football_primero_ultimo_y_t60():
    af = pd.DataFrame({
        "snapshot_id": [1, 2, 3], "match_id": ["m"] * 3, "bookmaker": ["pinnacle"] * 3, "market": ["totals"] * 3,
        "selection": ["over"] * 3, "price": [1.9, 1.8, 1.7], "provider_updated_at": ["2026-10-01 10:00:00+00"] * 3,
        "fetched_at": ["2026-10-01 10:05:00+00", "2026-10-01 14:05:00+00", "2026-10-01 18:05:00+00"],
        "mins_to_kickoff": [600, 240, 30], "line": [2.5, 2.5, 2.5]})
    f = C.filas_api_football(af).set_index("momento")
    assert f.loc["apertura", "cuota"] == 1.9 and f.loc["ultimo", "cuota"] == 1.7 and f.loc["t60", "cuota"] == 1.8
    assert not f["retroactiva"].any() and f["recibido_en"].notna().all()
