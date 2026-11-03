from datetime import date, timedelta

import numpy as np
import pytest

from nba import roster_strength as rs


def test_minutes_reconcile_and_cannot_give_a_star_more_than_48():
    minutes = rs.allocate_minutes(dict(star=1000, a=10, b=10, c=10, d=10, e=10))
    assert sum(minutes.values()) == pytest.approx(240)
    assert minutes['star'] == 48 and max(minutes.values()) <= 48
    with pytest.raises(ValueError):
        rs.allocate_minutes(dict(a=100, b=100))
    with pytest.raises(ValueError):
        rs.allocate_minutes(dict(a=float('nan'), b=1, c=1, d=1, e=1))


def schedule():
    games, players = [], []
    for i in range(40):
        day = (date(2025, 10, 20) + timedelta(days=i)).isoformat()
        games.append(dict(game_id=str(i), date=day, season='2025-26', home=dict(team_id=1, points=112 + i % 4),
                          away=dict(team_id=2, points=100 + i % 3)))
        for team, start in ((1, 1), (2, 7)):
            players.extend(dict(game_id=str(i), date=day, team_id=team, player_id=p, participated=True, minutes=40.)
                           for p in range(start, start + 6))
    return games, players


def test_strength_fit_ignores_future_scores_and_future_player_statistics():
    games, players = schedule()
    fitted = rs.fit_ratings(games, players, '2025-11-25')
    later = [dict(g, home=dict(g['home'], points=999)) if g['date'] >= '2025-11-25' else g for g in games]
    assert rs.fit_ratings(later, players, '2025-11-25') == fitted
    assert fitted['last_feature_date'] < fitted['before']
    assert fitted['margin']['weights']['1'] > fitted['margin']['weights']['7']


def test_departed_star_reduces_old_team_and_improves_new_team_before_debut():
    games, players = schedule()
    history = rs.RotationHistory()
    for g in games:
        history.observe(g, [r for r in players if r['game_id'] == g['game_id']])
    # Isolate the transfer mechanism from the estimation: player 1 is a strong individual, every other player is average.
    ratings = dict(before='2026-08-01', last_feature_date='2025-11-28',
                   margin=dict(weights={str(p): (12. if p == 1 else 0.) for p in range(1, 14)}),
                   total=dict(weights={str(p): (6. if p == 1 else 0.) for p in range(1, 14)}))
    original = {str(p): 1 if p <= 6 else 2 for p in range(1, 13)}
    changed = dict(original, **{'1': 2, '13': 1})
    old = history.change(1, '2026-10-20', '2026-27', ratings, original)
    lost = history.change(1, '2026-10-20', '2026-27', ratings, changed)
    gained = history.change(2, '2026-10-20', '2026-27', ratings, changed)
    assert abs(old['margin']) < 1e-9
    assert lost['margin'] < 0 < gained['margin']
    assert '1' not in lost['rotation'] and '1' in gained['rotation']
    assert history.change(1, '2026-10-20', '2026-27', ratings)['observed'] is False
    with pytest.raises(ValueError, match='future'):
        history.change(1, '2026-10-20', '2026-27', dict(ratings, before='2026-11-01'), changed)


def test_zero_correction_reproduces_probabilities_and_total_shift_reconciles():
    prediction = dict(winner=.7, home=dict(mean=112., sd=12., line=111.5, p=.516617),
                      away=dict(mean=108., sd=12., line=107.5, p=.516617), total=dict(mean=220., sd=18., line=219.5, p=.51108))
    # Reference probabilities are evaluated at their own means, so derive them exactly.
    for side in ('home', 'away', 'total'):
        r = prediction[side]
        r['p'] = float(rs.norm.sf(r['line'], r['mean'], r['sd']))
    change = {s: dict(margin=0., total=0.) for s in ('home', 'away')}
    out = rs.adjust(prediction, change, [[144., 18.], [18., 144.]], 1.)
    assert out['winner'] == pytest.approx(prediction['winner'], abs=1e-14)
    for s in ('home', 'away', 'total'):
        assert out[s] == prediction[s]
    change['home'] = dict(margin=8., total=2.)
    out = rs.adjust(prediction, change, [[144., 18.], [18., 144.]], .5)
    assert out['winner'] > prediction['winner']
    assert out['home']['mean'] - out['away']['mean'] == pytest.approx(8.)
    assert out['total']['mean'] == pytest.approx(out['home']['mean'] + out['away']['mean'])


def test_live_rotation_ignores_same_day_and_future_games():
    games, players = schedule()
    ratings = rs.fit_ratings(games, players, '2026-08-01')
    mappings = [dict(nba_game_id='next', et_date='2026-10-20', home_nba_team_id=1, away_nba_team_id=2)]
    memberships = {str(p): 1 if p <= 6 else 2 for p in range(1, 13)}
    before = rs.live_changes(games, players, mappings, memberships, ratings)
    future = dict(games[0], game_id='future', date='2026-10-20', season='2026-27')
    extra = [dict(r, game_id='future', date='2026-10-20', minutes=999.) for r in players if r['game_id'] == '0']
    assert rs.live_changes([*games, future], [*players, *extra], mappings, memberships, ratings) == before
