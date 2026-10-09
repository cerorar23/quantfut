"""Reusable finite collection of genuine NBA player O/U prices."""
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import re

import httpx

from .audit import digest, write_json
from .context import name_key, utc
from .odds_capture import BoundedOddsCapture, prop_pairs

PROFILE = Path(__file__).with_name('props_sources.json')
SPORTS = ('basketball_nba_preseason', 'basketball_nba')


def future_events(catalogs, now, maximum):
    """Balance regular/preseason samples without querying already started events."""
    if type(maximum) is not int or not 1 <= maximum <= 8:
        raise ValueError('one to eight events required')
    seen = set()
    pools = {sport: [] for sport in SPORTS}
    for event in catalogs:
        event_id, sport = event['id'], event['sport_key']
        if sport not in pools or not re.fullmatch(r'[a-f0-9]{32}', event_id) or event_id in seen:
            raise ValueError('distinct NBA provider events required')
        seen.add(event_id)
        if utc(event['commence_time']) > now:
            pools[sport].append(event)
    for pool in pools.values():
        pool.sort(key=lambda e:(utc(e['commence_time']), e['id']))
    selected = []
    while len(selected) < maximum and any(pools.values()):
        for sport in SPORTS:
            if pools[sport] and len(selected) < maximum:
                selected.append(pools[sport].pop(0))
    return selected


def capture_props(destination, key, cap, *, maximum_events=8, client=None, clock=None, regular_only=False):
    """Raw prices are data-ready; rules, identity and availability are separate gates."""
    if type(maximum_events) is not int or not 1 <= maximum_events <= 8:
        raise ValueError('one to eight events required')
    if not key or type(cap) is not int or not 1 <= cap <= 250:
        raise ValueError('existing key and explicit bounded credit cap required')
    profile = json.loads(PROFILE.read_bytes())
    books, markets = profile['bookmakers'], profile['markets']
    if (not 1 <= len(books) <= 10 or len(set(books)) != len(books)
            or set(markets) != {'player_points','player_rebounds','player_assists'}):
        raise ValueError('bounded prop source profile required')
    now = clock or (lambda: datetime.now(UTC))
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=False)
    write_json(root/'protocol.json', dict(profile=profile, profile_sha256=digest(PROFILE),
        credit_cap=cap, maximum_events=maximum_events, created_at_utc=now().isoformat(),
        selection='earliest future regular events' if regular_only else 'alternate earliest future preseason/regular events; fixed before paid queries',
        max_cost_per_event=4, automatic_retries=False, actionable=False))
    owned = client is None
    http = client or httpx.Client(timeout=25, follow_redirects=False)
    capture = BoundedOddsCapture(root/'raw', key, cap, client=http)
    catalogs, rows, pairs, quarantined = [], [], [], []
    try:
        capture.request('account.json', 'sports', {}, 0)
        for sport in (('basketball_nba',) if regular_only else SPORTS):
            if capture.meta['stopped']:
                break
            payload = capture.request(sport+'_events.json', f'sports/{sport}/events', {}, 0)
            if payload is None:
                break
            if not isinstance(payload, list):
                capture.stop('invalid_catalog'); break
            catalogs.extend(dict(event, sport_key=sport) for event in payload)
        selected = future_events(catalogs, now(), maximum_events)
        write_json(root/'selected_events.json', dict(events=selected, selected_at_utc=now().isoformat(), before_paid_queries=True))
        for event in selected:
            if capture.meta['stopped']:
                break
            record = dict(event_id=event['id'], sport_key=event['sport_key'], home_team=event['home_team'],
                away_team=event['away_team'], scheduled_utc=event['commence_time'], pairs=0, status='not_received',
                discovered_markets={}, coverage_status='unknown', actionable=False)
            rows.append(record)
            if now() >= utc(event['commence_time']):
                record.update(status='skipped_started', coverage_status='not_queried'); continue
            parameters = dict(bookmakers=','.join(books), dateFormat='iso')
            path = f"sports/{event['sport_key']}/events/{event['id']}"
            discovery = capture.request('markets_'+event['id']+'.json', path+'/markets', parameters, 1)
            if discovery is None:
                continue
            try:
                _event_matches(discovery, event, books)
                record['discovered_markets'] = {b['key']: sorted(m['key'] for m in b.get('markets', [])) for b in discovery.get('bookmakers', [])}
            except (KeyError, TypeError, ValueError):
                capture.stop('discovery_identity_or_shape_mismatch'); record['status']='quarantined'; continue
            if now() >= utc(event['commence_time']):
                record.update(status='skipped_started', coverage_status='not_queried'); continue
            payload = capture.request('props_'+event['id']+'.json', path+'/odds',
                dict(parameters, markets=','.join(markets), oddsFormat='decimal'), 3)
            if payload is None:
                continue
            receipt = capture.meta['files'][-1]
            try:
                _event_matches(payload, event, books)
                expected = dict(odds_api_event_id=event['id'], home_team=event['home_team'],
                    away_team=event['away_team'], scheduled_utc=event['commence_time'])
                accepted, rejected = prop_pairs(payload, receipt, expected, receipt['first_received_at_utc'], historical=False)
                pairs.extend(dict(pair, sport_key=event['sport_key'], home_team=event['home_team'],
                    away_team=event['away_team'], tipoff_utc=event['commence_time'], data_ready=True,
                    source='the_odds_api', scope='provider_bookmaker_version; Mexican equivalence unknown') for pair in accepted)
                quarantined.extend(dict(event_id=event['id'], **row) for row in rejected)
                record.update(status='received', pairs=len(accepted), coverage_status='pairs_received' if accepted else 'no_pairs_at_receipt',
                    first_received_at_utc=receipt['first_received_at_utc'], raw_sha256=receipt['sha256'])
            except (KeyError, TypeError, ValueError) as error:
                record.update(status='quarantined', coverage_status='unknown')
                quarantined.append(dict(event_id=event['id'], reason=type(error).__name__))
                # A late receipt is preserved, never admitted as a pregame price.
        write_json(root/'pairs.json', pairs)
        write_json(root/'quarantine.json', quarantined)
        write_json(root/'coverage.json', rows)
        result = dict(capture_status='functional' if pairs else 'no_pairs_in_current_sample', selected_events=len(selected),
            queried_events=len(rows), pairs=len(pairs), pairs_by_market=dict(Counter(p['market'] for p in pairs)),
            pairs_by_book=dict(Counter(p['book'] for p in pairs)), provider_API_calls=len(capture.meta['files']),
            credit_cap=cap, credits_consumed=capture.meta['charged_credits'], credits_reserved=capture.meta['reserved_credits'],
            stopped=capture.meta['stopped'], errors=capture.meta['errors'], pregame_data_ready=bool(pairs),
            production_ready=False, actionable=False, quote_file=(root/'pairs.json').as_posix(),
            commercial_blockers=['version_specific_contract', 'final_event_availability', 'prospective_validation'])
        write_json(root/'result.json', result)
        return result
    finally:
        if owned:
            http.close()


def _event_matches(payload, event, books):
    if (payload['id'] != event['id'] or payload['sport_key'] != event['sport_key']
            or payload['home_team'] != event['home_team'] or payload['away_team'] != event['away_team']):
        raise ValueError('event mismatch')
    returned = [b['key'] for b in payload.get('bookmakers', [])]
    if len(returned) != len(set(returned)) or any(book not in books for book in returned):
        raise ValueError('unexpected bookmaker version')


def attach_official_identities(pairs, roster, as_of=None):
    """Unique full-name identities only; roster membership never implies availability."""
    result = []
    for pair in pairs:
        candidates = [row for row in roster if name_key(row['name']) == name_key(pair['provider_player_name'])
            and (row.get('official_roster_listing_verified') is True or row.get('official_profile_identity_verified') is True)
            and type(row.get('nba_player_id')) is int and row['nba_player_id'] > 0
            and utc(row['first_received_at_utc']) <= utc(as_of or pair['first_received_at_utc'])]
        ids = {row['nba_player_id'] for row in candidates}
        value = dict(pair)
        if len(ids) == 1:
            proof = next(row for row in candidates if row['nba_player_id'] == next(iter(ids)))
            value.update(nba_player_id=proof['nba_player_id'], identity_verified=True,
                identity_reference='unique exact normalized full name in official roster or profile',
                identity_source_sha256=proof['source_sha256'], identity_received_at_utc=proof['first_received_at_utc'],
                identity_as_of=as_of or pair['first_received_at_utc'],
                identity_known_at_quote_receipt=utc(proof['first_received_at_utc']) <= utc(pair['first_received_at_utc']))
        else:
            value.update(identity_verified=False, identity_reason='no_unique_prior_official_full_name')
        value.update(availability_verified=False, actionable=False)
        result.append(value)
    return result
