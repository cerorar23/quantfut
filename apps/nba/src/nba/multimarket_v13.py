"""Research v1.3: v1.2 plus point-in-time availability from official injury reports."""
from collections import defaultdict
import json
from pathlib import Path

import numpy as np
from scipy.special import expit, logit
from scipy.stats import norm

from . import availability as av
from . import multimarket as m1
from . import multimarket_v12 as v12
from .audit import digest, write_json


def attach(rows, entries, table):
    """Add missing-minutes/points features to team-game rows (zero when the game is unobserved)."""
    for r in rows:
        teams = entries.get(r['game_id'])
        r['observed'] = int(teams is not None)
        for side in ('home', 'away'):
            minutes, points = av.missing(teams.get(r[side + '_team'], []), table) if teams else (0., 0.)
            r['mm_' + side], r['mp_' + side] = minutes, points


def winner_x(rows):
    return np.hstack([v12.winner_features(rows),
                      np.array([[r['mp_home'] / 10, r['mp_away'] / 10] for r in rows])])


def shift_x(rows, side):
    own, other = ('home', 'away') if side == 'home' else ('away', 'home')
    return np.array([[r['b2b_' + own], r['b2b_' + other], r['mp_' + own] / 10, r['mp_' + other] / 10, 1.]
                     for r in rows], float)


def team_predictions(train, test):
    prior = np.concatenate([v12.ELO_PRIOR, [0., 0.]])
    w = v12.fit_ridge_logistic(winner_x(train), [r['home_win'] for r in train], prior, .002)
    p_win = expit(winner_x(test) @ w)
    shifts, residuals = {}, []
    for side in ('home', 'away'):
        x = shift_x(train, side)
        resid = np.array([r[side + '_points'] - r[side + '_mean'] for r in train])
        shifts[side] = np.linalg.solve(x.T @ x + 5 * np.diag([1., 1., 1., 1., 0.]), x.T @ resid)
        residuals.append(resid - x @ shifts[side])
    covariance = np.cov(np.vstack(residuals))
    mean = {side: np.array([r[side + '_mean'] for r in test]) + shift_x(test, side) @ shifts[side]
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


def player_features(rows, index, entries, table):
    """own questionable/doubtful, own probable, teammates' expected missing minutes / 48."""
    out = np.zeros((len(rows), 3))
    for i, r in enumerate(rows):
        box = index.get((r['game_id'], str(r['unit'])))
        teams = entries.get(r['game_id'])
        if box is None or teams is None:
            continue
        status = None
        listed = teams.get(box['team_id'], [])
        for player, s, minutes, _ in listed:
            if player == str(r['unit']):
                status = s
        out[i, 0] = int(status in ('Questionable', 'Doubtful'))
        out[i, 1] = int(status == 'Probable')
        out[i, 2] = sum(m * (1 - table[s]) for player, s, m, _ in listed if player != str(r['unit'])) / 48
    return out


def fit_player(rows, feats, protocol):
    x = np.column_stack([logit(np.clip([r['probability'] for r in rows], 1e-6, 1 - 1e-6)), np.ones(len(rows)), feats])
    prior = np.array([1., 0., 0., 0., 0.])
    return v12.fit_ridge_logistic(x, [r['y'] for r in rows], prior, .002)


def apply_player(rows, feats, w):
    x = np.column_stack([logit(np.clip([r['probability'] for r in rows], 1e-6, 1 - 1e-6)), np.ones(len(rows)), feats])
    return expit(x @ w)


def availability_scores(statuses, index, season_games, table, base_rate):
    """Participation log loss on listed boxscore rows: status table vs trailing base rate."""
    y, p_status, p_base = [], [], []
    for (game, player), (status, _) in statuses.items():
        if game not in season_games:
            continue
        row = index.get((game, player))
        if row is None:
            continue
        y.append(int(row['participated'] and row['minutes'] > 0))
        p_status.append(table[status]); p_base.append(base_rate)
    y, p_status, p_base = (np.array(a, float) for a in (y, p_status, p_base))
    ll = lambda p: float(np.mean(-y * np.log(p) - (1 - y) * np.log1p(-p)))
    return dict(n=len(y), participation_rate=float(y.mean()), logloss_status_table=ll(p_status),
                logloss_base_rate=ll(p_base))


def evaluate(players, games, protocol, v12_protocol, v1_protocol, injury_path, api_dir, output):
    seasons = sorted({g['season'] for g in games})
    evaluated = [v12_protocol['selection_season']] + v12_protocol['test_seasons']
    index = {(r['game_id'], str(r['player_id'])): r for r in players}
    tips = av.tipoff_map(api_dir, games)
    statuses, observed = av.status_map(av.read_reports(injury_path), tips)
    entries = av.trailing_entries(players, games, statuses, observed)
    game_season = {g['game_id']: g['season'] for g in games}
    report = dict(version=protocol['version'], retrospective_not_confirmatory=True,
                  coverage={s: dict(games=sum(1 for g in games if g['season'] == s),
                                    observed=sum(1 for g in observed if game_season.get(g) == s)) for s in seasons},
                  availability={}, markets={})
    rows = v12.team_games(games, v12_protocol)
    by_season = defaultdict(list)
    for r in rows:
        by_season[r['season']].append(r)
    samples, _ = v12.player_weight_run(players, v12_protocol, .25)
    for season in evaluated:
        start, end = v12.training_window(season, seasons, v12_protocol)
        train_seasons = [s for s in seasons if s > v12_protocol['burn_in_season'] and start <= v12.season_start(s) < end]
        train_games = {g for g in observed if game_season.get(g) in train_seasons}
        table = av.play_table(statuses, index, train_games)
        base_rate = float(np.mean([int(index[(g, p)]['participated'] and index[(g, p)]['minutes'] > 0)
                                   for (g, p) in statuses if g in train_games and (g, p) in index]))
        report['availability'][season] = dict(
            play_probability=table, **availability_scores(statuses, index, {g for g in observed if game_season.get(g) == season},
                                                         table, base_rate))
        train = [dict(r) for s in train_seasons for r in by_season[s]]
        test = [dict(r) for r in by_season[season]]
        attach(train, entries, table); attach(test, entries, table)
        new, fit = team_predictions(train, test)
        old, _ = v12.team_predictions(train, test, v12_protocol)
        for market in ('winner', 'team_points', 'game_total'):
            ys, cs, rs, ds = [], [], [], []
            for r, a, b in zip(test, new, old):
                for m_, _, line, actual, prob in v12.team_market_rows(r, a):
                    if m_ == market:
                        ys.append(int(actual > line)); cs.append(prob); ds.append(r['date'])
                for m_, _, line, actual, prob in v12.team_market_rows(r, b):
                    if m_ == market:
                        rs.append(prob)
            report['markets'].setdefault(market, {})[season] = dict(
                vs_v12=v12.compare(ds, ys, cs, rs, v12_protocol),
                observed_share=float(np.mean([r['observed'] for r in test])),
                fit=fit if market == 'winner' else None)
    for market in v12.PLAYER_MARKETS:
        per_season = {}
        for season in evaluated:
            start, end = v12.training_window(season, seasons, v12_protocol)
            train_seasons = [s for s in seasons if s > v12_protocol['burn_in_season'] and start <= v12.season_start(s) < end]
            table = av.play_table(statuses, index, {g for g in observed if game_season.get(g) in train_seasons})
            train = [r for r in samples[market] if start <= r['date'] < end]
            test = v12.season_rows(samples[market], season)
            w = fit_player(train, player_features(train, index, entries, table), protocol)
            cand = apply_player(test, player_features(test, index, entries, table), w)
            ref = m1.apply_calibration(np.array([r['probability'] for r in test]), v12.calibrate(samples[market], (start, end)))
            per_season[season] = v12.compare([r['date'] for r in test], [r['y'] for r in test], cand, ref, v12_protocol)
            per_season[season]['weights'] = dict(zip(['logit', 'bias', 'own_questionable', 'own_probable', 'teammates_missing'], w.tolist()))
        report['markets'][market] = per_season
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'comparison_v13.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--v12-protocol', required=True)
    parser.add_argument('--v1-protocol', required=True)
    parser.add_argument('--injuries', required=True)
    parser.add_argument('--api-dir', required=True)
    parser.add_argument('--output', required=True)
    a = parser.parse_args()
    load = lambda p: json.loads(Path(p).read_bytes())
    players = m1.read_rows(Path(a.data) / 'players.jsonl.gz')
    games = load(Path(a.data) / 'games.json')
    report = evaluate(players, games, load(a.protocol), load(a.v12_protocol), load(a.v1_protocol), a.injuries, a.api_dir, a.output)
    write_json(Path(a.output) / 'inputs_v13.json', dict(
        source_sha256=digest(__file__), availability_sha256=digest(Path(__file__).with_name('availability.py')),
        protocol_sha256=digest(a.protocol), injuries_sha256=digest(a.injuries),
        players_sha256=digest(Path(a.data) / 'players.jsonl.gz'), games_sha256=digest(Path(a.data) / 'games.json')))
    print(json.dumps(report['coverage'], allow_nan=False))


if __name__ == '__main__':
    main()
