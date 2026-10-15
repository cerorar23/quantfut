"""Anuncios con recompensa (AdMob): tickets, tope diario y acreditación verificada.

El cliente nunca acredita monedas ni elige el importe. La app pide un ticket, muestra el
video y Google avisa al servidor con un callback firmado (SSV); solo ese callback acredita
(ver `credit` y `callback`). Tope, pausa y día UTC se deciden aquí, no en la app.
"""
from __future__ import annotations

import math
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from . import anuncios_ssv as ssv
from . import rewards
from ..comercial.auditoria import audit
from ..db import conn, query, query_one  # noqa: F401 - `query*` los usa el panel

router = APIRouter(tags=['anuncios'])
TICKET_TTL = timedelta(minutes=5)
# Bloques de prueba oficiales de Google (rewarded). Se confirman contra su documentación al
# configurar el panel: https://developers.google.com/admob/android/test-ads
TEST_UNITS = {'android': 'ca-app-pub-3940256099942544/5224354917',
              'ios': 'ca-app-pub-3940256099942544/1712485313'}


def utc_day(now: datetime) -> date:
    return now.astimezone(timezone.utc).date()


def unit_for(cfg: dict, platform: str) -> str:
    if cfg['ad_test_mode']:
        return TEST_UNITS[platform]
    return cfg['ad_unit_android'] if platform == 'android' else cfg['ad_unit_ios']


def check_ticket_allowed(cfg: dict, platform: str, *, used_today: int, last_credit_at: datetime | None,
                         open_ticket: bool, now: datetime) -> None:
    if not cfg['enabled'] or not cfg['ads_enabled']:
        raise HTTPException(503, 'Los anuncios con recompensa no están disponibles')
    if not unit_for(cfg, platform):
        raise HTTPException(409, 'Anuncios no disponibles en este dispositivo')
    if open_ticket:
        raise HTTPException(409, {'code': 'anuncio_en_curso', 'message': 'Ya tienes un anuncio en curso'})
    if used_today >= cfg['ad_daily_cap']:
        raise HTTPException(409, {'code': 'limite_diario', 'message': 'Has alcanzado el límite de anuncios de hoy'})
    if last_credit_at is not None:
        wait = (last_credit_at + timedelta(seconds=cfg['ad_cooldown_seconds']) - now).total_seconds()
        if wait > 0:
            raise HTTPException(409, {'code': 'anuncio_en_espera',
                                      'message': 'Espera un momento antes del siguiente anuncio'},
                                headers={'Retry-After': str(math.ceil(wait))})


def usage(c, account_id: int, day: date) -> tuple[int, datetime | None]:
    """Créditos del día UTC `day` y fecha del último crédito de siempre (la pausa cruza la medianoche)."""
    row = c.execute("SELECT count(*) FILTER (WHERE day=%s) AS n, max(created_at) AS last "
                    "FROM reward_ad_events WHERE account_id=%s AND outcome='credited'", (day, account_id)).fetchone()
    return row['n'], row['last']


def ads_state(cfg: dict, used: int, last: datetime | None, now: datetime) -> dict:
    if not cfg['enabled'] or not cfg['ads_enabled']:
        return {'enabled': False}
    next_at = None
    if last is not None and last + timedelta(seconds=cfg['ad_cooldown_seconds']) > now:
        next_at = (last + timedelta(seconds=cfg['ad_cooldown_seconds'])).isoformat()
    return {'enabled': True, 'coins': cfg['ad_coins'], 'daily_cap': cfg['ad_daily_cap'],
            'cooldown_seconds': cfg['ad_cooldown_seconds'], 'used_today': used,
            'remaining_today': max(0, cfg['ad_daily_cap'] - used), 'next_at': next_at}


def ads_block(c, account_id: int | None, cfg: dict, now: datetime) -> dict:
    if account_id is None:
        return {'enabled': False}
    used, last = usage(c, account_id, utc_day(now))
    return ads_state(cfg, used, last, now)


def issue_ticket(c, account_id: int, cfg: dict, platform: str, now: datetime) -> dict:
    wallet = rewards.wallet(c, account_id, lock=True)            # serializa por cuenta
    used, last = usage(c, account_id, utc_day(now))
    open_ticket = c.execute('SELECT 1 FROM reward_ad_tickets WHERE account_id=%s AND used_at IS NULL '
                            'AND cancelled_at IS NULL AND expires_at>%s', (account_id, now)).fetchone() is not None
    check_ticket_allowed(cfg, platform, used_today=used, last_credit_at=last, open_ticket=open_ticket, now=now)
    nonce = secrets.token_hex(16)
    expires = now + TICKET_TTL
    c.execute('INSERT INTO reward_ad_tickets(nonce,account_id,day,created_at,expires_at) VALUES(%s,%s,%s,%s,%s)',
              (nonce, account_id, utc_day(now), now, expires))
    return {'user_id': wallet['uid'], 'nonce': nonce, 'unit_id': unit_for(cfg, platform),
            'expires_at': expires.isoformat()}


def cancel_ticket(c, account_id: int, nonce: str, now: datetime) -> dict:
    cur = c.execute('UPDATE reward_ad_tickets SET cancelled_at=%s WHERE nonce=%s AND account_id=%s '
                    'AND used_at IS NULL AND cancelled_at IS NULL', (now, nonce, account_id))
    return {'cancelled': cur.rowcount > 0}


class TicketIn(BaseModel):
    platform: str = Field(pattern='^(android|ios)$')


class CancelIn(BaseModel):
    nonce: str = Field(min_length=1, max_length=64)


@router.post('/mobile/v1/rewards/ads/ticket')
def ticket(body: TicketIn, account: dict = Depends(rewards.verified_account)):
    cfg = rewards.settings()
    with conn() as c:
        return issue_ticket(c, account['account_id'], cfg, body.platform, datetime.now(timezone.utc))


@router.post('/mobile/v1/rewards/ads/cancel')
def cancel(body: CancelIn, account: dict = Depends(rewards.verified_account)):
    with conn() as c:
        return cancel_ticket(c, account['account_id'], body.nonce, datetime.now(timezone.utc))


def normalize_unit(unit: str) -> str:
    """Google envía `ad_unit` solo con la parte numérica; la configuración lleva `ca-app-pub-…/<n>`."""
    return unit.rsplit('/', 1)[-1]


def allowed_units(cfg: dict) -> set[str]:
    units = {cfg['ad_unit_android'], cfg['ad_unit_ios']} - {''}
    if cfg['ad_test_mode']:
        units |= set(TEST_UNITS.values())
    return {normalize_unit(u) for u in units}


def decide_outcome(*, ticket: dict | None, account: dict, cfg: dict, ad_unit: str,
                   used_today: int, now: datetime) -> str:
    if (ticket is None or ticket['used_at'] is not None or ticket['cancelled_at'] is not None
            or ticket['expires_at'] < now):
        return 'rejected_ticket'
    if account['status'] != 'active' or account['email_verified_at'] is None:
        return 'rejected_account'
    if normalize_unit(ad_unit) not in allowed_units(cfg):
        return 'rejected_unit'
    if used_today >= cfg['ad_daily_cap']:
        return 'rejected_cap'
    return 'credited'


def credit(c, *, transaction_id: str, uid: str, nonce: str, ad_unit: str, cfg: dict, now: datetime) -> str:
    """Decide y registra un callback ya autenticado. Idempotente por `transaction_id`."""
    account = c.execute('SELECT a.account_id,a.status,a.email_verified_at FROM accounts a '
                        'JOIN reward_wallets w USING(account_id) WHERE w.uid=%s', (uid,)).fetchone() if uid else None
    if account is None:
        return 'unknown_user'
    aid = account['account_id']
    rewards.wallet(c, aid, lock=True)
    prev = c.execute('SELECT outcome FROM reward_ad_events WHERE transaction_id=%s', (transaction_id,)).fetchone()
    if prev:
        return prev['outcome']
    ticket = c.execute('SELECT * FROM reward_ad_tickets WHERE nonce=%s AND account_id=%s FOR UPDATE',
                       (nonce, aid)).fetchone() if nonce else None
    day = ticket['day'] if ticket else utc_day(now)
    used = c.execute("SELECT count(*) AS n FROM reward_ad_events WHERE account_id=%s AND day=%s "
                     "AND outcome='credited'", (aid, day)).fetchone()['n']
    outcome = decide_outcome(ticket=ticket, account=account, cfg=cfg, ad_unit=ad_unit, used_today=used, now=now)
    coins = cfg['ad_coins'] if outcome == 'credited' else 0
    if outcome == 'credited':
        rewards.change(c, aid, coins, f'ad:{transaction_id}', 'ad')
    if ticket is not None and ticket['cancelled_at'] is None and ticket['used_at'] is None:
        c.execute('UPDATE reward_ad_tickets SET used_at=%s WHERE nonce=%s', (now, nonce))
    c.execute('INSERT INTO reward_ad_events(transaction_id,account_id,nonce,ad_unit,coins,outcome,day,created_at) '
              'VALUES(%s,%s,%s,%s,%s,%s,%s,%s)', (transaction_id, aid, nonce, ad_unit, coins, outcome, day, now))
    return outcome


@router.get('/rewards/callback/admob', include_in_schema=False)
def callback(request: Request):
    raw = request.scope.get('query_string', b'').decode('ascii', 'replace')
    try:
        _, _, key_id = ssv.split_signed(raw)
        ssv.verify(raw, ssv.keys_for(key_id))
    except ssv.SignatureError:
        raise HTTPException(403, 'Firma inválida') from None
    except ssv.KeysUnavailable:
        raise HTTPException(503, 'Claves de verificación no disponibles') from None
    q = request.query_params
    tx = q.get('transaction_id', '')
    if not tx or len(tx) > 160:
        raise HTTPException(422, 'Transacción inválida')
    # Un callback ya emitido se acepta aunque el administrador apague los anuncios después.
    cfg = rewards.settings()
    with conn() as c:
        outcome = credit(c, transaction_id=tx, uid=q.get('user_id', '')[:64], nonce=q.get('custom_data', '')[:64],
                         ad_unit=q.get('ad_unit', '')[:80], cfg=cfg, now=datetime.now(timezone.utc))
        audit(c, 'reward:admob', 'reward_callback', detail={'transaction_id': tx, 'outcome': outcome})
    return PlainTextResponse('OK', headers={'Cache-Control': 'no-store'})
