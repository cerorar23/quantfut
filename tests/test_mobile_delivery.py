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
    monkeypatch.setattr(mobile.mobile_updates, 'configuration', lambda: dict(mobile.mobile_updates.DEFAULTS))
    flags={k:{'enabled':True,'message':'Modelo en entrenamiento'} for k in mobile.SECTIONS}
    monkeypatch.setattr(mobile,'features',lambda:flags)
    monkeypatch.setattr(mobile.alta_prob_datos,'informe_publico',lambda:{'estado':'activa','motivos':[], 'proximos':[], 'historial':{'n':0}})
    monkeypatch.setattr(mobile,'allocations',lambda rows,stream:{mobile.pick_key(p) for p in mobile.choose_free(rows,stream)})
    return flags


@pytest.mark.parametrize('n,expected',[(0,0),(1,1),(9,1),(21,1)])
def test_one_free_per_market_highest_probability(n,expected):
    rows=[row(i,prob=.75+i/200,price=1.4) for i in range(1,n+1)]
    selected=mobile.choose_free(rows,'alta_probabilidad')
    assert len(selected)==expected
    assert [r['match_id'] for r in selected]==([f'm{n}'] if n else [])


def test_one_free_per_market_across_markets():
    rows=[{**row(i,prob=.75+i/100),'market':'totals'} for i in range(1,12)]
    rows+=[{**row(100+i,prob=.80+i/100),'market':'spreads'} for i in range(1,4)]
    rows+=[{**row(200,prob=.78),'market':'corners'}]
    ids={r['match_id'] for r in mobile.choose_free(rows,'alta_probabilidad')}
    assert ids=={'m11','m103','m200'}  # la mejor probabilidad de cada mercado


def test_free_pick_is_highest_quote_capped_at_1_60():
    rows=[row(1,.88,1.10),row(2,.80,1.25),row(3,.79,1.60),row(4,.78,1.61),row(5,.85,None)]
    ids=[r['match_id'] for r in mobile.choose_free(rows,'alta_probabilidad')]
    assert ids==['m3']  # manda la cuota (1,60 dentro del tope; 1,61 fuera; sin cuota no entra)
    assert [r['match_id'] for r in mobile.choose_free([row(1,.9,1.10),row(2,.8,1.65)],'alta_probabilidad')]==['m1']


def test_top_up_adds_best_quote_of_markets_without_an_open_free():
    now=datetime.now(timezone.utc)
    soon=now+timedelta(hours=2); started=now-timedelta(hours=1)
    rows=[{**row(1,.8,1.18),'market':'totals','kickoff_utc':soon},
          {**row(2,.8,1.10),'market':'totals','kickoff_utc':soon},
          {**row(3,.8,1.25),'market':'corners','kickoff_utc':soon},
          {**row(4,.8,1.30),'market':'spreads','kickoff_utc':started},   # ya empezó: no cuenta
          {**row(5,.8,None),'market':'double_chance','kickoff_utc':soon}]  # sin cuota: no entra
    assert {r['match_id'] for r in mobile.top_up(rows,set(),now)}=={'m1','m3'}
    # un mercado con gratis abierto no suma otro; el que ya empezó no cuenta como abierto
    assert {r['match_id'] for r in mobile.top_up(rows,{'m2'},now)}=={'m3'}
    assert {r['match_id'] for r in mobile.top_up(rows,{'m4'},now)}=={'m1','m3'}
    assert mobile.top_up(rows,{'m1','m3'},now)==[]  # idempotente


def test_probability_bounds_and_no_fake_quote():
    rows=[row(1,.729),row(2,.73),row(3,.95),row(4,.951),row(5,.85,None)]
    assert mobile.choose_free(rows,'alta_probabilidad')[0]['match_id']=='m3'
    # Por debajo de 73 % (incluido el antiguo piso de 62 %) y por encima de 95 % no se muestra.
    assert {r['match_id'] for r in mobile.choose_free([row(1,.729),row(6,.62),row(4,.951)],'alta_probabilidad')}==set()
    assert {r['match_id'] for r in mobile.choose_free([row(2,.73)],'alta_probabilidad')}=={'m2'}
    assert len(mobile.choose_free([row(1,.8,None)],'alta_probabilidad'))==0


def test_ladder_uses_exact_probability_not_rounded():
    rows=[{**row(1,.79),'pick_key':'1:2','_prob_exact':.7851,'price':1.3},
          {**row(2,.79),'pick_key':'2:2','_prob_exact':.7949,'price':1.25}]
    assert mobile.choose_free(rows,'escalera')[0]['pick_key']=='2:2'


def test_anonymous_does_not_receive_vip_selection(delivery,monkeypatch):
    monkeypatch.setattr(mobile,'high_rows',lambda:[row(i,price=1+i/100) for i in range(1,21)])
    report=mobile.high_probability()
    assert len(report['proximos'])==1 and len(report['vip'])==19  # uno por mercado
    for r in report['vip']:
        assert not {'selection','line','texto','prob','ref_price','fit'} & r.keys()
        assert r['market']=='totals'  # solo la categoría, para ubicar el candado
        assert 1.01<=r["cuota"]<=1.2  # la cuota publicada sí sale: es el gancho del candado
    assert len(mobile.high_probability(True)['proximos'])==20
    owned=mobile.high_probability(unlocks={('alta_probabilidad','m1')})
    assert len(owned['proximos'])==2
    assert len(owned['vip'])==18


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


SAMPLE_MARKETS = {'1x2': {'home': .5410917, 'draw': .28, 'away': .1769},
                  'btts': {'yes': .4004, 'no': .5995},
                  'totals': {'1.5': {'over': .6467}, '2.5': {'over': .3707}},
                  'team_totals': {'home': {'0.5': {'over': .767}, '1.5': {'over': .4277}, '2.5': {'over': .1805}},
                                  'away': {'0.5': {'over': .5125}, '1.5': {'over': .1623}}}}


def test_model_card_rounds_and_tolerates_missing_parts():
    card = mobile.model_card(SAMPLE_MARKETS)
    assert card['mas_2_5'] == .37 and card['ambos'] == .4 and card['local'] == .54
    assert card['goles_local'] == [.77, .43, .18]
    assert card['goles_visita'] == [.51, .16, None]  # lo que falta es None, no 0
    assert card['fuente'] == 'modelo'
    assert mobile.model_card({}) is None and mobile.model_card(None) is None
    assert mobile.model_card({'btts': {'yes': 7}}) is None  # fuera de [0, 1]


def test_model_card_only_with_a_visible_pick(delivery, monkeypatch):
    ficha = lambda: {'partido': {}, 'local': {'id': 1, 'nombre': 'A'}, 'visitante': {'id': 2, 'nombre': 'B'},
                     'cara_a_cara': None, 'alineaciones': None, 'bajas': None, 'tabla': None}
    monkeypatch.setattr(mobile.fichas, '_ficha', lambda mid: ficha())
    monkeypatch.setattr(mobile.rewards, 'entitlements', lambda account: set())
    monkeypatch.setattr(mobile, 'ladder', lambda *a, **k: {'actuales': []})
    monkeypatch.setattr(mobile, 'live_score', lambda mid: None)
    monkeypatch.setattr(mobile, 'query_one', lambda *a, **k: {'markets': SAMPLE_MARKETS})
    monkeypatch.setattr(mobile, 'high_probability',
                        lambda *a, **k: {'proximos': [{'match_id': 'm1'}], 'vip': []})
    out = mobile.detail('m1', Response(), plus=False, account=None)
    assert out['ficha']['modelo']['mas_1_5'] == .65 and out['ficha']['probabilities']['home'] == .5410917
    monkeypatch.setattr(mobile, 'high_probability',
                        lambda *a, **k: {'proximos': [], 'vip': [{'match_id': 'm1'}]})
    out = mobile.detail('m1', Response(), plus=False, account=None)
    assert out['ficha']['modelo'] is None and out['locked'] is True


def test_market_card_for_sharp_leagues_is_labelled_and_coherent(monkeypatch):
    monkeypatch.setattr(mobile, 'query_one', lambda *a, **k: {'fit': {'lambda': 2.41, 'mu': .76, 'rho': -.06}})
    card = mobile.market_card('m1')
    assert card['fuente'] == 'mercado'
    assert card['mas_1_5'] > card['mas_2_5'] > 0
    assert card['goles_local'][0] > card['goles_local'][1] > card['goles_local'][2]
    assert card['goles_local'][0] > card['goles_visita'][0]  # el local esperado es más goleador
    assert abs(card['local'] + card['empate'] + card['visita'] - 1) < .02
    for bad in ({'fit': None}, {'fit': {'lambda': 0, 'mu': 1}}, {'fit': {'lambda': 'x', 'mu': 1}},
                {'fit': {'lambda': float('nan'), 'mu': 1}}):
        monkeypatch.setattr(mobile, 'query_one', lambda *a, _b=bad, **k: _b)
        assert mobile.market_card('m1') is None
    monkeypatch.setattr(mobile, 'query_one', lambda *a, **k: None)
    assert mobile.market_card('m1') is None


def test_inicio_no_enseña_partidos_terminados():
    """Un partido terminado sale de la agenda de Inicio (queda en los registros históricos)."""
    agenda = [{'match_id': 'a', 'estado': 'scheduled'}, {'match_id': 'b', 'estado': 'live'},
              {'match_id': 'c', 'estado': 'finished', 'marcador': [5, 0]},
              {'match_id': 'd'}, {'match_id': 'e', 'estado': 'postponed'}]
    assert [m['match_id'] for m in mobile.visible_agenda(agenda)] == ['a', 'b', 'd', 'e']


def test_inicio_pide_una_semana_de_agenda(monkeypatch):
    """La app agrupa la agenda por día: el servidor manda DIAS_AGENDA (7) días desde la fecha."""
    pedido = {}

    def ventana(fecha, tz, dias, ahora=None):
        pedido['dias'] = dias
        raise ValueError('corta aquí')

    monkeypatch.setattr(mobile, 'config', lambda: {'features': {'agenda': {'enabled': True}}})
    monkeypatch.setattr(mobile.fichas, 'ventana', ventana)
    with pytest.raises(mobile.HTTPException):
        mobile.home(Response(), '2026-10-13', 0, False, None)
    assert pedido['dias'] == mobile.DIAS_AGENDA == 7


def test_detail_without_goals_model_lists_vip_picks_as_locks(delivery, monkeypatch):
    monkeypatch.setattr(mobile.fichas, '_ficha', lambda mid: {
        'partido': {}, 'local': {'id': 1, 'nombre': 'A'}, 'visitante': {'id': 2, 'nombre': 'B'},
        'cara_a_cara': None, 'alineaciones': None, 'bajas': None, 'tabla': None})
    monkeypatch.setattr(mobile.rewards, 'entitlements', lambda account: set())
    monkeypatch.setattr(mobile, 'ladder', lambda *a, **k: {'actuales': []})
    monkeypatch.setattr(mobile, 'live_score', lambda mid: None)
    monkeypatch.setattr(mobile, 'query_one', lambda *a, **k: None)
    monkeypatch.setattr(mobile, 'mercados_partido', lambda *a, **k: None)  # sin modelo de goles
    vip = [{'match_id': 'm1', 'pick_key': 'k1', 'market': 'corners', 'locked': True},
           {'match_id': 'm1', 'pick_key': 'k2', 'market': 'double_chance', 'locked': True}]
    monkeypatch.setattr(mobile, 'high_probability',
                        lambda *a, **k: {'proximos': [{'match_id': 'm1'}], 'vip': vip})
    out = mobile.detail('m1', Response(), plus=False, account=None)
    filas = out['ficha']['mercados']['filas']
    assert [f['grupo'] for f in filas] == ['DOBLE OPORTUNIDAD', 'CÓRNERS'] and all(f['locked'] for f in filas)
    assert out['ficha']['mercados']['sin_modelo'] is True and out['locked'] is True
    assert set(filas[0]) == {'id', 'grupo', 'locked'}
    out = mobile.detail('m1', Response(), plus=True, account=None)
    assert out['ficha']['mercados'] is None


def test_quote_of_accepts_both_price_names_and_rejects_garbage():
    assert mobile.quote_of({'ref_price': 1.3456}) == 1.35
    assert mobile.quote_of({'price': '1.25'}) == 1.25  # escalera
    for bad in ({}, {'ref_price': None}, {'ref_price': 1.0}, {'ref_price': .8},
                {'ref_price': float('nan')}, {'ref_price': 'x'}):
        assert mobile.quote_of(bad) is None
    meta = mobile.metadata({'match_id': 'm1', 'market': 'totals', 'selection': 'over', 'line': 2.5,
                            'prob': .9, 'ref_price': 1.4, 'fit': {}})
    assert meta['cuota'] == 1.4 and not {'selection', 'line', 'prob', 'ref_price', 'fit'} & meta.keys()


def test_cap_free_deja_cuatro_los_de_mayor_cuota():
    now = datetime.now(timezone.utc)
    rows = [{**row(i, price=1.0 + i / 100), 'market': f'mk{i}'} for i in range(1, 8)]
    free = {mobile.pick_key(r) for r in rows}
    kept = mobile.cap_free(rows, free, now)
    assert kept == {'m7', 'm6', 'm5', 'm4'}          # las cuatro cuotas más altas
    assert mobile.cap_free(rows, {'m1', 'm2', 'm3', 'm4'}, now) == {'m1', 'm2', 'm3', 'm4'}  # no toca si caben


def test_cap_free_no_cuenta_los_que_ya_empezaron():
    now = datetime.now(timezone.utc)
    empezados = [{**row(i, price=1.5), 'kickoff_utc': now - timedelta(hours=1)} for i in range(10, 14)]
    abiertos = [row(i, price=1.2) for i in range(1, 5)]
    free = {mobile.pick_key(r) for r in empezados + abiertos}
    assert mobile.cap_free(empezados + abiertos, free, now) == free      # 4 abiertos + 4 ya empezados


def test_alta_probabilidad_enseña_como_mucho_cuatro_gratis_y_el_resto_con_candado(monkeypatch, delivery):
    rows = [{**row(i, price=1.0 + i / 100), 'market': f'mk{i}'} for i in range(1, 9)]
    monkeypatch.setattr(mobile, 'high_rows', lambda: rows)
    monkeypatch.setattr(mobile, 'allocations', lambda r, stream: {mobile.pick_key(p) for p in r})
    report = mobile.high_probability()
    assert sorted(p['match_id'] for p in report['proximos']) == ['m5', 'm6', 'm7', 'm8']
    assert all(p['free'] for p in report['proximos'])
    assert {v['match_id'] for v in report['vip']} == {'m1', 'm2', 'm3', 'm4'}
    assert all(v['locked'] and v['cuota'] for v in report['vip'])          # el candado enseña su cuota
    assert mobile.config()['high_probability_free_max'] == 4


def test_equipo_desconocido_muestra_el_mercado_y_no_el_modelo():
    """Auditoría 2026-10-21: con `both_teams_known=false` el 1X2 propio no significa nada."""
    cons = {'home': .30, 'draw': .26, 'away': .44}
    probs, propio = mobile.uno_x_dos({'probabilities': {'home': .077, 'draw': .2, 'away': .723},
                                      'market_consensus': cons, 'conocido': 'false'})
    assert propio is False and probs == pytest.approx(cons)
    assert mobile.uno_x_dos({'probabilities': {'home': .5}, 'market_consensus': None,
                             'conocido': 'false'}) == (None, False)
    # Conocido o fila anterior al campo: el del modelo.
    assert mobile.uno_x_dos({'probabilities': {'home': .5}, 'conocido': 'true'}) == ({'home': .5}, True)
    assert mobile.uno_x_dos({'markets': SAMPLE_MARKETS}) == (SAMPLE_MARKETS['1x2'], True)
    assert mobile.uno_x_dos(None) == (None, False)


def test_ficha_con_equipo_desconocido_usa_la_tarjeta_de_mercado(delivery, monkeypatch):
    ficha = lambda: {'partido': {}, 'local': {'id': 1, 'nombre': 'A'}, 'visitante': {'id': 2, 'nombre': 'B'},
                     'cara_a_cara': None, 'alineaciones': None, 'bajas': None, 'tabla': None}
    monkeypatch.setattr(mobile.fichas, '_ficha', lambda mid: ficha())
    monkeypatch.setattr(mobile.rewards, 'entitlements', lambda account: set())
    monkeypatch.setattr(mobile, 'ladder', lambda *a, **k: {'actuales': []})
    monkeypatch.setattr(mobile, 'live_score', lambda mid: None)
    monkeypatch.setattr(mobile, 'query_one', lambda *a, **k: {
        'markets': SAMPLE_MARKETS, 'market_consensus': {'home': .3, 'draw': .3, 'away': .4}, 'conocido': 'false'})
    monkeypatch.setattr(mobile, 'market_card', lambda mid: {'fuente': 'mercado'})
    monkeypatch.setattr(mobile, 'high_probability',
                        lambda *a, **k: {'proximos': [{'match_id': 'm1'}], 'vip': []})
    out = mobile.detail('m1', Response(), plus=False, account=None)
    assert out['ficha']['probabilities']['home'] == pytest.approx(.3)
    assert out['ficha']['modelo'] == {'fuente': 'mercado'}
