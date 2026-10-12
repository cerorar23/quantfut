"""Delivery quotas, redaction and feature gates; model selection is unchanged."""
import copy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from qf.api import mobile, rewards, console, panel


def row(i, prob=.8, price=1.4):
    return {'match_id':f'm{i}', 'market':'totals', 'selection':'over', 'line':1.5,
            'prob':prob,'ref_price':price,'local':'A','visitante':'B',
            'kickoff_utc':datetime.now(timezone.utc)+timedelta(days=1), 'batch_date':'2026-10-11'}


@pytest.fixture
def delivery(monkeypatch):
    flags={k:{'enabled':True,'message':'Modelo en entrenamiento'} for k in mobile.SECTIONS}
    monkeypatch.setattr(mobile,'features',lambda:flags)
    monkeypatch.setattr(mobile.alta_prob_datos,'informe_publico',lambda:{'estado':'activa','motivos':[], 'proximos':[], 'historial':{'n':0}})
    monkeypatch.setattr(mobile,'allocations',lambda rows,stream:{mobile.pick_key(p) for p in mobile.choose_free(rows,stream)})
    return flags


@pytest.mark.parametrize('n,expected',[(0,0),(1,1),(9,1),(10,1),(11,2),(20,2),(21,3)])
def test_ten_percent_rounded_up_and_best_quote(n,expected):
    rows=[row(i,price=1+i/100) for i in range(1,n+1)]
    selected=mobile.choose_free(rows,'alta_probabilidad')
    assert len(selected)==expected
    assert [r['match_id'] for r in selected]==[f'm{i}' for i in range(n,n-expected,-1)]


def test_probability_bounds_and_no_fake_quote():
    rows=[row(1,.749),row(2,.75),row(3,.90),row(4,.901),row(5,.85,None)]
    assert mobile.choose_free(rows,'alta_probabilidad')[0]['match_id']=='m3'
    assert len(mobile.choose_free([row(1,.8,None)],'alta_probabilidad'))==0


def test_ladder_uses_exact_probability_not_rounded():
    rows=[{**row(1,.79),'pick_key':'1:2','_prob_exact':.7851,'price':1.3},
          {**row(2,.79),'pick_key':'2:2','_prob_exact':.7949,'price':1.25}]
    assert mobile.choose_free(rows,'escalera')[0]['pick_key']=='2:2'


def test_anonymous_does_not_receive_vip_selection(delivery,monkeypatch):
    monkeypatch.setattr(mobile,'high_rows',lambda:[row(i,price=1+i/100) for i in range(1,21)])
    report=mobile.high_probability()
    assert len(report['proximos'])==2 and len(report['vip'])==18
    for r in report['vip']:
        assert not {'market','selection','line','texto','prob','ref_price','fit'} & r.keys()
    assert len(mobile.high_probability(True)['proximos'])==20
    owned=mobile.high_probability(unlocks={('alta_probabilidad','m1')})
    assert len(owned['proximos'])==3
    assert len(owned['vip'])==17


def test_disabled_feature_and_disabled_vip(delivery,monkeypatch):
    monkeypatch.setattr(mobile,'high_rows',lambda:[row(i) for i in range(10)])
    delivery['vip']['enabled']=False
    assert len(mobile.high_probability(True)['proximos'])==1
    delivery['alta_probabilidad']['enabled']=False
    assert mobile.high_probability(True)['proximos']==[]
    assert mobile.high_probability(True)['vip']==[]


def test_ladder_one_free_across_challenges_and_history(delivery,monkeypatch):
    challenges=[{'reto_id':i,'pasos':[{'paso':1,'outcome':'loss',**row(f'{i}a')},
                    {'paso':2,'outcome':None,'price':1.3,**row(f'{i}b',.79)}]} for i in range(1,4)]
    monkeypatch.setattr(mobile.escalera_datos,'informe_publico',lambda:{'activo':True,'actuales':copy.deepcopy(challenges)})
    monkeypatch.setattr(mobile.escalera_datos,'_pasos',lambda i,**kwargs:[{'paso':2,'prob':.79+i/1000}])
    report=mobile.ladder()
    assert sum(len(r['vip']) for r in report['actuales'])==2
    assert sum(sum(p.get('free') is True for p in r['pasos']) for r in report['actuales'])==1
    assert all(any(p['outcome']=='loss' for p in r['pasos']) for r in report['actuales'])
    assert sum(len(r['vip']) for r in mobile.ladder(True)['actuales'])==0


def test_admin_post_requires_csrf_before_database(monkeypatch):
    app=FastAPI();app.include_router(mobile.router);app.include_router(rewards.router)
    app.dependency_overrides[console.require_console]=lambda:'tester'
    client=TestClient(app)
    assert client.post('/control/configuracion-app/agenda',data={'enabled':'1'}).status_code==403
    assert client.post('/control/recompensas/config',data={}).status_code==403
    assert client.post('/control/recompensas/proveedores/bitlabs',data={}).status_code==403
    r=client.post('/control/configuracion-app/agenda',headers={'sec-fetch-site':'cross-site'},data={'csrf':panel.csrf_token('tester')})
    assert r.status_code==403


def test_guest_cannot_award_or_unlock():
    app=FastAPI();app.include_router(rewards.router)
    client=TestClient(app)
    for route,body in [('attendance',{}),('referrals',{'code':'ABC'}),('unlock',{'stream':'alta_probabilidad','pick_key':'m1'})]:
        assert client.post('/mobile/v1/rewards/'+route,json=body).status_code==401


def test_goles_esperados_implicitos_sin_filtrar_el_ajuste(delivery,monkeypatch):
    con={**row(1),'fit':{'lambda':2.204,'mu':.856,'rho':-.1,'linea':2.5,'residuo':.001}}
    monkeypatch.setattr(mobile,'high_rows',lambda:[con,row(2)])
    proximos={p['match_id']:p for p in mobile.high_probability(True)['proximos']}
    assert proximos['m1']['xg']=={'local':2.2,'visita':.86,'total':3.06}
    assert proximos['m2']['xg'] is None
    assert all('fit' not in p for p in proximos.values())


@pytest.mark.parametrize('fit',[None,{},{'lambda':float('nan'),'mu':1},{'lambda':'x','mu':1}])
def test_goles_esperados_ausentes_o_invalidos(fit):
    assert mobile.implied_goals(fit) is None


def test_started_match_keeps_sealed_pick_with_result(monkeypatch,delivery):
    started={**row(1),'kickoff_utc':datetime.now(timezone.utc)-timedelta(minutes=30),
             'outcome':'win','home_goals':2,'away_goals':1}
    monkeypatch.setattr(mobile,'high_rows',lambda:[started])
    assert mobile.high_probability()['proximos']==[]
    shown=mobile.high_probability(started=True)['proximos']
    assert [(p['match_id'],p['started'],p['outcome']) for p in shown]==[('m1',True,'win')]


def test_live_score_shape(monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(mobile, 'query_one', lambda *a, **k: {
        'live_home_goals': 1, 'live_away_goals': 0, 'live_minute': 48,
        'live_status': '2H', 'live_updated_at': now})
    assert mobile.live_score('m1') == {'marcador': [1, 0], 'minuto': 48, 'estado': '2H', 'actualizado': now}
    monkeypatch.setattr(mobile, 'query_one', lambda *a, **k: None)
    assert mobile.live_score('m1') is None


def test_markets_history_filters_and_rounds(monkeypatch):
    captured = {}

    def fake_query(sql, params=()):
        captured['params'] = params
        return [{'match_id': 'm1', 'market': 'totals', 'selection': 'over', 'line': 1.5, 'prob': 0.8123456,
                 'local': 'A', 'visitante': 'B', 'outcome': 'win', 'home_goals': 2, 'away_goals': 1}]

    monkeypatch.setattr(mobile, 'query', fake_query)
    monkeypatch.setattr(mobile, 'features', lambda: {'alta_probabilidad': {'enabled': True}})
    out = mobile.markets_history(Response(), market='totals,spreads', limit=50)
    assert captured['params'][2] == ['totals', 'spreads'] and captured['params'][-1] == 50
    item = out['items'][0]
    assert item['prob'] == 0.81 and item['texto']
    monkeypatch.setattr(mobile, 'features', lambda: {'alta_probabilidad': {'enabled': False}})
    assert mobile.markets_history(Response(), market=None, limit=10) == {'items': []}
