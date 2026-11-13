"""Adaptador de fútbol del contrato `/deportes/v1/futbol` (Fase 3 parte D): reglas propias del deporte.

La suite genérica está en `test_deportes_v1.py` (caso `futbol`); la paridad con `football()` de la web, en
`test_deportes_futbol_paridad.py`. Los datos fijos y los parches de fuentes, en `datos_deportes_futbol.py`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import datos_deportes_futbol as datos
from qf.api import deportes_futbol, ratelimit
from qf.api import deportes_v1 as dv
from qf.api.deportes_futbol import AdaptadorFutbol
from qf.api.main import app
from qf.comercial import catalogo
from qf.comercial.catalogo_semilla import SEMILLA
from test_deportes_v1 import fijar_catalogo

UTC = timezone.utc
M1, M2, M3, M4, M5 = 'eu.ucl:m1', 'es.laliga:m2', 'es.laliga:m3', 'mx.ligamx:m4', 'mx.ligamx:m5'


@pytest.fixture
def fuentes(monkeypatch):
    monkeypatch.setattr(ratelimit, 'rate_limited', lambda *a, **k: False)
    f = datos.instalar_real(monkeypatch)
    fijar_catalogo(monkeypatch, 'futbol', 'futbol')
    return f


@pytest.fixture
def c(fuentes):
    return TestClient(app)


def ventana(dias=3):
    ini = datetime.fromisoformat(datos.DESDE + 'T00:00:00+00:00')
    return ini, ini + timedelta(days=dias)


def por_id(eventos):
    return {e.id: e for e in eventos}


def test_se_registra_al_importarse_y_cumple_la_interfaz():
    assert isinstance(dv.ADAPTADORES['futbol'], AdaptadorFutbol)
    assert isinstance(AdaptadorFutbol(), dv.Adaptador)


# ── league = competición ─────────────────────────────────────────────────────

def test_league_es_la_competicion_aunque_el_equipo_juegue_en_otra_liga(fuentes):
    """Real Madrid es de LaLiga, pero este partido es de Champions: `league` sale de `liga.nombre` de la agenda."""
    ev = por_id(AdaptadorFutbol().cartelera(*ventana()))
    assert ev[M1].league == 'UEFA Champions League' and ev[M1].home == 'Real Madrid'
    assert ev[M2].league == 'LaLiga' and ev[M4].league == 'Liga MX'
    assert 'LaLiga' not in ev[M1].model_dump_json()


def test_el_contrato_lo_dice_igual(c):
    r = c.get('/deportes/v1/futbol/partido/' + M1, params={'cliente': 'web'}).json()['evento']
    assert r['league'] == 'UEFA Champions League' and r['sport'] == 'futbol'


# ── bloqueados ───────────────────────────────────────────────────────────────

def test_bloqueados_cuenta_solo_el_numero(c, fuentes):
    cart = c.get('/deportes/v1/futbol/cartelera', params={'cliente': 'web', 'desde': datos.DESDE, 'dias': 3})
    eventos = {e['id']: e for e in cart.json()['eventos']}
    assert [eventos[i]['bloqueados'] for i in (M1, M2, M3, M4)] == [2, 0, 0, 1]
    part = c.get('/deportes/v1/futbol/partido/' + M1, params={'cliente': 'web'})
    assert part.json()['evento']['bloqueados'] == 2
    for texto in (cart.text, part.text):
        assert 'CENTINELA_VIP' not in texto and 'spreads' not in texto and '1.9' not in texto
    assert not any(m['market'] == 'spreads' for m in part.json()['evento']['markets'])


def test_las_filas_que_no_son_gratis_no_salen_aunque_vengan_en_la_lista(fuentes):
    ev = AdaptadorFutbol().partido(M1)
    assert 'CENTINELA_NOLIBRE' not in ev.model_dump_json()
    assert [m.id for m in ev.markets if m.id.startswith('pk')] == ['pk1', 'pk2']


# ── partido sin mercados públicos ────────────────────────────────────────────

def test_un_partido_sin_mercados_publicos_sale_igual(c, fuentes):
    cart = c.get('/deportes/v1/futbol/cartelera', params={'cliente': 'web', 'desde': datos.DESDE, 'dias': 3}).json()
    m2 = next(e for e in cart['eventos'] if e['id'] == M2)
    assert m2['markets'] == [] and m2['destacado'] is None and m2['seal'] is None and m2['sealed_at'] is None
    assert m2['status'] == 'scheduled' and m2['bloqueados'] == 0 and m2['planned_seal'] is not None
    assert m2['imagenes'] == {'home': '/web/escudos/3.png', 'away': None}
    part = c.get('/deportes/v1/futbol/partido/' + M2, params={'cliente': 'web'})
    assert part.status_code == 200 and part.json()['evento']['markets'] == []
    assert c.get('/deportes/v1/futbol/partido/' + M2 + '/mercados', params={'cliente': 'web'}).json()['familias'] == []


def test_la_fila_con_sello_invalido_no_se_publica(fuentes):
    ev = por_id(AdaptadorFutbol().cartelera(*ventana()))
    assert ev[M2].markets == [] and ev[M2].seal is None


def test_partido_que_no_existe_o_fuera_de_la_agenda_es_none(fuentes):
    assert AdaptadorFutbol().partido('no-existe') is None
    fuentes.agenda = [a for a in fuentes.agenda if a['match_id'] != M2]
    assert AdaptadorFutbol().partido(M2) is None


# ── anónimo ──────────────────────────────────────────────────────────────────

def test_misma_respuesta_con_y_sin_authorization_y_siempre_sin_vip(c, fuentes):
    for ruta in ('cartelera', 'partido/' + M1, 'partido/' + M1 + '/mercados'):
        url, q = '/deportes/v1/futbol/' + ruta, {'cliente': 'app', 'desde': datos.DESDE}
        anonimo = c.get(url, params=q)
        con = c.get(url, params=q, headers={'Authorization': 'Bearer token-de-un-vip'})
        assert con.status_code == 200 and con.content == anonimo.content
    assert fuentes.llamadas['alta'] and all(x['plus'] is False and not x['unlocks'] for x in fuentes.llamadas['alta'])
    assert all(x['plus'] is False and x['web'] is True for x in fuentes.llamadas['mercados'])


def test_cartelera_y_partido_piden_lo_que_cada_uno_necesita(fuentes):
    AdaptadorFutbol().cartelera(*ventana())
    assert [x['started'] for x in fuentes.llamadas['alta']] == [False] and not fuentes.llamadas['mercados']
    AdaptadorFutbol().partido(M1)
    assert fuentes.llamadas['alta'][-1]['started'] is True
    ficha = fuentes.llamadas['mercados'][-1]
    assert ficha['match_id'] == M1 and ficha['picks'] == ['pk1', 'pk2']
    assert ficha['ficha'] == {'local': {'nombre': 'Real Madrid'}, 'visitante': {'nombre': 'Manchester City'}}


# ── mapeo de campos ──────────────────────────────────────────────────────────

AHORA = datetime(2031, 3, 14, 12, tzinfo=UTC)


@pytest.mark.parametrize('crudo,desplazamiento,esperado', [
    ('finished', timedelta(hours=-10), 'finished'),
    ('postponed', timedelta(hours=10), 'cancelled'),
    ('live', timedelta(hours=-1), 'live'),
    ('scheduled', timedelta(hours=5), 'scheduled'),
    ('scheduled', timedelta(hours=-1), 'scheduled'),                # ya empezó pero la fuente no distingue «en juego»
    ('scheduled', timedelta(hours=-2, minutes=-59), 'scheduled'),
    ('scheduled', timedelta(hours=-3), 'awaiting_result'),
    ('scheduled', timedelta(days=-2), 'awaiting_result'),
    ('algo-nuevo', timedelta(hours=1), 'scheduled'),
])
def test_status_segun_el_estado_real_de_la_fuente(crudo, desplazamiento, esperado):
    assert deportes_futbol._estado(crudo, AHORA + desplazamiento, AHORA) == esperado


def test_el_aplazado_sale_cancelled_y_el_terminado_con_marcador(fuentes):
    ev = por_id(AdaptadorFutbol().cartelera(datetime(2031, 3, 14, tzinfo=UTC), datetime(2031, 4, 1, tzinfo=UTC)))
    assert ev[M5].status == 'cancelled' and ev[M5].score is None
    assert ev[M3].status == 'finished' and ev[M3].score == '2 – 1'
    assert ev[M1].score is None


def test_sello_y_fecha_del_sello(fuentes):
    ev = AdaptadorFutbol().partido(M1)
    assert ev.seal == datos.SELLO and ev.sealed_at == datetime(2031, 3, 14, tzinfo=UTC) and ev.planned_seal is None
    pk1, pk2 = (next(m for m in ev.markets if m.id == i) for i in ('pk1', 'pk2'))
    assert (pk1.eligible, pk1.sealed_at) == (True, datetime(2031, 3, 14, tzinfo=UTC))
    assert (pk2.eligible, pk2.sealed_at) == (False, datetime(2031, 3, 15, tzinfo=UTC))      # sello posterior al inicio


def test_imagenes_son_rutas_relativas_de_escudos(fuentes):
    ev = por_id(AdaptadorFutbol().cartelera(*ventana()))
    assert ev[M1].imagenes.model_dump() == {'home': '/web/escudos/1.png', 'away': '/web/escudos/2.png'}
    assert ev[M3].imagenes is None                                                      # sin escudo en ningún lado


def test_mercados_de_pick_y_destacado(fuentes):
    ev = AdaptadorFutbol().partido(M1)
    pk1 = next(m for m in ev.markets if m.id == 'pk1')
    assert (pk1.probability, pk1.price, pk1.reference, pk1.line, pk1.selection) == (.8, 1.4, 'Pinnacle', 2.5, 'Más de 2,5 goles')
    assert (pk1.market, pk1.family, pk1.outcome, pk1.label) == ('totals', 'goals', None, 'Pronóstico publicado')
    pk2 = next(m for m in ev.markets if m.id == 'pk2')
    assert pk2.price is None and pk2.reference is None                                  # sin cuota publicada
    assert ev.destacado == 'pk1'                                                        # la gratis de mayor probabilidad


def test_destacado_resuelto_de_un_partido_terminado(fuentes):
    ev = AdaptadorFutbol().partido(M3)
    assert [m.id for m in ev.markets] == ['destacado:' + M3] and ev.destacado == 'destacado:' + M3
    m = ev.markets[0]
    assert (m.outcome, m.probability, m.price, m.reference, m.eligible, m.sealed_at) == (
        'win', .81, 1.3, 'Pinnacle', True, None)
    assert (m.market, m.family, m.line) == ('totals', 'goals', 1.5)
    assert ev.seal is None and ev.sealed_at is None


def test_destacado_que_coincide_con_un_pick_no_se_repite(fuentes):
    fuentes.proximos.append(datos._pick(M3, 'pk3', 'totals', 'over', 1.5, .8, 'Más de 1,5 goles', outcome='loss',
                                        local='Girona', visitante='Getafe'))
    ev = AdaptadorFutbol().partido(M3)
    assert [m.id for m in ev.markets] == ['pk3'] and ev.destacado == 'pk3'
    assert ev.markets[0].outcome == 'loss'                                              # el liquidado del pick manda


def test_planned_seal_mientras_no_hay_pronostico(fuentes):
    ev = por_id(AdaptadorFutbol().cartelera(*ventana()))
    assert ev[M4].planned_seal is not None and ev[M4].planned_seal < ev[M4].start
    assert ev[M3].planned_seal is None and ev[M1].planned_seal is None


def test_mercados_abiertos_del_partido_son_analisis_no_sellado(fuentes):
    ev = AdaptadorFutbol().partido(M1)
    ids = [m.id for m in ev.markets]
    assert ids == ['pk1', 'pk2', 'h2h:home:None', 'double_chance:1X:None', 'btts:yes:None']   # sin repetir pk1 ni el candado
    h2h, dc, _ = ev.markets[2:]
    assert (h2h.eligible, h2h.sealed_at, h2h.price, h2h.reference, h2h.family) == (False, None, 1.8, 'bet365', 'winner')
    assert (dc.price, dc.reference, dc.family) == (None, None, 'double_chance')        # cuota justa 1/p: no se inventa
    assert 'CENTINELA_NOTA' not in ev.model_dump_json() and 'CENTINELA_BLOQUEADO' not in ev.model_dump_json()


def test_sin_modelo_de_goles_el_partido_sigue_con_sus_picks(fuentes):
    fuentes.mercados.clear()                                                            # mercados_partido devuelve None
    assert [m.id for m in AdaptadorFutbol().partido(M1).markets] == ['pk1', 'pk2']


# ── familias ─────────────────────────────────────────────────────────────────

def test_familia_de_mapea_a_familias_del_catalogo_de_futbol():
    ids = {f['familia_id'] for f in next(d for d in SEMILLA if d['deporte_id'] == 'futbol')['familias']}
    assert ids == {'corners_team', 'handicap', 'team_goals', 'double_chance', 'corners', 'goals', 'cards', 'winner'}
    a = AdaptadorFutbol()
    esperado = {'totals': 'goals', 'team_totals_home': 'team_goals', 'team_totals_away': 'team_goals',
                'corners': 'corners', 'corners_home': 'corners_team', 'corners_away': 'corners_team',
                'spreads': 'handicap', 'double_chance': 'double_chance', 'h2h': 'winner', 'cards': 'cards'}
    for mercado, familia in esperado.items():
        assert a.familia_de(mercado) == familia and familia in ids
    assert set(esperado.values()) == ids                                               # las 8 se alcanzan
    for desconocido in ('btts', 'ht_btts', 'win_to_nil', 'inventado', ''):
        assert a.familia_de(desconocido) == 'otros'


def test_mercados_con_el_catalogo_real_de_futbol(c, monkeypatch):
    """Con las familias reales de la semilla, goles y ganador caen en las suyas y btts en `otros`."""
    monkeypatch.setattr(catalogo, '_cargar', lambda: catalogo._ordenar(
        [__import__('copy').deepcopy(d) for d in SEMILLA]))
    catalogo.invalidar_cache()
    fams = c.get('/deportes/v1/futbol/partido/' + M1 + '/mercados', params={'cliente': 'web'}).json()['familias']
    grupos = {f['id']: [m['id'] for m in f['mercados']] for f in fams}
    assert grupos == {'double_chance': ['double_chance:1X:None'], 'corners': ['pk2'], 'goals': ['pk1'],
                      'winner': ['h2h:home:None'], 'otros': ['btts:yes:None']}
    catalogo.invalidar_cache()


# ── fallos ───────────────────────────────────────────────────────────────────

def test_si_la_fuente_falla_la_excepcion_sube(fuentes):
    fuentes.roto = True
    with pytest.raises(RuntimeError):
        AdaptadorFutbol().cartelera(*ventana())
    with pytest.raises(RuntimeError):
        AdaptadorFutbol().partido(M1)


def test_la_respuesta_no_lleva_ningun_campo_interno(c):
    textos = [c.get('/deportes/v1/futbol/cartelera', params={'cliente': 'web', 'desde': datos.DESDE, 'dias': 3}).text]
    for ruta in ('partido/' + M1, 'partido/' + M1 + '/mercados', 'partido/' + M3):
        textos.append(c.get('/deportes/v1/futbol/' + ruta, params={'cliente': 'app'}).text)
    for t in textos:
        for interno in datos.CENTINELAS + ('"fit"', '"xg"', '"fair_price"', '"oportunidad"', '"nivel"', '"racha"', '"posicion"'):
            assert interno not in t, interno
        json.loads(t)
