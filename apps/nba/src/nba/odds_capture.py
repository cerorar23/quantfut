"""Finite NBA odds acquisition with persistent reservations and no automatic retry."""
from collections import defaultdict
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import re

import httpx

from .audit import digest, write_json
from .context import utc

MARKETS = {'player_points', 'player_rebounds', 'player_assists'}


class BoundedOddsCapture:
    def __init__(self, root, key, cap, client=None, account_floor=1000, fraction=.10):
        if not key or isinstance(cap, bool) or not isinstance(cap, int) or not 1 <= cap <= 250:
            raise ValueError('key and bounded incremental credit cap required')
        if not 0 < fraction <= .10 or account_floor < 0:
            raise ValueError('conservative shared-account reserve required')
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.key, self.cap = key, cap
        self.floor, self.fraction = account_floor, fraction
        self.client = client or httpx.Client(timeout=25, follow_redirects=False)
        self.meta = dict(cap=cap, charged_credits=0, reserved_credits=0, files=[], errors=[],
                         stopped=False, initial_account_remaining=None, latest_account_remaining=None,
                         effective_credit_cap=None, automatic_retries=False, actionable=False)
        self.save()

    def save(self):
        write_json(self.root / 'manifest.json', self.meta)

    def stop(self, reason):
        self.meta['stopped'] = True
        self.meta['errors'].append(dict(reason=reason, recorded_at_utc=datetime.now(UTC).isoformat()))
        self.save()

    def request_selected(self, name, event_id, *, sport='basketball_nba', kind='markets', markets=None, date=None):
        """Use the selected European versions within this capture's existing credit budget."""
        from .odds_sources import selected_request
        spec = selected_request(event_id, sport=sport, kind=kind, markets=markets, date=date)
        return self.request(name, spec['path'], spec['parameters'], spec['max_cost'])

    def request(self, name, path, parameters, max_cost):
        if self.meta['stopped']:
            raise ValueError('capture stopped; no automatic resume')
        if (Path(name).name != name or not name.endswith('.json') or (self.root / name).exists()
                or not re.fullmatch(r'(?:historical/)?sports(?:/basketball_nba(?:_preseason)?/events(?:/[a-f0-9]{32}/(?:odds|markets))?)?', path)):
            raise ValueError('unsafe or repeated request')
        if any(re.search(r'key|token|secret|password', k, re.I) for k in parameters):
            raise ValueError('credentials forbidden in archived parameters')
        parameters = dict(parameters)
        if 'date' in parameters:
            parameters['date'] = utc(parameters['date']).strftime('%Y-%m-%dT%H:%M:%SZ')
        if isinstance(max_cost, bool) or not isinstance(max_cost, int) or not 0 <= max_cost <= 30:
            raise ValueError('bounded per-request reservation required')
        if max_cost:
            limit = self.meta['effective_credit_cap']
            remaining = self.meta['latest_account_remaining']
            if (limit is None or self.meta['charged_credits'] + self.meta['reserved_credits'] + max_cost > limit
                    or remaining is None or remaining - max_cost < self.floor):
                self.stop('budget_or_shared_account_reserve_insufficient')
                return None
        self.meta['reserved_credits'] += max_cost
        self.save()  # A crash/timeout retains the reservation; no network retry.
        requested = datetime.now(UTC).isoformat()
        url = 'https://api.the-odds-api.com/v4/' + path
        try:
            with self.client.stream('GET', url, params=dict(parameters, apiKey=self.key)) as response:
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 8_000_000:
                        raise ValueError('response_too_large')
                if self.key.encode() in body:
                    raise ValueError('credential_echo_rejected')
                received = datetime.now(UTC).isoformat()
                target = self.root / name
                with target.open('xb') as stream:
                    stream.write(body)
                quota = {k: response.headers.get(k) for k in
                         ('x-requests-last', 'x-requests-used', 'x-requests-remaining')}
                entry = dict(name=name, url_without_credentials=url, parameters_without_credentials=parameters,
                             http_status=response.status_code, bytes=len(body), sha256=digest(target),
                             requested_at_utc=requested, first_received_at_utc=received,
                             quota_headers=quota, original_historical_receipt_known=False)
                self.meta['files'].append(entry)
                valid = all(v is not None and v.isdecimal() for v in quota.values())
                if not valid:
                    self.stop('quota_unknown_reservation_retained')
                    return None
                cost, remaining = int(quota['x-requests-last']), int(quota['x-requests-remaining'])
                self.meta['reserved_credits'] -= max_cost
                self.meta['charged_credits'] += cost
                self.meta['latest_account_remaining'] = remaining
                if self.meta['initial_account_remaining'] is None:
                    self.meta['initial_account_remaining'] = remaining
                    self.meta['effective_credit_cap'] = max(0, min(self.cap, int(remaining * self.fraction), remaining - self.floor))
                self.save()
                if response.status_code != 200 or cost > max_cost:
                    self.stop('http_failure_or_unexpected_quota_cost')
                    return None
                try:
                    return json.loads(body)
                except (ValueError, UnicodeDecodeError):
                    self.stop('invalid_json')
                    return None
        except (httpx.HTTPError, ValueError) as error:
            self.stop(type(error).__name__)  # Never persist exception text containing a request URL/key.
            return None


def prop_pairs(payload, receipt, expected, decision, historical=True):
    """Strict price candidates; receipts and contract/availability evidence remain distinct."""
    cutoff = utc(decision)
    body = payload['data'] if historical else payload
    snapshot = utc(payload['timestamp']) if historical else cutoff
    if (body['id'] != expected['odds_api_event_id'] or body['home_team'] != expected['home_team']
            or body['away_team'] != expected['away_team']):
        raise ValueError('event identity mismatch')
    tip = utc(body['commence_time'])
    if not snapshot <= cutoff < tip or cutoff >= utc(expected['scheduled_utc']):
        raise ValueError('snapshot/cutoff/tipoff chronology mismatch')
    utc(receipt['first_received_at_utc'])
    if not historical and utc(receipt['first_received_at_utc']) > cutoff:
        raise ValueError('current quote received after cutoff')
    pairs, rejected = [], []
    seen_books = set()
    for book in body.get('bookmakers', []):
        if book['key'] in seen_books:
            raise ValueError('duplicate bookmaker')
        seen_books.add(book['key'])
        for market in book.get('markets', []):
            groups = defaultdict(dict)
            try:
                if market['key'] not in MARKETS:
                    raise ValueError('unsupported_market')
                update = utc(market['last_update'])
                book_clock = book.get('last_update')
                if historical and book_clock is None:
                    raise ValueError('missing_historical_book_clock')
                if update > snapshot or (book_clock is not None and utc(book_clock) > cutoff):
                    raise ValueError('future_market_or_book_update')
                for outcome in market.get('outcomes', []):
                    player, line = outcome['description'], outcome['point']
                    side, price = outcome['name'], outcome['price']
                    if (not isinstance(player, str) or not player.strip() or side not in {'Over', 'Under'}
                            or isinstance(line, bool) or not isinstance(line, (int, float)) or not math.isfinite(line)
                            or line < 0 or line * 2 != round(line * 2)
                            or isinstance(price, bool) or not isinstance(price, (int, float))
                            or not math.isfinite(price) or not 1 < price <= 1000):
                        raise ValueError('invalid_price_player_or_line')
                    group = groups[(player, line)]
                    if side in group:
                        raise ValueError('duplicate_side')
                    group[side] = price
                for (player, line), sides in groups.items():
                    if set(sides) != {'Over', 'Under'}:
                        rejected.append(dict(book=book['key'], market=market['key'], player=player, reason='missing_side'))
                        continue
                    pairs.append(dict(book=book['key'], market=market['key'], provider_player_name=player,
                        line=line, over_decimal=sides['Over'], under_decimal=sides['Under'],
                        event_id=body['id'], nba_game_id=expected.get('nba_game_id'), nba_player_id=None,
                        requested_decision_utc=decision, snapshot_timestamp_utc=snapshot.isoformat(),
                        source_updated_at_utc=update.isoformat(), first_received_at_utc=receipt['first_received_at_utc'],
                        book_updated_at_utc=book_clock,
                        raw_sha256=receipt['sha256'], snapshot_age_seconds=(cutoff-snapshot).total_seconds(),
                        market_age_at_cut_seconds=(cutoff-update).total_seconds(), identity_verified=False,
                        period_verified=False, jurisdiction_verified=False, rules_verified=False,
                        availability_verified=False, original_historical_receipt_known=False, actionable=False))
            except (KeyError, TypeError, ValueError) as error:
                rejected.append(dict(book=book['key'], market=market.get('key'), reason=str(error)))
    return pairs, rejected
