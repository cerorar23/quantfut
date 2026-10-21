"""Observed workload with receipt-time gates and conservative end intervals.

An interval describes uncertainty about completion, not time spent on court.
Counters are lower-bound observed workload when history is incomplete; they
are never converted to minutes, metabolic effort, or exact rest hours.
"""
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .operations import utc


@dataclass(frozen=True)
class LoadObservation:
    event_id: str
    player_ids: tuple[str, str]
    ended_after: str
    ended_by: str
    available_at: str
    status: str
    points: int | None
    games: int | None
    sets: int | None
    deciding_set: int | None
    source_sha256: str

    def __post_init__(self) -> None:
        if not self.event_id or len(self.player_ids) != 2 or len(set(self.player_ids)) != 2:
            raise ValueError('Distinct participants and an event identity required')
        if not utc(self.ended_after) <= utc(self.ended_by) <= utc(self.available_at):
            raise ValueError('Completion interval must precede receipt')
        for key in ('points', 'games', 'sets', 'deciding_set'):
            value = getattr(self, key)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError('Counters must be nonnegative integers or missing')
        if self.deciding_set not in (None, 0, 1):
            raise ValueError('Deciding set indicator must be binary or missing')
        if len(self.source_sha256) != 64 or any(c not in '0123456789abcdef' for c in self.source_sha256):
            raise ValueError('Source SHA-256 required')


class RecentLoadExtractor:
    """Use the latest available revision per event; exclude the target itself.

    All gates are strict before decision_at, which must precede scheduled_start.
    Window boundaries are [decision_at - days, decision_at). An interval that
    straddles a boundary is ambiguous and is not counted as definitely inside.
    Missing counters remain None; known subtotals and coverage are separate.
    """
    WINDOWS = {'points': (3, 7), 'games': (3, 7), 'sets': (3, 7), 'deciding_set': (5,)}

    def transform(self, history: Iterable[LoadObservation], player_id: str,
                  decision_at: str, scheduled_start: str, target_event_id: str,
                  *, history_complete: bool = False) -> dict[str, Any]:
        decision = utc(decision_at)
        if decision >= utc(scheduled_start):
            raise ValueError('Decision must precede scheduled start')
        latest: dict[str, LoadObservation] = {}
        excluded: Counter[str] = Counter()
        for row in history:
            if row.event_id == target_event_id:
                excluded['target_event'] += 1
                continue
            if utc(row.available_at) >= decision or utc(row.ended_by) >= decision:
                excluded['not_known_before_decision'] += 1
                continue
            prior = latest.get(row.event_id)
            if prior and utc(prior.available_at) == utc(row.available_at) and prior != row:
                raise ValueError('Conflicting revisions at the same receipt time')
            if prior is None or utc(row.available_at) > utc(prior.available_at):
                latest[row.event_id] = row
        # Resolve revisions before participant filtering: corrections may change identity.
        usable = [r for r in latest.values() if player_id in r.player_ids
                  and r.status in ('completed', 'retired', 'disqualified')]
        features: dict[str, Any] = {}
        for counter, windows in self.WINDOWS.items():
            for days in windows:
                boundary = decision - timedelta(days=days)
                inside = [r for r in usable if utc(r.ended_after) >= boundary]
                ambiguous = [r for r in usable if utc(r.ended_after) < boundary <= utc(r.ended_by)]
                values = [getattr(r, counter) for r in inside]
                known = [v for v in values if v is not None]
                key = f'{counter}_{days}d'
                features[key] = {
                    'value': sum(known) if len(known) == len(values) and not ambiguous
                             and (inside or history_complete) else None,
                    'known_subtotal': sum(known) if known or history_complete else None,
                    'observed_matches': len(inside), 'with_counter': len(known),
                    'ambiguous_boundary_matches': len(ambiguous),
                    'history_complete': history_complete,
                    'is_observed_lower_bound': not history_complete or len(known) != len(values) or bool(ambiguous),
                }
        return {'player_id': player_id, 'decision_at': decision_at,
                'window_anchor': 'decision_at', 'features': features,
                'excluded': dict(excluded), 'minutes_or_rest_inferred': False}


def api_tennis_history(path: Path, received_at: str, expected_sha256: str) -> list[LoadObservation]:
    """Normalize a captured UTC fixtures response without inventing actual times.

    Provider date is a scheduled date, not a trustworthy completion lower bound.
    Until actual start is known, use an unbounded-past lower bound. The receipt
    of a terminal state gives an upper bound only; short-window membership stays
    ambiguous. Points require full-match Service Points Won denominators for
    both players. Tie-breaks are included there, never reconstructed from games.
    """
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('Archived response does not match receipt hash')
    payload = json.loads(raw)
    if payload.get('success') != 1 or not isinstance(payload.get('result'), list):
        raise ValueError('Successful fixture archive required')
    result = []
    for row in payload['result']:
        if row.get('event_type_type') not in ('Atp Singles', 'Wta Singles', 'Challenger Men Singles', 'Challenger Women Singles'):
            continue
        status = {'Finished': 'completed', 'Retired': 'retired', 'Walk Over': 'walkover',
                  'Cancelled': 'cancelled'}.get(row.get('event_status'))
        if status is None:
            continue
        players = (str(row['first_player_key']), str(row['second_player_key']))
        service: dict[str, int] = {}
        for stat in row.get('statistics', []):
            if stat.get('stat_period') == 'match' and stat.get('stat_name') == 'Service Points Won':
                value = stat.get('stat_total')
                if type(value) is int and value >= 0:
                    key = str(stat['player_key'])
                    if key in service:
                        raise ValueError('Duplicate full-match service counter')
                    service[key] = value
        points = sum(service[p] for p in players) if all(p in service for p in players) else None
        games = sets = deciding = None
        scores = row.get('scores') or []
        # Only completed singles without nonstandard match tie-breaks have
        # unambiguous full games/sets here. Partial retired sets stay missing.
        if status == 'completed' and scores:
            try:
                pairs = [(int(s['score_first']), int(s['score_second'])) for s in scores]
                if all((a == 6 and 0 <= b <= 4) or (b == 6 and 0 <= a <= 4)
                       or (max(a, b) == 7 and min(a, b) in (5, 6)) for a, b in pairs):
                    wins = (sum(a > b for a, b in pairs), sum(b > a for a, b in pairs))
                    if max(wins) == 2 and min(wins) <= 1 and len(pairs) in (2, 3):
                        games = sum(a + b for a, b in pairs)
                        sets = len(pairs)
                        deciding = int(sets == 3)
            except (ValueError, KeyError, TypeError):
                pass
        result.append(LoadObservation('api_tennis:' + str(row['event_key']), players,
                      '0001-01-01T00:00:00+00:00', received_at, received_at, status,
                      points, games, sets, deciding, expected_sha256))
    return result
