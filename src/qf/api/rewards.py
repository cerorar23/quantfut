"""Server-owned coins, verified callbacks and per-pick entitlements.

Coins unlock content only; they cannot be purchased, transferred or withdrawn.
The client cannot choose a reward amount. A reversal may create a debt which
blocks further spending; historical ledger rows are never rewritten.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from psycopg.errors import UndefinedTable

from . import console, cuentas, panel
from ..db import conn, query, query_one
from ..comercial.auditoria import audit
from ..comercial import cifrado

router = APIRouter(tags=['rewards'])
bearer = HTTPBearer(auto_error=False)
PROVIDERS = {'revu':'RevU', 'bitlabs':'BitLabs', 'tapjoy':'Tapjoy / Unity Offerwall',
             'torox':'Torox','ayet':'ayeT-Studios','adjoe':'adjoe Playtime'}
IMPLEMENTED = {'revu', 'bitlabs', 'tapjoy'}


def settings() -> dict:
    try:
        return query_one('SELECT * FROM reward_settings WHERE id=1')
    except UndefinedTable:
        raise HTTPException(503, 'Configuración de monedas pendiente de instalar') from None


def optional_account(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                     request: Request = None) -> dict | None:
    if creds is None:
        return None
    cuentas.require_enabled()
    if request is not None and request.headers.get('x-qf-identity') == 'firebase':
        from .firebase import firebase_account
        return firebase_account(creds, request)
    return cuentas.current_account(creds)


def verified_account(account: dict | None = Depends(optional_account)) -> dict:
    if account is None:
        raise HTTPException(401, 'Inicia sesión para usar monedas')
    if account['email_verified_at'] is None:
        raise HTTPException(403, 'Verifica tu correo antes de usar monedas')
    return account


def require_active(cfg: dict | None = None) -> dict:
    cfg = cfg or settings()
    if not cfg['enabled']:
        raise HTTPException(503, cfg['message'])
    return cfg


def wallet(c, account_id: int, *, lock: bool = False) -> dict:
    c.execute('INSERT INTO reward_wallets(account_id,uid,referral_code) VALUES (%s,%s,%s) '
              'ON CONFLICT(account_id) DO NOTHING', (account_id, secrets.token_hex(16), secrets.token_hex(6).upper()))
    return c.execute('SELECT * FROM reward_wallets WHERE account_id=%s' + (' FOR UPDATE' if lock else ''), (account_id,)).fetchone()


def change(c, account_id: int, delta: int, event_key: str, kind: str, *, spend: bool = False) -> bool:
    """Serialize wallet changes. Returning false means an identical retry."""
    w = wallet(c, account_id, lock=True)
    old = c.execute('SELECT account_id,delta,kind FROM reward_ledger WHERE event_key=%s', (event_key,)).fetchone()
    if old:
        if (old['account_id'],old['delta'],old['kind']) != (account_id,delta,kind):
            raise HTTPException(409, 'Evento duplicado con datos distintos')
        return False
    if spend and w['balance'] + delta < 0:
        raise HTTPException(409, 'No tienes monedas suficientes')
    balance = w['balance'] + delta
    c.execute('UPDATE reward_wallets SET balance=%s WHERE account_id=%s', (balance,account_id))
    c.execute('INSERT INTO reward_ledger(account_id,delta,balance_after,event_key,kind) VALUES(%s,%s,%s,%s,%s)',
              (account_id,delta,balance,event_key,kind))
    return True


def public_settings() -> dict:
    cfg = settings()
    return {k: cfg[k] for k in ('enabled','unlock_cost','attendance_enabled','attendance_coins',
                               'referrals_enabled','referrer_coins','invitee_coins','referral_min_coins','message')}


def entitlements(account: dict | None) -> set[tuple[str,str]]:
    if account is None or not settings()['enabled']:
        return set()
    return {(r['stream'],r['pick_key']) for r in query('SELECT stream,pick_key FROM reward_unlocks WHERE account_id=%s', (account['account_id'],))}


@router.get('/mobile/v1/rewards')
def overview(response: Response, account: dict | None = Depends(optional_account)):
    response.headers['Cache-Control'] = 'no-store'
    cfg = public_settings()
    providers = query('SELECT provider,enabled FROM reward_providers ORDER BY provider')
    out = {'settings':cfg, 'signed_in':account is not None, 'providers':[
        {'provider':p['provider'],'name':PROVIDERS[p['provider']],
         'available':cfg['enabled'] and p['enabled'] and provider_ready(p['provider'])} for p in providers],
        'wallet':None, 'ledger':[], 'referrals':None,
        'terms':'Monedas sin valor monetario: canjeables solo por pronósticos. '
                'Las ofertas dependen del país y se acreditan tras la confirmación del proveedor. '
                'Una oferta anulada revierte sus monedas. La asistencia usa días UTC. '
                'Los referidos se premian una vez, después de verificar el correo y completar '
                'ofertas confirmadas por el mínimo indicado. No se premian reseñas.'}
    if account is not None:
        with conn() as c:
            w = wallet(c,account['account_id'])
        today = datetime.now(timezone.utc).date()
        out['wallet'] = {k:w[k] for k in ('balance','streak','last_attendance','referral_code')}
        out['wallet']['spendable'] = max(0,w['balance'])
        out['wallet']['can_check_in'] = cfg['enabled'] and cfg['attendance_enabled'] and w['last_attendance'] != today and account['email_verified_at'] is not None
        out['ledger'] = query('SELECT delta,balance_after,kind,created_at FROM reward_ledger WHERE account_id=%s ORDER BY ledger_id DESC LIMIT 50',(account['account_id'],))
        out['referrals'] = {'registered': query_one('SELECT count(*) AS n FROM reward_referrals WHERE referrer_id=%s',(account['account_id'],))['n'],
                            'qualified':query_one('SELECT count(*) AS n FROM reward_referrals WHERE referrer_id=%s AND qualified_at IS NOT NULL AND reversed_at IS NULL',(account['account_id'],))['n'],
                            'joined':query_one('SELECT qualified_at,reversed_at FROM reward_referrals WHERE invitee_id=%s',(account['account_id'],))}
    return out


@router.post('/mobile/v1/rewards/attendance')
def attendance(account: dict = Depends(verified_account)):
    cfg = require_active()
    if not cfg['attendance_enabled']:
        raise HTTPException(503,'Asistencia desactivada')
    today = datetime.now(timezone.utc).date()
    with conn() as c:
        w = wallet(c,account['account_id'],lock=True)
        if w['last_attendance'] == today:
            return {'credited':False,'balance':w['balance'],'streak':w['streak']}
        streak = w['streak']+1 if w['last_attendance'] == today-timedelta(days=1) else 1
        coins = cfg['attendance_coins'][(streak-1)%len(cfg['attendance_coins'])]
        change(c,account['account_id'],coins,f"attendance:{account['account_id']}:{today}",'attendance')
        c.execute('UPDATE reward_wallets SET last_attendance=%s,streak=%s WHERE account_id=%s',(today,streak,account['account_id']))
        return {'credited':True,'coins':coins,'balance':w['balance']+coins,'streak':streak}


class ReferralIn(BaseModel):
    code: str = Field(min_length=1,max_length=24)


@router.post('/mobile/v1/rewards/referrals')
def referral(body: ReferralIn, account: dict = Depends(verified_account)):
    cfg = require_active()
    if not cfg['referrals_enabled']:
        raise HTTPException(503,'Referidos desactivados')
    if datetime.now(timezone.utc)-account['created_at'] > timedelta(days=7):
        raise HTTPException(409,'El código se registra durante los primeros 7 días de la cuenta')
    with conn() as c:
        wallet(c,account['account_id'],lock=True)
        referrer = c.execute('SELECT w.account_id,a.created_at,a.email_verified_at,a.status FROM reward_wallets w JOIN accounts a USING(account_id) WHERE referral_code=%s',(body.code.strip().upper(),)).fetchone()
        if not referrer or referrer['status'] != 'active' or referrer['email_verified_at'] is None:
            raise HTTPException(422,'Código no disponible')
        if referrer['account_id'] == account['account_id'] or referrer['created_at'] >= account['created_at']:
            raise HTTPException(422,'No puedes usar este código')
        old = c.execute('SELECT referrer_id FROM reward_referrals WHERE invitee_id=%s',(account['account_id'],)).fetchone()
        if old and old['referrer_id'] != referrer['account_id']:
            raise HTTPException(409,'Ya tienes un código registrado')
        c.execute('INSERT INTO reward_referrals(invitee_id,referrer_id) VALUES(%s,%s) ON CONFLICT DO NOTHING',(account['account_id'],referrer['account_id']))
    return {'registered':True,'qualified':False}


def qualify_referral(c, account_id: int, cfg: dict, event: str) -> None:
    if not cfg['referrals_enabled']:
        return
    r = c.execute('SELECT * FROM reward_referrals WHERE invitee_id=%s FOR UPDATE',(account_id,)).fetchone()
    if not r or r['qualified_at'] is not None:
        return
    total = c.execute("SELECT coalesce(sum(CASE WHEN state='credit' THEN coins ELSE -coins END),0) AS n FROM reward_provider_events WHERE account_id=%s",(account_id,)).fetchone()['n']
    if total < cfg['referral_min_coins']:
        return
    for aid,coins,role in [(r['referrer_id'],cfg['referrer_coins'],'referrer'),(account_id,cfg['invitee_coins'],'invitee')]:
        change(c,aid,coins,f'referral:{account_id}:{role}',role)
    c.execute('UPDATE reward_referrals SET qualified_at=now(),referrer_award=%s,invitee_award=%s,qualifying_event=%s,qualifying_min_coins=%s WHERE invitee_id=%s',
              (cfg['referrer_coins'],cfg['invitee_coins'],event,cfg['referral_min_coins'],account_id))


class UnlockIn(BaseModel):
    stream: str = Field(pattern='^(alta_probabilidad|escalera)$')
    pick_key: str = Field(min_length=1,max_length=160)


@router.post('/mobile/v1/rewards/unlock')
def unlock(body: UnlockIn, account: dict = Depends(verified_account)):
    from . import mobile
    from ..comercial import suscripciones
    cfg = require_active()
    if not mobile.features()['vip']['enabled']:
        raise HTTPException(503,'Desbloqueos temporalmente desactivados')
    report = mobile.high_probability() if body.stream == 'alta_probabilidad' else mobile.ladder()
    rows = [*report['proximos'],*report['vip']] if body.stream == 'alta_probabilidad' else [p for r in report['actuales'] for p in [*r['pasos'],*r['vip']] if p.get('outcome') is None]
    pick = next((p for p in rows if str(p.get('pick_key')) == body.pick_key),None)
    if not pick or pick['kickoff_utc'] <= datetime.now(timezone.utc):
        raise HTTPException(404,'Este pronóstico no está disponible para desbloquear')
    if pick.get('locked') is not True or suscripciones.active_subscription(account['account_id']) is not None:
        return {'unlocked':True,'charged':0}
    with conn() as c:
        wallet(c,account['account_id'],lock=True)
        old = c.execute('SELECT cost FROM reward_unlocks WHERE account_id=%s AND stream=%s AND pick_key=%s',(account['account_id'],body.stream,body.pick_key)).fetchone()
        if old:
            return {'unlocked':True,'charged':0}
        change(c,account['account_id'],-cfg['unlock_cost'],f"unlock:{account['account_id']}:{body.stream}:{body.pick_key}",'unlock',spend=True)
        c.execute('INSERT INTO reward_unlocks(account_id,stream,pick_key,cost) VALUES(%s,%s,%s,%s)',(account['account_id'],body.stream,body.pick_key,cfg['unlock_cost']))
    return {'unlocked':True,'charged':cfg['unlock_cost']}


ENV_SECRETS = {'bitlabs':'QF_BITLABS_SECRET', 'tapjoy':'QF_TAPJOY_SECRET'}


def provider_secret(provider: str, p: dict | None = None) -> str:
    """Secret guardada (cifrada) desde el panel; si no hay o no se puede
    descifrar, la variable de entorno."""
    if p is None:
        p = query_one('SELECT * FROM reward_providers WHERE provider=%s',(provider,))
    token = (p or {}).get('secret_enc')
    if token:
        try:
            return cifrado.descifrar(token, f'reward_provider:{provider}')
        except cifrado.CifradoError:
            pass
    return os.getenv(ENV_SECRETS.get(provider,''),'')


def provider_ready(provider: str) -> bool:
    p = query_one('SELECT * FROM reward_providers WHERE provider=%s',(provider,))
    if not p or not p['public_id'] or provider not in IMPLEMENTED:
        return False
    if provider in ENV_SECRETS:
        return bool(provider_secret(provider,p))
    return bool(p['approved_ips'] and os.getenv('QF_REWARDS_TRUSTED_PROXY_CIDRS'))


@router.post('/mobile/v1/rewards/offers/{provider}')
def launch(provider: str, account: dict = Depends(verified_account)):
    require_active()
    p = query_one('SELECT * FROM reward_providers WHERE provider=%s',(provider,))
    if not p or not p['enabled'] or not provider_ready(provider):
        raise HTTPException(503,'Proveedor todavía no configurado')
    with conn() as c:
        uid = wallet(c,account['account_id'])['uid']
    if provider == 'tapjoy':
        # El offerwall de Tapjoy lo abre el SDK nativo: no hay URL. `user_id`
        # debe pasarse como TJC_OPTION_USER_ID para que llegue como `snuid`.
        return {'sdk':'tapjoy','sdk_key':p['public_id'],'user_id':uid}
    url = (f"https://wall.revenueuniverse.com/{p['public_id']}/offers/{uid}" if provider == 'revu' else
           'https://web.bitlabs.ai/?'+urlencode({'token':p['public_id'],'uid':uid}))
    return {'url':url}


def bitlabs_valid(raw_url: str, secret: str) -> bool:
    if raw_url.count('&hash=') != 1:
        return False
    original, signature = raw_url.rsplit('&hash=',1)
    if not secret or len(signature) != 40:
        return False
    return hmac.compare_digest(hmac.new(secret.encode(),original.encode(),hashlib.sha1).hexdigest(),signature)


def tapjoy_valid(request: Request, secret: str) -> bool:
    """MD5(id:snuid:currency:secret) del callback estándar de Tapjoy."""
    q = request.query_params
    if not secret or not q.get('id') or not q.get('verifier'):
        return False
    expected = hashlib.md5(f"{q['id']}:{q.get('snuid','')}:{q.get('currency','')}:{secret}".encode()).hexdigest()
    return hmac.compare_digest(expected, q['verifier'].lower())


def revu_valid(request: Request, allowed: str) -> bool:
    """Forwarded headers are trusted only from explicitly configured proxies."""
    try:
        proxy = ipaddress.ip_address(request.client.host)
        trusted = [ipaddress.ip_network(v.strip()) for v in os.getenv('QF_REWARDS_TRUSTED_PROXY_CIDRS','').split(',') if v.strip()]
        if not any(proxy in network for network in trusted):
            return False
        source = ipaddress.ip_address(request.headers.get('cf-connecting-ip',''))
        return any(source in ipaddress.ip_network(v.strip()) for v in allowed.split(',') if v.strip())
    except ValueError:
        return False


def coin_amount(value: str) -> int:
    try:
        n = Decimal(value)
        if not n.is_finite() or abs(n) > 1000000:
            raise ValueError
        return int(abs(n).quantize(Decimal('1'),rounding=ROUND_DOWN))
    except (InvalidOperation,ValueError):
        raise HTTPException(422,'Importe inválido') from None


def provider_event(provider: str, tx: str, uid: str, coins: int, state: str) -> None:
    cfg = settings()
    with conn() as c:
        # Global event/referral ordering prevents cross-wallet deadlocks and
        # races between a credit and its reversal. All callbacks are atomic.
        c.execute("SELECT pg_advisory_xact_lock(hashtextextended('reward:providers',0))")
        account = c.execute('SELECT a.* FROM accounts a JOIN reward_wallets w USING(account_id) WHERE w.uid=%s',(uid,)).fetchone()
        if not account or account['status'] != 'active' or account['email_verified_at'] is None:
            raise HTTPException(403,'Usuario no disponible')
        aid = account['account_id']
        previous = c.execute('SELECT account_id,coins FROM reward_provider_events WHERE provider=%s AND transaction_id=%s AND state=%s',(provider,tx,state)).fetchone()
        if previous:
            if (previous['account_id'],previous['coins']) != (aid,coins):
                raise HTTPException(409,'Transacción duplicada con datos distintos')
            return
        other = c.execute('SELECT * FROM reward_provider_events WHERE provider=%s AND transaction_id=%s AND state<>%s',(provider,tx,state)).fetchone()
        if other and (other['account_id'],other['coins']) != (aid,coins):
            raise HTTPException(409,'La reversión no coincide con el crédito')
        c.execute('INSERT INTO reward_provider_events(provider,transaction_id,state,account_id,coins) VALUES(%s,%s,%s,%s,%s)',(provider,tx,state,aid,coins))
        # An out-of-order reversal records a tombstone; a later credit must not
        # award currency. An existing credit is reversed exactly once.
        if state == 'credit' and other is None:
            change(c,aid,coins,f'offer:{provider}:{tx}:credit','offer')
            qualify_referral(c,aid,cfg,f'{provider}:{tx}')
        elif state == 'reversal' and other is not None:
            change(c,aid,-coins,f'offer:{provider}:{tx}:reversal','reversal')
            r = c.execute('SELECT * FROM reward_referrals WHERE invitee_id=%s AND qualified_at IS NOT NULL AND reversed_at IS NULL FOR UPDATE',(aid,)).fetchone()
            total = c.execute("SELECT coalesce(sum(CASE WHEN state='credit' THEN coins ELSE -coins END),0) AS n FROM reward_provider_events WHERE account_id=%s",(aid,)).fetchone()['n']
            if r and total < r['qualifying_min_coins']:
                change(c,r['referrer_id'],-r['referrer_award'],f'referral:{aid}:referrer:reverse','referral_reversal')
                change(c,aid,-r['invitee_award'],f'referral:{aid}:invitee:reverse','referral_reversal')
                c.execute('UPDATE reward_referrals SET reversed_at=now() WHERE invitee_id=%s',(aid,))
        audit(c,f'reward:{provider}','reward_callback',detail={'transaction_id':tx,'state':state,'account_id':aid,'coins':coins})


@router.get('/rewards/callback/{provider}', include_in_schema=False)
def callback(provider: str, request: Request):
    p = query_one('SELECT * FROM reward_providers WHERE provider=%s',(provider,))
    if not p or provider not in IMPLEMENTED or not provider_ready(provider):
        raise HTTPException(503,'Proveedor no configurado')
    # Do not stop accepted callbacks when an admin disables new offers:
    # users may have already completed a task before the switch was changed.
    if provider == 'bitlabs':
        raw = request.scope.get('query_string',b'').decode('ascii')
        base = os.getenv('QF_REWARDS_PUBLIC_ORIGIN','https://pronosticosdeportivos.pro').rstrip('/')
        original = base+request.scope.get('raw_path',request.url.path.encode()).decode('ascii')+'?'+raw
        if not bitlabs_valid(original,provider_secret(provider,p)):
            raise HTTPException(403,'Firma inválida')
        q = request.query_params; uid=q.get('uid','');tx=q.get('tx','');value=q.get('amount','')
        offer_state = q.get('state')
        if offer_state is not None and offer_state not in ('COMPLETED','RECONCILED'):
            raise HTTPException(422,'Estado de oferta no válido')
        state='reversal' if offer_state == 'RECONCILED' or value.startswith('-') else 'credit'
        if state == 'reversal' and offer_state is None:
            tx=q.get('ref','')  # configure REF for legacy negative reconciliation
    elif provider == 'tapjoy':
        # Tapjoy reintenta cada 5 min durante 4 días ante cualquier respuesta
        # distinta de 200/403: los errores definitivos deben ser 403.
        if p['approved_ips'] and not revu_valid(request,p['approved_ips']):
            raise HTTPException(403,'Origen no autorizado')
        if not tapjoy_valid(request,provider_secret(provider,p)):
            raise HTTPException(403,'Firma inválida')
        q=request.query_params;uid=q.get('snuid','');tx=q['id'];value=q.get('currency','');state='credit'
        if value.startswith('-'):
            raise HTTPException(403,'Un crédito no puede ser negativo')
        try:
            provider_event(provider,tx,uid,coin_amount(value),state)
        except HTTPException as e:
            if e.status_code in (409,422):
                raise HTTPException(403,e.detail) from None
            raise
        return PlainTextResponse('OK',headers={'Cache-Control':'no-store'})
    else:
        if not revu_valid(request,p['approved_ips']):
            raise HTTPException(403,'Origen no autorizado')
        q=request.query_params;uid=q.get('uid','');tx=q.get('actionid','');value=q.get('currency','')
        status=q.get('status','')
        if status not in ('1','2'):
            raise HTTPException(422,'Estado inválido')
        state='reversal' if status=='2' else 'credit'
    if not tx or len(tx)>160 or not uid or len(uid)>64:
        raise HTTPException(422,'Transacción inválida')
    if state == 'credit' and value.startswith('-'):
        raise HTTPException(422,'Un crédito no puede ser negativo')
    provider_event(provider,tx,uid,coin_amount(value),state)
    return PlainTextResponse('OK',headers={'Cache-Control':'no-store'})


@router.get('/control/recompensas',include_in_schema=False)
def control(request: Request, user: str = Depends(console.require_console)):
    providers=query('SELECT * FROM reward_providers ORDER BY provider')
    for p in providers:
        p['ready']=provider_ready(p['provider']);p['name']=PROVIDERS[p['provider']]
        p['has_secret']=bool(p.pop('secret_enc',''));p['env_secret']=bool(os.getenv(ENV_SECRETS.get(p['provider'],'')))
    return panel._render(request,'rewards.html',user,'rewards',cfg=settings(),providers=providers,
                         ledger=query('SELECT ledger_id,account_id,delta,balance_after,kind,created_at FROM reward_ledger ORDER BY ledger_id DESC LIMIT 100'),
                         referrals=query('SELECT * FROM reward_referrals ORDER BY created_at DESC LIMIT 100'))


@router.post('/control/recompensas/config',include_in_schema=False)
def control_config(request: Request, enabled: str = Form(''), attendance_enabled: str = Form(''),
                   referrals_enabled: str = Form(''), unlock_cost: int = Form(100,ge=1,le=1000000),
                   attendance_coins: str = Form('30,35,35,40,40,45,50',max_length=100),
                   referrer_coins: int = Form(200,ge=0,le=1000000), invitee_coins: int = Form(100,ge=0,le=1000000),
                   referral_min_coins: int = Form(100,ge=1,le=1000000), message: str = Form('Recompensas temporalmente no disponibles',max_length=180),
                   csrf: str = Form(''),user: str = Depends(console.require_console)):
    import json
    panel._check_post(request,user,csrf)
    if any(v not in ('','1') for v in (enabled,attendance_enabled,referrals_enabled)):
        raise HTTPException(422,'Estado inválido')
    try:
        coins=[int(v.strip()) for v in attendance_coins.split(',')]
        if len(coins)!=7 or any(v<0 or v>1000000 for v in coins):
            raise ValueError
    except ValueError:
        raise HTTPException(422,'Indica siete recompensas enteras entre 0 y 1000000') from None
    with conn() as c:
        c.execute('UPDATE reward_settings SET enabled=%s,attendance_enabled=%s,referrals_enabled=%s,unlock_cost=%s,attendance_coins=%s::jsonb,referrer_coins=%s,invitee_coins=%s,referral_min_coins=%s,message=%s,updated_at=now() WHERE id=1',
                  (enabled=='1',attendance_enabled=='1',referrals_enabled=='1',unlock_cost,json.dumps(coins),referrer_coins,invitee_coins,referral_min_coins,message.strip()))
        audit(c,panel._actor(request,user),'reward_settings',detail={'enabled':enabled=='1','unlock_cost':unlock_cost,'attendance':coins,'referrer_coins':referrer_coins,'invitee_coins':invitee_coins,'referral_min_coins':referral_min_coins})
    return panel._back('/control/recompensas','mobile_guardado')


@router.post('/control/recompensas/proveedores/{provider}',include_in_schema=False)
def control_provider(provider: str, request: Request, enabled: str = Form(''), public_id: str = Form('',max_length=120),
                     approved_ips: str = Form('',max_length=1000), secret: str = Form('',max_length=200),
                     clear_secret: str = Form(''), csrf: str = Form(''), user: str = Depends(console.require_console)):
    panel._check_post(request,user,csrf)
    if provider not in PROVIDERS or enabled not in ('','1') or clear_secret not in ('','1'):
        raise HTTPException(422,'Proveedor inválido')
    if public_id and not all(ch.isalnum() or ch in '-_' for ch in public_id):
        raise HTTPException(422,'Identificador público inválido')
    secret = secret.strip()
    if secret and not cifrado.disponible():
        raise HTTPException(422,'Falta QF_SECRETS_KEY en el servidor: no se puede guardar la secret key cifrada')
    if secret and (provider not in ENV_SECRETS or not secret.isprintable() or any(ch.isspace() for ch in secret)):
        raise HTTPException(422,'Secret key no válida para este proveedor')
    try:
        for v in approved_ips.split(','):
            if v.strip(): ipaddress.ip_network(v.strip())
    except ValueError:
        raise HTTPException(422,'Lista de IP no válida') from None
    current = query_one('SELECT * FROM reward_providers WHERE provider=%s',(provider,)) or {}
    # Campo de solo escritura: vacío conserva la actual; "quitar" la borra.
    if clear_secret == '1':
        new_enc = ''
    elif secret:
        new_enc = cifrado.cifrar(secret, f'reward_provider:{provider}')
    else:
        new_enc = current.get('secret_enc') or ''
    effective = secret or provider_secret(provider, {**current, 'secret_enc': new_enc})
    if enabled=='1' and (provider not in IMPLEMENTED or not public_id or
                         (provider in ENV_SECRETS and not effective) or
                         (provider=='revu' and (not approved_ips or not os.getenv('QF_REWARDS_TRUSTED_PROXY_CIDRS')))):
        raise HTTPException(422,'Faltan credenciales o la integración de este proveedor')
    with conn() as c:
        c.execute('UPDATE reward_providers SET enabled=%s,public_id=%s,approved_ips=%s,secret_enc=%s,updated_at=now() WHERE provider=%s',(enabled=='1',public_id,approved_ips,new_enc,provider))
        audit(c,panel._actor(request,user),'reward_provider',detail={'provider':provider,'enabled':enabled=='1','public_id':public_id,
              'secret':'cambiada' if secret else ('borrada' if clear_secret=='1' else 'sin cambios')})
    return panel._back('/control/recompensas','mobile_guardado')
