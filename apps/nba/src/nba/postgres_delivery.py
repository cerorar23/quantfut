"""Explicit isolated Postgres backend for NBA operational tests, never picks."""
from contextlib import contextmanager
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import time

import psycopg
from psycopg.conninfo import conninfo_to_dict

from .audit import canonical
from .context import utc
from .delivery import Outbox

LOCK_ID = 74754154


def connect(dsn):
    if not conninfo_to_dict(dsn).get('dbname', '').startswith('nba_'):
        raise ValueError('explicit isolated nba_* database required')
    return psycopg.connect(dsn, connect_timeout=5, options='-c lock_timeout=5000 -c statement_timeout=10000')


def migrate(dsn):
    with connect(dsn) as db:
        db.execute((Path(__file__).parent/'sql/001_delivery.sql').read_text(encoding='utf-8'))


@contextmanager
def locked(dsn):
    with connect(dsn) as db:
        db.execute('SELECT pg_advisory_xact_lock(%s)', (LOCK_ID,))
        yield db


def append_event(db, kind, payload):
    last = db.execute('SELECT seq,event_hash FROM nba_delivery.events ORDER BY seq DESC LIMIT 1').fetchone()
    seq, previous = (last[0]+1,last[1]) if last else (1,'0'*64)
    received = db.execute('SELECT clock_timestamp()').fetchone()[0].astimezone(UTC).isoformat()
    event = dict(seq=seq,received_at=received,kind=kind,payload=canonical(payload),previous_hash=previous)
    raw = canonical(event)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    db.execute('INSERT INTO nba_delivery.events VALUES (%s,%s,%s,%s,%s,%s,%s)',
               (seq,received,kind,event['payload'],previous,hashed,raw))
    return hashed


class PostgresLedger:
    def __init__(self, dsn):
        self._dsn = dsn

    def append(self, kind, payload):
        with locked(self._dsn) as db:
            return append_event(db,kind,payload)

    def verify(self):
        with connect(self._dsn) as db:
            rows = db.execute('SELECT seq,received_at,kind,payload,previous_hash,event_hash,canonical_event FROM nba_delivery.events ORDER BY seq').fetchall()
        previous = '0'*64
        for count, (seq,received,kind,payload,prev,hashed,raw) in enumerate(rows,1):
            event = dict(seq=seq,received_at=received,kind=kind,payload=payload,previous_hash=prev)
            if seq!=count or prev!=previous or canonical(event)!=raw or hashlib.sha256(raw.encode()).hexdigest()!=hashed:
                raise ValueError('NBA Postgres audit chain mismatch')
            previous = hashed
        return dict(events=len(rows),head=previous,external_anchor=False)


class PostgresOutbox(Outbox):
    """Atomic local seals/claims; commits precede every external transport call.

    The common queue_test/review_pick methods retain the operational-only scope.
    No default DSN, migration, or shared football configuration is consulted.
    """
    def __init__(self, dsn, clock=None):
        self._dsn = dsn
        self.ledger = PostgresLedger(dsn)
        self.clock = clock or (lambda: datetime.now(UTC))
        with connect(dsn) as db:
            db.execute('SELECT 1 FROM nba_delivery.messages LIMIT 0')

    def _queue(self, payload):
        raw = canonical(payload)
        identifier = hashlib.sha256(raw.encode()).hexdigest()
        with locked(self._dsn) as db:
            if not db.execute('SELECT 1 FROM nba_delivery.messages WHERE id=%s',(identifier,)).fetchone():
                sealed = append_event(db,'notification_sealed_before_queue',dict(id=identifier,payload=payload))
                db.execute("INSERT INTO nba_delivery.messages VALUES (%s,%s,%s,%s,'queued',NULL)",
                           (identifier,raw,sealed,utc(payload['expires_at_utc'])))
        return identifier

    def _finish(self, identifier, outcome, kind='notification_send_result'):
        with locked(self._dsn) as db:
            db.execute('UPDATE nba_delivery.messages SET state=%s,outcome=%s WHERE id=%s',
                       (outcome['state'],canonical(outcome),identifier))
            append_event(db,kind,dict(id=identifier,outcome=outcome))

    def dispatch_test(self, identifier, as_of, sender=None, dry_run=True):
        self.ledger.verify()
        with locked(self._dsn) as db:
            row = db.execute('SELECT payload,sealed_hash,state FROM nba_delivery.messages WHERE id=%s FOR UPDATE',(identifier,)).fetchone()
            if row is None:raise ValueError('unknown notification')
            raw,sealed,state = row
            payload = json.loads(raw)
            seal = db.execute("SELECT payload FROM nba_delivery.events WHERE event_hash=%s AND kind='notification_sealed_before_queue'",(sealed,)).fetchone()
            if hashlib.sha256(raw.encode()).hexdigest()!=identifier or not seal or json.loads(seal[0])!=dict(id=identifier,payload=payload):
                raise ValueError('NBA Postgres notification integrity mismatch')
            if state!='queued':return dict(state=state,send_attempted=False)
            now = utc(as_of) if dry_run else utc(self.clock().isoformat())
            if payload['kind']!='operational_test' or not utc(payload['created_at_utc'])<=now<utc(payload['expires_at_utc']):
                outcome = dict(state='rejected',reason='expired_or_invalid_kind',send_attempted=False)
                db.execute("UPDATE nba_delivery.messages SET state='rejected',outcome=%s WHERE id=%s",(canonical(outcome),identifier))
                append_event(db,'notification_expired',dict(id=identifier))
                return outcome
            if dry_run:
                append_event(db,'notification_local_preview',dict(id=identifier,text=payload['text']))
                return dict(state='dry_run',send_attempted=False,text=payload['text'],latency_measured=False)
            if sender is None:raise ValueError('explicit NBA sender required')
            db.execute("UPDATE nba_delivery.messages SET state='sending' WHERE id=%s",(identifier,))
            append_event(db,'notification_send_attempt',dict(id=identifier,attempted_at_utc=now.isoformat(),requested_as_of=as_of))
        # Claim and intent share one committed transaction. A lost commit ack
        # raises before this point; caller must inspect state, never blindly retry.
        now = utc(self.clock().isoformat())
        if not utc(payload['created_at_utc'])<=now<utc(payload['expires_at_utc']):
            outcome = dict(state='rejected',reason='expired_before_transport',send_attempted=False)
            self._finish(identifier,outcome,'notification_expired_before_transport')
            return outcome
        started = time.monotonic()
        try:
            outcome = sender(payload['text'])
            if outcome.get('state') not in {'sent','rejected','unknown'}:raise ValueError('invalid sender result')
        except Exception:
            outcome = dict(state='unknown',reason='ambiguous_transport_failure_no_retry')
        outcome = dict(outcome,request_duration_seconds=time.monotonic()-started,
                       response_recorded_at_utc=utc(self.clock().isoformat()).isoformat(),subscriber_receipt_verified=False)
        self._finish(identifier,outcome)
        return outcome

    def recover_expired_claims(self):
        now = utc(self.clock().isoformat())
        recovered=[]
        with locked(self._dsn) as db:
            rows=db.execute("SELECT id FROM nba_delivery.messages WHERE state='sending' AND expires_at<=%s FOR UPDATE",(now,)).fetchall()
            for (identifier,) in rows:
                outcome=dict(state='unknown',reason='expired_interrupted_claim_no_retry',recovered_at_utc=now.isoformat(),automatic_retry=False)
                db.execute("UPDATE nba_delivery.messages SET state='unknown',outcome=%s WHERE id=%s",(canonical(outcome),identifier))
                append_event(db,'notification_interrupted_recovery',dict(id=identifier,outcome=outcome))
                recovered.append(identifier)
        return recovered
