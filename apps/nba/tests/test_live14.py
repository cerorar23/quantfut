"""Live 1.4: new box-score counts, legacy cache refresh, game lines, environment features and the in-season team shift."""
import json

import numpy as np
import pytest
from scipy.special import expit, logit
from scipy.stats import norm

from nba import live_features as lf
from nba import multimarket_v13_live as live
from nba import prop_lines
from nba.audit import write_json
from test_live_players import NOW, archive, event, mapping  # noqa: F401  (archive is a fixture)
from test_multimarket_v13_live import AWAY, DAY, GID, HOME, V12, history_games, model


def person(pid, team_stats=None, **stats):
    base = dict(minutes='30:00', points=10, reboundsTotal=5, assists=2)
    base.update(stats)
    return dict(personId=pid, firstName='A', familyName=str(pid), comment='', statistics=base)


def test_player_rows_read_the_new_counts_and_tolerate_their_absence():
    game = dict(homeTeam=dict(teamId=HOME, players=[person(1, threePointersMade=2, steals=1, blocks=0, turnovers=3,
                                                           fieldGoalsAttempted=12, freeThrowsAttempted=4, reboundsOffensive=1)]),
                awayTeam=dict(teamId=AWAY, players=[person(2)]))
    full, bare = live.player_rows(game, GID, DAY)
    assert (full['threes'], full['steals'], full['blocks'], full['tov'], full['fga'], full['fta'], full['oreb']) == (2, 1, 0, 3, 12, 4, 1)
    assert set(full) == live.PLAYER_KEYS and bare['steals'] is None and bare['tov'] is None
    game['homeTeam']['players'][0]['statistics']['steals'] = -1
    with pytest.raises(ValueError, match='invalid box score counts'):
        live.player_rows(game, GID, DAY)


def test_a_cache_entry_written_by_1_3_is_downloaded_again_but_a_damaged_one_still_fails(tmp_path):
    legacy = dict(game_id='0022600001', date='2026-10-20', season=live.SEASON, home={}, away={}, box_score_sha256='x',
                  players=[{k: 0 for k in live.LEGACY_PLAYER_KEYS} | dict(game_id='0022600001', date='2026-10-20')])
    write_json(tmp_path / 'games' / '0022600001.json', legacy)
    assert live.cached_game(tmp_path, '0022600001', '2026-10-20') is None
    damaged = dict(legacy, players=[{k: 0 for k in live.PLAYER_KEYS - {'fga'}} | dict(game_id='0022600001', date='2026-10-20')])
    write_json(tmp_path / 'games' / '0022600001.json', damaged)
    with pytest.raises(ValueError, match='corrupt completed-game cache'):
        live.cached_game(tmp_path, '0022600001', '2026-10-20')


def test_turnovers_and_blocks_steals_are_derived_and_missing_parts_stay_missing():
    row = dict(points=10, rebounds=4, assists=3, steals=2, blocks=1, tov=3)
    out, = live.with_combinations([row])
    assert out['turnovers'] == 3 and out['blocks_steals'] == 3 and out['points_rebounds_assists'] == 17
    old, = live.with_combinations([dict(points=10, rebounds=4, assists=3)])
    assert old['turnovers'] is None and old['blocks_steals'] is None


def spread_and_total(book, home_point, total):
    sides = [dict(name='Bbb Club', side='home', point=home_point, price=-110), dict(name='Aaa Club', side='away', point=-home_point, price=-110)]
    over_under = [dict(name='Over', point=total, price=-110), dict(name='Under', point=total, price=-110)]
    return dict(key=book, markets=[dict(key='spreads', period=None, team=None, line_type='main', outcomes=sides),
                                   dict(key='totals', period=None, team=None, line_type='main', outcomes=over_under)])


def test_game_lines_are_the_consensus_main_spread_of_the_home_side_and_total(archive):
    archive['events'] = [event([spread_and_total('draftkings', -4.5, 226.5), spread_and_total('fanduel', -4.5, 226.5),
                                spread_and_total('betmgm', -5.5, 227.5), spread_and_total('prizepicks', -9.5, 200.5)])]
    lines, summary = prop_lines.game_lines('archive', NOW, [mapping()])
    assert summary['state'] == 'archivo_aplicado'
    assert lines[GID]['spread_home'] == -4.5 and lines[GID]['total'] == 226.5 and lines[GID]['books'] == dict(spread_home=3, total=3)
    assert prop_lines.game_lines(None, NOW, [mapping()]) == ({}, dict(state='sin_fuente'))


def records():
    games = []
    for i in range(12):
        home, away = (1, 2) if i % 2 == 0 else (2, 1)
        games.append(dict(game_id=f'h{i}', date=f'2025-11-{i + 1:02d}', home=dict(team_id=home, points=110, possessions_estimate=100.),
                          away=dict(team_id=away, points=100, possessions_estimate=96.)))
    return games


def test_team_history_uses_only_earlier_games_and_needs_five():
    history = lf.TeamHistory(lf.game_records(records()))
    assert history.recent(1, '2025-11-04') == (None, None)  # three earlier games
    pace, allowed = history.recent(1, '2025-11-12')
    assert pace == pytest.approx(np.mean([100., 96.] * 5)) and allowed is not None
    assert history.last_game(1, '2025-11-12') == '2025-11-11' and history.last_game(1, '2025-11-01') is None
    total, pace_l, ppp = history.league_means('2025-11-13')
    assert total == 210. and pace_l == 98.


def test_possessions_come_from_player_rows_for_live_games():
    rows = [dict(team_id=1, fga=40, oreb=5, tov=7, fta=10), dict(team_id=1, fga=45, oreb=6, tov=6, fta=12)]
    assert lf.possessions(rows) == pytest.approx(85 - 11 + 13 + .44 * 22)
    assert lf.possessions([dict(team_id=1, fga=40, oreb=None, tov=7, fta=10)]) is None


def test_environment_vector_signs_and_missing_inputs():
    history = lf.TeamHistory(lf.game_records(records()))
    hist = [dict(minutes=30., fga=10, fta=4, tov=2)] * 15 + [dict(minutes=30., fga=20, fta=4, tov=2)] * 5
    home = lf.environment(1, 1, 2, '2025-11-13', dict(spread_home=-6., total=230.), history, hist)
    away = lf.environment(2, 1, 2, '2025-11-13', dict(spread_home=-6., total=230.), history, hist)
    assert home[0] == pytest.approx((230 - 210) / 10) and home[1] == pytest.approx(-.6) and away[1] == pytest.approx(.6)
    assert home[2] == away[2] == pytest.approx(.6) and home[3] == 1. and away[3] == 0. and home[4] == 1.  # played the day before
    assert home[7] == pytest.approx(30 / 48) and home[8] > 0  # usage of the last 5 above the last 20
    missing = lf.environment(1, 1, 2, '2025-11-13', None, history, [])
    assert missing[:3] == [0., 0., 0.] and missing[7:] == [0., 0.]


def test_bets_lines_take_the_last_snapshot_old_enough():
    rows = [dict(game_id='g', market='spread_game', path=[[9000, -3., 1.9, 1.9], [3000, -4., 1.9, 1.9], [600, -5., 1.9, 1.9]]),
            dict(game_id='g', market='total_game', path=[[1000, 220., 1.9, 1.9]]), dict(game_id='g', market='ml_game', path=[])]
    assert lf.bets_lines(rows) == dict(g=dict(spread_home=-4.))


def test_team_shift_shrinks_toward_zero_and_moves_the_probabilities():
    done = [(110., 105., 115, 107)] * 10
    home, away = lf.team_shift(done, 40)
    assert home == pytest.approx(5 * 10 / 50) and away == pytest.approx(2 * 10 / 50)
    assert lf.team_shift(done, None) == (0., 0.) and lf.team_shift([], 40) == (0., 0.)
    pred = dict(winner=.6, home=dict(mean=110., sd=12., line=110.5, p=norm.sf(110.5, 110, 12)),
                away=dict(mean=105., sd=12., line=104.5, p=norm.sf(104.5, 105, 12)), total=dict(mean=215., sd=18., line=215.5, p=.48))
    moved = lf.apply_shift(pred, (1., .4))
    assert moved['home']['mean'] == 111. and moved['total']['mean'] == pytest.approx(216.4) and moved['winner'] == .6
    assert moved['home']['p'] == pytest.approx(norm.sf(110.5, 111, 12)) and lf.apply_shift(pred, (0., 0.)) is pred


def test_player_design_appends_the_environment_and_the_calibration_fits_it():
    rng = np.random.default_rng(0)
    rows = []
    for i in range(3000):
        p = float(rng.uniform(.2, .8))
        usage = float(rng.normal(0, .3))
        rows.append(dict(game_id=f'h{i % 12}', unit=1, team_id=1 if i % 2 else 2, date='2025-11-13', probability=p, min10=.6,
                         usage_trend=usage, y=int(rng.random() < expit(logit(p) + 1.5 * usage))))
    history = lf.TeamHistory(lf.game_records(records()))
    teams = {f'h{i}': (1, 2) for i in range(12)}
    features = list(lf.BASE) + list(lf.ENV)
    x = live.player_design(rows, {}, {}, dict.fromkeys(['Out'], 0.), features, (history, teams, {}))
    assert x.shape == (3000, len(features)) and np.allclose(x[:, 1], 1)
    w = live.fit_player_weights(x, np.array([r['y'] for r in rows], float))
    assert w[features.index('usage_trend')] > .5  # the signal put in the outcomes is found
    base = live.player_design(rows, {}, {}, {}, list(lf.BASE))
    assert base.shape == (3000, len(lf.BASE))


def test_season_shift_is_zero_without_option_and_uses_finished_games_with_it():
    base = model()
    done = [dict(g, season=live.SEASON) for g in history_games()[-6:]]
    assert live.season_shift(base, history_games()[:-6], done, V12) == ((0., 0.), 0)
    base['options'] = dict(live.DEFAULT_OPTIONS, team_shift_n0=10)
    (home, away), n = live.season_shift(base, history_games()[:-6], done, V12)
    assert n > 0 and np.isfinite(home) and np.isfinite(away)


def test_retrain_compare_checks_module_version_markets_and_inputs():
    new = model()
    new['inputs'] = dict(live_module_sha256=live.module_digest(), players_sha256='new', protocol_sha256='p2')
    new['options'] = dict(live.DEFAULT_OPTIONS, markets=list(live.PLAYER_MARKETS))
    old = dict(model(), version='nba-multimarket-live-1.3.2', inputs=dict(live_module_sha256='old', players_sha256='old', protocol_sha256='p1'))
    checks, detail = live.compare_models(new, old, retrain=True)
    assert all(checks.values()), checks
    new['inputs']['api_sha256'] = 'changed'
    assert not live.compare_models(new, old, retrain=True)[0]['inputs_changed_only_data_module_and_protocol']
