"""Research v1.5: the unchanged v1.3 model fed with injury reports closest before tipoff minus 60 minutes."""
from collections import defaultdict
import json
from pathlib import Path

import numpy as np

from . import availability as av
from . import injury_t60
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from . import multimarket_v14 as v14
from .audit import digest, write_json


class Arm:
    """Everything the v1.3 pipeline derives from one set of injury reports."""

    def __init__(self, reports, players, games, tips, index):
        self.statuses, self.observed = av.status_map(reports, tips)
        self.entries = av.trailing_entries(players, games, self.statuses, self.observed)
        self.index = index


def season_setup(season, seasons, v12_protocol, game_season, arm):
    start, end = v12.training_window(season, seasons, v12_protocol)
    train_seasons = [s for s in seasons if s > v12_protocol['burn_in_season'] and start <= v12.season_start(s) < end]
    train_games = {g for g in arm.observed if game_season.get(g) in train_seasons}
    return start, end, train_seasons, av.play_table(arm.statuses, arm.index, train_games)


def participation(arm, keys, table):
    y, p = [], []
    for key in keys:
        row = arm.index[key]
        y.append(int(row['participated'] and row['minutes'] > 0)); p.append(table[arm.statuses[key][0]])
    y, p = np.array(y, float), np.array(p)
    return dict(n=len(y), logloss=float(np.mean(-y * np.log(p) - (1 - y) * np.log1p(-p))))


def run_arm(arm, name, players, games, by_season, samples, seasons, game_season, v12_protocol, protocol):
    """Team predictions and player probabilities per test season for one arm."""
    out = {}
    for season in v12_protocol['test_seasons']:
        start, end, train_seasons, table = season_setup(season, seasons, v12_protocol, game_season, arm)
        train = [dict(r) for s in train_seasons for r in by_season[s]]
        test = [dict(r) for r in by_season[season]]
        v13.attach(train, arm.entries, table); v13.attach(test, arm.entries, table)
        predicted, fit = v13.team_predictions(train, test)
        record = dict(team=(test, predicted), fit=fit, table=table, players={}, observed_share=float(np.mean([r['observed'] for r in test])))
        for market in v12.PLAYER_MARKETS:
            tr = [r for r in samples[market] if start <= r['date'] < end]
            te = v12.season_rows(samples[market], season)
            w = v13.fit_player(tr, v13.player_features(tr, arm.index, arm.entries, table), protocol)
            record['players'][market] = (te, v13.apply_player(te, v13.player_features(te, arm.index, arm.entries, table), w), w)
        out[season] = record
    return out


def evaluate(players, games, protocol, v12_protocol, old_path, new_path, api_dir, v13_report_path, output):
    seasons = sorted({g['season'] for g in games})
    index = {(r['game_id'], str(r['player_id'])): r for r in players}
    game_season = {g['game_id']: g['season'] for g in games}
    old, new = av.read_reports(old_path), av.read_reports(new_path)
    tips = injury_t60.tip_index(api_dir, games, old)
    arms = dict(reference=Arm(old, players, games, tips, index), candidate=Arm(old + new, players, games, tips, index))
    by_season = defaultdict(list)
    for r in v12.team_games(games, v12_protocol):
        by_season[r['season']].append(r)
    samples, _ = v12.player_weight_run(players, v12_protocol, .25)
    runs = {name: run_arm(arm, name, players, games, by_season, samples, seasons, game_season, v12_protocol, protocol)
            for name, arm in arms.items()}
    published = json.loads(Path(v13_report_path).read_bytes())['markets']
    report = dict(version=protocol['version'], retrospective_not_confirmatory=True, arms={}, availability={}, markets={}, weights={})
    for name, arm in arms.items():
        report['arms'][name] = dict(reports=len(old) + (len(new) if name == 'candidate' else 0), listed_rows=len(arm.statuses),
                                    observed_games=len(arm.observed))
    for season in v12_protocol['test_seasons']:
        ref, cand = runs['reference'][season], runs['candidate'][season]
        # the reference arm must be the published v1.3
        for market in ('winner', 'team_points', 'game_total'):
            brier = v12.metrics([x[1] for x in v14.market_rows(*ref['team'], market)], [x[2] for x in v14.market_rows(*ref['team'], market)])[0]['brier']
            if abs(brier - published[market][season]['vs_v12']['candidate']['brier']) > 1e-9:
                raise ValueError(f'reference does not reproduce v1.3: {market} {season}')
        for market in v12.PLAYER_MARKETS:
            te, p, _ = ref['players'][market]
            brier = v12.metrics([r['y'] for r in te], p)[0]['brier']
            if abs(brier - published[market][season]['candidate']['brier']) > 1e-9:
                raise ValueError(f'reference does not reproduce v1.3: {market} {season}')
        for market in ('winner', 'team_points', 'game_total'):
            a, b = v14.market_rows(*cand['team'], market), v14.market_rows(*ref['team'], market)
            if [x[:2] for x in a] != [x[:2] for x in b]:
                raise ValueError('team row alignment lost')
            report['markets'].setdefault(market, {})[season] = v12.compare(
                [x[0] for x in a], [x[1] for x in a], [x[2] for x in a], [x[2] for x in b], v12_protocol)
        for market in v12.PLAYER_MARKETS:
            te, p_cand, w = cand['players'][market]
            te_ref, p_ref, _ = ref['players'][market]
            if [(r['game_id'], r['unit']) for r in te] != [(r['game_id'], r['unit']) for r in te_ref]:
                raise ValueError('player row alignment lost')
            report['markets'].setdefault(market, {})[season] = dict(
                v12.compare([r['date'] for r in te], [r['y'] for r in te], p_cand, p_ref, v12_protocol),
                weights=dict(zip(['logit', 'bias', 'own_questionable', 'own_probable', 'teammates_missing'], w.tolist())))
        shared = [k for k in arms['candidate'].statuses if k in arms['reference'].statuses and k in index
                  and game_season.get(k[0]) == season]
        report['availability'][season] = dict(
            shared_listed_rows=len(shared),
            reference=dict(play_probability=ref['table'], **participation(arms['reference'], shared, ref['table'])),
            candidate=dict(play_probability=cand['table'], **participation(arms['candidate'], shared, cand['table'])),
            observed_share=dict(reference=ref['observed_share'], candidate=cand['observed_share']))
        report['weights'][season] = dict(reference=ref['fit'], candidate=cand['fit'])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'comparison_v15.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--data', '--protocol', '--v12-protocol', '--old-reports', '--t60-reports', '--api-dir', '--v13-report', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    load = lambda p: json.loads(Path(p).read_bytes())
    if load(Path(a.output) / 'protocol_frozen.json')['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    players = m1.read_rows(Path(a.data) / 'players.jsonl.gz')
    games = load(Path(a.data) / 'games.json')
    report = evaluate(players, games, load(a.protocol), load(a.v12_protocol), a.old_reports, a.t60_reports, a.api_dir, a.v13_report, a.output)
    write_json(Path(a.output) / 'inputs_v15.json', dict(
        source_sha256=digest(__file__), v13_sha256=digest(Path(v13.__file__)), availability_sha256=digest(Path(av.__file__)),
        protocol_sha256=digest(a.protocol), old_reports_sha256=digest(a.old_reports), t60_reports_sha256=digest(a.t60_reports),
        players_sha256=digest(Path(a.data) / 'players.jsonl.gz'), games_sha256=digest(Path(a.data) / 'games.json')))
    print(json.dumps(report['arms'], allow_nan=False))


if __name__ == '__main__':
    main()
