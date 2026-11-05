"""Destacado de NBA por valor esperado (cuota >= 1,20, prob >= 55 %, gana prob × cuota); copia del módulo de `qf.api`."""
import pytest

from nba.api import destacado_valor as dv
from nba.api.mercados_partido import destacar


def mercado(id_, prob, price=None, **extra):
    return {"id": id_, "market": "game_total", "probability": prob, "price": price, "book": "casa" if price else None, **extra}


def test_cuota_180_con_70_por_ciento_gana_a_cuota_120_con_75_por_ciento_por_su_score():
    salida = {"markets": [mercado("seguro", .75, 1.20), mercado("valor", .70, 1.80)]}
    destacar(salida)
    assert salida["destacado"]["id"] == "valor"
    assert salida["destacado"]["score_destacado"] == pytest.approx(1.26)
    assert dv.elegir_destacado([{"prob": .75, "ref_price": 1.20}, {"prob": .70, "ref_price": 1.80}])["prob"] == .70


def test_con_cuotas_de_casa_solo_cuentan_esas_y_el_precio_del_modelo_no_compite():
    modelo = mercado("modelo", .80)                                         # 1 ÷ .80 = 1,25 → score 1,00
    casa = mercado("casa", .60, 1.50)                                       # score 0,90
    salida = {"markets": [modelo, casa]}
    destacar(salida)
    assert salida["destacado"]["id"] == "casa"


def test_sin_cuotas_de_casa_la_cuota_es_1_sobre_prob_y_gana_la_mayor_probabilidad_que_paga_1_20():
    salida = {"markets": [mercado("a", .95), mercado("b", .80), mercado("c", .60), mercado("d", .50)]}
    destacar(salida)
    assert salida["destacado"]["id"] == "b" and salida["destacado"]["score_destacado"] == 1.0


def test_sin_mercados_validos_el_destacado_es_none():
    for markets in ([], [mercado("a", .95), mercado("b", .50, 3.0), mercado("c", .70, 1.10)]):
        salida = {"markets": markets}
        destacar(salida)
        assert salida["destacado"] is None


def test_un_mercado_con_probabilidad_cero_no_rompe():
    salida = {"markets": [mercado("cero", 0.0), mercado("ok", .60)]}
    destacar(salida)
    assert salida["destacado"]["id"] == "ok"


def test_desempate_por_probabilidad_y_filtros_incluyentes():
    assert dv.elegir_destacado([{"prob": .60, "ref_price": 1.50}, {"prob": .75, "ref_price": 1.20}])["prob"] == .75
    assert dv.elegir_destacado([{"prob": .55, "ref_price": 1.20}]) is not None
    assert dv.elegir_destacado([{"prob": .55, "ref_price": 1.19}]) is None
    assert dv.elegir_destacado([{"prob": .54, "ref_price": 2.0}]) is None
