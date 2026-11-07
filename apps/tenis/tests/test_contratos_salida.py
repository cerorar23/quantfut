"""Distribución conjunta, física del marcador y pronóstico sellado.

La prueba de fuerza bruta usa una tabla de sets escrita a mano (no el código de src) para comprobar la física.
"""
import itertools
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from tenis.contratos.marcador import SetMarcador, set_valido, validar_totales
from tenis.contratos.salida import DistribucionPartido, PronosticoSellado

UTC = timezone.utc
AHORA = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
HASH = "a" * 64


def S(a, b, tb=False):
    return SetMarcador(juegos_a=a, juegos_b=b, tiebreak=tb)


def unica(sets, mejor_de=3, regla="tiebreak_7"):
    """Distribución con un solo marcador (prob. 1) y mercados derivados a mano."""
    ganados_a = sum(1 for s in sets if s.juegos_a > s.juegos_b)
    ganados_b = len(sets) - ganados_a
    total = sum(s.juegos_a + s.juegos_b for s in sets)
    return dict(
        mejor_de=mejor_de,
        regla_decisivo=regla,
        entradas=[dict(sets=[s.model_dump() for s in sets], probabilidad=1.0)],
        mercados=dict(
            gana_a=float(ganados_a > ganados_b),
            primer_set_a=float(sets[0].juegos_a > sets[0].juegos_b),
            sets_mas_de={"1": float(len(sets) > 1), "2": float(len(sets) > 2)},
            juegos_mas_de={"10.5": float(total > 10.5)},
            handicap_sets={"-1.5": float(ganados_a - ganados_b - 1.5 > 0)},
        ),
    )


def dos_partes(p_a=0.6, p_b=0.4):
    """Dos marcadores: A gana 2-0 (6-4 6-4, prob p_a) y B gana 2-1 (4-6 4-6 6-4, prob p_b).

    Mercados calculados a mano: gana A solo en el primero; el 1.er set lo gana A solo en el primero;
    hay 3 sets solo en el segundo; el total de juegos es 20 y 30; el hándicap -1,5 solo lo cubre A en el primero.
    El segundo es 2-1 para B: 4-6, 6-4, 4-6.
    """
    s1 = [S(6, 4), S(6, 4)]
    s2 = [S(4, 6), S(6, 4), S(4, 6)]
    return dict(
        mejor_de=3,
        regla_decisivo="tiebreak_7",
        entradas=[dict(sets=[x.model_dump() for x in s1], probabilidad=p_a),
                  dict(sets=[x.model_dump() for x in s2], probabilidad=p_b)],
        mercados=dict(
            gana_a=p_a,
            primer_set_a=p_a,
            sets_mas_de={"1": 1.0, "2": p_b},
            juegos_mas_de={"10.5": 1.0},
            handicap_sets={"-1.5": p_a},
        ),
    )


def test_dos_marcadores_con_mercados_a_mano_son_validos():
    assert DistribucionPartido(**dos_partes(0.6, 0.4)).mercados.gana_a == 0.6


def test_distribucion_de_un_marcador_valida():
    d = DistribucionPartido(**unica([S(6, 0), S(6, 0)]))
    assert d.mercados.gana_a == 1.0


def test_limite_6_0_6_0_en_mejor_de_3_es_valido():
    assert DistribucionPartido(**unica([S(6, 0), S(6, 0)])).mejor_de == 3


def test_limite_18_juegos_con_tres_sets_es_valido():
    d = DistribucionPartido(**unica([S(6, 0), S(0, 6), S(6, 0)]))
    assert d.mercados.sets_mas_de["2"] == 1.0


def test_limite_set_7_5_y_7_6_con_tiebreak_son_validos():
    assert DistribucionPartido(**unica([S(7, 5), S(6, 0)]))
    assert DistribucionPartido(**unica([S(7, 6, True), S(6, 0)]))


def test_set_7_6_sin_tiebreak_se_rechaza():
    with pytest.raises(ValidationError):
        DistribucionPartido(**unica([S(7, 6), S(6, 0)]))


def test_set_8_6_se_rechaza_fuera_de_ventaja():
    with pytest.raises(ValidationError):
        DistribucionPartido(**unica([S(8, 6), S(6, 0)]))
    with pytest.raises(ValidationError):
        DistribucionPartido(**unica([S(6, 0), S(0, 6), S(8, 6)], regla="tiebreak_7"))


def test_set_8_6_decisivo_con_ventaja_es_valido():
    assert DistribucionPartido(**unica([S(6, 0), S(0, 6), S(8, 6)], regla="ventaja"))


def test_tiebreak_con_marcador_distinto_de_7_6_se_rechaza():
    with pytest.raises(ValidationError):
        DistribucionPartido(**unica([S(6, 0, True), S(6, 0)]))


def test_mejor_de_5_con_decisivo_tiebreak_7_se_rechaza():
    partido_3_0 = [S(6, 0), S(6, 0), S(6, 0)]
    with pytest.raises(ValidationError):
        DistribucionPartido(**unica(partido_3_0, mejor_de=5, regla="tiebreak_7"))
    assert DistribucionPartido(**unica(partido_3_0, mejor_de=5, regla="tiebreak_10"))


def test_tercer_set_con_total_bajo_18_es_imposible():
    with pytest.raises(ValueError):
        validar_totales(3, 3, 17)
    validar_totales(3, 3, 18)


def test_masa_que_suma_0_999_se_rechaza():
    with pytest.raises(ValidationError):
        DistribucionPartido(**dos_partes(p_a=0.6, p_b=0.399))


def test_mercado_incoherente_con_la_conjunta_se_rechaza():
    d = unica([S(6, 0), S(6, 0)])
    d["mercados"]["gana_a"] = 0.0
    with pytest.raises(ValidationError):
        DistribucionPartido(**d)


def test_marcador_duplicado_se_rechaza():
    d = unica([S(6, 0), S(6, 0)])
    d["entradas"] = d["entradas"] * 2
    d["entradas"][0]["probabilidad"] = 0.5
    d["entradas"][1]["probabilidad"] = 0.5
    with pytest.raises(ValidationError):
        DistribucionPartido(**d)


def test_probabilidad_cero_en_una_entrada_se_rechaza():
    d = unica([S(6, 0), S(6, 0)])
    d["entradas"][0]["probabilidad"] = 0.0
    with pytest.raises(ValidationError):
        DistribucionPartido(**d)


# Física del marcador por fuerza bruta: tabla escrita a mano.
def _validos_no_decisivo():
    base = {(6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (7, 5)}
    return base | {(b, a) for a, b in base}


def _validos_decisivo_ventaja():
    return _validos_no_decisivo() | {(8, 6), (6, 8)}


def _valido_tb(a, b, tb, regla):
    if tb:
        return (a, b) in {(7, 6), (6, 7)} and regla != "ventaja"
    if regla == "ventaja":
        return (a, b) in _validos_decisivo_ventaja()
    return (a, b) in _validos_no_decisivo()


@pytest.mark.parametrize("a,b,tb", list(itertools.product(range(9), range(9), (False, True))))
def test_fuerza_bruta_sets_no_decisivos(a, b, tb):
    ganador = (6, 0) if a > b else (0, 6)
    sets = [S(a, b, tb), S(*ganador)]
    esperado = _valido_tb(a, b, tb, "tiebreak_7")
    if esperado:
        assert DistribucionPartido(**unica(sets, regla="tiebreak_7"))
    else:
        with pytest.raises(ValidationError):
            DistribucionPartido(**unica(sets, regla="tiebreak_7"))


@pytest.mark.parametrize("regla", ["tiebreak_7", "tiebreak_10", "ventaja"])
@pytest.mark.parametrize("a,b,tb", list(itertools.product(range(9), range(9), (False, True))))
def test_fuerza_bruta_set_decisivo(a, b, tb, regla):
    sets = [S(6, 0), S(0, 6), S(a, b, tb)]
    esperado = _valido_tb(a, b, tb, regla)
    if esperado:
        assert DistribucionPartido(**unica(sets, regla=regla))
    else:
        with pytest.raises(ValidationError):
            DistribucionPartido(**unica(sets, regla=regla))


def test_set_valido_coincide_con_la_tabla_a_mano_en_los_limites():
    assert set_valido(S(7, 5), None) and set_valido(S(7, 6, True), None)
    assert not set_valido(S(7, 6), None)
    assert not set_valido(S(8, 6), "tiebreak_7")
    assert set_valido(S(8, 6), "ventaja")


def _pronostico(**cambios):
    d = unica([S(6, 0), S(6, 0)])
    datos = dict(
        partido_id=1, version_modelo="v1", posicion=1,
        corte=AHORA, sellado_en=AHORA + timedelta(minutes=5),
        hash_previo=None, hash=HASH, distribucion=d,
    )
    datos.update(cambios)
    return datos


def test_pronostico_valido_primero_y_encadenado():
    assert PronosticoSellado(**_pronostico()).posicion == 1
    assert PronosticoSellado(**_pronostico(posicion=2, hash_previo="b" * 64)).posicion == 2


def test_pronostico_corte_no_anterior_al_sellado_se_rechaza():
    with pytest.raises(ValidationError):
        PronosticoSellado(**_pronostico(sellado_en=AHORA))
    with pytest.raises(ValidationError):
        PronosticoSellado(**_pronostico(corte=AHORA + timedelta(minutes=9)))


def test_pronostico_hash_previo_solo_puede_faltar_en_el_primero():
    with pytest.raises(ValidationError):
        PronosticoSellado(**_pronostico(posicion=2, hash_previo=None))
    with pytest.raises(ValidationError):
        PronosticoSellado(**_pronostico(posicion=1, hash_previo="b" * 64))


def test_pronostico_hash_mal_formado_se_rechaza():
    for valor in ("a" * 63, "A" * 64):
        with pytest.raises(ValidationError):
            PronosticoSellado(**_pronostico(hash=valor))


def test_pronostico_version_vacia_se_rechaza():
    with pytest.raises(ValidationError):
        PronosticoSellado(**_pronostico(version_modelo="   "))


def test_pronostico_con_distribucion_invalida_se_rechaza():
    d = unica([S(6, 0), S(6, 0)])
    d["mercados"]["gana_a"] = 0.5
    with pytest.raises(ValidationError):
        PronosticoSellado(**_pronostico(distribucion=d))
