from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from qf.model.features import ALL_SPORT_FEATURES, build_pit_features


START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _history(n=15):
    rows = []
    for i in range(n):
        rows.append({
            "match_id": f"m{i}", "kickoff_utc": START + timedelta(days=i * 3),
            "league_id": "L", "home_team_id": 1,
            "away_team_id": 100 + i, "home_team": "A", "away_team": f"B{i}",
            "home_goals": i % 4, "away_goals": (i + 1) % 3,
            "home_shots": 8 + i, "away_shots": 6 + i,
            "home_shots_target": 3 + i % 5, "away_shots_target": 2 + i % 4,
        })
    return pd.DataFrame(rows)


def test_partido_actual_no_entra_en_sus_features():
    df = _history(3)
    feats = build_pit_features(df)
    assert np.isnan(feats.loc[0, "home_points_5"])
    assert feats.loc[1, "home_points_5"] in (0.0, 1.0, 3.0)
    # El promedio de tiros del segundo partido solo puede contener el primero.
    assert feats.loc[1, "home_shots_for_5"] == df.loc[0, "home_shots"]


def test_cambiar_resultados_futuros_no_cambia_features_pasadas():
    df = _history(12)
    before = build_pit_features(df)
    changed = df.copy()
    changed.loc[8:, ["home_goals", "away_goals", "home_shots"]] = [9, 0, 40]
    after = build_pit_features(changed)
    cols = [c for c in ALL_SPORT_FEATURES if c != "elo_diff"]
    assert np.allclose(before.loc[:8, cols], after.loc[:8, cols], equal_nan=True)


def test_partidos_simultaneos_no_se_ven_entre_si():
    df = _history(2)
    df.loc[1, "kickoff_utc"] = df.loc[0, "kickoff_utc"]
    df.loc[1, "home_team_id"] = 1
    feats = build_pit_features(df)
    assert np.isnan(feats.loc[0, "home_rest_days"])
    assert np.isnan(feats.loc[1, "home_rest_days"])


def test_partido_solapado_no_ve_resultado_ni_tiros_aun_no_disponibles():
    df = _history(2)
    df.loc[1, "kickoff_utc"] = df.loc[0, "kickoff_utc"] + timedelta(minutes=30)
    feats = build_pit_features(df)
    assert np.isnan(feats.loc[1, "home_points_5"])
    assert np.isnan(feats.loc[1, "home_shots_for_5"])


def test_as_of_nunca_supera_kickoff():
    feats = build_pit_features(_history())
    assert (feats["feature_as_of"] <= feats["kickoff_utc"]).all()
