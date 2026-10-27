import hashlib
import json
from datetime import UTC, datetime
from fastapi import FastAPI
from fastapi.testclient import TestClient
from qf.api import web, tenis_publico as tp

NOW=datetime(2026,10,27,12,tzinfo=UTC)

def sealed(tmp_path, **change):
    folder=tmp_path/'predictions';folder.mkdir(exist_ok=True)
    v=dict(schema='tennis-intake-sealed-v1',event_key='1',circuit='ATP',tournament='Paris',rules={'surface':'Hard'},
           provider_start='2026-10-27T14:00:00Z',sealed_at='2026-10-27T11:00:00Z',
           forecast={'players':['A','B'],'winner':{'final_winner':.7,'private_parameter':'DO_NOT_PUBLISH'},'serve':{'internal':123},
                     'markets':[{'contract':{'kind':'games_total','selection':'over','line':22},'probabilities':{'win':.6,'push':.1}}]})
    v.update(change);v['payload_sha256']=tp._checksum(v)
    (folder/'1.json').write_text(json.dumps(v),encoding='utf-8')
    return folder/'1.json'

def test_only_public_projection_of_verified_seal(tmp_path):
    sealed(tmp_path);data=tp.projection(tmp_path,NOW)
    assert data['state']=='ok'
    e=data['events'][0];assert e['home']=='A' and e['markets'][0]['probability']==.7
    assert e['markets'][0]['price'] is None
    assert e['markets'][1]['push_probability']==.1
    assert 'DO_NOT_PUBLISH' not in json.dumps(data) and 'serve' not in e

def test_modified_or_late_forecasts_are_never_published(tmp_path):
    p=sealed(tmp_path);v=json.loads(p.read_text());v['forecast']['winner']['final_winner']=.99;p.write_text(json.dumps(v))
    assert tp.projection(tmp_path,NOW)['events']==[]
    sealed(tmp_path,sealed_at='2026-10-27T14:01:00Z')
    assert tp.projection(tmp_path,NOW)['events']==[]

def test_missing_source_is_unavailable_not_fake(tmp_path):
    assert tp.projection(tmp_path,NOW)['state']=='unavailable'
    (tmp_path/'predictions').mkdir();assert tp.projection(tmp_path,NOW)['events']==[]

def test_future_seal_and_invalid_probability_are_rejected(tmp_path):
    sealed(tmp_path,sealed_at='2026-10-27T13:00:00Z');assert tp.projection(tmp_path,NOW)['events']==[]
    sealed(tmp_path,forecast={'players':['A','B'],'winner':{'final_winner':None}});assert tp.projection(tmp_path,NOW)['events']==[]

def test_result_requires_original_receipt_hash_and_preserves_loss(tmp_path):
    sealed(tmp_path)
    folder=tmp_path/'fixtures'/'capture';folder.mkdir(parents=True)
    body=json.dumps({'result':[{'event_key':'1','event_status':'Finished','event_winner':'Second Player','event_final_result':'0 - 2'}]}).encode()
    (folder/'response.json').write_bytes(body)
    receipt={'method':'get_fixtures','http_status':200,'sha256':hashlib.sha256(body).hexdigest(),'received_at':'2026-10-27T16:00:00Z'}
    (folder/'receipt.json').write_text(json.dumps(receipt))
    data=tp.projection(tmp_path,datetime(2026,10,27,17,tzinfo=UTC));assert data['events'][0]['markets'][0]['outcome']=='loss'
    (folder/'response.json').write_bytes(body+b' ')
    assert tp.projection(tmp_path,datetime(2026,10,27,17,tzinfo=UTC))['events'][0]['markets'][0]['outcome'] is None

def test_public_endpoint_does_not_expose_arbitrary_paths(monkeypatch,tmp_path):
    monkeypatch.setenv('QF_TENNIS_PUBLIC_FEED',str(tmp_path/'absent.json'))
    app=FastAPI();app.include_router(web.router);client=TestClient(app)
    response=client.get('/web/deportes/tenis?path=/etc/passwd')
    assert response.status_code==200 and response.json()['state']=='unavailable'
    assert response.headers['cache-control']=='no-store'
    for path in ['/sports-data.js','/ergonomic-views.js']:
        assert client.get(path).status_code==200

def test_api_reads_only_public_feed_and_discards_unknown_fields(tmp_path):
    sealed(tmp_path);data=tp.projection(tmp_path,NOW)
    data['private_model']='SECRET';data['events'][0]['private_model']='SECRET'
    data['events'][0]['markets'][0]['private_model']='SECRET'
    path=tmp_path/'public.json';path.write_text(json.dumps(data))
    clean=tp.read_public_feed(path,NOW)
    assert len(clean['events'])==1 and 'SECRET' not in json.dumps(clean)
    assert tp.read_public_feed(path,datetime(2026,10,27,16,tzinfo=UTC))['state']=='stale'
