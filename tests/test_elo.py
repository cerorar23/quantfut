from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from qf.eval.comparison import compare_elo_dc_market
from qf.model.elo import EloConfig, EloRatings, sequential_elo


START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def _matches(n=20):
    rows = []
    for i in range(n):
        rows.append({
            "match_id": f"m{i}", "kickoff_utc": START + timedelta(days=i),
            "league_id": "L1", "home_team_id": i % 4,
            "away_team_id": (i + 1) % 4, "home_team": f"T{i % 4}",
            "away_team": f"T{(i + 1) % 4}", "home_league": "L1",
            "away_league": "L1", "home_goals": 1 if i % 3 else 0,
            "away_goals": 0 if i % 3 else 0,
        })
    return pd.DataFrame(rows)


def test_elo_predice_antes_de_actualizar():
    df = _matches(2)
    df.loc[0, ["home_goals", "away_goals"]] = [1, 0]
    model = EloRatings(EloConfig(home_advantage=0, new_team_penalty=0))
    out = model.predict_sequential(df)
    # Primer cruce equilibrado: local y visitante tienen la misma probabilidad.
    assert out.loc[0, "elo_p_home"] == out.loc[0, "elo_p_away"]
    # Después del primer resultado los ratings ya no son iguales.
    assert out.loc[1, "elo_home_rating"] != out.loc[1, "elo_away_rating"]


def test_probabilidades_elo_suman_uno_y_tienen_empate():
    out = sequential_elo(_matches())
    p = out[["elo_p_home", "elo_p_draw", "elo_p_away"]].to_numpy()
    assert np.allclose(p.sum(axis=1), 1.0)
    assert (p > 0).all()
    assert (out["elo_p_draw"] > 0).all()


def test_modificar_el_futuro_no_cambia_el_pasado():
    df = _matches(12)
    before = sequential_elo(df)
    changed = df.copy()
    changed.loc[10:, ["home_goals", "away_goals"]] = [0, 8]
    after = sequential_elo(changed)
    cols = ["elo_p_home", "elo_p_draw", "elo_p_away"]
    assert np.allclose(before.loc[:9, cols], after.loc[:9, cols])


def test_partidos_simultaneos_no_ven_el_resultado_del_otro():
    df = _matches(2)
    df.loc[1, "kickoff_utc"] = df.loc[0, "kickoff_utc"]
    df.loc[0, ["home_goals", "away_goals"]] = [5, 0]
    out = sequential_elo(df, config=EloConfig(home_advantage=0,
                                               new_team_penalty=0))
    assert out.loc[1, "elo_home_rating"] == 1500.0


def test_partido_que_empieza_media_hora_despues_no_ve_el_resultado():
    df = _matches(2)
    df.loc[1, "kickoff_utc"] = START + timedelta(minutes=30)
    df.loc[1, "home_team_id"] = 10
    df.loc[1, "away_team_id"] = 11
    df.loc[0, ["home_goals", "away_goals"]] = [0, 0]
    out = sequential_elo(df, config=EloConfig(home_advantage=0,
                                               new_team_penalty=0))
    assert out.loc[1, "elo_p_draw"] == out.loc[0, "elo_p_draw"]


def test_regresion_por_inactividad_se_aplica_una_vez_por_partido():
    df = _matches(2)
    df.loc[1, "kickoff_utc"] = START + timedelta(days=200)
    df.loc[0, ["home_goals", "away_goals"]] = [5, 0]
    cfg = EloConfig(home_advantage=0, new_team_penalty=0,
                    inactivity_days=120, inactivity_regression=0.5)
    model = EloRatings(cfg)
    model.predict_sequential(df)
    # El equipo 1 jugó ambos partidos; al predecir el segundo se encoge una
    # vez, y update() no debe volver a encogerlo antes del ajuste por resultado.
    reference = EloRatings(cfg)
    first = df.iloc[0]
    second = df.iloc[1]
    reference.predict(first)
    reference.update(first)
    before = reference.predict(second)
    rating_before_update = reference.ratings[before["home_key"]]
    reference.update(second)
    assert reference.last_advanced[before["home_key"]] == pd.Timestamp(
        second["kickoff_utc"])
    assert abs(reference.ratings[before["home_key"]] - rating_before_update) < 20


def test_comparacion_usa_la_misma_interseccion():
    elo = sequential_elo(_matches(8))
    dc = elo[["match_id", "kickoff_utc", "league_id", "outcome"]].copy()
    dc[["p_home", "p_draw", "p_away"]] = [0.45, 0.28, 0.27]
    dc[["mk_home", "mk_draw", "mk_away"]] = [0.43, 0.29, 0.28]
    dc.loc[0, "mk_home"] = np.nan
    report = compare_elo_dc_market(dc, elo)
    assert report["n_obs"] == 7
    assert set(report["models"]) == {"dixon_coles", "elo", "market"}
    assert report["by_league"]["L1"]["n"] == 7
