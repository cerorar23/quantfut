"""Consolidate validated NBA boxes without duplicate games or players; preserve source counts and exclusions."""
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path

from .audit import digest, write_json

CORE = ('points', 'rebounds', 'assists', 'threes', 'steals', 'blocks')
EXTRA = ('fga', 'fta', 'oreb', 'tov', 'fgm', 'ftm', 'fg3a', 'dreb', 'pf', 'plus_minus')


def read_players(path):
    with gzip.open(path, 'rt', encoding='utf8') as stream:
        return [json.loads(line) for line in stream]


def write_players(path, rows):
    with Path(path).open('wb') as file:
        with gzip.GzipFile(filename='', fileobj=file, mode='wb', mtime=0) as stream:
            for row in rows:
                stream.write((json.dumps(row, sort_keys=True) + '\n').encode())


def merge(sources):
    """Sources in increasing detail order; core counts must agree, later non-null columns enrich earlier rows."""
    games, players, provenance = {}, {}, defaultdict(set)
    for name, game_rows, player_rows in sources:
        indexed = {g['game_id']: g for g in game_rows}
        if len(indexed) != len(game_rows):
            raise ValueError('duplicate game in source ' + name)
        seen = set()
        for g in game_rows:
            gid = g['game_id']
            if gid in games:
                old = games[gid]
                if any(old[k] != g[k] for k in ('date', 'season')) or any(
                        old[s][k] != g[s][k] for s in ('home', 'away') for k in ('team_id', 'points')):
                    raise ValueError('conflicting game identities/scores: ' + gid)
                for side in ('home', 'away'):
                    games[gid][side].update({k: v for k, v in g[side].items() if v is not None})
            else:
                games[gid] = json.loads(json.dumps(g))
            provenance[gid].add(name)
        for r in player_rows:
            gid = r['game_id']
            if gid not in indexed or r['date'] != indexed[gid]['date'] or r['team_id'] not in (
                    indexed[gid]['home']['team_id'], indexed[gid]['away']['team_id']):
                raise ValueError('foreign player/game/date in ' + name)
            key = gid, int(r['player_id'])
            if key in seen:
                raise ValueError('duplicate player in ' + name)
            seen.add(key)
            if key in players:
                old = players[key]
                participation_fix = (r.get('participation_proof') == 'official_positive_count'
                                     and not old['participated'] and r['participated']
                                     and not old.get('minutes') and not r.get('minutes'))
                if old['team_id'] != r['team_id'] or (old['participated'] != r['participated'] and not participation_fix) or any(
                        old.get(k) is not None and r.get(k) is not None and old[k] != r[k] for k in CORE):
                    raise ValueError('conflicting player counts: ' + str(key))
                if abs((old.get('minutes') or 0.) - (r.get('minutes') or 0.)) > .25:
                    raise ValueError('conflicting player minutes: ' + str(key))
                old.update({k: v for k, v in r.items() if v is not None and k not in ('minutes', *CORE)})
                for k in CORE:
                    if old.get(k) is None and r.get(k) is not None:
                        old[k] = r[k]
            else:
                players[key] = dict(r)
    by_game = defaultdict(list)
    for row in players.values():
        by_game[row['game_id']].append(row)
    for gid, g in games.items():
        g['season_type'] = g.get('season_type') or {'002': 'regular', '004': 'playoffs', '005': 'play_in', '006': 'cup_final'}.get(gid[:3], 'other')
        g['training_sources'] = sorted(provenance[gid])
        for side in ('home', 'away'):
            own = [r for r in by_game[gid] if r['team_id'] == g[side]['team_id']]
            if any(not r['participated'] and any(r.get(k) not in (None, 0) for k in CORE) for r in own):
                raise ValueError('nonparticipant has production: ' + gid)
            if not own or sum(r.get('points') or 0 for r in own) != g[side]['points']:
                raise ValueError('player points do not reconcile: ' + gid)
            if not 239 <= sum(r.get('minutes') or 0 for r in own) <= 365:
                raise ValueError('team minutes do not reconcile: ' + gid)
            for r in own:
                r['season'], r['season_type'] = g['season'], g['season_type']
                r['training_sources'] = sorted(provenance[gid])
            if all(r.get(k) is not None for r in own for k in ('fga', 'fta', 'oreb', 'tov')):
                g[side]['possessions_estimate'] = sum(r['fga'] + .44 * r['fta'] - r['oreb'] + r['tov'] for r in own)
    game_rows = sorted(games.values(), key=lambda g: (g['date'], g['game_id']))
    player_rows = sorted(players.values(), key=lambda r: (r['date'], r['game_id'], r['team_id'], r['player_id']))
    return player_rows, game_rows


def audit(players, games):
    return dict(games=len(games), player_rows=len(players), players=len({r['player_id'] for r in players}),
                seasons=dict(Counter(g['season'] for g in games)), season_types=dict(Counter(g['season_type'] for g in games)),
                missing_columns={k: sum(r.get(k) is None for r in players if r['participated']) for k in EXTRA},
                latest_date=max(g['date'] for g in games), unique_games=len({g['game_id'] for g in games}) == len(games),
                unique_player_games=len({(r['game_id'], r['player_id']) for r in players}) == len(players))


def build(folders, output):
    sources, hashes = [], {}
    for folder in map(Path, folders):
        gp, pp = folder / 'games.json', folder / 'players.jsonl.gz'
        sources.append((folder.name, json.loads(gp.read_bytes()), read_players(pp)))
        hashes[str(gp)], hashes[str(pp)] = digest(gp), digest(pp)
    players, games = merge(sources)
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    write_players(out / 'players.jsonl.gz', players)
    write_json(out / 'games.json', games)
    report = dict(audit(players, games), sources=hashes)
    write_json(out / 'coverage.json', report)
    return report


def append_completed(players, games, completed, before):
    completed = [g for g in completed if g['date'] < before]
    rows = [dict(r, season=g['season']) for g in completed for r in g['players']]
    entries = [{k: v for k, v in g.items() if k != 'players'} for g in completed]
    return merge([('validated_history', games, players), ('official_current_season', entries, rows)])
