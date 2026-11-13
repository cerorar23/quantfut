"""Bloques de contenido de `partido.bloques` (Fase 4, tarea 4.1). Complementa la suite de contrato
(`test_deportes_v1.py`): los tipos, límites, ids, idiomas y el 503 de un bloque inválido.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from qf.api import deportes_v1 as dv
from qf.api.deportes_v1 import BloqueBarras, BloquePares, BloqueTabla, BloqueTexto, Partido
from qf.api.main import app
from test_deportes_v1 import (CASOS, _Proxy, _caso_prueba, base, c, caso, fijar_catalogo)   # noqa: F401  (fixtures)

TIPOS = {'tabla', 'barras', 'pares', 'texto'}


def partido_get(c, k, **q):
    return c.get(f'{base(k)}/partido/{k.partido_id}', params={'cliente': 'web', **q})


@pytest.fixture
def prueba(monkeypatch, c):
    k = _caso_prueba()
    k.instalar(monkeypatch)
    fijar_catalogo(monkeypatch, k.deporte, k.adaptador)
    from qf.api import idiomas
    monkeypatch.setattr(idiomas, 'estado', lambda cod: 'on')           # idiomas de la web encendidos
    return k


def con_bloques(monkeypatch, k, bloques):
    real = dv.ADAPTADORES[k.adaptador]
    monkeypatch.setitem(dv.ADAPTADORES, k.adaptador, _Proxy(real, bloques=lambda id: bloques))


# ── contrato para todos los casos ────────────────────────────────────────────

def test_bloques_de_cualquier_adaptador_son_de_tipo_cerrado_con_ids_unicos_y_sin_claves_crudas(c, caso):
    for cliente in ('web', 'app'):
        r = partido_get(c, caso, cliente=cliente, lang='en')
        b = r.json()['bloques']
        assert {x['tipo'] for x in b} <= TIPOS
        ids = [x['id'] for x in b]
        assert len(set(ids)) == len(ids)
        assert '"@' not in r.text                     # ninguna clave sin resolver
        assert not any(s in r.text for s in caso.centinelas)


def test_los_adaptadores_reales_no_rellenan_bloques_todavia(c, caso):
    if caso.adaptador != 'prueba':
        assert partido_get(c, caso).json()['bloques'] == []


def test_adaptador_sin_metodo_bloques_da_lista_vacia(c, caso, monkeypatch):
    real = dv.ADAPTADORES[caso.adaptador]

    class Sin:
        cartelera = real.cartelera
        partido = real.partido
        familia_de = real.familia_de
    monkeypatch.setitem(dv.ADAPTADORES, caso.adaptador, Sin())
    assert partido_get(c, caso).json()['bloques'] == []


@pytest.mark.parametrize('lang', ['E', 'esp', '1a', 'e', ''])
def test_lang_con_formato_invalido_da_422(c, caso, lang):
    assert partido_get(c, caso, lang=lang).status_code == 422


def test_bloque_que_lanza_la_fuente_da_503_sin_filtrar_el_error(c, caso, monkeypatch):
    real = dv.ADAPTADORES[caso.adaptador]

    def falla(id):
        raise RuntimeError('fuente caída: CENTINELA_ERROR')
    monkeypatch.setitem(dv.ADAPTADORES, caso.adaptador, _Proxy(real, bloques=falla))
    r = partido_get(c, caso)
    assert r.status_code == 503 and set(r.json()) == {'detail'} and 'CENTINELA_ERROR' not in r.text


# ── adaptador de prueba: un bloque de cada tipo ──────────────────────────────

def test_un_bloque_de_cada_tipo_con_su_forma_exacta(c, prueba):
    b = partido_get(c, prueba).json()['bloques']
    assert [x['tipo'] for x in b] == ['tabla', 'barras', 'pares', 'texto']
    assert set(b[0]) == {'id', 'tipo', 'titulo', 'columnas', 'filas'}
    assert set(b[1]) == {'id', 'tipo', 'titulo', 'items'} and set(b[1]['items'][0]) == {'etiqueta', 'valor', 'nota'}
    assert set(b[2]) == {'id', 'tipo', 'titulo', 'items'} and set(b[2]['items'][0]) == {'etiqueta', 'valor'}
    assert set(b[3]) == {'id', 'tipo', 'titulo', 'cuerpo'}
    assert b[0]['titulo'] == 'Forma reciente' and b[0]['columnas'] == ['Equipo', 'Victorias', 'Promedio']
    assert b[0]['filas'] == [['Local', 3, 0.5], ['Visitante', 2, None]]            # nombres y números no se traducen
    assert b[2]['items'][1] == {'etiqueta': 'Rival', 'valor': 'Visitante'}


@pytest.mark.parametrize('cliente,lang,esperado', [
    ('web', None, 'Forma reciente'), ('web', 'es', 'Forma reciente'), ('web', 'en', 'Recent form'),
    ('web', 'pt', 'Forma recente'), ('web', 'fr', 'Forma reciente'), ('web', 'de', 'Forma reciente'),
    ('web', 'zz', 'Forma reciente'),                                                # la web solo sirve es, en, pt
    ('app', 'fr', 'Forme récente'), ('app', 'it', 'Forma recente'), ('app', 'de', 'Aktuelle Form'),
    ('app', 'en', 'Recent form'), ('app', 'zz', 'Forma reciente'), ('app', None, 'Forma reciente')])
def test_idioma_pedido_con_caida_a_es(c, prueba, cliente, lang, esperado):
    q = {'cliente': cliente, **({'lang': lang} if lang else {})}
    r = c.get(f'{base(prueba)}/partido/{prueba.partido_id}', params=q)
    assert r.status_code == 200 and r.json()['bloques'][0]['titulo'] == esperado


def test_idioma_de_la_web_apagado_se_sirve_como_es(c, prueba, monkeypatch):
    from qf.api import idiomas
    monkeypatch.setattr(idiomas, 'estado', lambda cod: 'on' if cod in ('es', 'en') else 'off')
    assert partido_get(c, prueba, lang='en').json()['bloques'][0]['titulo'] == 'Recent form'
    assert partido_get(c, prueba, lang='pt').json()['bloques'][0]['titulo'] == 'Forma reciente'


def test_los_bloques_no_dependen_del_usuario(c, prueba):
    anon = partido_get(c, prueba, lang='en')
    con = TestClient(app, cookies={'qf_session': 'x'}).get(
        f'{base(prueba)}/partido/{prueba.partido_id}', params={'cliente': 'web', 'lang': 'en'},
        headers={'Authorization': 'Bearer vip'})
    assert con.content == anon.content and con.headers['etag'] == anon.headers['etag']


# ── bloque inválido -> 503 ───────────────────────────────────────────────────

def _t(**kw):
    return {'id': 't', 'tipo': 'texto', 'titulo': '@resumen', 'cuerpo': '@total', **kw}


def _tabla(**kw):
    return {'id': 'a', 'tipo': 'tabla', 'titulo': '@resumen', 'columnas': ['x'], 'filas': [[1]], **kw}


def _barras(items):
    return {'id': 'b', 'tipo': 'barras', 'titulo': '@resumen', 'items': items}


def _pares(items):
    return {'id': 'p', 'tipo': 'pares', 'titulo': '@resumen', 'items': items}


@pytest.mark.parametrize('malo', [
    [_t(tipo='grafico')],                                          # tipo desconocido
    [_t(extra=1)],                                                 # campo extra
    [_t(id='Mal Id')], [_t(id='')], [_t(id='x' * 41)],
    [_t(), _t()],                                                  # ids repetidos
    [_t(titulo='Texto libre')],                                    # el título no es clave
    [_t(cuerpo='Texto libre')],                                    # el cuerpo no es clave
    [_t(titulo='@no_existe')], [_t(cuerpo='@no_existe')],
    [_t(cuerpo='<b>hola</b>')], [_t(titulo='<i>@x</i>')],
    [_tabla(columnas=[f'c{i}' for i in range(13)], filas=[])],     # 13 columnas
    [_tabla(columnas=[])],
    [_tabla(filas=[[1]] * 101)],                                   # 101 filas
    [_tabla(filas=[[1, 2]])],                                      # fila de otro ancho
    [_tabla(filas=[[True]])], [_tabla(filas=[[{'a': 1}]])], [_tabla(filas=[[float('nan')]])],
    [_tabla(columnas=['<script>'])], [_tabla(columnas=['@no_existe'])],
    [_barras([{'etiqueta': 'x', 'valor': 1.2}])], [_barras([{'etiqueta': 'x', 'valor': -0.1}])],
    [_barras([{'etiqueta': 'x', 'valor': 0.5}] * 21)], [_barras([{'etiqueta': 'x', 'valor': 0.5, 'otro': 1}])],
    [_pares([{'etiqueta': 'x', 'valor': 1}] * 31)], [_pares([{'etiqueta': '@no_existe', 'valor': 1}])],
    'no es una lista', [3],
])
def test_bloque_invalido_da_503(c, prueba, monkeypatch, malo):
    con_bloques(monkeypatch, prueba, malo)
    r = partido_get(c, prueba)
    assert r.status_code == 503 and set(r.json()) == {'detail'}


def test_limites_exactos_son_validos(c, prueba, monkeypatch):
    con_bloques(monkeypatch, prueba, [
        _tabla(columnas=[f'c{i}' for i in range(12)], filas=[[i] * 12 for i in range(100)]),
        _barras([{'etiqueta': 'x', 'valor': v / 19} for v in range(20)]),
        _pares([{'etiqueta': f'k{i}', 'valor': i} for i in range(30)]),
        _t()])
    r = partido_get(c, prueba)
    assert r.status_code == 200 and len(r.json()['bloques']) == 4


def test_los_bloques_del_adaptador_pueden_ser_modelos(c, prueba, monkeypatch):
    con_bloques(monkeypatch, prueba, [BloqueTexto(id='t', titulo='@resumen', cuerpo='@total')])
    assert partido_get(c, prueba).json()['bloques'] == [{'id': 't', 'tipo': 'texto', 'titulo': 'Resumen', 'cuerpo': 'Total'}]


def test_cuerpo_de_mas_de_600_caracteres_no_cumple_el_modelo():
    BloqueTexto(id='t', titulo='x', cuerpo='a' * 600)
    with pytest.raises(ValidationError):
        BloqueTexto(id='t', titulo='x', cuerpo='a' * 601)


def test_modelos_de_bloque_cerrados():
    for cls in (BloqueTabla, BloqueBarras, BloquePares, BloqueTexto):
        assert cls.model_config['extra'] == 'forbid'
    ev = dict(id='1', sport='s', home='h', away='a', league='l', start=datetime(2026, 1, 1, tzinfo=timezone.utc),
              status='scheduled')
    with pytest.raises(ValidationError):
        Partido.model_validate({'deporte': 'x', 'evento': ev, 'bloques': [{'id': 'a', 'tipo': 'raro', 'titulo': 'x'}]})
