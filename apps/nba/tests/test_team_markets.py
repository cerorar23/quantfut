from datetime import date, timedelta

import numpy as np
from scipy.special import expit, logit
from scipy.stats import norm

from nba import team_markets as tm

GRID = [1e-4, 1e-3, 1e-2, 1e-1]


def test_exceed_half_integers_integers_and_odd_lines():
    assert abs(tm.exceed(0., 10., -.5) - norm.sf(-.5, 0, 10)) < 1e-12
    assert abs(tm.exceed(0., 10., 0.) - .5) < 1e-12  # integer line: conditioned on no push, symmetric
    above, below = norm.sf(5.5, 3, 8), norm.cdf(4.5, 3, 8)
    assert abs(tm.exceed(3., 8., 5.) - above / (above + below)) < 1e-12
    assert tm.exceed(0., 10., 224.25) is None and tm.exceed(0., 10., 224.75) is None


def pred(**kw):
    base = dict(game_id='g', date='2025-12-01', season='2025-26', p_win=.7, home_win=1, mu_m=6., sigma_m=12., mu_t=228., sigma_t=19.,
                b2b_home=0, b2b_away=0, mp_home=0., mp_away=0.)
    return base | kw


def test_full_game_probabilities_use_the_winner_total_and_the_home_line_sign():
    p = pred()
    assert tm.model_probability('ml_game', p, None, None) == .7
    favourite_small, favourite_big = tm.model_probability('spread_game', p, -3.5, None), tm.model_probability('spread_game', p, -9.5, None)
    assert favourite_small > favourite_big  # the home side covers a smaller handicap more often
    assert abs(tm.model_probability('spread_game', p, -6.5, None) - norm.sf(6.5, 6, 12)) < 1e-12
    assert abs(tm.model_probability('total_game', p, 228.5, None) - norm.sf(228.5, 228, 19)) < 1e-12
    assert tm.model_probability('total_game', p, 228.25, None) is None


def test_period_probabilities_need_a_fit_and_use_its_coefficients():
    fit = dict(total=dict(a=0., b=.5, sd=7.), margin=dict(a=0., b=.5, sd=6.))
    p = pred()
    assert tm.model_probability('total_h1', p, 114.5, None) is None
    assert abs(tm.model_probability('total_h1', p, 114.5, fit) - norm.sf(114.5, 114, 7)) < 1e-12
    assert abs(tm.model_probability('spread_h1', p, -3.5, fit) - norm.sf(3.5, 3, 6)) < 1e-12
    ml = tm.model_probability('ml_h1', p, None, fit)
    assert ml > .5 and abs(ml - tm.exceed(3., 6., 0.)) < 1e-12


def test_fit_period_recovers_a_linear_relation():
    rng = np.random.default_rng(0)
    pairs = []
    for _ in range(600):
        mu_t, mu_m = rng.normal(228, 6), rng.normal(0, 5)
        total, margin = .5 * mu_t + 1 + rng.normal(0, 7), .5 * mu_m + rng.normal(0, 6)
        home = round((total + margin) / 2)
        pairs.append((dict(mu_t=mu_t, mu_m=mu_m), home, round(total) - home))
    fit = tm.fit_period(pairs)
    assert abs(fit['total']['b'] - .5) < .08 and abs(fit['margin']['b'] - .5) < .08 and 6 < fit['total']['sd'] < 8


def bet(game, market, line, p1, y, season, points=None):
    return dict(game_id=game, market=market, season=season, period=market.split('_')[1], y_close=y, date='2025-12-01',
                close=dict(line=line, p1_novig=p1), home_points=None if points is None else points[0],
                away_points=None if points is None else points[1])


def test_build_units_uses_only_earlier_seasons_for_period_fits_and_counts_drops():
    old = [pred(game_id=f'o{i}', season='2023-24', date=f'2023-12-{i % 28 + 1:02d}', mu_t=228 + i % 7, mu_m=i % 5 - 2.) for i in range(250)]
    new = [pred(game_id='n1', season='2024-25'), pred(game_id='n2', season='2023-24')]
    bets = [bet(p['game_id'], 'total_h1', 114.5, .5, 1, p['season'], (60 + i % 4, 57)) for i, p in enumerate(old)]
    bets += [bet('n1', 'total_h1', 114.5, .5, 1, '2024-25'), bet('n1', 'ml_game', None, .7, 1, '2024-25'),
             bet('n1', 'total_game', 228.25, .5, 1, '2024-25'), bet('n1', 'spread_game', -6.5, .5, None, '2024-25'),
             bet('n2', 'total_h1', 114.5, .5, 1, '2023-24'), bet('zz', 'ml_game', None, .5, 1, '2024-25')]
    units, drops, fits = tm.build_units(old + new, bets, tm.period_points_from(bets))
    kept = {(u['game_id'], u['market']) for u in units}
    assert ('n1', 'total_h1') in kept and ('n1', 'ml_game') in kept
    assert ('n2', 'total_h1') not in kept  # no earlier season to fit the period relation
    assert drops == dict(no_period_fit_or_odd_line=2 + 250, push_or_unsettled=1, no_score_model_prediction=1) or drops['no_score_model_prediction'] == 1
    assert fits['2023-24 h1'] is None and fits['2024-25 h1'] is not None


def synthetic(informative, n=1500, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for season, start in (('2024-25', date(2024, 11, 1)), ('2025-26', date(2025, 11, 1))):
        for i in range(n):
            lk = rng.normal(0, 1)
            delta = rng.normal(0, .5)
            truth = expit(lk + informative * delta)
            market_p = float(expit(lk))
            rows.append(dict(game_id=f'{season}-{i}', market='ml_game', line=None, season=season, market_p=market_p,
                             q=float(expit(lk + delta)), model_delta=float(delta), y=int(rng.random() < truth),
                             date=(start + timedelta(days=i % 150)).isoformat(),
                             b2b_home=float(rng.integers(0, 2)), b2b_away=float(rng.integers(0, 2)),
                             mp_home=float(rng.normal()), mp_away=float(rng.normal())))
    return rows


def test_an_informative_model_beats_the_market_and_a_null_model_does_not():
    found = tm.evaluate_market(synthetic(1.), GRID)
    assert found['arms']['B_model']['vs_market']['paired_brier_difference'] < 0
    assert found['model_only']['vs_market']['paired_brier_difference'] < 0
    assert found['placebo']['vs_model_only']['interval'][1] >= 0
    null = tm.evaluate_market(synthetic(0.), GRID)
    assert null['decision']['verdict'] == 'no_evidence'
    assert len(found['reliability']['C_full']) == 10 and sum(b['n'] for b in found['reliability']['C_full']) == 1500


def test_decision_labels():
    report = dict(market=dict(brier=.25), arms=dict(C_full=dict(vs_market=dict(interval=[-.01, -.002]), scores=dict(slope=1.0),
                                                                vs_recalibration=dict(interval=[-.006, -.001]))),
                  walk_forward=dict(scores=dict(brier=.24)), placebo=dict(vs_model_only=dict(interval=[-.001, .003])))
    assert tm.decide(report)['verdict'] == 'adds_information'
    report['arms']['C_full']['vs_recalibration']['interval'] = [-.004, .003]
    assert tm.decide(report)['verdict'] == 'calibration_only'
    report['arms']['C_full']['vs_recalibration']['interval'] = [-.006, -.001]
    report['placebo']['vs_model_only']['interval'] = [-.004, -.001]
    assert tm.decide(report)['verdict'] == 'void_placebo'
    report['walk_forward']['scores']['brier'] = .26
    assert tm.decide(report)['verdict'] == 'no_evidence'
