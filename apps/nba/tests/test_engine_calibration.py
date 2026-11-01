from datetime import date, timedelta

import numpy as np
from scipy.special import expit, logit
from scipy.stats import norm

from nba import engine_calibration as ec
from nba import multimarket as m1


def test_over_probs_equal_the_v1_player_law_at_every_line():
    local = dict(history_window=20, min_history=10, history_max_days=370, prior_minutes=90, empirical_weight=.25,
                 player_prior_rates=dict(points=.65))
    rng = np.random.default_rng(0)
    hist = [dict(date=f'2025-01-{i + 1:02d}', minutes=float(rng.integers(20, 38)), points=int(rng.integers(5, 35))) for i in range(20)]
    params = m1.player_parameters(hist, 'points', local)
    lines = np.array([12.5, 18.5, 24.5, 30.5])
    got = ec.over_probs(params, lines, .25)
    want = [m1.player_over(params, float(x), local) for x in lines]
    assert np.allclose(got, want, atol=1e-12)


def test_period_pairs_and_quantities():
    rec = dict(game=(110, 100), h1=(60, 50), q1=(30, 22))
    assert ec.period_pair(rec, 'h2') == (50, 50) and ec.period_pair(rec, 'q2') == (30, 28)
    assert ec.quantity(rec, 'total_game') == 210 and ec.quantity(rec, 'margin_h1') == 10 and ec.quantity(rec, 'home_points') == 110
    assert ec.quantity(rec, 'margin_q2') == 2 and ec.quantity(rec, 'total_h2') == 100


def test_engine_law_for_team_points_and_periods():
    pred = dict(mu_t=230., sigma_t=19., mu_m=6., sigma_m=12.)
    assert ec.engine_law(pred, 'home_points', {}, 's') == (118., float(np.sqrt((19 ** 2 + 12 ** 2) / 4)))
    assert ec.engine_law(pred, 'away_points', {}, 's')[0] == 112.
    fits = {('s', 'h1'): dict(total=dict(a=1., b=.5, sd=7.), margin=dict(a=0., b=.5, sd=6.)), ('s', 'q1'): None}
    assert ec.engine_law(pred, 'total_h1', fits, 's') == (116., 7.) and ec.engine_law(pred, 'margin_h1', fits, 's') == (3., 6.)
    assert ec.engine_law(pred, 'total_q1', fits, 's') is None


def team_pred(i, season):
    return dict(game_id=f'{season}-{i}', season=season, date='2024-12-01', mu_t=228., sigma_t=19., mu_m=2., sigma_m=12.)


def test_team_units_fit_periods_only_on_earlier_seasons_and_lines_are_half_integers():
    rng = np.random.default_rng(1)
    recs, preds = {}, []
    for season, n, day in (('2023-24', 260, '2023-12-01'), ('2024-25', 40, '2024-12-01'), ('2025-26', 40, '2025-12-01')):
        for i in range(n):
            g = f'{season}-{i}'
            h1h, h1a = int(rng.normal(58, 7)), int(rng.normal(56, 7))
            recs[g] = dict(season=season, date=day, game=(h1h + 55, h1a + 54), h1=(h1h, h1a), q1=(h1h // 2, h1a // 2))
            preds.append(team_pred(i, season))
    units, drops, fits = ec.team_units(preds, recs)
    assert fits['2024-25 h1'] is not None and fits['2025-26 q1'] is not None
    seasons = {u[0] for u in units['total_h1']}
    assert seasons == {'2024-25', '2025-26'}  # 2023-24 is never a unit season
    sample = [u for u in units['total_game'] if u[0] == '2025-26'][:5]
    for u in sample:
        assert u[5] in (0, 1) and 0 < u[3] < 1 and 0 < u[4] < 1
    # the first unit of a game uses z = -1: line = floor(mean - sd) + .5, probability sf(line)
    game = [u for u in units['total_game'] if u[2] == '2025-26-0']
    assert len(game) == 5 and abs(game[0][3] - norm.sf(np.floor(228 - 19) + .5, 228, 19)) < 1e-12


def synthetic_arrays(skill, n_dates=120, per_date=40, seed=0, overconfident=1.):
    rng = np.random.default_rng(seed)
    date_ids = np.repeat(np.arange(n_dates), per_date)
    lk = rng.normal(0, 1.2, len(date_ids))
    y = (rng.random(len(lk)) < expit(lk)).astype(int)
    p = expit(overconfident * lk)
    base = np.full(len(lk), y.mean()) if skill else expit(rng.normal(0, 1.2, len(lk)))
    x = rng.normal(size=(len(lk), len(ec.FEATURES)))
    return dict(p=p, p_base=base, y=y, date_ids=date_ids, x=x, x_perm=x[rng.permutation(len(lk))])


def test_a_calibrated_skilled_engine_is_labelled_and_an_overconfident_one_is_recalibrated():
    train, test = synthetic_arrays(True, seed=1), synthetic_arrays(True, seed=2)
    good = ec.evaluate(train, test, ec.LEVEL_PLAYER, True)
    assert good['decision']['skilled'] and good['decision']['calibrated'] and not good['decision']['recalibration_helps']
    assert abs(good['coefficients']['b'] - 1) < .1 and not good['decision']['features_help']
    over_tr, over_te = synthetic_arrays(True, seed=3, overconfident=2.), synthetic_arrays(True, seed=4, overconfident=2.)
    bad = ec.evaluate(over_tr, over_te, ec.LEVEL_PLAYER, False)
    assert not bad['decision']['calibrated'] and bad['decision']['recalibration_helps']
    assert abs(bad['coefficients']['b'] - .5) < .1  # the logistic recalibration undoes the doubled slope
    assert bad['raw']['slope'] < .9


def test_player_replay_uses_only_earlier_days_and_skips_missing_turnovers():
    rows, day = [], date(2024, 11, 1)
    for i in range(40):
        rows.append(dict(game_id=f'g{i}', player_id=7, team_id=1, date=(day + timedelta(days=i)).isoformat(), season='2024-25',
                         participated=True, minutes=30., points=20 + i % 3, rebounds=6, assists=4, steals=1, blocks=0, threes=2))
    ec.add_counts(rows, [])
    assert rows[0]['points_rebounds_assists'] == 30 and rows[0]['turnovers'] is None and rows[0]['dd'] == 0
    stores, seen = ec.player_units(rows, dict(points=.65, rebounds=.2, assists=.15, steals=.035, blocks=.025))
    assert len(seen) == 30  # the first ten days only build history
    assert len(stores['turnovers'].p) == 0  # no turnover counts in these rows
    assert len(stores['points_rebounds'].p) >= 30 and len(stores['double_double'].p) == 30
    first = np.frombuffer(stores['double_double'].pg, dtype=np.int32)[0]
    assert seen[first][2] == (day + timedelta(days=10)).isoformat()


def test_double_double_prior_uses_earlier_seasons_only():
    rows = []
    for season, start, dd in (('2023-24', date(2023, 11, 1), 1), ('2024-25', date(2024, 11, 1), 0)):
        for i in range(30):
            rows.append(dict(game_id=f'{season}-{i}', player_id=1 if i < 15 else 2, team_id=1,
                             date=(start + timedelta(days=i)).isoformat(), season=season, participated=True, minutes=30.,
                             points=12 if dd else 5, rebounds=11 if dd else 2, assists=3, steals=0, blocks=0, threes=0))
    ec.add_counts(rows, [])
    stores, seen = ec.player_units(rows, dict(points=.65, rebounds=.2, assists=.15, steals=.035, blocks=.025))
    # the 2023-24 rows are not scored units (season outside fit/test) so the 2024-25 prior comes from them: rate 1.0
    s = stores['double_double']
    assert all(f == 0 for f in s.flag) and all(abs(b - 1.0) < 1e-12 for b in s.base)
    assert all(.5 < p <= 1 for p in s.p)
