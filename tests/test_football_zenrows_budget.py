import importlib.util
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
