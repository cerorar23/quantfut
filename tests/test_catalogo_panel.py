"""Panel /control/deportes (src/qf/api/catalogo_panel.py), sin Postgres.

El catálogo y los guardados se sustituyen por una copia en memoria que aplica las MISMAS validaciones de
`comercial/catalogo.py` (`validar_deporte`, `validar_familia`, `_validar_conjunto`): así se prueba que cada guarda
llega al usuario como mensaje, sin duplicar las reglas en el panel.
"""
import copy
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import catalogo_panel, console, panel
from qf.comercial import catalogo
from qf.comercial.catalogo_semilla import SEMILLA


@pytest.fixture
def cliente(monkeypatch):
    estado = {'deportes': copy.deepcopy(catalogo._de_semilla()), 'llamadas': []}

    def todos():
        estado['deportes'].sort(key=lambda d: (d['orden'], d['deporte_id']))
        return copy.deepcopy(estado['deportes'])

    def guardar_deporte(deporte_id, datos, actor):
        estado['llamadas'].append(('deporte', deporte_id, datos))
        if 'deporte_id' in datos and datos['deporte_id'] != deporte_id:
            raise ValueError('El id del deporte no se puede cambiar.')
        actual = next(d for d in estado['deportes'] if d['deporte_id'] == deporte_id)
        nuevo = catalogo.validar_deporte({**actual, **datos})
        resto = [d for d in estado['deportes'] if d['deporte_id'] != deporte_id]
        catalogo._validar_conjunto(resto + [nuevo])
        actual.update({k: nuevo[k] for k in datos})

    def guardar_familia(deporte_id, familia_id, datos, actor):
        estado['llamadas'].append(('familia', deporte_id, familia_id, datos))
        dep = next(d for d in estado['deportes'] if d['deporte_id'] == deporte_id)
        fam = next(f for f in dep['familias'] if f['familia_id'] == familia_id)
        nueva = catalogo.validar_familia({**fam, **datos})
        fam.update({k: nueva[k] for k in datos})

    monkeypatch.setattr(catalogo, 'todos', todos)
    monkeypatch.setattr(catalogo, 'guardar_deporte', guardar_deporte)
    monkeypatch.setattr(catalogo, 'guardar_familia', guardar_familia)
    monkeypatch.setattr(catalogo, 'invalidar_cache', lambda: None)
    app = FastAPI()
    app.include_router(catalogo_panel.router)
    app.dependency_overrides[console.require_console] = lambda: 'tester'
    return TestClient(app), panel.csrf_token('tester'), estado


def formulario(csrf, **cambios):
    f = {'csrf': csrf, 'icono': 'futbol', 'color': '#22d3ee', 'secciones': ['high'],
         'estado_web': 'on', 'estado_app': 'on'}
    for lg in catalogo.IDIOMAS_APP:
        f[f'nombre_{lg}'] = f'Nombre {lg}'
    for lg in catalogo.IDIOMAS_WEB:
        f[f'slug_{lg}'] = 'deporte-x'
    f.update(cambios)
    return f


def mensaje(resp):
    assert resp.status_code == 303
    q = parse_qs(urlsplit(resp.headers['location']).query)
    return q.get('m', [''])[0], q.get('err', [''])[0]


def test_lista_y_edicion_responden_con_sesion(cliente):
    c, _, _ = cliente
    r = c.get('/control/deportes')
    assert r.status_code == 200 and 'Fútbol' in r.text and '/control/deportes/nba' in r.text
    r = c.get('/control/deportes/nba')
    assert r.status_code == 200 and 'buscadores verán un 404' in r.text and 'nombre_de' in r.text
    r = c.get('/control/deportes/nba/mercados')
    assert r.status_code == 200 and 'Guardar' in r.text
    assert c.get('/control/deportes/no_existe').status_code == 404


def test_sin_sesion_es_401(monkeypatch):
    monkeypatch.setenv('ADMIN_CONSOLE_USER', 'admin')
    monkeypatch.setenv('ADMIN_CONSOLE_PASSWORD_HASH', 'pbkdf2_sha256$600000$00$00')
    app = FastAPI()
    app.include_router(catalogo_panel.router)
    for ruta in ('/control/deportes', '/control/deportes/nba', '/control/deportes/nba/mercados'):
        assert TestClient(app).get(ruta).status_code == 401


def test_post_sin_csrf_es_403_y_no_guarda(cliente):
    c, _, estado = cliente
    assert c.post('/control/deportes/nba', data=formulario('malo')).status_code == 403
    assert c.post('/control/deportes/nba/orden', data={'csrf': 'malo', 'sentido': 'subir'}).status_code == 403
    assert c.post('/control/deportes/nba/traducir', data={'csrf': 'malo'}).status_code == 403
    assert estado['llamadas'] == []


def test_edicion_valida_guarda(cliente):
    c, csrf, estado = cliente
    r = c.post('/control/deportes/nba', data=formulario(csrf, color='#AABBCC'), follow_redirects=False)
    assert mensaje(r)[0] == 'catalogo_guardado'
    nba = next(d for d in estado['deportes'] if d['deporte_id'] == 'nba')
    assert nba['color'] == '#aabbcc' and nba['nombre']['de'] == 'Nombre de'


def test_guarda_ultimo_deporte_on_de_un_cliente(cliente):
    c, csrf, estado = cliente
    for d in estado['deportes']:
        if d['deporte_id'] != 'nba':
            d['estado_web'] = 'off'
    r = c.post('/control/deportes/nba', data=formulario(csrf, estado_web='off'), follow_redirects=False)
    m, err = mensaje(r)
    assert m == 'catalogo_error' and 'sin ningún deporte' in err


def test_guarda_sin_adaptador_solo_off(cliente):
    c, csrf, estado = cliente
    estado['deportes'][2]['adaptador'] = None
    r = c.post('/control/deportes/tenis', data=formulario(csrf), follow_redirects=False)
    m, err = mensaje(r)
    assert m == 'catalogo_error' and 'sin adaptador' in err


def test_guarda_falta_un_idioma(cliente):
    c, csrf, _ = cliente
    r = c.post('/control/deportes/nba', data=formulario(csrf, nombre_de=''), follow_redirects=False)
    m, err = mensaje(r)
    assert m == 'catalogo_error' and '«de»' in err


def test_guarda_slug_y_color_invalidos(cliente):
    c, csrf, _ = cliente
    assert 'Slug' in mensaje(c.post('/control/deportes/nba', data=formulario(csrf, slug_es='Mal Slug'),
                                    follow_redirects=False))[1]
    assert 'color' in mensaje(c.post('/control/deportes/nba', data=formulario(csrf, color='rojo'),
                                     follow_redirects=False))[1]


def test_icono_fuera_de_la_lista_se_rechaza(cliente):
    c, csrf, estado = cliente
    r = c.post('/control/deportes/nba', data=formulario(csrf, icono='pelota'), follow_redirects=False)
    assert mensaje(r)[0] == 'catalogo_error' and estado['llamadas'] == []


def test_el_panel_no_ofrece_cambiar_el_deporte_id(cliente):
    c, csrf, estado = cliente
    assert 'name="deporte_id"' not in c.get('/control/deportes/nba').text
    c.post('/control/deportes/nba', data=formulario(csrf, deporte_id='otro'), follow_redirects=False)
    _, _, datos = estado['llamadas'][-1]
    assert 'deporte_id' not in datos


def test_orden_intercambia_con_el_vecino(cliente):
    c, csrf, estado = cliente
    r = c.post('/control/deportes/nba/orden', data={'csrf': csrf, 'sentido': 'subir'}, follow_redirects=False)
    assert mensaje(r)[0] == 'catalogo_guardado'
    orden = {d['deporte_id']: d['orden'] for d in estado['deportes']}
    assert orden['nba'] == 1 and orden['futbol'] == 2 and orden['tenis'] == 3
    r = c.post('/control/deportes/nba/orden', data={'csrf': csrf, 'sentido': 'bajar'}, follow_redirects=False)
    assert {d['deporte_id']: d['orden'] for d in estado['deportes']}['nba'] == 2


def test_orden_en_los_extremos_no_cambia_nada(cliente):
    c, csrf, estado = cliente
    r = c.post('/control/deportes/futbol/orden', data={'csrf': csrf, 'sentido': 'subir'}, follow_redirects=False)
    assert mensaje(r)[0] == 'sin_cambios' and estado['llamadas'] == []
    assert c.post('/control/deportes/nba/orden', data={'csrf': csrf, 'sentido': 'lateral'}).status_code == 422


def test_orden_con_empate_mueve_solo_al_elegido(cliente):
    c, csrf, estado = cliente
    for d in estado['deportes']:
        d['orden'] = 5
    c.post('/control/deportes/nba/orden', data={'csrf': csrf, 'sentido': 'subir'}, follow_redirects=False)
    assert {d['deporte_id']: d['orden'] for d in estado['deportes']}['nba'] == 4


def test_mercados_guardan_y_validan(cliente):
    c, csrf, estado = cliente
    fam = estado['deportes'][1]['familias'][0]
    ruta = f"/control/deportes/nba/mercados/{fam['familia_id']}"
    datos = {'csrf': csrf, 'orden': '7', 'visible_web': '1'}
    datos.update({f'nombre_{lg}': f'N {lg}' for lg in catalogo.IDIOMAS_APP})
    r = c.post(ruta, data=datos, follow_redirects=False)
    assert mensaje(r)[0] == 'catalogo_guardado'
    assert (fam['orden'], fam['visible_web'], fam['visible_app']) == (7, True, False)
    assert mensaje(c.post(ruta, data={**datos, 'orden': 'x'}, follow_redirects=False))[1] == 'El orden debe ser un entero.'
    assert 'falta el texto' in mensaje(c.post(ruta, data={**datos, 'nombre_fr': ''}, follow_redirects=False))[1]
    assert c.post('/control/deportes/nba/mercados/inventada', data=datos).status_code == 404


def test_traducir_sin_clave_muestra_el_mensaje_de_apimart(cliente, monkeypatch):
    c, csrf, _ = cliente
    from qf.api import web_config
    monkeypatch.setattr(web_config, 'get_apimart_runtime_config',
                        lambda: {'api_key': '', 'base_url': 'https://x', 'model': 'm'})
    r = c.post('/control/deportes/nba/traducir', data={'csrf': csrf}, follow_redirects=False)
    m, err = mensaje(r)
    assert m == 'catalogo_error' and 'clave API de APIMart' in err


def test_traducir_guarda_fr_it_de(cliente, monkeypatch):
    c, csrf, estado = cliente
    from qf.api import apimart, web_config
    monkeypatch.setattr(web_config, 'get_apimart_runtime_config',
                        lambda: {'api_key': 'k', 'base_url': 'https://x', 'model': 'm'})
    monkeypatch.setattr(apimart, '_chat_completion',
                        lambda **kw: {'content': '{"fr":"Basket","it":"Pallacanestro","de":"Basketball"}'})
    r = c.post('/control/deportes/nba/traducir', data={'csrf': csrf}, follow_redirects=False)
    assert mensaje(r)[0] == 'catalogo_traducido'
    nba = next(d for d in estado['deportes'] if d['deporte_id'] == 'nba')
    assert nba['nombre']['it'] == 'Pallacanestro' and nba['nombre']['es'] == SEMILLA[1]['nombre']['es']


def test_menu_enlaza_deportes_y_mensajes_existen(cliente):
    c, _, _ = cliente
    assert '/control/deportes' in c.get('/control/deportes').text
    for clave in ('catalogo_guardado', 'catalogo_traducido', 'catalogo_error'):
        assert clave in panel._MENSAJES
