"""PostgreSQL validation inside an outer transaction which always rolls back."""
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row
from fastapi import HTTPException
from starlette.requests import Request

from qf.config import settings
from qf.api import mobile, rewards, main

c=psycopg.connect(settings.pg_dsn,row_factory=dict_row)
original={}
checks=0
try:
    assert not c.execute('SELECT 1 FROM accounts WHERE account_id IN (-91001,-91002)').fetchone()
    for aid in (-91001,-91002):
        c.execute("INSERT INTO accounts(account_id,email,password_hash,created_at,email_verified_at) VALUES(%s,%s,'not-a-login',now()-interval '1 day',now())",(aid,f'mobile-rollback-{abs(aid)}@invalid.example'))
    for module in (mobile,rewards):
        for name in ('conn','query','query_one'):original[module,name]=getattr(module,name)
        module.conn=lambda:nullcontext(c)
        module.query=lambda sql,params=():c.execute(sql,params).fetchall()
        module.query_one=lambda sql,params=():c.execute(sql,params).fetchone()
    c.execute('UPDATE reward_settings SET enabled=true,attendance_enabled=true,referrals_enabled=true,unlock_cost=100,referrer_coins=200,invitee_coins=100,referral_min_coins=100 WHERE id=1')
    c.execute("UPDATE mobile_features SET enabled=true WHERE section='vip'")

    with c.transaction(force_rollback=True):
        rewards.change(c,-91001,150,'rollback:credit','offer')
        assert not rewards.change(c,-91001,150,'rollback:credit','offer')
        rewards.change(c,-91001,-100,'rollback:spend','unlock',spend=True)
        try:rewards.change(c,-91001,-100,'rollback:spend2','unlock',spend=True)
        except HTTPException as e:assert e.status_code==409
        else:raise AssertionError('Overspend accepted')
        rewards.change(c,-91001,-150,'rollback:reverse','reversal')
        assert rewards.wallet(c,-91001)['balance']==-100
        checks+=1

    with c.transaction(force_rollback=True):
        account=c.execute('SELECT * FROM accounts WHERE account_id=-91001').fetchone()
        first=rewards.attendance(account);second=rewards.attendance(account)
        assert first['credited'] and first['coins']==30 and not second['credited']
        assert rewards.wallet(c,-91001)['balance']==30
        rewards.wallet(c,-91002)
        c.execute('UPDATE reward_wallets SET streak=4,last_attendance=%s WHERE account_id=-91002',(datetime.now(timezone.utc).date()-timedelta(days=2),))
        assert rewards.attendance(c.execute('SELECT * FROM accounts WHERE account_id=-91002').fetchone())['streak']==1
        checks+=1

    with c.transaction(force_rollback=True):
        w=rewards.wallet(c,-91001)
        for _ in range(2):rewards.provider_event('bitlabs','rollback:o1',w['uid'],100,'credit')
        assert rewards.wallet(c,-91001)['balance']==100
        for _ in range(2):rewards.provider_event('bitlabs','rollback:o1',w['uid'],100,'reversal')
        assert rewards.wallet(c,-91001)['balance']==0
        rewards.provider_event('bitlabs','rollback:o2',w['uid'],50,'reversal')
        rewards.provider_event('bitlabs','rollback:o2',w['uid'],50,'credit')
        assert rewards.wallet(c,-91001)['balance']==0
        checks+=1

    with c.transaction(force_rollback=True):
        rewards.wallet(c,-91001);w=rewards.wallet(c,-91002)
        c.execute('INSERT INTO reward_referrals(invitee_id,referrer_id) VALUES(-91002,-91001)')
        rewards.provider_event('bitlabs','rollback:ref',w['uid'],100,'credit')
        assert rewards.wallet(c,-91001)['balance']==200 and rewards.wallet(c,-91002)['balance']==200
        rewards.provider_event('bitlabs','rollback:ref',w['uid'],100,'credit')
        assert rewards.wallet(c,-91001)['balance']==200
        rewards.provider_event('bitlabs','rollback:ref',w['uid'],100,'reversal')
        assert rewards.wallet(c,-91001)['balance']==0 and rewards.wallet(c,-91002)['balance']==0
        checks+=1

    with c.transaction(force_rollback=True):
        rows=[{'match_id':f'rollback-{i}','prob':.8+i/1000,'ref_price':1.5+i/100,'batch_date':'2040-01-01'} for i in range(20)]
        free=mobile.allocations(rows,'alta_probabilidad');assert len(free)==2
        rows[0]['ref_price']=99
        assert mobile.allocations(rows,'alta_probabilidad')==free
        for i,r in enumerate(rows):r.update(price=1.3,batch_date='2040-01-01' if i<10 else '2040-01-02')
        assert len(mobile.allocations(rows,'escalera'))==1
        checks+=1

    with c.transaction(force_rollback=True):
        old=mobile.high_probability;sub=mobile.suscripciones.active_subscription
        mobile.high_probability=lambda:{'proximos':[],'vip':[{'match_id':'rollback-match','pick_key':'rollback-match','locked':True,'kickoff_utc':datetime.now(timezone.utc)+timedelta(days=1)}]}
        mobile.suscripciones.active_subscription=lambda aid:None
        try:
            account=c.execute('SELECT * FROM accounts WHERE account_id=-91001').fetchone()
            rewards.change(c,-91001,150,'rollback:unlock-credit','offer')
            body=rewards.UnlockIn(stream='alta_probabilidad',pick_key='rollback-match')
            assert rewards.unlock(body,account)['charged']==100
            assert rewards.unlock(body,account)['charged']==0
            assert rewards.wallet(c,-91001)['balance']==50
            assert ('alta_probabilidad','rollback-match') in rewards.entitlements(account)
            checks+=1
        finally:mobile.high_probability=old;mobile.suscripciones.active_subscription=sub

    request=Request({'type':'http','method':'GET','path':'/control/recompensas','query_string':b'','headers':[(b'host',b'localhost')],'client':('127.0.0.1',1),'scheme':'http','server':('localhost',80)})
    assert b'Monedas y referidos' in rewards.control(request,'rollback-tester').body
    assert b'Configuraci' in mobile.configuration_page(request,'rollback-tester').body
    checks+=1
    with c.transaction(force_rollback=True):
        from qf.api import panel
        request=Request({'type':'http','method':'POST','path':'/control/configuracion-app/estadisticas','query_string':b'','headers':[(b'host',b'localhost'),(b'origin',b'http://localhost'),(b'sec-fetch-site',b'same-origin')],'client':('127.0.0.1',1),'scheme':'http','server':('localhost',80)})
        token=panel.csrf_token('rollback-tester')
        assert mobile.configuration_update('estadisticas',request,enabled='',message='Entrenamiento comprobado',csrf=token,user='rollback-tester').status_code==303
        assert not mobile.features()['estadisticas']['enabled']
        assert mobile.features()['estadisticas']['message']=='Entrenamiento comprobado'
        assert mobile.configuration_update('estadisticas',request,enabled='1',message='Modelo en entrenamiento',csrf=token,user='rollback-tester').status_code==303
        assert mobile.features()['estadisticas']['enabled']
        rewards.control_config(request,enabled='1',attendance_enabled='1',referrals_enabled='1',unlock_cost=123,attendance_coins='1,2,3,4,5,6,7',referrer_coins=200,invitee_coins=100,referral_min_coins=100,message='Pendiente',csrf=token,user='rollback-tester')
        assert rewards.settings()['unlock_cost']==123
        assert rewards.settings()['attendance_coins']==[1,2,3,4,5,6,7]
        checks+=1
    print(f'{checks} PostgreSQL checks passed; all test changes rolled back.')
finally:
    c.rollback();c.close()
    for (module,name),value in original.items():setattr(module,name,value)
