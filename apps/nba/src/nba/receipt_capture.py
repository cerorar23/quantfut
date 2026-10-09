"""New receipts of public responses. Archives never acquire past receipt times."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request
import urllib.error

from .audit import Ledger, digest
from .context import utc


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('redirect rejected before requesting another URL')


class CaptureStore:
    def __init__(self, root):
        self.root = Path(root)
        (self.root / 'blobs').mkdir(parents=True, exist_ok=True)
        self.ledger = Ledger(self.root / 'receipts.sqlite')

    def collect_public(self, url, allowed_urls):
        """One allowlisted HTTPS GET. Receipt is recorded after the complete body."""
        parts = urlsplit(url)
        if url not in allowed_urls or parts.scheme != 'https' or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError('explicit public HTTPS URL without credentials required')
        started = datetime.now(UTC).isoformat()
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'NBA research receipt collector/1.0'})
            with urllib.request.build_opener(NoRedirect()).open(req, timeout=15) as response:
                # Never follow a redirect outside the protocol allowlist.
                if response.url != url:
                    raise ValueError('redirected response rejected')
                raw = response.read(10_000_001)
                status = response.status
                headers = {k:response.headers.get(k) for k in ('Date','Last-Modified','Content-Type')}
        except urllib.error.HTTPError as error:
            raw = error.read(10_000_001)
            status, headers = error.code, {}
        received = datetime.now(UTC).isoformat()
        if len(raw) > 10_000_000:
            raise ValueError('response exceeds capture limit')
        hashed = hashlib.sha256(raw).hexdigest()
        path = self.root / 'blobs' / hashed
        if path.exists():
            if digest(path) != hashed:
                raise ValueError('existing raw body corrupted')
        else:
            with path.open('xb') as f:
                f.write(raw)
        receipt = dict(url=url, requested_at_utc=started, first_received_at_utc=received,
            http_status=status, headers=headers, raw_sha256=hashed, raw_bytes=len(raw),
            original_historical_receipt_known=False, source_updated_at_utc=None,
            external_timestamp_authority=False, actionable=False)
        sealed = self.ledger.append('public_response_received', receipt)
        return dict(receipt, receipt_event_hash=sealed)

    def verify_receipt(self, receipt):
        self.ledger.verify()
        import sqlite3
        with sqlite3.connect(self.ledger.path) as db:
            row = db.execute("SELECT payload FROM events WHERE event_hash=? AND kind='public_response_received'",
                (receipt['receipt_event_hash'],)).fetchone()
        expected = {k:v for k,v in receipt.items() if k != 'receipt_event_hash'}
        if row is None or json.loads(row[0]) != expected or digest(self.root/'blobs'/receipt['raw_sha256']) != receipt['raw_sha256']:
            raise ValueError('receipt or body integrity mismatch')
        return expected

    def schedule_context(self, receipt):
        """Only scheduled, future NBA IDs become candidate prospective context."""
        self.verify_receipt(receipt)
        if receipt['http_status'] != 200:
            return dict(state='unavailable', events=[], actionable=False)
        body = json.loads((self.root/'blobs'/receipt['raw_sha256']).read_bytes())
        games = body['scoreboard']['games']
        received = utc(receipt['first_received_at_utc'])
        events, excluded, seen = [], [], set()
        for game in games:
            identifier = game['gameId']
            if not isinstance(identifier,str) or len(identifier)!=10 or not identifier.isdecimal() or identifier in seen:
                raise ValueError('invalid or duplicate NBA event identity')
            seen.add(identifier)
            tip = utc(game['gameTimeUTC'])
            if game['gameStatus'] != 1 or received >= tip:
                excluded.append(identifier)
                continue
            events.append(dict(event_id=identifier, tipoff_utc=tip.isoformat(),
                home_team_id=game['homeTeam']['teamId'], away_team_id=game['awayTeam']['teamId'],
                receipt_event_hash=receipt['receipt_event_hash'], original_receipt_at_utc=received.isoformat(),
                competition_verified=False, availability_verified=False, role_verified=False,
                contract_verified=False, overtime_model_verified=False, actionable=False))
        return dict(state='captured', events=events, excluded_started_or_finished=excluded,
            F7_started=False, source_updated_at_utc=None, actionable=False)


def contract_readiness(quote, receipt, rules_path):
    """List missing inputs without upgrading an operator's claim to a verified contract."""
    from .markets import validate_quote
    reasons=[]
    if quote.get('first_received_at_utc') != receipt['first_received_at_utc']:
        reasons.append('own_receipt_mismatch')
    if quote.get('raw_response_sha256') != receipt['raw_sha256']:
        reasons.append('raw_response_binding_missing')
    if not rules_path or not Path(rules_path).is_file() or digest(rules_path) != quote.get('rules_sha256'):
        reasons.append('rule_body_hash_unverified')
    if quote.get('jurisdiction') is None or quote.get('rule_applicability_evidence_sha256') is None:
        reasons.append('jurisdiction_or_rule_applicability_missing')
    try:
        validate_quote(quote,receipt['first_received_at_utc'])
    except (ValueError,KeyError,TypeError):
        reasons.append('market_contract_invalid_or_incomplete')
    return dict(state='candidate_requires_review' if not reasons else 'incomplete', reasons=reasons,
        contract_verified=False, original_historical_receipt_known=False, actionable=False)
