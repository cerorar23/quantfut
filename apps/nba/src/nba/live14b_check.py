"""Validation of RUN071 + new box-score columns against the deployed 1.4.0 configuration (nba_live14b_protocol.json, frozen before running).

Both arms use the accepted 1.4.0 options and reports and differ only in the data; they are compared on the reference arm's 2025-26 grid
of the 11 player markets. player_turnovers, which RUN071 cannot price, is judged by its live calibration against the raw law."""
import gzip
import json
from pathlib import Path

import numpy as np

from . import live14_check as lc
from . import live_features as lf
from . import multimarket as m1
from . import multimarket_v13_live as live
from . import props_residual as pr
from .audit import digest, write_json

SEED = 20261030
MARKETS = lc.OLD_MARKETS + ('player_threes', 'player_steals', 'player_blocks', 'player_blocks_steals')


def run(args):
    load = lambda p: json.loads(Path(p).read_bytes())
    lc.API_DIR[0], lc.SEED = args.api_dir, SEED
    root = Path(live.__file__).parents[2]
    protocol = dict(load(root / 'multimarket_v13_live_protocol.json'), _path=str(root / 'multimarket_v13_live_protocol.json'))
    v12_protocol = load(root / 'multimarket_v12_protocol.json')
    pprot = live.player_protocol(v12_protocol)
    bets = [json.loads(line) for line in gzip.open(args.bets, 'rt', encoding='utf8')]
    blines = lf.bets_lines(bets)
    options = load(args.options)
    if sorted(options['markets']) != sorted(MARKETS):
        raise ValueError('reference options are not the deployed 1.4.0 markets')

    def arm(name, data, markets):
        cfg = lc.Config(name, m1.read_rows(Path(data) / 'players.jsonl.gz'), load(Path(data) / 'games.json'), args.reports,
                        dict(options, markets=list(markets)))
        return cfg, cfg.fit(protocol, v12_protocol, lc.TARGET, bets)

    cfg0, model0 = arm('reference_1_4_0', args.reference, MARKETS)
    start, end = lc.season_bounds(lc.TARGET)
    grid = [dict(r, market=m) for m, rows in live.player_training_rows(cfg0.players, pprot, start, end, MARKETS).items() for r in rows]
    wanted = lc.reference_grid(grid)
    ref_rows = lc.price_units(cfg0.players, pprot, wanted)
    ref_p = lc.calibrated(model0, cfg0, ref_rows, blines)
    cfg1, model1 = arm('run71_columns', args.candidate, MARKETS + ('player_turnovers',))
    rows1 = lc.price_units(cfg1.players, pprot, wanted)
    p1 = lc.calibrated(model1, cfg1, rows1, blines)
    data = lc.compare_player('data', ref_rows, ref_p, rows1, p1, MARKETS)
    weights = {m: dict(zip(f['features'], f['weights'])) for m, f in model1['player_fit'].items()}
    report = dict(version=load(args.protocol)['version'], retrospective_not_confirmatory=True, data=data,
                  environment_weights_candidate={m: {k: w[k] for k in ('pace_c', 'opp_def_c', 'usage_trend') if k in w} for m, w in weights.items()})

    tov = [dict(r, market=m) for m, rows in live.player_training_rows(cfg1.players, pprot, start, end, ('player_turnovers',)).items()
           for r in rows if str(r['game_id']).startswith('002')]
    p_tov = lc.calibrated(model1, cfg1, tov, blines)
    idx = [i for i, r in enumerate(tov) if np.isfinite(p_tov[i])]
    entry = dict(units=len(idx))
    if len(idx) >= 500:
        y = np.array([tov[i]['y'] for i in idx], float)
        raw, cal = np.array([tov[i]['probability'] for i in idx]), p_tov[idx]
        diff = (cal - y) ** 2 - (raw - y) ** 2
        s = pr.scores(y, cal)
        entry.update(raw=pr.scores(y, raw), live=s, live_vs_raw=dict(
            paired_brier_difference=float(diff.mean()), interval=pr.date_bootstrap([tov[i]['date'] for i in idx], diff, lc.BOOTSTRAP, SEED, .99)))
        entry['accept'] = bool(data['accept'] and entry['live_vs_raw']['interval'][1] < 0 and .9 <= s['slope'] <= 1.1
                               and abs(s['intercept']) <= .10)
    else:
        entry['accept'] = False
    report['player_turnovers'] = entry
    accepted = dict(options, markets=list(MARKETS) + (['player_turnovers'] if entry['accept'] else []))
    report['accepted'] = dict(data='run71_columns' if data['accept'] else 'run71', options=accepted if data['accept'] else options)
    write_json(Path(args.output) / 'live14b_report.json', report)
    write_json(Path(args.output) / 'accepted_options.json', report['accepted']['options'])
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--reference', '--candidate', '--reports', '--options', '--bets', '--api-dir', '--protocol', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    if json.loads((Path(a.output) / 'protocol_frozen.json').read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    report = run(a)
    write_json(Path(a.output) / 'inputs.json', dict(source_sha256=digest(__file__), check_sha256=digest(lc.__file__),
                                                    live_module_sha256=live.module_digest(), protocol_sha256=digest(a.protocol),
                                                    candidate_players_sha256=digest(Path(a.candidate) / 'players.jsonl.gz')))
    print(json.dumps(dict(accepted=report['accepted']['data'], pooled=report['data']['pooled'], turnovers=report['player_turnovers'].get('accept'))))


if __name__ == '__main__':
    main()
