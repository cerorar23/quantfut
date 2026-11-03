"""v1.3 winner probabilities against Pinnacle no-vig prices (needs the cached snapshots from odds_history).

Research only: it answers whether the model adds information over the market, never produces a bet.
Protocol: nba_vs_market_protocol.json, frozen before any price was bought."""
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import expit, logit

from . import availability as av
from . import injury_t60
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from .audit import digest, write_json

ARMS = ('aligned', 'tminus60')
BUCKETS = ((0, 60), (60, 180), (180, float('inf')))
GAP_EDGES = (-1., -.10, -.05, .05, .10, 1.)
COVERAGE_MINIMUM = .85
STATS = dict(bootstrap=400, seed=20261101)  # fixed by the frozen protocol


def aligned_tips(tips, odds_rows):
    """Tipoff times in which a game's report cutoff (tipoff - LEAD) is min(tipoff - LEAD, snapshot).

    Raising the apparent tipoff is not needed: lowering it to snapshot + LEAD moves the cutoff to the snapshot."""
    out = dict(tips)
    for row in odds_rows:
        game = row['game_id']
        if game in out:
            out[game] = min(out[game], datetime.fromisoformat(row['snapshot_utc']) + av.LEAD)
    return out


def model_winner(players, games, v12_protocol, injury_path, api_dir, odds_rows=(), seasons=None):
    """Season -> arm -> rows of (game, date, model home-win probability, outcome), same fit as v1.3 evaluate.

    'tminus60' is the published rule; 'aligned' caps the information of games that have a price at the snapshot time.
    Training rows always use the published rule, so both arms share one fitted model."""
    all_seasons = sorted({g['season'] for g in games})
    index = {(r['game_id'], str(r['player_id'])): r for r in players}
    reports = av.read_reports(injury_path)
    tips = injury_t60.tip_index(api_dir, games, reports)
    maps = {'tminus60': av.status_map(reports, tips)}
    maps['aligned'] = av.status_map(reports, aligned_tips(tips, odds_rows))
    entries = {arm: av.trailing_entries(players, games, *maps[arm]) for arm in ARMS}
    statuses, observed = maps['tminus60']
    game_season = {g['game_id']: g['season'] for g in games}
    by_season = defaultdict(list)
    for r in v12.team_games(games, v12_protocol):
        by_season[r['season']].append(r)
    out = {}
    for season in seasons or v12_protocol['test_seasons']:
        start, end = v12.training_window(season, all_seasons, v12_protocol)
        train_seasons = [s for s in all_seasons if s > v12_protocol['burn_in_season'] and start <= v12.season_start(s) < end]
        table = av.play_table(statuses, index, {g for g in observed if game_season.get(g) in train_seasons})
        train = [dict(r) for s in train_seasons for r in by_season[s]]
        v13.attach(train, entries['tminus60'], table)
        out[season] = {}
        for arm in ARMS:
            test = [dict(r) for r in by_season[season]]
            v13.attach(test, entries[arm], table)
            predictions, _ = v13.team_predictions(train, test)
            out[season][arm] = [dict(game_id=r['game_id'], date=r['date'], model=p['winner'], y=r['home_win'])
                                for r, p in zip(test, predictions)]
    return out


def join(model_rows, odds_rows):
    """Games with both a model probability and a market price taken before tipoff."""
    market = {o['game_id']: o for o in odds_rows}
    return [dict(m, market=market[m['game_id']]['home_no_vig'], overround=market[m['game_id']]['overround'],
                 minutes_to_tipoff=market[m['game_id']]['minutes_to_tipoff'],
                 market_power=market[m['game_id']].get('home_no_vig_power'))
            for m in model_rows if m['game_id'] in market]


def _logits(rows):
    clip = lambda p: np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return logit(clip([r['model'] for r in rows])), logit(clip([r['market'] for r in rows]))


def fit_weight(y, lm, lk, weights=None):
    """c in logit(p) = logit(market) + c * (logit(model) - logit(market)); maximum likelihood, one parameter."""
    w = np.ones(len(y)) if weights is None else weights
    gap = lm - lk

    def loss(c):
        z = lk + c * gap
        return float(np.sum(w * (np.logaddexp(0, z) - y * z)) / w.sum())
    return float(minimize_scalar(loss, bounds=(-3., 4.), method='bounded').x)


def information_weight(rows, protocol):
    """c with a 95% interval that resamples whole dates; 0 = the market is enough, 1 = the model is enough."""
    y = np.array([r['y'] for r in rows], float)
    lm, lk = _logits(rows)
    dates = sorted({r['date'] for r in rows})
    position = {d: i for i, d in enumerate(dates)}
    day = np.array([position[r['date']] for r in rows])
    rng = np.random.default_rng(protocol['seed'])
    draws = []
    for _ in range(protocol['bootstrap']):
        counts = np.bincount(rng.integers(0, len(dates), len(dates)), minlength=len(dates))
        draws.append(fit_weight(y, lm, lk, counts[day].astype(float)))
    return dict(c=fit_weight(y, lm, lk), ci95_date_bootstrap=np.quantile(draws, [.025, .975]).tolist())


def blend(rows, c):
    lm, lk = _logits(rows)
    return expit(lk + c * (lm - lk))


def strata(rows):
    """Descriptive only: by minutes between the price and tipoff, and by size of the model-market gap."""
    out = dict(minutes_to_tipoff=[], gap=[])
    y = np.array([r['y'] for r in rows], float)
    model, market = (np.array([r[k] for r in rows], float) for k in ('model', 'market'))
    minutes = np.array([r['minutes_to_tipoff'] for r in rows], float)
    for low, high in BUCKETS:
        mask = (minutes >= low) & (minutes < high)
        out['minutes_to_tipoff'].append(dict(
            low=low, high=None if high == float('inf') else high, n=int(mask.sum()),
            brier_model=float(np.mean((model[mask] - y[mask]) ** 2)) if mask.any() else None,
            brier_market=float(np.mean((market[mask] - y[mask]) ** 2)) if mask.any() else None))
    gap = model - market
    for low, high in zip(GAP_EDGES[:-1], GAP_EDGES[1:]):
        mask = (gap >= low) & (gap < high)
        out['gap'].append(dict(low=low, high=high, n=int(mask.sum()),
                               model=float(model[mask].mean()) if mask.any() else None,
                               market=float(market[mask].mean()) if mask.any() else None,
                               observed_home_win=float(y[mask].mean()) if mask.any() else None))
    return out


def compare_to_market(rows, protocol):
    """Model vs market vs an equal logit blend; paired Brier differences with a date-block bootstrap."""
    if not rows:
        return dict(n=0)
    dates = [r['date'] for r in rows]
    y = [r['y'] for r in rows]
    model = np.array([r['model'] for r in rows])
    market = np.array([r['market'] for r in rows])
    equal = blend(rows, .5)
    out = dict(
        n=len(rows), mean_overround=float(np.mean([r['overround'] for r in rows])),
        mean_minutes_to_tipoff=float(np.mean([r['minutes_to_tipoff'] for r in rows])),
        model_vs_market=v12.compare(dates, y, model, market, protocol),
        blend_vs_market=v12.compare(dates, y, equal, market, protocol),
        information_weight=information_weight(rows, protocol),
        correlation=float(np.corrcoef(model, market)[0, 1]) if len(rows) > 2 else None,
        mean_abs_gap=float(np.mean(np.abs(model - market))), strata=strata(rows))
    powered = [r for r in rows if r.get('market_power') is not None]
    if len(powered) == len(rows):
        alt = [dict(r, market=r['market_power']) for r in rows]
        out['sensitivity_power_devig'] = dict(
            model_vs_market=v12.compare(dates, y, model, np.array([r['market'] for r in alt]), protocol),
            information_weight=information_weight(alt, protocol))
    return out


def walk_forward(first_rows, second_rows, protocol):
    """Weight fitted on the first season, applied unchanged to the second."""
    if not first_rows or not second_rows:
        return dict(n=0)
    lm, lk = _logits(first_rows)
    c = fit_weight(np.array([r['y'] for r in first_rows], float), lm, lk)
    p = blend(second_rows, c)
    return dict(c_from_first_season=c, n=len(second_rows),
                blend_vs_market=v12.compare([r['date'] for r in second_rows], [r['y'] for r in second_rows], p,
                                            np.array([r['market'] for r in second_rows]), protocol))


def decide(report, protocol):
    """Apply the frozen decision rule to the primary (aligned) arm."""
    seasons = protocol['seasons']
    primary = {s: report['seasons'][s]['aligned'] for s in seasons}
    inconclusive = [s for s in seasons if report['seasons'][s]['coverage'] < COVERAGE_MINIMUM or primary[s].get('n', 0) == 0]
    if inconclusive:
        return dict(verdict='inconclusive', reason=f'coverage below {COVERAGE_MINIMUM} or no games in {inconclusive}')
    better = all(primary[s]['model_vs_market']['ci95_date_bootstrap'][1] < 0 for s in seasons)
    informative = (all(primary[s]['information_weight']['ci95_date_bootstrap'][0] > 0 for s in seasons)
                   and report['walk_forward'].get('blend_vs_market', {}).get('paired_brier_difference', 1) < 0)
    return dict(verdict='better_than_market' if better else 'adds_information' if informative else 'no_evidence_of_added_information',
                better_than_market=bool(better), adds_information=bool(informative))


def evaluate(players, games, tips, odds_rows, odds_stats, v12_protocol, protocol, injury_path, api_dir):
    per_season = model_winner(players, games, v12_protocol, injury_path, api_dir, odds_rows, protocol['seasons'])
    report = dict(retrospective_not_confirmatory=True, odds_load=odds_stats, seasons={})
    for season in protocol['seasons']:
        known = [g['game_id'] for g in games if g['season'] == season and g['game_id'] in tips]
        arms = {arm: join(per_season[season][arm], odds_rows) for arm in ARMS}
        matched = {r['game_id'] for r in arms['aligned']}
        report['seasons'][season] = dict(
            games_with_tipoff=len(known), matched=len(matched & set(known)),
            coverage=len(matched & set(known)) / len(known) if known else 0.,
            **{arm: compare_to_market(rows, STATS) for arm, rows in arms.items()})
    first, second = protocol['seasons']
    report['walk_forward'] = walk_forward(join(per_season[first]['aligned'], odds_rows), join(per_season[second]['aligned'], odds_rows),
                                          STATS)
    report['decision'] = decide(report, protocol)
    return report


def main():
    import argparse
    from . import odds_history as oh
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True)
    parser.add_argument('--protocol', required=True, help='nba_vs_market_protocol.json')
    parser.add_argument('--v12-protocol', required=True)
    parser.add_argument('--injuries', required=True)
    parser.add_argument('--api-dir', required=True)
    parser.add_argument('--plan-file', required=True)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--output', required=True, help='folder holding protocol_frozen.json')
    a = parser.parse_args()
    load = lambda p: json.loads(Path(p).read_bytes())
    if load(Path(a.output) / 'protocol_frozen.json')['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    games = load(Path(a.data) / 'games.json')
    protocol, v12_protocol = load(a.protocol), load(a.v12_protocol)
    players = m1.read_rows(Path(a.data) / 'players.jsonl.gz')
    tips = injury_t60.tip_index(a.api_dir, games, av.read_reports(a.injuries))
    odds, stats = oh.load(load(a.plan_file), a.cache, games)
    report = evaluate(players, games, tips, odds, stats, v12_protocol, protocol, a.injuries, a.api_dir)
    write_json(Path(a.output) / 'market_comparison.json', report)
    write_json(Path(a.output) / 'inputs_market.json', dict(
        source_sha256=digest(__file__), protocol_sha256=digest(a.protocol), injuries_sha256=digest(a.injuries),
        plan_sha256=digest(a.plan_file), players_sha256=digest(Path(a.data) / 'players.jsonl.gz'),
        games_sha256=digest(Path(a.data) / 'games.json')))
    print(json.dumps(dict(decision=report['decision'], coverage={s: v['coverage'] for s, v in report['seasons'].items()}), allow_nan=False))


if __name__ == '__main__':
    main()
