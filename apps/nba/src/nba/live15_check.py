"""Validation of the team-market prior and recalibration (nba_live15_protocol.json, frozen before running).

Every arm fits the team model as the producer does (multimarket_v13_live.fit_team on the two scored seasons before the target)
and is scored on the same units: regular-season games at the live lines, in date order."""
from datetime import date, timedelta
import json
from pathlib import Path

import numpy as np
from scipy.special import expit

from . import availability as av
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from . import multimarket_v13_live as live
from . import props_residual as pr
from . import team_recal as tr
from .audit import digest, write_json

TARGET, TUNE, BEFORE_TUNE = '2025-26', '2024-25', '2023-24'
SEED, BOOTSTRAP = 20261031, 400
PRIOR_GRID = [dict(rho=rho, drop_days=d) for rho in (.25, .5) for d in (0, 10)]
TAU_GRID = (.05, .1, .2)
EARLY_DAYS = 30


class Inputs:
    def __init__(self, data, reports, api_dir, v12_protocol):
        self.players, self.games = m1.read_rows(Path(data) / 'players.jsonl.gz'), json.loads((Path(data) / 'games.json').read_bytes())
        self.v12p = v12_protocol
        self.index = {(r['game_id'], str(r['player_id'])): r for r in self.players}
        self.statuses, self.observed = av.status_map(av.read_reports(reports), av.tipoff_map(api_dir, self.games))
        self.entries = av.trailing_entries(self.players, self.games, self.statuses, self.observed)
        self.season_of = {g['game_id']: g['season'] for g in self.games}
        self.rows = {}

    def team_rows(self, prior):
        key = json.dumps(prior, sort_keys=True)
        if key not in self.rows:
            self.rows[key] = tr.apply_prior(v12.team_games(self.games, self.v12p), self.games, self.v12p, prior)
        return self.rows[key]

    def fit(self, target, prior):
        """(table, fit) exactly as fit_model's team part for `target`, with the prior on the form."""
        seasons = sorted({g['season'] for g in self.games if g['season'] < target})
        start, end = v12.training_window(target, seasons, self.v12p)
        train_seasons = [s for s in seasons if s > self.v12p['burn_in_season'] and start <= v12.season_start(s) < end]
        table = av.play_table(self.statuses, self.index, {g for g in self.observed if self.season_of.get(g) in train_seasons})
        before = [g for g in self.games if g['season'] < target]
        train = [dict(r) for r in tr.apply_prior(v12.team_games(before, self.v12p), before, self.v12p, prior) if r['season'] in train_seasons]
        v13.attach(train, self.entries, table)
        return table, live.fit_team(train), train_seasons

    def units(self, target, prior, availability=True, model=None):
        table, fit, _ = model or self.fit(target, prior)
        rows = sorted((dict(r) for r in self.team_rows(prior) if r['season'] == target and str(r['game_id']).startswith('002')),
                      key=lambda r: (r['date'], r['game_id']))
        v13.attach(rows, self.entries if availability else {}, table)
        return tr.units(rows, live.predict_team(rows, fit))


def paired(name, base, cand, markets=tr.MARKETS):
    cmap = {(u['market'], u['key']): u for u in cand}
    pairs = [(u, cmap[(u['market'], u['key'])]) for u in base if (u['market'], u['key']) in cmap and u['market'] in markets]
    if any(u['line'] != c['line'] for u, c in pairs):
        raise ValueError('arms disagree on the lines')
    y = np.array([u['y'] for u, _ in pairs], float)
    a, b = np.array([c['p'] for _, c in pairs]), np.array([u['p'] for u, _ in pairs])
    diff = (a - y) ** 2 - (b - y) ** 2
    dates = [u['date'] for u, _ in pairs]
    out = dict(arm=name, units=len(pairs), pooled=dict(paired_brier_difference=float(diff.mean()),
                                                       interval=pr.date_bootstrap(dates, diff, BOOTSTRAP, SEED, .95)), markets={})
    level = 1 - .05 / len(markets)
    for market in markets:
        pick = np.array([u['market'] == market for u, _ in pairs])
        out['markets'][market] = dict(units=int(pick.sum()), brier_reference=float(np.mean((b[pick] - y[pick]) ** 2)),
                                      brier_candidate=float(np.mean((a[pick] - y[pick]) ** 2)),
                                      paired_brier_difference=float(diff[pick].mean()),
                                      interval=pr.date_bootstrap([d for d, k in zip(dates, pick) if k], diff[pick], BOOTSTRAP, SEED, level))
    first = min(dates)
    early = np.array([d < (date.fromisoformat(first) + timedelta(days=EARLY_DAYS)).isoformat() for d in dates])
    out['first_30_days'] = dict(units=int(early.sum()), paired_brier_difference=float(diff[early].mean()))
    out['accept'] = bool(out['pooled']['interval'][1] < 0 and all(m['interval'][0] <= 0 for m in out['markets'].values()))
    return out


def describe(unit_rows):
    out = {}
    for market in tr.MARKETS:
        sub = [u for u in unit_rows if u['market'] == market]
        out[market] = pr.scores(np.array([u['y'] for u in sub], float), np.array([u['p'] for u in sub]))
    return out


def pooled_brier(unit_rows):
    return float(np.mean([(u['p'] - u['y']) ** 2 for u in unit_rows]))


def recalibrated(unit_rows, recal):
    return [dict(u, p=float(expit(tr.recal_p_logit(u['p'], recal, u['market'])))) for u in unit_rows]


def run(args):
    load = lambda p: json.loads(Path(p).read_bytes())
    root = Path(live.__file__).parents[2]
    inp = Inputs(args.data, args.reports, args.api_dir, load(root / 'multimarket_v12_protocol.json'))
    report = dict(version=load(args.protocol)['version'], retrospective_not_confirmatory=True, arms={}, components={})

    ref = inp.units(TARGET, None)
    report['arms']['REF'] = describe(ref)
    accepted, current = dict(prior=None, recal=False, tau=None), ref

    # P: (rho, drop_days) on 2024-25, applied to 2025-26
    tune_ref = inp.units(TUNE, None)
    tune = {json.dumps(p, sort_keys=True): pooled_brier(inp.units(TUNE, p)) - pooled_brier(tune_ref) for p in PRIOR_GRID}
    best = json.loads(min(tune, key=tune.get))
    cand = inp.units(TARGET, best)
    p_cmp = paired('P_prior', current, cand)
    p_cmp.update(tuning_2024_25=tune, chosen=best)
    report['components']['P_prior'] = p_cmp
    report['arms']['P'] = describe(cand)
    if p_cmp['accept']:
        accepted['prior'], current = best, cand

    # R1: logistic recalibration fitted on the previous season's units of the accepted configuration
    recal = tr.fit_recal(inp.units(TUNE, accepted['prior']))
    cand = recalibrated(inp.units(TARGET, accepted['prior']), recal)
    r1 = paired('R1_rolling', current, cand)
    r1['recal_fitted_on_2024_25'] = recal
    report['components']['R1_rolling'] = r1
    report['arms']['R1'] = describe(cand)
    if r1['accept']:
        accepted['recal'], current = True, cand

    # R2: tau on 2024-25 (R1 fitted on 2023-24), applied to 2025-26 with R1 fitted on 2024-25
    recal_tune = tr.fit_recal(inp.units(BEFORE_TUNE, accepted['prior']))
    model_tune = inp.fit(TUNE, accepted['prior'])
    tune_with = inp.units(TUNE, accepted['prior'], model=model_tune)
    tune_without = inp.units(TUNE, accepted['prior'], availability=False, model=model_tune)
    tune_r1 = pooled_brier(recalibrated(tune_with, recal_tune))
    taus = {str(t): pooled_brier(tr.with_intercepts(tune_with, tune_without, recal_tune, t)) - tune_r1 for t in TAU_GRID}
    tau = float(min(taus, key=taus.get))
    model_target = inp.fit(TARGET, accepted['prior'])
    with_av = inp.units(TARGET, accepted['prior'], model=model_target)
    without_av = inp.units(TARGET, accepted['prior'], availability=False, model=model_target)
    cand = tr.with_intercepts(with_av, without_av, recal, tau)
    r2 = paired('R2_in_season', current, cand)
    r2.update(tuning_2024_25=taus, tau=tau, recal_tune_fitted_on_2023_24=recal_tune,
              final_intercepts={m: next(u['intercept'] for u in reversed(cand) if u['market'] == m) for m in tr.MARKETS})
    report['components']['R2_in_season'] = r2
    report['arms']['R2'] = describe(cand)
    if r2['accept']:
        accepted['recal'], accepted['tau'], current = True, tau, cand
    report['accepted'] = accepted
    write_json(Path(args.output) / 'live15_report.json', report)
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
    write_json(Path(a.output) / 'inputs.json', dict(source_sha256=digest(__file__), team_recal_sha256=digest(tr.__file__),
                                                    live_module_sha256=live.module_digest(), protocol_sha256=digest(a.protocol),
                                                    players_sha256=digest(Path(a.data) / 'players.jsonl.gz'),
                                                    games_sha256=digest(Path(a.data) / 'games.json'), reports_sha256=digest(a.reports)))
    print(json.dumps(dict(accepted=report['accepted'], decisions={k: v['accept'] for k, v in report['components'].items()},
                          pooled={k: v['pooled'] for k, v in report['components'].items()})))


if __name__ == '__main__':
    main()
