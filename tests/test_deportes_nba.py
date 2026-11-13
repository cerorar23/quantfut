"""Adaptador de NBA del contrato /deportes/v1: ventana UTC ↔ días ET, deduplicación, mapeo y llamadas a la fuente."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from nba_contrato_datos import MERCADOS_103, SELLO_A, NbaApiFalsa, instalar, partido, romper

from qf.api import deportes_nba, nba_datos
from qf.api.deportes_nba import AdaptadorNba, dias_et
from qf.api.deportes_v1 import ADAPTADORES

UTC = timezone.utc


def utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


@pytest.fixture
def falsa(monkeypatch):
    return instalar(monkeypatch)


def test_se_registra_al_importarse():
    assert isinstance(ADAPTADORES['nba'], AdaptadorNba)


def test_dias_et_con_margen_y_cruce_de_dia():
    # 01:00 UTC del 12-nov son las 20:00 ET del 11-nov: la ventana UTC que empieza el 12 toca el día ET 11
    dias = dias_et(utc('2026-11-12T00:00:00'), utc('2026-11-13T00:00:00'))
    assert [d.isoformat() for d in dias] == ['2026-11-10', '2026-11-11', '2026-11-12', '2026-11-13']


def test_dias_et_ignora_la_pretemporada():
    dias = dias_et(utc('2026-10-14T00:00:00'), utc('2026-10-22T00:00:00'))
    assert dias[0].isoformat() == '2026-10-20'


def test_dias_et_cambio_de_hora():
    # 2026-11-01 cambia a horario estándar: 00:30 UTC del 2-nov son las 19:30 ET del 1-nov
    dias = dias_et(utc('2026-11-02T00:30:00'), utc('2026-11-02T01:00:00'))
    assert [d.isoformat() for d in dias] == ['2026-10-31', '2026-11-01', '2026-11-02']


def test_el_partido_de_la_1_am_utc_pertenece_al_dia_et_anterior(falsa):
    eventos = AdaptadorNba().cartelera(utc('2026-11-12T00:00:00'), utc('2026-11-13T00:00:00'))
    assert [e.id for e in eventos] == ['99'] and eventos[0].start == utc('2026-11-12T01:00:00')
    assert '2026-11-11' in falsa.dias_pedidos


def test_filtra_por_start_dentro_de_la_ventana(falsa):
    eventos = AdaptadorNba().cartelera(utc('2026-11-13T00:00:00'), utc('2026-11-14T00:00:00'))
    assert sorted(e.id for e in eventos) == ['100', '101']          # el 99 (01:00 del 12) y el 102 (01:00 del 14) quedan fuera


def test_deduplica_por_id_entre_dias(monkeypatch):
    p = partido(100, 'Denver Nuggets', 'Utah Jazz', '2026-11-12', '2026-11-13T00:00:00+00:00')
    instalar(monkeypatch, NbaApiFalsa(dias={'2026-11-12': [p], '2026-11-13': [p, p]}))
    eventos = AdaptadorNba().cartelera(utc('2026-11-12T00:00:00'), utc('2026-11-15T00:00:00'))
    assert [e.id for e in eventos] == ['100']


def test_llamadas_a_la_fuente_son_los_dias_et_necesarios(falsa):
    ini, fin = utc('2026-11-12T00:00:00'), utc('2026-11-19T00:00:00')
    AdaptadorNba().cartelera(ini, fin)
    esperados = [d.isoformat() for d in dias_et(ini, fin)]
    assert sorted(falsa.dias_pedidos) == esperados and len(esperados) == 10      # 8 días ET que toca la ventana UTC de 7 días + 1 de margen por lado
    assert len(set(falsa.dias_pedidos)) == len(falsa.dias_pedidos)
    # una segunda petición idéntica sale de la caché de nba_datos: ni una llamada más
    AdaptadorNba().cartelera(ini, fin)
    assert len(falsa.llamadas) == 10


def test_un_dia_que_falla_lanza_y_no_devuelve_lista_parcial(monkeypatch):
    falsa = NbaApiFalsa()
    instalar(monkeypatch, falsa)

    def a_medias(ruta, params=None):
        if params and params.get('fecha') == '2026-11-13':
            raise nba_datos.NbaNoDisponible('caído')
        return falsa(ruta, params)
    monkeypatch.setattr(nba_datos, '_pedir', a_medias)
    with pytest.raises(nba_datos.NbaNoDisponible):
        AdaptadorNba().cartelera(utc('2026-11-12T00:00:00'), utc('2026-11-19T00:00:00'))


def test_estados_y_marcador(falsa):
    por_id = {e.id: e for e in AdaptadorNba().cartelera(utc('2026-11-12T00:00:00'), utc('2026-11-19T00:00:00'))}
    assert por_id['101'].status == 'finished' and por_id['101'].score == '99 – 104'
    assert por_id['100'].status == 'awaiting_result'          # AHORA = 12:00 UTC del 13; empezó a las 00:00 del 13
    assert por_id['102'].status == 'scheduled' and por_id['102'].planned_seal == utc('2026-11-14T00:30:00')
    assert por_id['102'].markets == [] and por_id['102'].seal is None and por_id['102'].destacado is None
    assert por_id['100'].seal == SELLO_A and por_id['100'].league == 'NBA' and por_id['100'].bloqueados == 0
    assert por_id['100'].imagenes is None


def test_empezo_hace_menos_de_cuatro_horas_sigue_programado(monkeypatch):
    instalar(monkeypatch)
    monkeypatch.setattr(deportes_nba, '_ahora', lambda: utc('2026-11-13T03:59:00'))
    e = {x.id: x for x in AdaptadorNba().cartelera(utc('2026-11-13T00:00:00'), utc('2026-11-14T00:00:00'))}
    assert e['100'].status == 'scheduled'


def test_ganador_mercado_destacado_y_resultado(falsa):
    por_id = {e.id: e for e in AdaptadorNba().cartelera(utc('2026-11-12T00:00:00'), utc('2026-11-19T00:00:00'))}
    g100, g101 = por_id['100'].markets[0], por_id['101'].markets[0]
    assert (g100.id, g100.selection, g100.probability, g100.outcome, g100.eligible) == ('winner-100', 'Denver Nuggets', 0.62, None, True)
    # p_local .30 -> favorito el visitante con .70; ganó el visitante
    assert (g101.selection, round(g101.probability, 6), g101.outcome) == ('Los Angeles Lakers', 0.7, 'win')
    assert por_id['101'].destacado is None      # .70 no llega al 75 %: la cartelera sigue la regla de la web
    assert por_id['100'].markets[0].principal is True


def test_sello_posterior_al_inicio_no_es_elegible_ni_tiene_resultado(falsa):
    ev = AdaptadorNba().partido('103')
    g = ev.markets[0]
    assert g.id == 'winner-103' and g.eligible is False and g.outcome is None


def test_partido_trae_los_mercados_publicos(falsa):
    ev = AdaptadorNba().partido('103')
    ids = [m.id for m in ev.markets]
    assert ids == ['winner-103', 'spreads-1-5.5-local', 'totals-None-228.5-over', 'player_points-77-24.5-over']
    m = {x.id: x for x in ev.markets}
    h, t, j = m['spreads-1-5.5-local'], m['totals-None-228.5-over'], m['player_points-77-24.5-over']
    assert (h.family, h.line, h.price, h.reference, h.selection) == ('handicap', -5.5, 1.91, 'pinnacle', 'Phoenix Suns -5.5')
    assert (t.selection, t.label, t.price) == ('Más de 228.5 puntos', 'Total del partido', 1.95)
    assert (j.player, j.player_id, j.price, j.label, j.reference) == ('Devin Booker', '77', None, 'Puntos de Devin Booker', 'Probabilidad estadística')
    assert ev.destacado == 'totals-None-228.5-over'      # el que eligió el servidor


def test_partido_inexistente_o_con_id_raro_es_none(falsa):
    a = AdaptadorNba()
    assert a.partido('999') is None and a.partido('abc') is None and a.partido('1' * 40) is None


def test_partido_no_llama_a_mercados_si_no_existe(falsa):
    AdaptadorNba().partido('999')
    assert not [r for r, _ in falsa.llamadas if r.endswith('/mercados')]


def test_familia_de():
    a = AdaptadorNba()
    assert [a.familia_de(f) for f in deportes_nba.FAMILIAS] == list(deportes_nba.FAMILIAS)
    assert a.familia_de('desconocida') == 'otros'


def test_mercado_con_probabilidad_fuera_de_rango_se_descarta(monkeypatch):
    mk = {'partido_id': 103, 'markets': [{**m, 'probability': 1.0} for m in MERCADOS_103['markets']],
          'projections': [], 'destacado': None}
    instalar(monkeypatch, NbaApiFalsa(mercados={103: mk}))
    assert [m.id for m in AdaptadorNba().partido('103').markets] == ['winner-103']


def test_fuente_caida_lanza(monkeypatch):
    instalar(monkeypatch)
    romper(monkeypatch)
    with pytest.raises(nba_datos.NbaNoDisponible):
        AdaptadorNba().cartelera(utc('2026-11-12T00:00:00'), utc('2026-11-19T00:00:00'))
    with pytest.raises(nba_datos.NbaNoDisponible):
        AdaptadorNba().partido('103')


# ── cartelera completa para la web: destacado (regla 75 %–83,3 %), ganador revisado y puntos esperados ───────────────

def _una_cartelera(monkeypatch, p_local, sellado='antes', mu=True, inicio='2026-11-13T00:00:00+00:00'):
    p = partido(500, 'Denver Nuggets', 'Utah Jazz', '2026-11-12', inicio, p_local=p_local, sellado=sellado)
    if not mu:
        p['pronostico'].pop('mu')
    instalar(monkeypatch, NbaApiFalsa(dias={'2026-11-12': [p]}))
    return AdaptadorNba().cartelera(utc('2026-11-12T00:00:00'), utc('2026-11-15T00:00:00'))[0]


# Los mismos casos que `featuredSportMarket` (frontend/sports-data.js) resuelve sobre el ganador del modelo: cuota = 1 ÷ probabilidad >= 1,20 y prob >= 75 %.
@pytest.mark.parametrize('p_local, destacado', [
    (0.75, True), (0.7499, False), (0.80, True), (0.83, True), (0.8333, True), (0.8334, False),
    (0.84, False), (0.95, False), (0.62, False), (0.25, True), (0.20, True), (0.17, True), (0.16, False), (0.30, False)])
def test_destacado_de_la_cartelera_sigue_la_regla_de_la_web(monkeypatch, p_local, destacado):
    e = _una_cartelera(monkeypatch, p_local)
    assert e.destacado == ('winner-500' if destacado else None)
    assert [m.id for m in e.markets] == ['winner-500']              # el ganador va siempre, sea o no el destacado


def test_ganador_revisado_no_es_destacado_pero_sigue_en_el_evento(monkeypatch):
    e = _una_cartelera(monkeypatch, 0.78, sellado='despues')
    assert e.destacado is None and [m.id for m in e.markets] == ['winner-500']
    assert e.markets[0].eligible is False and e.markets[0].principal is True


def test_sin_pronostico_no_hay_mercados_ni_destacado(monkeypatch):
    e = _una_cartelera(monkeypatch, 0.5, sellado=None)
    assert e.markets == [] and e.destacado is None and e.team_projection is None


def test_team_projection_es_mu_local_y_visitante(monkeypatch):
    assert _una_cartelera(monkeypatch, 0.6).team_projection == [111.7, 116.4]
    assert _una_cartelera(monkeypatch, 0.6, mu=False).team_projection is None


@pytest.mark.parametrize('mu', [[111.7], [1, 2, 3], ['a', 2], [float('nan'), 2], [True, 2], 'x', None])
def test_team_projection_invalida_se_omite(monkeypatch, mu):
    p = partido(500, 'Denver Nuggets', 'Utah Jazz', '2026-11-12', '2026-11-13T00:00:00+00:00')
    p['pronostico']['mu'] = mu
    instalar(monkeypatch, NbaApiFalsa(dias={'2026-11-12': [p]}))
    assert AdaptadorNba().cartelera(utc('2026-11-12T00:00:00'), utc('2026-11-15T00:00:00'))[0].team_projection is None
