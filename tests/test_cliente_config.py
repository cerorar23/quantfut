"""`GET /cliente/v1/config` (parte B de la Fase 1): forma, 422, idioma apagado, ETag/304, lista blanca y centinelas.

La clasificación de columnas usa Postgres real y se omite sin `QF_TEST_PG_DSN` (corre en CI). Nunca apuntarlo a producción.
"""
from __future__ import annotations

import copy
import os
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from qf.api import cliente_config as cc
from qf.api import idiomas, mobile, ratelimit, rutas_web, web_config
from qf.api.main import app
from qf.comercial import acceso_reglas as ar
from qf.comercial import cifrado, mobile_updates

DSN = os.getenv('QF_TEST_PG_DSN')
pg = pytest.mark.skipif(not DSN, reason='sin QF_TEST_PG_DSN')
RUTA = '/cliente/v1/config'

FEATURES = {k: {'section': k, 'enabled': True, 'message': f'msg {k}', 'updated_at': 'PRIV_FEAT_UPDATED'}
            for k in mobile.SECTIONS}


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    archivo = tmp_path / 'activos.txt'
    archivo.write_text('en = off\npt = off\n', encoding='utf-8')
    monkeypatch.setenv('IDIOMAS_ARCHIVO', str(archivo))
    monkeypatch.setenv('QF_SECRETS_KEY', cifrado.generar_clave())
    monkeypatch.setattr(ratelimit, 'rate_limited', lambda *a, **k: False)
    monkeypatch.setattr(web_config, '_db_reachable', lambda: False)
    monkeypatch.setattr(mobile_updates, 'configuration', lambda: dict(mobile_updates.DEFAULTS))
    monkeypatch.setattr(mobile, 'features', lambda: copy.deepcopy(FEATURES))
    idiomas.olvidar()
    web_config.invalidar_cache()
    rutas_web._leido = None
    yield TestClient(app), archivo
    idiomas.olvidar()
    web_config.invalidar_cache()


def test_forma_app(cliente):
    r = cliente[0].get(RUTA, params={'cliente': 'app'})
    assert r.status_code == 200
    b = r.json()
    assert set(b) == {'contrato', 'cliente', 'lang', 'general', 'idiomas', 'acceso', 'app'}
    assert b['contrato'] == 0 and b['cliente'] == 'app' and b['lang'] == 'es'
    assert set(b['app']) == {'versiones', 'secciones'}
    assert set(b['app']['versiones']) == set(mobile_updates.DEFAULTS) and len(b['app']['versiones']) == 7
    assert set(b['app']['secciones']) == set(mobile.SECTIONS)
    assert b['app']['secciones']['agenda'] == {'enabled': True, 'message': 'msg agenda'}
    assert b['acceso'] == {'probability_min': .73, 'probability_max': .95, 'high_probability_free_fraction': .10,
                           'ladder_free_count': 1, 'dias_agenda': 7}
    assert set(b['general']) == {'brand_name', 'legal_name', 'hero_badge', 'support_email', 'disclaimer_text',
                                 'maintenance_banner', 'social'}
    assert set(b['idiomas']) == {'selector', 'estados'} and b['idiomas']['estados']['es'] == 'on'
    assert 'server_time' not in r.text
    assert r.headers['cache-control'] == 'no-cache'


def test_forma_web(cliente):
    r = cliente[0].get(RUTA, params={'cliente': 'web'})
    b = r.json()
    assert set(b) == {'contrato', 'cliente', 'lang', 'general', 'idiomas', 'acceso', 'web'}
    assert set(b['web']) == {'ui', 'sections'} and b['web']['ui']
    max_age = web_config.get_settings()['public_cache_seconds']
    assert r.headers['cache-control'] == f'public, max-age={max_age}'


def test_cliente_obligatorio_y_enumerado(cliente):
    c = cliente[0]
    assert c.get(RUTA).status_code == 422
    assert c.get(RUTA, params={'cliente': 'tv'}).status_code == 422


@pytest.mark.parametrize('lang', ['EN', 'e', 'eng', 'e1', '../x'])
def test_lang_con_formato_invalido_da_422(cliente, lang):
    assert cliente[0].get(RUTA, params={'cliente': 'web', 'lang': lang}).status_code == 422


def test_idioma_apagado_o_desconocido_se_sirve_como_es(cliente):
    c, archivo = cliente
    for lang in ('en', 'fr'):
        assert c.get(RUTA, params={'cliente': 'web', 'lang': lang}).json()['lang'] == 'es'
    archivo.write_text('en = on\npt = off\n', encoding='utf-8')
    idiomas.olvidar()
    b = c.get(RUTA, params={'cliente': 'web', 'lang': 'en'}).json()
    assert b['lang'] == 'en' and b['idiomas']['estados']['en'] == 'on'
    assert c.get(RUTA, params={'cliente': 'web', 'lang': 'pt'}).json()['lang'] == 'es'


def test_etag_y_304(cliente):
    c = cliente[0]
    r = c.get(RUTA, params={'cliente': 'app'})
    etag = r.headers['etag']
    assert etag.startswith('W/"') and len(etag) == 3 + 64 + 1
    assert c.get(RUTA, params={'cliente': 'app'}).headers['etag'] == etag
    r2 = c.get(RUTA, params={'cliente': 'app'}, headers={'If-None-Match': etag})
    assert r2.status_code == 304 and r2.content == b'' and r2.headers['etag'] == etag
    assert c.get(RUTA, params={'cliente': 'app'}, headers={'If-None-Match': 'W/"otro", ' + etag}).status_code == 304
    assert c.get(RUTA, params={'cliente': 'app'}, headers={'If-None-Match': 'W/"otro"'}).status_code == 200
    assert c.get(RUTA, params={'cliente': 'web'}).headers['etag'] != etag


def test_el_etag_cambia_con_el_contenido(cliente, monkeypatch):
    c = cliente[0]
    antes = c.get(RUTA, params={'cliente': 'app'}).headers['etag']
    monkeypatch.setattr(mobile_updates, 'configuration',
                        lambda: {**mobile_updates.DEFAULTS, 'force_update_app': True})
    r = c.get(RUTA, params={'cliente': 'app'}, headers={'If-None-Match': antes})
    assert r.status_code == 200 and r.headers['etag'] != antes


def test_ignora_authorization_y_cookies(cliente):
    c = cliente[0]
    base = c.get(RUTA, params={'cliente': 'app'})
    con = c.get(RUTA, params={'cliente': 'app'}, headers={'Authorization': 'Bearer algo'},
                cookies={'qf_session': 'x'})
    assert con.status_code == 200 and con.content == base.content and con.headers['etag'] == base.headers['etag']


def test_modelo_rechaza_campos_no_declarados():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        cc.Acceso(probability_min=.7, probability_max=.9, high_probability_free_fraction=.1,
                  ladder_free_count=1, dias_agenda=7, nota='privada')


# --- centinelas: ningún valor privado aparece en los tres endpoints públicos ---------------------------

def test_centinelas_no_salen_en_ningun_endpoint_publico(cliente, monkeypatch):
    c, archivo = cliente
    archivo.write_text('en = on\npt = on\n', encoding='utf-8')
    idiomas.olvidar()
    cfg = web_config.get_settings()
    cfg.update(apimart_base_url='PRIV_apimart_base_url', apimart_model='PRIV_apimart_model',
               apimart_key_enc='PRIV_apimart_key_enc', default_robots='PRIV_default_robots',
               content_signal='PRIV_content_signal', updated_by='PRIV_wsettings_updated_by')
    monkeypatch.setattr(web_config, 'get_settings', lambda **k: copy.deepcopy(cfg))
    monkeypatch.setattr(mobile_updates, 'configuration',
                        lambda: {**mobile_updates.DEFAULTS, 'id': 'PRIV_mus_id', 'updated_at': 'PRIV_mus_updated'})
    hoy = ar.hoy_utc()
    reglas = [ar.Regla(1, date(2000, 1, 1), .73, .95, .10, 'PRIV_creado_por_hoy', None, 'PRIV_nota_hoy'),
              ar.Regla(2, hoy + timedelta(days=1), .80, .90, .33, 'PRIV_creado_por_futura', None, 'PRIV_nota_futura')]
    monkeypatch.setattr(ar, '_cargar', lambda: reglas)
    ar.invalidar_cache()
    # /mobile/v1/config conserva su salida de hoy: ahí `features` lleva `updated_at` y `configuration()` filtra las
    # columnas con su propio SELECT (lo cubre la prueba con Postgres real), así que esos dos centinelas no aplican.
    solo_nuevo = ('PRIV_FEAT_', 'PRIV_mus_')
    for url in (f'{RUTA}?cliente=app', f'{RUTA}?cliente=web&lang=en', f'{RUTA}?cliente=web&lang=pt',
                '/web/config', '/mobile/v1/config'):
        r = c.get(url)
        assert r.status_code == 200, url
        texto = r.text
        if url == '/mobile/v1/config':
            texto = texto.replace('PRIV_FEAT_UPDATED', '').replace('PRIV_mus_id', '').replace('PRIV_mus_updated', '')
        assert 'PRIV_' not in texto, url
        if url != '/mobile/v1/config':
            assert not any(x in r.text for x in solo_nuevo), url
        assert '0.33' not in r.text and '"regla_id"' not in r.text, url


@pg
def test_centinelas_con_postgres_real(monkeypatch, cliente):
    from psycopg_pool import ConnectionPool
    from qf import db
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    monkeypatch.undo()   # quita los parches del fixture: lectura real de web_site_settings y mobile_*
    monkeypatch.setattr(db, '_pool', pool)
    monkeypatch.setattr(ratelimit, 'rate_limited', lambda *a, **k: False)
    idiomas.olvidar()
    c = TestClient(app)
    web_config.invalidar_cache()
    cols = ['apimart_base_url', 'apimart_model', 'apimart_key_enc', 'default_robots', 'content_signal', 'updated_by']
    with pool.connection() as k:
        previo = k.execute(f"SELECT {', '.join(cols)} FROM web_site_settings WHERE id=1").fetchone()
    try:
        with pool.connection() as k:
            k.execute('UPDATE web_site_settings SET ' + ', '.join(f"{x}='PRIV_{x}'" for x in cols) + ' WHERE id=1')
        web_config.invalidar_cache()
        for url in (f'{RUTA}?cliente=app', f'{RUTA}?cliente=web', '/web/config', '/mobile/v1/config'):
            assert 'PRIV_' not in c.get(url).text, url
    finally:
        with pool.connection() as k:
            vals = previo if isinstance(previo, tuple) else tuple(previo[x] for x in cols)
            k.execute('UPDATE web_site_settings SET ' + ', '.join(f'{x}=%s' for x in cols) + ' WHERE id=1', vals)
        web_config.invalidar_cache()
        pool.close()
        idiomas.olvidar()


# --- clasificación de columnas (Postgres real) ---------------------------------------------------------

@pg
def test_toda_columna_real_esta_clasificada():
    import psycopg
    with psycopg.connect(DSN) as k:
        for tabla in cc.PUBLICAS:
            reales = {r[0] for r in k.execute(
                'SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() '
                'AND table_name = %s', (tabla,))}
            assert reales, f'{tabla} no existe: aplica db/*.sql'
            solape = cc.PUBLICAS[tabla] & cc.PRIVADAS[tabla]
            assert not solape, f'{tabla}: columnas en ambas listas {sorted(solape)}'
            sin = reales - cc.PUBLICAS[tabla] - cc.PRIVADAS[tabla]
            assert not sin, f'{tabla}: columnas sin clasificar como pública o privada: {sorted(sin)}'
            fantasma = (cc.PUBLICAS[tabla] | cc.PRIVADAS[tabla]) - reales
            assert not fantasma, f'{tabla}: clasificadas pero inexistentes: {sorted(fantasma)}'


def test_las_listas_cubren_las_cinco_tablas():
    assert set(cc.PUBLICAS) == set(cc.PRIVADAS) == {
        'web_site_settings', 'mobile_update_settings', 'mobile_features', 'acceso_reglas', 'cliente_ajustes'}


# --- arreglo de la parte A: valores no finitos ---------------------------------------------------------

@pytest.mark.parametrize('valor', ['inf', '-inf', 'nan', float('inf'), float('nan')])
def test_validar_rechaza_no_finitos_con_mensaje_claro(valor):
    manana = ar.manana_utc()
    for args in [(valor, '0.95', '0.10'), ('0.73', valor, '0.10'), ('0.73', '0.95', valor)]:
        with pytest.raises(ValueError, match='finitos'):
            ar.validar(*args, manana, 'ok')
