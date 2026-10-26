"""Official NBA Stats box scores (BoxScoreTraditionalV3) for quarantined games, fetched through a paid proxy.

stats.nba.com times out from this machine and from the VPS, so each request goes through ZenRows. The credit
ceiling is enforced here, before every request. Captured originals are kept untouched; acceptance is a separate,
offline step (`validate`) that never imputes: any doubt leaves the game quarantined."""
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import time

import httpx

from .audit import write_json
from .extended_box import EXTRA, derive, identities, minutes_mmss

ENDPOINT = 'https://stats.nba.com/stats/boxscoretraditionalv3'
ROTATION = 'https://stats.nba.com/stats/gamerotation'
PROXY = 'https://api.zenrows.com/v1/'
CREDITS = dict(basic=1, premium=10)
TEAM_SUMS = dict(points='points', fgm='fieldGoalsMade', fga='fieldGoalsAttempted', threes='threePointersMade',
                 fg3a='threePointersAttempted', ftm='freeThrowsMade', fta='freeThrowsAttempted',
                 oreb='reboundsOffensive', dreb='reboundsDefensive', rebounds='reboundsTotal', assists='assists',
                 steals='steals', blocks='blocks', tov='turnovers', pf='foulsPersonal')
MINUTES_TOLERANCE = .15


def api_key():
    key = os.environ.get('ZENROWS_API_KEY')
    if key:
        return key
    secrets = Path(__file__).resolve().parents[4] / '.zenrows' / 'secrets.json'
    return json.loads(secrets.read_text(encoding='utf-8'))['apiKey']


def target(game_id, resource='box'):
    if resource == 'rotation':
        return f'{ROTATION}?GameID={game_id}&LeagueID=00'
    return (f'{ENDPOINT}?GameID={game_id}&LeagueID=00&endPeriod=0&endRange=28800&rangeType=0'
            f'&startPeriod=0&startRange=0')


def fetch(game_id, tier, key, timeout=120, resource='box'):
    params = dict(url=target(game_id, resource), apikey=key)
    if tier == 'premium':
        params.update(premium_proxy='true', proxy_country='us')
    started = time.time()
    try:
        r = httpx.get(PROXY, params=params, timeout=timeout)
        status, body = r.status_code, r.content
    except httpx.HTTPError as error:
        status, body = None, type(error).__name__.encode()
    return dict(game_id=game_id, tier=tier, status=status, seconds=round(time.time() - started, 1),
                received_utc=datetime.now(UTC).isoformat(), bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                credits=CREDITS[tier] if status == 200 else 0), body


def capture(game_ids, tier, ceiling, output, key=None, pause=1.0, resource='box'):
    """Fetch each game once. Stops at the credit ceiling or after two consecutive failures."""
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    key = key or api_key()
    spent, failures, receipts = 0, 0, []
    for game_id in game_ids:
        target_file = out / (f'{game_id}.json' if resource == 'box' else f'{game_id}_rotation.json')
        if target_file.exists():
            continue
        if spent + CREDITS[tier] > ceiling:
            receipts.append(dict(game_id=game_id, skipped='credit ceiling'))
            break
        receipt, body = fetch(game_id, tier, key, resource=resource)
        spent += receipt['credits']
        if receipt['status'] == 200 and (b'boxScoreTraditional' if resource == 'box' else b'"resultSets"') in body:
            target_file.write_bytes(body)
            failures = 0
        else:
            receipt['rejected'] = body[:200].decode('utf-8', 'replace') if receipt['status'] else 'transport error'
            failures += 1
        receipts.append(receipt)
        with (out / 'receipts.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(receipt, sort_keys=True) + '\n')
        if failures >= 2:
            break
        time.sleep(pause)
    return dict(credits_spent=spent, ceiling=ceiling, tier=tier, requests=len(receipts))


def team_rows(side):
    return [dict(player_id=p['personId'], comment=p['comment'], **p['statistics']) for p in side['players']]


def validate(game_id, payload, base_rows):
    """Issues found in an official box against the contract; an empty list means the game is accepted."""
    box = payload['boxScoreTraditional']
    issues = []
    if box['gameId'] != game_id:
        issues.append('game_id')
    sides = [box['homeTeam'], box['awayTeam']]
    ids = {s['teamId'] for s in sides}
    if len(ids) != 2 or ids != {r['team_id'] for r in base_rows}:
        issues.append('teams')
    if box['homeTeamId'] != sides[0]['teamId'] or box['awayTeamId'] != sides[1]['teamId']:
        issues.append('home_away')
    official = {}
    for side in sides:
        rows = team_rows(side)
        minutes = 0.
        for r in rows:
            played = r['minutes'] not in ('', '0:00')
            if played:
                try:
                    seconds = int(r['minutes'].split(':')[1])
                    value = minutes_mmss(r['minutes'])
                except (ValueError, IndexError):
                    issues.append('minutes_format'); continue
                if seconds > 59:
                    issues.append('minutes_60'); continue
                minutes += value
            elif any(r[k] for k in TEAM_SUMS.values()):
                issues.append('dnp_inconsistent')
            counts = dict(points=r['points'], rebounds=r['reboundsTotal'], assists=r['assists'],
                          threes=r['threePointersMade'], fgm=r['fieldGoalsMade'], oreb=r['reboundsOffensive'],
                          dreb=r['reboundsDefensive'], fga=r['fieldGoalsAttempted'], fg3a=r['threePointersAttempted'],
                          ftm=r['freeThrowsMade'], fta=r['freeThrowsAttempted'])
            if played and not identities(counts):
                issues.append('player_identity')
            official[r['player_id']] = dict(r, team_id=side['teamId'], played=played)
        total = side['statistics']
        for name, column in TEAM_SUMS.items():
            if sum(r[column] for r in rows) != total[column]:
                issues.append(f'team_sum_{name}')
        team_minutes = minutes_mmss(total['minutes'])
        if abs(minutes - team_minutes) > MINUTES_TOLERANCE or (team_minutes - 240) % 25:
            issues.append('team_minutes')
    if sides[0]['statistics']['points'] == sides[1]['statistics']['points']:
        issues.append('tied_final')
    played_base = {r['player_id']: r for r in base_rows if r['participated']}
    for pid, r in played_base.items():
        o = official.get(pid)
        if o is None or not o['played'] or o['team_id'] != r['team_id']:
            issues.append('base_player_missing'); continue
        if (o['points'], o['reboundsTotal'], o['assists']) != (r['points'], r['rebounds'], r['assists']):
            issues.append('base_counts')
        if abs(minutes_mmss(o['minutes']) - r['minutes']) > .25:
            issues.append('base_minutes')
    if any(o['played'] and pid not in played_base for pid, o in official.items()):
        issues.append('official_player_not_in_base')
    return sorted(set(issues))


def validate_rotation(game_id, payload, base_rows):
    """Issues in an official GameRotation against the base box rows; empty means five on the floor all game."""
    issues = []
    tables = {t['name']: t for t in payload.get('resultSets', [])}
    if set(tables) != {'HomeTeam', 'AwayTeam'}:
        return ['tables']
    players = {r['player_id']: r for r in base_rows}
    spans, points, teams = {}, {}, {}
    end = 0
    for table in tables.values():
        names = table['headers']
        side_teams = set()
        for values in table['rowSet']:
            r = dict(zip(names, values))
            pid, a, b = r['PERSON_ID'], r['IN_TIME_REAL'], r['OUT_TIME_REAL']
            if r['GAME_ID'] != game_id or pid not in players or players[pid]['team_id'] != r['TEAM_ID']:
                issues.append('identity'); continue
            if not 0 <= a <= b:
                issues.append('interval'); continue
            side_teams.add(r['TEAM_ID'])
            points[pid] = points.get(pid, 0) + r['PLAYER_PTS']
            end = max(end, b)
            if a == b:
                if r['PLAYER_PTS']:
                    issues.append('zero_time_points')
                continue
            spans.setdefault(pid, []).append((a, b))
            teams[pid] = r['TEAM_ID']
        if len(side_teams) != 1:
            issues.append('teams')
    if end not in {28800 + 3000 * n for n in range(7)}:
        issues.append('duration')
    for pid, intervals in spans.items():
        intervals.sort()
        if any(x[1] > y[0] for x, y in zip(intervals, intervals[1:])):
            issues.append('overlap')
    for pid, r in players.items():
        if points.get(pid, 0) != r['points']:
            issues.append('points')
        ticks = sum(b - a for a, b in spans.get(pid, ()))
        if r['participated'] and r['minutes'] > 0 and abs(ticks / 10 - r['minutes'] * 60) > len(spans.get(pid, ())) + 1:
            issues.append('minutes')
        if not r['participated'] and ticks:
            issues.append('dnp_on_floor')
    for team in set(teams.values()):
        own = {pid: s for pid, s in spans.items() if teams[pid] == team}
        bounds = sorted({0, end} | {t for s in own.values() for pair in s for t in pair})
        if any(sum(any(x <= a and y >= b for x, y in s) for s in own.values()) != 5
               for a, b in zip(bounds, bounds[1:])):
            issues.append('not_five_on_floor')
    return sorted(set(issues))


def team_entry(side, home, opponent, base):
    total = side['statistics']
    name = f"{side['teamCity']} {side['teamName']}"
    tricode, other = side['teamTricode'], opponent['teamTricode']
    team = dict(game_id=base['game_id'], date=base['date'], season=base['season'], team_id=side['teamId'], name=name,
                matchup=f'{tricode} vs. {other}' if home else f'{tricode} @ {other}', home=home,
                points=total['points'], threes=total['threePointersMade'], steals=total['steals'],
                blocks=total['blocks'], fgm=total['fieldGoalsMade'], fga=total['fieldGoalsAttempted'],
                fg3a=total['threePointersAttempted'], ftm=total['freeThrowsMade'], fta=total['freeThrowsAttempted'],
                oreb=total['reboundsOffensive'], dreb=total['reboundsDefensive'], pf=total['foulsPersonal'],
                tov=total['turnovers'], minutes=minutes_mmss(total['minutes']) / 5, possessions=None, pace=None)
    return team


def extend_rows(game_id, payload, base_rows):
    """Base rows of one accepted game, each with the official extended counts (zeros for players who did not play)."""
    box = payload['boxScoreTraditional']
    official = {r['player_id']: r for side in (box['homeTeam'], box['awayTeam']) for r in team_rows(side)}
    rows = []
    for b in base_rows:
        o = official.get(b['player_id'])
        played = o is not None and o['minutes'] not in ('', '0:00')
        counts = dict(threes=o['threePointersMade'], steals=o['steals'], blocks=o['blocks'],
                      fgm=o['fieldGoalsMade'], fga=o['fieldGoalsAttempted'], fg3a=o['threePointersAttempted'],
                      ftm=o['freeThrowsMade'], fta=o['freeThrowsAttempted'], oreb=o['reboundsOffensive'],
                      dreb=o['reboundsDefensive'], tov=o['turnovers'], pf=o['foulsPersonal'],
                      plus_minus=int(o['plusMinusPoints'])) if played else dict.fromkeys(
            ('threes', 'steals', 'blocks') + EXTRA, 0)
        rows.append(dict(b, **counts, count_source='nba_stats_v3_proxy'))
    return rows


def game_entry(game_id, payload, base_rows):
    box = payload['boxScoreTraditional']
    home, away = box['homeTeam'], box['awayTeam']
    base = base_rows[0]
    teams = [team_entry(home, True, away, base), team_entry(away, False, home, base)]
    own = {t['team_id']: [r for r in extend_rows(game_id, payload, base_rows) if r['team_id'] == t['team_id']]
           for t in teams}
    for t in teams:
        derive(t, own[t['team_id']])
    return dict(game_id=game_id, date=base['date'], season=base['season'], season_type='regular',
                count_source='nba_stats_v3_proxy', home=teams[0], away=teams[1])


def recover(raw_dir, game_ids, base_path, output):
    """Accept every game whose official box meets the contract; the rest stay quarantined, with their issues."""
    import collections
    import gzip
    wanted = set(game_ids)
    base = collections.defaultdict(list)
    with gzip.open(base_path, 'rt', encoding='utf8') as stream:
        for line in stream:
            r = json.loads(line)
            if r['game_id'] in wanted:
                base[r['game_id']].append(r)
    rows, games, rejected = [], [], {}
    for game_id in game_ids:
        payload = json.loads((Path(raw_dir) / f'{game_id}.json').read_bytes())
        issues = validate(game_id, payload, base[game_id])
        if issues:
            rejected[game_id] = issues
            continue
        rows += extend_rows(game_id, payload, base[game_id])
        games.append(game_entry(game_id, payload, base[game_id]))
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda r: (r['date'], r['game_id'], r['player_id']))
    with (out / 'players.jsonl.gz').open('wb') as file:
        with gzip.GzipFile(filename='', fileobj=file, mode='wb', mtime=0) as stream:
            for row in rows:
                stream.write((json.dumps(row, sort_keys=True) + '\n').encode())
    games.sort(key=lambda g: (g['date'], g['game_id']))
    write_json(out / 'games.json', games)
    report = dict(requested=len(game_ids), accepted=len(games), rows=len(rows), rejected=rejected,
                  contract='official box: identities, player sums = team totals, valid MM:SS, team minutes, no tie, '
                           'agreement with base points/rebounds/assists/minutes; ":60" minutes are never converted',
                  receipts_sha256=hashlib.sha256((Path(raw_dir) / 'receipts.jsonl').read_bytes()).hexdigest())
    write_json(out / 'report.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('games', help='JSON file with the list of game ids')
    parser.add_argument('output')
    parser.add_argument('--tier', choices=sorted(CREDITS), default='premium')
    parser.add_argument('--resource', choices=('box', 'rotation'), default='box')
    parser.add_argument('--ceiling', type=int, help='maximum ZenRows credits for this run')
    parser.add_argument('--recover', metavar='BASE_PLAYERS', help='validate captured boxes against this base file '
                        'instead of fetching; the output argument is then the captured folder')
    parser.add_argument('--into', help='with --recover: folder for the accepted rows')
    args = parser.parse_args()
    ids = json.loads(Path(args.games).read_text(encoding='utf-8'))
    if args.recover:
        print(json.dumps(recover(args.output, ids, args.recover, args.into), indent=1))
        return
    if args.ceiling is None:
        parser.error('--ceiling is required to fetch')
    summary = capture(ids, args.tier, args.ceiling, args.output, resource=args.resource)
    write_json(Path(args.output) / 'capture_summary.json', summary)
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
