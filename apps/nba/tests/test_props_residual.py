from datetime import date, timedelta

import numpy as np
from scipy.special import expit, logit

from nba import props_residual as pr

PROTOCOL = dict(seasons=dict(train='2024-25', test='2025-26'), model=dict(lambda_grid=[1e-4, 1e-3, 1e-2, 1e-1]))
ALL = pr.ENVIRONMENT + pr.AVAILABILITY


def team_game(gid, day, home, away, hp, ap, hposs=100., aposs=98.):
    mk = lambda tid, pts, poss: dict(team_id=tid, points=pts, possessions_estimate=poss)
    return dict(game_id=gid, date=day, home=mk(home, hp, hposs), away=mk(away, ap, aposs))


def schedule(n=8):
    """Teams 1 and 2 meet every second day; teams 3 and 4 on the other days."""
    out, day = [], date(2024, 11, 1)
    for i in range(n):
        out.append(team_game(f'g{i}', day.isoformat(), 1 + (i % 2), 2 - (i % 2), 110 + i, 100, 100. + i, 98.))
        day += timedelta(days=1)
    return out


def test_team_context_uses_only_earlier_dates_and_waits_for_enough_games():
    ctx = pr.team_context(schedule())
    assert ctx['g0']['pace_l'] is None and ctx['g0']['home']['last'] is None
    assert ctx['g1']['pace_l'] == 99. and ctx['g1']['home']['pace'] == 99.  # league mean until 5 games: not the team's own
    assert ctx['g4']['home']['pace'] == ctx['g4']['pace_l']  # four earlier games: still the league mean
    g5 = ctx['g5']  # team 2 is at home and has five earlier games: 98, 101, 98, 103, 98
    assert g5['home']['team_id'] == 2 and abs(g5['home']['pace'] - 99.6) < 1e-9
    assert g5['home']['last'] == '2024-11-05' and g5['away']['last'] == '2024-11-05'


def test_same_day_games_do_not_feed_each_other():
    games = [team_game('a', '2024-11-01', 1, 2, 100, 90), team_game('b', '2024-11-01', 3, 4, 120, 80, hposs=140.)]
    ctx = pr.team_context(games)
    assert ctx['a']['pace_l'] is None and ctx['b']['pace_l'] is None


def test_as_of_takes_the_latest_entry_not_after_the_quote():
    path = [[7200, -5.0, 1.9, 1.9], [3600, -5.5, 1.9, 1.9], [1500, -6.0, 1.9, 1.9], [60, -7.0, 1.9, 1.9]]
    assert pr.as_of(path, 2400)[1] == -5.5  # quote 40 min before tip: the 25-min-old entry did not exist yet
    assert pr.as_of(path, 1500)[1] == -6.0
    assert pr.as_of(path, 7300) is None


def test_minutes_context_excludes_the_same_day_and_needs_five_rows():
    rows = [dict(game_id=f'g{i}', player_id=7, date=f'2024-11-{i + 1:02d}', participated=True, minutes=30. + i) for i in range(7)]
    out = pr.minutes_context(rows, {('g5', '7'), ('g2', '7')})
    assert ('g2', '7') not in out  # only two earlier rows
    assert out[('g5', '7')] == np.mean([30., 31., 32., 33., 34.]) / 48


def test_permutation_keeps_each_groups_values_and_breaks_the_pairing():
    rng = np.random.default_rng(0)
    rows = [dict(date='d%d' % (i % 3), market='m', a=float(i), b=float(i) * 10, y=i % 2) for i in range(60)]
    shuffled = pr.permute_within_date(rows, ('a', 'b'), 5)
    assert [r['y'] for r in shuffled] == [r['y'] for r in rows]
    for d in ('d0', 'd1', 'd2'):
        assert sorted(r['a'] for r in shuffled if r['date'] == d) == sorted(r['a'] for r in rows if r['date'] == d)
    assert all(r['b'] == r['a'] * 10 for r in shuffled)  # the columns move together
    assert any(s['a'] != r['a'] for s, r in zip(shuffled, rows))


def synthetic(signal, n=3000, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for season, start in (('2024-25', date(2024, 11, 1)), ('2025-26', date(2025, 11, 1))):
        for i in range(n):
            lk = rng.normal(0, 1)
            feats = {c: float(rng.normal()) for c in ALL}
            truth = expit(lk + signal * feats['total_c'])
            market_p = float(expit(lk))
            rows.append(dict(game_id=f'{season}-{i}', player_id=i, market='player_points', line=20.5, books=3,
                             market_p=market_p, model_p=market_p, model_delta=0., y=int(rng.random() < truth),
                             date=(start + timedelta(days=i % 150)).isoformat(), season=season,
                             starter=bool(i % 2), main_line=True, **feats))
    return rows


def test_a_real_environment_signal_is_found_and_a_null_is_not():
    found = pr.evaluate_market(synthetic(.8), PROTOCOL)
    decision = found['decision']
    assert decision['beats_market_upper_below_zero'] and decision['walk_forward_beats'] and decision['placebo_clean']
    assert found['arms'][pr.PRIMARY]['vs_market']['interval'][1] < 0
    assert found['arms']['D_environment']['vs_market']['paired_brier_difference'] < 0
    assert found['placebo']['vs_market']['interval'][1] >= 0  # shuffled features are not a signal
    null = pr.evaluate_market(synthetic(0.), PROTOCOL)
    assert null['decision']['verdict'] == 'no_evidence'


def test_ridge_prior_keeps_the_market_when_there_is_nothing_to_learn():
    rows = synthetic(0., n=2000, seed=3)
    model = pr.fit(rows, pr.ARMS['E_full'], 0.1)
    assert abs(model['w'][1] - 1) < .1 and abs(model['w'][0]) < .1 and np.abs(model['w'][2:]).max() < .1


def test_bootstrap_interval_widens_with_confidence():
    dates = [f'd{i % 40}' for i in range(400)]
    diff = np.random.default_rng(1).normal(0, 1, 400)
    narrow, wide = pr.date_bootstrap(dates, diff, 400, 7, .8), pr.date_bootstrap(dates, diff, 400, 7, .9875)
    assert wide[0] < narrow[0] < narrow[1] < wide[1]


def test_calibration_of_a_perfect_probability_is_slope_one():
    rng = np.random.default_rng(2)
    p = rng.uniform(.1, .9, 20000)
    y = (rng.random(20000) < p).astype(int)
    c = pr.calibration(y, p)
    assert abs(c['slope'] - 1) < .05 and abs(c['intercept']) < .05


def test_decision_labels_calibration_only_when_recalibration_matches_the_gain():
    report = dict(market=dict(brier=.25), arms=dict(E_full=dict(vs_market=dict(interval=[-.01, -.002]), scores=dict(slope=1.0),
                                                                vs_recalibration=dict(interval=[-.001, .001]))),
                  walk_forward=dict(scores=dict(brier=.24)), placebo=dict(vs_market=dict(interval=[-.001, .002])))
    assert pr.decide(report)['verdict'] == 'calibration_only'
    report['arms']['E_full']['vs_recalibration']['interval'] = [-.01, -.003]
    assert pr.decide(report)['verdict'] == 'adds_information'
    report['arms']['E_full']['scores']['slope'] = 1.4
    assert pr.decide(report)['verdict'] == 'no_evidence'
