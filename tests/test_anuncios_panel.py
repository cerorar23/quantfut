"""Panel /control/anuncios y app-ads.txt (src/qf/api/anuncios.py)."""
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from qf.api import anuncios, console, panel, rewards
from test_anuncios import CFG, pg  # noqa: F401 - `pg` es una fixture compartida

FORM = dict(enabled='1', test_mode='1', coins=10, cap=5, cooldown=180,
            unit_android='', unit_ios='', publisher='')


def _parse(**kw):
    return anuncios.parse_config(**(FORM | kw))


def test_parse_config_valida_y_normaliza():
    out = _parse(unit_android=' ca-app-pub-1234567890123456/1234567890 ', publisher='pub-1234567890123456')
    assert out == {'ads_enabled': True, 'ad_test_mode': True, 'ad_coins': 10, 'ad_daily_cap': 5,
                   'ad_cooldown_seconds': 180, 'ad_unit_android': 'ca-app-pub-1234567890123456/1234567890',
                   'ad_unit_ios': '', 'admob_publisher_id': 'pub-1234567890123456'}


@pytest.mark.parametrize('kw', [
    dict(enabled='si'), dict(test_mode='x'), dict(coins=0), dict(coins=1000001), dict(cap=0), dict(cap=51),
    dict(cooldown=-1), dict(cooldown=3601), dict(unit_android='ca-app-pub-1/2'), dict(unit_ios='abc'),
    dict(publisher='1234567890123456'), dict(publisher='pub-12'),
])
def test_parse_config_rechaza_valores_invalidos(kw):
    with pytest.raises(HTTPException) as e:
        _parse(**kw)
    assert e.value.status_code == 422


def test_no_se_activa_en_real_sin_ningun_id_de_bloque():
    with pytest.raises(HTTPException) as e:
        _parse(test_mode='')
    assert e.value.status_code == 422 and 'modo prueba' in e.value.detail
    _parse(test_mode='', unit_ios='ca-app-pub-1234567890123456/1234567890')
    _parse(enabled='', test_mode='')                      # apagado sí puede guardarse sin IDs


def test_pg_save_config_escribe_ajustes_y_auditoria(pg):
    values = _parse(coins=15, cap=3, cooldown=60)
    anuncios.save_config(pg, 'panel:test', values)
    cfg = pg.execute('SELECT * FROM reward_settings WHERE id=1').fetchone()
    assert (cfg['ads_enabled'], cfg['ad_coins'], cfg['ad_daily_cap'], cfg['ad_cooldown_seconds']) == (True, 15, 3, 60)
    fila = pg.execute("SELECT actor,detail FROM admin_audit WHERE action='ads_settings' "
                      "ORDER BY audit_id DESC LIMIT 1").fetchone()
    assert fila['actor'] == 'panel:test' and fila['detail']['ad_coins'] == 15


@pytest.fixture
def panel_client(monkeypatch):
    app = FastAPI()
    app.include_router(anuncios.router)
    app.dependency_overrides[console.require_console] = lambda: 'tester'
    monkeypatch.setattr(anuncios, 'page_data',
                        lambda: {'cfg': CFG | {'ad_test_mode': True}, 'today': {}, 'events': []})
    return TestClient(app), panel.csrf_token('tester')


def test_pagina_del_panel_se_pinta(panel_client):
    client, _ = panel_client
    r = client.get('/control/anuncios')
    assert r.status_code == 200 and 'Publicidad AdMob' in r.text and 'Nunca pulses anuncios reales' in r.text


def test_post_sin_csrf_valido_es_403(panel_client):
    client, _ = panel_client
    r = client.post('/control/anuncios/config', data={**{k: str(v) for k, v in FORM.items()}, 'csrf': 'malo'})
    assert r.status_code == 403


# --- app-ads.txt ------------------------------------------------------------------

def test_app_ads_line():
    assert anuncios.app_ads_line('pub-1234567890123456') == \
        'google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n'


def test_app_ads_txt_con_y_sin_id_de_editor(monkeypatch):
    app = FastAPI()
    app.include_router(anuncios.router)
    client = TestClient(app)
    monkeypatch.setattr(rewards, 'settings', lambda: CFG | {'admob_publisher_id': ''})
    assert client.get('/app-ads.txt').status_code == 404
    monkeypatch.setattr(rewards, 'settings', lambda: CFG | {'admob_publisher_id': 'pub-1234567890123456'})
    r = client.get('/app-ads.txt')
    assert r.status_code == 200 and r.headers['content-type'].startswith('text/plain')
    assert r.text == 'google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n'
