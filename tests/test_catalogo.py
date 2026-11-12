"""Catálogo de deportes y mercados (db/112).

Sin base: validaciones, forma de `deportes_para`, semilla, respaldo ante tabla ausente, `exigir_web` y el asset de
la app. Con Postgres real (`QF_TEST_PG_DSN`, nunca producción; corren en CI): guardado, auditoría y las tres guardas.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from psycopg.errors import UndefinedTable

from qf.comercial import catalogo as cat
from qf.comercial.catalogo_semilla import SEMILLA

RAIZ = Path(__file__).resolve().parents[1]
ES6 = {'es': 'Uno', 'en': 'One', 'pt': 'Um', 'fr': 'Un', 'it': 'Uno', 'de': 'Eins'}
SLUG3 = {'es': 'hockey', 'en': 'hockey', 'pt': 'hoquei'}


def dep(**kw):
    base = {'deporte_id': 'hockey', 'adaptador': None, 'orden': 4, 'icono': 'hockey', 'color': '#aabbcc',
            'secciones': ['high'], 'nombre': dict(ES6), 'slug': dict(SLUG3), 'estado_web': 'off', 'estado_app': 'off'}
    base.update(kw)
    return base


def fijar(monkeypatch, deportes):
    monkeypatch.setattr(cat, '_cargar', lambda: cat._ordenar(copy.deepcopy(deportes)))
    cat.invalidar_cache()


# ── validación ──────────────────────────────────────────────────────────────

def test_validar_deporte_acepta_lo_correcto_y_rechaza_cada_regla():
    assert cat.validar_deporte(dep())['deporte_id'] == 'hockey'
    malos = [dep(deporte_id='1x'), dep(deporte_id='A'), dep(deporte_id='x' * 25), dep(adaptador='golf'),
             dep(color='#AABBCC'), dep(color='rojo'), dep(secciones=['high', 'otra']),
             dep(estado_web='visible'), dep(slug={'es': 'a', 'en': 'b'}), dep(slug={**SLUG3, 'pt': 'Hoquei'}),
             dep(slug={**SLUG3, 'es': 'a b'}), dep(orden='1'),
             dep(nombre={**ES6, 'de': ''}), dep(nombre={k: v for k, v in ES6.items() if k != 'fr'}),
             dep(nombre={**ES6, 'es': 'x' * 41}),
             dep(adaptador=None, estado_app='preview')]      # sin adaptador solo off
    for m in malos:
        with pytest.raises(ValueError):
            cat.validar_deporte(m)
    assert cat.validar_deporte(dep(nombre={**ES6, 'es': 'x' * 40}))
    assert cat.validar_deporte(dep(adaptador='nba', estado_web='on'))['adaptador'] == 'nba'


def test_validar_familia():
    f = {'familia_id': 'winner', 'orden': 1, 'nombre': dict(ES6), 'subtitulo': {}, 'visible_web': True,
         'visible_app': True}
    assert cat.validar_familia(f)['subtitulo'] == {}
    for m in [{**f, 'familia_id': 'Win'}, {**f, 'nombre': {**ES6, 'it': ' '}}, {**f, 'visible_web': 1},
              {**f, 'subtitulo': {'es': 'x' * 121}}, {**f, 'subtitulo': {'ru': 'x'}}]:
        with pytest.raises(ValueError):
            cat.validar_familia(m)


def test_la_semilla_es_valida_y_fiel_a_lo_de_hoy():
    assert [d['deporte_id'] for d in SEMILLA] == ['futbol', 'nba', 'tenis']
    for d in SEMILLA:
        assert cat.validar_deporte(d)
        assert d['adaptador'] == d['deporte_id'] and d['estado_web'] == d['estado_app'] == 'on'
        for f in d['familias']:
            assert cat.validar_familia(f)
    por = {d['deporte_id']: d for d in SEMILLA}
    assert [d['orden'] for d in SEMILLA] == [1, 2, 3]
    assert por['futbol']['secciones'] == ['high', 'ladder', 'parley']
    assert por['nba']['secciones'] == por['tenis']['secciones'] == ['high']
    assert (por['futbol']['color'], por['nba']['color'], por['tenis']['color']) == ('#22d3ee', '#b58cff', '#d4f53c')
    assert por['futbol']['slug'] == {'es': 'futbol', 'en': 'futbol', 'pt': 'futebol'}
    assert [f['familia_id'] for f in por['nba']['familias']] == [
        'winner', 'handicap', 'game_total', 'team_points', 'player_points', 'player_rebounds', 'player_assists',
        'player_threes']
    assert len(por['futbol']['familias']) == 8 and len(por['tenis']['familias']) == 6


# ── lectura ─────────────────────────────────────────────────────────────────

def test_deportes_para_web_y_app_tienen_la_forma_del_contrato():
    web, app = cat.deportes_para('web'), cat.deportes_para('app')
    assert [d['id'] for d in web] == [d['id'] for d in app] == ['futbol', 'nba', 'tenis']
    for d in web:
        assert set(d) == {'id', 'orden', 'estado', 'nombre', 'slug', 'icono', 'color', 'secciones', 'familias'}
        assert set(d['nombre']) == {'es', 'en', 'pt'} and set(d['slug']) == {'es', 'en', 'pt'}
        assert set(d['familias'][0]) == {'id', 'orden', 'nombre', 'subtitulo'}
    assert set(app[0]['nombre']) == set(cat.IDIOMAS_APP)
    assert set(app[0]['familias'][0]['nombre']) == set(cat.IDIOMAS_APP)
    assert app[1]['familias'][0]['subtitulo'] == {}          # NBA no trae subtítulos


def test_deportes_para_filtra_por_cliente_y_ordena(monkeypatch):
    base = copy.deepcopy(cat._de_semilla())
    base[0]['estado_web'] = 'off'
    base[1]['estado_app'] = 'preview'
    base[2]['orden'] = 0
    base[1]['familias'][0]['visible_app'] = False
    fijar(monkeypatch, base)
    assert [d['id'] for d in cat.deportes_para('web')] == ['tenis', 'nba']
    app = cat.deportes_para('app')
    assert [d['id'] for d in app] == ['tenis', 'futbol', 'nba']
    nba = app[2]
    assert nba['estado'] == 'preview' and 'winner' not in [f['id'] for f in nba['familias']]
    assert 'winner' in [f['id'] for f in cat.deportes_para('web')[1]['familias']]
    with pytest.raises(ValueError):
        cat.deportes_para('otro')


def test_deportes_para_no_filtra_campos_privados():
    texto = json.dumps([cat.deportes_para('web'), cat.deportes_para('app')])
    for privado in ('adaptador', 'updated_by', 'updated_at', 'estado_web', 'estado_app', 'visible_'):
        assert privado not in texto


def test_sin_tabla_o_con_tabla_vacia_se_sirve_la_semilla(monkeypatch):
    monkeypatch.setattr(cat, '_cargar', cat._cargar_real)    # la lectura real, sin el parche de conftest
    for resultado in (UndefinedTable('no existe'), []):
        def consulta(*a, _r=resultado, **k):
            if isinstance(_r, Exception):
                raise _r
            return _r
        monkeypatch.setattr(cat, 'query', consulta)
        cat.invalidar_cache()
        assert [d['id'] for d in cat.deportes_para('app')] == ['futbol', 'nba', 'tenis']
        assert cat.web_estado('nba') == 'on'


def test_web_estado_y_exigir_web(monkeypatch):
    base = copy.deepcopy(cat._de_semilla())
    base[1]['estado_web'] = 'preview'
    base[2]['estado_web'] = 'off'
    fijar(monkeypatch, base)
    assert (cat.web_estado('futbol'), cat.web_estado('nba'), cat.web_estado('tenis'), cat.web_estado('zzz')) == \
           ('on', 'preview', 'off', 'off')
    app = FastAPI()
    for d in ('futbol', 'nba', 'tenis', 'zzz'):
        app.add_api_route(f'/{d}', lambda: {'ok': 1}, dependencies=[Depends(cat.exigir_web(d))])
    c = TestClient(app)
    r = c.get('/futbol')
    assert r.status_code == 200 and 'x-robots-tag' not in r.headers
    r = c.get('/nba')
    assert r.status_code == 200 and r.headers['x-robots-tag'] == 'noindex'
    assert c.get('/tenis').status_code == 404 and c.get('/zzz').status_code == 404


def test_la_cache_dura_y_se_invalida(monkeypatch):
    llamadas = []
    monkeypatch.setattr(cat, '_cargar', lambda: llamadas.append(1) or cat._de_semilla())
    cat.invalidar_cache()
    cat.todos()
    cat.deportes_para('web')
    assert len(llamadas) == 1
    cat.invalidar_cache()
    cat.todos()
    assert len(llamadas) == 2


def test_todos_devuelve_copia_con_los_campos_del_panel():
    t = cat.todos()
    assert t[0]['adaptador'] == 'futbol' and 'estado_web' in t[0] and 'updated_by' in t[0]
    t[0]['nombre']['es'] = 'MUTADO'
    assert cat.todos()[0]['nombre']['es'] == 'Fútbol'


def test_conjunto_sin_deporte_on_se_rechaza():
    base = cat._de_semilla()
    cat._validar_conjunto(base)
    for d in base:
        d['estado_app'] = 'preview'
    with pytest.raises(ValueError, match='app'):
        cat._validar_conjunto(base)


# ── asset de la app ─────────────────────────────────────────────────────────

def test_el_asset_de_la_app_coincide_con_la_semilla():
    ruta = RAIZ / 'apps' / 'mobile' / 'assets' / 'model' / 'cliente_config_defecto.json'
    esperado = {'deportes': cat.deportes_para_semilla('app')}
    assert json.loads(ruta.read_text(encoding='utf-8')) == esperado, \
        'Regenera: python scripts/generar_catalogo_defecto.py'
    spec = importlib.util.spec_from_file_location('gen', RAIZ / 'scripts' / 'generar_catalogo_defecto.py')
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    assert ruta.read_bytes() == gen.contenido().encode('utf-8')


# ── Postgres real ───────────────────────────────────────────────────────────
DSN = os.getenv('QF_TEST_PG_DSN')
pg = pytest.mark.skipif(not DSN, reason='sin QF_TEST_PG_DSN')


@pytest.fixture
def base(monkeypatch):
    from psycopg_pool import ConnectionPool
    from qf import db
    pool = ConnectionPool(DSN, min_size=1, max_size=3, open=True)
    monkeypatch.setattr(db, '_pool', pool)
    monkeypatch.setattr(cat, '_cargar', cat._cargar_real)
    with db.conn() as c:
        c.execute('TRUNCATE deporte_mercados, deportes')
    cat.invalidar_cache()
    yield db
    with db.conn() as c:
        c.execute('TRUNCATE deporte_mercados, deportes')
    cat.invalidar_cache()
    pool.close()


@pg
def test_ensure_seeded_solo_con_tabla_vacia_y_es_idempotente(base):
    assert cat.ensure_seeded() is True and cat.ensure_seeded() is False
    assert [d['deporte_id'] for d in cat.todos()] == ['futbol', 'nba', 'tenis']
    assert cat.deportes_para('app') == cat.deportes_para_semilla('app')
    assert base.query('SELECT count(*) AS n FROM deporte_mercados')[0]['n'] == 22


@pg
def test_guardar_deporte_audita_antes_y_despues_y_respeta_las_guardas(base):
    cat.ensure_seeded()
    cat.guardar_deporte('nba', {'estado_app': 'off', 'nombre': {**ES6, 'es': 'Baloncesto'}}, 'admin@test')
    nba = next(d for d in cat.todos() if d['deporte_id'] == 'nba')
    assert nba['estado_app'] == 'off' and nba['nombre']['es'] == 'Baloncesto' and nba['updated_by'] == 'admin@test'
    assert [d['id'] for d in cat.deportes_para('app')] == ['futbol', 'tenis']
    fila = base.query("SELECT detail FROM admin_audit WHERE action='catalogo:deporte' ORDER BY audit_id DESC LIMIT 1")[0]
    assert fila['detail']['antes']['estado_app'] == 'on' and fila['detail']['despues']['estado_app'] == 'off'
    # guarda 1: ningún cliente sin un deporte on
    cat.guardar_deporte('futbol', {'estado_app': 'off'}, 'a')
    with pytest.raises(ValueError, match='app'):
        cat.guardar_deporte('tenis', {'estado_app': 'preview'}, 'a')
    assert next(d for d in cat.todos() if d['deporte_id'] == 'tenis')['estado_app'] == 'on'
    # guarda 2: sin adaptador solo off
    with pytest.raises(ValueError, match='adaptador'):
        cat.guardar_deporte('hockey', dep(estado_web='preview'), 'a')
    cat.guardar_deporte('hockey', dep(), 'a')
    assert 'hockey' in [d['deporte_id'] for d in cat.todos()]
    assert 'hockey' not in [d['id'] for d in cat.deportes_para('web')]
    with pytest.raises(ValueError, match='adaptador'):
        cat.guardar_deporte('hockey', {'estado_web': 'on'}, 'a')
    # guarda 3: id inmutable
    with pytest.raises(ValueError, match='id'):
        cat.guardar_deporte('hockey', {'deporte_id': 'otro'}, 'a')


@pg
def test_guardar_familia_audita_y_exige_deporte(base):
    cat.ensure_seeded()
    cat.guardar_familia('nba', 'winner', {'visible_app': False, 'orden': 9}, 'a')
    app_nba = next(d for d in cat.deportes_para('app') if d['id'] == 'nba')
    assert 'winner' not in [f['id'] for f in app_nba['familias']]
    cat.guardar_familia('nba', 'blocks', {'nombre': dict(ES6)}, 'a')
    nba = next(d for d in cat.todos() if d['deporte_id'] == 'nba')
    assert 'blocks' in [f['familia_id'] for f in nba['familias']]
    fila = base.query("SELECT detail FROM admin_audit WHERE action='catalogo:familia' ORDER BY audit_id DESC LIMIT 1")[0]
    assert fila['detail']['antes'] is None and fila['detail']['despues']['visible_web'] is True
    with pytest.raises(ValueError, match='no existe'):
        cat.guardar_familia('zzz', 'winner', {'nombre': dict(ES6)}, 'a')


@pg
def test_las_restricciones_de_sql_rechazan_lo_invalido(base):
    import psycopg
    cat.ensure_seeded()
    with pytest.raises(psycopg.errors.CheckViolation):      # sin adaptador no puede estar on
        with base.conn() as c:
            c.execute("INSERT INTO deportes (deporte_id, color, nombre, slug, orden, estado_web) "
                      "VALUES ('xx', '#000000', '{}', '{}', 9, 'on')")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with base.conn() as c:
            c.execute("INSERT INTO deporte_mercados (deporte_id, familia_id, orden, nombre) "
                      "VALUES ('nada', 'winner', 1, '{}')")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):  # ON DELETE RESTRICT
        with base.conn() as c:
            c.execute("DELETE FROM deportes WHERE deporte_id='nba'")
