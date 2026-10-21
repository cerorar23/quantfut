"""Point-in-time availability from official injury reports. Retrospective research input only."""
from collections import defaultdict, deque
from datetime import datetime, timedelta
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

EASTERN = ZoneInfo('America/New_York')
STATUSES = ('Out', 'Doubtful', 'Questionable', 'Probable', 'Available', 'unlisted')
LEAD = timedelta(minutes=60)


def tipoff_map(api_dir, games):
    """NBA game id -> UTC tipoff, from api-sports files joined by Eastern date and team names."""
    by_key = {(g['date'], g['home']['name'], g['away']['name']): g['game_id'] for g in games}
    tips = {}
    for path in sorted(Path(api_dir).glob('games_*.json')):
        for r in json.loads(path.read_bytes()).get('response', []):
            if r.get('stage') != 2 or not r['date'].get('start'):
                continue
            start = datetime.fromisoformat(r['date']['start'].replace('Z', '+00:00'))
            key = (start.astimezone(EASTERN).date().isoformat(), r['teams']['home']['name'], r['teams']['visitors']['name'])
            if key in by_key:
                tips[by_key[key]] = start
    return tips


def read_reports(path):
    with gzip.open(path, 'rt', encoding='utf8') as stream:
        return [json.loads(line) for line in stream]


def status_map(reports, tips):
    """(game, player) -> (status, team id); only reports at least LEAD before tipoff; latest wins.

    Returns the map and the set of games with at least one qualifying report ("observed")."""
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
            if not game or game not in tips or stamp > tips[game] - LEAD:
                continue
            observed.add(game)
            if not player or status not in STATUSES:
                continue
            key = game, str(player)
            if key not in best or stamp > best[key][0]:
                best[key] = (stamp, status, row.get('nba_team_id'))
    return {k: (v[1], v[2]) for k, v in best.items()}, observed


def trailing_entries(players, games, statuses, observed, max_days=370, window=20, minimum=5):
    """game id -> team id -> [(player, status, mean minutes, mean points)], using only earlier dates."""
    listed = defaultdict(list)
    for (game, player), (status, team) in statuses.items():
        listed[game].append((player, status, team))
    day_games, day_rows = defaultdict(list), defaultdict(list)
    teams = {}
    for g in games:
        day_games[g['date']].append(g)
        teams[g['game_id']] = (g['home']['team_id'], g['away']['team_id'])
    for r in players:
        day_rows[r['date']].append(r)
    history, team_of, out = defaultdict(lambda: deque(maxlen=window)), {}, {}
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
                per_team[team].append((player, status, float(np.mean([h[1] for h in recent])),
                                       float(np.mean([h[2] for h in recent]))))
            out[g['game_id']] = dict(per_team)
        for r in day_rows[day]:
            if r['participated'] and r['minutes'] > 0:
                history[str(r['player_id'])].append((datetime.fromisoformat(day), r['minutes'], r['points']))
                team_of[str(r['player_id'])] = r['team_id']
    return out


def play_table(statuses, players_index, games_in_window):
    """Beta(1,1)-smoothed participation rate by status over the given game ids."""
    counts = {s: [1., 2.] for s in STATUSES}
    for (game, player), (status, _) in statuses.items():
        if game not in games_in_window:
            continue
        row = players_index.get((game, player))
        counts[status][0] += int(bool(row and row['participated'] and row['minutes'] > 0))
        counts[status][1] += 1
    return {s: a / b for s, (a, b) in counts.items()}


def missing(entries, table):
    """Expected missing minutes and points for one team in one game."""
    minutes = sum(m * (1 - table[s]) for _, s, m, _ in entries)
    points = sum(p * (1 - table[s]) for _, s, _, p in entries)
    return float(minutes), float(points)
