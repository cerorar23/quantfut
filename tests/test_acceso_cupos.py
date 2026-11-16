"""Cupos de gratis por deporte y cliente (db/116, `/control/cupos`), sin Postgres."""
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import console, cupos_panel, panel
from qf.api import partido_mercados as pm
from qf.comercial import acceso_cupos as ac
from qf.comercial.acceso_cupos import Cupo

LAM, MU, RHO = 1.457, .7185, -.06


@pytest.fixture(autouse=True)
def sin_lecturas_externas(monkeypatch):
    monkeypatch.setattr(pm, 'query_one', lambda *a, **k: None)


@pytest.fixture(scope='module')
def lista():
    return pm.filas_goles(LAM, MU, RHO, 'Local FC', 'Visita FC')


def fijar(monkeypatch, **cupos):
    monkeypatch.setattr(ac, '_cargar', lambda: {tuple(k.split('_')): v for k, v in cupos.items()})
    ac.invalidar_cache()


# --- módulo ---------------------------------------------------------------------------------

def test_sin_tabla_valen_los_cupos_de_hoy():
    assert ac.cupo('futbol', 'web') == Cupo(None, 3)
    assert ac.cupo('futbol', 'app') == Cupo(None, 0)
    assert ac.cupo('nba', 'web') == ac.cupo('tenis', 'app') == Cupo(None, None)     # todo abierto
    assert ac.cupo('deporte_nuevo', 'web') == Cupo(None, None)


def test_la_fila_de_la_base_manda_sobre_el_valor_de_codigo(monkeypatch):
    fijar(monkeypatch, futbol_web=Cupo(2, 5), nba_app=Cupo(1, 0))
    assert ac.cupo('futbol', 'web') == Cupo(2, 5) and ac.cupo('nba', 'app') == Cupo(1, 0)
    assert ac.cupo('futbol', 'app') == Cupo(None, 0)
    assert ac.para_cliente('app', ['futbol', 'nba', 'tenis']) == {
        'futbol': Cupo(None, 0), 'nba': Cupo(1, 0), 'tenis': Cupo(None, None)}


@pytest.mark.parametrize('texto,valor', [('', None), ('  ', None), (None, None), ('0', 0), (' 7 ', 7), ('999', 999)])
def test_numero_del_formulario(texto, valor):
    assert ac._numero(texto) == valor


@pytest.mark.parametrize('texto', ['-1', '1000', '2.5', 'tres'])
def test_numero_no_valido(texto):
    with pytest.raises(ValueError):
        ac._numero(texto)


def test_abiertos_del_dia_son_los_de_mayor_probabilidad():
    dia = [('a', .76), ('b', .91), ('c', .83), ('d', .83)]
    assert ac.abiertos_del_dia(dia, None) is None                    # sin límite: todos
    assert ac.abiertos_del_dia(dia, 0) == set()
    assert ac.abiertos_del_dia(dia, 2) == {'b', 'c'}                 # empate: el id menor
    assert ac.abiertos_del_dia(dia, 9) == {'a', 'b', 'c', 'd'}


# --- fútbol: mercados del partido -----------------------------------------------------------

def abiertas(filas):
    return [f for f in filas if not f['locked']]


def test_web_abre_tantos_mercados_como_diga_el_cupo(lista):
    filas, marcadores = lista
    for n in (0, 1, 3, 5):
        out, _, destacado = pm.aplicar_acceso_web(filas, marcadores, {}, plus=False, gratis=n)
        assert len(abiertas(out)) == n
        assert destacado is not None and not destacado['locked']     # el destacado se decide aparte
    out, marcadores_out, _ = pm.aplicar_acceso_web(filas, marcadores, {}, plus=False, gratis=None)
    assert len(abiertas(out)) == len(out) and marcadores_out is None    # todo abierto no regala marcadores


def test_web_destacado_con_candado_no_cuenta_entre_los_gratis(lista):
    filas, marcadores = lista
    _, _, libre = pm.aplicar_acceso_web(filas, marcadores, {}, plus=False, gratis=3)
    out, _, _ = pm.aplicar_acceso_web(filas, marcadores, {}, plus=False, gratis=3, destacado_abierto=False)
    assert len(abiertas(out)) == 3 and libre['id'] not in {f['id'] for f in abiertas(out)}
    out, candado = pm._candado_destacado(out, libre)
    assert candado == {'id': libre['id'], 'grupo': libre['grupo'], 'locked': True, 'destacado': True}
    assert next(f for f in out if f['id'] == libre['id']) == candado


def test_construir_web_pone_candado_al_destacado_fuera_del_cupo_del_dia(monkeypatch):
    from datetime import datetime, timezone
    monkeypatch.setattr(pm, 'lambdas_goles', lambda m: (LAM, MU, RHO))
    monkeypatch.setattr(pm, 'lambdas_estadisticas', lambda m: (None, None))
    monkeypatch.setattr(pm, 'liga_de_partido', lambda m: None)
    monkeypatch.setattr(pm, 'cuotas_casas', lambda m: {})
    monkeypatch.setattr(pm, 'datos_partido', lambda m: None)
    monkeypatch.setattr(pm, 'destacados_gratis_del_dia', lambda ko, n: {'otro'})
    ko = datetime(2026, 11, 20, 20, tzinfo=timezone.utc)
    fijar(monkeypatch, futbol_web=Cupo(1, 2))
    fuera = pm.construir('m1', 'A', 'B', {}, False, True, ko)
    assert fuera['destacado'] == {'id': fuera['destacado']['id'], 'grupo': fuera['destacado']['grupo'],
                                  'locked': True, 'destacado': True}
    assert fuera['abiertas'] == 2
    con_vip = pm.construir('m1', 'A', 'B', {}, True, True, ko)
    assert not con_vip['destacado']['locked'] and con_vip['abiertas'] == con_vip['total']
    monkeypatch.setattr(pm, 'destacados_gratis_del_dia', lambda ko, n: {'m1'})
    dentro = pm.construir('m1', 'A', 'B', {}, False, True, ko)
    assert not dentro['destacado']['locked'] and dentro['abiertas'] == 2


def test_app_abre_los_de_mayor_probabilidad_segun_el_cupo(lista):
    filas, marcadores = lista
    assert pm.gratis_app(filas, 0) == set()
    dos = pm.gratis_app(filas, 2)
    assert dos == {f['id'] for f in sorted(filas, key=lambda f: (-f['prob'], f['id']))[:2]}
    out, marcadores_out = pm.aplicar_acceso(filas, marcadores, {}, plus=False, gratis=dos)
    assert {f['id'] for f in abiertas(out)} == dos and marcadores_out is None
    assert all(set(f) == {'id', 'grupo', 'locked'} for f in out if f['locked'])
    assert pm.gratis_app(filas, None) == {f['id'] for f in filas}


# --- panel ----------------------------------------------------------------------------------

@pytest.fixture
def cliente(monkeypatch):
    guardados = []
    monkeypatch.setattr(ac, 'guardar', lambda *a: guardados.append(a[:4]) or ac.Cupo(ac._numero(a[2]), ac._numero(a[3])))
    app = FastAPI()
    app.include_router(cupos_panel.router)
    app.dependency_overrides[console.require_console] = lambda: 'tester'
    return TestClient(app, follow_redirects=False), panel.csrf_token('tester'), guardados


def test_pagina_muestra_los_tres_deportes_y_los_dos_clientes(cliente):
    c, _, _ = cliente
    r = c.get('/control/cupos')
    assert r.status_code == 200
    for accion in ('futbol/web', 'futbol/app', 'nba/web', 'nba/app', 'tenis/web', 'tenis/app'):
        assert f'action="/control/cupos/{accion}"' in r.text
    assert 'No aplica' in r.text and r.text.count('name="destacados"') == 5      # fútbol app no tiene destacado
    assert 'value="3"' in r.text


def test_guardar_exige_csrf_y_valida(cliente):
    c, csrf, guardados = cliente
    assert c.post('/control/cupos/nba/web', data={'csrf': 'x', 'destacados': '2', 'mercados': '4'}).status_code == 403
    r = c.post('/control/cupos/nba/web', data={'csrf': csrf, 'destacados': '2', 'mercados': ''})
    assert r.status_code == 303 and parse_qs(urlsplit(r.headers['location']).query)['m'] == ['cupos_guardados']
    assert guardados == [('nba', 'web', '2', '')]
    assert c.post('/control/cupos/inventado/web', data={'csrf': csrf}).status_code == 404


def test_error_de_validacion_vuelve_como_mensaje(monkeypatch):
    app = FastAPI()
    app.include_router(cupos_panel.router)
    app.dependency_overrides[console.require_console] = lambda: 'tester'
    c = TestClient(app, follow_redirects=False)
    r = c.post('/control/cupos/tenis/app', data={'csrf': panel.csrf_token('tester'), 'destacados': '-3'})
    q = parse_qs(urlsplit(r.headers['location']).query)
    assert r.status_code == 303 and q['m'] == ['acceso_error'] and 'entre 0 y 999' in q['err'][0]
