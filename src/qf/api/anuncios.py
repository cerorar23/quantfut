"""Anuncios con recompensa (AdMob): tickets, tope diario y acreditación verificada.

El cliente nunca acredita monedas ni elige el importe. La app pide un ticket, muestra el
video y Google avisa al servidor con un callback firmado (SSV); solo ese callback acredita
(ver `credit` y `callback`). Tope, pausa y día UTC se deciden aquí, no en la app.
"""
from __future__ import annotations

import math
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from . import rewards
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
