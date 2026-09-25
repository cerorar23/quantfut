"""
Verificación del modelo de residuo.

Lo crítico aquí no es que el GBM aprenda —eso es fácil— sino que:

1. Las features de descanso/congestión NO miran el futuro. Es la fuga que
   convierte cualquier backtest de fútbol en ficción.
2. La corrección deja probabilidades válidas (suman 1, todas positivas).
3. La puerta de validación descarta el modelo cuando no aporta.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from qf.model.residual import (
    FEATURES,
    ResidualModel,
    _sigmoid,
    build_features,
    fit_and_validate,
)

START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_oos(n: int = 3000, seed: int = 0, con_senal: bool = True) -> pd.DataFrame:
    """
    Genera predicciones fuera de muestra sintéticas.

    Si `con_senal`, el modelo tiene un sesgo REAL que depende del descanso:
    infravalora al local cuando viene con muchos días de descanso. Eso es lo
    que el GBM debería encontrar.
    """
    rng = np.random.default_rng(seed)
    teams = [f"T{i}" for i in range(40)]
    rows = []
    for i in range(n):
        ko = START + timedelta(hours=8 * i)
        h, a = rng.choice(teams, 2, replace=False)
        p_market = float(np.clip(rng.beta(5, 5), 0.12, 0.85))
        # El modelo difiere del mercado con ruido.
        p_model = float(np.clip(p_market + rng.normal(0, 0.05), 0.05, 0.92))
        p_draw = float(np.clip(0.26 + rng.normal(0, 0.02), 0.15, 0.35))

        p_true = p_market
        if con_senal:
            # Sesgo sistemático que las features SÍ pueden ver.
            p_true = float(np.clip(p_market + 0.05 * ((i % 7) - 3) / 3.0,
                                   0.05, 0.92))
        resto = 1.0 - p_true
        probs = [p_true, resto * 0.35, resto * 0.65]
        outcome = int(rng.choice(3, p=probs))

        rows.append({
            "match_id": f"m{i}", "kickoff_utc": ko, "league_id": "L1",
            "home_team": h, "away_team": a,
            "p_home": p_model, "p_draw": p_draw,
            "p_away": max(1.0 - p_model - p_draw, 0.01),
            "lam": 1.4, "mu": 1.1,
            "mk_home": p_market, "mk_draw": 0.26,
            "mk_away": max(1.0 - p_market - 0.26, 0.01),
            "outcome": outcome, "both_known": True,
            "home_goals": 1, "away_goals": 1,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Point-in-time: la parte que de verdad importa
# ---------------------------------------------------------------------------

def test_descanso_no_mira_el_futuro():
    """
    El primer partido de un equipo no puede tener días de descanso, y el
    segundo debe medir exactamente la distancia al primero. Si `build_features`
    actualizara el historial ANTES de calcular, el descanso saldría 0 y estaría
    filtrando el presente.
    """
    ko = [START, START + timedelta(days=3), START + timedelta(days=10)]
    df = pd.DataFrame([
        {"match_id": "m1", "kickoff_utc": ko[0], "league_id": "L",
         "home_team": "A", "away_team": "B", "p_home": 0.5, "p_draw": 0.25,
         "p_away": 0.25, "lam": 1.3, "mu": 1.1, "mk_home": 0.5, "mk_draw": 0.26,
         "mk_away": 0.24, "outcome": 0, "both_known": True,
         "home_goals": 1, "away_goals": 0},
        {"match_id": "m2", "kickoff_utc": ko[1], "league_id": "L",
         "home_team": "A", "away_team": "C", "p_home": 0.5, "p_draw": 0.25,
         "p_away": 0.25, "lam": 1.3, "mu": 1.1, "mk_home": 0.5, "mk_draw": 0.26,
         "mk_away": 0.24, "outcome": 1, "home_goals": 1, "away_goals": 1,
         "both_known": True},
        {"match_id": "m3", "kickoff_utc": ko[2], "league_id": "L",
         "home_team": "A", "away_team": "D", "p_home": 0.5, "p_draw": 0.25,
         "p_away": 0.25, "lam": 1.3, "mu": 1.1, "mk_home": 0.5, "mk_draw": 0.26,
         "mk_away": 0.24, "outcome": 2, "home_goals": 0, "away_goals": 1,
         "both_known": True},
    ])
    f = build_features(df)
    assert np.isnan(f.loc[0, "home_rest_days"]), "El primer partido no tiene pasado"
    assert f.loc[1, "home_rest_days"] == 3
    assert f.loc[2, "home_rest_days"] == 7


def test_congestion_cuenta_solo_partidos_anteriores():
    kos = [START + timedelta(days=d) for d in (0, 2, 4, 30)]
    rows = []
    for i, ko in enumerate(kos):
        rows.append({
            "match_id": f"m{i}", "kickoff_utc": ko, "league_id": "L",
            "home_team": "A", "away_team": f"B{i}", "p_home": 0.5,
            "p_draw": 0.25, "p_away": 0.25, "lam": 1.3, "mu": 1.1,
            "mk_home": 0.5, "mk_draw": 0.26, "mk_away": 0.24,
            "outcome": 0, "both_known": True, "home_goals": 1, "away_goals": 0,
        })
    f = build_features(pd.DataFrame(rows))
    assert f.loc[0, "home_matches_14d"] == 0
    assert f.loc[1, "home_matches_14d"] == 1
    assert f.loc[2, "home_matches_14d"] == 2
    # El de +30 días ya no ve ninguno dentro de la ventana de 14.
    assert f.loc[3, "home_matches_14d"] == 0


def test_todas_las_features_existen_tras_construirlas():
    f = build_features(make_oos(200))
    for col in FEATURES:
        assert col in f.columns, f"Falta la feature {col}"


# ---------------------------------------------------------------------------
# Corrección
# ---------------------------------------------------------------------------

def test_modelo_desactivado_no_toca_nada():
    rm = ResidualModel.disabled()
    assert not rm.is_active
    f = build_features(make_oos(300))
    p = f[["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
    p = p / p.sum(axis=1, keepdims=True)
    assert np.allclose(rm.adjust(f, p), p)


def test_la_correccion_mantiene_probabilidades_validas():
    oos = make_oos(2500, seed=3)
    feats = build_features(oos)
    rm = ResidualModel().fit(feats, shrink=0.5)

    p = feats[["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
    p = p / p.sum(axis=1, keepdims=True)
    out = rm.adjust(feats, p)

    assert np.allclose(out.sum(axis=1), 1.0, atol=1e-9)
    assert (out > 0).all()
    assert (out < 1).all()


def test_muestra_insuficiente_es_error_explicito():
    feats = build_features(make_oos(200))
    with pytest.raises(ValueError, match="insuficiente"):
        ResidualModel().fit(feats)


def test_shrink_reduce_la_magnitud_de_la_correccion():
    oos = make_oos(2500, seed=4)
    feats = build_features(oos)
    p = feats[["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
    p = p / p.sum(axis=1, keepdims=True)

    fuerte = ResidualModel().fit(feats, shrink=1.0)
    # `replace` crea params NUEVOS. Compartir el objeto haría que cambiar
    # shrink en uno lo cambiara en el otro y el test se auto-engañaría.
    suave = ResidualModel(fuerte.model, replace(fuerte.params, shrink=0.2))

    d_fuerte = np.abs(fuerte.adjust(feats, p)[:, 0] - p[:, 0]).mean()
    d_suave = np.abs(suave.adjust(feats, p)[:, 0] - p[:, 0]).mean()
    assert d_suave < d_fuerte


# ---------------------------------------------------------------------------
# Puerta de validación
# ---------------------------------------------------------------------------

def test_puerta_descarta_cuando_no_hay_datos():
    rm, report = fit_and_validate(make_oos(400))
    assert not report["ok"]
    assert not rm.is_active
    assert "insuficientes" in report["reason"]


def test_puerta_devuelve_informe_comparable():
    """Pase o no, el informe debe traer el antes y el después para auditarlo."""
    rm, report = fit_and_validate(make_oos(4000, seed=9), shrink=0.5)
    if report["ok"]:
        assert report["log_loss_after"] < report["log_loss_before"]
        assert rm.is_active
    else:
        assert not rm.is_active
        assert "reason" in report


def test_sin_columna_de_mercado_no_se_puede_entrenar():
    oos = make_oos(2000, seed=5)
    oos["mk_home"] = np.nan          # histórico sin cuotas de cierre
    rm, report = fit_and_validate(oos)
    assert not report["ok"]
    assert not rm.is_active
