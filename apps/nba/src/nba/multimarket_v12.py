"""Research v1.2: walk-forward refits, margin Elo and rest effects. Never replaces sealed RUN071."""
from collections import defaultdict, deque
from datetime import date
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import norm

from . import multimarket as m1
from .audit import digest, write_json

PLAYER_MARKETS = tuple('player_' + s for s in m1.STATS)
ELO_PRIOR = np.array([np.log(10) / 4, 0., 0., 0.65 * np.log(10) / 4])  # per 100 Elo points


def season_start(season):
    return f'{season[:4]}-08-01'


def training_window(season, seasons, protocol):
    """Date range [start, end) of the scored seasons before `season`, at most two."""
    scored = [s for s in seasons if s > protocol['burn_in_season'] and s < season]
    if not scored:
        raise ValueError('no training season before ' + season)
    chosen = scored[-2:]
    return season_start(chosen[0]), season_start(season)


def mov_multiplier(margin, winner_gap):
    return (abs(margin) + 3) ** .8 / (7.5 + .006 * winner_gap)


def team_games(games, protocol):
    """One feature row per game; every feature uses only strictly earlier dates."""
    margins = defaultdict(list)
    for g in games:
        margins[g['season']].append(g['home']['points'] - g['away']['points'])
    order = sorted(margins)
    days = defaultdict(list)
    for g in games:
        days[g['date']].append(g)
    plain, mov = defaultdict(lambda: 1500.), defaultdict(lambda: 1500.)
    history, last = defaultdict(lambda: deque(maxlen=20)), {}
    season, rows = None, []
    for cut in sorted(days):
        current = days[cut][0]['season']
        if season is not None and season != current:
            for table in (plain, mov):
                for key in table:
                    table[key] = 1500 + (table[key] - 1500) * (1 - protocol['elo_season_regression'])
        season = current
        position = order.index(current)
        previous = [x for s in order[max(0, position - 2):position] for x in margins[s]]
        home_advantage = float(np.mean(previous)) if previous else None
        today = date.fromisoformat(cut)
        for g in days[cut]:
            h, a = g['home'], g['away']
            hh = m1.eligible(history[h['team_id']], cut, protocol)
            ah = m1.eligible(history[a['team_id']], cut, protocol)
            if home_advantage is None or min(len(hh), len(ah)) < protocol['min_history']:
                continue
            b2b = [int(t in last and (today - last[t]).days == 1) for t in (h['team_id'], a['team_id'])]
            home_raw = (np.mean([r['points'] for r in hh]) + np.mean([r['allowed'] for r in ah])) / 2
            away_raw = (np.mean([r['points'] for r in ah]) + np.mean([r['allowed'] for r in hh])) / 2
            gap_plain = plain[h['team_id']] - plain[a['team_id']]
            rows.append(dict(
                game_id=g['game_id'], date=cut, season=current, home_team=h['team_id'], away_team=a['team_id'], home_points=h['points'], away_points=a['points'],
                home_win=int(h['points'] > a['points']), b2b_home=b2b[0], b2b_away=b2b[1],
                elo_gap_mov=mov[h['team_id']] - mov[a['team_id']],
                v1_probability=float(1 / (1 + 10 ** (-(gap_plain + protocol['elo_home']) / 400))),
                home_mean=float(home_raw + home_advantage / 2), away_mean=float(away_raw - home_advantage / 2),
                home_baseline=float(np.mean([r['points'] for r in hh[-10:]])),
                away_baseline=float(np.mean([r['points'] for r in ah[-10:]]))))
        for g in days[cut]:
            h, a = g['home'], g['away']
            for table, scaled in ((plain, False), (mov, True)):
                gap = table[h['team_id']] - table[a['team_id']] + protocol['elo_home']
                expected = 1 / (1 + 10 ** (-gap / 400))
                result = int(h['points'] > a['points'])
                factor = 1.
                if scaled:
                    winner_gap = gap if result else -gap
                    factor = mov_multiplier(h['points'] - a['points'], winner_gap)
                delta = protocol['elo_k'] * factor * (result - expected)
                table[h['team_id']] += delta
                table[a['team_id']] -= delta
            for own, other in ((h, a), (a, h)):
                history[own['team_id']].append(dict(date=cut, points=own['points'], allowed=other['points']))
                last[own['team_id']] = today
    return rows


def fit_ridge_logistic(x, y, prior, l2):
    x, y = np.asarray(x, float), np.asarray(y, float)

    def objective(w):
        z = x @ w
        return float(np.mean(np.logaddexp(0, z) - y * z) + l2 * np.sum((w - prior) ** 2))
    result = minimize(objective, prior, method='L-BFGS-B')
    if not result.success:
        raise ValueError('logistic fit failed')
    return result.x


def winner_features(rows):
    return np.array([[r['elo_gap_mov'] / 100, r['b2b_home'], r['b2b_away'], 1.] for r in rows])


def fit_shift(rows, side, protocol):
    """Ridge shift of the v1 mean on rest flags; returns weights and residual vector."""
    own, other = ('home', 'away') if side == 'home' else ('away', 'home')
    x = np.array([[r['b2b_' + own], r['b2b_' + other], 1.] for r in rows], float)
    resid = np.array([r[own + '_points'] - r[own + '_mean'] for r in rows])
    gram = x.T @ x + 5 * np.diag([1., 1., 0.])
    return np.linalg.solve(gram, x.T @ resid), x


def team_predictions(rows, test, protocol):
    """Fitted on `rows` only; returns the probability dict per market for each game in `test`."""
    w = fit_ridge_logistic(winner_features(rows), [r['home_win'] for r in rows], ELO_PRIOR, .002)
    p_win = expit(winner_features(test) @ w)
    shifts, residuals = {}, []
    for side in ('home', 'away'):
        shifts[side], x = fit_shift(rows, side, protocol)
        residuals.append(np.array([r[side + '_points'] - r[side + '_mean'] for r in rows]) - x @ shifts[side])
    covariance = np.cov(np.vstack(residuals))
    out = []
    for r, p in zip(test, p_win):
        means = {}
        for side, other in (('home', 'away'), ('away', 'home')):
            means[side] = r[side + '_mean'] + shifts[side] @ [r['b2b_' + side], r['b2b_' + other], 1.]
        record = dict(winner=float(p))
        for side, idx in (('home', 0), ('away', 1)):
            line = np.floor(r[side + '_baseline']) + .5
            record['team_points_' + side] = float(norm.sf(line, means[side], np.sqrt(covariance[idx, idx])))
        line = np.floor(r['home_baseline'] + r['away_baseline']) + .5
        record['game_total'] = float(norm.sf(line, means['home'] + means['away'], np.sqrt(covariance.sum())))
        out.append(record)
    return out, dict(winner_weights=w.tolist(), shifts={k: v.tolist() for k, v in shifts.items()},
                     covariance=covariance.tolist(), train_games=len(rows))


def metrics(y, p, reference=None):
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    loss = (p - y) ** 2
    out = dict(n=len(y), brier=float(loss.mean()),
               logloss=float(np.mean(-y * np.log(p) - (1 - y) * np.log1p(-p))),
               bias=float(p.mean() - y.mean()), accuracy=float(((p >= .5) == y).mean()))
    return out, loss


def date_bootstrap(dates, difference, replicates, seed):
    """Resample whole dates; returns the 95% interval of the mean paired difference."""
    keys = sorted(set(dates))
    index = {k: i for i, k in enumerate(keys)}
    total, count = np.zeros(len(keys)), np.zeros(len(keys))
    for d, v in zip(dates, difference):
        total[index[d]] += v
        count[index[d]] += 1
    rng = np.random.default_rng(seed)
    pick = rng.integers(0, len(keys), size=(replicates, len(keys)))
    means = total[pick].sum(axis=1) / count[pick].sum(axis=1)
    return np.quantile(means, [.025, .975]).tolist()


def compare(dates, y, candidate, reference, protocol):
    cand, c_loss = metrics(y, candidate)
    ref, r_loss = metrics(y, reference)
    diff = c_loss - r_loss
    return dict(candidate=cand, reference=ref, paired_brier_difference=float(diff.mean()),
                ci95_date_bootstrap=date_bootstrap(dates, diff, protocol['bootstrap'], protocol['seed']))


def player_weight_run(players, protocol, weight):
    local = dict(protocol, empirical_weight=weight, train_end='2022-07-01', validation_end='2023-07-01')
    samples, _, _ = m1.player_samples(players, local)
    return samples, local


def calibrate(rows, window, field='probability'):
    start, end = window
    return m1.fit_calibration(rows, dict(train_end=start, validation_end=end), field)


def season_rows(rows, season):
    return [r for r in rows if m1.season_label(r['date']) == season]


def choose_weight(players, protocol):
    """Selection uses only the selection season, calibrated on the seasons before it."""
    season = protocol['selection_season']
    scores, runs = {}, {}
    for weight in protocol['player_empirical_weight_candidates']:
        samples, _ = player_weight_run(players, protocol, weight)
        runs[weight] = samples
        window = training_window(season, sorted({m1.season_label(r['date']) for r in samples['player_points']}), protocol)
        losses = []
        for market in PLAYER_MARKETS:
            calibration = calibrate(samples[market], window)
            test = season_rows(samples[market], season)
            p = m1.apply_calibration(np.array([r['probability'] for r in test]), calibration)
            losses.append(float(np.mean((p - np.array([r['y'] for r in test])) ** 2)))
        scores[weight] = float(np.mean(losses))
    best = min(sorted(scores), key=lambda w: scores[w])
    return best, scores, runs


def team_market_rows(r, p):
    """(market, key, line, actual, candidate probability) for one game."""
    total_line = np.floor(r['home_baseline'] + r['away_baseline']) + .5
    return [('winner', r['game_id'], .5, r['home_win'], p['winner']),
            ('team_points', (r['game_id'], r['home_team']), np.floor(r['home_baseline']) + .5, r['home_points'], p['team_points_home']),
            ('team_points', (r['game_id'], r['away_team']), np.floor(r['away_baseline']) + .5, r['away_points'], p['team_points_away']),
            ('game_total', r['game_id'], total_line, r['home_points'] + r['away_points'], p['game_total'])]


def evaluate(players, games, protocol, v1_protocol, output):
    best, selection, runs = choose_weight(players, protocol)
    seasons = sorted({g['season'] for g in games})
    evaluated = [protocol['selection_season']] + protocol['test_seasons']
    report = dict(version=protocol['version'], selected_empirical_weight=best, selection_mean_brier=selection,
                  retrospective_not_confirmatory=True, markets={})
    rows = team_games(games, protocol)
    by_season = defaultdict(list)
    for r in rows:
        by_season[r['season']].append(r)
    v1_samples, _, _, _ = m1.team_samples(games, v1_protocol)
    v1_cal = {k: m1.fit_calibration(v1_samples[k], v1_protocol) for k in ('winner', 'team_points', 'game_total')}
    v1_key = {'winner': lambda x: x['game_id'], 'team_points': lambda x: (x['game_id'], x['unit']),
              'game_total': lambda x: x['game_id']}
    sealed = {k: {v1_key[k](x): float(m1.apply_calibration(x['probability'], v1_cal[k])) for x in v1_samples[k]}
              for k in v1_cal}
    raw_v1 = {k: {v1_key[k](x): x['probability'] for x in v1_samples[k]} for k in v1_cal}
    for season in evaluated:
        start, end = training_window(season, seasons, protocol)
        train = [r for s in seasons if s > protocol['burn_in_season'] and start <= season_start(s) < end
                 for r in by_season[s]]
        test = by_season[season]
        predicted, fit = team_predictions(train, test, protocol)
        wf_cal = {}
        for market in v1_cal:
            history = [dict(date=x['date'], probability=x['probability'], y=x['y']) for x in v1_samples[market]]
            wf_cal[market] = calibrate(history, (start, end))
        gathered = defaultdict(lambda: defaultdict(list))
        for r, p in zip(test, predicted):
            for market, key, line, actual, prob in team_market_rows(r, p):
                if key not in sealed[market]:
                    continue
                g = gathered[market]
                g['date'].append(r['date']); g['y'].append(int(actual > line)); g['cand'].append(prob)
                g['sealed'].append(sealed[market][key])
                g['wf'].append(float(m1.apply_calibration(raw_v1[market][key], wf_cal[market])))
        for market, g in gathered.items():
            report['markets'].setdefault(market, {})[season] = dict(
                vs_v1_sealed=compare(g['date'], g['y'], g['cand'], g['sealed'], protocol),
                vs_v1_walk_forward=compare(g['date'], g['y'], g['cand'], g['wf'], protocol),
                fit=fit if market == 'winner' else None)
    reference = runs[.25]
    chosen = runs[best]
    player_cal = {k: m1.fit_calibration(reference[k], dict(train_end='2022-07-01', validation_end='2023-07-01'))
                  for k in PLAYER_MARKETS}
    for market in PLAYER_MARKETS:
        per_season = {}
        for season in evaluated:
            calibration = calibrate(chosen[market], training_window(season, seasons, protocol))
            test_new, test_old = season_rows(chosen[market], season), season_rows(reference[market], season)
            if [(r['game_id'], r['unit']) for r in test_new] != [(r['game_id'], r['unit']) for r in test_old]:
                raise ValueError('player row alignment lost')
            cand = m1.apply_calibration(np.array([r['probability'] for r in test_new]), calibration)
            old = m1.apply_calibration(np.array([r['probability'] for r in test_old]), player_cal[market])
            per_season[season] = compare([r['date'] for r in test_new], [r['y'] for r in test_new], cand, old, protocol)
            per_season[season]['calibration'] = calibration
        report['markets'][market] = per_season
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'comparison_v12.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--v1-protocol', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    protocol = json.loads(Path(args.protocol).read_bytes())
    v1 = json.loads(Path(args.v1_protocol).read_bytes())
    players = m1.read_rows(Path(args.data) / 'players.jsonl.gz')
    games = json.loads((Path(args.data) / 'games.json').read_bytes())
    report = evaluate(players, games, protocol, v1, args.output)
    write_json(Path(args.output) / 'inputs_v12.json', dict(
        source_sha256=digest(__file__), protocol_sha256=digest(args.protocol),
        players_sha256=digest(Path(args.data) / 'players.jsonl.gz'), games_sha256=digest(Path(args.data) / 'games.json')))
    print(json.dumps(dict(selected_empirical_weight=report['selected_empirical_weight']), allow_nan=False))


if __name__ == '__main__':
    main()
