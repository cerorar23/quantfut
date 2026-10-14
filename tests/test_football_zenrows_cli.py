import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

spec=importlib.util.spec_from_file_location('football_zenrows_cli',
    Path(__file__).resolve().parents[1]/'scripts/football_zenrows_cli.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_inflight_reservations_and_exact_cost_share_one_budget():
    b=module.CreditBudget(150,max_requests=5)
    b.acquire();b.acquire()
    with pytest.raises(RuntimeError):b.acquire()
    b.settle(1)
    assert b.remaining==124
    with pytest.raises(RuntimeError):b.acquire()
    b.settle(10);b.acquire()
    assert b.remaining==114


def test_unknown_cost_never_refunds_and_call_limit_still_applies():
    b=module.CreditBudget(500,max_requests=1)
    b.acquire()
    for cost in [None,True,-1,26,'1']:b.settle(cost)
    assert b.remaining==475
    b.settle(1)
    with pytest.raises(RuntimeError):b.acquire()


@pytest.mark.parametrize('code',['AUTH_INVALID','KEY_CREDIT_CAP_REACHED',
                               'POLICY_MAX_CREDITS_EXCEEDED'])
def test_terminal_failure_stops_remaining_calls_without_retry(tmp_path,monkeypatch,code):
    monkeypatch.setenv('ZENROWS_API_KEY','synthetic-test-secret')
    calls=[]
    def run(cmd,**kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=1,stdout=json.dumps({'ok':False,'error':{'code':code}}))
    monkeypatch.setattr(module.subprocess,'run',run)
    monkeypatch.setattr(module.shutil,'which',lambda _:'npx')
    b=module.CreditBudget(1000,max_requests=10);c=module.ZenRowsCLI(tmp_path,b)
    _,receipt=c.scrape('https://fbref.com/en/comps/')
    assert receipt['provider_error'] and b.blocked==code and receipt['error_code']==code
    with pytest.raises(RuntimeError):c.scrape('https://fbref.com/en/')
    assert len(calls)==1


def test_cli_uses_environment_key_fixed_version_no_signup_and_original_bytes(tmp_path,monkeypatch):
    monkeypatch.setenv('ZENROWS_API_KEY','synthetic-test-secret')
    calls=[]
    def run(cmd,**kwargs):
        calls.append((cmd,kwargs))
        Path(cmd[cmd.index('--out')+1]).write_bytes(b'{"rounds":[]}')
        return SimpleNamespace(returncode=0,stdout=json.dumps({'ok':True,'httpStatus':200,'costCredits':1,'runId':'test'}))
    monkeypatch.setattr(module.subprocess,'run',run)
    monkeypatch.setattr(module.shutil,'which',lambda _: 'npx')
    b=module.CreditBudget(150,max_requests=2)
    c=module.ZenRowsCLI(tmp_path,b)
    raw,receipt=c.scrape('https://www.sofascore.com/api/v1/unique-tournament/40/rounds')
    cmd,options=calls[0]
    assert 'synthetic-test-secret' not in ' '.join(cmd)
    assert '@zenrows/cli@1.5.0' in cmd and '--no-signup' in cmd and '--manual' not in cmd
    assert options['env']['ZENROWS_API_KEY']=='synthetic-test-secret'
    assert raw==b'{"rounds":[]}' and receipt['cost_credits']==1 and not receipt['provider_error']
    assert b.remaining==149
