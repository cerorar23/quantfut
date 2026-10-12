import hashlib
import hmac
import os
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from qf.api import rewards, mobile


def test_bitlabs_signs_exact_original_url():
    url='https://example.org/rewards/callback/bitlabs?uid=test&tx=o1&amount=30&tag=a%20b'
    signature=hmac.new(b'test-secret',url.encode(),hashlib.sha1).hexdigest()
    assert rewards.bitlabs_valid(url+'&hash='+signature,'test-secret')
    assert not rewards.bitlabs_valid(url.replace('%20','+')+'&hash='+signature,'test-secret')
    assert not rewards.bitlabs_valid(url+'&hash='+signature,'wrong')
    assert not rewards.bitlabs_valid(url+'&hash='+signature+'&hash='+signature,'test-secret')


@pytest.mark.parametrize('value', ['NaN','Infinity','1e100','abc'])
def test_invalid_rewards_rejected(value):
    with pytest.raises(HTTPException):rewards.coin_amount(value)


def test_fractional_coins_round_down():
    assert rewards.coin_amount('35.9')==35
    assert rewards.coin_amount('-35.9')==35


def test_revu_rejects_forged_forwarded_ip(monkeypatch):
    monkeypatch.setenv('QF_REWARDS_TRUSTED_PROXY_CIDRS','172.20.0.0/16')
    request=Request({'type':'http','headers':[(b'cf-connecting-ip',b'1.2.3.4')],'client':('9.9.9.9',80)})
    assert not rewards.revu_valid(request,'1.2.3.4/32')
    request.scope['client']=('172.20.0.2',80)
    assert rewards.revu_valid(request,'1.2.3.4/32')
    assert not rewards.revu_valid(request,'1.2.3.5/32')


def test_tapjoy_verifier_md5():
    verifier=hashlib.md5(b'tx1:abc123:50:secreto').hexdigest()
    def req(**q):
        qs='&'.join(f'{k}={v}' for k,v in q.items()).encode()
        return Request({'type':'http','headers':[],'query_string':qs})
    ok=dict(id='tx1',snuid='abc123',currency='50',verifier=verifier)
    assert rewards.tapjoy_valid(req(**ok),'secreto')
    assert not rewards.tapjoy_valid(req(**{**ok,'currency':'500'}),'secreto')
    assert not rewards.tapjoy_valid(req(**ok),'otro')
    assert not rewards.tapjoy_valid(req(snuid='abc123',currency='50'),'secreto')


@pytest.fixture
def pg(monkeypatch):
    """Optional real PostgreSQL tests, ALL changes rolled back including users."""
    if os.getenv('QF_TEST_POSTGRES')!='1':pytest.skip('requires PostgreSQL')
    import psycopg
    from psycopg.rows import dict_row
    from qf.config import settings
    c=psycopg.connect(settings.pg_dsn,row_factory=dict_row)
    try:
        for aid in (-91001,-91002):
            c.execute("INSERT INTO accounts(account_id,email,password_hash,created_at,email_verified_at) VALUES(%s,%s,'test-not-a-login',now()-interval '1 day',now())",(aid,f'mobile-test-{abs(aid)}@invalid.example'))
        for module in (rewards,mobile):
            monkeypatch.setattr(module,'conn',lambda:nullcontext(c))
            monkeypatch.setattr(module,'query',lambda sql,params=():c.execute(sql,params).fetchall())
            monkeypatch.setattr(module,'query_one',lambda sql,params=():c.execute(sql,params).fetchone())
        yield c
    finally:
        c.rollback();c.close()


def test_pg_ledger_retry_spending_and_debt(pg):
    assert rewards.change(pg,-91001,150,'test:credit','offer')
    assert not rewards.change(pg,-91001,150,'test:credit','offer')
    assert rewards.change(pg,-91001,-100,'test:spend','unlock',spend=True)
    with pytest.raises(HTTPException):rewards.change(pg,-91001,-100,'test:spend2','unlock',spend=True)
    assert rewards.change(pg,-91001,-150,'test:reverse','reversal')
    assert rewards.wallet(pg,-91001)['balance']==-100
    assert pg.execute('SELECT count(*) AS n FROM reward_ledger WHERE account_id=-91001').fetchone()['n']==3


def test_pg_attendance_once_and_gap_resets(pg):
    account=pg.execute('SELECT * FROM accounts WHERE account_id=-91001').fetchone()
    first=rewards.attendance(account);second=rewards.attendance(account)
    assert first['coins']==30 and second['credited'] is False
    pg.execute("UPDATE reward_wallets SET last_attendance=current_date-2,streak=4 WHERE account_id=-91001")
    # A test gap creates a new date but today's immutable ledger already exists;
    # use a second account to test resetting without rewriting a ledger.
    rewards.wallet(pg,-91002)
    pg.execute('UPDATE reward_wallets SET last_attendance=%s,streak=4 WHERE account_id=-91002',(datetime.now(timezone.utc).date()-timedelta(days=2),))
    result=rewards.attendance(pg.execute('SELECT * FROM accounts WHERE account_id=-91002').fetchone())
    assert result['streak']==1 and result['coins']==30


def test_pg_provider_duplicate_reversal_and_out_of_order(pg):
    w=rewards.wallet(pg,-91001)
    rewards.provider_event('bitlabs','test-o1',w['uid'],100,'credit')
    rewards.provider_event('bitlabs','test-o1',w['uid'],100,'credit')
    assert rewards.wallet(pg,-91001)['balance']==100
    rewards.provider_event('bitlabs','test-o1',w['uid'],100,'reversal')
    rewards.provider_event('bitlabs','test-o1',w['uid'],100,'reversal')
    assert rewards.wallet(pg,-91001)['balance']==0
    rewards.provider_event('bitlabs','test-o2',w['uid'],50,'reversal')
    rewards.provider_event('bitlabs','test-o2',w['uid'],50,'credit')
    assert rewards.wallet(pg,-91001)['balance']==0


def test_pg_fixed_allocations_and_ladder_global_one(pg):
    rows=[{'match_id':f'test-{i}','prob':.8+i/1000,'ref_price':1.5+i/100,'batch_date':'2040-01-01'} for i in range(20)]
    first=mobile.allocations(rows,'alta_probabilidad')
    assert len(first)==2
    rows[-1]['ref_price']=99
    assert mobile.allocations(rows,'alta_probabilidad')==first
    for i,r in enumerate(rows):r.update(price=1.3,batch_date='2040-01-01' if i<10 else '2040-01-02')
    assert len(mobile.allocations(rows,'escalera'))==1


def test_pg_referral_paid_once_and_reversed(pg):
    inviter=rewards.wallet(pg,-91001)
    invitee=rewards.wallet(pg,-91002)
    pg.execute('INSERT INTO reward_referrals(invitee_id,referrer_id) VALUES(-91002,-91001)')
    rewards.provider_event('bitlabs','test-ref',invitee['uid'],100,'credit')
    assert rewards.wallet(pg,-91001)['balance']==200
    assert rewards.wallet(pg,-91002)['balance']==200
    rewards.provider_event('bitlabs','test-ref',invitee['uid'],100,'credit')
    assert rewards.wallet(pg,-91001)['balance']==200
    rewards.provider_event('bitlabs','test-ref',invitee['uid'],100,'reversal')
    assert rewards.wallet(pg,-91001)['balance']==0
    assert rewards.wallet(pg,-91002)['balance']==0
