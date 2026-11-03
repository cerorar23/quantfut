"""Market-anchored residual model for player props against the US books' no-vig consensus.

Research only. Protocol: nba_props_residual_protocol.json, frozen before running. Needs props_link output, the extended
box games, the BetsAPI odds normalisation and the v1.3/v1.5 injury inputs. It promotes nothing."""
from collections import defaultdict, deque
from datetime import date as Date, timedelta
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from . import availability as av
from . import injury_t60
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from . import multimarket_v15 as v15
from . import props_market as pm
from .audit import digest, write_json
from .props_link import read_players

AVAILABILITY = ('own_questionable_or_doubtful', 'own_probable', 'teammates_missing_minutes')
ENVIRONMENT = ('total_c', 'own_spread', 'abs_spread', 'home', 'back_to_back', 'pace_c', 'opp_def_c', 'min10')
ARMS = {'A_recalibration': (), 'B_model': ('model_delta',), 'C_availability': ('model_delta',) + AVAILABILITY,
        'D_environment': ('model_delta',) + ENVIRONMENT, 'E_full': ('model_delta',) + AVAILABILITY + ENVIRONMENT}
PRIMARY = 'E_full'
LOOKBACK = 10
BOOTSTRAP, SEED, LEVEL = 400, 20261025, .9875  # protocol: 400 date-resampled replicates, 98.75% (Bonferroni over 4 markets)
MIN_TEAM_GAMES = 5
STARTER_MINUTES = 28 / 48


def clip_logit(p):
    return logit(np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6))


def team_context(games):
    """game id -> both teams' pace / defence over their last 10 games and the league means, using earlier dates only."""
    by_day = defaultdict(list)
    for g in games:
        by_day[g['date']].append(g)
    history, last, out = defaultdict(lambda: deque(maxlen=LOOKBACK)), {}, {}
    n = poss = ppp = 0.
    for day in sorted(by_day):
        pace_l, ppp_l = (poss / n, ppp / n) if n else (None, None)
        for g in by_day[day]:
            sides = {}
            for side in ('home', 'away'):
                team, hist = g[side]['team_id'], history[g[side]['team_id']]
                ready = len(hist) >= MIN_TEAM_GAMES
                sides[side] = dict(team_id=team, last=last.get(team),
                                   pace=float(np.mean([h[0] for h in hist])) if ready else pace_l,
                                   allowed=float(np.mean([h[1] for h in hist])) if ready else ppp_l)
            out[g['game_id']] = dict(date=day, pace_l=pace_l, ppp_l=ppp_l, **sides)
        for g in by_day[day]:
            for side, other in (('home', 'away'), ('away', 'home')):
                t, o = g[side], g[other]
                allowed = o['points'] / o['possessions_estimate']
                history[t['team_id']].append((t['possessions_estimate'], allowed))
                last[t['team_id']] = day
                n += 1; poss += t['possessions_estimate']; ppp += allowed
    return out


def bets_context(rows):
    """BetsAPI spread/total paths per game, and the mean closing total over strictly earlier dates."""
    paths, closes = {}, defaultdict(list)
    for r in rows:
        if r['market'] in ('spread_game', 'total_game'):
            paths[(r['game_id'], r['market'])] = r['path']
            if r['market'] == 'total_game':
                closes[r['date']].append(r['close']['line'])
    mean_before, total, count = {}, 0., 0
    for day in sorted(closes):
        mean_before[day] = total / count if count else None
        total += sum(closes[day]); count += len(closes[day])
    return paths, mean_before


def as_of(path, seconds):
    """Latest [seconds_before_tip, line, p1, p2] entry at or before the quote time (path runs from far to near)."""
    found = None
    for entry in path:
        if entry[0] >= seconds:
            found = entry
        else:
            break
    return found


def minutes_context(players, need):
    """(game, player) -> mean minutes / 48 of the last 10 participations on earlier dates (needs at least 5)."""
    days = defaultdict(list)
    for r in players:
        days[r['date']].append(r)
    history, out = defaultdict(lambda: deque(maxlen=LOOKBACK)), {}
    for day in sorted(days):
        for r in days[day]:
            key = str(r['game_id']), str(r['player_id'])
            if key in need and len(history[r['player_id']]) >= MIN_TEAM_GAMES:
                out[key] = float(np.mean(history[r['player_id']])) / 48
        for r in days[day]:
            if r['participated'] and r['minutes'] and r['minutes'] > 0:
                history[r['player_id']].append(r['minutes'])
    return out


def add_features(priced, index, teams, bets, minutes, arm, tables):
    """Attach every protocol feature to the priced units; units without a required input are dropped and counted."""
    paths, total_mean = bets
    out, drops = [], defaultdict(int)
    for u in priced:
        box = index.get((u['game_id'], str(u['player_id'])))
        ctx = teams.get(u['game_id'])
        if box is None or ctx is None:
            drops['no_team_context'] += 1
            continue
        spread = as_of(paths.get((u['game_id'], 'spread_game'), []), u['minutes_to_tipoff'] * 60)
        total = as_of(paths.get((u['game_id'], 'total_game'), []), u['minutes_to_tipoff'] * 60)
        key = u['game_id'], str(u['player_id'])
        if spread is None or total is None or total_mean.get(ctx['date']) is None:
            drops['no_betsapi_as_of'] += 1
            continue
        if key not in minutes or ctx['pace_l'] is None:
            drops['no_minutes_or_league_context'] += 1
            continue
        home = box['team_id'] == ctx['home']['team_id']
        own, opp = (ctx['home'], ctx['away']) if home else (ctx['away'], ctx['home'])
        if None in (own['pace'], opp['pace'], opp['allowed']):
            drops['no_team_history'] += 1
            continue
        line = spread[1] if home else -spread[1]
        u = dict(u)
        u.update(total_c=(total[1] - total_mean[ctx['date']]) / 10, own_spread=line / 10, abs_spread=abs(line) / 10,
                 home=float(home), min10=minutes[key],
                 back_to_back=float(own['last'] is not None and (Date.fromisoformat(ctx['date']) - Date.fromisoformat(own['last'])) == timedelta(days=1)),
                 pace_c=((own['pace'] + opp['pace']) / 2 - ctx['pace_l']) / 10, opp_def_c=(opp['allowed'] - ctx['ppp_l']) * 10)
        out.append(u)
    for season in sorted({u['season'] for u in out}):
        rows = [u for u in out if u['season'] == season]
        f = v13.player_features([dict(game_id=u['game_id'], unit=u['player_id']) for u in rows], index, arm.entries, tables[season])
        for u, (q, p, m) in zip(rows, f):
            u.update(own_questionable_or_doubtful=float(q), own_probable=float(p), teammates_missing_minutes=float(m))
    for u in out:
        u['model_delta'] = float(clip_logit(u['model_p']) - clip_logit(u['market_p']))
        u['starter'] = u['min10'] >= STARTER_MINUTES
    main = {}
    for u in out:
        k = u['game_id'], u['player_id'], u['market']
        if k not in main or (u['books'], -u['line']) > (main[k]['books'], -main[k]['line']):
            main[k] = u
    for u in out:
        u['main_line'] = main[(u['game_id'], u['player_id'], u['market'])] is u
    return out, dict(drops)


def design(rows, cols, mean=None, sd=None):
    """[1, lk, standardised features]; mean and sd come from the training rows."""
    lk = clip_logit([r['market_p'] for r in rows])
    if not cols:
        return np.column_stack([np.ones(len(rows)), lk]), None, None
    x = np.array([[r[c] for c in cols] for r in rows], float)
    if mean is None:
        mean, sd = x.mean(axis=0), x.std(axis=0)
        sd[sd < 1e-12] = 1.
    return np.column_stack([np.ones(len(rows)), lk, (x - mean) / sd]), mean, sd


def fit_ridge(x, y, prior, lam):
    """Mean log loss + lam * ||w - prior||^2, analytic gradient."""
    n = len(y)

    def objective(w):
        z = x @ w
        return (float(np.mean(np.logaddexp(0, z) - y * z) + lam * np.sum((w - prior) ** 2)),
                x.T @ (expit(z) - y) / n + 2 * lam * (w - prior))
    result = minimize(objective, prior, jac=True, method='L-BFGS-B')
    if not result.success:
        raise ValueError('logistic fit failed')
    return result.x


def fit(rows, cols, lam):
    x, mean, sd = design(rows, cols)
    prior = np.zeros(x.shape[1]); prior[1] = 1.
    return dict(w=fit_ridge(x, np.array([r['y'] for r in rows], float), prior, lam), mean=mean, sd=sd, cols=cols)


def predict(model, rows):
    x, _, _ = design(rows, model['cols'], model['mean'], model['sd'])
    return expit(x @ model['w'])


def logloss(y, p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(np.mean(-y * np.log(p) - (1 - y) * np.log1p(-p)))


def choose_lambda(rows, cols, grid, folds=5):
    """Contiguous date blocks inside the training season; held-out log loss."""
    days = sorted({r['date'] for r in rows})
    block = {d: min(folds - 1, i * folds // len(days)) for i, d in enumerate(days)}
    y = np.array([r['y'] for r in rows], float)
    fold = np.array([block[r['date']] for r in rows])
    best = None
    for lam in grid:
        losses = []
        for k in range(folds):
            tr = [r for r, f in zip(rows, fold) if f != k]
            te = [r for r, f in zip(rows, fold) if f == k]
            if not te or not tr:
                continue
            losses.append(logloss(y[fold == k], predict(fit(tr, cols, lam), te)))
        score = float(np.mean(losses))
        if best is None or score < best[1]:
            best = (lam, score)
    return best[0]


def date_bootstrap(dates, difference, replicates, seed, level):
    keys = sorted(set(dates))
    where = {k: i for i, k in enumerate(keys)}
    total, count = np.zeros(len(keys)), np.zeros(len(keys))
    for d, v in zip(dates, difference):
        total[where[d]] += v; count[where[d]] += 1
    pick = np.random.default_rng(seed).integers(0, len(keys), size=(replicates, len(keys)))
    means = total[pick].sum(axis=1) / count[pick].sum(axis=1)
    return np.quantile(means, [(1 - level) / 2, 1 - (1 - level) / 2]).tolist()


def calibration(y, p):
    """Slope and intercept of y on logit p."""
    z, y = clip_logit(p), np.asarray(y, float)
    f = lambda w: float(np.mean(np.logaddexp(0, w[0] + w[1] * z) - y * (w[0] + w[1] * z)))
    r = minimize(f, [0., 1.], method='L-BFGS-B')
    return dict(intercept=float(r.x[0]), slope=float(r.x[1]))


def scores(y, p):
    s, _ = v12.metrics(y, p)
    return dict(brier=s['brier'], logloss=s['logloss'], bias=s['bias'], **calibration(y, p))


def delta(rows, p, reference):
    y = np.array([r['y'] for r in rows], float)
    diff = (np.asarray(p) - y) ** 2 - (np.asarray(reference) - y) ** 2
    return dict(paired_brier_difference=float(diff.mean()),
                interval=date_bootstrap([r['date'] for r in rows], diff, BOOTSTRAP, SEED, LEVEL))


def permute_within_date(rows, cols, seed):
    """Misassign the feature vectors among units of the same date and market (same permutation for all columns)."""
    rng = np.random.default_rng(seed)
    groups = defaultdict(list)
    for i, r in enumerate(rows):
        groups[(r['date'], r['market'])].append(i)
    out = [dict(r) for r in rows]
    for idx in groups.values():
        order = rng.permutation(len(idx))
        for c in cols:
            values = [rows[idx[j]][c] for j in order]
            for i, v in zip(idx, values):
                out[i][c] = v
    return out


def months(rows):
    return sorted({r['date'][:7] for r in rows})


def walk_forward(train, test, cols, lam):
    p = np.zeros(len(test))
    for month in months(test):
        where = [i for i, r in enumerate(test) if r['date'][:7] == month]
        past = train + [r for r in test if r['date'][:7] < month]
        p[where] = predict(fit(past, cols, lam), [test[i] for i in where])
    return p


def evaluate_market(rows, protocol):
    train = [r for r in rows if r['season'] == protocol['seasons']['train']]
    test = [r for r in rows if r['season'] == protocol['seasons']['test']]
    y = np.array([r['y'] for r in test], float)
    market = np.array([r['market_p'] for r in test])
    grid = protocol['model']['lambda_grid']
    arms, models = {}, {}
    for name, cols in ARMS.items():
        lam = choose_lambda(train, cols, grid)
        models[name] = fit(train, cols, lam)
        arms[name] = dict(lam=lam, p=predict(models[name], test))
    wf = walk_forward(train, test, ARMS[PRIMARY], arms[PRIMARY]['lam'])
    shuffled = ARMS[PRIMARY][1:]
    ptrain, ptest = permute_within_date(train, shuffled, SEED), permute_within_date(test, shuffled, SEED + 1)
    placebo = predict(fit(ptrain, ARMS[PRIMARY], arms[PRIMARY]['lam']), ptest)
    report = dict(units=dict(train=len(train), test=len(test)), market=scores(y, market), arms={}, strata={})
    for name, a in arms.items():
        report['arms'][name] = dict(lambda_=a['lam'], scores=scores(y, a['p']), vs_market=delta(test, a['p'], market))
    report['arms'][PRIMARY]['vs_recalibration'] = delta(test, arms[PRIMARY]['p'], arms['A_recalibration']['p'])
    report['walk_forward'] = dict(scores=scores(y, wf), vs_market=delta(test, wf, market))
    report['placebo'] = dict(scores=scores(y, placebo), vs_market=delta(test, placebo, market))
    p_full = arms[PRIMARY]['p']
    for label, mask in (('starters', [r['starter'] for r in test]), ('bench', [not r['starter'] for r in test]),
                        ('main_line', [r['main_line'] for r in test])):
        sub = [r for r, m in zip(test, mask) if m]
        if len(sub) >= 200:
            keep = np.array(mask)
            report['strata'][label] = dict(n=len(sub), **delta(sub, p_full[keep], market[keep]))
    report['coefficients'] = dict(zip(['a', 'b'] + list(ARMS[PRIMARY]), models[PRIMARY]['w'].tolist()))
    report['decision'] = decide(report)
    return report


def decide(report):
    full = report['arms'][PRIMARY]
    beats = full['vs_market']['interval'][1] < 0
    wf = report['walk_forward']['scores']['brier'] < report['market']['brier']
    slope = .9 <= full['scores']['slope'] <= 1.1
    if beats and wf and slope:
        verdict = 'adds_information'
        if full['vs_recalibration']['interval'][0] <= 0 <= full['vs_recalibration']['interval'][1]:
            verdict = 'calibration_only'
    else:
        verdict = 'no_evidence'
    return dict(verdict=verdict, beats_market_upper_below_zero=bool(beats), walk_forward_beats=bool(wf), slope_in_range=bool(slope),
                placebo_clean=bool(report['placebo']['vs_market']['interval'][1] >= 0))


def reproduction(priced, published, seasons):
    """The unfiltered v1-vs-market difference must reproduce the published comparison exactly."""
    out = {}
    for market, entry in published['markets'].items():
        for season, comparison in entry['seasons'].items():
            rows = [r for r in priced if r['market'] == market and r['season'] == season]
            y = np.array([r['y'] for r in rows], float)
            diff = (np.array([r['model_p'] for r in rows]) - y) ** 2 - (np.array([r['market_p'] for r in rows]) - y) ** 2
            if abs(float(diff.mean()) - comparison['paired_brier_difference']) > 1e-9:
                raise ValueError(f'v1 comparison not reproduced: {market} {season}')
            out[f'{market} {season}'] = float(diff.mean())
    return out


def run(args):
    load = lambda p: json.loads(Path(p).read_bytes())
    protocol, v12_protocol, v1_protocol = load(args.protocol), load(args.v12_protocol), load(args.v1_protocol)
    v1_protocol['player_prior_rates'] = v12_protocol['player_prior_rates']
    players = m1.read_rows(Path(args.data) / 'players.jsonl.gz')
    games = load(Path(args.data) / 'games.json')
    ext = load(args.extended_games)
    index = {(str(r['game_id']), str(r['player_id'])): r for r in players}
    units, unit_drops = pm.units(read_players(args.linked))
    ext_ids, game_ids = {g['game_id'] for g in ext}, {g['game_id'] for g in games}
    priced, skipped = pm.attach_model(units, players, v1_protocol)
    repro = reproduction(priced, load(args.published), protocol['seasons'])
    drops = dict(unit_construction=unit_drops, v1_insufficient_history=skipped, priced_units=len(priced))
    before = len(priced)
    priced = [u for u in priced if u['game_id'] in ext_ids and u['game_id'] in game_ids]
    drops['game_not_in_extended_or_v13'] = before - len(priced)
    before = len(priced)
    priced = [u for u in priced if 0 < u['minutes_to_tipoff'] <= 60 and u['market'] in protocol['markets']]
    drops['snapshot_more_than_60_min_before_tip'] = before - len(priced)
    game_season = {g['game_id']: g['season'] for g in games}
    old, new = av.read_reports(args.old_reports), av.read_reports(args.t60_reports)
    tips = injury_t60.tip_index(args.api_dir, games, old)
    arm = v15.Arm(old + new, players, games, tips, index)
    tables = {s: av.play_table(arm.statuses, index, {g for g in arm.observed if g in game_season and game_season[g] < s})
              for s in {u['season'] for u in priced}}
    bets = bets_context([json.loads(line) for line in gzip.open(args.bets, 'rt', encoding='utf8')])
    need = {(u['game_id'], str(u['player_id'])) for u in priced}
    rows, feature_drops = add_features(priced, index, team_context(ext), bets, minutes_context(players, need), arm, tables)
    drops['feature_inputs'] = feature_drops
    report = dict(version=protocol['version'], retrospective_not_confirmatory=True, promoted=False, drops=drops,
                  reproduction_of_published_v1=repro, markets={})
    for market in protocol['markets']:
        report['markets'][market] = evaluate_market([r for r in rows if r['market'] == market], protocol)
    out = Path(args.output)
    write_json(out / 'props_residual_report.json', report)
    write_json(out / 'props_residual_coefficients.json', dict(promoted=False, markets={
        m: dict(lambda_=e['arms'][PRIMARY]['lambda_'], weights=e['coefficients']) for m, e in report['markets'].items()}))
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--data', '--extended-games', '--linked', '--bets', '--protocol', '--v12-protocol', '--v1-protocol',
                 '--old-reports', '--t60-reports', '--api-dir', '--published', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    if json.loads((Path(a.output) / 'protocol_frozen.json').read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    report = run(a)
    write_json(Path(a.output) / 'inputs.json', dict(
        source_sha256=digest(__file__), protocol_sha256=digest(a.protocol), linked_sha256=digest(a.linked), bets_sha256=digest(a.bets),
        extended_games_sha256=digest(a.extended_games), players_sha256=digest(Path(a.data) / 'players.jsonl.gz'),
        old_reports_sha256=digest(a.old_reports), t60_reports_sha256=digest(a.t60_reports)))
    print(json.dumps({m: e['decision'] for m, e in report['markets'].items()}, allow_nan=False))


if __name__ == '__main__':
    main()
