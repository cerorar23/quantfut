"""Lista de mercados del partido: coherencia con el modelo, líneas validadas y candados."""
import pytest

from qf.api import partido_mercados as pm
from qf.model import estadisticas_mercado as em
from qf.model import pricing

LAM, MU, RHO = 1.457, .7185, -.06


@pytest.fixture(scope='module')
def lista():
    return pm.filas_goles(LAM, MU, RHO, 'Local FC', 'Visita FC')


def test_goal_rows_match_the_stored_market_package(lista):
    filas, _ = lista
    stored = pricing.price_all_markets(LAM, MU, RHO)
    by_id = {f['id']: f for f in filas}
    assert by_id[pm.clave('totals', 'under', 2.5)]['prob'] == pytest.approx(stored['totals']['2.5']['under'], abs=1e-4)
    assert by_id[pm.clave('btts', 'no', None)]['prob'] == pytest.approx(stored['btts']['no'], abs=1e-4)
    assert by_id[pm.clave('team_totals_home', 'over', .5)]['prob'] == pytest.approx(
        stored['team_totals']['home']['0.5']['over'], abs=1e-4)
    assert by_id[pm.clave('h2h', 'home', None)]['prob'] == pytest.approx(stored['1x2']['home'], abs=1e-4)


def test_every_row_shows_its_more_likely_side_and_a_fair_quote(lista):
    filas, marcadores = lista
    assert all(f['prob'] >= .5 for f in filas if f['grupo'] not in ('HÁNDICAP', 'ESPECIALES'))  # el lado más probable
    for f in filas:
        assert f['cuota'] == pytest.approx(1 / f['prob'], abs=.01) and f['cuota_tipo'] == 'justa'
        assert f['nivel'] == pm.nivel(f['prob']) and not f['locked']
    assert len(marcadores) == pm.MARCADORES and marcadores == sorted(marcadores, key=lambda r: -r['prob'])


def test_win_to_nil_and_handicap_are_derived_from_the_score_matrix(lista):
    filas, _ = lista
    m = pricing.score_matrix(LAM, MU, RHO)
    nil = next(f for f in filas if f['market'] == 'win_to_nil')
    assert nil['selection'] == 'home' and nil['prob'] == pytest.approx(float(m[1:, 0].sum()), abs=1e-4)
    assert {f['id'] for f in filas if f['grupo'] == 'HÁNDICAP'} == {
        pm.clave('spreads', 'home', -1.0), pm.clave('spreads', 'home', -1.5), pm.clave('spreads', 'away', 1.5)}


def test_corners_and_cards_only_use_validated_lines():
    filas = pm.filas_estadisticas((5.0, 3.8), (2.4, 2.0))
    got = {(f['market'], f['selection'], f['line']) for f in filas}
    want = {(mk, lado, ln) for mk in ('corners', 'cards') for lado, ln in em.LINEAS_HABILITADAS[mk]}
    assert got == want                                     # ni una línea más
    assert ('corners', 'over', 9.5) not in got            # esa línea NO pasó la prueba histórica
    assert pm.filas_estadisticas(None, None) == []
    assert {f['grupo'] for f in pm.filas_estadisticas((5.0, 3.8), None)} == {'CÓRNERS'}


def test_locked_rows_reveal_only_the_category_and_do_not_sort_by_probability(lista):
    filas, marcadores = lista
    filas = filas + pm.filas_estadisticas((5.0, 3.8), (2.4, 2.0))
    abiertas = {pm.clave('totals', 'over', 1.5): {'ref_price': 1.19}}
    out, marc = pm.aplicar_acceso(filas, marcadores, abiertas, plus=False)
    assert marc == marcadores                               # el pronóstico abierto trae sus marcadores
    abierta = [f for f in out if not f['locked']]
    assert [f['id'] for f in abierta] == [pm.clave('totals', 'over', 1.5)]
    assert abierta[0]['cuota'] == 1.19 and abierta[0]['cuota_tipo'] == 'publicada'
    cerradas = [f for f in out if f['locked']]
    assert len(cerradas) == len(filas) - 1
    for c in cerradas:
        assert set(c) == {'id', 'grupo', 'locked'}          # nada más: ni línea, ni prob, ni cuota
    orden = [pm.GRUPOS.index(c['grupo']) for c in cerradas]
    assert orden == sorted(orden)                           # orden canónico, no por probabilidad


def test_sin_pronostico_abierto_ni_vip_no_hay_marcadores(lista):
    filas, marcadores = lista
    out, marc = pm.aplicar_acceso(filas, marcadores, {}, plus=False)
    assert marc is None and all(f['locked'] for f in out)


def test_vip_sees_everything_and_marks_real_value_only_with_a_published_quote(lista):
    filas, marcadores = lista
    out, marc = pm.aplicar_acceso(filas, marcadores, {}, plus=True)
    assert marc == marcadores and not any(f['locked'] for f in out)
    assert [f['prob'] for f in out] == sorted((f['prob'] for f in out), reverse=True)
    assert not any(f.get('oportunidad') for f in out)       # sin cuota publicada no hay «oportunidad»
    row = pm.clave('totals', 'over', 1.5)
    high = pm.aplicar_acceso(filas, marcadores, {row: {'ref_price': 2.0}}, plus=False)[0][0]
    assert high['oportunidad'] is True                      # prob × cuota publicada > 1,02


def test_nivel_boundaries():
    assert [pm.nivel(p) for p in (.75, .7499, .60, .5999)] == ['alta', 'solida', 'solida', 'moderada']
    assert pm.clave('totals', 'over', 1.5) == 'totals:over:1.5' and pm.clave('h2h', 'home', None) == 'h2h:home:None'


def test_first_half_publishes_only_the_two_validated_markets_inside_the_measured_range():
    filas = pm.filas_primer_tiempo(2.41, .76)
    assert {f['id'] for f in filas} == {pm.clave('ht_btts', 'no', None), pm.clave('ht_goal', 'yes', None)}
    assert all(f['grupo'] == '1ª MITAD' and .62 <= f['prob'] <= .95 for f in filas)
    # partido cerrado: «gol en 1T: sí» cae por debajo de lo medido -> no se publica; el «no» tampoco existe
    assert [f['market'] for f in pm.filas_primer_tiempo(.9, .7)] == ['ht_btts']
    # partido abierto: «ambos 1T: no» cae por debajo de lo medido -> solo «gol en 1T»
    assert [f['market'] for f in pm.filas_primer_tiempo(3.2, 2.4)] == ['ht_goal']
    assert pm.GRUPOS.index('1ª MITAD') < pm.GRUPOS.index('CÓRNERS')


def test_first_half_model_is_a_proper_distribution():
    from qf.model import primer_tiempo as m
    p = m.probs(1.46, .72)
    assert p['ganador_1t_local'] + p['ganador_1t_empate'] + p['ganador_1t_visita'] == pytest.approx(1)
    assert 0 < p['ambos_1t_si'] < p['gol_1t_si'] < 1
