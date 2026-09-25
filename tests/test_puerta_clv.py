"""
La puerta comercial pasa a decidirse por CLV, no por batir al cierre en RPS.

El cambio no ablanda nada, y estos tests son los que lo demuestran. La
condición anterior era "media de CLV no negativa" más "RPS mejor que el
cierre"; la primera mitad se cumple con cualquier racha y la segunda no la
cumple casi nadie, así que la puerta no discriminaba: rechazaba todo por el
motivo equivocado.

La nueva pide tres cosas a la vez, y cada test tumba una:
  - muestra suficiente,
  - intervalo de confianza ENTERO por encima de cero,
  - varias ligas con muestra propia.
"""
from __future__ import annotations

import numpy as np

from qf.eval.clv import summarize_clv
from qf.model.promotion import (CLV_MIN_LEAGUES, CLV_MIN_N,
                                evaluate_base_promotion, evaluate_clv_gate)


def _clv(n=400, media=1.2, sd=3.0, ligas=4, semilla=0, margen=2.5):
    """`ev_close_pct` es lo que decide; `clv_pct` va `margen` puntos por encima."""
    rng = np.random.default_rng(semilla)
    valores = rng.normal(media, sd, n)
    return summarize_clv([
        {"ev_close_pct": float(v), "clv_pct": float(v + margen),
         "beat_close": bool(v + margen > 0),
         "league_id": f"L{i % ligas}", "market": "h2h"}
        for i, v in enumerate(valores)
    ])


def test_clv_solido_abre_la_puerta():
    ok, motivos = evaluate_clv_gate(_clv())
    assert ok and motivos == []


def test_sin_datos_no_autoriza():
    ok, motivos = evaluate_clv_gate(None)
    assert not ok and "Sin datos" in motivos[0]


def test_muestra_corta_no_autoriza():
    ok, motivos = evaluate_clv_gate(_clv(n=CLV_MIN_N - 1))
    assert not ok and "muestra insuficiente" in motivos[0]


def test_el_intervalo_que_cruza_cero_no_autoriza():
    """Media positiva pero ruido grande: es lo que produce una racha."""
    informe = _clv(n=400, media=0.6, sd=9.0, semilla=0)
    assert informe["avg_ev_close"] > 0, "la media engaña; el intervalo no"
    assert informe["ev_close_ci95"][0] <= 0
    ok, motivos = evaluate_clv_gate(informe)
    assert not ok and "por encima de cero" in motivos[0]


def test_el_margen_no_abre_la_puerta():
    """
    El caso que la vara anterior dejaba pasar: CLV contra la cuota con margen
    claramente positivo, valor real contra el cierre sin margen negativo. Es
    lo que da apostar a Pinnacle sin criterio (-0,32 frente a -3,90 medido).
    """
    informe = _clv(n=600, media=-2.0, sd=3.0, margen=3.5)
    assert informe["avg_clv"] > 1.0
    ok, motivos = evaluate_clv_gate(informe)
    assert not ok and "por encima de cero" in motivos[0]


def test_sin_cierre_justo_no_hay_muestra():
    """Filas con clv_pct pero sin cierre sharp completo no cuentan para la puerta."""
    informe = summarize_clv([
        {"clv_pct": 5.0, "ev_close_pct": None, "beat_close": True,
         "league_id": f"L{i % 4}", "market": "btts"}
        for i in range(500)
    ])
    assert informe["n"] == 0
    assert informe["n_without_fair_close"] == 500
    assert informe["avg_clv"] == 5.0, "se sigue reportando"
    ok, motivos = evaluate_clv_gate(informe)
    assert not ok and "muestra insuficiente" in motivos[0]


def test_una_sola_liga_no_autoriza():
    """Un CLV que solo vive en una liga no es un hallazgo sobre el sistema."""
    ok, motivos = evaluate_clv_gate(_clv(ligas=1))
    assert not ok and "pocas ligas" in motivos[0]
    assert CLV_MIN_LEAGUES >= 3


def test_perder_en_rps_contra_el_cierre_ya_no_veta_la_venta():
    """El cambio de fondo: el cierre deja de ser el rival."""
    comparacion = {
        "models": {"dixon_coles": {"rps": 0.2024},
                   "elo": {"rps": 0.2053},
                   "market": {"rps": 0.1956}},   # el mercado GANA
        "n_obs": 1907, "market_age_days": 5,
    }
    d = evaluate_base_promotion({"rps": 0.2024, "validation_signature": "x"},
                                None, comparacion, _clv())
    assert d.checks["beats_market_same_rows"] is False, "se sigue reportando"
    assert d.ready_for_commercial_picks, "pero ya no es un veto"


def test_sin_clv_no_se_autoriza_aunque_todo_lo_demas_pase():
    comparacion = {
        "models": {"dixon_coles": {"rps": 0.19},
                   "elo": {"rps": 0.21},
                   "market": {"rps": 0.20}},
        "n_obs": 1907, "market_age_days": 5,
    }
    d = evaluate_base_promotion({"rps": 0.19, "validation_signature": "x"},
                                None, comparacion, None)
    assert d.promote
    assert not d.ready_for_commercial_picks
