import importlib.util
import json
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('football_zenrows_mcp',
    Path(__file__).resolve().parents[1]/'scripts/football_zenrows_mcp.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def client(remaining=150,max_requests=10):
    obj=module.ZenRowsMCP.__new__(module.ZenRowsMCP)
    obj.reserve=100
    obj.max_requests=max_requests
    obj.calls=0
    obj.remaining_floor=None
    obj.usage_last=None
    obj.log=[]
    def rpc(method,params):
        obj.log.append(params['name'])
        if params['name']=='account_usage':
            return {'content':[{'type':'text','text':
                '{"credit_limit":5000,"usage_credits":'+str(5000-remaining)+'}'}]}
        return {'content':[{'type':'text','text':'{"events":[]}'}]}
    obj.rpc=rpc
    return obj


def test_delayed_billing_cannot_spend_reserved_credits():
    c=client()
    for _ in range(2):
        raw,receipt=c.scrape('https://api.sofascore.com/api/v1/event/1')
        assert receipt['provider_error'] is False
    assert c.remaining_floor==100
    with pytest.raises(RuntimeError,match='budget_exhausted'):
        c.scrape('https://api.sofascore.com/api/v1/event/2')
    assert c.log.count('scrape')==2


def test_request_limit_and_destination_checked_before_charged_call():
    c=client(remaining=2000,max_requests=0)
    with pytest.raises(RuntimeError,match='budget_exhausted'):
        c.scrape('https://fbref.com/en/comps/')
    with pytest.raises(ValueError,match='unapproved'):
        c.scrape('https://evil.test/')
    assert 'scrape' not in c.log


def test_automatic_requests_do_not_force_a_country_or_expensive_features():
    c=client();c.default_country=None
    original=c.rpc;arguments=[]
    def rpc(method,params):
        if params['name']=='scrape':arguments.append(params['arguments'])
        return original(method,params)
    c.rpc=rpc
    c.scrape('https://api.sofascore.com/api/v1/event/1')
    assert arguments==[{'url':'https://api.sofascore.com/api/v1/event/1','response_type':'html'}]
    c.scrape('https://api.sofascore.com/api/v1/event/2',country='DE')
    assert arguments[-1]['proxy_country']=='DE'


def test_key_cap_is_respected_even_if_account_has_more_credits():
    c=client(remaining=4000)
    def rpc(method,params):
        assert params['name']=='account_usage'
        return {'content':[{'type':'text','text':'{"credit_limit":5000,"usage_credits":1000,"api_key":{"caps":[{"remaining_credits":100}]}}'}]}
    c.rpc=rpc
    with pytest.raises(RuntimeError,match='budget_exhausted'):
        c.scrape('https://fbref.com/en/comps/')


def test_task_key_overrides_only_child_environment(tmp_path,monkeypatch):
    config={'mcpServers':{'zenrows':{'command':'npx','args':['-y','@zenrows/mcp@2.4.0'],
        'env':{'ZENROWS_API_KEY':'shared-test-secret'}}}}
    path=tmp_path/'.mcp.json';path.write_text(json.dumps(config))
    monkeypatch.setenv('ZENROWS_API_KEY','task-test-secret')
    captured=[]
    class Process:
        stdout=[]
        stderr=[]
        class Input:
            def write(self,value):pass
            def flush(self):pass
        stdin=Input()
    monkeypatch.setattr(module.subprocess,'Popen',lambda *args,**kwargs:captured.append(kwargs) or Process())
    monkeypatch.setattr(module.shutil,'which',lambda _: 'npx')
    monkeypatch.setattr(module.ZenRowsMCP,'rpc',lambda *args: {})
    c=module.ZenRowsMCP(tmp_path,default_country=None)
    assert c.secret=='task-test-secret'
    assert captured[0]['env']['ZENROWS_API_KEY']=='task-test-secret'
    assert json.loads(path.read_text())==config
