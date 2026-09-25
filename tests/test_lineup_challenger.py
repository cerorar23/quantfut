from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from qf.model.lineup_challenger import build_lineup_features, readiness_report


def _data(n=8):
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    matches, lineups = [], []
    regular = [{"player_id": i, "pos": "G" if i == 1 else "D" if i < 6
                else "M" if i < 9 else "F"} for i in range(1, 12)]
    for i in range(n):
        match_id, ko = f"m{i}", start + timedelta(days=7 * i)
        matches.append({"match_id": match_id, "league_id": "L",
                        "kickoff_utc": ko, "home_team_id": 1,
                        "away_team_id": 2})
        home = regular if i < n - 1 else regular[1:] + [{"player_id": 99, "pos": "F"}]
        lineups.extend([
            {"match_id": match_id, "side": "home", "starters": home,
             "captured_at": ko - timedelta(minutes=60)},
            {"match_id": match_id, "side": "away", "starters": regular,
             "captured_at": ko - timedelta(minutes=60)},
        ])
    return pd.DataFrame(matches), pd.DataFrame(lineups)


def test_xi_actual_no_entra_en_su_propia_historia():
    matches, lineups = _data()
    features = build_lineup_features(matches, lineups)
    last = features.loc[features["match_id"] == "m7"].iloc[0]
    assert last["home_missing_regulars"] == 1
    assert last["home_missing_g"] == 1


def test_readiness_no_aprueba_muestra_pequena():
    matches, lineups = _data()
    report = readiness_report(matches, lineups)
    assert report["matches_with_both_lineups"] == len(matches)
    assert not report["ready_for_training"]
