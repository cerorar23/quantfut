"""Pronóstico destacado por valor esperado: filtro (cuota >= 1,20 y prob >= 55 %), puntuación prob × cuota y desempate."""
import json
from datetime import datetime, timezone

import pytest

from qf.api import destacado_valor as dv
from qf.api import partido_mercados as pm


def m(id_, prob, ref_price, **extra):
    return {'id': id_, 'prob': prob, 'ref_price': ref_price, **extra}


# --- el dilema pedido por el titular ---------------------------------------------------------

def test_cuota_180_con_70_por_ciento_gana_a_cuota_120_con_75_por_ciento_por_su_score():
    seguro = m('seguro', .75, 1.20)        # score 0,90: el más probable, pero paga poco
    valor = m('valor', .70, 1.80)          # score 1,26
    for orden in ([seguro, valor], [valor, seguro]):
        ganador = dv.elegir_destacado(orden)
        assert ganador['id'] == 'valor'
        assert ganador['score_destacado'] == pytest.approx(1.26)
    assert dv.score_destacado(.75, 1.20) == pytest.approx(.90)
    assert dv.score_destacado(.75, 1.20) < dv.score_destacado(.70, 1.80)


def test_el_dilema_tambien_se_resuelve_en_la_lista_de_mercados_de_futbol():
    hora = datetime(2026, 11, 5, 10, tzinfo=timezone.utc)
    seguro = pm._fila('GOLES', 'Goles totales', 'totals', 'over', 1.5, 'Más de 1,5 goles', .75)
    valor = pm._fila('GOLES', 'Goles totales', 'totals', 'under', 3.5, 'Menos de 3,5 goles', .70)
    filas = pm.con_cuotas_casas([seguro, valor], {seguro['id']: (1.20, 'bet365', hora), valor['id']: (1.80, 'bet365', hora)})
    _, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado['id'] == valor['id'] and destacado['score_destacado'] == pytest.approx(1.26)
    assert destacado['destacado'] is True and destacado['locked'] is False


# --- filtro de entrada -------------------------------------------------------------------------

def test_cuota_minima_1_20_incluida_y_probabilidad_minima_55_incluida():
    assert dv.elegir_destacado([m('a', .55, 1.20)])['id'] == 'a'
    assert dv.elegir_destacado([m('a', .60, 1.1999)]) is None
    assert dv.elegir_destacado([m('a', .5499, 3.0)]) is None


def test_una_cuota_enorme_con_poca_probabilidad_nunca_es_destacado():
    assert dv.elegir_destacado([m('loteria', .20, 5.0), m('segura', .90, 1.10)]) is None


def test_el_filtro_deja_fuera_aunque_el_score_sea_mayor():
    ganador = dv.elegir_destacado([m('baja_prob', .50, 2.50), m('ok', .60, 1.40)])      # 1,25 > 0,84
    assert ganador['id'] == 'ok'


def test_si_nadie_pasa_el_filtro_es_none():
    assert dv.elegir_destacado([]) is None
    assert dv.elegir_destacado([m('a', .90, 1.05), m('b', .40, 2.5)]) is None


# --- desempate y robustez ---------------------------------------------------------------------

def test_empate_de_score_gana_la_mayor_probabilidad():
    a, b = m('a', .60, 1.50), m('b', .75, 1.20)                                          # ambos 0,90
    assert dv.score_destacado(.60, 1.50) == dv.score_destacado(.75, 1.20)
    for orden in ([a, b], [b, a]):
        assert dv.elegir_destacado(orden)['id'] == 'b'


def test_empate_total_gana_el_primero_de_la_lista():
    assert dv.elegir_destacado([m('x', .60, 1.50), m('y', .60, 1.50)])['id'] == 'x'


def test_el_ruido_de_coma_flotante_no_decide_empates():
    # prob × (1 ÷ prob) da 0,9999999999999999 o 1,0000000000000002 según la prob: todos valen 1 y manda la probabilidad
    probs = [.57, .58, .59, .61, .63, .67, .71, .77, .81]
    items = [m(f'p{p}', p, 1 / p) for p in probs]
    assert dv.elegir_destacado(items)['id'] == 'p0.81'
    assert dv.elegir_destacado(list(reversed(items)))['id'] == 'p0.81'


def test_datos_invalidos_se_ignoran_sin_romper():
    basura = [m('nan', float('nan'), 1.5), m('inf', .6, float('inf')), m('none', None, 1.5), m('str', '.7', 1.5),
              m('bool', True, 1.5), {'id': 'sin_campos'}, m('ok', .60, 1.50)]
    assert dv.elegir_destacado(basura)['id'] == 'ok'


def test_no_modifica_el_mercado_original_y_acepta_otros_nombres_de_campo():
    original = {'id': 'a', 'probability': .6, 'price': 1.7}
    ganador = dv.elegir_destacado([original], prob='probability', precio='price')
    assert 'score_destacado' not in original and ganador['score_destacado'] == pytest.approx(1.02)
    assert dv.elegir_destacado([original], prob='probability', precio=lambda x: x['price'] * 2)['score_destacado'] == pytest.approx(2.04)


# --- fútbol: acceso de la web ---------------------------------------------------------------------

def fila(i, prob, linea=None, market='totals', sel='over'):
    return pm._fila('GOLES', f'M{i}', market, sel, float(i) if linea is None else linea, f'Más de {i}', prob)


def test_rango_del_destacado_arranca_en_1_20_y_no_tiene_tope():
    assert pm.RANGO_DESTACADO == (1.20, None)
    assert pm.en_rango_destacado(1.20) and pm.en_rango_destacado(25.0)
    assert not pm.en_rango_destacado(1.19) and not pm.en_rango_destacado(None) and not pm.en_rango_destacado(0)


def test_futbol_sin_cuotas_de_casa_gana_la_mayor_probabilidad_que_aun_paga_1_20():
    # cuota del modelo = 1 ÷ prob → score 1 para todas: .95 y .90 pagan menos de 1,20 y .40 no llega al 55 %
    filas = [fila(1, .95), fila(2, .90), fila(3, .80), fila(4, .60), fila(5, .40)]
    out, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado['id'] == filas[2]['id'] and destacado['score_destacado'] == 1.0
    abiertas = [f['id'] for f in out if not f['locked']]
    # destacado (.80), el otro válido (.60) y se completa con el más probable (.95); `aplicar_acceso` las ordena por probabilidad
    assert abiertas == [filas[0]['id'], filas[2]['id'], filas[3]['id']]
    assert next(f for f in out if f['id'] == filas[2]['id'])['destacado'] is True


def test_futbol_sin_ningun_mercado_valido_no_hay_destacado_pero_si_tres_gratis():
    filas = [fila(1, .95), fila(2, .90), fila(3, .85), fila(4, .40)]
    out, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado is None and sum(not f['locked'] for f in out) == 3


def test_futbol_con_cuotas_de_casa_gana_el_mayor_valor_y_la_cuota_bajo_1_20_queda_fuera():
    hora = datetime(2026, 11, 5, 10, tzinfo=timezone.utc)
    a, b, c = fila(1, .80), fila(2, .66), fila(3, .90)
    filas = pm.con_cuotas_casas([a, b, c], {a['id']: (1.25, 'bet365', hora), b['id']: (1.60, 'bet365', hora),
                                            c['id']: (1.10, 'bet365', hora)})
    _, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado['id'] == b['id']                                        # 1,056 > 1,00; c (cuota 1,10) ni entra
    assert destacado['score_destacado'] == pytest.approx(1.056)


def test_futbol_el_destacado_es_gratis_aunque_no_sea_de_los_tres_mas_probables():
    hora = datetime(2026, 11, 5, 10, tzinfo=timezone.utc)
    sobrantes = [fila(i, .90 - i * .01) for i in range(1, 5)]                  # más probables pero pagan menos de 1,20
    valor = fila(9, .58, market='btts', sel='yes')
    filas = pm.con_cuotas_casas(sobrantes + [valor], {valor['id']: (2.10, 'bet365', hora),
                                                      **{f['id']: (1.18, 'bet365', hora) for f in sobrantes}})
    out, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado['id'] == valor['id']
    assert next(f for f in out if f['id'] == valor['id'])['locked'] is False


# --- tenis: el servidor entrega el destacado en cada evento --------------------------------------

def test_tenis_el_feed_publico_trae_el_destacado_de_cada_evento(tmp_path):
    seal = 'a' * 64
    mercados = [{'id': 'winner', 'label': 'Ganador', 'selection': 'A', 'probability': .90, 'price': None},
                {'id': 'g1', 'label': 'Juegos', 'selection': 'Más de 22', 'probability': .70, 'price': None},
                {'id': 'g2', 'label': 'Juegos', 'selection': 'Menos de 20', 'probability': .52, 'price': None}]
    evento = {'id': '1', 'sport': 'tenis', 'home': 'A', 'away': 'B', 'start': '2026-11-05T14:00:00Z', 'league': 'ATP',
              'surface': 'Hard', 'sealed_at': '2026-11-05T11:00:00Z', 'seal': seal, 'status': 'scheduled', 'markets': mercados}
    ahora = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
    ruta = tmp_path / 'tenis.json'
    ruta.write_text(json.dumps({'state': 'ok', 'generated_at': ahora.isoformat(), 'events': [evento]}))
    from qf.api import tenis_publico as tp
    data = tp.read_public_feed(ruta, ahora)
    destacado = data['events'][0]['destacado']
    assert destacado['id'] == 'g1'                       # .90 paga 1,11 (< 1,20) y .52 no llega al 55 %
    assert destacado['score_destacado'] == 1.0

    evento['markets'] = [mercados[0], mercados[2]]
    ruta.write_text(json.dumps({'state': 'ok', 'generated_at': ahora.isoformat(), 'events': [evento]}))
    assert tp.read_public_feed(ruta, ahora)['events'][0]['destacado'] is None
