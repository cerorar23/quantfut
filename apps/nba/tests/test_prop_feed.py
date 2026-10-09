from datetime import UTC, datetime, timedelta
import json

import httpx
import pytest

from nba.prop_feed import attach_official_identities, capture_props, future_events

NOW = datetime.now(UTC)
TIP = (NOW+timedelta(hours=2)).isoformat()
UPDATE = (NOW-timedelta(seconds=10)).isoformat()
EVENT = 'a'*32


def event(identifier=EVENT, time=TIP, sport='basketball_nba'):
    return dict(id=identifier, sport_key=sport, commence_time=time, home_team='Home', away_team='Away')


def handler(calls, mode='normal'):
    def respond(request):
        calls.append(request)
        route = request.url.path
        cost = 0
        if route.endswith('/sports'):
            body = []
        elif route.endswith('/events'):
            body = [] if 'preseason' in route else [event(), event('b'*32, '2026-10-08T20:00:00Z')]
        elif route.endswith('/markets'):
            cost = 1
            body = dict(event(), bookmakers=[dict(key='fanduel', markets=[dict(key='player_points')])])
        else:
            cost = 3
            markets = [dict(key=market, last_update=UPDATE, outcomes=[
                dict(name=side, description='Real Player', point=10.5, price=1.9) for side in ['Over','Under']])
                for market in ['player_points','player_rebounds','player_assists']]
            body = dict(event(), bookmakers=[dict(key='fanduel', markets=markets)])
            if mode == 'wrong_book': body['bookmakers'][0]['key']='codere_it'
            if mode == 'empty': body['bookmakers']=[]
            if mode == 'timeout': raise httpx.ReadTimeout('credential-bearing URL must not be logged')
        return httpx.Response(200, json=body, headers={'x-requests-last':str(cost),
            'x-requests-used':'100', 'x-requests-remaining':'10000'})
    return respond


def test_real_pairs_exported_without_false_operational_flags(tmp_path):
    calls=[]
    with httpx.Client(transport=httpx.MockTransport(handler(calls))) as client:
        result=capture_props(tmp_path/'feed','test_only_key',4,client=client,clock=lambda:NOW)
    assert result['capture_status']=='functional' and result['pairs']==3
    assert result['credits_consumed']==4 and not result['production_ready']
    pairs=json.loads((tmp_path/'feed/pairs.json').read_bytes())
    assert all(p['data_ready'] and not p['availability_verified'] and not p['actionable'] for p in pairs)
    assert len(calls)==5
    assert all('/'+('b'*32)+'/' not in str(call.url) for call in calls)
    assert all(len(call.url.params['bookmakers'].split(','))==10 and 'regions' not in call.url.params for call in calls[-2:])
    assert 'test_only_key' not in (tmp_path/'feed/raw/manifest.json').read_text()


def test_insufficient_budget_stops_before_prop_request(tmp_path):
    calls=[]
    with httpx.Client(transport=httpx.MockTransport(handler(calls))) as client:
        result=capture_props(tmp_path/'feed','test_only_key',3,client=client,clock=lambda:NOW)
    assert result['stopped'] and result['pairs']==0 and len(calls)==4


def test_regular_only_never_queries_preseason_catalog(tmp_path):
    calls=[]
    with httpx.Client(transport=httpx.MockTransport(handler(calls))) as client:
        result=capture_props(tmp_path/'feed','test_only_key',4,client=client,clock=lambda:NOW,regular_only=True)
    assert result['pairs']==3 and len(calls)==4
    assert all('preseason' not in str(call.url) for call in calls)


@pytest.mark.parametrize('mode',['empty','wrong_book','timeout'])
def test_empty_wrong_source_and_uncertain_failure_do_not_fabricate_pairs(tmp_path,mode):
    calls=[]
    with httpx.Client(transport=httpx.MockTransport(handler(calls,mode))) as client:
        result=capture_props(tmp_path/'feed','test_only_key',4,client=client,clock=lambda:NOW)
    assert result['pairs']==0 and not result['production_ready'] and len(calls)==5
    if mode=='timeout': assert result['credits_reserved']==3 and result['stopped']


def test_balanced_selection_is_future_and_timezone_aware():
    catalog=[event('b'*32,'2026-10-08T21:00:00Z'),event(),event('c'*32,sport='basketball_nba_preseason')]
    chosen=future_events(catalog,NOW,8)
    assert [row['id'] for row in chosen]==['c'*32,EVENT]
    with pytest.raises(ValueError): future_events([event(),event()],NOW,8)


def test_identity_requires_unique_prior_evidence_and_never_health():
    pair=dict(provider_player_name='Real Player',first_received_at_utc='2026-10-08T23:00:00Z',actionable=False)
    proof=dict(name='Real Player',nba_player_id=1,official_roster_listing_verified=True,
        first_received_at_utc='2026-10-08T22:00:00Z',source_sha256='a'*64)
    identified=attach_official_identities([pair],[proof])[0]
    assert identified['nba_player_id']==1 and identified['identity_verified'] and not identified['availability_verified']
    assert not attach_official_identities([pair],[dict(proof,first_received_at_utc='2026-10-09T01:00:00Z')])[0]['identity_verified']
    assert not attach_official_identities([pair],[proof,dict(proof,nba_player_id=2)])[0]['identity_verified']
    later=dict(proof,first_received_at_utc='2026-10-09T01:00:00Z')
    enriched=attach_official_identities([pair],[later],as_of='2026-10-09T02:00:00Z')[0]
    assert enriched['identity_verified'] and not enriched['identity_known_at_quote_receipt']
