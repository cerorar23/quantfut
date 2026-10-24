"""Calibrate and anchor the engine's team probabilities on the bet365 close for nine markets.

Full game, first half and first quarter: moneyline, spread, total. Research only. Protocol: nba_team_markets_protocol.json,
frozen before running. The score model is the v1.5 candidate arm (Elo winner, v1 team means, residual covariance)."""
from collections import defaultdict
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.special import expit, logit
from scipy.stats import norm

from . import availability as av
from . import injury_t60
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from . import multimarket_v15 as v15
from . import props_residual as pr
from .audit import digest, write_json

MARKETS = ('ml_game', 'spread_game', 'total_game', 'ml_h1', 'spread_h1', 'total_h1', 'ml_q1', 'spread_q1', 'total_q1')
SEASONS = ('2023-24', '2024-25', '2025-26')
COLS = ('model_delta', 'b2b_home', 'b2b_away', 'mp_home', 'mp_away')
ARMS = {'A_recalibration': (), 'B_model': ('model_delta',), 'C_full': COLS}
PRIMARY = 'C_full'
BOOTSTRAP, SEED, LEVEL = 400, 20261026, 1 - .05 / 9


def score_model(train, test):
    """The v1.5 candidate arm, returning means and covariance instead of probabilities at fixed lines."""
    prior = np.concatenate([v12.ELO_PRIOR, [0., 0.]])
    w = v12.fit_ridge_logistic(v13.winner_x(train), [r['home_win'] for r in train], prior, .002)
    p_win = expit(v13.winner_x(test) @ w)
    shifts, residuals = {}, []
    for side in ('home', 'away'):
        x = v13.shift_x(train, side)
        resid = np.array([r[side + '_points'] - r[side + '_mean'] for r in train])
        shifts[side] = np.linalg.solve(x.T @ x + 5 * np.diag([1., 1., 1., 1., 0.]), x.T @ resid)
        residuals.append(resid - x @ shifts[side])
    cov = np.cov(np.vstack(residuals))
    mean = {side: np.array([r[side + '_mean'] for r in test]) + v13.shift_x(test, side) @ shifts[side] for side in ('home', 'away')}
    sigma_m = float(np.sqrt(cov[0, 0] + cov[1, 1] - 2 * cov[0, 1]))
    sigma_t = float(np.sqrt(cov[0, 0] + cov[1, 1] + 2 * cov[0, 1]))
    out = []
    for i, (r, p) in enumerate(zip(test, p_win)):
        out.append(dict(game_id=r['game_id'], date=r['date'], season=r['season'], p_win=float(p), home_win=r['home_win'],
                        mu_m=float(sigma_m * norm.ppf(np.clip(p, 1e-6, 1 - 1e-6))), sigma_m=sigma_m,
                        mu_t=float(mean['home'][i] + mean['away'][i]), sigma_t=sigma_t,
                        b2b_home=r['b2b_home'], b2b_away=r['b2b_away'], mp_home=r['mp_home'] / 10, mp_away=r['mp_away'] / 10))
    return out


def exceed(mu, sd, threshold):
    """P(X > threshold) for an integer-valued X ~ Normal(mu, sd) with continuity correction.

    A threshold on the integer grid has a push at X == threshold: the probability is conditioned on no push.
    Returns None for thresholds that are neither integers nor half-integers."""
    twice = threshold * 2
    if abs(twice - round(twice)) > 1e-9:
        return None
    if round(twice) % 2:
        return float(norm.sf(threshold, mu, sd))
    above, below = norm.sf(threshold + .5, mu, sd), norm.cdf(threshold - .5, mu, sd)
    return float(above / (above + below))


def fit_period(pairs):
    """Least squares of the period total on mu_t and the period margin on mu_m. pairs: (pred, period home pts, away pts)."""
    mu_t = np.array([p['mu_t'] for p, _, _ in pairs]); mu_m = np.array([p['mu_m'] for p, _, _ in pairs])
    total = np.array([h + a for _, h, a in pairs], float); margin = np.array([h - a for _, h, a in pairs], float)
    out = {}
    for name, x, y in (('total', mu_t, total), ('margin', mu_m, margin)):
        design = np.column_stack([np.ones(len(x)), x])
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        out[name] = dict(a=float(coef[0]), b=float(coef[1]), sd=float(np.std(y - design @ coef, ddof=2)), n=len(y))
    return out


def model_probability(market, pred, line, period_fit):
    kind, period = market.split('_')
    if period == 'game':
        if kind == 'ml':
            return pred['p_win']
        return exceed(pred['mu_t'], pred['sigma_t'], line) if kind == 'total' else exceed(pred['mu_m'], pred['sigma_m'], -line)
    if period_fit is None:
        return None
    if kind == 'total':
        return exceed(period_fit['total']['a'] + period_fit['total']['b'] * pred['mu_t'], period_fit['total']['sd'], line)
    mean = period_fit['margin']['a'] + period_fit['margin']['b'] * pred['mu_m']
    return exceed(mean, period_fit['margin']['sd'], 0. if kind == 'ml' else -line)


def build_units(preds, bets_rows, period_points):
    """Join bet365 close rows with the score model; period fits use only games of earlier seasons."""
    by_game = {p['game_id']: p for p in preds}
    fits, drops = {}, defaultdict(int)
    for season in SEASONS:
        for period in ('h1', 'q1'):
            earlier = [(by_game[g], *pts) for g, (s, pts) in period_points[period].items() if s < season and g in by_game]
            fits[(season, period)] = fit_period(earlier) if len(earlier) >= 200 else None
    units = []
    for r in bets_rows:
        market = r['market']
        if market not in MARKETS:
            continue
        pred = by_game.get(r['game_id'])
        if pred is None:
            drops['no_score_model_prediction'] += 1
            continue
        if r['y_close'] is None:
            drops['push_or_unsettled'] += 1
            continue
        period = market.split('_')[1]
        q = model_probability(market, pred, r['close']['line'], fits.get((pred['season'], period)) if period != 'game' else None)
        if q is None:
            drops['no_period_fit_or_odd_line'] += 1
            continue
        lk = pr.clip_logit(r['close']['p1_novig'])
        units.append(dict(game_id=r['game_id'], date=r['date'], season=pred['season'], market=market, line=r['close']['line'],
                          market_p=float(r['close']['p1_novig']), y=int(r['y_close']), q=float(q),
                          model_delta=float(pr.clip_logit(q) - lk), b2b_home=pred['b2b_home'], b2b_away=pred['b2b_away'],
                          mp_home=pred['mp_home'], mp_away=pred['mp_away']))
    return units, dict(drops), {f'{s} {p}': f for (s, p), f in fits.items()}


def delta(rows, p, reference):
    y = np.array([r['y'] for r in rows], float)
    diff = (np.asarray(p) - y) ** 2 - (np.asarray(reference) - y) ** 2
    return dict(paired_brier_difference=float(diff.mean()),
                interval=pr.date_bootstrap([r['date'] for r in rows], diff, BOOTSTRAP, SEED, LEVEL))


def reliability(y, p, bins=10):
    order = np.argsort(p)
    return [dict(n=len(i), predicted=float(np.mean(p[i])), observed=float(np.mean(np.asarray(y)[i])))
            for i in np.array_split(order, bins) if len(i)]


def evaluate_market(rows, grid, test_season='2025-26'):
    train = [r for r in rows if r['season'] != test_season]
    test = [r for r in rows if r['season'] == test_season]
    y = np.array([r['y'] for r in test], float)
    market = np.array([r['market_p'] for r in test])
    q = np.array([r['q'] for r in test])
    arms, models = {}, {}
    for name, cols in ARMS.items():
        lam = pr.choose_lambda(train, cols, grid)
        models[name] = pr.fit(train, cols, lam)
        arms[name] = dict(lam=lam, p=pr.predict(models[name], test))
    lam_c = arms[PRIMARY]['lam']
    wf = pr.walk_forward(train, test, COLS, lam_c)
    shuffled = COLS[1:]
    placebo = pr.predict(pr.fit(pr.permute_within_date(train, shuffled, SEED), COLS, lam_c), pr.permute_within_date(test, shuffled, SEED + 1))
    report = dict(units=dict(train=len(train), test=len(test)), market=pr.scores(y, market), model_only=dict(
        scores=pr.scores(y, q), vs_market=delta(test, q, market)), arms={})
    for name, a in arms.items():
        report['arms'][name] = dict(lambda_=a['lam'], scores=pr.scores(y, a['p']), vs_market=delta(test, a['p'], market))
    report['arms'][PRIMARY]['vs_recalibration'] = delta(test, arms[PRIMARY]['p'], arms['A_recalibration']['p'])
    report['walk_forward'] = dict(scores=pr.scores(y, wf), vs_market=delta(test, wf, market))
    report['placebo'] = dict(scores=pr.scores(y, placebo), vs_model_only=delta(test, placebo, arms['B_model']['p']))
    report['reliability'] = dict(market=reliability(y, market), model_only=reliability(y, q), C_full=reliability(y, arms[PRIMARY]['p']))
    report['coefficients'] = dict(zip(['a', 'b'] + list(COLS), models[PRIMARY]['w'].tolist()))
    report['decision'] = decide(report)
    return report


def decide(report):
    full = report['arms'][PRIMARY]
    beats = full['vs_market']['interval'][1] < 0
    wf = report['walk_forward']['scores']['brier'] < report['market']['brier']
    slope = .9 <= full['scores']['slope'] <= 1.1
    placebo_clean = report['placebo']['vs_model_only']['interval'][1] >= 0
    better = bool(beats and wf and slope)
    if not better:
        verdict = 'no_evidence'
    else:
        over_recal = full['vs_recalibration']['interval'][1] < 0
        verdict = 'adds_information' if over_recal and placebo_clean else ('calibration_only' if not over_recal else 'void_placebo')
    return dict(verdict=verdict, better_calibrated_than_market=better, beats_market_upper_below_zero=bool(beats),
                walk_forward_beats=bool(wf), slope_in_range=bool(slope), placebo_clean=bool(placebo_clean))


def predictions(players, games, v12_protocol, old, new, api_dir, published):
    seasons = sorted({g['season'] for g in games})
    index = {(r['game_id'], str(r['player_id'])): r for r in players}
    game_season = {g['game_id']: g['season'] for g in games}
    tips = injury_t60.tip_index(api_dir, games, old)
    arm = v15.Arm(old + new, players, games, tips, index)
    by_season = defaultdict(list)
    for r in v12.team_games(games, v12_protocol):
        by_season[r['season']].append(r)
    preds, repro = [], {}
    for season in SEASONS:
        _, _, train_seasons, table = v15.season_setup(season, seasons, v12_protocol, game_season, arm)
        train = [dict(r) for s in train_seasons for r in by_season[s]]
        test = [dict(r) for r in by_season[season]]
        v13.attach(train, arm.entries, table); v13.attach(test, arm.entries, table)
        out = score_model(train, test)
        preds += out
        brier = float(np.mean([(p['p_win'] - p['home_win']) ** 2 for p in out]))
        if season in published['markets']['winner']:
            want = published['markets']['winner'][season]['candidate']['brier']
            if abs(brier - want) > 1e-9:
                raise ValueError(f'v1.5 winner Brier not reproduced for {season}: {brier} vs {want}')
            repro[season] = brier
    return preds, repro


def period_points_from(bets_rows):
    out = {'h1': {}, 'q1': {}}
    for r in bets_rows:
        if r['market'] in ('total_h1', 'total_q1') and r['home_points'] is not None:
            out[r['period']][r['game_id']] = (r['season'], (r['home_points'], r['away_points']))
    return out


def run(args):
    load = lambda p: json.loads(Path(p).read_bytes())
    protocol, v12_protocol = load(args.protocol), load(args.v12_protocol)
    players = m1.read_rows(Path(args.data) / 'players.jsonl.gz')
    games = load(Path(args.data) / 'games.json')
    old, new = av.read_reports(args.old_reports), av.read_reports(args.t60_reports)
    preds, repro = predictions(players, games, v12_protocol, old, new, args.api_dir, load(args.published_v15))
    bets = [json.loads(line) for line in gzip.open(args.bets, 'rt', encoding='utf8')]
    units, drops, fits = build_units(preds, bets, period_points_from(bets))
    report = dict(version=protocol['version'], retrospective_not_confirmatory=True, promoted=False,
                  reproduction_of_published_v15_winner=repro, drops=drops, period_fits=fits,
                  games_with_predictions={s: sum(1 for p in preds if p['season'] == s) for s in SEASONS}, markets={})
    grid = protocol['anchor_model']['lambda_grid']
    for market in MARKETS:
        rows = [u for u in units if u['market'] == market]
        report['markets'][market] = evaluate_market(rows, grid)
    out = Path(args.output)
    write_json(out / 'team_markets_report.json', report)
    write_json(out / 'team_markets_coefficients.json', dict(promoted=False, markets={
        m: dict(lambda_=e['arms'][PRIMARY]['lambda_'], weights=e['coefficients']) for m, e in report['markets'].items()}))
    write_json(out / 'score_model_predictions.json', preds)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--data', '--bets', '--protocol', '--v12-protocol', '--old-reports', '--t60-reports', '--api-dir',
                 '--published-v15', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    if json.loads((Path(a.output) / 'protocol_frozen.json').read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    report = run(a)
    write_json(Path(a.output) / 'inputs.json', dict(
        source_sha256=digest(__file__), protocol_sha256=digest(a.protocol), bets_sha256=digest(a.bets),
        players_sha256=digest(Path(a.data) / 'players.jsonl.gz'), old_reports_sha256=digest(a.old_reports),
        t60_reports_sha256=digest(a.t60_reports)))
    print(json.dumps({m: e['decision']['verdict'] for m, e in report['markets'].items()}, allow_nan=False))


if __name__ == '__main__':
    main()
