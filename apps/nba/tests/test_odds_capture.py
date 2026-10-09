import copy
import json

import httpx
import pytest

from nba.odds_capture import BoundedOddsCapture, prop_pairs

KEY = 'unit_test_private_credential'
EVENT = 'a' * 32


def client_response(request, cost='0', remaining='10000', status=200, body=None):
    return httpx.Response(status, json=body or [], headers={
        'x-requests-last': cost, 'x-requests-used': '40', 'x-requests-remaining': remaining})


def capture(tmp_path, handler=client_response, cap=30):
    return BoundedOddsCapture(tmp_path/'capture', KEY, cap,
                              client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_reservation_survives_uncertain_timeout_and_prevents_retry(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return client_response(request)
        raise httpx.ReadTimeout('URL with secret '+KEY)
    c = capture(tmp_path, handler)
    c.request('sports.json', 'sports', {}, 0)
    assert c.request('props.json', f'sports/basketball_nba/events/{EVENT}/odds', {}, 3) is None
    assert c.meta['reserved_credits'] == 3
    assert KEY not in (c.root/'manifest.json').read_text()
    with pytest.raises(ValueError, match='stopped'):
        c.request('again.json', f'sports/basketball_nba/events/{EVENT}/odds', {}, 3)
    assert len(calls) == 2


@pytest.mark.parametrize('remaining,cap,cost,expected_calls', [('10000',2,3,1), ('1001',30,3,1), ('10',30,3,1)])
def test_budget_and_shared_account_floor_stop_before_network(tmp_path, remaining, cap, cost, expected_calls):
    calls=[]
    def handler(request):
        calls.append(request)
        return client_response(request, remaining=remaining)
    c=capture(tmp_path,handler,cap)
    c.request('sports.json','sports',{},0)
    assert c.request('props.json',f'sports/basketball_nba/events/{EVENT}/odds',{},cost) is None
    assert len(calls)==expected_calls


def test_missing_quota_preserves_reserved_cost(tmp_path):
    calls=[]
    def handler(request):
        calls.append(request)
        return client_response(request) if len(calls)==1 else httpx.Response(200,json={})
    c=capture(tmp_path,handler)
    c.request('sports.json','sports',{},0)
    c.request('props.json',f'sports/basketball_nba/events/{EVENT}/odds',{},3)
    assert c.meta['reserved_credits']==3 and c.meta['stopped']
    assert len(c.meta['files'])==2


def test_no_paid_call_without_initial_account_quota(tmp_path):
    c=capture(tmp_path,lambda r:pytest.fail('network not allowed'))
    assert c.request('props.json',f'sports/basketball_nba/events/{EVENT}/odds',{},3) is None


@pytest.mark.parametrize('name,path,params', [('../escape.json','sports',{}),('safe.json','https://evil.test',{}),
    ('safe.json','sports',{'apiKey':KEY})])
def test_unsafe_request_rejected_without_network(tmp_path,name,path,params):
    c=capture(tmp_path,lambda r:pytest.fail('network not allowed'))
    with pytest.raises(ValueError):c.request(name,path,params,0)


def test_credential_echo_is_not_written(tmp_path):
    c=capture(tmp_path,lambda r:client_response(r,body={'credential':KEY}))
    assert c.request('sports.json','sports',{},0) is None
    assert not (c.root/'sports.json').exists()
    assert KEY not in (c.root/'manifest.json').read_text()


@pytest.mark.parametrize('status,cost',[(429,'0'),(302,'0'),(200,'4')])
def test_denial_redirect_and_unexpected_charge_stop(tmp_path,status,cost):
    calls=[]
    def handler(request):
        calls.append(request)
        return client_response(request) if len(calls)==1 else client_response(request,status=status,cost=cost)
    c=capture(tmp_path,handler)
    c.request('sports.json','sports',{},0)
    assert c.request('props.json',f'sports/basketball_nba/events/{EVENT}/odds',{},3) is None
    assert c.meta['stopped'] and len(calls)==2 and c.meta['charged_credits']==int(cost)


def fixture():
    expected=dict(odds_api_event_id=EVENT,home_team='Home',away_team='Away',scheduled_utc='2025-10-21T23:00:00Z')
    market=dict(key='player_points',last_update='2025-10-21T21:58:00Z',outcomes=[
        dict(name=s,description='Player',point=10.5,price=1.9) for s in ['Over','Under']])
    payload=dict(timestamp='2025-10-21T22:00:00Z',data=dict(id=EVENT,home_team='Home',away_team='Away',
        commence_time='2025-10-21T23:00:00Z',bookmakers=[dict(key='book',last_update='2025-10-21T21:58:00Z',markets=[market])]))
    receipt=dict(first_received_at_utc='2026-10-08T22:00:00Z',sha256='b'*64)
    return payload,receipt,expected


def test_historical_pair_preserves_new_receipt_and_unknown_contract():
    payload,receipt,expected=fixture()
    pairs,rejected=prop_pairs(payload,receipt,expected,'2025-10-21T22:00:00Z')
    assert len(pairs)==1 and not rejected
    assert pairs[0]['first_received_at_utc'].startswith('2026-')
    assert not pairs[0]['actionable'] and not pairs[0]['rules_verified']
    assert not pairs[0]['original_historical_receipt_known']


@pytest.mark.parametrize('issue',['future','one_side','duplicate','bad_price'])
def test_quarantine_instead_of_inventing_pair(issue):
    payload,receipt,expected=fixture();market=payload['data']['bookmakers'][0]['markets'][0]
    if issue=='future':market['last_update']='2025-10-21T22:01:00Z'
    if issue=='one_side':market['outcomes'].pop()
    if issue=='duplicate':market['outcomes'].append(copy.deepcopy(market['outcomes'][0]))
    if issue=='bad_price':market['outcomes'][0]['price']=True
    pairs,rejected=prop_pairs(payload,receipt,expected,'2025-10-21T22:00:00Z')
    assert not pairs and rejected


def test_wrong_event_and_post_tipoff_rejected():
    payload,receipt,expected=fixture();expected['odds_api_event_id']='wrong'
    with pytest.raises(ValueError,match='identity'):prop_pairs(payload,receipt,expected,'2025-10-21T22:00:00Z')
    payload,receipt,expected=fixture()
    with pytest.raises(ValueError,match='chronology'):prop_pairs(payload,receipt,expected,'2025-10-21T23:00:00Z')


def test_current_receipt_cannot_be_backdated():
    payload,receipt,expected=fixture()
    with pytest.raises(ValueError,match='received after'):
        prop_pairs(payload['data'],receipt,expected,'2025-10-21T22:00:00Z',historical=False)


def test_current_market_clock_valid_without_optional_book_clock():
    payload,receipt,expected=fixture()
    del payload['data']['bookmakers'][0]['last_update']
    receipt['first_received_at_utc']='2025-10-21T22:00:00Z'
    pairs,rejected=prop_pairs(payload['data'],receipt,expected,receipt['first_received_at_utc'],historical=False)
    assert len(pairs)==1 and not rejected
    assert pairs[0]['book_updated_at_utc'] is None
    assert pairs[0]['source_updated_at_utc']=='2025-10-21T21:58:00+00:00'


def test_historical_missing_book_clock_remains_quarantined():
    payload,receipt,expected=fixture()
    del payload['data']['bookmakers'][0]['last_update']
    pairs,rejected=prop_pairs(payload,receipt,expected,'2025-10-21T22:00:00Z')
    assert not pairs and rejected[0]['reason']=='missing_historical_book_clock'


def test_historical_date_is_normalized_before_transmission(tmp_path):
    def handler(request):
        assert request.url.params['date']=='2025-10-21T22:00:00Z'
        return client_response(request)
    c=capture(tmp_path,handler)
    c.request('events.json','historical/sports/basketball_nba/events',{'date':'2025-10-21T17:00:00-05:00'},0)
    assert c.meta['files'][0]['parameters_without_credentials']['date']=='2025-10-21T22:00:00Z'
