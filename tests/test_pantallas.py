"""Definición de pantallas por bloques (db/113, src/qf/comercial/pantallas.py).

La validación, `resolver` y `para_entrega` corren sin base (sustituyen `_cargar`); publicar, volver atrás y el
trigger usan Postgres real y se omiten sin `QF_TEST_PG_DSN` (corren en CI). Nunca apuntarlo a producción.
"""
import copy
import json
import os

import pytest

from qf.comercial import pantallas as pa

DSN = os.getenv('QF_TEST_PG_DSN')
pg = pytest.mark.skipif(not DSN, reason='sin QF_TEST_PG_DSN')
ES6 = {'es': 'Uno', 'en': 'One', 'pt': 'Um', 'fr': 'Un', 'it': 'Uno', 'de': 'Eins'}


def sec(seccion, bid='=', **kw):
    b = {'id': seccion if bid == '=' else bid, 'tipo': 'seccion', 'seccion': seccion, 'visible': True, 'params': {},
         'build_min_app': None}
    b.update(kw)
    return b


def aviso(bid='aviso', **params):
    p = {'texto': dict(ES6), 'tono': 'info'}
    p.update(params)
    return {'id': bid, 'tipo': 'aviso', 'visible': True, 'params': p, 'build_min_app': None}


def rechaza(pantalla, bloques, parte):
    with pytest.raises(ValueError) as exc:
        pa.validar(pantalla, bloques)
    assert parte.lower() in str(exc.value).lower(), str(exc.value)


# --- validación -----------------------------------------------------------------------------------------

def test_lista_cerrada_exactamente_la_de_la_especificacion():
    assert pa.PANTALLAS == {'deporte': ('dias', 'resumen', 'destacado', 'partidos'),
                            'partido': ('cabecera', 'pronostico', 'mercados', 'contenido', 'sello',
                                        'estadisticas', 'h2h', 'alertas')}
    assert pa.TIPOS == ('seccion', 'aviso', 'vip') and pa.TONOS == ('info', 'exito', 'aviso', 'peligro')
    assert pa.MAX_BLOQUES == 20


def test_definicion_valida_se_normaliza():
    out = pa.validar('deporte', [sec('dias'), aviso(enlace='/planes/'), {'id': 'vip', 'tipo': 'vip'},
                                 sec('partidos', build_min_app=12)])
    assert [b['id'] for b in out] == ['dias', 'aviso', 'vip', 'partidos']
    assert out[0] == {'id': 'dias', 'tipo': 'seccion', 'seccion': 'dias', 'visible': True, 'params': {},
                      'build_min_app': None}
    assert out[1]['seccion'] is None and out[1]['params']['enlace'] == '/planes/'
    assert out[2]['params'] == {} and out[3]['build_min_app'] == 12


def test_cada_pantalla_solo_admite_sus_secciones():
    for pantalla, secciones in pa.PANTALLAS.items():
        for s in secciones:
            pa.validar(pantalla, [sec(s)])
    rechaza('deporte', [sec('cabecera')], 'sección debe ser')
    rechaza('partido', [sec('partidos')], 'sección debe ser')
    rechaza('inventada', [sec('dias')], 'pantalla desconocida')


def test_tipos_fuera_de_la_lista_y_campos_extra_se_rechazan():
    rechaza('deporte', [{'id': 'x', 'tipo': 'grafico'}, sec('dias')], 'tipo no válido')
    rechaza('deporte', [sec('dias', color='rojo')], 'campos no admitidos')
    rechaza('deporte', [sec('dias', params={'x': 1})], 'no admite parámetros')
    rechaza('deporte', [sec('dias'), {'id': 'v', 'tipo': 'vip', 'params': {'x': 1}}], 'no admite parámetros')
    rechaza('deporte', [sec('dias'), {'id': 'v', 'tipo': 'vip', 'seccion': 'dias'}], 'solo los bloques')
    rechaza('deporte', 'no es lista', 'lista')
    rechaza('deporte', [5], 'objeto')


def test_secciones_obligatorias_en_el_tipo_seccion():
    rechaza('deporte', [{'id': 'x', 'tipo': 'seccion'}], 'sección debe ser')


@pytest.mark.parametrize('malo', ['', 'A', 'con espacio', 'ñ', 'x' * 41, 'a-b', None, 5])
def test_ids_con_formato(malo):
    rechaza('deporte', [sec('dias', bid=malo)], 'id')


def test_ids_unicos_y_secciones_no_repetidas():
    rechaza('deporte', [sec('dias', bid='a'), sec('partidos', bid='a')], 'repetido')
    rechaza('deporte', [sec('dias', bid='a'), sec('dias', bid='b')], 'ya está')


def test_maximo_20_bloques():
    avisos = [aviso(f'a{i}') for i in range(19)]
    pa.validar('deporte', [sec('dias')] + avisos)                         # 20
    rechaza('deporte', [sec('dias')] + avisos + [aviso('a99')], 'como mucho 20')


def test_al_menos_una_seccion_visible():
    rechaza('deporte', [], 'al menos una sección visible')
    rechaza('deporte', [sec('dias', visible=False), aviso()], 'al menos una sección visible')
    pa.validar('deporte', [sec('dias', visible=False), sec('partidos')])
    rechaza('deporte', [sec('dias', visible='si')], 'verdadero o falso')


def test_aviso_exige_los_seis_idiomas_con_texto():
    rechaza('deporte', [sec('dias'), aviso(texto={'es': 'a', 'en': 'b', 'pt': 'c'})], '6 idiomas')
    rechaza('deporte', [sec('dias'), aviso(texto={**ES6, 'de': '  '})], 'falta el texto')
    rechaza('deporte', [sec('dias'), aviso(texto={**ES6, 'fr': 7})], 'falta el texto')
    rechaza('deporte', [sec('dias'), aviso(texto={**ES6, 'xx': 'extra'})], '6 idiomas')
    rechaza('deporte', [sec('dias'), aviso(texto={**ES6, 'es': 'x' * 301})], '300')
    rechaza('deporte', [sec('dias'), {'id': 'a', 'tipo': 'aviso', 'params': {'tono': 'info'}}], '6 idiomas')


@pytest.mark.parametrize('tono', pa.TONOS)
def test_tonos_validos(tono):
    pa.validar('deporte', [sec('dias'), aviso(tono=tono)])


def test_tono_invalido_y_parametros_desconocidos():
    rechaza('deporte', [sec('dias'), aviso(tono='rojo')], 'tono')
    rechaza('deporte', [sec('dias'), aviso(color='x')], 'parámetros no admitidos')


@pytest.mark.parametrize('enlace', ['https://malo.com/', '//malo.com', 'javascript:alert(1)', '/no-existe/',
                                    '../planes', 'planes', '/planes/?x=1', 7])
def test_enlace_debe_ser_una_ruta_relativa_existente(enlace):
    rechaza('deporte', [sec('dias'), aviso(enlace=enlace)], 'enlace')


def test_enlace_acepta_rutas_fijas_y_slugs_del_catalogo():
    for ruta in pa.RUTAS_ENLACE:
        pa.validar('deporte', [sec('dias'), aviso(enlace=ruta)])
    pa.validar('deporte', [sec('dias'), aviso(enlace='/nba/')])          # slug de la semilla del catálogo
    out = pa.validar('deporte', [sec('dias'), aviso(enlace='')])
    assert 'enlace' not in out[1]['params']


def test_las_rutas_de_enlace_son_rutas_reales_de_la_web():
    from qf.api import rutas_web
    assert set(pa.RUTAS_ENLACE) <= {s.path for s in rutas_web.SECCIONES}


@pytest.mark.parametrize('minimo', ['12', 1.5, -1, True, 'x'])
def test_build_min_app_entero_o_null(minimo):
    rechaza('deporte', [sec('dias', build_min_app=minimo)], 'build_min_app')


def test_clave_valida():
    pa.validar_clave('deporte', '*', 'web')
    pa.validar_clave('partido', 'nba', 'app')
    for args in (('x', '*', 'web'), ('deporte', 'NBA', 'web'), ('deporte', '', 'web'), ('deporte', '*', 'tv'),
                 ('deporte', '**', 'web')):
        with pytest.raises(ValueError):
            pa.validar_clave(*args)


# --- lectura: prioridad del deporte, caché y sin tabla --------------------------------------------------

def fijar(monkeypatch, tabla):
    monkeypatch.setattr(pa, '_cargar', lambda: copy.deepcopy(tabla))
    pa.invalidar_cache()


def test_el_deporte_concreto_gana_sobre_todos(monkeypatch):
    fijar(monkeypatch, {('deporte', '*', 'app'): [sec('partidos')],
                        ('deporte', 'nba', 'app'): [sec('dias')],
                        ('deporte', 'tenis', 'web'): [sec('resumen')]})
    assert pa.resolver('deporte', 'nba', 'app')[0]['seccion'] == 'dias'
    assert pa.resolver('deporte', 'tenis', 'app')[0]['seccion'] == 'partidos'    # sin la suya: la de «*»
    assert pa.resolver('deporte', 'tenis', 'web')[0]['seccion'] == 'resumen'
    assert pa.resolver('deporte', 'nba', 'web') is None                          # otro cliente: nada
    assert pa.resolver('partido', 'nba', 'app') is None                          # otra pantalla: nada


def test_publicadas_devuelve_copias_y_filtra_por_cliente(monkeypatch):
    fijar(monkeypatch, {('deporte', '*', 'app'): [sec('dias')], ('deporte', '*', 'web'): [sec('partidos')]})
    pa.publicadas('app')[('deporte', '*')].append('basura')
    assert pa.publicadas('app')[('deporte', '*')] == [sec('dias')]
    assert list(pa.publicadas('web')) == [('deporte', '*')]


def test_cache_de_30_segundos_e_invalidar(monkeypatch):
    llamadas = []
    monkeypatch.setattr(pa, '_cargar', lambda: llamadas.append(1) or {})
    pa.invalidar_cache()
    pa.publicadas('app'), pa.publicadas('web'), pa.resolver('deporte', 'x', 'app')
    assert len(llamadas) == 1 and pa._TTL == 30.0
    pa.invalidar_cache()
    pa.publicadas('app')
    assert len(llamadas) == 2


def test_sin_tabla_no_hay_definicion(monkeypatch):
    from psycopg.errors import UndefinedTable
    monkeypatch.undo()   # quita el parche de conftest: la lectura real

    def sin_tabla(*a, **k):
        raise UndefinedTable('no existe')
    monkeypatch.setattr(pa, 'query', sin_tabla)
    pa.invalidar_cache()
    assert pa.publicadas('app') == {} and pa.resolver('deporte', 'nba', 'app') is None
    assert pa.para_entrega('app') == {}
    pa.invalidar_cache()


def test_para_entrega_filtra_por_build_y_omite_claves_vacias(monkeypatch):
    fijar(monkeypatch, {('deporte', '*', 'app'): [sec('dias'), sec('partidos', build_min_app=9)],
                        ('deporte', 'nba', 'app'): [sec('resumen', build_min_app=30)]})
    assert [b['id'] for b in pa.para_entrega('app')['deporte']['*']] == ['dias', 'partidos']
    e = pa.para_entrega('app', 8)
    assert [b['id'] for b in e['deporte']['*']] == ['dias'] and 'nba' not in e['deporte']
    assert pa.para_entrega('app', 0)['deporte'].keys() == {'*'}
    assert pa.para_entrega('web') == {}


# --- Postgres real (db/113 aplicado) --------------------------------------------------------------------

@pytest.fixture
def base(monkeypatch):
    from psycopg_pool import ConnectionPool
    from qf import db
    monkeypatch.undo()                     # lectura real, sin los parches de conftest
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    monkeypatch.setattr(db, '_pool', pool)
    pa.invalidar_cache()
    yield db
    pa.invalidar_cache()
    pool.close()


def clave_nueva():
    import uuid
    return 'deporte', 'p' + uuid.uuid4().hex[:12], 'app'


@pg
def test_publicar_crea_filas_nuevas_y_nunca_edita(base):
    pantalla, deporte, cliente = clave_nueva()
    with pytest.raises(ValueError, match='No hay borrador'):
        pa.publicar(pantalla, deporte, cliente, 'n', 't')
    pa.guardar_borrador(pantalla, deporte, cliente, [sec('dias'), sec('partidos')], 't')
    with pytest.raises(ValueError, match='nota'):
        pa.publicar(pantalla, deporte, cliente, '  ', 't')
    assert pa.historial(pantalla, deporte, cliente) == []
    assert pa.publicar(pantalla, deporte, cliente, 'primera', 'tester') == 1
    pa.guardar_borrador(pantalla, deporte, cliente, [sec('partidos'), sec('dias')], 't')
    assert pa.publicar(pantalla, deporte, cliente, 'segunda', 'tester') == 2
    h = pa.historial(pantalla, deporte, cliente)
    assert [v['version'] for v in h] == [2, 1]
    assert [b['id'] for b in h[0]['bloques']] == ['partidos', 'dias'] and h[1]['nota'] == 'primera'
    assert pa.publicadas(cliente)[(pantalla, deporte)][0]['id'] == 'partidos'
    from qf.db import query
    auds = query("SELECT action FROM admin_audit WHERE action LIKE 'pantallas:%%' AND detail->>'deporte'=%s",
                 (deporte,))
    assert sorted(a['action'] for a in auds) == ['pantallas:borrador'] * 2 + ['pantallas:publicar'] * 2


@pg
def test_volver_atras_publica_de_nuevo_como_version_nueva(base):
    pantalla, deporte, cliente = clave_nueva()
    pa.guardar_borrador(pantalla, deporte, cliente, [sec('dias')], 't')
    pa.publicar(pantalla, deporte, cliente, 'v1', 't')
    pa.guardar_borrador(pantalla, deporte, cliente, [sec('partidos')], 't')
    pa.publicar(pantalla, deporte, cliente, 'v2', 't')
    with pytest.raises(ValueError, match='no existe'):
        pa.volver_a(pantalla, deporte, cliente, 9, 'n', 't')
    with pytest.raises(ValueError, match='nota'):
        pa.volver_a(pantalla, deporte, cliente, 1, '', 't')
    assert pa.volver_a(pantalla, deporte, cliente, 1, 'volvemos', 't') == 3
    h = pa.historial(pantalla, deporte, cliente)
    assert [v['version'] for v in h] == [3, 2, 1]
    assert h[0]['bloques'] == h[2]['bloques'] and h[1]['bloques'] != h[0]['bloques']      # 2 sigue intacta
    assert pa.resolver(pantalla, deporte, cliente)[0]['seccion'] == 'dias'
    assert pa.borrador(pantalla, deporte, cliente)['bloques'][0]['seccion'] == 'partidos'   # el borrador no se toca


@pg
def test_el_trigger_rechaza_update_y_delete(base):
    import psycopg
    pantalla, deporte, cliente = clave_nueva()
    pa.guardar_borrador(pantalla, deporte, cliente, [sec('dias')], 't')
    pa.publicar(pantalla, deporte, cliente, 'v1', 't')
    for sql in ("UPDATE pantalla_publicaciones SET nota='x'", "DELETE FROM pantalla_publicaciones",
                "UPDATE pantalla_publicaciones SET bloques='[]'::jsonb"):
        with pytest.raises(psycopg.errors.RaiseException):
            with base.conn() as c:
                c.execute(sql)
    assert len(pa.historial(pantalla, deporte, cliente)) == 1


@pg
def test_la_base_rechaza_claves_y_notas_invalidas(base):
    import psycopg
    insertar = ("INSERT INTO pantalla_publicaciones (pantalla, deporte, cliente, version, bloques, publicado_por, "
                "nota) VALUES (%s,%s,%s,%s,'[]'::jsonb,'t',%s)")
    for args in (('otra', 'x1', 'app', 1, 'n'), ('deporte', 'NBA', 'app', 1, 'n'), ('deporte', 'x1', 'tv', 1, 'n'),
                 ('deporte', 'x1', 'app', 0, 'n'), ('deporte', 'x1', 'app', 1, '  ')):
        with pytest.raises(psycopg.errors.CheckViolation):
            with base.conn() as c:
                c.execute(insertar, args)


@pg
def test_claves_dice_si_el_borrador_difiere(base):
    pantalla, deporte, cliente = clave_nueva()
    pa.guardar_borrador(pantalla, deporte, cliente, [sec('dias')], 't')
    fila = lambda: next(k for k in pa.claves() if k['deporte'] == deporte)   # noqa: E731
    assert fila()['version'] is None and fila()['difiere']
    pa.publicar(pantalla, deporte, cliente, 'v1', 't')
    assert fila()['version'] == 1 and not fila()['difiere']
    pa.guardar_borrador(pantalla, deporte, cliente, [sec('partidos')], 't')
    assert fila()['difiere']


@pg
def test_toda_columna_real_esta_clasificada_y_nada_privado_sale(base):
    from qf.api import cliente_config as cc
    pantalla, deporte, cliente = clave_nueva()
    pa.guardar_borrador(pantalla, deporte, cliente, [sec('dias')], 'PRIV_updated_by')
    pa.publicar(pantalla, deporte, cliente, 'PRIV_nota', 'PRIV_publicado_por')
    for tabla in ('pantalla_publicaciones', 'pantalla_borradores'):
        reales = {r['column_name'] for r in base.query(
            'SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() '
            'AND table_name = %s', (tabla,))}
        assert reales == cc.PUBLICAS[tabla] | cc.PRIVADAS[tabla] and not cc.PUBLICAS[tabla] & cc.PRIVADAS[tabla]
    # el bloque de `pantallas` tal como sale en /cliente/v1/config (la respuesta completa pide tablas ajenas a db/113)
    entrega = cc._pantallas(cc.Cliente.app, 'es', None)
    texto = json.dumps({k: {d: [b.model_dump(mode='json') for b in v] for d, v in por.items()}
                        for k, por in entrega.items()})
    assert deporte in texto and 'PRIV_' not in texto
