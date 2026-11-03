"""Validation of the rotation-weighted winner Elo (nba_roster_elo_protocol.json, frozen before running).

Every arm fits the team model as the producer does (multimarket_v13_live.fit_team on the two scored seasons before the target,
with the T-60 availability) and is scored on the same units: regular-season winners in date order."""
from datetime import date, timedelta
import json
from pathlib import Path

import numpy as np

from . import availability as av
from . import live15_check as l15
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from . import multimarket_v13_live as live
from . import props_residual as pr
from . import roster_elo as re_
from .audit import digest, write_json

TARGET, TUNE = '2025-26', '2024-25'
SEED, BOOTSTRAP = 20261027, 400
GRID = [dict(weights=w, alpha=a) for w in re_.WEIGHTS for a in (.5, 1.)]
EARLY_DAYS, MOVED = 30, 25.


class Inputs(l15.Inputs):
    def __init__(self, *args):
        super().__init__(*args)
        self.base = v12.team_games(self.games, self.v12p)
        self.cache = {}

    def team_rows(self, config):
        key = json.dumps(config, sort_keys=True)
        if key not in self.cache:
            rows = [dict(r) for r in self.base]
            if config:
                rows = re_.apply(rows, re_.effective_gaps(self.games, self.players, self.v12p, config['weights'], config['alpha']))
            self.cache[key] = rows
        return self.cache[key]

    def fit(self, target, config):
        seasons = sorted({g['season'] for g in self.games if g['season'] < target})
        start, end = v12.training_window(target, seasons, self.v12p)
        train_seasons = [s for s in seasons if s > self.v12p['burn_in_season'] and start <= v12.season_start(s) < end]
        table = av.play_table(self.statuses, self.index, {g for g in self.observed if self.season_of.get(g) in train_seasons})
        train = [dict(r) for r in self.team_rows(config) if r['season'] in train_seasons]
        v13.attach(train, self.entries, table)
        return table, live.fit_team(train), train_seasons

    def units(self, target, config):
        table, fit, _ = self.fit(target, config)
        rows = sorted((dict(r) for r in self.team_rows(config) if r['season'] == target and str(r['game_id']).startswith('002')),
                      key=lambda r: (r['date'], r['game_id']))
        v13.attach(rows, self.entries, table)
        return [dict(key=r['game_id'], date=r['date'], y=r['home_win'], p=p['winner'],
                     moved=abs(r['elo_gap_mov'] - r.get('elo_gap_base', r['elo_gap_mov'])))
                for r, p in zip(rows, live.predict_team(rows, fit))]


def brier(units):
    return float(np.mean([(u['p'] - u['y']) ** 2 for u in units]))


def paired(base, cand):
    cmap = {u['key']: u for u in cand}
    pairs = [(u, cmap[u['key']]) for u in base if u['key'] in cmap]
    if len(pairs) != len(base) or len(cand) != len(base):
        raise ValueError('arms score different games')
    y = np.array([u['y'] for u, _ in pairs], float)
    a, b = np.array([c['p'] for _, c in pairs]), np.array([u['p'] for u, _ in pairs])
    diff = (a - y) ** 2 - (b - y) ** 2
    dates = [u['date'] for u, _ in pairs]
    first = date.fromisoformat(min(dates))
    early = np.array([d < (first + timedelta(days=EARLY_DAYS)).isoformat() for d in dates])
    moved = np.array([c['moved'] >= MOVED for _, c in pairs])
    part = lambda pick: dict(units=int(pick.sum()), paired_brier_difference=float(diff[pick].mean()) if pick.any() else None,
                             interval=pr.date_bootstrap([d for d, k in zip(dates, pick) if k], diff[pick], BOOTSTRAP, SEED, .95)
                             if pick.sum() > 1 else None)
    out = dict(units=len(pairs), paired_brier_difference=float(diff.mean()),
               interval=pr.date_bootstrap(dates, diff, BOOTSTRAP, SEED, .95),
               reference=pr.scores(y, b), candidate=pr.scores(y, a), first_30_days=part(early),
               moved_at_least_25=part(moved),
               mean_abs_gap_change=float(np.mean([c['moved'] for _, c in pairs])))
    out['accept'] = bool(out['interval'][1] < 0)
    return out


def run(args):
    load = lambda p: json.loads(Path(p).read_bytes())
    root = Path(live.__file__).parents[2]
    inp = Inputs(args.data, args.reports, args.api_dir, load(root / 'multimarket_v12_protocol.json'))
    ref, ref_tune = inp.units(TARGET, None), inp.units(TUNE, None)
    # REF must be the producer's winner: the same fit as nba.live15_check (and the deployed model) for the target.
    l15_ref = l15.Inputs.fit(inp, TARGET, None)[1]
    if inp.fit(TARGET, None)[1]['winner_weights'] != l15_ref['winner_weights']:
        raise ValueError('REF winner weights differ from the deployed team fit')
    tune = {json.dumps(c, sort_keys=True): brier(inp.units(TUNE, c)) - brier(ref_tune) for c in GRID}
    chosen = json.loads(min(tune, key=lambda k: (round(tune[k], 12), GRID.index(json.loads(k)))))
    report = dict(version=load(args.protocol)['version'], retrospective_not_confirmatory=True,
                  reference=dict(target=pr.scores(np.array([u['y'] for u in ref], float), np.array([u['p'] for u in ref])),
                                 tune_brier=brier(ref_tune)),
                  tuning_2024_25=tune, chosen=chosen, decision=paired(ref, inp.units(TARGET, chosen)),
                  other_configurations_2025_26={json.dumps(c, sort_keys=True): paired(ref, inp.units(TARGET, c))
                                                for c in GRID if c != chosen})
    report['accepted'] = report['decision']['accept']
    write_json(Path(args.output) / 'roster_elo_report.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--data', '--reports', '--api-dir', '--protocol', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    if json.loads((Path(a.output) / 'protocol_frozen.json').read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    report = run(a)
    write_json(Path(a.output) / 'inputs.json', dict(source_sha256=digest(__file__), roster_elo_sha256=digest(re_.__file__),
                                                    live_module_sha256=live.module_digest(), protocol_sha256=digest(a.protocol),
                                                    players_sha256=digest(Path(a.data) / 'players.jsonl.gz'),
                                                    games_sha256=digest(Path(a.data) / 'games.json'), reports_sha256=digest(a.reports)))
    d = report['decision']
    print(json.dumps(dict(accepted=report['accepted'], chosen=report['chosen'], tuning=report['tuning_2024_25'],
                          paired=d['paired_brier_difference'], interval=d['interval'])))


if __name__ == '__main__':
    main()
