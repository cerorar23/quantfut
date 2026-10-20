"""Evidence-backed, event-specific corrections without rewriting provider data.

Only edition metadata is corrected. An accepted review does not authenticate
participants, a start time, live status, or an individual court. A changed
provider row requires a new review, even when its event identifier is reused.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from .operations import utc
from .venues import VenueRegistry, canonical


def fixture_digest(row: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(row).encode('utf-8')).hexdigest()


class FixtureReviews:
    """Append-only revisions sharing the venue registry's evidence store."""

    def __init__(self, registry: VenueRegistry):
        self.registry = registry
        registry.db.execute('''CREATE TABLE IF NOT EXISTS fixture_reviews(
            revision_id TEXT PRIMARY KEY,review_id TEXT NOT NULL,
            recorded_at TEXT NOT NULL,body TEXT NOT NULL)''')
        for operation in ('UPDATE', 'DELETE'):
            registry.db.execute(f'''CREATE TRIGGER IF NOT EXISTS fixture_reviews_{operation}_immutable
                BEFORE {operation} ON fixture_reviews BEGIN
                SELECT RAISE(ABORT,'append-only fixture review'); END''')
        registry.db.commit()

    def register(self, review: dict[str, Any]) -> str:
        for field in ('review_id', 'provider_event_id', 'input_sha256', 'recorded_at', 'reason'):
            if not isinstance(review.get(field), str) or not review[field]:
                raise ValueError('Explicit event review and reason required')
        if review.get('provider') != 'api_tennis':
            raise ValueError('Unsupported provider')
        if len(review['input_sha256']) != 64 or any(c not in '0123456789abcdef' for c in review['input_sha256']):
            raise ValueError('Canonical input digest required')
        if review.get('field') != 'tournament_season':
            raise ValueError('Only reviewed edition-season correction is supported')
        if review.get('action') not in ('correct', 'quarantine'):
            raise ValueError('Explicit correction or quarantine required')
        if review['action'] == 'correct':
            for key in ('before', 'after'):
                value = review.get(key)
                if not isinstance(value, str) or len(value) != 4 or not value.isdigit():
                    raise ValueError('Season must be an explicit four-digit string')
            if review['before'] == review['after']:
                raise ValueError('Correction must change the season')
        self.registry._check_sources(review.get('sources', []), review['recorded_at'])
        self.registry._check_sources([review['input_source_id']], review['recorded_at'])
        # The reviewed input itself must occur in the archived provider response.
        stored = self.registry.db.execute('SELECT body FROM venue_sources WHERE source_id=?',
                                         (review['input_source_id'],)).fetchone()
        archived = json.loads(Path(json.loads(stored[0])['source_path']).read_bytes())
        if not any(str(row.get('event_key')) == review['provider_event_id'] and
                   fixture_digest(row) == review['input_sha256'] for row in archived['result']):
            raise ValueError('Reviewed event does not match archived provider input')
        return self.registry._insert_revision('fixture_reviews', 'review_id', review['review_id'],
                                              review['recorded_at'], review)

    def apply(self, rows: list[dict[str, Any]], decision_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        decision = utc(decision_at)
        latest: dict[str, dict[str, Any]] = {}
        for record in self.registry.db.execute('SELECT * FROM fixture_reviews ORDER BY recorded_at,revision_id'):
            if utc(record['recorded_at']) < decision:
                latest[record['review_id']] = json.loads(record['body'])
        indexed: dict[str, list[dict[str, Any]]] = {}
        for review in latest.values():
            indexed.setdefault(review['provider_event_id'], []).append(review)
        normalized, audit = [], []
        for original in rows:
            row = deepcopy(original)
            event = str(row.get('event_key'))
            candidates = indexed.get(event, [])
            item: dict[str, Any] = {'provider_event_id': event, 'status': 'not_reviewed',
                                   'provider_season': original.get('tournament_season')}
            if candidates:
                if len(candidates) != 1:
                    raise ValueError('Conflicting event reviews; do not choose one silently')
                review = candidates[0]
                self.registry._check_sources(review['sources'] + [review['input_source_id']], decision_at)
                if fixture_digest(original) != review['input_sha256']:
                    raise ValueError('Provider event changed; review it again')
                if review['action'] == 'quarantine':
                    raise ValueError('Quarantined fixture cannot enter enriched calendar')
                if str(original.get(review['field'])) != review['before']:
                    raise ValueError('Original season differs from reviewed value')
                row[review['field']] = review['after']
                item.update(status='corrected', normalized_season=review['after'],
                            review_id=review['review_id'], recorded_at=review['recorded_at'],
                            reason=review['reason'], sources=review['sources'])
            normalized.append(row)
            audit.append(item)
        return normalized, audit

    def enrich_calendar(self, rows: list[dict[str, Any]], decision_at: str, *,
                        input_timezone: str, source_received_at: str) -> dict[str, Any]:
        normalized, audit = self.apply(rows, decision_at)
        report = self.registry.enrich_calendar(normalized, decision_at, input_timezone=input_timezone,
                                               source_received_at=source_received_at)
        for event, review in zip(report['events'], audit):
            event['edition_review'] = review
            event['provider_season'] = review['provider_season']
        report['n_season_corrected'] = sum(r['status'] == 'corrected' for r in audit)
        report['n_season_unresolved'] = sum(bool(r['review_flags']) for r in report['events'])
        report['provider_input_modified'] = False
        report['individual_fixtures_independently_verified'] = False
        return report
