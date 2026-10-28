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


def market(kind, selection, line=None, set_number=None):
    contract={'kind':kind,'selection':selection}
    if line is not None:contract['line']=line
    if set_number:contract['set_number']=set_number
    return {'contract':contract,'probabilities':{'win':.55,'push':0.}}

def capture(tmp_path, row, received='2026-10-27T16:00:00Z', name='capture'):
    folder=tmp_path/'fixtures'/name;folder.mkdir(parents=True)
    body=json.dumps({'result':[dict(event_key='1',**row)]}).encode()
    (folder/'response.json').write_bytes(body)
    (folder/'receipt.json').write_text(json.dumps({'method':'get_fixtures','http_status':200,'sha256':hashlib.sha256(body).hexdigest(),'received_at':received}))

def sets(*pairs):
    return [{'score_first':str(a),'score_second':str(b),'score_set':str(i+1)} for i,(a,b) in enumerate(pairs)]

def outcomes(data):
    return {m['label']+' | '+m['selection']:m['outcome'] for m in data['events'][0]['markets']}

LATER=datetime(2026,10,27,18,tzinfo=UTC)

def test_every_market_is_settled_from_the_official_set_scores(tmp_path):
    forecast={'players':['A','B'],'winner':{'final_winner':.7},'markets':[
        market('games_total','over',22),market('games_total','under',22),market('games_total','over',32),
        market('sets_total','over',2.5),market('games_handicap','B',.5),market('games_handicap','A',-.5),
        market('sets_handicap','A',-1.5),market('set_winner','A',set_number=3),market('set_winner','A',set_number=2),
        market('tiebreak','yes'),market('tiebreak','no')]}
    sealed(tmp_path,forecast=forecast)
    capture(tmp_path,{'event_status':'Finished','event_winner':'First Player','event_final_result':'2 - 1','scores':sets((6,4),(3,6),(7,6))})
    got=outcomes(tp.projection(tmp_path,LATER))
    assert got['Ganador del partido | A']=='win'
    assert got['Juegos totales | Más de 22']=='win' and got['Juegos totales | Menos de 22']=='loss'
    assert got['Juegos totales | Más de 32']=='push'
    assert got['Sets totales | Más de 2.5']=='win'
    assert got['Hándicap de juegos | B 0.5']=='win' and got['Hándicap de juegos | A -0.5']=='loss'
    assert got['Hándicap de sets | A -1.5']=='loss'
    assert got['Ganador de set · set 3 | A']=='win' and got['Ganador de set · set 2 | A']=='loss'
    assert got['Tie-break | Sí']=='win' and got['Tie-break | No']=='loss'

def test_set_that_was_never_played_is_returned(tmp_path):
    sealed(tmp_path,forecast={'players':['A','B'],'winner':{'final_winner':.7},'markets':[market('set_winner','A',set_number=3),market('set_winner','B',set_number=2)]})
    capture(tmp_path,{'event_status':'Finished','event_winner':'First Player','event_final_result':'2 - 0','scores':sets((6,4),(6,3))})
    got=outcomes(tp.projection(tmp_path,LATER))
    assert got['Ganador de set · set 3 | A']=='push' and got['Ganador de set · set 2 | B']=='loss'

def test_unverifiable_score_leaves_markets_open(tmp_path):
    sealed(tmp_path)
    capture(tmp_path,{'event_status':'Finished','event_winner':'First Player','event_final_result':'2 - 0','scores':sets((6,4))})
    got=outcomes(tp.projection(tmp_path,LATER))
    assert got['Ganador del partido | A']=='win' and got['Juegos totales | Más de 22'] is None

def test_retirement_voids_what_was_not_played(tmp_path):
    forecast={'players':['A','B'],'winner':{'final_winner':.7},'markets':[
        market('games_total','over',22),market('set_winner','A',set_number=1),market('set_winner','A',set_number=2),market('tiebreak','yes')]}
    sealed(tmp_path,forecast=forecast)
    capture(tmp_path,{'event_status':'Retired','event_winner':'First Player','event_final_result':'1 - 0','scores':sets((6,4),(2,1))})
    got=outcomes(tp.projection(tmp_path,LATER))
    assert got['Ganador del partido | A']=='win' and got['Juegos totales | Más de 22']=='push'
    assert got['Ganador de set · set 1 | A']=='win' and got['Ganador de set · set 2 | A']=='push'
    assert got['Tie-break | Sí'] is None

def test_walkover_and_cancelled_are_returned_not_pending(tmp_path):
    sealed(tmp_path)
    capture(tmp_path,{'event_status':'Walk Over','event_winner':'First Player','event_final_result':'0 - 0','scores':[]})
    data=tp.projection(tmp_path,LATER)
    assert data['events'][0]['status']=='finished' and set(outcomes(data).values())=={'push'}
    for old in (tmp_path/'fixtures').iterdir():
        for f in old.iterdir():f.unlink()
        old.rmdir()
    capture(tmp_path,{'event_status':'Cancelled','event_winner':None,'event_final_result':'-','scores':[]})
    data=tp.projection(tmp_path,LATER)
    assert data['events'][0]['status']=='cancelled' and set(outcomes(data).values())=={'push'}

def test_postponed_match_shows_its_new_start_and_stays_scheduled(tmp_path):
    sealed(tmp_path)
    capture(tmp_path,{'event_status':'','event_winner':None,'event_final_result':'-','scores':[],'event_date':'2026-10-28','event_time':'14:00'})
    e=tp.projection(tmp_path,LATER)['events'][0]
    assert e['status']=='scheduled' and e['start']=='2026-10-28T14:00:00+00:00'
    assert e['sealed_at']=='2026-10-27T11:00:00Z' and all(m['outcome'] is None for m in e['markets'])

def test_match_without_a_result_after_a_day_and_a_half_is_flagged(tmp_path):
    sealed(tmp_path)
    capture(tmp_path,{'event_status':'Set 1','event_winner':None,'event_final_result':'0 - 0','scores':[],'event_date':'2026-10-27','event_time':'14:00'})
    assert tp.projection(tmp_path,datetime(2026,10,28,20,tzinfo=UTC))['events'][0]['status']=='awaiting_result'
    assert tp.projection(tmp_path,datetime(2026,10,29,6,tzinfo=UTC))['events'][0]['status']=='no_result'
