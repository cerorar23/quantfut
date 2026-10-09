import subprocess
from datetime import UTC,datetime,timedelta
import pytest
from nba.vps_telegram import vps_sender

def fresh_bounds():return dict(remote_minus_local_lower_seconds=0.,remote_minus_local_upper_seconds=0.,observed_at_local_utc=datetime.now(UTC).isoformat())

def expiry():return (datetime.now(UTC)+timedelta(minutes=10)).isoformat()


@pytest.mark.parametrize('bounds',[None,dict(remote_minus_local_lower_seconds=0.,remote_minus_local_upper_seconds=0.,observed_at_local_utc='2020-01-01T00:00:00Z')])
def test_missing_or_stale_clock_never_invokes_ssh(monkeypatch,bounds):
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:pytest.fail('clock rejection must precede SSH'))
    result=vps_sender(expiry(),bounds)('PRUEBA TÉCNICA NBA — test')
    assert result['state']=='rejected' and result['send_attempted'] is False


@pytest.mark.parametrize('body,state',[
    ('{"state":"sent","message_id":123,"destination_matches_authorized_chat":true}','sent'),
    ('{"state":"rejected","error_code":429}','rejected'),
    ('{"state":"unknown"}','unknown'),
    ('invalid-json','unknown'),
    ('{"state":"sent","secret":"not_allowed"}','unknown'),
    ('{"state":"sent","message_id":123,"destination_matches_authorized_chat":false}','unknown'),
])
def test_only_allowlisted_result_and_no_retry(monkeypatch,body,state):
    calls=[]
    def invoke(args,**kwargs):calls.append(args);return subprocess.CompletedProcess(args,0,body,'')
    monkeypatch.setattr(subprocess,'run',invoke)
    result=vps_sender(expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA — test')
    assert result['state']==state and len(calls)==1
    assert 'secret' not in result


def test_nonoperational_text_never_invokes_ssh(monkeypatch):
    monkeypatch.setattr(subprocess,'run',lambda *a,**k:pytest.fail('unauthorized send'))
    with pytest.raises(ValueError):vps_sender(expiry(),fresh_bounds())('pick')


def test_timeout_is_unknown_without_retry(monkeypatch):
    calls=[]
    def invoke(*a,**k):calls.append(1);raise subprocess.TimeoutExpired('ssh',25)
    monkeypatch.setattr(subprocess,'run',invoke)
    result=vps_sender(expiry(),fresh_bounds())('PRUEBA TÉCNICA NBA — test')
    assert result['state']=='unknown' and len(calls)==1


def test_remote_program_runs_with_python310_datetime(monkeypatch,tmp_path,capsys):
    import datetime,sys,types
    import urllib.request
    from nba.vps_telegram import REMOTE
    # Python3.10 exposes timezone.utc but has no module-level datetime.UTC.
    module=types.ModuleType('datetime');module.datetime=datetime.datetime;module.timezone=datetime.timezone
    monkeypatch.setitem(sys.modules,'datetime',module)
    env=tmp_path/'synthetic.env';env.write_text('TG_BOT_TOKEN=synthetic\nTG_ALERT_CHAT=-123\n')
    code=REMOTE.replace('/home/qf/quantfut/.env',str(env).replace('\\','/'))
    code=code.replace('REQUEST_JSON',repr(dict(text='READONLY_DIAGNOSTIC',expires_at_utc='2030-01-01T00:00:00Z')),1)
    exec(compile(code,'remote_program','exec'),{})
    import json
    assert json.loads(capsys.readouterr().out)['state']=='unknown'
