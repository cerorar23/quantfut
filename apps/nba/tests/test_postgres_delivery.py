"""Opt-in real Postgres tests: never use the football DATABASE_URL."""
from datetime import UTC,datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
import os

import pytest

pytest.importorskip('psycopg')
from nba import postgres_delivery as pg


@pytest.fixture
def box():
    dsn=os.environ.get('NBA_TEST_POSTGRES_DSN')
    if not dsn:pytest.skip('explicit isolated NBA Postgres test DSN absent')
    return pg.PostgresOutbox(dsn)


def queued(box,ttl=300):
    now=datetime.now(UTC).isoformat()
    return now,box.queue_test(now,ttl)


def test_shared_or_default_database_disallowed():
    with pytest.raises(ValueError):pg.connect('dbname=quantfut')
    with pytest.raises(ValueError):pg.connect('')


def test_dedup_and_preview(box):
    now,identifier=queued(box)
    count=box.ledger.verify()['events']
    assert box.queue_test(now)==identifier and box.ledger.verify()['events']==count
    assert box.dispatch_test(identifier,now)['state']=='dry_run'


@pytest.mark.parametrize('statement',[
    'UPDATE nba_delivery.events SET kind=kind',
    'DELETE FROM nba_delivery.events',
    'TRUNCATE nba_delivery.events',
    "UPDATE nba_delivery.messages SET payload='{}'",
    'DELETE FROM nba_delivery.messages',
    'TRUNCATE nba_delivery.messages',
])
def test_worker_cannot_mutate_evidence(box,statement):
    queued(box)
    import psycopg
    with pytest.raises(psycopg.Error):
        with pg.connect(box._dsn) as db:db.execute(statement)
    box.ledger.verify()


def test_seal_and_queue_rollback_together(box,monkeypatch):
    before=box.ledger.verify()
    original=pg.append_event
    def fail(db,kind,payload):
        original(db,kind,payload)
        raise OSError('synthetic failure after ledger insert')
    monkeypatch.setattr(pg,'append_event',fail)
    with pytest.raises(OSError):queued(box)
    assert box.ledger.verify()==before


def test_claim_and_intent_rollback_together(box,monkeypatch):
    now,identifier=queued(box)
    before=box.ledger.verify()
    original=pg.append_event
    def fail(db,kind,payload):
        result=original(db,kind,payload)
        if kind=='notification_send_attempt':raise OSError('synthetic claim rollback')
        return result
    monkeypatch.setattr(pg,'append_event',fail)
    with pytest.raises(OSError):box.dispatch_test(identifier,now,lambda _:pytest.fail('rolled back send'),False)
    assert box.ledger.verify()==before
    with pg.connect(box._dsn) as db:
        assert db.execute('SELECT state FROM nba_delivery.messages WHERE id=%s',(identifier,)).fetchone()[0]=='queued'


@pytest.mark.parametrize('state',['sent','rejected','unknown'])
def test_terminal_states_never_retry(box,state):
    now,identifier=queued(box);calls=[]
    def sender(text):
        calls.append(text)
        return dict(state=state,error_code=429 if state=='rejected' else None)
    box.dispatch_test(identifier,now,sender,False)
    restarted=pg.PostgresOutbox(box._dsn)
    assert not restarted.dispatch_test(identifier,now,sender,False)['send_attempted']
    assert len(calls)==1


def test_concurrent_claims_one_transport(box):
    now,identifier=queued(box);calls=[]
    def sender(text):calls.append(text);return dict(state='sent')
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:pg.PostgresOutbox(box._dsn).dispatch_test(identifier,now,sender,False),range(4)))
    assert len(calls)==1 and sum(r.get('send_attempted') is False for r in results)==3
    box.ledger.verify()


def test_committed_claim_visible_during_send(box):
    now,identifier=queued(box)
    def sender(_):
        with pg.connect(box._dsn) as db:
            assert db.execute('SELECT state FROM nba_delivery.messages WHERE id=%s',(identifier,)).fetchone()[0]=='sending'
            assert db.execute("SELECT count(*) FROM nba_delivery.events WHERE kind='notification_send_attempt' AND payload::jsonb->>'id'=%s",(identifier,)).fetchone()[0]==1
        return dict(state='sent')
    box.dispatch_test(identifier,now,sender,False)


def test_crash_claim_only_recovered_after_expiry(box):
    now,identifier=queued(box,30)
    clock=[datetime.fromisoformat(now)];box.clock=lambda:clock[0]
    class WorkerCrash(BaseException):pass
    def crash(_):raise WorkerCrash()
    with pytest.raises(WorkerCrash):box.dispatch_test(identifier,now,crash,False)
    assert identifier not in box.recover_expired_claims()
    clock[0]+=timedelta(seconds=31)
    assert identifier in box.recover_expired_claims()
    assert identifier not in box.recover_expired_claims()
    assert not box.dispatch_test(identifier,now,lambda _:pytest.fail('duplicate'),False)['send_attempted']


def test_expiry_after_commit_blocks_transport(box):
    now,identifier=queued(box,30)
    ticks=iter([datetime.fromisoformat(now),datetime.fromisoformat(now)+timedelta(seconds=30)])
    box.clock=lambda:next(ticks)
    assert box.dispatch_test(identifier,now,lambda _:pytest.fail('expired send'),False)['reason']=='expired_before_transport'


def test_failed_result_transaction_leaves_uncertain_claim(box,monkeypatch):
    now,identifier=queued(box);calls=[];before=box.ledger.verify()['events']
    original=pg.append_event
    def fail(db,kind,payload):
        if kind=='notification_send_result':raise OSError('synthetic result ledger failure')
        return original(db,kind,payload)
    monkeypatch.setattr(pg,'append_event',fail)
    def sender(text):calls.append(text);return dict(state='sent')
    with pytest.raises(OSError):box.dispatch_test(identifier,now,sender,False)
    assert box.ledger.verify()['events']==before+1
    restart=pg.PostgresOutbox(box._dsn)
    assert restart.dispatch_test(identifier,now,sender,False)['state']=='sending'
    assert len(calls)==1
