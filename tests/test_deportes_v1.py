"""Suite de contrato de `GET /deportes/v1/{deporte}/…` (Fase 3 parte A de «Web y App»).

Sin Postgres ni red: el catálogo es uno de prueba (`catalogo._cargar`) y el adaptador, uno definido aquí.

CÓMO AÑADIR UN ADAPTADOR REAL (tenis, NBA, fútbol): escribe su `Caso` y añádelo a `CASOS`; toda la sección «contrato»
corre sola con él. Un `Caso` es:
  * `adaptador` / `deporte`: la clave de `ADAPTADORES` y el `deporte_id` del catálogo (`tenis`, `nba`, `futbol`);
  * `instalar(monkeypatch)`: registra el adaptador real en `ADAPTADORES` alimentado con datos FIJOS (parchea su fuente);
  * `romper(monkeypatch)`: hace que su fuente lance una excepción;
  * `desde`: fecha AAAA-MM-DD en UTC desde la que hay al menos 3 eventos en 2 días distintos, uno de ellos con la misma
    hora de inicio que otro (para comprobar el desempate por `id`);
  * `partido_id`: un partido con varios mercados: uno con `eligible=False`, uno con familia del catálogo, uno que
    `familia_de` no resuelve (irá a `otros`) y, si puedes, uno de una familia que el catálogo oculta a la web;
  * `centinelas`: textos presentes en la fuente cruda que NO pueden salir en ninguna respuesta.
La prueba de paridad con `nbaV2Events` / `tennisEvents` / `football()` va en el archivo del adaptador.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from qf.api import deportes_v1 as dv
from qf.api import ratelimit, seo
from qf.api.deportes_v1 import Evento, Imagenes, Mercado
from qf.api.main import app
from qf.comercial import catalogo

ES6 = {'es': 'Uno', 'en': 'One', 'pt': 'Um', 'fr': 'Un', 'it': 'Uno', 'de': 'Eins'}
SELLO = 'a' * 64


# ── adaptador de prueba ──────────────────────────────────────────────────────

def _m(id, market, p, *, sellado='2026-11-12T06:00:00Z', outcome=None, secreto='CENTINELA_MERCADO'):
    return {'id': id, 'market': market, 'p': p, 'sellado': sellado, 'outcome': outcome, 'secreto': secreto}


FILAS = [
    {'id': 'e-b', 'inicio': '2026-11-12T08:00:00Z', 'estado': 'scheduled', 'fit': 'CENTINELA_FIT',
     'mercados': [_m('e-b-1', 'alfa', 0.61)], 'destacado': 'e-b-1'},
    {'id': 'e-a', 'inicio': '2026-11-12T08:00:00Z', 'estado': 'live', 'fit': 'CENTINELA_FIT', 'mercados': []},
    {'id': 'e-c', 'inicio': '2026-11-12T20:00:00+00:00', 'estado': 'finished', 'fit': 'CENTINELA_FIT',
     'mercados': [_m('e-c-2', 'beta', 0.55, sellado='2026-11-12T21:00:00Z'),   # sellado tras el inicio
                  _m('e-c-1', 'alfa', 0.62, outcome='win'),
                  _m('e-c-3', 'gamma', 0.70),                                 # familia oculta en la web
                  _m('e-c-4', 'delta', 0.58)],                                # sin familia -> otros
     'destacado': 'e-c-1'},
    {'id': 'e-d', 'inicio': '2026-11-13T02:00:00Z', 'estado': 'scheduled', 'fit': 'CENTINELA_FIT', 'mercados': []},
    {'id': 'e-z', 'inicio': '2026-11-30T12:00:00Z', 'estado': 'cancelled', 'fit': 'CENTINELA_FIT', 'mercados': []},
]
FAMILIAS = {'alfa': 'fam_a', 'beta': 'fam_b', 'gamma': 'fam_oculta', 'delta': 'inventada'}


def _utc(t: str) -> datetime:
    return datetime.fromisoformat(t.replace('Z', '+00:00'))


class AdaptadorPrueba:
    def __init__(self, deporte: str, filas=FILAS):
        self.deporte, self.filas, self.roto = deporte, filas, False

    def _evento(self, f, todos: bool) -> Evento:
        inicio = _utc(f['inicio'])
        mercados = [Mercado(id=m['id'], label=f"Etiqueta {m['market']}", selection='Sí', probability=m['p'],
                            sealed_at=_utc(m['sellado']), eligible=_utc(m['sellado']) <= inicio, market=m['market'],
                            family=FAMILIAS[m['market']], outcome=m['outcome'])
                    for m in f['mercados']]
        return Evento(id=f['id'], sport=self.deporte, home='Local', away='Visitante', league='Liga', start=inicio,
                      status=f['estado'], seal=SELLO if f['mercados'] else None, bloqueados=2 if todos else 0,
                      imagenes=Imagenes(home='/web/escudos/a.png', away=None), markets=mercados,
                      destacado=f.get('destacado'))

    def cartelera(self, inicio, fin):
        if self.roto:
            raise RuntimeError('fuente caída: CENTINELA_ERROR')
        return [self._evento(f, False) for f in self.filas if inicio <= _utc(f['inicio']) < fin]

    def partido(self, id):
        if self.roto:
            raise RuntimeError('fuente caída: CENTINELA_ERROR')
        return next((self._evento(f, True) for f in self.filas if f['id'] == id), None)

    def familia_de(self, market):
        return FAMILIAS[market]

    def bloques(self, id):
        """Un bloque de cada tipo; títulos y etiquetas son CLAVES de `bloques_textos` (prefijo @), los nombres propios no."""
        if self.roto:
            raise RuntimeError('fuente caída: CENTINELA_ERROR')
        return BLOQUES_PRUEBA


BLOQUES_PRUEBA = [
    {'id': 'forma', 'tipo': 'tabla', 'titulo': '@forma', 'columnas': ['@equipo', '@victorias', '@promedio'],
     'filas': [['Local', 3, 0.5], ['Visitante', 2, None]]},
    {'id': 'prob', 'tipo': 'barras', 'titulo': '@probabilidades',
     'items': [{'etiqueta': '@local', 'valor': 0.6, 'nota': '@muestra_pequena'}, {'etiqueta': 'Visitante', 'valor': 0.4}]},
    {'id': 'resumen', 'tipo': 'pares', 'titulo': '@resumen',
     'items': [{'etiqueta': '@total', 'valor': 12}, {'etiqueta': '@rival', 'valor': 'Visitante'}]},
    {'id': 'aviso', 'tipo': 'texto', 'titulo': '@estadisticas', 'cuerpo': '@muestra_pequena'},
]


@dataclass
class Caso:
    adaptador: str
    deporte: str
    desde: str
    partido_id: str
    centinelas: tuple[str, ...]
    instalar: Callable
    romper: Callable


def _caso_prueba() -> Caso:
    def instalar(mp):
        mp.setitem(dv.ADAPTADORES, 'prueba', AdaptadorPrueba('prueba'))

    def romper(mp):
        dv.ADAPTADORES['prueba'].roto = True
    return Caso('prueba', 'prueba', '2026-11-12', 'e-c',
                ('CENTINELA_FIT', 'CENTINELA_MERCADO', 'CENTINELA_ERROR'), instalar, romper)


def _caso_futbol() -> Caso:
    import datos_deportes_futbol as datos      # datos fijos y parches de fuentes: tests/datos_deportes_futbol.py
    estado = {}

    def instalar(mp):
        estado['fuentes'] = datos.instalar_para_suite(mp)

    def romper(mp):
        estado['fuentes'].roto = True
    return Caso('futbol', 'futbol', datos.DESDE, 'eu.ucl:m1', datos.CENTINELAS, instalar, romper)


def _caso_tenis() -> Caso:
    # Datos fijos y centinelas de `test_deportes_tenis_paridad`. Familias del catálogo de prueba: fam_a / fam_b / oculta.
    def instalar(mp):
        from test_deportes_tenis_paridad import fijar_fuente
        from qf.api import deportes_tenis
        fijar_fuente(mp)
        mp.setattr(deportes_tenis, 'FAMILIAS', {'games_total': 'fam_a', 'sets_total': 'fam_b', 'tiebreak': 'fam_oculta'})
        mp.setitem(dv.ADAPTADORES, 'tenis', deportes_tenis.AdaptadorTenis())

    def romper(mp):
        def falla():
            raise RuntimeError('fuente caída: CENTINELA_ERROR')
        mp.setattr('qf.api.tenis_publico.public_data', falla)
    return Caso('tenis', 'tenis', '2026-11-12', 't-c', ('CENTINELA_FIT', 'CENTINELA_MERCADO', 'CENTINELA_ERROR'),
                instalar, romper)


CASOS = [pytest.param(_caso_prueba(), id='prueba'),
         pytest.param(_caso_tenis(), id='tenis'),
         pytest.param(_caso_futbol(), id='futbol')]   # ← los adaptadores reales añaden aquí su Caso


class _FamiliasDePrueba:
    """El catálogo de prueba solo tiene fam_a/fam_b/fam_oculta: mapea ahí tres familias reales de NBA y deja el resto a `otros`."""
    def __init__(self, real):
        self._real = real

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)

    def familia_de(self, market):
        return {'winner': 'fam_a', 'handicap': 'fam_b', 'game_total': 'fam_oculta'}.get(market, self._real.familia_de(market))


def _caso_nba() -> Caso:
    from nba_contrato_datos import PARTIDO_ID, instalar as datos, romper as caida
    from qf.api import deportes_nba

    def instalar(mp):
        datos(mp)
        mp.setitem(dv.ADAPTADORES, 'nba', _FamiliasDePrueba(deportes_nba.AdaptadorNba()))
    return Caso('nba', 'nba', '2026-11-12', PARTIDO_ID, ('CENTINELA_FIT', 'CENTINELA_MERCADO', 'CENTINELA_ERROR'), instalar, caida)


CASOS.append(pytest.param(_caso_nba(), id='nba'))



# ── catálogo y cliente ───────────────────────────────────────────────────────

def _familia(id, orden, visible_web=True):
    return {'familia_id': id, 'orden': orden, 'nombre': dict(ES6), 'subtitulo': {}, 'visible_web': visible_web,
            'visible_app': True, 'updated_by': 'x', 'updated_at': None}


def fijar_catalogo(mp, deporte, adaptador, *, web='on', app_='on'):
    cat = [{'deporte_id': deporte, 'adaptador': adaptador, 'orden': 1, 'icono': 'x', 'color': '#aabbcc',
            'secciones': ['high'], 'nombre': dict(ES6), 'slug': {'es': 'x', 'en': 'x', 'pt': 'x'},
            'estado_web': web, 'estado_app': app_, 'updated_by': 'x', 'updated_at': None,
            'familias': [_familia('fam_b', 2), _familia('fam_oculta', 3, visible_web=False), _familia('fam_a', 1)]}]
    mp.setattr(catalogo, '_cargar', lambda: catalogo._ordenar(copy.deepcopy(cat)))
    catalogo.invalidar_cache()


@pytest.fixture
def c(monkeypatch):
    monkeypatch.setattr(ratelimit, 'rate_limited', lambda *a, **k: False)
    return TestClient(app)


@pytest.fixture(params=CASOS)
def caso(request, monkeypatch):
    k: Caso = request.param
    k.instalar(monkeypatch)
    fijar_catalogo(monkeypatch, k.deporte, k.adaptador)
    return k


def base(k: Caso) -> str:
    return f'/deportes/v1/{k.deporte}'


def cartelera(c, k, **kw):
    params = {'cliente': 'web', 'desde': k.desde, 'dias': 7, **kw}
    return c.get(f'{base(k)}/cartelera', params=params)


EVENTO_CLAVES = {'id', 'sport', 'home', 'away', 'league', 'start', 'status', 'seal', 'sealed_at', 'planned_seal',
                 'score', 'surface', 'bloqueados', 'imagenes', 'markets', 'destacado', 'team_projection'}
MERCADO_CLAVES = {'id', 'label', 'selection', 'probability', 'sealed_at', 'eligible', 'market', 'family', 'line',
                  'player', 'player_id', 'price', 'reference', 'outcome', 'push_probability', 'principal'}
ESTADOS = {'scheduled', 'live', 'awaiting_result', 'finished', 'cancelled'}


# ── contrato (parametrizado por adaptador) ───────────────────────────────────

def test_forma_exacta(c, caso):
    r = cartelera(c, caso)
    assert r.status_code == 200
    b = r.json()
    assert set(b) == {'contrato', 'deporte', 'desde', 'dias', 'eventos'}
    assert (b['contrato'], b['deporte'], b['desde'], b['dias']) == (1, caso.deporte, caso.desde, 7)
    assert b['eventos']
    for ev in b['eventos']:
        assert set(ev) == EVENTO_CLAVES
        assert ev['sport'] == caso.deporte and ev['status'] in ESTADOS
        assert isinstance(ev['bloqueados'], int) and ev['bloqueados'] >= 0
        assert ev['seal'] is None or len(ev['seal']) == 64
        assert ev['start'].endswith('Z')
        for m in ev['markets']:
            assert set(m) == MERCADO_CLAVES
    p = c.get(f'{base(caso)}/partido/{caso.partido_id}', params={'cliente': 'web'}).json()
    assert set(p) == {'contrato', 'deporte', 'evento', 'bloques'} and isinstance(p['bloques'], list)
    assert set(p['evento']) == EVENTO_CLAVES
    assert len(p['evento']['markets']) >= 2
    for m in p['evento']['markets']:
        assert set(m) == MERCADO_CLAVES and 0 < m['probability'] < 1
        assert m['outcome'] in ('win', 'loss', 'push', 'void', None) and isinstance(m['eligible'], bool)
    mk = c.get(f'{base(caso)}/partido/{caso.partido_id}/mercados', params={'cliente': 'web'}).json()
    assert set(mk) == {'contrato', 'deporte', 'evento_id', 'familias'} and mk['evento_id'] == caso.partido_id
    assert all(set(f) == {'id', 'mercados'} for f in mk['familias'])


def test_orden_por_start_y_id(c, caso):
    ev = cartelera(c, caso).json()['eventos']
    claves = [(e['start'], e['id']) for e in ev]
    assert claves == sorted(claves) and len(set(claves)) == len(claves)


def test_ventana_y_tz(c, caso):
    todos = cartelera(c, caso).json()['eventos']
    ini = datetime.fromisoformat(caso.desde + 'T00:00:00+00:00')
    for dias in (1, 2):
        for tz in (0, 480, -300):
            a = ini - timedelta(minutes=tz)
            esperados = [e['id'] for e in todos if a <= _utc(e['start']) < a + timedelta(days=dias)]
            b = cartelera(c, caso, dias=dias, tz=tz).json()
            assert [e['id'] for e in b['eventos']] == esperados, (dias, tz)
            assert b['dias'] == dias
    # el día local de tz=-300 empieza 5 h más tarde: `desde` sigue siendo la fecha local pedida
    assert cartelera(c, caso, tz=-300).json()['desde'] == caso.desde


def test_sin_partidos_es_200_con_lista_vacia(c, caso):
    r = cartelera(c, caso, desde='2001-01-01')
    assert r.status_code == 200 and r.json()['eventos'] == []


def test_cartelera_solo_trae_el_destacado_y_los_principales_y_partido_trae_todos(c, caso):
    for e in cartelera(c, caso).json()['eventos']:
        assert all(m['id'] == e['destacado'] or m['principal'] for m in e['markets'])     # nada más que destacado y principal
        assert e['destacado'] is None or e['destacado'] in [m['id'] for m in e['markets']]
        p = c.get(f'{base(caso)}/partido/{e["id"]}', params={'cliente': 'web'}).json()['evento']
        assert (p['id'], p['start'], p['home'], p['away']) == (e['id'], e['start'], e['home'], e['away'])
        assert {m['id'] for m in e['markets']} <= {m['id'] for m in p['markets']}


def test_cartelera_conserva_el_principal_aunque_sea_revision_y_team_projection_viaja(c, monkeypatch):
    """Regla genérica del router: destacado + `principal`; el resto se recorta. Sin conocer ningún deporte."""
    def mk(id, principal, eligible=True):
        return Mercado(id=id, label=id, selection='Sí', probability=0.6, sealed_at=_utc('2026-11-12T06:00:00Z'), eligible=eligible,
                       market='alfa', family='fam_a', principal=principal)
    ev = Evento(id='x1', sport='prueba', home='L', away='V', league='Liga', start=_utc('2026-11-12T08:00:00Z'), status='scheduled',
                markets=[mk('revision', True, eligible=False), mk('otro', False), mk('dest', False)], destacado='dest',
                team_projection=[110.5, 104.25])
    sin = Evento(id='x2', sport='prueba', home='L', away='V', league='Liga', start=_utc('2026-11-12T09:00:00Z'), status='scheduled',
                 markets=[mk('otro2', False)])
    monkeypatch.setitem(dv.ADAPTADORES, 'prueba', type('A', (), {'cartelera': lambda self, i, f: [ev, sin], 'partido': lambda self, id: None,
                                                                  'familia_de': lambda self, m: 'fam_a'})())
    fijar_catalogo(monkeypatch, 'prueba', 'prueba')
    r = c.get('/deportes/v1/prueba/cartelera', params={'cliente': 'web', 'desde': '2026-11-12', 'dias': 1}).json()['eventos']
    assert [(e['id'], [m['id'] for m in e['markets']]) for e in r] == [('x1', ['revision', 'dest']), ('x2', [])]
    assert r[0]['team_projection'] == [110.5, 104.25] and r[1]['team_projection'] is None
    assert r[0]['markets'][0]['principal'] is True and r[0]['markets'][1]['principal'] is False


@pytest.mark.parametrize('malo', [[1.0], [1.0, 2.0, 3.0], [float('nan'), 1.0], [float('inf'), 1.0]])
def test_team_projection_mal_formado_no_cumple_el_modelo(malo):
    with pytest.raises(ValidationError):
        Evento(id='x', sport='s', home='L', away='V', league='L', start=_utc('2026-11-12T08:00:00Z'), status='scheduled', team_projection=malo)


def test_eligible_false_si_el_sello_es_posterior_al_inicio(c, caso):
    p = c.get(f'{base(caso)}/partido/{caso.partido_id}', params={'cliente': 'web'}).json()['evento']
    assert any(not m['eligible'] for m in p['markets'])
    for m in p['markets']:
        if m['sealed_at'] and _utc(m['sealed_at']) > _utc(p['start']):
            assert m['eligible'] is False


def test_mercados_por_familia_en_orden_del_catalogo_con_otros_al_final(c, caso):
    ev = c.get(f'{base(caso)}/partido/{caso.partido_id}', params={'cliente': 'web'}).json()['evento']
    fams = c.get(f'{base(caso)}/partido/{caso.partido_id}/mercados', params={'cliente': 'web'}).json()['familias']
    ids = [f['id'] for f in fams]
    orden = ['fam_a', 'fam_b', 'otros']
    assert ids == [i for i in orden if i in ids] and 'fam_a' in ids and 'otros' == ids[-1]
    assert 'fam_oculta' not in ids                                      # visible_web=False
    assert all(f['mercados'] for f in fams)
    en_familias = {m['id'] for f in fams for m in f['mercados']}
    assert en_familias <= {m['id'] for m in ev['markets']}
    # `app` sí ve la familia que la web oculta
    ids_app = [f['id'] for f in c.get(f'{base(caso)}/partido/{caso.partido_id}/mercados',
                                      params={'cliente': 'app'}).json()['familias']]
    assert 'fam_oculta' in ids_app


@pytest.mark.parametrize('params', [{'dias': 0}, {'dias': 8}, {'tz': 841}, {'tz': -721}, {'contrato': 2},
                                    {'contrato': 0}, {'desde': '2026-13-45'}, {'desde': 'ayer'}, {'cliente': 'tv'}])
def test_parametros_invalidos_dan_422(c, caso, params):
    assert cartelera(c, caso, **params).status_code == 422


def test_cliente_obligatorio_y_contrato_en_partido_y_mercados(c, caso):
    assert c.get(f'{base(caso)}/cartelera').status_code == 422
    for ruta in (f'partido/{caso.partido_id}', f'partido/{caso.partido_id}/mercados'):
        assert c.get(f'{base(caso)}/{ruta}').status_code == 422
        assert c.get(f'{base(caso)}/{ruta}', params={'cliente': 'web', 'contrato': 2}).status_code == 422


def test_deporte_inexistente_u_off_da_404(c, caso, monkeypatch):
    for ruta in ('cartelera', f'partido/{caso.partido_id}', f'partido/{caso.partido_id}/mercados'):
        assert c.get(f'/deportes/v1/no_existe/{ruta}', params={'cliente': 'web'}).status_code == 404
    fijar_catalogo(monkeypatch, caso.deporte, caso.adaptador, web='off', app_='on')
    for ruta in ('cartelera', f'partido/{caso.partido_id}', f'partido/{caso.partido_id}/mercados'):
        assert c.get(f'{base(caso)}/{ruta}', params={'cliente': 'web'}).status_code == 404
        assert c.get(f'{base(caso)}/{ruta}', params={'cliente': 'app'}).status_code == 200


def test_preview_responde_con_noindex(c, caso, monkeypatch):
    fijar_catalogo(monkeypatch, caso.deporte, caso.adaptador, web='preview', app_='preview')
    for ruta in ('cartelera', f'partido/{caso.partido_id}', f'partido/{caso.partido_id}/mercados'):
        r = c.get(f'{base(caso)}/{ruta}', params={'cliente': 'web'})
        assert r.status_code == 200 and 'noindex' in r.headers['x-robots-tag']


def test_noindex_y_cache_siempre(c, caso):
    assert 'deportes' in seo.NOINDEX_SEGMENTS
    esperado = {'cartelera': 'public, max-age=30', f'partido/{caso.partido_id}': 'public, max-age=60',
                f'partido/{caso.partido_id}/mercados': 'public, max-age=60'}
    for ruta, cache in esperado.items():
        r = c.get(f'{base(caso)}/{ruta}', params={'cliente': 'web', 'desde': caso.desde})
        assert r.headers['cache-control'] == cache and 'noindex' in r.headers['x-robots-tag']
        assert r.headers['content-type'].startswith('application/json')


def test_partido_inexistente_o_ajeno_da_404(c, caso, monkeypatch):
    assert c.get(f'{base(caso)}/partido/no-existe', params={'cliente': 'web'}).status_code == 404
    assert c.get(f'{base(caso)}/partido/no-existe/mercados', params={'cliente': 'web'}).status_code == 404
    real = dv.ADAPTADORES[caso.adaptador]
    ajeno = _Proxy(real, partido=lambda id: real.partido(id).model_copy(update={'sport': 'otro'}))
    monkeypatch.setitem(dv.ADAPTADORES, caso.adaptador, ajeno)
    assert c.get(f'{base(caso)}/partido/{caso.partido_id}', params={'cliente': 'web'}).status_code == 404
    assert c.get(f'{base(caso)}/partido/{caso.partido_id}/mercados', params={'cliente': 'web'}).status_code == 404


def test_fuente_que_falla_da_503_no_200_vacio(c, caso, monkeypatch):
    caso.romper(monkeypatch)
    for ruta in ('cartelera', f'partido/{caso.partido_id}', f'partido/{caso.partido_id}/mercados'):
        r = c.get(f'{base(caso)}/{ruta}', params={'cliente': 'web', 'desde': caso.desde})
        assert r.status_code == 503 and set(r.json()) == {'detail'}
        assert not any(s in r.text for s in caso.centinelas)            # ni el texto de la excepción


class _Proxy:
    def __init__(self, real, **sustituciones):
        self._real, self._s = real, sustituciones

    def __getattr__(self, nombre):
        return self._s.get(nombre) or getattr(self._real, nombre)


def test_dato_fuera_de_contrato_da_503(c, caso, monkeypatch):
    real = dv.ADAPTADORES[caso.adaptador]
    for cambio in ({'status': 'raro'}, {'bloqueados': -1}, {'seal': 'xyz'}):
        def mala(i, f, cambio=cambio):
            return [e.model_copy(update=cambio) for e in real.cartelera(i, f)]
        monkeypatch.setitem(dv.ADAPTADORES, caso.adaptador, _Proxy(real, cartelera=mala))
        assert cartelera(c, caso).status_code == 503, cambio
    def mercado_malo(i, f):
        return [e.model_copy(update={'markets': [Mercado.model_construct(**{**m.model_dump(), 'outcome': 'raro'})
                                                 for m in e.markets]}) for e in real.cartelera(i, f)]
    monkeypatch.setitem(dv.ADAPTADORES, caso.adaptador, _Proxy(real, cartelera=mercado_malo))
    assert cartelera(c, caso).status_code == 503


def test_etag_y_304(c, caso):
    for ruta in ('cartelera', f'partido/{caso.partido_id}', f'partido/{caso.partido_id}/mercados'):
        url, q = f'{base(caso)}/{ruta}', {'cliente': 'web', 'desde': caso.desde}
        r = c.get(url, params=q)
        etag = r.headers['etag']
        assert etag.startswith('W/"')
        assert c.get(url, params=q).headers['etag'] == etag
        r2 = c.get(url, params=q, headers={'If-None-Match': etag})
        assert r2.status_code == 304 and r2.content == b'' and r2.headers['etag'] == etag
        assert 'noindex' in r2.headers['x-robots-tag']
        assert c.get(url, params=q, headers={'If-None-Match': 'W/"otro"'}).status_code == 200


def test_sin_efecto_de_authorization_ni_cookies(c, caso):
    for ruta in ('cartelera', f'partido/{caso.partido_id}', f'partido/{caso.partido_id}/mercados'):
        url, q = f'{base(caso)}/{ruta}', {'cliente': 'web', 'desde': caso.desde}
        anonimo = c.get(url, params=q)
        con = TestClient(app, cookies={'qf_session': 'x', 'session': 'y'}).get(
            url, params=q, headers={'Authorization': 'Bearer token-de-un-vip'})
        assert con.status_code == 200 and con.content == anonimo.content and con.headers['etag'] == anonimo.headers['etag']
        assert 'set-cookie' not in con.headers


def test_centinelas_no_salen(c, caso):
    textos = [cartelera(c, caso).text]
    for ruta in (f'partido/{caso.partido_id}', f'partido/{caso.partido_id}/mercados'):
        for cliente in ('web', 'app'):
            textos.append(c.get(f'{base(caso)}/{ruta}', params={'cliente': cliente}).text)
    for t in textos:
        assert not any(s in t for s in caso.centinelas)


# ── base común (sin adaptador real) ──────────────────────────────────────────

def test_adaptador_no_registrado_da_503_claro(c, monkeypatch):
    fijar_catalogo(monkeypatch, 'nuevo', 'inexistente')
    monkeypatch.delitem(dv.ADAPTADORES, 'inexistente', raising=False)
    for ruta in ('cartelera', 'partido/x', 'partido/x/mercados'):
        r = c.get(f'/deportes/v1/nuevo/{ruta}', params={'cliente': 'web'})
        assert r.status_code == 503 and r.json() == {'detail': 'Adaptador no disponible'}


def test_registro_arranca_sin_adaptadores_reales_ni_los_inventa():
    assert isinstance(AdaptadorPrueba('x'), dv.Adaptador)
    assert not isinstance(object(), dv.Adaptador)


def test_modelos_cerrados_y_con_rangos():
    ok = dict(id='1', label='l', selection='s', probability=0.5, eligible=True, market='m', family='f')
    assert Mercado(**ok).outcome is None
    for malo in ({'probability': 0}, {'probability': 1}, {'probability': 1.2}, {'outcome': 'ganada'}, {'extra': 1},
                 {'sealed_at': datetime(2026, 1, 1)}, {'push_probability': 2}):
        with pytest.raises(ValidationError):
            Mercado(**{**ok, **malo})
    for bueno in ('win', 'loss', 'push', 'void', None):
        Mercado(**{**ok, 'outcome': bueno})
    ev = dict(id='1', sport='s', home='h', away='a', league='l', start=datetime(2026, 1, 1, tzinfo=timezone.utc),
              status='scheduled')
    assert Evento(**ev).markets == [] and Evento(**ev).bloqueados == 0
    for malo in ({'status': 'postponed'}, {'extra': 1}, {'start': datetime(2026, 1, 1)}, {'bloqueados': -1},
                 {'imagenes': {'home': 'https://otro.com/x.png', 'away': None}},
                 {'imagenes': {'home': '//otro.com/x.png', 'away': None}}):
        with pytest.raises(ValidationError):
            Evento(**{**ev, **malo})
    for bueno in ESTADOS:
        Evento(**{**ev, 'status': bueno})


def test_las_horas_salen_en_utc():
    ev = Evento(id='1', sport='s', home='h', away='a', league='l', status='live',
                start=datetime(2026, 1, 1, 12, tzinfo=timezone(timedelta(hours=2))))
    assert ev.model_dump(mode='json')['start'] == '2026-01-01T10:00:00Z'


# ── catálogo: ids y slugs reservados ─────────────────────────────────────────

def _dep(**kw):
    d = {'deporte_id': 'hockey', 'adaptador': None, 'orden': 4, 'icono': 'hockey', 'color': '#aabbcc',
         'secciones': ['high'], 'nombre': dict(ES6), 'slug': {'es': 'hockey', 'en': 'hockey', 'pt': 'hoquei'},
         'estado_web': 'off', 'estado_app': 'off'}
    d.update(kw)
    return d


@pytest.mark.parametrize('reservado', sorted(catalogo.RESERVADOS))
def test_ids_y_slugs_reservados_se_rechazan(reservado):
    if reservado != 'nba':          # el id `nba` es el de la semilla (su propio deporte); lo que no puede es el slug de otro
        with pytest.raises(ValueError, match='reservado'):
            catalogo.validar_deporte(_dep(deporte_id=reservado))
    with pytest.raises(ValueError, match='reservado'):
        catalogo.validar_deporte(_dep(slug={'es': reservado, 'en': 'hockey', 'pt': 'hoquei'}))


@pytest.mark.parametrize('ruta', ['calibration', 'picks', 'matches', 'leagues'])
def test_un_primer_segmento_de_ruta_existente_se_rechaza(ruta):
    assert ruta in catalogo._segmentos_de_rutas()
    with pytest.raises(ValueError, match='reservado'):
        catalogo.validar_deporte(_dep(slug={'es': ruta, 'en': 'hockey', 'pt': 'hoquei'}))


def test_la_semilla_sigue_validando_y_solo_ella_usa_sus_nombres():
    from qf.comercial.catalogo_semilla import SEMILLA
    for d in SEMILLA:
        catalogo.validar_deporte(copy.deepcopy(d))
    # `nba` es suyo en la semilla, no de otro deporte
    with pytest.raises(ValueError, match='reservado'):
        catalogo.validar_deporte(_dep(slug={'es': 'nba', 'en': 'hockey', 'pt': 'hoquei'}))
    with pytest.raises(ValueError, match='reservado'):
        catalogo.validar_deporte(_dep(slug={'es': 'futbol', 'en': 'hockey', 'pt': 'hoquei'}))
    assert catalogo.validar_deporte(_dep())['deporte_id'] == 'hockey'


def test_la_ruta_generica_de_slug_no_se_ve_afectada(c, monkeypatch):
    """`/{slug}/` solo responde a slugs del catálogo; `/deportes/…` sigue siendo API y `noindex`."""
    assert c.get('/deportes/').status_code == 404
    assert 'noindex' in c.get('/deportes/v1/no_existe/cartelera', params={'cliente': 'web'}).headers['x-robots-tag']
