from datetime import date, timedelta
import json
from pathlib import Path

import numpy as np
import pytest

from nba import multimarket_v12 as v

PROTOCOL = json.loads((Path(__file__).parents[1] / 'multimarket_v12_protocol.json').read_bytes())
PROTOCOL = dict(PROTOCOL, history_max_days=370)


def game(day, season, home_points, away_points, n):
    team = lambda tid, pts: dict(team_id=tid, points=pts)
    return dict(game_id=f'g{n}', date=day, season=season, home=team(1, home_points), away=team(2, away_points))


def schedule(season, start, count, gap=1, offset=0):
    first = date.fromisoformat(start)
    return [game((first + timedelta(days=gap * i)).isoformat(), season, 100 + i % 7, 98 + i % 5, offset + i)
            for i in range(count)]


def test_training_window_never_includes_target_or_burn_in():
    seasons = ['2021-22', '2022-23', '2023-24', '2024-25']
    assert v.training_window('2023-24', seasons, PROTOCOL) == ('2022-08-01', '2023-08-01')
    assert v.training_window('2024-25', seasons, PROTOCOL) == ('2022-08-01', '2024-08-01')
    with pytest.raises(ValueError):
        v.training_window('2022-23', seasons, PROTOCOL)


def test_features_ignore_same_day_and_future_outcomes():
    games = schedule('2021-22', '2021-10-20', 40, 2) + schedule('2022-23', '2022-10-20', 40, 2, 100)
    target = games[-1]
    changed = [dict(g) for g in games]
    changed[-1] = dict(target, home=dict(target['home'], points=300), away=dict(target['away'], points=1))
    changed.append(game('2023-06-01', '2022-23', 250, 40, 999))
    before = {r['game_id']: r for r in v.team_games(games, PROTOCOL)}
    after = {r['game_id']: r for r in v.team_games(changed, PROTOCOL)}
    row = target['game_id']
    for key in ('elo_gap_mov', 'v1_probability', 'home_mean', 'away_mean', 'b2b_home', 'b2b_away'):
        assert before[row][key] == after[row][key]


def test_back_to_back_flag_uses_consecutive_calendar_days_only():
    games = schedule('2021-22', '2021-10-20', 30, 1) + schedule('2022-23', '2022-10-20', 30, 1, 100)
    rows = {r['game_id']: r for r in v.team_games(games, PROTOCOL)}
    assert all(r['b2b_home'] == 1 and r['b2b_away'] == 1 for r in rows.values() if r['date'] > '2022-10-21')
    spaced = schedule('2021-22', '2021-10-20', 30, 2) + schedule('2022-23', '2022-10-20', 30, 2, 100)
    assert all(r['b2b_home'] == 0 for r in v.team_games(spaced, PROTOCOL))


def test_margin_multiplier_grows_with_margin_and_shrinks_for_favorites():
    assert v.mov_multiplier(25, 0) > v.mov_multiplier(3, 0)
    assert v.mov_multiplier(10, 200) < v.mov_multiplier(10, -200)


def test_date_bootstrap_resamples_dates_and_is_deterministic():
    dates = ['a', 'a', 'b', 'c'] * 5
    diff = np.array([1., 1., -1., 0.] * 5)
    first = v.date_bootstrap(dates, diff, 200, 7)
    assert first == v.date_bootstrap(dates, diff, 200, 7) and first[0] <= diff.mean() <= first[1]
