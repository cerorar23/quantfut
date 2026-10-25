"""Validation of the live 1.4 configuration piece by piece (nba_live14_protocol.json, frozen before running).

Each arm is fitted by the producer's own fit_model as if the target were 2025-26 and scored on 2025-26 regular-season units.
Arms are compared on identical units: the thresholds of the reference arm, each arm pricing them with its own history."""
from collections import defaultdict, deque
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.special import expit
from scipy.stats import norm

from . import availability as av
from . import live_features as lf
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from . import multimarket_v13_live as live
from . import props_residual as pr
from .audit import digest, write_json

TARGET, TUNE = '2025-26', '2024-25'
SEED, BOOTSTRAP = 20261029, 400
OLD_MARKETS = ('player_points', 'player_rebounds', 'player_assists', 'player_points_rebounds', 'player_points_assists',
               'player_rebounds_assists', 'player_points_rebounds_assists')
NEW_MARKETS = ('player_threes', 'player_steals', 'player_blocks', 'player_turnovers', 'player_blocks_steals')
TEAM_MARKETS = ('winner', 'team_points', 'game_total')
N0_GRID = (50, 150, 400)


def season_bounds(season):
    return f'{season[:4]}-08-01', f'{int(season[:4]) + 1}-08-01'


class Config:
    """One arm's inputs: players/games, reports, model options."""

    def __init__(self, name, players, games, reports, options):
        self.name, self.players, self.games, self.reports_path, self.options = name, players, games, reports, options
        self.index = {(r['game_id'], str(r['player_id'])): r for r in players}
        statuses, observed = av.status_map(av.read_reports(reports), av.tipoff_map(API_DIR[0], games))
        self.entries = av.trailing_entries(players, games, statuses, observed)
        self.teams = {g['game_id']: (g['home']['team_id'], g['away']['team_id']) for g in games}
        self.history = lf.TeamHistory(lf.game_records(games))

    def fit(self, protocol, v12_protocol, target, bets):
        before_p = [r for r in self.players if r['season'] < target]
        before_g = [g for g in self.games if g['season'] < target]
        return live.fit_model(before_p, before_g, dict(protocol, target_season=target), v12_protocol, self.reports_path, API_DIR[0], {},
                              self.options, bets)


API_DIR = [None]


def price_units(players, protocol, wanted):
    """For each wanted (game id, player id) -> {market: [lines]}, the arm's raw probability at those lines from its own history."""
    protocol = live.with_combo_rates(protocol)
    days = defaultdict(list)
    for r in live.with_combinations(players):
        days[r['date']].append(r)
    history, out = defaultdict(lambda: deque(maxlen=protocol['history_window'])), []
    for cut in sorted(days):
        for r in days[cut]:
            want = wanted.get((r['game_id'], r['player_id']))
            if want is None:
                continue
            hist = m1.eligible(history[r['player_id']], cut, protocol)
            if not (r['participated'] and r['minutes'] > 0) or len(hist) < protocol['min_history']:
                continue
            min10, usage = lf.player_recent(hist)
            for market, lines in want.items():
                stat = live.stat_of(market)
                if r.get(stat) is None or not live.has_stat(hist, stat):
                    continue
                par = m1.player_parameters(hist, stat, protocol)
                for line, offset in lines:
                    out.append(dict(market=market, date=cut, game_id=r['game_id'], unit=r['player_id'], line=line, offset=offset,
                                    probability=m1.player_over(par, line, protocol), y=int(r[stat] > line), team_id=r['team_id'],
                                    min10=min10, usage_trend=usage))
        for r in days[cut]:
            if r['participated'] and r['minutes'] > 0:
                history[r['player_id']].append(r)
    return out


def calibrated(model, cfg, rows, bets_lines):
    by_market = defaultdict(list)
    for i, r in enumerate(rows):
        by_market[r['market']].append(i)
    p = np.full(len(rows), np.nan)
    for market, idx in by_market.items():
        fit = model['player_fit'].get(market)
        if fit is None:
            continue
        sub = [rows[i] for i in idx]
        x = live.player_design(sub, cfg.index, cfg.entries, model['play_probability'], fit['features'],
                               (cfg.history, cfg.teams, bets_lines))
        p[idx] = expit(x @ np.array(fit['weights']))
    return p


def key(r):
    return (r['market'], r['game_id'], r['unit'], r['line'])


def compare_player(name, base_rows, base_p, cand_rows, cand_p, markets):
    """Paired comparison on the units both arms priced."""
    cand = {key(r): (r, p) for r, p in zip(cand_rows, cand_p) if np.isfinite(p)}
    pairs = [(r, pb, cand[key(r)][1]) for r, pb in zip(base_rows, base_p) if np.isfinite(pb) and key(r) in cand and r['market'] in markets]
    y = np.array([r['y'] for r, _, _ in pairs], float)
    a, b = np.array([x for _, _, x in pairs]), np.array([x for _, x, _ in pairs])
    diff = (a - y) ** 2 - (b - y) ** 2
    dates = [r['date'] for r, _, _ in pairs]
    out = dict(arm=name, units=len(pairs), pooled=dict(paired_brier_difference=float(diff.mean()),
                                                       interval=pr.date_bootstrap(dates, diff, BOOTSTRAP, SEED, .95)), markets={})
    level = 1 - .05 / len(markets)
    for market in markets:
        pick = np.array([r['market'] == market for r, _, _ in pairs])
        if pick.sum() < 200:
            continue
        out['markets'][market] = dict(units=int(pick.sum()), brier_reference=float(np.mean((b[pick] - y[pick]) ** 2)),
                                      brier_candidate=float(np.mean((a[pick] - y[pick]) ** 2)),
                                      paired_brier_difference=float(diff[pick].mean()),
                                      interval=pr.date_bootstrap([d for d, k in zip(dates, pick) if k], diff[pick], BOOTSTRAP, SEED, level))
    out['accept'] = bool(out['pooled']['interval'][1] < 0 and all(m['interval'][0] <= 0 for m in out['markets'].values()))
    return out


def team_units(model, cfg, v12_protocol, season, n0=None, reference_lines=None):
    """(rows, probabilities) of winner, team points and total for a season's regular games, sequentially; optional shift."""
    rows = [r for r in v12.team_games(cfg.games, v12_protocol) if r['season'] == season and str(r['game_id']).startswith('002')]
    rows.sort(key=lambda r: (r['date'], r['game_id']))
    v13.attach(rows, cfg.entries, model['play_probability'])
    preds = live.predict_team(rows, model['fit'])
    zero = [dict(r) for r in rows]
    v13.attach(zero, {}, model['play_probability'])
    zero_preds = live.predict_team(zero, model['fit'])
    done, units = [], []
    i = 0
    by_date = defaultdict(list)
    for r, p, z in zip(rows, preds, zero_preds):
        by_date[r['date']].append((r, p, z))
    for day in sorted(by_date):
        shift = lf.team_shift(done, n0) if n0 is not None else (0., 0.)
        for r, p, z in by_date[day]:
            lines = (reference_lines or {}).get(r['game_id'])
            q = lf.apply_shift(p, shift)
            if lines is None:
                lines = dict(home=q['home']['line'], away=q['away']['line'], total=q['total']['line'])
            units.append(dict(market='winner', date=day, game_id=r['game_id'], line=.5, y=int(r['home_win']), p=q['winner']))
            for side in ('home', 'away'):
                units.append(dict(market='team_points', date=day, game_id=r['game_id'] + side, line=lines[side],
                                  y=int(r[side + '_points'] > lines[side]), p=float(norm.sf(lines[side], q[side]['mean'], q[side]['sd']))))
            units.append(dict(market='game_total', date=day, game_id=r['game_id'], line=lines['total'],
                              y=int(r['home_points'] + r['away_points'] > lines['total']),
                              p=float(norm.sf(lines['total'], q['total']['mean'], q['total']['sd']))))
        for r, p, z in by_date[day]:
            done.append((z['home']['mean'], z['away']['mean'], r['home_points'], r['away_points']))
    lines_out = {}
    for u in units:
        if u['market'] == 'team_points':
            lines_out.setdefault(u['game_id'][:-4], {})[u['game_id'][-4:]] = u['line']
        elif u['market'] == 'game_total':
            lines_out.setdefault(u['game_id'], {})['total'] = u['line']
    return units, lines_out


def compare_team(name, base, cand, markets):
    cmap = {(u['market'], u['game_id']): u for u in cand}
    pairs = [(u, cmap[(u['market'], u['game_id'])]) for u in base if (u['market'], u['game_id']) in cmap and u['market'] in markets]
    y = np.array([u['y'] for u, _ in pairs], float)
    a, b = np.array([c['p'] for _, c in pairs]), np.array([u['p'] for u, _ in pairs])
    diff = (a - y) ** 2 - (b - y) ** 2
    dates = [u['date'] for u, _ in pairs]
    out = dict(arm=name, units=len(pairs), pooled=dict(paired_brier_difference=float(diff.mean()),
                                                       interval=pr.date_bootstrap(dates, diff, BOOTSTRAP, SEED, .95)), markets={})
    level = 1 - .05 / len(markets)
    for market in markets:
        pick = np.array([u['market'] == market for u, _ in pairs])
        if pick.sum():
            out['markets'][market] = dict(units=int(pick.sum()), brier_reference=float(np.mean((b[pick] - y[pick]) ** 2)),
                                          brier_candidate=float(np.mean((a[pick] - y[pick]) ** 2)), paired_brier_difference=float(diff[pick].mean()),
                                          interval=pr.date_bootstrap([d for d, k in zip(dates, pick) if k], diff[pick], BOOTSTRAP, SEED, level))
    return out


def reference_grid(rows):
    wanted = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if str(r['game_id']).startswith('002'):
            wanted[(r['game_id'], r['unit'])][r['market']].append((r['line'], r['offset']))
    return wanted


def run(args):
    load = lambda p: json.loads(Path(p).read_bytes())
    API_DIR[0] = args.api_dir
    root = Path(live.__file__).parents[2]
    protocol = dict(load(root / 'multimarket_v13_live_protocol.json'), _path=str(root / 'multimarket_v13_live_protocol.json'))
    v12_protocol = load(root / 'multimarket_v12_protocol.json')
    pprot = live.player_protocol(v12_protocol)
    run71 = (m1.read_rows(Path(args.data) / 'players.jsonl.gz'), load(Path(args.data) / 'games.json'))
    ext = (m1.read_rows(Path(args.extended) / 'players.jsonl.gz'), load(Path(args.extended) / 'games.json'))
    bets = [json.loads(line) for line in gzip.open(args.bets, 'rt', encoding='utf8')]
    blines = lf.bets_lines(bets)
    base_options = dict(features=list(lf.BASE), team_shift_n0=None, markets=list(OLD_MARKETS))
    env_options = dict(base_options, features=list(lf.BASE) + list(lf.ENV))
    report = dict(version=load(args.protocol)['version'], retrospective_not_confirmatory=True, components={})

    def arm(name, data, reports, options):
        cfg = Config(name, data[0], data[1], reports, options)
        model = cfg.fit(protocol, v12_protocol, TARGET, bets)
        return cfg, model

    # L0: the deployed 1.3.2 path; its 2025-26 grid defines the shared units
    cfg0, model0 = arm('L0', run71, args.old_reports, base_options)
    start, end = season_bounds(TARGET)
    grid_rows = [dict(r, market=m) for m, rows in live.player_training_rows(cfg0.players, pprot, start, end, OLD_MARKETS).items() for r in rows]
    wanted = reference_grid(grid_rows)

    def score(cfg, model):
        rows = price_units(cfg.players, pprot, wanted)
        return rows, calibrated(model, cfg, rows, blines)

    ref_rows, ref_p = score(cfg0, model0)
    team_ref, ref_lines = team_units(model0, cfg0, v12_protocol, TARGET)
    accepted = dict(data='run71', reports=args.old_reports, options=base_options)
    current = (cfg0, model0, ref_rows, ref_p, team_ref)

    # C1 reports
    cfg1, model1 = arm('C1', run71, args.combined_reports, base_options)
    rows1, p1 = score(cfg1, model1)
    c1 = compare_player('C1_reports', current[2], current[3], rows1, p1, OLD_MARKETS)
    report['components']['C1_reports'] = c1
    if c1['accept']:
        accepted['reports'] = args.combined_reports
        current = (cfg1, model1, rows1, p1, team_units(model1, cfg1, v12_protocol, TARGET, reference_lines=ref_lines)[0])

    # C2 data
    cfg2, model2 = arm('C2', ext, accepted['reports'], base_options)
    rows2, p2 = score(cfg2, model2)
    c2 = compare_player('C2_data', current[2], current[3], rows2, p2, OLD_MARKETS)
    team2 = team_units(model2, cfg2, v12_protocol, TARGET, reference_lines=ref_lines)[0]
    c2_team = compare_team('C2_data_team', current[4], team2, TEAM_MARKETS)
    c2['team'] = c2_team
    c2['accept'] = bool(c2['accept'] and all(m['interval'][0] <= 0 for m in c2_team['markets'].values()))
    report['components']['C2_data'] = c2
    if c2['accept']:
        accepted['data'] = 'extended'
        current = (cfg2, model2, rows2, p2, team2)
    data_acc = ext if accepted['data'] == 'extended' else run71

    # C3 environment features
    cfg3, model3 = arm('C3', data_acc, accepted['reports'], env_options)
    rows3, p3 = score(cfg3, model3)
    c3 = compare_player('C3_environment', current[2], current[3], rows3, p3, OLD_MARKETS)
    report['components']['C3_environment'] = c3
    if c3['accept']:
        accepted['options'] = env_options
        current = (cfg3, model3, rows3, p3, current[4])

    # C4 team shift: n0 tuned on 2024-25, applied to 2025-26
    cfg_t = Config('C4_tune', data_acc[0], data_acc[1], accepted['reports'], accepted['options'])
    model_t = cfg_t.fit(protocol, v12_protocol, TUNE, bets)
    tune_base, tune_lines = team_units(model_t, cfg_t, v12_protocol, TUNE)
    tune = {}
    for n0 in N0_GRID:
        cand = team_units(model_t, cfg_t, v12_protocol, TUNE, n0=n0, reference_lines=tune_lines)[0]
        tune[n0] = compare_team(f'n0={n0}', tune_base, cand, ('team_points', 'game_total'))['pooled']['paired_brier_difference']
    best = min(tune, key=tune.get)
    cfg_c, model_c = current[0], current[1]
    shifted = team_units(model_c, cfg_c, v12_protocol, TARGET, n0=best, reference_lines=ref_lines)[0]
    c4 = compare_team('C4_team_shift', current[4], shifted, TEAM_MARKETS)
    pooled_scoring = compare_team('C4_pooled', current[4], shifted, ('team_points', 'game_total'))
    winner = c4['markets'].get('winner')
    c4['accept'] = bool(pooled_scoring['pooled']['interval'][1] < 0 and (winner is None or winner['interval'][0] <= 0))
    c4['n0_tuning_2024_25'] = {str(k): v for k, v in tune.items()}
    c4['n0'] = best
    c4['pooled_scoring'] = pooled_scoring['pooled']
    report['components']['C4_team_shift'] = c4
    accepted_options = dict(accepted['options'], team_shift_n0=best if c4['accept'] else None)

    # C5 new markets with the accepted configuration (their own grid; the live calibration against the raw law)
    cfg5 = Config('C5', data_acc[0], data_acc[1], accepted['reports'], dict(accepted_options, markets=list(OLD_MARKETS + NEW_MARKETS)))
    model5 = cfg5.fit(protocol, v12_protocol, TARGET, bets)
    new_rows = [dict(r, market=m) for m, rows in live.player_training_rows(cfg5.players, pprot, start, end, NEW_MARKETS).items() for r in rows
                if str(r['game_id']).startswith('002')]
    p_new = calibrated(model5, cfg5, new_rows, blines)
    c5 = {}
    for market in NEW_MARKETS:
        idx = [i for i, r in enumerate(new_rows) if r['market'] == market and np.isfinite(p_new[i])]
        if len(idx) < 500:
            c5[market] = dict(skipped='too few units', units=len(idx))
            continue
        y = np.array([new_rows[i]['y'] for i in idx], float)
        raw, cal = np.array([new_rows[i]['probability'] for i in idx]), p_new[idx]
        diff = (cal - y) ** 2 - (raw - y) ** 2
        s = pr.scores(y, cal)
        entry = dict(units=len(idx), raw=pr.scores(y, raw), live=s, live_vs_raw=dict(
            paired_brier_difference=float(diff.mean()),
            interval=pr.date_bootstrap([new_rows[i]['date'] for i in idx], diff, BOOTSTRAP, SEED, 1 - .05 / len(NEW_MARKETS))))
        entry['accept'] = bool(entry['live_vs_raw']['interval'][1] < 0 and .9 <= s['slope'] <= 1.1 and abs(s['intercept']) <= .10)
        c5[market] = entry
    report['components']['C5_new_markets'] = c5
    report['accepted'] = dict(reports='old+t60' if accepted['reports'] == args.combined_reports else 'old', data=accepted['data'],
                              options=dict(accepted_options, markets=list(OLD_MARKETS) + [m for m in NEW_MARKETS if c5.get(m, {}).get('accept')]))
    write_json(Path(args.output) / 'live14_report.json', report)
    write_json(Path(args.output) / 'accepted_options.json', report['accepted']['options'])
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--data', '--extended', '--bets', '--old-reports', '--combined-reports', '--api-dir', '--protocol', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    if json.loads((Path(a.output) / 'protocol_frozen.json').read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    report = run(a)
    write_json(Path(a.output) / 'inputs.json', dict(source_sha256=digest(__file__), live_module_sha256=live.module_digest(),
                                                    features_sha256=digest(lf.__file__), protocol_sha256=digest(a.protocol)))
    print(json.dumps(dict(accepted=report['accepted'], decisions={k: (v.get('accept') if isinstance(v, dict) and 'accept' in v else
                                                                     {m: e.get('accept') for m, e in v.items()}) for k, v in report['components'].items()})))


if __name__ == '__main__':
    main()
