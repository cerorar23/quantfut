"""Calibrate the engine's own distributions against realised results across lines, for markets with and without a price.

Research only. Protocol: nba_engine_calibration_protocol.json, frozen before running. Team scores by period come from the
nba-team-markets score model; player counts and combinations from the v1 player law; double-double from a smoothed rate."""
from array import array
from collections import defaultdict, deque
from datetime import date as Date
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.special import expit, logit
from scipy.stats import nbinom, norm

from . import availability as av
from . import injury_t60
from . import multimarket as m1
from . import multimarket_v15 as v15
from . import props_residual as pr
from . import team_markets as tm
from .audit import digest, write_json

Z_GRID = (-1., -.5, 0., .5, 1.)
SEED = 20261027
BOOTSTRAP = 400
LEVEL_TEAM, LEVEL_PLAYER = 1 - .05 / 12, 1 - .05 / 9
FIT_SEASON, TEST_SEASON = '2024-25', '2025-26'
RECAL_LAMBDA = 1e-4
LAMBDA_GRID = (1e-4, 1e-3, 1e-2, 1e-1)
TEAM_MARKETS = ('total_game', 'margin_game', 'home_points', 'away_points', 'total_h1', 'margin_h1', 'total_q1', 'margin_q1',
                'total_h2', 'margin_h2', 'total_q2', 'margin_q2')
PERIODS = ('h1', 'q1', 'h2', 'q2')
PLAYER_STATS = {  # name -> (component fields, prior rate per minute)
    'steals': (('steals',), .035), 'blocks': (('blocks',), .025), 'turnovers': (('turnovers',), .07),
    'steals_blocks': (('steals', 'blocks'), .06), 'points_rebounds': (('points', 'rebounds'), .85),
    'points_assists': (('points', 'assists'), .80), 'rebounds_assists': (('rebounds', 'assists'), .35),
    'points_rebounds_assists': (('points', 'rebounds', 'assists'), 1.0)}
FEATURES = pr.AVAILABILITY + pr.ENVIRONMENT
DD_PRIOR_GAMES = 10
SEASON_FLAG = {FIT_SEASON: 0, TEST_SEASON: 1}


# ---------- array machinery -------------------------------------------------------------------------------------------

def logit_arr(p):
    return logit(np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6))


def design(lk, x, mean=None, sd=None):
    if x is None:
        return np.column_stack([np.ones(len(lk)), lk]), None, None
    if mean is None:
        mean, sd = x.mean(axis=0), x.std(axis=0)
        sd = np.where(sd < 1e-12, 1., sd)
    return np.column_stack([np.ones(len(lk)), lk, (x - mean) / sd]), mean, sd


def fit_arrays(lk, x, y, lam):
    d, mean, sd = design(lk, x)
    prior = np.zeros(d.shape[1]); prior[1] = 1.
    return dict(w=pr.fit_ridge(d, np.asarray(y, float), prior, lam), mean=mean, sd=sd, has_x=x is not None)


def predict_arrays(model, lk, x):
    d, _, _ = design(lk, x if model['has_x'] else None, model['mean'], model['sd'])
    return expit(d @ model['w'])


def choose_lambda_arrays(lk, x, y, date_ids, grid, folds=5):
    uniq = np.unique(date_ids)
    block = np.minimum(folds - 1, np.searchsorted(uniq, date_ids) * folds // len(uniq))
    best = None
    for lam in grid:
        losses = []
        for k in range(folds):
            tr, te = block != k, block == k
            if not te.any() or not tr.any():
                continue
            m = fit_arrays(lk[tr], None if x is None else x[tr], y[tr], lam)
            losses.append(pr.logloss(np.asarray(y[te], float), predict_arrays(m, lk[te], None if x is None else x[te])))
        score = float(np.mean(losses))
        if best is None or score < best[1]:
            best = (lam, score)
    return best[0]


def boot(date_ids, diff, level):
    k = int(date_ids.max()) + 1
    total, count = np.bincount(date_ids, weights=diff, minlength=k), np.bincount(date_ids, minlength=k).astype(float)
    pick = np.random.default_rng(SEED).integers(0, k, size=(BOOTSTRAP, k))
    means = total[pick].sum(axis=1) / count[pick].sum(axis=1)
    return np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2]).tolist()


def delta(y, a, b, date_ids, level):
    diff = (np.asarray(a) - y) ** 2 - (np.asarray(b) - y) ** 2
    return dict(paired_brier_difference=float(diff.mean()), interval=boot(date_ids, diff, level))


def reliability(y, p, bins=10):
    order = np.argsort(p)
    return [dict(n=int(len(i)), predicted=float(np.mean(p[i])), observed=float(np.mean(y[i])))
            for i in np.array_split(order, bins) if len(i)]


def evaluate(train, test, level, with_features):
    """train/test: dicts with p, p_base, y, date_ids (chronological integers) and, with features, x and x_perm."""
    y_te, y_tr = test['y'].astype(float), train['y'].astype(float)
    lk_tr, lk_te = logit_arr(train['p']), logit_arr(test['p'])
    a = fit_arrays(lk_tr, None, y_tr, RECAL_LAMBDA)
    p_a = predict_arrays(a, lk_te, None)
    report = dict(units=dict(train=int(len(y_tr)), test=int(len(y_te))),
                  raw=pr.scores(y_te, test['p']), baseline=pr.scores(y_te, test['p_base']), recalibrated=pr.scores(y_te, p_a),
                  coefficients=dict(a=float(a['w'][0]), b=float(a['w'][1])),
                  raw_vs_baseline=delta(y_te, test['p'], test['p_base'], test['date_ids'], level),
                  recal_vs_raw=delta(y_te, p_a, test['p'], test['date_ids'], level),
                  reliability=dict(raw=reliability(y_te, test['p']), recalibrated=reliability(y_te, p_a)))
    if with_features:
        lam = choose_lambda_arrays(lk_tr, train['x'], y_tr, train['date_ids'], LAMBDA_GRID)
        f = fit_arrays(lk_tr, train['x'], y_tr, lam)
        p_f = predict_arrays(f, lk_te, test['x'])
        placebo = predict_arrays(fit_arrays(lk_tr, train['x_perm'], y_tr, lam), lk_te, test['x_perm'])
        report['features'] = dict(lambda_=lam, scores=pr.scores(y_te, p_f), vs_recalibration=delta(y_te, p_f, p_a, test['date_ids'], level),
                                  placebo_vs_recalibration=delta(y_te, placebo, p_a, test['date_ids'], level),
                                  weights=dict(zip(['a', 'b'] + list(FEATURES), f['w'].tolist())))
    report['decision'] = decide(report)
    return report


def decide(report):
    raw = report['raw']
    out = dict(skilled=bool(report['raw_vs_baseline']['interval'][1] < 0),
               calibrated=bool(.9 <= raw['slope'] <= 1.1 and abs(raw['intercept']) <= .10),
               recalibration_helps=bool(report['recal_vs_raw']['interval'][1] < 0))
    if 'features' in report:
        f = report['features']
        out['features_help'] = bool(f['vs_recalibration']['interval'][1] < 0 and f['placebo_vs_recalibration']['interval'][1] >= 0
                                    and .9 <= f['scores']['slope'] <= 1.1)
    return out


# ---------- team markets ----------------------------------------------------------------------------------------------

def realised(bets_rows):
    """game id -> season, date, (home, away) points of the game, first half and first quarter, and the bet365 close lines."""
    games = defaultdict(dict)
    for r in bets_rows:
        g = games[r['game_id']]
        g['season'], g['date'] = r['season'], r['date']
        if r['home_points'] is not None:
            g[r['period']] = (r['home_points'], r['away_points'])
        if r['kind'] != 'moneyline':
            g[r['market']] = r['close']['line']
    return {k: v for k, v in games.items() if all(p in v for p in ('game', 'h1', 'q1'))}


def period_pair(rec, period):
    if period in ('h1', 'q1'):
        return rec[period]
    if period == 'h2':
        return rec['game'][0] - rec['h1'][0], rec['game'][1] - rec['h1'][1]
    return rec['h1'][0] - rec['q1'][0], rec['h1'][1] - rec['q1'][1]


def quantity(rec, market):
    if market in ('home_points', 'away_points'):
        return rec['game'][0 if market == 'home_points' else 1]
    kind, period = market.split('_')
    h, a = rec['game'] if period == 'game' else period_pair(rec, period)
    return h + a if kind == 'total' else h - a


def engine_law(pred, market, fits, season):
    """(mean, sd) of the engine for one quantity of one game, or None if a period relation is not available."""
    if market == 'total_game':
        return pred['mu_t'], pred['sigma_t']
    if market == 'margin_game':
        return pred['mu_m'], pred['sigma_m']
    if market in ('home_points', 'away_points'):
        sign = 1 if market == 'home_points' else -1
        return (pred['mu_t'] + sign * pred['mu_m']) / 2, float(np.sqrt((pred['sigma_t'] ** 2 + pred['sigma_m'] ** 2) / 4))
    kind, period = market.split('_')
    fit = fits[(season, period)]
    if fit is None:
        return None
    f = fit['total'] if kind == 'total' else fit['margin']
    return f['a'] + f['b'] * (pred['mu_t'] if kind == 'total' else pred['mu_m']), f['sd']


def team_units(preds, recs):
    by_game = {p['game_id']: p for p in preds}
    fits, law = {}, {}
    for season in (FIT_SEASON, TEST_SEASON):
        for period in PERIODS:
            earlier = [(by_game[g], *period_pair(rec, period)) for g, rec in recs.items() if rec['season'] < season and g in by_game]
            fits[(season, period)] = tm.fit_period(earlier) if len(earlier) >= 200 else None
        previous = sorted({r['season'] for r in recs.values() if r['season'] < season})[-2:]
        for market in TEAM_MARKETS:
            values = np.array([quantity(rec, market) for rec in recs.values() if rec['season'] in previous], float)
            law[(season, market)] = (float(values.mean()), float(values.std(ddof=1))) if len(values) >= 200 else None
    out = {m: [] for m in TEAM_MARKETS}
    drops = defaultdict(int)
    for g, rec in recs.items():
        pred = by_game.get(g)
        if pred is None or rec['season'] not in SEASON_FLAG:
            continue
        for market in TEAM_MARKETS:
            engine, clim = engine_law(pred, market, fits, rec['season']), law[(rec['season'], market)]
            if engine is None or clim is None:
                drops['no_period_fit_or_climatology'] += 1
                continue
            mean, sd = engine
            actual = quantity(rec, market)
            for line in sorted({float(np.floor(mean + z * sd) + .5) for z in Z_GRID}):
                out[market].append((rec['season'], rec['date'], g, float(norm.sf(line, mean, sd)), float(norm.sf(line, *clim)),
                                    int(actual > line), mean, actual, clim[0]))
    return out, dict(drops), {f'{s} {p}': f for (s, p), f in fits.items()}


def team_arrays(units, season):
    rows = [u for u in units if u[0] == season]
    index = {d: i for i, d in enumerate(sorted({r[1] for r in rows}))}
    return dict(p=np.array([r[3] for r in rows]), p_base=np.array([r[4] for r in rows]), y=np.array([r[5] for r in rows]),
                date_ids=np.array([index[r[1]] for r in rows])), rows


def centre_error(rows, recs, market):
    """Descriptive: the engine mean against the bet365 close centre (spread, total; game, first half, first quarter)."""
    kind, period = market.split('_')
    key = ('spread_' if kind == 'margin' else 'total_') + period
    seen, engine, centre, actual, dates = set(), [], [], [], []
    for season, date, g, _, _, _, mean, value, _ in rows:
        if g in seen or g not in recs or key not in recs[g]:
            continue
        seen.add(g)
        line = recs[g][key]
        engine.append(mean); centre.append(-line if kind == 'margin' else line); actual.append(value); dates.append(date)
    if len(engine) < 200:
        return None
    engine, centre, actual = np.array(engine), np.array(centre), np.array(actual, float)
    x = np.column_stack([np.ones(len(actual)), centre, engine - centre])
    beta, *_ = np.linalg.lstsq(x, actual, rcond=None)
    resid = actual - x @ beta
    meat = np.zeros((3, 3))
    for d in set(dates):
        idx = [i for i, dd in enumerate(dates) if dd == d]
        s = (x[idx] * resid[idx, None]).sum(axis=0)
        meat += np.outer(s, s)
    inv = np.linalg.inv(x.T @ x)
    se = np.sqrt(np.diag(inv @ meat @ inv))
    return dict(n=len(actual), rmse_engine=float(np.sqrt(np.mean((actual - engine) ** 2))),
                rmse_bet365_centre=float(np.sqrt(np.mean((actual - centre) ** 2))),
                beta2_engine_minus_centre=float(beta[2]), beta2_ci95=[float(beta[2] - 1.96 * se[2]), float(beta[2] + 1.96 * se[2])])


def run_team(preds, bets_rows):
    recs = realised(bets_rows)
    units, drops, fits = team_units(preds, recs)
    report = dict(drops=drops, period_fits=fits, games=len(recs), markets={})
    params = {}
    for market in TEAM_MARKETS:
        train, rows_tr = team_arrays(units[market], FIT_SEASON)
        test, rows_te = team_arrays(units[market], TEST_SEASON)
        if len(rows_tr) < 500 or len(rows_te) < 500:
            report['markets'][market] = dict(skipped='too few units', train=len(rows_tr), test=len(rows_te))
            continue
        e = evaluate(train, test, LEVEL_TEAM, False)
        games = {}
        for r in rows_te:
            games.setdefault(r[2], r)
        actual = np.array([r[7] for r in games.values()], float)
        e['rmse_engine_mean'] = float(np.sqrt(np.mean((actual - np.array([r[6] for r in games.values()])) ** 2)))
        e['rmse_climatology_mean'] = float(np.sqrt(np.mean((actual - np.array([r[8] for r in games.values()])) ** 2)))
        e['vs_bet365_centre'] = centre_error(rows_te, recs, market) if market.split('_')[0] in ('total', 'margin') \
            and market.split('_')[1] in ('game', 'h1', 'q1') else None
        report['markets'][market] = e
        params[market] = e['coefficients']
    return report, params


# ---------- player markets --------------------------------------------------------------------------------------------

def add_counts(players, extended):
    """Derived per-game counts. Turnovers come from the extended box; a game missing there has None."""
    tov = {(str(r['game_id']), r['player_id'], r['team_id']): r['tov'] for r in extended}
    for r in players:
        r['turnovers'] = tov.get((str(r['game_id']), r['player_id'], r['team_id']))
        for name, (parts, _) in PLAYER_STATS.items():
            if len(parts) > 1:
                r[name] = sum(r[p] for p in parts)
        r['dd'] = int(sum(r[s] >= 10 for s in ('points', 'rebounds', 'assists')) >= 2)


def over_probs(params, lines, weight):
    """The v1 law at several lines at once: (1 - w) NegBin survival + w empirical share (nba.multimarket.player_over)."""
    sample = np.asarray(params['sample'])
    empirical = (sample[:, None] > lines[None, :]).mean(axis=0)
    return (1 - weight) * nbinom.sf(np.floor(lines), params['n'], params['p']) + weight * empirical


class Store:
    """Compact column store: one entry per (player-game, line)."""

    def __init__(self):
        self.flag, self.day, self.pg = array('b'), array('i'), array('i')
        self.p, self.base, self.y = array('d'), array('d'), array('b')

    def add(self, flag, day, pg, p, base, y):
        self.flag.append(flag); self.day.append(day); self.pg.append(pg); self.p.append(p); self.base.append(base); self.y.append(y)


def player_units(players, protocol_rates):
    """Replay by date; per player-game the engine probability, the empirical baseline and the outcome at each grid line."""
    local = dict(history_window=20, min_history=10, history_max_days=370, prior_minutes=90, empirical_weight=.25,
                 player_prior_rates=dict(protocol_rates))
    for name, (_, rate) in PLAYER_STATS.items():
        local['player_prior_rates'][name] = rate
    days = defaultdict(list)
    for r in players:
        days[r['date']].append(r)
    history = defaultdict(lambda: deque(maxlen=20))
    season_dd = defaultdict(lambda: [0, 0])
    stores = {name: Store() for name in list(PLAYER_STATS) + ['double_double']}
    seen = []
    for day in sorted(days):
        ordinal = Date.fromisoformat(day).toordinal()
        for r in days[day]:
            if not r['participated'] or not r['minutes'] or r['minutes'] <= 0 or r['season'] not in SEASON_FLAG:
                continue
            hist = m1.eligible(history[r['player_id']], day, local)
            if len(hist) < local['min_history']:
                continue
            seen.append((str(r['game_id']), r['player_id'], day, r['season']))
            pg, flag = len(seen) - 1, SEASON_FLAG[r['season']]
            for name in PLAYER_STATS:
                if name == 'turnovers' and (r['turnovers'] is None or any(h['turnovers'] is None for h in hist)):
                    continue
                params = m1.player_parameters(hist, name, local)
                sd = float(np.sqrt(params['mean'] + params['mean'] ** 2 / params['n']))
                lines = np.array(sorted({float(np.floor(params['mean'] + z * sd) + .5) for z in Z_GRID}))
                p = over_probs(params, lines, local['empirical_weight'])
                sample = np.asarray(params['sample'])
                base = ((sample[:, None] > lines[None, :]).sum(axis=0) + 1) / (len(sample) + 2)
                for line, pe, pb in zip(lines, p, base):
                    stores[name].add(flag, ordinal, pg, float(pe), float(pb), int(r[name] > line))
            earlier = [v for s, v in season_dd.items() if s < r['season']]
            rate0 = sum(v[0] for v in earlier) / max(sum(v[1] for v in earlier), 1)
            k = sum(h['dd'] for h in hist)
            stores['double_double'].add(flag, ordinal, pg, (k + DD_PRIOR_GAMES * rate0) / (len(hist) + DD_PRIOR_GAMES), rate0, r['dd'])
        for r in days[day]:
            if r['participated'] and r['minutes'] and r['minutes'] > 0:
                history[r['player_id']].append(r)
                season_dd[r['season']][0] += r['dd']; season_dd[r['season']][1] += 1
    return stores, seen


def feature_matrix(seen, index, teams, bets, minutes, arm, tables):
    """One feature row per player-game (the features do not depend on the line); NaN rows mark player-games without inputs."""
    dummy = [dict(game_id=g, player_id=pid, market='pg', line=0., books=1, market_p=.5, model_p=.5, y=0, minutes_to_tipoff=45.,
                  date=d, season=s, pg=i) for i, (g, pid, d, s) in enumerate(seen)]
    rows, drops = pr.add_features(dummy, index, teams, bets, minutes, arm, tables)
    matrix = np.full((len(seen), len(FEATURES)), np.nan)
    for r in rows:
        matrix[r['pg']] = [r[c] for c in FEATURES]
    return matrix, drops


def player_arrays(store, matrix, flag, seed):
    pg = np.frombuffer(store.pg, dtype=np.int32)
    keep = (np.frombuffer(store.flag, dtype=np.int8) == flag) & ~np.isnan(matrix[pg, 0])
    pg, day = pg[keep], np.frombuffer(store.day, dtype=np.int32)[keep]
    _, date_ids = np.unique(day, return_inverse=True)
    # placebo: one permutation of the feature rows among the player-games of the same date, shared by all their lines
    rng = np.random.default_rng(seed)
    swap = {}
    members = defaultdict(list)
    for g, d in zip(pg.tolist(), day.tolist()):
        if g not in swap:
            swap[g] = None
            members[d].append(g)
    for d, group in members.items():
        for g, h in zip(group, [group[i] for i in rng.permutation(len(group))]):
            swap[g] = h
    permuted = np.array([swap[g] for g in pg.tolist()])
    return dict(p=np.frombuffer(store.p, dtype=np.float64)[keep], p_base=np.frombuffer(store.base, dtype=np.float64)[keep],
                y=np.frombuffer(store.y, dtype=np.int8)[keep], date_ids=date_ids, x=matrix[pg], x_perm=matrix[permuted])


def run_player(players, extended, args, v12_protocol, games, ext_games):
    add_counts(players, extended)
    stores, seen = player_units(players, v12_protocol['player_prior_rates'])
    index = {(str(r['game_id']), str(r['player_id'])): r for r in players}
    old, new = av.read_reports(args.old_reports), av.read_reports(args.t60_reports)
    tips = injury_t60.tip_index(args.api_dir, games, old)
    arm = v15.Arm(old + new, players, games, tips, index)
    game_season = {g['game_id']: g['season'] for g in games}
    tables = {s: av.play_table(arm.statuses, index, {g for g in arm.observed if g in game_season and game_season[g] < s})
              for s in {s for _, _, _, s in seen}}
    bets = pr.bets_context([json.loads(line) for line in gzip.open(args.bets, 'rt', encoding='utf8')])
    need = {(g, str(pid)) for g, pid, _, _ in seen}
    matrix, feature_drops = feature_matrix(seen, index, pr.team_context(ext_games), bets, pr.minutes_context(players, need), arm, tables)
    report = dict(player_games=len(seen), with_features=int((~np.isnan(matrix[:, 0])).sum()), feature_drops=feature_drops, markets={})
    params = {}
    for market, store in stores.items():
        train = player_arrays(store, matrix, 0, SEED)
        test = player_arrays(store, matrix, 1, SEED + 1)
        if len(train['y']) < 500 or len(test['y']) < 500:
            report['markets'][market] = dict(skipped='too few units', train=int(len(train['y'])), test=int(len(test['y'])))
            continue
        e = evaluate(train, test, LEVEL_PLAYER, True)
        report['markets'][market] = e
        params[market] = dict(recalibration=e['coefficients'], features=e['features']['weights'])
    return report, params


def run(args):
    load = lambda p: json.loads(Path(p).read_bytes())
    protocol, v12_protocol = load(args.protocol), load(args.v12_protocol)
    bets = [json.loads(line) for line in gzip.open(args.bets, 'rt', encoding='utf8')]
    team_report, team_params = run_team(load(args.score_predictions), bets)
    players = m1.read_rows(Path(args.data) / 'players.jsonl.gz')
    games = load(Path(args.data) / 'games.json')
    extended = m1.read_rows(Path(args.extended_players))
    player_report, player_params = run_player(players, extended, args, v12_protocol, games, load(args.extended_games))
    report = dict(version=protocol['version'], retrospective_not_confirmatory=True, promoted=False, team=team_report, player=player_report)
    out = Path(args.output)
    write_json(out / 'engine_calibration_report.json', report)
    write_json(out / 'engine_calibration_params.json', dict(promoted=False, team=team_params, player=player_params))
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--data', '--extended-players', '--extended-games', '--bets', '--score-predictions', '--protocol', '--v12-protocol',
                 '--old-reports', '--t60-reports', '--api-dir', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    if json.loads((Path(a.output) / 'protocol_frozen.json').read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    report = run(a)
    write_json(Path(a.output) / 'inputs.json', dict(
        source_sha256=digest(__file__), protocol_sha256=digest(a.protocol), bets_sha256=digest(a.bets),
        score_predictions_sha256=digest(a.score_predictions), players_sha256=digest(Path(a.data) / 'players.jsonl.gz'),
        extended_players_sha256=digest(a.extended_players)))
    print(json.dumps({'team': {m: e.get('decision') for m, e in report['team']['markets'].items()},
                      'player': {m: e.get('decision') for m, e in report['player']['markets'].items()}}, allow_nan=False))


if __name__ == '__main__':
    main()
