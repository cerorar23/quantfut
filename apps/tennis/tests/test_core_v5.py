"""Artificial canonical rows only."""
import pandas as pd
import pytest
from tennis_core_v5.features import pair_features, latest


def table():
    rows = [
        dict(circuit='ATP', tourney_date='20260105', source_row=1, winner_id='a', loser_id='b', winner_rank=10., loser_rank=50., winner_rank_points=3000., loser_rank_points=900., winner_age=25.0, loser_age=30.0),
        dict(circuit='ATP', tourney_date='20260112', source_row=2, winner_id='b', loser_id='a', winner_rank=40., loser_rank=12., winner_rank_points=1000., loser_rank_points=2800., winner_age=30.05, loser_age=25.05),
        dict(circuit='ATP', tourney_date='20260301', source_row=3, winner_id='c', loser_id='a', winner_rank=5., loser_rank=500., winner_rank_points=5., loser_rank_points=5., winner_age=19., loser_age=99.),
    ]
    return pd.DataFrame(rows)


def test_uses_last_usable_row_before_decision_and_ignores_garbage_age_or_future_rows():
    df = table()
    assert latest(df, 'ATP', 'a', '2026-01-20T00:00:00Z')['rank'] == 12.
    assert latest(df, 'ATP', 'a', '2026-02-01T00:00:00Z')['rank'] == 12.  # March row has garbage age 99 and is later anyway
    with pytest.raises(ValueError):
        latest(df, 'ATP', 'a', '2026-01-05T00:00:00Z')  # nothing strictly before the first row


def test_stale_and_missing_players_are_rejected_and_pair_signs_are_oriented():
    df = table()
    x = pair_features(df, 'ATP', 'a', 'b', '2026-01-20T00:00:00Z')
    assert x['lrank'] > 0 and x['lpts'] > 0 and x['age'] < 0  # a is better ranked, more points, younger
    with pytest.raises(ValueError):
        pair_features(df, 'ATP', 'a', 'b', '2026-06-01T00:00:00Z')
    with pytest.raises(ValueError):
        pair_features(df, 'ATP', 'a', 'zzz', '2026-01-20T00:00:00Z')
