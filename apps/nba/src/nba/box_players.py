"""Resolve duplicated empty official stubs without overwriting a real played row."""
import re

ZERO_CLOCK = re.compile(r'(?:0+:0+|PT0+M0+(?:\.0+)?S)?')
PRODUCTION = ('points', 'reboundsTotal', 'assists', 'threePointersMade', 'steals', 'blocks',
              'turnovers', 'fieldGoalsAttempted', 'freeThrowsAttempted')


def participated(stats):
    value = stats.get('minutes') or ''
    return not ZERO_CLOCK.fullmatch(value) or any((stats.get(k) or 0) > 0 for k in PRODUCTION)


def unique_players(people, corrections=None):
    rows, positions = [], {}
    for person in people:
        pid = person['personId']
        if type(pid) is not int or pid <= 0:
            raise ValueError('invalid official player ID')
        if pid not in positions:
            positions[pid] = len(rows)
            rows.append(person)
            continue
        i = positions[pid]
        old = rows[i]
        old_empty = not participated(old['statistics']) and all(
            v in (None, '', 0) for k, v in old['statistics'].items() if k != 'minutes')
        new_empty = not participated(person['statistics']) and all(
            v in (None, '', 0) for k, v in person['statistics'].items() if k != 'minutes')
        if old['statistics'] != person['statistics'] and not (old_empty or new_empty):
            raise ValueError('conflicting duplicated official player')
        if old_empty and not new_empty:
            rows[i] = person
        if corrections is not None:
            corrections.append(dict(player_id=pid, correction='duplicate_empty_stub_removed' if old_empty or new_empty else 'identical_duplicate_removed'))
    return rows
