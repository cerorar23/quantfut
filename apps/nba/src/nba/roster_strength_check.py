"""Run the dated roster-strength protocol; no write to a live cohort or deployed model."""
import argparse
from datetime import date, timedelta
import gzip
import json
from pathlib import Path

import numpy as np

from . import live15_check as l15
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from . import multimarket_v13_live as live
from . import props_residual as pr
from . import roster_strength as rs
from .audit import digest, write_json

GRID = [(ridge, weight) for ridge in (25., 100.) for weight in (.25, .5, 1.)]
MARKETS = ('winner', 'team_points', 'game_total')


def units(inp, season, changes, weight):
    table, fit, _ = inp.fit(season, None)
    rows = [dict(r) for r in inp.team_rows(None) if r['season'] == season and str(r['game_id']).startswith('002')]
    v13.attach(rows, inp.entries, table)
    reference = live.predict_team(rows, fit)
    output = []
    for row, base in zip(rows, reference):
        change = changes[row['game_id']]
        pred = rs.adjust(base, change, fit['covariance'], weight)
        common = dict(game_id=row['game_id'], date=row['date'], observed=all(change[s]['observed'] for s in ('home', 'away')),
                      turnover=max(change[s]['turnover'] for s in ('home', 'away')))
        output.append(dict(common, market='winner', unit='winner', y=row['home_win'], p=pred['winner'], base=base['winner']))
        for side in ('home', 'away', 'total'):
            actual = row[side + '_points'] if side != 'total' else row['home_points'] + row['away_points']
            output.append(dict(common, market='game_total' if side == 'total' else 'team_points', unit=side,
                               line=base[side]['line'], y=int(actual > base[side]['line']),
                               p=pred[side]['p'], base=base[side]['p'], shift=pred[side]['mean'] - base[side]['mean']))
    return output


def summarize(rows):
    out = {}
    for market in MARKETS:
        sub = [r for r in rows if r['market'] == market]
        y, p, base = (np.array([r[k] for r in sub]) for k in ('y', 'p', 'base'))
        delta = (p - y) ** 2 - (base - y) ** 2
        dates = [r['date'] for r in sub]
        first = min(dates)
        early = np.array([d < (date.fromisoformat(first) + timedelta(days=30)).isoformat() for d in dates])
        turnover = np.array([r['turnover'] >= .25 for r in sub])
        out[market] = dict(n=len(sub), reference=pr.scores(y, base), candidate=pr.scores(y, p),
                           difference=float(delta.mean()),
                           ci95=pr.date_bootstrap(dates, delta, 800, 20261026, .95),
                           ci975=pr.date_bootstrap(dates, delta, 800, 20261026, .975),
                           first_30_days=dict(n=int(early.sum()), difference=float(delta[early].mean())),
                           high_turnover=dict(n=int(turnover.sum()), difference=float(delta[turnover].mean()) if turnover.any() else None))
    return out


def run(args):
    root = Path(live.__file__).parents[2]
    protocol = args.protocol or root / 'nba_roster_strength_protocol.json'
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / 'protocol_frozen.json', dict(path=str(protocol), sha256=digest(protocol), protocol=json.loads(Path(protocol).read_bytes())))
    print('loading historical inputs', flush=True)
    inp = l15.Inputs(args.data, args.reports, args.api_dir, json.loads((root / 'multimarket_v12_protocol.json').read_bytes()))
    feature_sets, ratings, tune = {}, {}, {}
    for ridge in (25., 100.):
        print(f'individual ridge {ridge}: earlier-season fits and chronological rotations', flush=True)
        feature_sets[ridge], ratings[ridge] = rs.features(inp.games, inp.players, ridge)
        for weight in (.25, .5, 1.):
            scored = summarize(units(inp, '2024-25', feature_sets[ridge], weight))
            key = f'{ridge}:{weight}'
            tune[key] = dict(ridge=ridge, weight=weight, pooled_difference=float(np.mean([scored[m]['difference'] for m in MARKETS])), markets=scored)
            print(key, tune[key]['pooled_difference'], flush=True)
    best = min(tune.values(), key=lambda s: (s['pooled_difference'], s['weight'], -s['ridge']))
    chosen = dict(ridge=best['ridge'], weight=best['weight'])
    print('selected on 2024-25', chosen, flush=True)
    scored = units(inp, '2025-26', feature_sets[chosen['ridge']], chosen['weight'])
    metrics = summarize(scored)
    accepted = metrics['winner']['ci95'][1] < 0 and all(metrics[m]['ci975'][0] <= 0 for m in ('team_points', 'game_total'))
    report = dict(version=json.loads(Path(protocol).read_bytes())['version'], descriptive_retrospective=True,
                  chosen=chosen, tuning=tune, test_season='2025-26', metrics=metrics, accepted=bool(accepted),
                  sources={str(p): digest(p) for p in (Path(args.data) / 'games.json', Path(args.data) / 'players.jsonl.gz',
                                                      Path(args.reports), protocol, Path(rs.__file__), Path(live.__file__))})
    with gzip.open(out / 'evaluation_rows.jsonl.gz', 'wt', encoding='utf8') as f:
        for row in scored:
            f.write(json.dumps(row) + '\n')
    write_json(out / 'report.json', report)
    write_json(out / 'ratings.json', ratings[chosen['ridge']])
    live_rating = rs.fit_ratings(inp.games, inp.players, '2026-08-01', chosen['ridge'])
    write_json(out / 'candidate.json', dict(promoted=False, accepted=bool(accepted), **chosen, ratings=live_rating))
    print(json.dumps(dict(chosen=chosen, accepted=bool(accepted), metrics=metrics)), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('data', 'reports', 'api-dir', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--protocol', type=Path)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
