"""Research v1.4: v1.3 with missing value relative to the form window and a separate G League category."""
from collections import defaultdict, deque
from datetime import datetime
import json
from pathlib import Path

import numpy as np

from . import availability as av
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from .audit import digest, write_json

G_LEAGUE = 'G League'
CATEGORIES = (*av.STATUSES, G_LEAGUE)
VARIANTS = dict(v13=dict(relative=False, g_league=False), fix1=dict(relative=True, g_league=False),
                fix2=dict(relative=False, g_league=True), v14=dict(relative=True, g_league=True))


def category(status, reason, g_league):
    return G_LEAGUE if g_league and G_LEAGUE in (reason or '') else status


def status_map(reports, tips, g_league):
    """av.status_map with the category of the latest valid row; G League rows get their own category."""
    tips = dict(tips)
    for report in reports:
        for row in report['rows']:
            if row.get('nba_game_id') and row.get('game_tipoff_utc') and row['nba_game_id'] not in tips:
                tips[row['nba_game_id']] = datetime.fromisoformat(row['game_tipoff_utc'])
    best, observed = {}, set()
    for report in reports:
        stamp = datetime.fromisoformat(report['report_timestamp_utc'])
        for row in report['rows']:
            game, player, status = row.get('nba_game_id'), row.get('nba_player_id'), row.get('status_raw')
            if not game or game not in tips or stamp > tips[game] - av.LEAD:
                continue
            observed.add(game)
            if not player or status not in av.STATUSES:
                continue
            key = game, str(player)
            if key not in best or stamp > best[key][0]:
                best[key] = (stamp, category(status, row.get('reason_raw'), g_league), row.get('nba_team_id'))
    return {k: (v[1], v[2]) for k, v in best.items()}, observed


def trailing_entries(players, games, statuses, observed, max_days=370, window=20, minimum=5, form_window=20):
    """av.trailing_entries plus the share of the team's form window the player took part in, for that team."""
    listed = defaultdict(list)
    for (game, player), (status, team) in statuses.items():
        listed[game].append((player, status, team))
    played = {(r['game_id'], str(r['player_id']), r['team_id']) for r in players if r['participated'] and r['minutes'] > 0}
    day_games, day_rows, teams = defaultdict(list), defaultdict(list), {}
    for g in games:
        day_games[g['date']].append(g)
        teams[g['game_id']] = (g['home']['team_id'], g['away']['team_id'])
    for r in players:
        day_rows[r['date']].append(r)
    history, team_of, out = defaultdict(lambda: deque(maxlen=window)), {}, {}
    team_games = defaultdict(lambda: deque(maxlen=form_window))
    for day in sorted(day_games):
        cut = datetime.fromisoformat(day)
        for g in day_games[day]:
            if g['game_id'] not in observed:
                continue
            per_team = defaultdict(list)
            for player, status, team in listed[g['game_id']]:
                recent = [h for h in history[player] if 0 < (cut - h[0]).days <= max_days]
                if len(recent) < minimum:
                    continue
                team = team_of.get(player, team)
                if team not in teams[g['game_id']]:
                    continue
                form = [gid for d, gid in team_games[team] if 0 < (cut - d).days <= max_days]
                share = float(np.mean([(gid, player, team) in played for gid in form])) if form else 0.
                per_team[team].append((player, status, float(np.mean([h[1] for h in recent])),
                                       float(np.mean([h[2] for h in recent])), share))
            out[g['game_id']] = dict(per_team)
        for r in day_rows[day]:
            if r['participated'] and r['minutes'] > 0:
                history[str(r['player_id'])].append((datetime.fromisoformat(day), r['minutes'], r['points']))
                team_of[str(r['player_id'])] = r['team_id']
        for g in day_games[day]:
            for team in teams[g['game_id']]:
                team_games[team].append((cut, g['game_id']))
    return out


def play_table(statuses, players_index, games_in_window):
    """Beta(1,1)-smoothed participation rate per category (same estimator as av.play_table)."""
    counts = {s: [1., 2.] for s in CATEGORIES}
    for (game, player), (status, _) in statuses.items():
        if game not in games_in_window:
            continue
        row = players_index.get((game, player))
        counts[status][0] += int(bool(row and row['participated'] and row['minutes'] > 0))
        counts[status][1] += 1
    return {s: a / b for s, (a, b) in counts.items()}


def absent(share, play, relative):
    return share - play if relative else 1 - play


def missing(entries, table, relative):
    minutes = sum(m * absent(f, table[s], relative) for _, s, m, _, f in entries)
    points = sum(p * absent(f, table[s], relative) for _, s, _, p, f in entries)
    return float(minutes), float(points)


def attach(rows, entries, table, relative):
    for r in rows:
        teams = entries.get(r['game_id'])
        r['observed'] = int(teams is not None)
        for side in ('home', 'away'):
            minutes, points = missing(teams.get(r[side + '_team'], []), table, relative) if teams else (0., 0.)
            r['mm_' + side], r['mp_' + side] = minutes, points


def player_features(rows, index, entries, table, relative):
    """v13.player_features with the relative teammates' term; G League rows set neither own flag."""
    out = np.zeros((len(rows), 3))
    for i, r in enumerate(rows):
        box = index.get((r['game_id'], str(r['unit'])))
        teams = entries.get(r['game_id'])
        if box is None or teams is None:
            continue
        status = None
        listed = teams.get(box['team_id'], [])
        for player, s, *_ in listed:
            if player == str(r['unit']):
                status = s
        out[i, 0] = int(status in ('Questionable', 'Doubtful'))
        out[i, 1] = int(status == 'Probable')
        out[i, 2] = sum(m * absent(f, table[s], relative) for player, s, m, _, f in listed if player != str(r['unit'])) / 48
    return out


def participation_logloss(statuses, index, games, table):
    y, p = [], []
    for (game, player), (status, _) in statuses.items():
        row = index.get((game, player))
        if game in games and row is not None:
            y.append(int(row['participated'] and row['minutes'] > 0)); p.append(table[status])
    y, p = np.array(y, float), np.array(p)
    return dict(n=len(y), logloss=float(np.mean(-y * np.log(p) - (1 - y) * np.log1p(-p))))


def evaluate(players, games, protocol, v12_protocol, injury_path, api_dir, output):
    seasons = sorted({g['season'] for g in games})
    index = {(r['game_id'], str(r['player_id'])): r for r in players}
    game_season = {g['game_id']: g['season'] for g in games}
    tips = av.tipoff_map(api_dir, games)
    reports = av.read_reports(injury_path)
    maps = {flag: status_map(reports, tips, flag) for flag in (False, True)}
    if maps[False][0].keys() != maps[True][0].keys() or maps[False][1] != maps[True][1]:
        raise ValueError('G League category changed the listed rows')
    legacy = av.status_map(reports, tips)
    if legacy != maps[False]:
        raise ValueError('v1.3 statuses do not reproduce')
    entries = {flag: trailing_entries(players, games, maps[flag][0], maps[flag][1]) for flag in (False, True)}
    legacy_entries = av.trailing_entries(players, games, *legacy)
    if {g: {t: [e[:4] for e in v] for t, v in d.items()} for g, d in entries[False].items()} != legacy_entries:
        raise ValueError('v1.3 entries do not reproduce')
    observed = maps[False][1]
    rows = v12.team_games(games, v12_protocol)
    by_season = defaultdict(list)
    for r in rows:
        by_season[r['season']].append(r)
    samples, _ = v12.player_weight_run(players, v12_protocol, .25)
    report = dict(version=protocol['version'], retrospective_not_confirmatory=True, availability={}, markets={}, weights={})
    for season in protocol_test_seasons(v12_protocol):
        start, end = v12.training_window(season, seasons, v12_protocol)
        train_seasons = [s for s in seasons if s > v12_protocol['burn_in_season'] and start <= v12.season_start(s) < end]
        train_games = {g for g in observed if game_season.get(g) in train_seasons}
        test_games = {g for g in observed if game_season.get(g) == season}
        tables = {flag: play_table(maps[flag][0], index, train_games) for flag in (False, True)}
        report['availability'][season] = {
            name: dict(play_probability=tables[flag], **participation_logloss(maps[flag][0], index, test_games, tables[flag]))
            for name, flag in (('v13', False), ('v14', True))}
        team, player = {}, {}
        for name, v in VARIANTS.items():
            flag, table = v['g_league'], tables[v['g_league']]
            train = [dict(r) for s in train_seasons for r in by_season[s]]
            test = [dict(r) for r in by_season[season]]
            attach(train, entries[flag], table, v['relative']); attach(test, entries[flag], table, v['relative'])
            predicted, fit = v13.team_predictions(train, test)
            team[name] = (test, predicted)
            report['weights'].setdefault(season, {})[name] = dict(
                fit, mean_missing_points=float(np.mean([r['mp_home'] + r['mp_away'] for r in test]) / 2))
            for market in v12.PLAYER_MARKETS:
                tr = [r for r in samples[market] if start <= r['date'] < end]
                te = v12.season_rows(samples[market], season)
                w = v13.fit_player(tr, player_features(tr, index, entries[flag], table, v['relative']), None)
                player[name, market] = (te, v13.apply_player(te, player_features(te, index, entries[flag], table, v['relative']), w), w)
        if season in v12_protocol['test_seasons']:
            reproduce_v13(team['v13'], player, entries[False], legacy_entries, tables[False], index, train_seasons, by_season, season, samples, start, end)
        for market in ('winner', 'team_points', 'game_total'):
            base = market_rows(*team['v13'], market)
            out = {}
            for name in ('v14', 'fix1', 'fix2'):
                cand = market_rows(*team[name], market)
                if [x[:2] for x in cand] != [x[:2] for x in base]:
                    raise ValueError('team row alignment lost')
                out[name + '_vs_v13'] = v12.compare([x[0] for x in cand], [x[1] for x in cand], [x[2] for x in cand],
                                                    [x[2] for x in base], v12_protocol)
            report['markets'].setdefault(market, {})[season] = out
        for market in v12.PLAYER_MARKETS:
            te, base, _ = player[('v13', market)]
            out = {}
            for name in ('v14', 'fix1', 'fix2'):
                _, cand, w = player[(name, market)]
                out[name + '_vs_v13'] = v12.compare([r['date'] for r in te], [r['y'] for r in te], cand, base, v12_protocol)
                out[name + '_vs_v13']['weights'] = dict(zip(['logit', 'bias', 'own_questionable', 'own_probable', 'teammates_missing'], w.tolist()))
            report['markets'].setdefault(market, {})[season] = out
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / 'comparison_v14.json', report)
    return report


def protocol_test_seasons(v12_protocol):
    return v12_protocol['test_seasons']


def market_rows(test, predicted, market):
    """(date, y, probability) per unit of one team market, in v12.team_market_rows order."""
    return [(r['date'], int(actual > line), prob) for r, p in zip(test, predicted)
            for m_, _, line, actual, prob in v12.team_market_rows(r, p) if m_ == market]


def reproduce_v13(team, player, entries, legacy_entries, table, index, train_seasons, by_season, season, samples, start, end):
    """The 'v13' variant must equal multimarket_v13 run on the same inputs."""
    train = [dict(r) for s in train_seasons for r in by_season[s]]
    test = [dict(r) for r in by_season[season]]
    v13.attach(train, legacy_entries, table); v13.attach(test, legacy_entries, table)
    predicted, _ = v13.team_predictions(train, test)
    if not np.allclose([p['winner'] for p in predicted], [p['winner'] for p in team[1]], atol=1e-12):
        raise ValueError('v1.3 team markets do not reproduce')
    tr = [r for r in samples['player_points'] if start <= r['date'] < end]
    te = v12.season_rows(samples['player_points'], season)
    w = v13.fit_player(tr, v13.player_features(tr, index, legacy_entries, table), None)
    if not np.allclose(v13.apply_player(te, v13.player_features(te, index, legacy_entries, table), w), player[('v13', 'player_points')][1], atol=1e-12):
        raise ValueError('v1.3 player markets do not reproduce')


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('--data', '--protocol', '--v12-protocol', '--injuries', '--api-dir', '--output'):
        parser.add_argument(name, required=True)
    a = parser.parse_args()
    load = lambda p: json.loads(Path(p).read_bytes())
    frozen = load(Path(a.output) / 'protocol_frozen.json')
    if frozen['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    players = m1.read_rows(Path(a.data) / 'players.jsonl.gz')
    games = load(Path(a.data) / 'games.json')
    report = evaluate(players, games, load(a.protocol), load(a.v12_protocol), a.injuries, a.api_dir, a.output)
    write_json(Path(a.output) / 'inputs_v14.json', dict(
        source_sha256=digest(__file__), availability_sha256=digest(Path(av.__file__)), v13_sha256=digest(Path(v13.__file__)),
        protocol_sha256=digest(a.protocol), injuries_sha256=digest(a.injuries),
        players_sha256=digest(Path(a.data) / 'players.jsonl.gz'), games_sha256=digest(Path(a.data) / 'games.json')))
    print(json.dumps({s: {k: v['logloss'] for k, v in x.items()} for s, x in report['availability'].items()}, allow_nan=False))


if __name__ == '__main__':
    main()
