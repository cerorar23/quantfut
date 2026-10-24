"""Check, against 2025-26, the live calibration of the four sums of points, rebounds and assists.

Protocol: nba_live_combos_protocol.json, frozen before running. The model is fitted by the live producer's own fit_model as if
the target season were 2025-26, and scored at the live threshold grid. Research only: nothing is deployed."""
import json
from pathlib import Path

import numpy as np
from scipy.special import expit, logit

from . import availability as av
from . import multimarket as m1
from . import multimarket_v13 as v13
from . import multimarket_v13_live as live
from . import props_residual as pr
from .audit import digest, write_json

TARGET = '2025-26'
SEED, BOOTSTRAP, LEVEL = 20261028, 400, 1 - .05 / 4
COMBOS = tuple(live.COMBOS)


def features(rows, index, entries, table):
    x = v13.player_features(rows, index, entries, table)
    return np.column_stack([logit(np.clip([r['probability'] for r in rows], 1e-6, 1 - 1e-6)), np.ones(len(rows)), x])


def decide(entry):
    """Enable a market only if the live calibration beats the raw law with a clear margin and is calibrated."""
    live_scores = entry['live']
    return dict(beats_raw=bool(entry['live_vs_raw']['interval'][1] < 0),
                slope_in_range=bool(.9 <= live_scores['slope'] <= 1.1),
                intercept_small=bool(abs(live_scores['intercept']) <= .10))


def enabled(decision):
    return all(decision.values())


def evaluate_market(rows, p_raw, p_live):
    y = np.array([r['y'] for r in rows], float)
    dates = [r['date'] for r in rows]
    diff = (p_live - y) ** 2 - (p_raw - y) ** 2
    entry = dict(units=len(rows), raw=pr.scores(y, p_raw), live=pr.scores(y, p_live),
                 live_vs_raw=dict(paired_brier_difference=float(diff.mean()),
                                  interval=pr.date_bootstrap(dates, diff, BOOTSTRAP, SEED, LEVEL)),
                 reliability=dict(raw=pr_reliability(y, p_raw), live=pr_reliability(y, p_live)), by_offset={})
    for offset in live.LINE_OFFSETS:
        pick = np.array([r['offset'] == offset for r in rows])
        if pick.sum() >= 200:
            entry['by_offset'][str(offset)] = dict(n=int(pick.sum()), brier_raw=float(np.mean((p_raw[pick] - y[pick]) ** 2)),
                                                   brier_live=float(np.mean((p_live[pick] - y[pick]) ** 2)),
                                                   bias_raw=float(p_raw[pick].mean() - y[pick].mean()),
                                                   bias_live=float(p_live[pick].mean() - y[pick].mean()))
    entry['decision'] = decide(entry)
    entry['enable_in_live'] = enabled(entry['decision'])
    return entry


def pr_reliability(y, p, bins=10):
    order = np.argsort(p)
    return [dict(n=int(len(i)), predicted=float(np.mean(p[i])), observed=float(np.mean(y[i]))) for i in np.array_split(order, bins) if len(i)]


def run(args):
    load = lambda p: json.loads(Path(p).read_bytes())
    root = Path(live.__file__).parents[2]
    protocol = dict(load(root / 'multimarket_v13_live_protocol.json'), target_season=TARGET, _path=str(root / 'multimarket_v13_live_protocol.json'))
    v12_protocol = load(root / 'multimarket_v12_protocol.json')
    players = m1.read_rows(Path(args.data) / 'players.jsonl.gz')
    games = load(Path(args.data) / 'games.json')
    before_players, before_games = [r for r in players if r['season'] < TARGET], [g for g in games if g['season'] < TARGET]
    model = live.fit_model(before_players, before_games, protocol, v12_protocol, args.injuries, args.api_dir, {})
    index = {(r['game_id'], str(r['player_id'])): r for r in players}
    tips = av.tipoff_map(args.api_dir, games)
    statuses, observed = av.status_map(av.read_reports(args.injuries), tips)
    entries = av.trailing_entries(players, games, statuses, observed)
    samples = live.player_training_rows(players, live.player_protocol(v12_protocol), f'{TARGET[:4]}-08-01', f'{int(TARGET[:4]) + 1}-08-01')
    report = dict(version=load(args.protocol)['version'], retrospective_not_confirmatory=True, train_seasons=model['train_seasons'],
                  play_probability=model['play_probability'], markets={})
    for market in COMBOS:
        rows = samples[market]
        x = features(rows, index, entries, model['play_probability'])
        w = np.array(model['player_fit'][market]['weights'])
        entry = evaluate_market(rows, expit(x[:, 0]), expit(x @ w))
        entry['weights'] = dict(zip(model['player_fit'][market]['features'], w.tolist()))
        entry['training_observations'] = model['player_fit'][market]['observations']
        report['markets'][market] = entry
    write_json(Path(args.output) / 'live_combos_report.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--data', '--injuries', '--api-dir', '--protocol', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    if json.loads((Path(a.output) / 'protocol_frozen.json').read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    report = run(a)
    write_json(Path(a.output) / 'inputs.json', dict(source_sha256=digest(__file__), live_module_sha256=digest(live.__file__),
                                                    protocol_sha256=digest(a.protocol), players_sha256=digest(Path(a.data) / 'players.jsonl.gz'),
                                                    injuries_sha256=digest(a.injuries)))
    print(json.dumps({m: dict(enable=e['enable_in_live'], **e['decision']) for m, e in report['markets'].items()}))


if __name__ == '__main__':
    main()
