from datetime import date, timedelta

import numpy as np
from scipy.special import expit

from nba import multimarket_v12 as v12
from nba import team_recal as tr

PROTOCOL = dict(history_window=20, history_max_days=370, min_history=10, elo_season_regression=.25, elo_k=20, elo_home=65)


def schedule(seasons=(('2023-24', '2023-10-24'), ('2024-25', '2024-10-22')), days=60, teams=4, level=None):
    """Round-robin games every day of each season; scores depend on the team and the season level."""
    rng = np.random.default_rng(7)
    level = level or {'2023-24': 110, '2024-25': 116}
    games, n = [], 0
    for season, first in seasons:
        start = date.fromisoformat(first)
        for d in range(days):
            day = (start + timedelta(days=d)).isoformat()
            for i in range(0, teams, 2):
                h, a = (i + d) % teams, (i + d + 1) % teams
                n += 1
                games.append(dict(game_id=f'002{n:07d}', date=day, season=season,
                                  home=dict(team_id=h, points=int(level[season] + 3 * h + rng.integers(-8, 9))),
                                  away=dict(team_id=a, points=int(level[season] + 3 * a + rng.integers(-8, 9)))))
    return games


def test_no_prior_reproduces_the_v12_form_means():
    games = schedule()
    rows = v12.team_games(games, PROTOCOL)
    entries, means, ends = tr.team_entries(games), tr.league_means(games), tr.season_ends(games)
    for r in rows[::7]:
        f = [tr.form(entries[r[s + '_team']], r['date'], r['season'], PROTOCOL, None, means, ends) for s in ('home', 'away')]
        ha = r['home_mean'] - (f[0][0] + f[1][1]) / 2
        assert abs((r['away_mean'] - (f[1][0] + f[0][1]) / 2) + ha) < 1e-9  # same home advantage on both sides
    assert tr.apply_prior(rows, games, PROTOCOL, None) == rows


def test_prior_only_moves_rows_whose_window_reaches_an_earlier_season():
    games = schedule()
    rows = v12.team_games(games, PROTOCOL)
    moved = tr.apply_prior(rows, games, PROTOCOL, dict(rho=.5, drop_days=0))
    second = [(r, m) for r, m in zip(rows, moved) if r['season'] == '2024-25']
    late = [(r, m) for r, m in second if r['date'] > '2024-12-10']  # 4 teams play daily: the last 20 are all in-season
    assert late and all(abs(r['home_mean'] - m['home_mean']) < 1e-9 for r, m in late)
    early = [(r, m) for r, m in second if r['date'] < '2024-10-30']
    assert early and any(abs(r['home_mean'] - m['home_mean']) > 1e-6 for r, m in early)
    for r, m in zip(rows, moved):  # the lines and the outcome are never touched
        assert (r['home_baseline'], r['away_baseline'], r['home_points']) == (m['home_baseline'], m['away_baseline'], m['home_points'])


def test_prior_regresses_toward_the_earlier_season_mean_and_drops_its_last_days():
    entries = [('2024-04-01', 'a', 130, 100), ('2024-04-14', 'a', 140, 90), ('2024-10-25', 'b', 120, 110)]
    means, ends = {'a': 110., 'b': 115.}, {'a': '2024-04-14', 'b': '2025-04-13'}
    plain = tr.form(entries, '2024-10-30', 'b', PROTOCOL, None, means, ends)
    assert plain == (130., 100.)
    half = tr.form(entries, '2024-10-30', 'b', PROTOCOL, dict(rho=.5, drop_days=0), means, ends)
    assert half == (np.mean([120, 125, 120]), np.mean([105, 100, 110]))
    dropped = tr.form(entries, '2024-10-30', 'b', PROTOCOL, dict(rho=.5, drop_days=10), means, ends)
    assert dropped == (np.mean([120, 120]), np.mean([105, 110]))  # 14-apr is in the last 10 days of season a


def test_fit_recal_recovers_slope_and_intercept():
    rng = np.random.default_rng(3)
    p = rng.uniform(.2, .8, 20000)
    z = np.log(p / (1 - p))
    rows = []
    for market, (a, b) in (('team_points', (.1, .8)), ('game_total', (-.2, .6))):
        y = rng.random(len(p)) < expit(a + b * z)
        rows += [dict(market=market, p=float(pi), y=int(yi)) for pi, yi in zip(p, y)]
    fit = tr.fit_recal(rows)
    assert abs(fit['team_points']['a'] - .1) < .05 and abs(fit['team_points']['b'] - .8) < .05
    assert abs(fit['game_total']['a'] + .2) < .05 and abs(fit['game_total']['b'] - .6) < .05


def test_in_season_intercept_is_shrunk_and_zero_without_data():
    assert tr.in_season_intercept([], [], .1) == 0.
    z, y = np.zeros(400), np.r_[np.ones(240), np.zeros(160)]  # 60 % overs at p = 0.5
    loose, tight = tr.in_season_intercept(z, y, 1.), tr.in_season_intercept(z, y, .05)
    assert abs(loose - np.log(.6 / .4)) < .02
    assert 0 < tight < loose


def test_with_intercepts_reads_only_earlier_dates():
    units = [dict(market=m, key=f'{m}{i}', date=d, line=1.5, y=1, p=.5) for i, d in enumerate(['2025-11-01'] * 3 + ['2025-11-02'] * 3)
             for m in tr.MARKETS]
    recal = {m: dict(a=0., b=1.) for m in tr.MARKETS}
    out = tr.with_intercepts(units, units, recal, .2)
    first = [u for u in out if u['date'] == '2025-11-01']
    second = [u for u in out if u['date'] == '2025-11-02']
    assert all(u['intercept'] == 0. and abs(u['p'] - .5) < 1e-12 for u in first)
    assert all(u['intercept'] > 0 and u['p'] > .5 for u in second)


def test_live_probability_without_recal_is_the_normal_tail():
    assert abs(tr.live_probability(110, 12, 109.5, 'team_points', None) - .5166) < 1e-3
    recal = {'team_points': dict(a=0., b=.5), 'game_total': dict(a=0., b=1.)}
    assert abs(tr.live_probability(110, 12, 109.5, 'team_points', recal) - .5) < tr.live_probability(110, 12, 109.5, 'team_points', None) - .5
