from datetime import datetime,timedelta,timezone
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

import pytest

spec=importlib.util.spec_from_file_location('operations_worker',Path(__file__).parents[1]/'ops/operations_worker.py')
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
NOW=datetime(2026,10,9,14,tzinfo=timezone.utc)


@pytest.fixture
def setup(tmp_path,monkeypatch):
    config=dict(data=str(tmp_path/'ops'),capture_health=str(tmp_path/'capture.json'),paper_health=str(tmp_path/'paper.json'),
        private_file='not-read-in-tests',daily_message_cap=20,cycle_seconds=30,paper_container='nba-paper-pilot-run67',paper_label='paper-run67')
    Path(config['capture_health']).write_text(json.dumps(dict(state='capturing',at_utc=NOW.isoformat(),optional_source_issues=[{}])))
    Path(config['paper_health']).write_text(json.dumps(dict(state='waiting',as_of=NOW.isoformat(),completed_events=0)))
    monkeypatch.setattr(worker,'validate_config',lambda config:None)
    return config


def test_same_state_restart_and_single_meaningful_transition(setup):
    calls=[]
    def sender(*args):calls.append(args[0]);return dict(state='sent',message_id=1,destination_verified=True)
    one=worker.cycle(setup,clock=lambda:NOW,sender=sender)
    two=worker.cycle(setup,clock=lambda:NOW,sender=sender)
    assert len(calls)==1 and two['last_message']==one['last_message']
    Path(setup['paper_health']).write_text(json.dumps(dict(state='waiting',as_of=NOW.isoformat(),completed_events=1)))
    worker.cycle(setup,clock=lambda:NOW,sender=sender)
    assert len(calls)==2


def test_transport_uncertainty_never_retries_and_claim_precedes_sender(setup):
    calls=[]
    def sender(*args):
        with sqlite3.connect(Path(setup['data'])/'operations.sqlite') as db:
            assert db.execute('SELECT count(*) FROM claims').fetchone()[0]==1
        calls.append(1);raise TimeoutError('secret should never appear')
    one=worker.cycle(setup,clock=lambda:NOW,sender=sender)
    worker.cycle(setup,clock=lambda:NOW,sender=sender)
    assert len(calls)==1 and one['last_message']['state']=='unknown'
    assert 'secret' not in json.dumps(one)


def test_restart_after_claim_before_ack_does_not_resend(setup):
    root=Path(setup['data']);root.mkdir()
    components=dict(capture=worker.snapshot(setup['capture_health'],NOW,1800),paper=worker.snapshot(setup['paper_health'],NOW,120))
    signature=worker.hashlib.sha256(worker.canonical(components).encode()).hexdigest()
    with worker.store(root/'operations.sqlite') as db:worker.claim(db,'telegram:1:'+signature,'telegram',NOW,20)
    result=worker.cycle(setup,clock=lambda:NOW,sender=lambda *args:pytest.fail('claimed uncertain POST retried'))
    assert result['last_message']['previous_claim'] and result['signature']==signature


def test_terminal_stops_only_owned_pilot_once(setup):
    Path(setup['paper_health']).write_text(json.dumps(dict(state='completed',as_of=NOW.isoformat(),completed_events=3)))
    stops=[]
    def stopper(name,label):stops.append((name,label));return dict(state='stopped',ownership_verified=True)
    sender=lambda *args:dict(state='sent',message_id=1)
    worker.cycle(setup,clock=lambda:NOW,sender=sender,stopper=stopper)
    worker.cycle(setup,clock=lambda:NOW,sender=sender,stopper=stopper)
    assert stops==[('nba-paper-pilot-run67','paper-run67')]
    with pytest.raises(ValueError):worker.stop_pilot('quantfut-worker-1','paper-run67')


def test_stale_future_clock_and_rollback(setup):
    assert worker.snapshot(setup['paper_health'],NOW+timedelta(seconds=121),120)['state']=='stale'
    assert worker.snapshot(setup['paper_health'],NOW-timedelta(seconds=6),120)['state']=='stale'
    worker.cycle(setup,clock=lambda:NOW,sender=lambda *args:dict(state='sent'))
    with pytest.raises(ValueError,match='rollback'):worker.cycle(setup,clock=lambda:NOW-timedelta(seconds=1))


def test_cap_blocks_new_messages_until_next_UTC_day(setup):
    root=Path(setup['data']);root.mkdir()
    with worker.store(root/'operations.sqlite') as db:
        for i in range(20):assert worker.claim(db,'old:'+str(i),'telegram',NOW,20)
    result=worker.cycle(setup,clock=lambda:NOW,sender=lambda *args:pytest.fail('daily cap'))
    assert result['signature'] is None
    calls=[]
    worker.cycle(setup,clock=lambda:NOW+timedelta(days=1),sender=lambda *args:(calls.append(1) or dict(state='sent')))
    assert calls==[1]


def test_immutable_journal_and_claims(setup):
    worker.cycle(setup,clock=lambda:NOW,sender=lambda *args:dict(state='sent'))
    with worker.store(Path(setup['data'])/'operations.sqlite') as db:
        for sql in ('DELETE FROM claims','UPDATE claims SET category=\'x\'','DELETE FROM journal','UPDATE journal SET kind=\'x\''):
            with pytest.raises(sqlite3.IntegrityError):db.execute(sql)
        assert worker.verify(db)['events']==2


def test_expired_message_does_not_read_credentials():
    result=worker.telegram('ESTADO OPERATIVO NBA\nNo bets.','nonexistent',datetime.now(timezone.utc)-timedelta(seconds=1))
    assert result==dict(state='expired',send_attempted=False)


def test_wrong_owner_label_prevents_stop(monkeypatch):
    calls=[]
    class Result:
        returncode=0
        stdout=json.dumps([dict(Config=dict(Labels={'NBA.scope':'football'}),State=dict(Running=True))])
    def run(args,**kwargs):calls.append(args);return Result()
    monkeypatch.setattr(worker.subprocess,'run',run)
    assert worker.stop_pilot('nba-paper-pilot-run67','paper-run67')['state']=='unknown'
    assert len(calls)==1 and calls[0][1]=='inspect'


def test_systemd_ready_follows_lock_and_durable_cycle(setup,monkeypatch,tmp_path):
    order=[];config_file=tmp_path/'config.json';config_file.write_text(json.dumps(setup))
    Path(setup['data']).mkdir()
    monkeypatch.setattr(sys,'argv',['worker',str(config_file)])
    monkeypatch.setenv('NOTIFY_SOCKET','@nba-readiness-test')
    monkeypatch.setitem(sys.modules,'fcntl',SimpleNamespace(LOCK_EX=1,LOCK_NB=2,flock=lambda *args:order.append('lock')))
    monkeypatch.setattr(worker,'cycle',lambda *args:order.append('durable_cycle'))
    class FakeSocket:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def connect(self,address):assert address=='\0nba-readiness-test'
        def sendall(self,body):assert body==b'READY=1';order.append('ready')
    monkeypatch.setitem(sys.modules,'socket',SimpleNamespace(AF_UNIX=1,SOCK_DGRAM=2,socket=lambda *args:FakeSocket()))
    class End(Exception):pass
    def sleep(*args):raise End()
    monkeypatch.setattr(worker.time,'sleep',sleep)
    with pytest.raises(End):worker.main()
    assert order==['lock','durable_cycle','ready']
