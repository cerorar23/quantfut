"""Destacado «probabilidad máxima segura»: filtro (cuota >= 1,20 y prob >= 75 %), gana la mayor probabilidad, desempate por cuota."""
import json
from datetime import datetime, timezone

import pytest

from qf.api import destacado_valor as dv
from qf.api import partido_mercados as pm


def m(id_, prob, ref_price, **extra):
    return {'id': id_, 'prob': prob, 'ref_price': ref_price, **extra}


# --- la regla nueva ----------------------------------------------------------------------------

def test_gana_la_mayor_probabilidad_aunque_otra_pague_mas():
    segura = m('segura', .82, 1.22)        # con valor esperado habría perdido contra 'rentable' (0,81 × 1,60 = 1,30 > 1,00)
    rentable = m('rentable', .81, 1.60)
    for orden in ([segura, rentable], [rentable, segura]):
        assert dv.elegir_destacado(orden)['id'] == 'segura'


def test_la_cuota_no_multiplica_nada_ni_se_expone_ningun_score():
    ganador = dv.elegir_destacado([m('a', .80, 1.25)])
    assert ganador == {'id': 'a', 'prob': .80, 'ref_price': 1.25}


def test_el_dilema_de_antes_ya_no_elige_la_cuota_larga():
    seguro = m('seguro', .75, 1.20)
    valor = m('valor', .70, 1.80)            # 70 % no llega al 75 %: ni siquiera es candidato
    assert dv.elegir_destacado([valor, seguro])['id'] == 'seguro'
    assert dv.elegir_destacado([valor]) is None


# --- filtro de entrada --------------------------------------------------------------------------

def test_cuota_minima_1_20_incluida_y_probabilidad_minima_75_incluida():
    assert dv.elegir_destacado([m('a', .75, 1.20)])['id'] == 'a'
    assert dv.elegir_destacado([m('a', .80, 1.1999)]) is None
    assert dv.elegir_destacado([m('a', .7499, 3.0)]) is None


def test_un_mercado_de_55_por_ciento_ya_no_es_candidato():
    assert dv.PROB_MIN == .75 and dv.CUOTA_MIN == 1.20
    assert dv.elegir_destacado([m('a', .55, 2.0), m('b', .74, 1.4)]) is None


def test_una_cuota_enorme_con_poca_probabilidad_nunca_es_destacado():
    assert dv.elegir_destacado([m('loteria', .20, 5.0), m('segura', .90, 1.10)]) is None


def test_si_nadie_pasa_el_filtro_es_none():
    assert dv.elegir_destacado([]) is None
    assert dv.elegir_destacado([m('a', .90, 1.05), m('b', .40, 2.5)]) is None


# --- desempate y robustez -----------------------------------------------------------------------

def test_igual_probabilidad_gana_la_mayor_cuota():
    a, b = m('a', .80, 1.25), m('b', .80, 1.45)
    for orden in ([a, b], [b, a]):
        assert dv.elegir_destacado(orden)['id'] == 'b'


def test_empate_total_gana_el_primero_de_la_lista():
    assert dv.elegir_destacado([m('x', .80, 1.30), m('y', .80, 1.30)])['id'] == 'x'


def test_datos_invalidos_se_ignoran_sin_romper():
    basura = [m('nan', float('nan'), 1.5), m('inf', .8, float('inf')), m('none', None, 1.5), m('str', '.8', 1.5),
              m('bool', True, 1.5), {'id': 'sin_campos'}, m('ok', .80, 1.50)]
    assert dv.elegir_destacado(basura)['id'] == 'ok'


def test_no_modifica_el_mercado_original_y_acepta_otros_nombres_de_campo():
    original = {'id': 'a', 'probability': .8, 'price': 1.3}
    ganador = dv.elegir_destacado([original], prob='probability', precio='price')
    assert ganador == original and ganador is not original
    assert dv.elegir_destacado([original], prob='probability', precio=lambda x: x['price'] / 2) is None


# --- fútbol: acceso de la web ---------------------------------------------------------------------

def fila(i, prob, linea=None, market='totals', sel='over'):
    return pm._fila('GOLES', f'M{i}', market, sel, float(i) if linea is None else linea, f'Más de {i}', prob)


def test_rango_del_destacado_arranca_en_1_20_y_no_tiene_tope():
    assert pm.RANGO_DESTACADO == (1.20, None)
    assert pm.en_rango_destacado(1.20) and pm.en_rango_destacado(25.0)
    assert not pm.en_rango_destacado(1.19) and not pm.en_rango_destacado(None) and not pm.en_rango_destacado(0)


def test_futbol_sin_cuotas_de_casa_gana_la_mayor_probabilidad_que_aun_paga_1_20():
    # cuota del modelo = 1 ÷ prob: .95 y .90 pagan menos de 1,20, .60 no llega al 75 %, .83 y .78 sí
    filas = [fila(1, .95), fila(2, .90), fila(3, .83), fila(4, .78), fila(5, .60)]
    out, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado['id'] == filas[2]['id'] and 'score_destacado' not in destacado
    abiertas = [f['id'] for f in out if not f['locked']]
    assert abiertas == [filas[0]['id'], filas[2]['id'], filas[3]['id']]     # destacado, el otro válido y el más probable de relleno (orden por prob.)
    assert next(f for f in out if f['id'] == filas[2]['id'])['destacado'] is True


def test_futbol_sin_ningun_mercado_valido_no_hay_destacado_pero_si_tres_gratis():
    filas = [fila(1, .95), fila(2, .90), fila(3, .85), fila(4, .60)]       # tres pagan menos de 1,20 y .60 < 75 %
    out, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado is None and sum(not f['locked'] for f in out) == 3


def test_futbol_un_mercado_de_60_por_ciento_ya_no_es_destacado():
    out, _, destacado = pm.aplicar_acceso_web([fila(1, .60), fila(2, .55)], [], {}, plus=False)
    assert destacado is None


def test_futbol_con_cuotas_de_casa_gana_la_mayor_probabilidad_y_la_cuota_bajo_1_20_queda_fuera():
    hora = datetime(2026, 11, 5, 10, tzinfo=timezone.utc)
    a, b, c = fila(1, .80), fila(2, .78), fila(3, .90)
    filas = pm.con_cuotas_casas([a, b, c], {a['id']: (1.25, 'bet365', hora), b['id']: (1.60, 'bet365', hora),
                                            c['id']: (1.10, 'bet365', hora)})
    _, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado['id'] == a['id']                       # .90 paga 1,10 (< 1,20); entre .80 y .78 gana la probabilidad
    assert destacado['cuota'] == 1.25 and destacado['cuota_tipo'] == 'casa'


def test_futbol_el_destacado_es_gratis_aunque_no_sea_de_los_tres_mas_probables():
    hora = datetime(2026, 11, 5, 10, tzinfo=timezone.utc)
    sobrantes = [fila(i, .95 - i * .01) for i in range(1, 5)]                  # más probables pero pagan menos de 1,20
    seguro = fila(9, .78, market='btts', sel='yes')
    filas = pm.con_cuotas_casas(sobrantes + [seguro], {seguro['id']: (1.30, 'bet365', hora),
                                                       **{f['id']: (1.18, 'bet365', hora) for f in sobrantes}})
    out, _, destacado = pm.aplicar_acceso_web(filas, [], {}, plus=False)
    assert destacado['id'] == seguro['id']
    assert next(f for f in out if f['id'] == seguro['id'])['locked'] is False


# --- tenis: el servidor entrega el destacado en cada evento --------------------------------------

def test_tenis_el_feed_publico_trae_el_destacado_de_cada_evento(tmp_path):
    seal = 'a' * 64
    mercados = [{'id': 'winner', 'label': 'Ganador', 'selection': 'A', 'probability': .90, 'price': None},
                {'id': 'g1', 'label': 'Juegos', 'selection': 'Más de 22', 'probability': .79, 'price': None},
                {'id': 'g2', 'label': 'Juegos', 'selection': 'Menos de 20', 'probability': .60, 'price': None}]
    evento = {'id': '1', 'sport': 'tenis', 'home': 'A', 'away': 'B', 'start': '2026-11-05T14:00:00Z', 'league': 'ATP',
              'surface': 'Hard', 'sealed_at': '2026-11-05T11:00:00Z', 'seal': seal, 'status': 'scheduled', 'markets': mercados}
    ahora = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
    ruta = tmp_path / 'tenis.json'
    ruta.write_text(json.dumps({'state': 'ok', 'generated_at': ahora.isoformat(), 'events': [evento]}))
    from qf.api import tenis_publico as tp
    data = tp.read_public_feed(ruta, ahora)
    destacado = data['events'][0]['destacado']
    assert destacado['id'] == 'g1'                       # .90 paga 1,11 (< 1,20) y .60 no llega al 75 %
    assert 'score_destacado' not in destacado

    evento['markets'] = [mercados[0], mercados[2]]
    ruta.write_text(json.dumps({'state': 'ok', 'generated_at': ahora.isoformat(), 'events': [evento]}))
    assert tp.read_public_feed(ruta, ahora)['events'][0]['destacado'] is None
