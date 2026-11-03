"""Piezas del cierre del rediseño: regresión de Poisson con desplazamiento y construcción de opciones con cuotas reales."""
import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _cargar(nombre):
    ruta = Path(__file__).resolve().parents[1] / "scripts" / "rediseno_futbol" / f"{nombre}.py"
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_poisson_con_desplazamiento_recupera_el_coeficiente():
    once = _cargar("once_a4")
    rng = np.random.default_rng(7)
    n = 60000
    x = rng.normal(size=(n, 1)); off = rng.normal(0.1, 0.3, n)
    y = rng.poisson(np.exp(off + 0.2 + 0.05 * x[:, 0]))
    b, se = once.poisson_offset(x, y.astype(float), off, ridge=0.0)
    assert b[0] == pytest.approx(0.2, abs=0.02) and b[1] == pytest.approx(0.05, abs=0.02) and se[1] < 0.01


def test_construir_opciones_usa_pinnacle_y_la_mediana_de_las_demas():
    af = _cargar("af_cuotas")
    cr = af.cargar_cuotas_reales()
    partidos = pd.DataFrame({"match_id": ["m"], "kickoff_utc": pd.to_datetime(["2026-10-20 18:00"], utc=True),
                             "home_goals": [2], "away_goals": [1], "home_corners": [5], "away_corners": [4],
                             "home_yellow": [1], "away_yellow": [2], "home_red": [0], "away_red": [0]})
    filas = []
    # totales 2,5: Pinnacle y dos casas; goles del partido = 3 → gana «más»
    for casa, o, u in (("pinnacle", 1.90, 1.95), ("bovada", 1.85, 2.00), ("heritage", 1.88, 1.97)):
        for sel, p in (("over", o), ("under", u)):
            filas.append({"match_id": "m", "bookmaker": casa, "market": "totals", "selection": sel, "line": 2.5, "price": p,
                          "mins_to_kickoff": 120})
    # totales 3,5 sin Pinnacle: solo las otras casas
    for casa in ("bovada", "heritage"):
        for sel, p in (("over", 3.0), ("under", 1.40)):
            filas.append({"match_id": "m", "bookmaker": casa, "market": "totals", "selection": sel, "line": 3.5, "price": p,
                          "mins_to_kickoff": 120})
    o = af.construir_opciones(pd.DataFrame(filas), partidos, cr, 60).set_index(["seleccion", "linea"])
    assert o.loc[("over", 2.5), "acierto"] == 1 and o.loc[("under", 3.5), "acierto"] == 1
    assert o.loc[("over", 2.5), "cuota"] == pytest.approx(1.90)  # la mejor cuota entre casas
    assert o.loc[("over", 2.5), "mercado_p"] == o.loc[("over", 2.5), "pinnacle"]
    assert np.isnan(o.loc[("under", 3.5), "pinnacle"]) and o.loc[("under", 3.5), "mercado_p"] == pytest.approx(
        o.loc[("under", 3.5), "otras_casas"])
    assert o.loc[("under", 3.5), "mercado_p"] == pytest.approx((1 / 1.40) / (1 / 1.40 + 1 / 3.0))
