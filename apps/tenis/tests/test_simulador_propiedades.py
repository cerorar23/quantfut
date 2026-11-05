"""Propiedades del simulador (plan G.6) sobre una rejilla determinista (sin `hypothesis`): masa 1, simetría,
monotonía, p_A = p_B ⇒ 0,5 exacto, neutralidad del saque, física del marcador y paso al contrato."""
import itertools

import numpy as np
import pytest

from tenis.contratos.marcador import SetMarcador, set_valido, validar_marcador
from tenis.simulador import Formato, Incertidumbre, SIN_INCERTIDUMBRE, distribucion_mezclada, distribucion_partido, prob_ganar
from tenis.simulador.salida import a_contrato
from tenis.simulador.set_ import tabla_set

FD = Incertidumbre(0.22, -0.45)
TODOS = [Formato(3, "tiebreak_7"), Formato(3, "tiebreak_10"), Formato(3, "ventaja"), Formato(3, "super_tiebreak_10"),
         Formato(5, "tiebreak_7"), Formato(5, "tiebreak_10"), Formato(5, "ventaja")]
REJILLA = [0.03, 0.2, 0.45, 0.55, 0.62, 0.66, 0.75, 0.97]
PARES = [(a, b) for a, b in itertools.product(REJILLA, REJILLA) if (REJILLA.index(a) + REJILLA.index(b)) % 3 == 0]


def espejo(m):
    return tuple((b, a, t) for a, b, t in m)


@pytest.mark.parametrize("formato", TODOS)
@pytest.mark.parametrize("pa,pb", PARES)
def test_masa_uno_y_simetria(formato, pa, pb):
    d, e = distribucion_partido(pa, pb, formato), distribucion_partido(pb, pa, formato)
    assert abs(d.masa_total - 1.0) < 1e-12
    assert abs(d.gana_a + e.gana_a - 1.0) < 1e-12
    if formato.mejor_de == 3:                                       # simetría marcador a marcador
        md, me = d.marcadores(), e.marcadores()
        assert max(abs(p - me[espejo(m)]) for m, p in md.items()) < 1e-14


@pytest.mark.parametrize("formato", TODOS)
def test_mezcla_masa_uno_y_simetria(formato):
    d, e = distribucion_mezclada(0.66, 0.60, formato, FD), distribucion_mezclada(0.60, 0.66, formato, FD)
    assert abs(d.masa_total - 1.0) < 1e-12 and abs(d.gana_a + e.gana_a - 1.0) < 1e-12
    assert abs(prob_ganar(0.66, 0.60, formato, FD) - d.gana_a) < 1e-12


@pytest.mark.parametrize("formato", TODOS)
@pytest.mark.parametrize("inc", [SIN_INCERTIDUMBRE, FD, Incertidumbre(0.3, 0.2, ((0.01, 0.0), (0.0, 0.01)))])
def test_iguales_dan_medio_exacto(formato, inc):
    for p in (0.03, 0.5, 0.64, 0.97):
        assert abs(prob_ganar(p, p, formato, inc) - 0.5) < 1e-12
        assert abs(distribucion_mezclada(p, p, formato, inc).gana_a - 0.5) < 1e-12


@pytest.mark.parametrize("formato", TODOS)
def test_monotonia_en_pa_y_pb(formato):
    ps = np.linspace(0.05, 0.95, 31)
    for inc in (SIN_INCERTIDUMBRE, FD):
        en_a = [prob_ganar(p, 0.62, formato, inc) for p in ps]
        en_b = [prob_ganar(0.62, p, formato, inc) for p in ps]
        assert np.all(np.diff(en_a) > 0) and np.all(np.diff(en_b) < 0)


@pytest.mark.parametrize("pa,pb", [(0.60, 0.55), (0.66, 0.60), (0.95, 0.95), (0.3, 0.7)])
@pytest.mark.parametrize("regla", ["tiebreak_7", "tiebreak_10", "ventaja", "super_tiebreak_10"])
def test_neutralidad_del_saque_y_invariantes_de_a31(pa, pb, regla):
    ta, tb = tabla_set(pa, pb, "A", regla), tabla_set(pa, pb, "B", regla)
    assert abs(ta.gana_a - tb.gana_a) < 1e-12
    if regla in ("tiebreak_7", "tiebreak_10"):
        da, db = dict(zip(ta.marcadores, ta.prob)), dict(zip(tb.marcadores, tb.prob))
        for grupo in ([(6, 0)], [(6, 1), (6, 2)], [(6, 3), (6, 4)], [(7, 5)]):
            for lado in (lambda a, b: (a, b), lambda a, b: (b, a)):
                sa = sum(da[(*lado(a, b), False)] for a, b in grupo)
                sb = sum(db[(*lado(a, b), False)] for a, b in grupo)
                assert abs(sa - sb) < 1e-12
        p66a, p66b = da[(7, 6, True)] + da[(6, 7, True)], db[(7, 6, True)] + db[(6, 7, True)]
        assert abs(p66a - p66b) < 1e-12


@pytest.mark.parametrize("formato", TODOS)
def test_partido_neutral_al_primer_sacador_pero_no_el_marcador(formato):
    a = distribucion_partido(0.60, 0.55, formato, saca_primero="A", max_juegos=12)
    b = distribucion_partido(0.60, 0.55, formato, saca_primero="B", max_juegos=12)
    assert abs(a.gana_a - b.gana_a) < 1e-12
    ma, mb = a.marcadores(), b.marcadores()
    assert max(abs(ma[k] - mb[k]) for k in ma) > 1e-3                # T32: 6-1 0,0947 frente a 0,0485


@pytest.mark.parametrize("formato", [f for f in TODOS if f.decisivo != "super_tiebreak_10"])
def test_fisica_del_marcador_aceptada_por_el_contrato(formato):
    """Todo marcador con masa pasa la física del contrato. Excepciones del CONTRATO (no del simulador): TB7 decisivo
    en mejor de 5 no está listado, y con set decisivo de ventaja `validar_totales` topa el total en 39/65 juegos
    (plan G.6), así que ahí se comprueba set a set con `set_valido` y el mínimo de juegos."""
    d = distribucion_partido(0.64, 0.61, formato, max_juegos=14)
    minimo = {(3, 3): 18, (5, 3): 18, (5, 4): 24, (5, 5): 30}
    completo = not (formato.mejor_de == 5 and formato.decisivo == "tiebreak_7") and formato.decisivo != "ventaja"
    for m in d.marcadores():
        total = sum(a + b for a, b, _ in m)
        assert total >= minimo.get((formato.mejor_de, len(m)), 12)
        sets = [SetMarcador(juegos_a=a, juegos_b=b, tiebreak=t) for a, b, t in m]
        if completo:
            validar_marcador(sets, formato.mejor_de, formato.decisivo)
        else:
            dec = formato.mejor_de - 1
            assert all(set_valido(s, formato.decisivo if i == dec else None) for i, s in enumerate(sets))
            assert max(sum(s.juegos_a > s.juegos_b for s in sets), sum(s.juegos_b > s.juegos_a for s in sets)) \
                == formato.sets_para_ganar


@pytest.mark.parametrize("formato", TODOS)
def test_mercados_coherentes(formato):
    d = distribucion_mezclada(0.66, 0.61, formato, FD, max_juegos=30)
    lineas = np.arange(11.5, 60.5, 1.0)
    totales = [d.juegos_mas_de(x) for x in lineas]
    assert np.all(np.diff(totales) <= 1e-15)
    hs = [d.handicap_juegos(h) for h in np.arange(-12.5, 13.0, 1.0)]
    assert np.all(np.diff(hs) >= -1e-15)
    assert d.handicap_sets(-1.5) <= d.gana_a + 1e-15
    assert abs(d.handicap_sets(0.0) - d.gana_a) < 1e-15
    assert abs(sum(d.resumen().values()) + d.masa_cola - 1.0) < 1e-12
    n = d.sets_a + d.sets_b
    assert np.all(n >= formato.sets_para_ganar) and np.all(n <= formato.mejor_de)
    assert np.all(d.n_tb <= n)


def test_mejor_de_5_favorece_mas_al_favorito():
    for pa, pb in ((0.62, 0.60), (0.70, 0.55), (0.66, 0.65)):
        for inc in (SIN_INCERTIDUMBRE, FD):
            assert prob_ganar(pa, pb, Formato(5, "tiebreak_10"), inc) > prob_ganar(pa, pb, Formato(3, "tiebreak_7"), inc)


def test_primer_set_coherente_con_la_tabla_de_set():
    d = distribucion_partido(0.64, 0.60, Formato(3, "tiebreak_7"))
    t = tabla_set(0.64, 0.60, "A", "tiebreak_7")
    assert abs(d.primer_set_a_prob - t.gana_a) < 1e-14


@pytest.mark.parametrize("formato", [Formato(3, "tiebreak_7"), Formato(3, "tiebreak_10"), Formato(5, "tiebreak_10")])
def test_paso_al_contrato_distribucion_partido(formato):
    d = distribucion_mezclada(0.65, 0.62, formato, FD)
    c = a_contrato(d, sets_mas_de=(2.5,), juegos_mas_de=(22.5, 38.5), handicap_sets=(-1.5, 1.5))
    assert abs(c.mercados.gana_a - d.gana_a) < 1e-12
    assert abs(c.mercados.juegos_mas_de["22.5"] - d.juegos_mas_de(22.5)) < 1e-12


def test_paso_al_contrato_rechaza_lo_no_representable():
    with pytest.raises(ValueError, match="súper tiebreak"):
        a_contrato(distribucion_partido(0.64, 0.6, Formato(3, "super_tiebreak_10")))
    with pytest.raises(ValueError, match="ventaja"):
        a_contrato(distribucion_partido(0.55, 0.53, Formato(3, "ventaja")))
    with pytest.raises(ValueError):
        a_contrato(distribucion_partido(0.64, 0.6, Formato(5, "tiebreak_7")))   # el contrato no lo lista
