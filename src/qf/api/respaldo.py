"""Panel /control/respaldo: PitchAPI como verificador y respaldo de API-Football.

La clave se guarda cifrada (AES-256-GCM), es de solo escritura y nunca vuelve a
mostrarse; la variable PITCHAPI_KEY del entorno sirve de respaldo. Cada cambio
queda en admin_audit.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Form, HTTPException, Request

from . import console, panel
from ..comercial import cifrado
from ..comercial.auditoria import audit
from ..db import conn, query, query_one
from ..ingest import pitchapi_respaldo as respaldo

router = APIRouter()

KINDS = {
    'score': 'Marcador distinto',
    'result_pending': 'Resultado sin cerrar en la base',
    'missing_in_db': 'Partido ausente en la base',
}


def valid_key(key: str) -> bool:
    return (20 <= len(key) <= 200 and key.startswith('pk_') and key.isprintable()
            and not any(ch.isspace() for ch in key))


@router.get('/control/respaldo', include_in_schema=False)
def pagina(request: Request, user: str = Depends(console.require_console)):
    cfg = respaldo.settings_row()
    has_key = bool(cfg.get('key_enc'))
    stats = query_one("""SELECT
        (SELECT count(*) FROM pitchapi_teams) AS equipos,
        (SELECT count(*) FROM matches WHERE xg_source = 'pitchapi') AS xg_total,
        (SELECT count(*) FROM matches WHERE xg_source = 'pitchapi'
           AND xg_recorded_at >= now() - interval '30 days') AS xg_30d""") or {}
    return panel._render(
        request, 'respaldo.html', user, 'respaldo', cfg=cfg, has_key=has_key,
        env_key=bool(os.getenv('PITCHAPI_KEY')), cifrado_ok=cifrado.disponible(), stats=stats,
        kinds=KINDS,
        discrepancias=query("""SELECT d.id, d.detected_at, d.kind, d.league_id, d.match_id, d.detail
                               FROM pitchapi_discrepancies d WHERE d.reviewed_at IS NULL
                               ORDER BY d.detected_at DESC LIMIT 100"""),
        pasadas=query("""SELECT ran_at, rows_written, ok, detail FROM ingest_health
                         WHERE source = 'pitchapi' ORDER BY ran_at DESC LIMIT 15"""))


@router.post('/control/respaldo/config', include_in_schema=False)
def guardar(request: Request, enabled: str = Form(''), key: str = Form('', max_length=200),
            clear_key: str = Form(''), csrf: str = Form(''),
            user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    if enabled not in ('', '1') or clear_key not in ('', '1'):
        raise HTTPException(422, 'Valor inválido')
    key = key.strip()
    if key and not valid_key(key):
        raise HTTPException(422, 'La clave de PitchAPI no tiene un formato válido (pk_live_… o pk_test_…)')
    if key and not cifrado.disponible():
        raise HTTPException(422, 'Falta QF_SECRETS_KEY en el servidor: no se puede guardar la clave cifrada')
    current = respaldo.settings_row()
    if clear_key == '1':
        key_enc, hint = '', ''
    elif key:
        key_enc, hint = cifrado.cifrar(key, respaldo.KEY_CONTEXT), key[-4:]
    else:
        key_enc, hint = current.get('key_enc') or '', current.get('key_hint') or ''
    if enabled == '1' and not (key_enc or os.getenv('PITCHAPI_KEY')):
        raise HTTPException(422, 'No se puede activar sin una clave')
    with conn() as c:
        c.execute('UPDATE pitchapi_settings SET enabled = %s, key_enc = %s, key_hint = %s, updated_at = now() '
                  'WHERE id = 1', (enabled == '1', key_enc, hint))
        audit(c, panel._actor(request, user), 'pitchapi_respaldo',
              detail={'enabled': enabled == '1',
                      'key': 'cambiada' if key else ('borrada' if clear_key == '1' else 'sin cambios')})
    return panel._back('/control/respaldo', 'respaldo_guardado')


@router.post('/control/respaldo/probar', include_in_schema=False)
def probar(request: Request, csrf: str = Form(''), user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    ok, text = respaldo.test_connection(respaldo.api_key())
    with conn() as c:
        audit(c, panel._actor(request, user), 'pitchapi_probar', detail={'ok': ok, 'resultado': text})
    code = 'respaldo_ok' if ok else ('respaldo_401' if 'inválida' in text else 'respaldo_error')
    return panel._back('/control/respaldo', code)


@router.post('/control/respaldo/discrepancias/{discrepancy_id}/revisar', include_in_schema=False)
def revisar(request: Request, discrepancy_id: int, csrf: str = Form(''),
            user: str = Depends(console.require_console)):
    panel._check_post(request, user, csrf)
    with conn() as c:
        n = c.execute('UPDATE pitchapi_discrepancies SET reviewed_at = now(), reviewed_by = %s '
                      'WHERE id = %s AND reviewed_at IS NULL', (panel._actor(request, user), discrepancy_id)).rowcount
        if n:
            audit(c, panel._actor(request, user), 'pitchapi_discrepancia_revisada',
                  detail={'id': discrepancy_id})
    return panel._back('/control/respaldo', 'respaldo_revisada' if n else 'sin_cambios')
