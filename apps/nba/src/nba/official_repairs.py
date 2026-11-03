"""Reconcile archived official boxes: carry :60 exactly and retain genuine zero-clock participants.

Raw captures are never edited. A complete coherent official box may correct a quarantined secondary row;
every disagreement and normalization is retained in the repair report.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from .extended_box import identities
from .stats_proxy import TEAM_SUMS
from .training_data import read_players, write_players
from .audit import write_json
from .box_players import unique_players, participated


def clock(value):
    if value in ('', None):
        return 0.
    parts = value.split(':')
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError('unsupported official minutes')
    minute, second = map(int, parts)
    if second > 60:
        raise ValueError('official seconds exceed 60')
    return minute + second / 60.


def normalize(gid, payload, references, raw_sha):
    box = payload['boxScoreTraditional']
    if box['gameId'] != gid or len({r['date'] for r in references}) != 1 or len({r['season'] for r in references}) != 1:
        raise ValueError('official game/date/season identity mismatch')
    ref = references[0]
    if {r['team_id'] for r in references} != {box['homeTeamId'], box['awayTeamId']}:
        raise ValueError('official reference teams disagree')
    rows, teams, corrections, seen = [], [], [], set()
    previous = {r['player_id']: r for r in references}
    for label, is_home in (('homeTeam', True), ('awayTeam', False)):
        side = box[label]
        if side['teamId'] != box[label + 'Id']:
            raise ValueError('official locality mismatch')
        total = side['statistics']
        own = []
        for person in unique_players(side['players'], corrections):
            pid, stats = person['personId'], person['statistics']
            if type(pid) is not int or pid <= 0 or pid in seen:
                raise ValueError('official player identity mismatch')
            seen.add(pid)
            if any(type(stats[k]) is not int or stats[k] < 0 for k in TEAM_SUMS.values()):
                raise ValueError('invalid official counts')
            minutes = clock(stats['minutes'])
            counts = {key: stats[column] for key, column in TEAM_SUMS.items()}
            if not identities(counts):
                raise ValueError('official player statistical identities disagree')
            did_play = participated(stats)
            row = dict(game_id=gid, date=ref['date'], season=ref['season'], season_type='regular',
                       team_id=side['teamId'], player_id=pid, name=(person['firstName'] + ' ' + person['familyName']).strip(),
                       id_namespace='nba', minutes=minutes, participated=did_play, **counts,
                       plus_minus=int(stats['plusMinusPoints']), count_source='official_reconciled_20261026',
                       source_sha256=raw_sha, original_minutes=stats['minutes'])
            if minutes == 0 and did_play:
                row['participation_proof'] = 'official_positive_count'
                corrections.append(dict(player_id=pid, correction='zero_clock_participant', counts=counts))
            if str(stats['minutes']).endswith(':60'):
                corrections.append(dict(player_id=pid, correction='exact_seconds_carry', original=stats['minutes'], minutes=minutes))
            old = previous.get(pid)
            if old and (any(old.get(k) is not None and old.get(k) != row[k] for k in ('points', 'rebounds', 'assists'))
                        or bool(old['participated']) != did_play):
                corrections.append(dict(player_id=pid, correction='coherent_official_box_over_quarantined_row',
                                        old={k: old.get(k) for k in ('points', 'rebounds', 'assists', 'minutes', 'participated')},
                                        official={k: row[k] for k in ('points', 'rebounds', 'assists', 'minutes', 'participated')}))
            own.append(row)
        for key, column in TEAM_SUMS.items():
            if sum(r[key] for r in own) != total[column]:
                raise ValueError('official player/team count sum mismatch: ' + key)
        team_minutes = clock(total['minutes'])
        if abs(sum(r['minutes'] for r in own) - team_minutes) > .15 or abs((team_minutes - 240) % 25) > 1e-9:
            raise ValueError('official team minutes mismatch')
        team = dict(game_id=gid, date=ref['date'], season=ref['season'], team_id=side['teamId'],
                    name=side['teamCity'] + ' ' + side['teamName'], home=is_home,
                    **{key: total[col] for key, col in TEAM_SUMS.items()})
        teams.append(team)
        rows.extend(own)
    if teams[0]['points'] == teams[1]['points']:
        raise ValueError('tied official final')
    return rows, dict(game_id=gid, date=ref['date'], season=ref['season'], season_type='regular',
                      count_source='official_reconciled_20261026', home=teams[0], away=teams[1]), corrections


def recover(raw_dir, reference_players, gids, output):
    references = defaultdict(list)
    wanted = set(gids)
    for row in read_players(reference_players):
        if row['game_id'] in wanted:
            references[row['game_id']].append(row)
    players, games, evidence, rejected = [], [], {}, {}
    for gid in gids:
        path = Path(raw_dir) / (gid + '.json')
        raw = path.read_bytes()
        try:
            rows, game, corrections = normalize(gid, json.loads(raw), references[gid], hashlib.sha256(raw).hexdigest())
        except (ValueError, KeyError, IndexError, TypeError) as error:
            rejected[gid] = str(error)
            continue
        players.extend(rows); games.append(game); evidence[gid] = corrections
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    write_players(out / 'players.jsonl.gz', players)
    write_json(out / 'games.json', games)
    report = dict(requested=len(gids), accepted=len(games), player_rows=len(players), corrections=evidence, rejected=rejected,
                  raw_originals_unchanged=True, semantics='zero clock with recorded production is participation, never invented positive minutes')
    write_json(out / 'report.json', report)
    return report
