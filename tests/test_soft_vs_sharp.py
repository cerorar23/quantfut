"""
Backtest "casa blanda contra precio sharp".

Lo que fijan estos tests:
  - la selección no ve ni el cierre ni el resultado;
  - la vara es la de la puerta: valor esperado contra el cierre SIN margen;
  - el control (Pinnacle en todo, sin criterio) sale negativo por su margen.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qf.eval import soft_vs_sharp as svs

PIN = (2.00, 3.40, 4.00)   # margen ~3,8%


def _frame(n_weeks=10, per_week=3, b365=(2.20, 3.30, 3.80), close=PIN, goals=(2, 1)):
    rows = []
    start = pd.Timestamp("2024-08-03")
    for w in range(n_weeks):
        for k in range(per_week):
            d = start + pd.Timedelta(days=7 * w)
            rows.append({
                "Date": d.strftime("%d/%m/%Y"), "HomeTeam": f"H{w}{k}", "AwayTeam": f"A{w}{k}",
                "FTHG": goals[0], "FTAG": goals[1], "league_id": f"L{k}",
                "PSH": PIN[0], "PSD": PIN[1], "PSA": PIN[2],
                "PSCH": close[0], "PSCD": close[1], "PSCA": close[2],
                "B365H": b365[0], "B365D": b365[1], "B365A": b365[2],
                "P>2.5": 1.95, "P<2.5": 1.95, "PC>2.5": 1.95, "PC<2.5": 1.95,
                "B365>2.5": 2.10, "B365<2.5": 1.70,
                "AvgH": 1.97, "AvgD": 3.35, "AvgA": 3.90,
                "Avg>2.5": 1.90, "Avg<2.5": 1.90,
            })
    return pd.DataFrame(rows)


def test_la_seleccion_no_ve_el_cierre_ni_el_resultado():
    q1 = svs.build_quotes(_frame())
    q2 = svs.build_quotes(_frame(close=(1.60, 4.20, 6.00), goals=(0, 3)))
    s1 = svs.select_by_book(q1, "bet365", 0.02)
    s2 = svs.select_by_book(q2, "bet365", 0.02)
    cols = ["match", "market", "selection", "book", "price_early"]
    pd.testing.assert_frame_equal(s1[cols].reset_index(drop=True),
                                  s2[cols].reset_index(drop=True))
    assert len(s1) > 0


def test_solo_pasa_la_seleccion_por_encima_del_precio_justo():
    q = svs.build_quotes(_frame())
    sel = svs.select_by_book(q, "bet365", 0.0)
    h2h = sel[sel["market"] == "h2h"]
    assert set(h2h["selection"]) == {"home"}, "2,20 supera el justo; 3,30 y 3,80 no"
    over = sel[sel["market"] == "totals_2.5"]
    assert set(over["selection"]) == {"over"}


def test_si_el_cierre_no_se_mueve_el_ev_es_el_edge_temprano():
    q = svs.build_quotes(_frame())
    r = svs.evaluate(svs.select_by_book(q[q["market"] == "h2h"], "bet365", 0.0))
    assert r["ev_close"] == pytest.approx(r["edge_early"], abs=1e-9)
    assert r["persistence"] == pytest.approx(1.0)
    assert r["clv_with_margin"] > r["ev_close"], "la cifra con margen sale inflada"


def test_si_el_cierre_se_acorta_hacia_la_seleccion_el_valor_sube():
    q = svs.build_quotes(_frame(close=(1.85, 3.60, 4.60)))
    r = svs.evaluate(svs.select_by_book(q[q["market"] == "h2h"], "bet365", 0.0))
    assert r["ev_close"] > r["edge_early"] > 0


def test_el_control_sin_criterio_pierde_el_margen():
    ctrl = svs.control_no_criterion(_frame())
    assert ctrl["h2h"]["ev_close"] < -1.0
    assert ctrl["h2h"]["clv_with_margin"] == pytest.approx(0.0, abs=1e-9)


def test_mejor_de_lista_toma_la_cuota_mas_alta_una_vez():
    f = _frame()
    f["WHH"], f["WHD"], f["WHA"] = 2.30, 3.20, 3.70
    q = svs.build_quotes(f)
    best = svs.select_best_of(q[q["market"] == "h2h"], ["bet365", "williamhill"], 0.0)
    assert (best["book"] == "williamhill").all()
    assert best.groupby(["match", "selection"]).size().max() == 1


def test_sin_semanas_suficientes_no_hay_intervalo():
    q = svs.build_quotes(_frame(n_weeks=svs.MIN_WEEKS - 1))
    r = svs.evaluate(svs.select_by_book(q, "bet365", 0.0))
    assert r["ev_close_ci95"] is None
    q = svs.build_quotes(_frame(n_weeks=svs.MIN_WEEKS + 2))
    assert svs.evaluate(svs.select_by_book(q, "bet365", 0.0))["ev_close_ci95"] is not None


def test_partidos_sin_pinnacle_completo_no_entran():
    f = _frame()
    f.loc[0, "PSCD"] = np.nan
    f["PSH"] = f["PSH"].astype(object)
    f.loc[1, "PSH"] = "n/a"
    q = svs.build_quotes(f)
    assert q[q["market"] == "h2h"]["match"].nunique() == len(f) - 2


def test_pinnacle_apartado_de_la_media_no_se_usa_de_referencia():
    """
    El caso real de over/under: Pinnacle congelado a 1,53 mientras todas las
    casas dan 1,36-1,44. El "edge" que sale contra esa referencia es un
    artefacto, y el cierre no lo delata porque está igual de roto.
    """
    f = _frame()
    f[["P>2.5", "P<2.5", "PC>2.5", "PC<2.5"]] = [1.53, 2.63, 1.53, 2.63]
    f[["Avg>2.5", "Avg<2.5"]] = [1.41, 2.90]
    f[["B365>2.5", "B365<2.5"]] = [1.36, 3.20]
    q = svs.build_quotes(f)
    ou = q[q["market"] == "totals_2.5"]
    assert (ou["sharp_dev_early"] > svs.MAX_SHARP_DEVIATION).all()
    assert svs.select_by_book(ou, "bet365", 0.0).empty
    assert svs.select_best_of(ou, ["bet365"], 0.0).empty


def test_sin_media_no_se_puede_verificar_y_no_entra():
    f = _frame().drop(columns=["AvgH", "AvgD", "AvgA"])
    q = svs.build_quotes(f)
    assert svs.select_by_book(q[q["market"] == "h2h"], "bet365", 0.0).empty


def test_casa_sin_columnas_no_rompe():
    q = svs.build_quotes(_frame())
    assert "bwin" not in set(q["book"])
    assert svs.evaluate(svs.select_by_book(q, "bwin", 0.0)) == {"n": 0}


def test_totales_liquidan_por_goles():
    q = svs.build_quotes(_frame(goals=(2, 1)))
    over = q[(q["market"] == "totals_2.5") & (q["selection"] == "over")]
    assert over["won"].all()
