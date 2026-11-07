"""Destacado de NBA «probabilidad máxima segura» (cuota >= 1,20, prob >= 75 %, gana la mayor probabilidad); copia de `qf.api`."""
from nba.api import destacado_valor as dv
from nba.api.mercados_partido import destacar


def mercado(id_, prob, price=None, **extra):
    return {"id": id_, "market": "game_total", "probability": prob, "price": price, "book": "casa" if price else None, **extra}


def test_gana_la_mayor_probabilidad_aunque_otra_pague_mas():
    salida = {"markets": [mercado("segura", .82, 1.22), mercado("rentable", .81, 1.60)]}
    destacar(salida)
    assert salida["destacado"]["id"] == "segura" and "score_destacado" not in salida["destacado"]


def test_con_cuotas_de_casa_solo_cuentan_esas_y_el_precio_del_modelo_no_compite():
    modelo = mercado("modelo", .83)                                         # 1 ÷ .83 = 1,20: más probable, pero sin casa
    casa = mercado("casa", .78, 1.30)
    salida = {"markets": [modelo, casa]}
    destacar(salida)
    assert salida["destacado"]["id"] == "casa"


def test_sin_cuotas_de_casa_la_cuota_es_1_sobre_prob_y_gana_la_mayor_probabilidad_que_paga_1_20():
    salida = {"markets": [mercado("a", .95), mercado("b", .83), mercado("c", .78), mercado("d", .60)]}
    destacar(salida)
    assert salida["destacado"]["id"] == "b"


def test_sin_mercados_validos_el_destacado_es_none():
    for markets in ([], [mercado("a", .95), mercado("b", .60, 3.0), mercado("c", .80, 1.10)]):
        salida = {"markets": markets}
        destacar(salida)
        assert salida["destacado"] is None


def test_un_mercado_con_probabilidad_cero_no_rompe():
    salida = {"markets": [mercado("cero", 0.0), mercado("ok", .80)]}
    destacar(salida)
    assert salida["destacado"]["id"] == "ok"


def test_desempate_por_cuota_y_filtros_incluyentes():
    assert dv.elegir_destacado([{"prob": .80, "ref_price": 1.25}, {"prob": .80, "ref_price": 1.40}])["ref_price"] == 1.40
    assert dv.elegir_destacado([{"prob": .75, "ref_price": 1.20}]) is not None
    assert dv.elegir_destacado([{"prob": .75, "ref_price": 1.19}]) is None
    assert dv.elegir_destacado([{"prob": .74, "ref_price": 2.0}]) is None
