"""Panel /control/pantallas (src/qf/api/pantallas_panel.py), sin Postgres.

El almacén se sustituye por uno en memoria que aplica la MISMA `pantallas.validar` y las mismas reglas de nota de
`comercial/pantallas.py`: así se prueba que cada error de servidor llega tal cual al usuario, sin duplicarlo.
"""
import copy
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import console, panel, pantallas_panel
from qf.comercial import pantallas as pa

ES6 = {'es': 'Uno', 'en': 'One', 'pt': 'Um', 'fr': 'Un', 'it': 'Uno', 'de': 'Eins'}
CLAVE = {'pantalla': 'deporte', 'deporte': 'nba', 'cliente': 'app'}


@pytest.fixture
def cliente(monkeypatch):
    estado = {'borradores': {}, 'publicaciones': {}, 'llamadas': []}

    def k(p, d, c):
        return (p, d, c)

    def guardar(p, d, c, bloques, actor):
        pa.validar_clave(p, d, c)
        limpios = pa.validar(p, bloques)
        estado['borradores'][k(p, d, c)] = limpios
        estado['llamadas'].append(('guardar', k(p, d, c)))
        return limpios

    def publicar(p, d, c, nota, actor):
        pa._nota(nota)
        if k(p, d, c) not in estado['borradores']:
            raise ValueError('No hay borrador que publicar para esta clave: guárdalo primero.')
        lista = estado['publicaciones'].setdefault(k(p, d, c), [])
        lista.append({'version': len(lista) + 1, 'bloques': pa.validar(p, estado['borradores'][k(p, d, c)]),
                      'publicado_por': actor, 'publicado_en': datetime.now(timezone.utc), 'nota': nota.strip()})
        estado['llamadas'].append(('publicar', k(p, d, c)))
        return len(lista)

    def volver(p, d, c, version, nota, actor):
        pa._nota(nota)
        lista = estado['publicaciones'].get(k(p, d, c), [])
        origen = next((v for v in lista if v['version'] == version), None)
        if not origen:
            raise ValueError(f'La versión {version} no existe para esta clave.')
        lista.append({**copy.deepcopy(origen), 'version': len(lista) + 1, 'nota': nota.strip()})
        estado['llamadas'].append(('volver', k(p, d, c), version))
        return len(lista)

    monkeypatch.setattr(pa, 'guardar_borrador', guardar)
    monkeypatch.setattr(pa, 'publicar', publicar)
    monkeypatch.setattr(pa, 'volver_a', volver)
    monkeypatch.setattr(pa, 'borrador', lambda p, d, c: (
        {'bloques': estado['borradores'][k(p, d, c)]} if k(p, d, c) in estado['borradores'] else None))
    monkeypatch.setattr(pa, 'historial', lambda p, d, c: list(reversed(estado['publicaciones'].get(k(p, d, c), []))))
    monkeypatch.setattr(pa, 'claves', lambda: [
        {'pantalla': p, 'deporte': d, 'cliente': c, 'version': 1, 'publicado_en': datetime.now(timezone.utc),
         'tiene_borrador': True, 'difiere': True} for (p, d, c) in estado['borradores']])
    monkeypatch.setattr(pa, 'invalidar_cache', lambda: None)
    app = FastAPI()
    app.include_router(pantallas_panel.router)
    app.dependency_overrides[console.require_console] = lambda: 'tester'
    return TestClient(app, follow_redirects=False), panel.csrf_token('tester'), estado


def fila(i, tipo='seccion', seccion='', **kw):
    f = {f'b{i}_tipo': tipo, f'b{i}_seccion': seccion, f'b{i}_id': kw.pop('id', seccion), f'b{i}_orden': str(i + 1)}
    if kw.pop('visible', True):
        f[f'b{i}_visible'] = '1'
    for clave, valor in kw.items():
        f[f'b{i}_{clave}'] = valor
    return f


def formulario(csrf, filas, **extra):
    datos = {'csrf': csrf, **CLAVE, 'n': str(len(filas) + 1), **extra}
    for f in filas:
        datos.update(f)
    return datos


def buenas(csrf, **extra):
    return formulario(csrf, [fila(0, seccion='dias'), fila(1, seccion='partidos')], **extra)


def aviso(i, **kw):
    texto = {f't_{lg}': v for lg, v in ES6.items()}
    return fila(i, 'aviso', id='mant', tono='info', **texto, **kw)


def mensaje(resp):
    assert resp.status_code == 303
    q = parse_qs(urlsplit(resp.headers['location']).query)
    return q.get('m', [''])[0]


def test_sin_sesion_es_401(monkeypatch):
    monkeypatch.setenv('ADMIN_CONSOLE_USER', 'admin')
    monkeypatch.setenv('ADMIN_CONSOLE_PASSWORD_HASH', 'pbkdf2_sha256$600000$00$00')
    app = FastAPI()
    app.include_router(pantallas_panel.router)
    c = TestClient(app)
    for ruta in ('/control/pantallas', '/control/pantallas/editar?pantalla=deporte&deporte=*&cliente=web'):
        assert c.get(ruta).status_code == 401
    for ruta in ('guardar', 'validar', 'publicar', 'volver'):
        assert c.post(f'/control/pantallas/{ruta}', data={}).status_code == 401


def test_post_sin_csrf_es_403_y_no_toca_nada(cliente):
    c, _, estado = cliente
    for ruta in ('guardar', 'validar', 'publicar', 'volver'):
        assert c.post(f'/control/pantallas/{ruta}', data=buenas('malo', nota='n', version='1')).status_code == 403
    assert estado['llamadas'] == [] and estado['borradores'] == {}


def test_lista_y_editor_nuevo_parten_del_orden_natural(cliente):
    c, _, _ = cliente
    r = c.get('/control/pantallas')
    assert r.status_code == 200 and 'Abrir' in r.text and 'Todos (*)' in r.text
    r = c.get('/control/pantallas/editar', params={'pantalla': 'partido', 'deporte': '*', 'cliente': 'web'})
    assert r.status_code == 200 and 'Definición nueva' in r.text
    for s in pa.PANTALLAS['partido']:
        assert f'value="{s}"' in r.text
    for boton in ('Validar', 'Guardar borrador', 'Publicar', 'Historial'):
        assert boton in r.text


@pytest.mark.parametrize('params', [
    {'pantalla': 'otra', 'deporte': '*', 'cliente': 'web'}, {'pantalla': 'deporte', 'deporte': 'X!', 'cliente': 'web'},
    {'pantalla': 'deporte', 'deporte': '*', 'cliente': 'tv'}, {}])
def test_clave_invalida_es_404(cliente, params):
    assert cliente[0].get('/control/pantallas/editar', params=params).status_code == 404


def test_guardar_valido_crea_borrador_en_el_orden_pedido(cliente):
    c, csrf, estado = cliente
    datos = formulario(csrf, [fila(0, seccion='partidos'), fila(1, seccion='dias')])
    datos['b0_orden'], datos['b1_orden'] = '5', '1'                      # el orden se lee de la columna
    assert mensaje(c.post('/control/pantallas/guardar', data=datos)) == 'pantallas_guardada'
    guardado = estado['borradores'][('deporte', 'nba', 'app')]
    assert [b['seccion'] for b in guardado] == ['dias', 'partidos']
    # y el editor lo muestra ahora como borrador
    assert 'borrador guardado' in c.get('/control/pantallas/editar', params=CLAVE).text


def test_errores_de_validacion_se_muestran_tal_cual_y_no_guardan(cliente):
    c, csrf, estado = cliente
    casos = [
        (formulario(csrf, [fila(0, seccion='cabecera')]), 'La sección debe ser una de dias'),
        (formulario(csrf, [fila(0, seccion='dias', visible=False)]), 'al menos una sección visible'),
        (formulario(csrf, [fila(0, seccion='dias'), fila(1, seccion='partidos', id='dias')]), 'repetido'),
        (formulario(csrf, [fila(0, seccion='dias'), fila(1, 'aviso', id='x', t_es='solo es', tono='info')]), '6 idiomas'),
        (formulario(csrf, [fila(0, seccion='dias'), aviso(1, enlace='https://malo.com/')]), 'enlace'),
        (formulario(csrf, [fila(0, seccion='dias', build='abc')]), 'build_min_app'),
        (formulario(csrf, [fila(0, tipo='grafico', seccion='dias')]), 'tipo no válido'),
    ]
    for datos, parte in casos:
        for accion in ('validar', 'guardar', 'publicar'):
            r = c.post(f'/control/pantallas/{accion}', data={**datos, 'nota': 'n'})
            assert r.status_code == 422, (accion, parte)
            assert parte.lower() in r.text.lower().replace('&#39;', "'"), (accion, parte)
            assert 'alert-danger' in r.text
    assert estado['borradores'] == {} and estado['publicaciones'] == {}


def test_el_error_conserva_lo_que_el_usuario_escribio(cliente):
    c, csrf, _ = cliente
    datos = formulario(csrf, [fila(0, seccion='dias', visible=False), aviso(1)])
    r = c.post('/control/pantallas/validar', data=datos)
    assert r.status_code == 422 and 'value="mant"' in r.text and 'value="Eins"' in r.text


def test_validar_no_guarda_ni_publica(cliente):
    c, csrf, estado = cliente
    r = c.post('/control/pantallas/validar', data=buenas(csrf))
    assert r.status_code == 200 and 'Válido: 2 bloques' in r.text
    assert estado['llamadas'] == []


def test_publicar_exige_nota_y_no_guarda_sin_ella(cliente):
    c, csrf, estado = cliente
    for nota in ('', '   '):
        r = c.post('/control/pantallas/publicar', data=buenas(csrf, nota=nota))
        assert r.status_code == 422 and 'nota es obligatoria' in r.text
    assert estado['llamadas'] == [] and estado['borradores'] == {}
    assert mensaje(c.post('/control/pantallas/publicar', data=buenas(csrf, nota='Primera'))) == 'pantallas_publicada'
    assert estado['llamadas'] == [('guardar', ('deporte', 'nba', 'app')), ('publicar', ('deporte', 'nba', 'app'))]
    assert estado['publicaciones'][('deporte', 'nba', 'app')][0]['nota'] == 'Primera'


def test_historial_y_volver_a_una_version(cliente):
    c, csrf, estado = cliente
    c.post('/control/pantallas/publicar', data=buenas(csrf, nota='v1'))
    c.post('/control/pantallas/publicar', data=formulario(csrf, [fila(0, seccion='partidos')], nota='v2'))
    r = c.get('/control/pantallas/editar', params=CLAVE)
    assert 'Volver a esta versión' in r.text and 'vigente' in r.text and '<td>v2</td>' in r.text
    # sin nota: error visible y nada nuevo
    r = c.post('/control/pantallas/volver', data={'csrf': csrf, **CLAVE, 'version': '1', 'nota': ''})
    assert r.status_code == 422 and 'nota es obligatoria' in r.text
    assert len(estado['publicaciones'][('deporte', 'nba', 'app')]) == 2
    # versión inexistente
    r = c.post('/control/pantallas/volver', data={'csrf': csrf, **CLAVE, 'version': '9', 'nota': 'x'})
    assert r.status_code == 422 and 'no existe' in r.text
    # bien: crea la 3 con el contenido de la 1
    assert mensaje(c.post('/control/pantallas/volver',
                          data={'csrf': csrf, **CLAVE, 'version': '1', 'nota': 'volvemos'})) == 'pantallas_vuelta'
    lista = estado['publicaciones'][('deporte', 'nba', 'app')]
    assert [v['version'] for v in lista] == [1, 2, 3] and lista[2]['bloques'] == lista[0]['bloques']


def test_version_no_numerica_da_error_y_no_traza(cliente):
    c, csrf, _ = cliente
    r = c.post('/control/pantallas/volver', data={'csrf': csrf, **CLAVE, 'version': 'abc', 'nota': 'x'})
    assert r.status_code == 422 and 'Traceback' not in r.text


def test_aviso_completo_se_guarda_con_sus_seis_textos(cliente):
    c, csrf, estado = cliente
    datos = formulario(csrf, [fila(0, seccion='dias'), aviso(1, enlace='/planes/', build='12')])
    assert mensaje(c.post('/control/pantallas/guardar', data=datos)) == 'pantallas_guardada'
    a = estado['borradores'][('deporte', 'nba', 'app')][1]
    assert a['params'] == {'texto': ES6, 'tono': 'info', 'enlace': '/planes/'} and a['build_min_app'] == 12


def test_quitar_y_filas_en_blanco(cliente):
    c, csrf, estado = cliente
    datos = formulario(csrf, [fila(0, seccion='dias'), fila(1, seccion='partidos', quitar='1'),
                              fila(2, tipo='', seccion='')])
    assert mensaje(c.post('/control/pantallas/guardar', data=datos)) == 'pantallas_guardada'
    assert [b['id'] for b in estado['borradores'][('deporte', 'nba', 'app')]] == ['dias']


def test_el_menu_incluye_pantallas_en_web_y_app(cliente):
    c, _, _ = cliente
    r = c.get('/control/pantallas')
    assert 'href="/control/pantallas"' in r.text and r.text.index('Web y App') < r.text.index('href="/control/pantallas"')


def test_registrado_en_la_app_principal_y_el_icono_existe():
    from pathlib import Path

    from qf.api.main import app
    assert any(getattr(r, 'path', '') == '/control/pantallas' for r in app.routes)
    base = Path(pantallas_panel.__file__).parent / 'templates' / 'base.html'
    assert "'/control/pantallas', 'layout-dashboard'" in base.read_text(encoding='utf-8')
    assert (Path(pantallas_panel.__file__).parent / 'static' / 'vendor' / 'icons' / 'layout-dashboard.svg').exists()


# --- el mismo recorrido con Postgres real (db/113 aplicado; se omite sin QF_TEST_PG_DSN) -------------------

@pytest.mark.skipif(not __import__('os').getenv('QF_TEST_PG_DSN'), reason='sin QF_TEST_PG_DSN')
def test_recorrido_completo_con_postgres_real(monkeypatch):
    import os
    import uuid

    from psycopg_pool import ConnectionPool

    from qf import db
    monkeypatch.undo()
    pool = ConnectionPool(os.environ['QF_TEST_PG_DSN'], min_size=1, max_size=2, open=True)
    monkeypatch.setattr(db, '_pool', pool)
    pa.invalidar_cache()
    app = FastAPI()
    app.include_router(pantallas_panel.router)
    app.dependency_overrides[console.require_console] = lambda: 'tester'
    c, csrf = TestClient(app, follow_redirects=False), panel.csrf_token('tester')
    clave = {'pantalla': 'deporte', 'deporte': 'p' + uuid.uuid4().hex[:12], 'cliente': 'web'}
    try:
        datos = {**buenas(csrf, nota='Primera'), **clave}
        assert mensaje(c.post('/control/pantallas/publicar', data=datos)) == 'pantallas_publicada'
        datos2 = {**formulario(csrf, [fila(0, seccion='partidos')], nota='Segunda'), **clave}
        assert mensaje(c.post('/control/pantallas/publicar', data=datos2)) == 'pantallas_publicada'
        assert mensaje(c.post('/control/pantallas/volver',
                              data={'csrf': csrf, **clave, 'version': '1', 'nota': 'atrás'})) == 'pantallas_vuelta'
        assert [v['version'] for v in pa.historial(*clave.values())] == [3, 2, 1]
        assert [b['seccion'] for b in pa.resolver(*clave.values())] == ['dias', 'partidos']
        pagina = c.get('/control/pantallas/editar', params=clave)
        assert pagina.status_code == 200 and 'atrás' in pagina.text
        lista = c.get('/control/pantallas')
        assert clave['deporte'] in lista.text and 'versión 3' in lista.text
    finally:
        pa.invalidar_cache()
        pool.close()
