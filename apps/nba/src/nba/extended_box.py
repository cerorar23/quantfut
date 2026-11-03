"""Extended NBA box scores: shot attempts, turnovers, rebound split, fouls, plus-minus and team possessions,
plus play-in and playoff games.

Protocol: nba_extended_box_protocol.json, frozen before building. Data only: trains or promotes nothing."""
from collections import Counter, defaultdict
from datetime import UTC, datetime
import gzip
import json
from pathlib import Path

from . import multimarket as m1
from .audit import digest, write_json
from .availability import EASTERN

EXTRA = ('fgm', 'fga', 'fg3a', 'ftm', 'fta', 'oreb', 'dreb', 'tov', 'pf', 'plus_minus')
COUNTS = m1.STATS + EXTRA
TYPES = {'002': 'regular', '004': 'playoffs', '005': 'play_in'}
SNAKE = dict(points='points', rebounds='rebounds_total', assists='assists', threes='three_pointers_made',
             steals='steals', blocks='blocks', fgm='field_goals_made', fga='field_goals_attempted',
             fg3a='three_pointers_attempted', ftm='free_throws_made', fta='free_throws_attempted',
             oreb='rebounds_offensive', dreb='rebounds_defensive', tov='turnovers', pf='fouls_personal',
             plus_minus='plus_minus_points')
CAMEL = {k: v.split('_')[0] + ''.join(p.title() for p in v.split('_')[1:]) for k, v in SNAKE.items()}
# Official team box column for each count that must equal the players' sum.
TEAM_BOX = dict(points='pts', threes='fg3m', steals='stl', blocks='blk', fgm='fgm', fga='fga', fg3a='fg3a',
                ftm='ftm', fta='fta', oreb='oreb', dreb='dreb', pf='pf')
ORIGINAL = 'github/9252ea665d8ea68ad20aa3209a6546381066fd98/manifest.json'
RELEASE = 'github/sportsdataverse__sportsdataverse-data/release_97519777/manifest.json'
YEARS = range(2022, 2027)
SINGLE_SOURCE_YEARS = (2023, 2024, 2025)  # postseason 2022-23..2024-25: no accepted rows, no team box
MAX_REGULAR_LOSS = .02


def season_of(year):
    return f'{year - 1}-{year % 100:02d}'


def count(value):
    return int(value) if isinstance(value, float) and value.is_integer() else value


def valid(counts):
    return all(type(x) is int and x >= 0 for x in counts[:-1]) and isinstance(counts[-1], (int, float))


def identities(row):
    return (row['points'] == 2 * row['fgm'] + row['threes'] + row['ftm'] and row['rebounds'] == row['oreb'] + row['dreb']
            and row['fgm'] <= row['fga'] and row['threes'] <= row['fg3a'] <= row['fga'] and row['ftm'] <= row['fta'])


def minutes_mmss(text):
    if not text:
        return None
    minutes, seconds = text.split(':')
    return int(minutes) + int(seconds) / 60


def derive(team, players):
    team['players_tov'] = sum(r['tov'] for r in players)
    team['team_turnovers'] = None if team.get('tov') is None else team['tov'] - team['players_tov']
    team['possessions_estimate'] = team['fga'] - team['oreb'] + team['players_tov'] + .44 * team['fta']
    return team


def load(raw_root, sources):
    """Count tuples per (game, player, team) from both player sources, team boxes, and single-source postseason rows."""
    import pyarrow.parquet as pq
    root = Path(raw_root)
    candidates, teams, postseason = defaultdict(set), {}, []
    for year in YEARS:
        for manifest, name, names, ids in [
                (ORIGINAL, f'playerlog_{year}.parquet', CAMEL, ('gameId', 'personId', 'teamId')),
                (RELEASE, f'player_boxscores_{year}.parquet', SNAKE, ('game_id', 'person_id', 'team_id'))]:
            for r in pq.read_table(m1.archive_file(root / manifest, name, sources)).to_pylist():
                if str(r[ids[0]])[:3] not in TYPES:
                    continue
                candidates[tuple(r[k] for k in ids)].add(tuple(count(r[names[k]]) for k in COUNTS))
                if names is SNAKE and year in SINGLE_SOURCE_YEARS and r['game_id'][:3] != '002':
                    postseason.append(dict(r, file_year=year))
        for r in pq.read_table(m1.archive_file(root / ORIGINAL, f'gamelog_{year}.parquet', sources)).to_pylist():
            if str(r['game_id'])[:3] not in TYPES:
                continue
            t = dict(game_id=r['game_id'], date=r['game_date'][:10], season=r['season_year'], team_id=r['team_id'],
                     name=r['team_name'], matchup=r['matchup'], home=' vs. ' in r['matchup'],
                     **{k: count(r[c]) for k, c in TEAM_BOX.items()}, tov=count(r['tov']), minutes=r['min'],
                     possessions=count(r['poss']), pace=r['pace'])
            key = r['game_id'], r['team_id']
            if (' vs. ' not in r['matchup'] and ' @ ' not in r['matchup']) or (key in teams and teams[key] != t):
                raise ValueError('team reference conflict')
            teams[key] = t
    return candidates, teams, postseason


def extend_accepted(accepted, candidates, teams):
    """Accepted rows + exactly one consistent raw tuple; any doubt quarantines the whole game."""
    rows, bad, issues = [], set(), Counter()
    for r in accepted:
        if r.get('id_namespace', 'nba') != 'nba':  # 0022400942 rows carry no namespace in the accepted file
            raise ValueError('NBA ID namespace required')
        if TYPES.get(str(r['game_id'])[:3]) != r['season_type']:
            continue
        matches = {v for v in candidates[(r['game_id'], r['player_id'], r['team_id'])]
                   if v[:3] == (r['points'], r['rebounds'], r['assists']) and valid(v)}
        if len(matches) != 1:
            bad.add(r['game_id']); issues['missing_or_conflicting_counts'] += 1
            continue
        row = dict(r, **dict(zip(COUNTS, *matches)), count_source='accepted_base')
        if not row['participated'] and any(row[k] for k in COUNTS[:-1]):
            bad.add(r['game_id']); issues['DNP_nonzero'] += 1
        if not identities(row):
            bad.add(r['game_id']); issues['player_identity'] += 1
        rows.append(row)
    groups = defaultdict(list)
    for r in rows:
        groups[r['game_id']].append(r)
    games = []
    for gid, players in groups.items():
        ids = sorted({r['team_id'] for r in players})
        refs = [teams.get((gid, i)) for i in ids]
        if gid in bad or len(ids) != 2 or any(t is None for t in refs):
            bad.add(gid); issues['incomplete_game'] += 1; continue
        if sum(t['home'] for t in refs) != 1:
            bad.add(gid); issues['home_away'] += 1; continue
        for t in refs:
            own = [r for r in players if r['team_id'] == t['team_id']]
            if any(r['date'] != t['date'] or r['season'] != t['season'] for r in own) or any(
                    sum(r[k] for r in own) != t[k] for k in TEAM_BOX):
                bad.add(gid); issues['team_count_reconciliation'] += 1
            elif t['tov'] < sum(r['tov'] for r in own):
                bad.add(gid); issues['team_turnovers_negative'] += 1
        if gid in bad:
            continue
        home, = [dict(t) for t in refs if t['home']]
        away, = [dict(t) for t in refs if not t['home']]
        if home['points'] == away['points']:
            bad.add(gid); issues['tied_final'] += 1; continue
        for t in (home, away):
            derive(t, [r for r in players if r['team_id'] == t['team_id']])
        games.append(dict(game_id=gid, date=home['date'], season=home['season'], season_type=players[0]['season_type'],
                          count_source='accepted_base', home=home, away=away))
    return [r for r in rows if r['game_id'] not in bad], games, bad, issues


def api_postseason(api_dir):
    """(season, team pair) -> finished API-Sports postseason games ordered by start time."""
    pairs = defaultdict(list)
    for path in sorted(Path(api_dir).glob('games_*.json')):
        for g in json.loads(path.read_bytes()).get('response', []):
            if g.get('stage') != 3 or g['status']['long'] != 'Finished':
                continue
            season = season_of(int(g['season']) + 1)
            pairs[(season, frozenset([g['teams']['home']['name'], g['teams']['visitors']['name']]))].append(g)
    return {k: sorted(v, key=lambda g: g['date']['start']) for k, v in pairs.items()}


def single_source(raw_rows, api):
    """Postseason games with no accepted rows: sportsdataverse counts, API date/home side/final points."""
    issues, games, rows = Counter(), [], []
    by_game = defaultdict(list)
    for r in raw_rows:
        by_game[r['game_id']].append(r)
    built = {}
    for gid, raw in by_game.items():
        season, stype = season_of(raw[0]['file_year']), TYPES[gid[:3]]
        players, sides = [], {}
        for r in raw:
            minutes = minutes_mmss(r['minutes'])
            players.append(dict(game_id=gid, season=season, season_type=stype, id_namespace='nba',
                                player_id=r['person_id'], team_id=r['team_id'],
                                name=f"{r['first_name']} {r['family_name']}".strip(), minutes=minutes,
                                participated=minutes is not None, status=r['comment'],
                                count_source='sportsdataverse_only', **{k: count(r[SNAKE[k]]) for k in COUNTS}))
            sides.setdefault(r['side'], set()).add((r['team_id'], f"{r['team_city']} {r['team_name']}"))
        if sorted(sides) != ['away', 'home'] or any(len(v) != 1 for v in sides.values()):
            issues['incomplete_game'] += 1; continue
        if not all(valid(tuple(p[k] for k in COUNTS)) and identities(p) for p in players):
            issues['player_identity'] += 1; continue
        teams = {}
        for side, ((team_id, name),) in sides.items():
            own = [p for p in players if p['team_id'] == team_id]
            teams[side] = dict(game_id=gid, season=season, team_id=team_id, name=name, matchup=None, home=side == 'home',
                               **{k: sum(p[k] for p in own) for k in TEAM_BOX}, tov=None, minutes=None,
                               possessions=None, pace=None)
            derive(teams[side], own)
        built[gid] = players, teams
    series = defaultdict(list)
    for gid, (_, teams) in built.items():
        series[(teams['home']['season'], frozenset([teams['home']['name'], teams['away']['name']]))].append(gid)
    for key, gids in series.items():
        gids.sort(key=lambda g: (g[:3] != '005', g))
        scheduled = api.get(key, [])
        if len(scheduled) != len(gids):
            issues['series_count_mismatch'] += len(gids); continue
        for gid, g in zip(gids, scheduled):
            players, teams = built[gid]
            home, away = teams['home'], teams['away']
            if (g['teams']['home']['name'] != home['name'] or g['scores']['home']['points'] != home['points']
                    or g['scores']['visitors']['points'] != away['points']):
                issues['api_mismatch'] += 1; continue
            if home['points'] == away['points']:
                issues['tied_final'] += 1; continue
            day = datetime.fromisoformat(g['date']['start'].replace('Z', '+00:00')).astimezone(EASTERN).date().isoformat()
            for t in (home, away):
                t['date'] = day
            rows += [dict(p, date=day) for p in players]
            games.append(dict(game_id=gid, date=day, season=home['season'], season_type=players[0]['season_type'],
                              count_source='sportsdataverse_only', home=home, away=away))
    return rows, games, issues


def check_reference(rows, games, reference_rows, reference_games):
    """Non-regression: kept regular rows are identical to the reference and nothing new appears in the regular season."""
    ref = {(r['game_id'], r['player_id'], r['team_id']): r for r in reference_rows}
    ref_games = {g['game_id'] for g in reference_games}
    kept = {g['game_id'] for g in games if g['season_type'] == 'regular'}
    if not kept <= ref_games:
        raise ValueError('regular game outside the reference')
    by_game = defaultdict(set)
    for r in reference_rows:
        if r['game_id'] in kept:
            by_game[r['game_id']].add((r['game_id'], r['player_id'], r['team_id']))
    seen = defaultdict(set)
    for r in rows:
        if r['season_type'] != 'regular':
            continue
        key = r['game_id'], r['player_id'], r['team_id']
        if key not in ref or any(r[k] != v for k, v in ref[key].items()):
            raise ValueError(f'row differs from the reference: {key}')
        seen[r['game_id']].add(key)
    if seen != by_game:
        raise ValueError('regular rows missing against the reference')
    return sorted(ref_games - kept)


def build(accepted, reference, raw_root, api_dir, protocol, output):
    sources = [dict(path=Path(accepted).as_posix(), sha256=digest(accepted))]
    candidates, teams, postseason = load(raw_root, sources)
    rows, games, bad, issues = extend_accepted(m1.read_rows(accepted), candidates, teams)
    extra_rows, extra_games, extra_issues = single_source(postseason, api_postseason(api_dir))
    sources += [dict(path=p.as_posix(), sha256=digest(p)) for p in sorted(Path(api_dir).glob('games_*.json'))]
    rows += extra_rows
    games += extra_games
    reference = Path(reference)
    lost = check_reference(rows, games, m1.read_rows(reference / 'players.jsonl.gz'),
                           json.loads((reference / 'games.json').read_bytes()))
    reference_games = len(json.loads((reference / 'games.json').read_bytes()))
    rows.sort(key=lambda r: (r['date'], r['game_id'], r['player_id']))
    games.sort(key=lambda g: (g['date'], g['game_id']))
    output = Path(output)
    with (output / 'players.jsonl.gz').open('wb') as file:
        with gzip.GzipFile(filename='', fileobj=file, mode='wb', mtime=0) as stream:
            for row in rows:
                stream.write((json.dumps(row, sort_keys=True) + '\n').encode())
    write_json(output / 'games.json', games)
    per = Counter((g['season'], g['season_type']) for g in games)
    per_rows = Counter((r['season'], r['season_type']) for r in rows)
    report = dict(
        protocol=protocol['version'], accepted=len(lost) <= MAX_REGULAR_LOSS * reference_games,
        rows=len(rows), games=len(games),
        by_season_type={f'{s} {t}': dict(games=n, rows=per_rows[(s, t)]) for (s, t), n in sorted(per.items())},
        regular_games_lost_vs_reference=len(lost), lost_game_ids=lost, reference_regular_games=reference_games,
        accepted_tier_quarantined_games=len(bad), accepted_tier_issues=dict(issues),
        single_source_tier_issues=dict(extra_issues), sources=sources,
        first_date=rows[0]['date'], last_date=rows[-1]['date'], original_pregame_receipt_known=False)
    write_json(output / 'coverage.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    freeze = sub.add_parser('freeze', help='record the protocol hash before building')
    freeze.add_argument('--protocol', required=True)
    freeze.add_argument('--output', required=True, type=Path)
    run = sub.add_parser('build')
    run.add_argument('--protocol', required=True)
    run.add_argument('--output', required=True, type=Path, help='folder holding protocol_frozen.json')
    run.add_argument('--raw-root', default='apps/nba/.local/raw')
    run.add_argument('--accepted', default='apps/nba/.local/normalized/nba_subsecond_20261006/player_games.jsonl.gz')
    run.add_argument('--reference', default='apps/nba/.local/normalized/nba_f6_run71_20261009/data')
    run.add_argument('--api-dir', default='apps/nba/.local/raw/api_nba_20261006')
    a = parser.parse_args()
    frozen = a.output / 'protocol_frozen.json'
    if a.command == 'freeze':
        if frozen.exists():
            raise ValueError('protocol already frozen')
        write_json(frozen, dict(path=Path(a.protocol).as_posix(), sha256=digest(a.protocol),
                                frozen_at_utc=datetime.now(UTC).isoformat()))
        return
    if json.loads(frozen.read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    report = build(a.accepted, a.reference, a.raw_root, a.api_dir, json.loads(Path(a.protocol).read_bytes()), a.output)
    print(json.dumps({k: report[k] for k in ('accepted', 'rows', 'games', 'regular_games_lost_vs_reference',
                                             'accepted_tier_issues', 'single_source_tier_issues')}))


if __name__ == '__main__':
    main()
