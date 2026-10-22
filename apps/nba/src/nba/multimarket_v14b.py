"""Research v1.4b: absolute and relative missing-value terms together, with a floor on participation probabilities."""
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from scipy.special import expit, logit
from scipy.stats import norm

from . import availability as av
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from . import multimarket_v14 as v14
from .audit import digest, write_json

FLOOR = .02
SPECS = dict(v13=dict(abs=True, rel=False), both=dict(abs=True, rel=True), abs_floor=dict(abs=True, rel=False),
             both_nofloor=dict(abs=True, rel=True))
TABLE = dict(v13=('plain', False), both=('g_league', True), abs_floor=('g_league', True), both_nofloor=('g_league', False))


def floored(table, floor=FLOOR):
    return {k: min(max(v, floor), 1 - floor) for k, v in table.items()}


def attach(rows, entries, table):
    """Absolute (mm/mp) and relative (rm/rp) expected missing minutes and points; zero when unobserved."""
    for r in rows:
        teams = entries.get(r['game_id'])
        r['observed'] = int(teams is not None)
        for side in ('home', 'away'):
            listed = teams.get(r[side + '_team'], []) if teams else []
            r['mm_' + side], r['mp_' + side] = v14.missing(listed, table, False) if teams else (0., 0.)
            r['rm_' + side], r['rp_' + side] = v14.missing(listed, table, True) if teams else (0., 0.)


def winner_x(rows, spec):
    cols = [v12.winner_features(rows)]
    if spec['abs']:
        cols.append(np.array([[r['mp_home'] / 10, r['mp_away'] / 10] for r in rows]))
    if spec['rel']:
        cols.append(np.array([[r['rp_home'] / 10, r['rp_away'] / 10] for r in rows]))
    return np.hstack(cols)


def shift_x(rows, side, spec):
    own, other = ('home', 'away') if side == 'home' else ('away', 'home')
    cols = []
    for r in rows:
        row = [r['b2b_' + own], r['b2b_' + other]]
        if spec['abs']:
            row += [r['mp_' + own] / 10, r['mp_' + other] / 10]
        if spec['rel']:
            row += [r['rp_' + own] / 10, r['rp_' + other] / 10]
        cols.append(row + [1.])
    return np.array(cols, float)


def team_predictions(train, test, spec):
    extra = 2 * (spec['abs'] + spec['rel'])
    w = v12.fit_ridge_logistic(winner_x(train, spec), [r['home_win'] for r in train],
                               np.concatenate([v12.ELO_PRIOR, np.zeros(extra)]), .002)
    p_win = expit(winner_x(test, spec) @ w)
    shifts, residuals = {}, []
    penalty = 5 * np.diag([1.] * (2 + extra) + [0.])
    for side in ('home', 'away'):
        x = shift_x(train, side, spec)
        resid = np.array([r[side + '_points'] - r[side + '_mean'] for r in train])
        shifts[side] = np.linalg.solve(x.T @ x + penalty, x.T @ resid)
        residuals.append(resid - x @ shifts[side])
    covariance = np.cov(np.vstack(residuals))
    mean = {side: np.array([r[side + '_mean'] for r in test]) + shift_x(test, side, spec) @ shifts[side]
            for side in ('home', 'away')}
    out = []
    for i, (r, p) in enumerate(zip(test, p_win)):
        total_line = np.floor(r['home_baseline'] + r['away_baseline']) + .5
        out.append(dict(
            winner=float(p),
            team_points_home=float(norm.sf(np.floor(r['home_baseline']) + .5, mean['home'][i], np.sqrt(covariance[0, 0]))),
            team_points_away=float(norm.sf(np.floor(r['away_baseline']) + .5, mean['away'][i], np.sqrt(covariance[1, 1]))),
            game_total=float(norm.sf(total_line, mean['home'][i] + mean['away'][i], np.sqrt(covariance.sum())))))
    return out, dict(winner_weights=w.tolist(), shifts={k: v.tolist() for k, v in shifts.items()})


def player_x(rows, probabilities, index, entries, table):
    absolute = v14.player_features(rows, index, entries, table, False)
    relative = v14.player_features(rows, index, entries, table, True)
    return np.column_stack([logit(np.clip(probabilities, 1e-6, 1 - 1e-6)), np.ones(len(rows)),
                            absolute, relative[:, 2]])


def participation(statuses, index, games, table):
    return v14.participation_logloss(statuses, index, games, table)


def evaluate(players, games, protocol, v12_protocol, injury_path, api_dir, output):
    seasons = sorted({g['season'] for g in games})
    index = {(r['game_id'], str(r['player_id'])): r for r in players}
    game_season = {g['game_id']: g['season'] for g in games}
    tips = av.tipoff_map(api_dir, games)
    reports = av.read_reports(injury_path)
    legacy = av.status_map(reports, tips)
    maps = {'plain': v14.status_map(reports, tips, False), 'g_league': v14.status_map(reports, tips, True)}
    if maps['plain'] != legacy:
        raise ValueError('v1.3 statuses do not reproduce')
    entries = {k: v14.trailing_entries(players, games, *maps[k]) for k in maps}
    legacy_entries = av.trailing_entries(players, games, *legacy)
    observed = legacy[1]
    by_season = defaultdict(list)
    for r in v12.team_games(games, v12_protocol):
        by_season[r['season']].append(r)
    samples, _ = v12.player_weight_run(players, v12_protocol, .25)
    report = dict(version=protocol['version'], retrospective_not_confirmatory=True, availability={}, markets={}, weights={})
    for season in v12_protocol['test_seasons']:
        start, end = v12.training_window(season, seasons, v12_protocol)
        train_seasons = [s for s in seasons if s > v12_protocol['burn_in_season'] and start <= v12.season_start(s) < end]
        train_games = {g for g in observed if game_season.get(g) in train_seasons}
        test_games = {g for g in observed if game_season.get(g) == season}
        base = {k: v14.play_table(maps[k][0], index, train_games) for k in maps}
        tables = {name: (floored(base[key]) if flag else base[key]) for name, (key, flag) in TABLE.items()}
        report['availability'][season] = {
            'v13': dict(play_probability=tables['v13'], **participation(maps['plain'][0], index, test_games, tables['v13'])),
            'g_league_no_floor': dict(play_probability=tables['both_nofloor'],
                                      **participation(maps['g_league'][0], index, test_games, tables['both_nofloor'])),
            'g_league_floor': dict(play_probability=tables['both'],
                                   **participation(maps['g_league'][0], index, test_games, tables['both']))}
        team, player = {}, {}
        for name, spec in SPECS.items():
            key = TABLE[name][0]
            train = [dict(r) for s in train_seasons for r in by_season[s]]
            test = [dict(r) for r in by_season[season]]
            attach(train, entries[key], tables[name]); attach(test, entries[key], tables[name])
            predicted, fit = team_predictions(train, test, spec)
            team[name] = (test, predicted)
            report['weights'].setdefault(season, {})[name] = fit
        # the reference must equal multimarket_v13 on the same inputs
        train = [dict(r) for s in train_seasons for r in by_season[s]]
        test = [dict(r) for r in by_season[season]]
        v13.attach(train, legacy_entries, tables['v13']); v13.attach(test, legacy_entries, tables['v13'])
        reference, _ = v13.team_predictions(train, test)
        if not all(np.allclose([p[k] for p in reference], [p[k] for p in team['v13'][1]], atol=1e-12)
                   for k in ('winner', 'team_points_home', 'game_total')):
            raise ValueError('v1.3 team markets do not reproduce')
        for market in v12.PLAYER_MARKETS:
            tr = [r for r in samples[market] if start <= r['date'] < end]
            te = v12.season_rows(samples[market], season)
            for name in ('v13', 'both'):
                key, table = TABLE[name][0], tables[name]
                prior = np.array([1., 0., 0., 0., 0.] + ([0.] if SPECS[name]['rel'] else []))
                if SPECS[name]['rel']:
                    fx = lambda rows: player_x(rows, [r['probability'] for r in rows], index, entries[key], table)
                else:
                    fx = lambda rows: np.column_stack([logit(np.clip([r['probability'] for r in rows], 1e-6, 1 - 1e-6)), np.ones(len(rows)),
                                                       v14.player_features(rows, index, entries[key], table, False)])
                w = v12.fit_ridge_logistic(fx(tr), [r['y'] for r in tr], prior, .002)
                player[name, market] = (te, expit(fx(te) @ w), w)
        for market in ('winner', 'team_points', 'game_total'):
            ref = v14.market_rows(*team['v13'], market)
            out = {}
            for name in ('both', 'abs_floor', 'both_nofloor'):
                cand = v14.market_rows(*team[name], market)
                out[name + '_vs_v13'] = v12.compare([x[0] for x in cand], [x[1] for x in cand], [x[2] for x in cand],
                                                    [x[2] for x in ref], v12_protocol)
            cand = v14.market_rows(*team['both'], market)
            floor_only = v14.market_rows(*team['abs_floor'], market)
            out['both_vs_abs_floor'] = v12.compare([x[0] for x in cand], [x[1] for x in cand], [x[2] for x in cand],
                                                   [x[2] for x in floor_only], v12_protocol)
            report['markets'].setdefault(market, {})[season] = out
        for market in v12.PLAYER_MARKETS:
            te, ref, _ = player[('v13', market)]
            _, cand, w = player[('both', market)]
            report['markets'].setdefault(market, {})[season] = dict(
                both_vs_v13=dict(v12.compare([r['date'] for r in te], [r['y'] for r in te], cand, ref, v12_protocol),
                                 weights=dict(zip(['logit', 'bias', 'own_questionable', 'own_probable', 'teammates_abs', 'teammates_rel'], w.tolist()))))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'comparison_v14b.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--data', '--protocol', '--v12-protocol', '--injuries', '--api-dir', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    load = lambda p: json.loads(Path(p).read_bytes())
    if load(Path(a.output) / 'protocol_frozen.json')['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    players = m1.read_rows(Path(a.data) / 'players.jsonl.gz')
    games = load(Path(a.data) / 'games.json')
    report = evaluate(players, games, load(a.protocol), load(a.v12_protocol), a.injuries, a.api_dir, a.output)
    write_json(Path(a.output) / 'inputs_v14b.json', dict(
        source_sha256=digest(__file__), v14_sha256=digest(Path(v14.__file__)), availability_sha256=digest(Path(av.__file__)),
        protocol_sha256=digest(a.protocol), injuries_sha256=digest(a.injuries),
        players_sha256=digest(Path(a.data) / 'players.jsonl.gz'), games_sha256=digest(Path(a.data) / 'games.json')))
    print(json.dumps({s: {k: v['logloss'] for k, v in x.items()} for s, x in report['availability'].items()}, allow_nan=False))


if __name__ == '__main__':
    main()
