"""Feature builder secuencial: cada fila usa exclusivamente partidos previos."""
from __future__ import annotations

from collections import defaultdict, deque

import numpy as np
import pandas as pd


FEATURE_GROUPS = {
    "elo": ["elo_diff"],
    "rest": ["home_rest_days", "away_rest_days", "rest_diff",
             "home_matches_14d", "away_matches_14d"],
    "form": ["home_points_5", "away_points_5", "points_diff_5",
             "home_points_10", "away_points_10", "points_diff_10",
             "home_goal_diff_5", "away_goal_diff_5", "goal_diff_form_5"],
    "shots": ["home_shots_for_5", "away_shots_for_5", "shots_for_diff_5",
              "home_shots_against_5", "away_shots_against_5",
              "shots_against_diff_5", "home_sot_for_5", "away_sot_for_5",
              "sot_for_diff_5"],
}

ALL_SPORT_FEATURES = [c for cols in FEATURE_GROUPS.values() for c in cols]


def _team_key(row, side: str):
    team_id = row.get(f"{side}_team_id")
    if team_id is not None and not pd.isna(team_id):
        return int(team_id)
    league = row.get(f"{side}_league") or row.get("league_id") or "unknown"
    return f"{league}||{row[f'{side}_team']}"


def _mean(history: deque[dict], field: str, n: int) -> float:
    vals = [float(x[field]) for x in list(history)[-n:]
            if x.get(field) is not None and not pd.isna(x.get(field))]
    return float(np.mean(vals)) if vals else float("nan")


def _side_features(history: deque[dict], kickoff: pd.Timestamp,
                   prefix: str) -> dict[str, float]:
    previous = history[-1]["kickoff"] if history else None
    rest = (kickoff - previous).days if previous is not None else np.nan
    m14 = sum(1 for x in history if 0 <= (kickoff - x["kickoff"]).days <= 14)
    return {
        f"{prefix}_rest_days": float(np.clip(rest, 0, 60))
        if not pd.isna(rest) else float("nan"),
        f"{prefix}_matches_14d": float(m14),
        f"{prefix}_points_5": _mean(history, "points", 5),
        f"{prefix}_points_10": _mean(history, "points", 10),
        f"{prefix}_goal_diff_5": _mean(history, "goal_diff", 5),
        f"{prefix}_shots_for_5": _mean(history, "shots_for", 5),
        f"{prefix}_shots_against_5": _mean(history, "shots_against", 5),
        f"{prefix}_sot_for_5": _mean(history, "sot_for", 5),
    }


def _number(row, name: str) -> float | None:
    value = row.get(name)
    return None if value is None or pd.isna(value) else float(value)


def build_pit_features(df: pd.DataFrame,
                       elo_predictions: pd.DataFrame | None = None,
                       result_delay_hours: float = 2.0) -> pd.DataFrame:
    """
    Construye descanso, forma y tiros ANTES de incorporar el partido actual.

    El resultado conserva una fila por ``match_id`` y puede unirse a cualquier
    walk-forward. ``feature_as_of`` es el kickoff: todo lo usado es anterior a
    ese instante. Sin timestamp de finalización, cada resultado y sus tiros
    entran dos horas después del inicio; tampoco se ven partidos solapados.
    """
    required = {"match_id", "kickoff_utc", "home_team", "away_team",
                "home_goals", "away_goals", "league_id"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas para features PIT: {sorted(missing)}")

    ordered = df.copy()
    ordered["kickoff_utc"] = pd.to_datetime(ordered["kickoff_utc"], utc=True)
    ordered = ordered.sort_values(["kickoff_utc", "match_id"])
    elo_map = {}
    if elo_predictions is not None and not elo_predictions.empty:
        elo_map = elo_predictions.set_index("match_id")["elo_diff"].to_dict()

    histories: dict[object, deque[dict]] = defaultdict(lambda: deque(maxlen=50))
    out: list[dict] = []
    pending: deque[tuple[pd.Timestamp, object, dict, object, dict]] = deque()

    for kickoff, group in ordered.groupby("kickoff_utc", sort=True):
        while pending and pending[0][0] <= kickoff:
            _, hk, home_update, ak, away_update = pending.popleft()
            histories[hk].append(home_update)
            histories[ak].append(away_update)
        pending_updates: list[tuple[object, dict, object, dict]] = []
        for _, row in group.iterrows():
            hk, ak = _team_key(row, "home"), _team_key(row, "away")
            home = _side_features(histories[hk], kickoff, "home")
            away = _side_features(histories[ak], kickoff, "away")
            feats = {
                "match_id": row["match_id"],
                "kickoff_utc": kickoff,
                "feature_as_of": kickoff,
                "league_id": row["league_id"],
                "elo_diff": float(elo_map.get(row["match_id"], np.nan)),
                **home, **away,
            }
            feats.update({
                "rest_diff": feats["home_rest_days"] - feats["away_rest_days"],
                "points_diff_5": feats["home_points_5"] - feats["away_points_5"],
                "points_diff_10": feats["home_points_10"] - feats["away_points_10"],
                "goal_diff_form_5": (feats["home_goal_diff_5"]
                                     - feats["away_goal_diff_5"]),
                "shots_for_diff_5": (feats["home_shots_for_5"]
                                     - feats["away_shots_for_5"]),
                "shots_against_diff_5": (feats["home_shots_against_5"]
                                         - feats["away_shots_against_5"]),
                "sot_for_diff_5": (feats["home_sot_for_5"]
                                   - feats["away_sot_for_5"]),
            })
            out.append(feats)

            hg, ag = int(row["home_goals"]), int(row["away_goals"])
            h_points = 3.0 if hg > ag else 1.0 if hg == ag else 0.0
            a_points = 3.0 if ag > hg else 1.0 if hg == ag else 0.0
            home_update = {
                "kickoff": kickoff, "points": h_points, "goal_diff": hg - ag,
                "shots_for": _number(row, "home_shots"),
                "shots_against": _number(row, "away_shots"),
                "sot_for": _number(row, "home_shots_target"),
            }
            away_update = {
                "kickoff": kickoff, "points": a_points, "goal_diff": ag - hg,
                "shots_for": _number(row, "away_shots"),
                "shots_against": _number(row, "home_shots"),
                "sot_for": _number(row, "away_shots_target"),
            }
            pending_updates.append((hk, home_update, ak, away_update))

        # Ningún partido simultáneo ni aún en juego entra en otra feature.
        for hk, home_update, ak, away_update in pending_updates:
            pending.append((kickoff + pd.Timedelta(hours=result_delay_hours),
                            hk, home_update, ak, away_update))

    result = pd.DataFrame(out)
    if result["match_id"].duplicated().any():
        raise ValueError("El feature builder produjo match_id duplicados")
    if (result["feature_as_of"] > result["kickoff_utc"]).any():
        raise AssertionError("FUGA: feature_as_of posterior al kickoff")
    return result


def merge_pit_features(oos: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Une features por ID y conserva exactamente las filas del walk-forward."""
    cols = ["match_id", "feature_as_of", *ALL_SPORT_FEATURES]
    merged = oos.merge(features[cols], on="match_id", how="left",
                       validate="one_to_one")
    if len(merged) != len(oos):
        raise AssertionError("La unión de features cambió el número de predicciones")
    return merged
