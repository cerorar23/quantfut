"""Explicit Firebase identity and authenticated installation preferences."""
from __future__ import annotations

import logging
import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from . import cuentas as api
from ..comercial import cuentas, firebase
from ..comercial.cuentas import CuentaError
from ..db import conn, query, query_one

_log = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)
router = APIRouter(prefix='/app/v1/firebase', tags=['firebase'],
                   dependencies=[Depends(api.require_enabled)])
Language = Literal['es', 'en', 'pt', 'fr', 'it', 'de']


def fail(error: CuentaError):
    _log.warning('identidad Firebase rechazada: %s', error.code)
    status = 401 if error.code == 'firebase_token_invalido' else (
        503 if error.code in ('firebase_no_configurado', 'firebase_no_disponible', 'firebase_deshabilitado') else 409)
    raise HTTPException(status, {'code': error.code, 'message': error.message})


def check_app_token(request: Request) -> None:
    token = request.headers.get('x-firebase-appcheck')
    enforce = os.getenv('FIREBASE_APPCHECK_ENFORCE', '0') == '1'
    if not token:
        if enforce:
            raise HTTPException(403, {'code': 'app_check_requerido', 'message': 'Actualiza la app para continuar'})
        return
    from firebase_admin import app_check
    try:
        app_check.verify_token(token, app=firebase.admin_app())
    except Exception:
        if enforce:
            raise HTTPException(403, {'code': 'app_check_invalido', 'message': 'No se pudo comprobar esta instalación'}) from None


def firebase_account(creds: HTTPAuthorizationCredentials | None, request: Request) -> dict:
    if not creds:
        raise HTTPException(401, {'code': 'no_autenticado', 'message': 'Inicia sesión'})
    check_app_token(request)
    try:
        claims = firebase.verify_identity(creds.credentials)
        account = firebase.identity_account(claims)
    except CuentaError as error:
        fail(error)
    if not account:
        _log.warning('identidad Firebase sin cuenta activa vinculada')
        raise HTTPException(401, {'code': 'firebase_sin_cuenta', 'message': 'Vuelve a iniciar sesión'})
    return {**account, '_identity': 'firebase', '_token': creds.credentials}


class ConnectIn(BaseModel):
    id_token: str = Field(min_length=1, max_length=8192)
    terms_version: str | None = Field(default=None, max_length=40)
    privacy_version: str | None = Field(default=None, max_length=40)
    language: Language = 'es'


@router.post('/connect', response_model=api.MeOut)
def connect(body: ConnectIn, request: Request,
            creds: HTTPAuthorizationCredentials | None = Depends(_bearer)):
    api._limit(request, 'firebase_connect', 15, 300)
    check_app_token(request)
    existing = None
    if creds:
        if request.headers.get('x-qf-identity') == 'firebase':
            raise HTTPException(400, 'La vinculación requiere la sesión de la cuenta existente')
        existing = cuentas.account_from_access(api.redis_client(), creds.credentials)
        if not existing:
            raise HTTPException(401, {'code': 'no_autenticado', 'message': 'Accede de nuevo a tu cuenta existente'})
    try:
        claims = firebase.verify_identity(body.id_token)
        account = firebase.connect_identity(claims, body.terms_version, body.privacy_version,
                                            body.language, existing)
    except CuentaError as error:
        fail(error)
    return api.me(account)


class PreferencesIn(BaseModel):
    language: Language = 'es'
    analytics: bool = False
    diagnostics: bool = False
    push_enabled: bool = False
    # None = no tocar lo guardado (apps antiguas no lo envian). NULL en BD = activo.
    ads_measurement: bool | None = None


@router.get('/preferences')
def preferences(account: dict = Depends(api.current_account)):
    row = query_one('''SELECT language, analytics, diagnostics, push_enabled,
                              coalesce(ads_measurement, true) AS ads_measurement
                       FROM firebase_preferences WHERE account_id=%s''', (account['account_id'],))
    return row or {**PreferencesIn().model_dump(), 'ads_measurement': True}


@router.post('/preferences')
def save_preferences(body: PreferencesIn, account: dict = Depends(api.current_account)):
    with conn() as c:
        c.execute('''INSERT INTO firebase_preferences (account_id, language, analytics, diagnostics,
                                                       push_enabled, ads_measurement)
                     VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (account_id) DO UPDATE SET
                     language=EXCLUDED.language, analytics=EXCLUDED.analytics, diagnostics=EXCLUDED.diagnostics,
                     push_enabled=EXCLUDED.push_enabled,
                     ads_measurement=coalesce(EXCLUDED.ads_measurement, firebase_preferences.ads_measurement),
                     updated_at=now()''',
                  (account['account_id'], body.language, body.analytics, body.diagnostics,
                   body.push_enabled, body.ads_measurement))
        if not body.push_enabled:
            c.execute('UPDATE push_devices SET enabled=false WHERE account_id=%s', (account['account_id'],))
    return body


class DeviceIn(BaseModel):
    installation_id: UUID
    token: str = Field(min_length=20, max_length=4096)
    platform: Literal['android', 'ios']
    language: Language = 'es'


@router.post('/devices')
def register_device(body: DeviceIn, request: Request, account: dict = Depends(api.current_account)):
    api._limit(request, 'firebase_device', 30, 300)
    with conn() as c:
        prefs = c.execute('SELECT push_enabled FROM firebase_preferences WHERE account_id=%s',
                          (account['account_id'],)).fetchone()
        if not prefs or not prefs['push_enabled']:
            raise HTTPException(409, {'code': 'notificaciones_desactivadas', 'message': 'Activa las notificaciones primero'})
        # A token has only one owner. In-flight outbox rows also check that owner.
        c.execute('DELETE FROM notification_outbox WHERE installation_id IN '
                  '(SELECT installation_id FROM push_devices WHERE token=%s AND installation_id<>%s)',
                  (body.token, body.installation_id))
        c.execute('DELETE FROM push_devices WHERE token=%s AND installation_id<>%s',
                  (body.token, body.installation_id))
        c.execute('''INSERT INTO push_devices (installation_id, account_id, token, platform, language)
                     VALUES (%s,%s,%s,%s,%s) ON CONFLICT (installation_id) DO UPDATE SET
                     account_id=EXCLUDED.account_id, token=EXCLUDED.token, platform=EXCLUDED.platform,
                     language=EXCLUDED.language, enabled=true, updated_at=now()''',
                  (body.installation_id, account['account_id'], body.token, body.platform, body.language))
    return {'registered': True}


class InstallationIn(BaseModel):
    installation_id: UUID


@router.post('/devices/unregister', status_code=204)
def unregister_device(body: InstallationIn, account: dict = Depends(api.current_account)):
    with conn() as c:
        c.execute('UPDATE push_devices SET enabled=false WHERE installation_id=%s AND account_id=%s',
                  (body.installation_id, account['account_id']))


@router.get('/notifications')
def notifications(account: dict = Depends(api.current_account),
                  before: int | None = Query(None, ge=1), limit: int = Query(30, ge=1, le=100)):
    rows = query('''SELECT notification_id, title, body, match_id, created_at, expires_at, read_at
                    FROM account_notifications WHERE account_id=%s AND expires_at>now()
                    AND (%s::bigint IS NULL OR notification_id<%s)
                    ORDER BY notification_id DESC LIMIT %s''',
                 (account['account_id'], before, before, limit))
    return {'notifications': rows}


@router.post('/notifications/{notification_id}/read', status_code=204)
def mark_read(notification_id: int, account: dict = Depends(api.current_account)):
    with conn() as c:
        changed = c.execute('UPDATE account_notifications SET read_at=COALESCE(read_at,now()) '
                            'WHERE notification_id=%s AND account_id=%s',
                            (notification_id, account['account_id'])).rowcount
    if not changed:
        raise HTTPException(404, 'Aviso no disponible')
