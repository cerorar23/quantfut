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


def test_open_pick_row_shows_the_sealed_probability_not_the_analysis(lista):
    """Auditoría 2026-10-25: el destacado decía 76 % y la lista 79 % para la misma selección."""
    filas, marcadores = lista
    row = pm.clave('totals', 'over', 1.5)
    out, _ = pm.aplicar_acceso(filas, marcadores, {row: {'prob': .76, 'ref_price': 1.25}}, plus=False)
    abierta = next(f for f in out if f['id'] == row)
    assert abierta['prob'] == .76 and abierta['nivel'] == 'alta'
    assert abierta['cuota'] == 1.25 and abierta['cuota_tipo'] == 'publicada'
    assert abierta['oportunidad'] is False                 # 0,76 × 1,25 = 0,95


def test_open_pick_missing_from_the_analysis_is_added_not_lost(lista):
    """El análisis da «12» en doble oportunidad; el pick gratis era «1X» y desaparecía."""
    filas, marcadores = lista
    assert pm.clave('double_chance', 'X2', None) not in {f['id'] for f in filas}
    pick = {'market': 'double_chance', 'selection': 'X2', 'line': None, 'prob': .74,
            'ref_price': 1.29, 'texto': 'Visita FC o empate'}
    out, marc = pm.aplicar_acceso(filas, marcadores, {pm.clave('double_chance', 'X2', None): pick}, plus=False)
    abiertas = [f for f in out if not f['locked']]
    assert [f['id'] for f in abiertas] == [pm.clave('double_chance', 'X2', None)]
    assert abiertas[0]['grupo'] == 'DOBLE OPORTUNIDAD' and abiertas[0]['seleccion'] == 'Visita FC o empate'
    assert abiertas[0]['prob'] == .74 and abiertas[0]['cuota'] == 1.29 and marc == marcadores
    assert len([f for f in out if f['locked']]) == len(filas)   # las del análisis siguen con candado
    dnb = {'market': 'spreads', 'selection': 'away', 'line': 0.0, 'prob': .7, 'price': 1.4}
    out, _ = pm.aplicar_acceso([], [], {pm.clave('spreads', 'away', 0.0): dnb}, plus=False)
    assert out[0]['grupo'] == 'EMPATE NO ACCIÓN' and out[0]['cuota'] == 1.4
    # Sin probabilidad o de un mercado desconocido no se inventa una fila.
    out, _ = pm.aplicar_acceso([], [], {'x': {'market': 'raro', 'prob': .8}, 'y': {'market': 'btts'}}, plus=False)
    assert out == []


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


def test_sin_modelo_de_goles_los_vip_salen_solo_con_su_categoria():
    vip = [{'match_id': 'm1', 'pick_key': 'k1', 'market': 'double_chance', 'prob': .9, 'price': 1.2},
           {'match_id': 'm1', 'pick_key': 'k2', 'market': 'corners', 'selection': 'under'},
           {'match_id': 'm1', 'pick_key': 'k3', 'market': 'raro'}]
    out = pm.solo_candados(vip)
    assert out['filas'] == [{'id': 'k1', 'grupo': 'DOBLE OPORTUNIDAD', 'locked': True},
                            {'id': 'k2', 'grupo': 'CÓRNERS', 'locked': True}]
    assert out['marcadores'] is None and out['sin_modelo'] is True and out['abiertas'] == 0
    assert pm.solo_candados([{'market': 'raro'}]) is None and pm.solo_candados([]) is None


def test_equipo_desconocido_toma_las_lambdas_del_mercado(monkeypatch):
    """Auditoría 2026-10-21: si el modelo no conoce a un equipo, sus lambdas no valen."""
    def consulta(sql, params):
        if 'FROM predictions' in sql:
            return {'home_lambda': 0.4, 'away_lambda': 3.1, 'rho': -0.06, 'conocido': 'false'}
        return {'fit': {'lambda': 1.2, 'mu': 1.4, 'rho': -0.05}}
    monkeypatch.setattr(pm, 'query_one', consulta)
    assert pm.lambdas_goles('m1') == (1.2, 1.4, -0.05)
    monkeypatch.setattr(pm, 'query_one', lambda sql, params: (
        {'home_lambda': 1.5, 'away_lambda': 1.1, 'rho': -0.06, 'conocido': 'true'} if 'FROM predictions' in sql else None))
    assert pm.lambdas_goles('m1') == (1.5, 1.1, -0.06)


# --- regla de la WEB: destacado de 1,40 en adelante (sin tope) y 3 mercados gratis -------------

def _en_rango(filas):
    return sorted((f for f in filas if f['cuota'] >= 1.40), key=lambda f: -f['prob'])


def test_el_rango_del_destacado_no_tiene_tope():
    assert pm.RANGO_DESTACADO == (1.40, None)
    assert pm.en_rango_destacado(1.40) and pm.en_rango_destacado(1.81) and pm.en_rango_destacado(25.0)
    assert not pm.en_rango_destacado(1.39) and not pm.en_rango_destacado(None) and not pm.en_rango_destacado(0)


def test_web_destacado_sale_de_todos_los_mercados_aunque_sean_vip(lista):
    filas, marcadores = lista
    esperado = _en_rango(filas)
    assert len(esperado) >= 3
    out, _, destacado = pm.aplicar_acceso_web(filas, marcadores, {}, plus=False)
    assert destacado['id'] == esperado[0]['id']
    assert destacado['cuota'] >= 1.40 and destacado['locked'] is False
    assert destacado['prob'] == max(f['prob'] for f in filas if f['cuota'] >= 1.40)


def test_web_gratis_tiene_tres_abiertas_las_mas_probables_del_rango_y_el_resto_con_candado(lista):
    filas, marcadores = lista
    out, marcadores_out, destacado = pm.aplicar_acceso_web(filas, marcadores, {}, plus=False)
    abiertas = [f for f in out if not f['locked']]
    assert [f['id'] for f in abiertas] == [f['id'] for f in _en_rango(filas)[:3]]
    assert abiertas[0]['id'] == destacado['id'] and abiertas[0]['destacado'] is True
    candados = [f for f in out if f['locked']]
    assert len(abiertas) + len(candados) == len(filas)
    assert all(set(f) == {'id', 'grupo', 'locked'} for f in candados)      # sin selección, prob ni cuota
    assert marcadores_out is None                                          # los marcadores no se regalan


def test_web_con_vip_todo_va_abierto_y_el_destacado_es_el_mismo(lista):
    filas, marcadores = lista
    _, _, gratis = pm.aplicar_acceso_web(filas, marcadores, {}, plus=False)
    out, marcadores_out, vip = pm.aplicar_acceso_web(filas, marcadores, {}, plus=True)
    assert not any(f['locked'] for f in out) and marcadores_out == marcadores
    assert vip['id'] == gratis['id']


def test_web_si_el_rango_no_da_para_tres_se_completa_con_las_mas_probables():
    def fila(i, prob):
        return pm._fila('GOLES', f'M{i}', 'totals', 'over', float(i), f'Más de {i}', prob)
    filas = [fila(1, .60), fila(2, .90), fila(3, .85), fila(4, .80)]   # solo la primera tiene cuota ≥ 1,40
    out, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado['id'] == filas[0]['id']
    assert {f['id'] for f in out if not f['locked']} == {filas[0]['id'], filas[1]['id'], filas[2]['id']}


def test_web_sin_ningun_mercado_en_rango_no_hay_destacado_pero_si_tres_gratis():
    def fila(i, prob):
        return pm._fila('GOLES', f'M{i}', 'totals', 'over', float(i), f'Más de {i}', prob)
    filas = [fila(1, .95), fila(2, .90), fila(3, .85), fila(4, .80)]   # todas por debajo de 1,40
    out, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado is None and sum(not f['locked'] for f in out) == 3


def test_web_una_cuota_larga_tambien_puede_ser_el_destacado():
    def fila(i, prob):
        return pm._fila('GOLES', f'M{i}', 'totals', 'over', float(i), f'Más de {i}', prob)
    filas = [fila(1, .95), fila(2, .90), fila(3, .20)]                 # solo la tercera tiene cuota ≥ 1,40 (5,00)
    _, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado['id'] == filas[2]['id'] and destacado['cuota'] >= 5


def test_web_un_pick_sellado_abierto_conserva_su_probabilidad_y_no_se_duplica(lista):
    filas, marcadores = lista
    objetivo = _en_rango(filas)[0]
    pick = {'pick_key': 'k1', 'market': objetivo['market'], 'selection': objetivo['selection'],
            'line': objetivo['line'], 'prob': .66, 'ref_price': 1.52}
    out, marcadores_out, destacado = pm.aplicar_acceso_web(filas, marcadores, {objetivo['id']: pick}, plus=False)
    fila = next(f for f in out if f['id'] == objetivo['id'])
    assert fila['prob'] == .66 and fila['cuota'] == 1.52 and fila['cuota_tipo'] == 'publicada'
    assert sum(f['id'] == objetivo['id'] for f in out) == 1
    assert marcadores_out == marcadores                                    # hay pick abierto: mismo trato que la app
    assert destacado['pick_key'] == 'k1'


def test_la_app_conserva_su_regla_sin_destacado_ni_gratis_extra(lista):
    filas, marcadores = lista
    out, marcadores_out = pm.aplicar_acceso(filas, marcadores, {}, plus=False)
    assert all(f['locked'] for f in out) and marcadores_out is None


def test_mercados_partido_pasa_la_regla_web_solo_cuando_se_pide(monkeypatch):
    from qf.api import mobile
    visto = []
    monkeypatch.setattr(pm, 'construir', lambda *a, **k: visto.append(a[-1] if len(a) > 5 else None) or {'ok': True})
    ficha = {'local': {'nombre': 'A'}, 'visitante': {'nombre': 'B'}}
    mobile.mercados_partido('m', ficha, [], False)
    mobile.mercados_partido('m', ficha, [], False, True)
    assert visto == [False, True]                 # la app (por defecto) nunca activa la regla de la web
    import inspect
    assert inspect.signature(mobile.detail).parameters['web'].default.default is False


# --- resultado de cada mercado (estado Acertó / Falló / Devolución) --------------------------

PARTIDO = {'home_goals': 2, 'away_goals': 0, 'home_goals_ht': 1, 'away_goals_ht': 0,
           'home_corners': 6, 'away_corners': 3, 'home_yellow': 2, 'away_yellow': 1,
           'home_red': 0, 'away_red': 1}


def _res(market, selection, line=None, partido=PARTIDO):
    return pm.resultado_fila({'market': market, 'selection': selection, 'line': line}, partido)


def test_resultado_de_los_mercados_de_marcador():
    assert _res('h2h', 'home') == 'win' and _res('h2h', 'draw') == 'loss'
    assert _res('totals', 'over', 1.5) == 'win' and _res('totals', 'under', 1.5) == 'loss'
    assert _res('btts', 'no') == 'win' and _res('btts', 'yes') == 'loss'
    assert _res('double_chance', 'X2') == 'loss' and _res('double_chance', '1X') == 'win'
    assert _res('team_totals_away', 'under', .5) == 'win'
    assert _res('win_to_nil', 'home') == 'win' and _res('win_to_nil', 'away') == 'loss'


def test_empate_no_accion_devuelve_en_empate_y_el_handicap_entero_tambien():
    empate = dict(PARTIDO, home_goals=1, away_goals=1)
    assert _res('spreads', 'home', 0.0, empate) == 'push'
    assert _res('spreads', 'home', -1.0) == 'win' and _res('spreads', 'home', -2.0) == 'push'
    assert _res('spreads', 'away', 1.5) == 'loss'


def test_primer_tiempo_corners_y_tarjetas_usan_sus_propias_estadisticas():
    assert _res('ht_btts', 'no') == 'win' and _res('ht_goal', 'yes') == 'win'
    assert _res('corners', 'over', 8.5) == 'win' and _res('corners', 'under', 8.5) == 'loss'
    assert _res('cards', 'under', 3.5) == 'loss' and _res('cards', 'over', 3.5) == 'win'  # 2+1+0+1 = 4


def test_sin_dato_no_se_inventa_resultado():
    sin = dict(PARTIDO, home_goals_ht=None, home_corners=None, home_yellow=None)
    assert _res('ht_goal', 'yes', None, sin) is None
    assert _res('corners', 'over', 8.5, sin) is None
    assert _res('cards', 'over', 3.5, sin) is None
    assert _res('h2h', 'home', None, dict(PARTIDO, home_goals=None)) is None
    assert pm.resultado_fila({'market': 'raro', 'selection': 'x', 'line': None}, PARTIDO) is None


def test_con_resultados_solo_marca_las_abiertas_y_nunca_las_bloqueadas():
    filas = [{'id': 'a', 'market': 'h2h', 'selection': 'home', 'line': None, 'locked': False},
             {'id': 'b', 'grupo': 'GOLES', 'locked': True}]
    out = pm.con_resultados(filas, dict(PARTIDO, status='finished'))
    assert out[0]['resultado'] == 'win' and 'resultado' not in out[1]
    assert 'resultado' not in pm.con_resultados(filas, dict(PARTIDO, status='scheduled'))[0]
    assert pm.con_resultados(filas, None)[0].get('resultado') is None


def test_destacados_resueltos_usa_el_analisis_sin_picks_y_solo_cuenta_los_resueltos(monkeypatch):
    from datetime import date, datetime, timezone
    kick = datetime(2026, 10, 26, 18, tzinfo=timezone.utc)
    base = {'league_id': 'it.serie_a', 'kickoff_utc': kick, 'home_goals': 2, 'away_goals': 1}
    partidos = [dict(base, match_id=m, local='A', visitante='B') for m in 'abcd']
    vistos = {}

    def construir(match_id, local, visitante, abiertas, plus, web=False):
        vistos[match_id] = (abiertas, plus, web)
        dest = {'market': 'totals', 'selection': 'over', 'line': 1.5, 'seleccion': 'Más de 1,5 goles',
                'prob': 0.69561, 'resultado': 'win'}
        return {'a': {'destacado': dest}, 'b': {'destacado': None},
                'c': {'destacado': dict(dest, resultado=None)}, 'd': None}[match_id]

    pedido = {}
    monkeypatch.setattr(pm, 'query', lambda sql, params=(): pedido.update(params=params) or partidos)
    monkeypatch.setattr(pm, 'construir', construir)
    pm._destacados.clear()
    items = pm.destacados_resueltos(date(2026, 10, 26))
    assert [i['match_id'] for i in items] == ['a']
    assert items[0]['outcome'] == 'win' and items[0]['prob'] == 0.6956 and items[0]['ref_price'] is None
    assert all(v == ({}, False, True) for v in vistos.values())
    assert pedido['params'][0] == datetime(2026, 10, 25, tzinfo=timezone.utc)


# --- el destacado de la web elige entre TODAS las opciones de los mercados de goles --------------------

def test_complementarias_son_el_otro_lado_y_las_otras_lineas_sin_repetir(lista):
    filas, _ = lista
    ya = {f['id'] for f in filas}
    extra = pm.filas_complementarias(LAM, MU, RHO, 'Local FC', 'Visita FC', set(ya))
    todas = filas + extra
    ids = [f['id'] for f in todas]
    assert len(ids) == len(set(ids)) and not (ya & {f['id'] for f in extra})       # ni repetidas ni pisan las del modelo
    assert all(f['prob'] >= pm.PROB_MIN_OPCION and f['cuota_tipo'] == 'justa' and not f['locked'] for f in extra)
    por_id = {f['id']: f for f in todas}
    for ln in pm.LINEAS_GOLES:                                                       # más + menos = 1 en cada línea
        total = por_id[pm.clave('totals', 'over', ln)]['prob'] + por_id[pm.clave('totals', 'under', ln)]['prob']
        assert total == pytest.approx(1, abs=2e-4)
    assert por_id[pm.clave('btts', 'yes', None)]['prob'] + por_id[pm.clave('btts', 'no', None)]['prob'] == pytest.approx(1, abs=2e-4)
    assert sum(por_id[pm.clave('h2h', s, None)]['prob'] for s in ('home', 'draw', 'away')) == pytest.approx(1, abs=2e-4)
    assert pm.clave('spreads', 'away', 1.0) in por_id                                # el complemento de «local −1»
    assert {f['grupo'] for f in extra} <= {'RESULTADO', 'DOBLE OPORTUNIDAD', 'EMPATE NO ACCIÓN', 'GOLES', 'GOLES DE EQUIPO',
                                           'AMBOS MARCAN', 'HÁNDICAP', 'ESPECIALES'}   # córners, tarjetas y 1T siguen validados


def test_el_destacado_puede_ser_una_opcion_que_no_era_el_lado_mas_probable():
    def f(i, prob, market='totals'):
        return pm._fila('GOLES', f'M{i}', market, 'over', float(i), f'Más de {i}', prob)
    mas_probables = [f(1, .90), f(2, .85), f(3, .80)]                    # todas por debajo de cuota 1,40: sin destacado
    _, _, sin = pm.aplicar_acceso_web(mas_probables, [], {}, plus=False)
    assert sin is None
    otro_lado = pm._fila('GOLES', 'M4', 'totals', 'under', 4.0, 'Menos de 4', .55)
    _, _, con = pm.aplicar_acceso_web(mas_probables + [otro_lado], [], {}, plus=False)
    assert con['id'] == otro_lado['id'] and con['cuota'] >= 1.40


def test_construir_web_suma_las_complementarias_y_la_app_no(monkeypatch):
    monkeypatch.setattr(pm, 'lambdas_goles', lambda mid: (LAM, MU, RHO))
    monkeypatch.setattr(pm, 'lambdas_estadisticas', lambda mid: (None, None))
    monkeypatch.setattr(pm, 'datos_partido', lambda mid: None)
    web = pm.construir('m1', 'Local FC', 'Visita FC', {}, False, web=True)
    app = pm.construir('m1', 'Local FC', 'Visita FC', {}, False, web=False)
    assert web['total'] > app['total'] >= 16                      # la web enseña más opciones; la app conserva su lista
    assert web['rango'] == [1.4, None] and web['destacado']['cuota'] >= 1.40
