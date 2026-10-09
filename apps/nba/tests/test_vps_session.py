import io
import json
import math
from datetime import UTC,datetime,timedelta

import pytest

from nba.vps_session import OperationalSession, remote_program


class Process:
    def __init__(self, responses):
        self.stdin=io.StringIO()
        self.stdout=io.StringIO('\n'.join(json.dumps(r) for r in [{'ready':True},*responses])+'\n')
        self.closed=False
    def poll(self):return 0 if self.closed else None
    def terminate(self):self.closed=True
    def kill(self):self.closed=True
    def wait(self,timeout):return 0


def session(outcome,identifier='a'):
    p=Process([dict(request_id=identifier,outcome=outcome)])
    return OperationalSession(process_factory=lambda *a,**k:p),p


def fresh_bounds():return dict(remote_minus_local_lower_seconds=0.,remote_minus_local_upper_seconds=0.,observed_at_local_utc=datetime.now(UTC).isoformat())

def expiry():return (datetime.now(UTC)+timedelta(minutes=10)).isoformat()

def sent():return dict(state='sent',message_id=7,destination_matches_authorized_chat=True,remote_elapsed_seconds=.2)


@pytest.mark.parametrize('bounds',[None,dict(remote_minus_local_lower_seconds=0.,remote_minus_local_upper_seconds=0.,observed_at_local_utc='2020-01-01T00:00:00Z')])
def test_missing_or_stale_clock_never_writes_request(bounds):
    s,p=session(sent())
    try:
        result=s.sender('a',expiry(),bounds)('PRUEBA TÉCNICA NBA')
        assert result['state']=='rejected' and result['send_attempted'] is False
        assert p.stdin.getvalue()==''
        assert s.sender('a',expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA')['state']=='sent'
    finally:s.close()


def test_reuses_one_process_and_binds_request():
    p=Process([dict(request_id=str(i),outcome=sent()) for i in range(3)])
    calls=[]
    def factory(*a,**k):calls.append(a);return p
    s=OperationalSession(process_factory=factory)
    try:
        for i in range(3):
            r=s.sender(str(i),expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA')
            assert r['state']=='sent' and r['acknowledged_at_utc']
        assert len(calls)==1 and len(p.stdin.getvalue().splitlines())==3
        with pytest.raises(ValueError):s.sender('4',expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA')
    finally:s.close()


@pytest.mark.parametrize('change',[{'message_id':True},{'destination_matches_authorized_chat':False},
    {'private_token':'never expose'},{'remote_elapsed_seconds':math.nan},{'state':'queued'}])
def test_uncertain_response_poisoned_without_retry(change):
    s,p=session(dict(sent(),**change))
    try:
        r=s.sender('a',expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA')
        assert r['state']=='unknown' and 'private_token' not in r
        with pytest.raises(ValueError):s.sender('b',expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA')
        assert len(p.stdin.getvalue().splitlines())==1
    finally:s.close()


def test_response_from_other_identifier_rejected():
    s,p=session(sent(),'wrong')
    try:assert s.sender('a',expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA')['state']=='unknown'
    finally:s.close()


def test_commercial_text_never_written():
    s,p=session(sent())
    try:
        with pytest.raises(ValueError):s.sender('a',expiry(),fresh_bounds())('APUESTA')
        assert p.stdin.getvalue()==''
    finally:s.close()


def test_remote_expiry_prevents_http(monkeypatch):
    import pathlib,urllib.request
    monkeypatch.setattr(pathlib.Path,'read_text',lambda _: 'TG_BOT_TOKEN=test\nTG_ALERT_CHAT=123')
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**k:pytest.fail('expired send contacted Telegram'))
    monkeypatch.setattr('sys.stdin',io.StringIO(json.dumps(dict(request_id='old',text='PRUEBA TÉCNICA NBA',
        expires_at_utc=(datetime.now(UTC)-timedelta(seconds=1)).isoformat()))+'\n'))
    output=io.StringIO();monkeypatch.setattr('sys.stdout',output)
    exec(compile(remote_program(),'<remote>','exec'),{})
    r=json.loads(output.getvalue().splitlines()[1])
    assert r['outcome']['state']=='rejected' and r['outcome']['send_attempted'] is False


def test_timeout_closes_retry_path(monkeypatch):
    s,p=session(sent())
    def timeout():raise TimeoutError()
    monkeypatch.setattr(s,'_read',timeout)
    try:
        assert s.sender('a',expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA')['state']=='unknown'
        with pytest.raises(ValueError):s.sender('b',expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA')
        assert len(p.stdin.getvalue().splitlines())==1
    finally:s.close()
