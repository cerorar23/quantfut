"""Casos absurdos y extremos del simulador: entradas imposibles se rechazan con un error claro; los extremos
admitidos (p = 0,02 / 0,98, el caso «Isner» con 95 % al saque) no producen NaN y respetan la física."""
import math

import numpy as np
import pytest

from tenis.simulador import Formato, Incertidumbre, SIN_INCERTIDUMBRE, distribucion_mezclada, distribucion_partido, prob_ganar
from tenis.simulador.inversion import invertir
from tenis.simulador.juego import distribucion_juego, ganar_juego, ganar_juego_sin_ventaja, romper_saque
from tenis.simulador.set_ import tabla_set
from tenis.simulador.tiebreak import distribucion_tiebreak, ganar_tiebreak

B3 = Formato(3, "tiebreak_7")
FD = Incertidumbre(0.22, -0.45)
MALAS = [0.0, 1.0, -0.1, 1.2, math.nan, math.inf, -math.inf]
TODOS = [Formato(3, "tiebreak_7"), Formato(3, "tiebreak_10"), Formato(3, "ventaja"), Formato(3, "super_tiebreak_10"),
         Formato(5, "tiebreak_7"), Formato(5, "tiebreak_10"), Formato(5, "ventaja")]


@pytest.mark.parametrize("p", MALAS)
def test_p_imposible_se_rechaza_en_todas_las_piezas(p):
    llamadas = [lambda: ganar_juego(p), lambda: romper_saque(p), lambda: ganar_juego_sin_ventaja(p),
                lambda: distribucion_juego(p), lambda: ganar_tiebreak(p, 0.6, 7, "A"),
                lambda: ganar_tiebreak(0.6, p, 10, "B"), lambda: distribucion_tiebreak(p, 0.6, 7, "A"),
                lambda: tabla_set(p, 0.6, "A", "tiebreak_7"), lambda: tabla_set(0.6, p, "B", "ventaja"),
                lambda: distribucion_partido(p, 0.6, B3), lambda: distribucion_partido(0.6, p, B3),
                lambda: prob_ganar(p, 0.6, B3, FD), lambda: distribucion_mezclada(0.6, p, B3, FD)]
    for f in llamadas:
        with pytest.raises(ValueError):
            f()


@pytest.mark.parametrize("p", ["0.6", None, True])
def test_p_que_no_es_numero_se_rechaza(p):
    with pytest.raises(TypeError):
        ganar_juego(p)


def test_vector_con_un_valor_malo_se_rechaza_entero():
    with pytest.raises(ValueError):
        ganar_juego(np.array([0.5, 1.0]))


@pytest.mark.parametrize("mejor_de,decisivo", [(1, "tiebreak_7"), (2, "tiebreak_7"), (4, "tiebreak_10"),
                                               (True, "tiebreak_7"), (3, "fast4"), (3, "tiebreak_12"), (3, ""),
                                               (5, "super_tiebreak_10"), (3, None)])
def test_formato_desconocido_es_error_explicito(mejor_de, decisivo):
    with pytest.raises(ValueError):
        Formato(mejor_de, decisivo)


def test_sin_formato_no_hay_valor_por_omision():
    for f in (lambda: distribucion_partido(0.6, 0.6, None), lambda: prob_ganar(0.6, 0.6, "mejor de 3", FD),
              lambda: distribucion_mezclada(0.6, 0.6, (3, "tiebreak_7"), FD)):
        with pytest.raises(TypeError):
            f()
    with pytest.raises(TypeError):
        prob_ganar(0.6, 0.6, B3, None)


def test_tiebreak_y_set_desconocidos_y_sacador_desconocido():
    with pytest.raises(ValueError):
        ganar_tiebreak(0.6, 0.6, 8, "A")
    with pytest.raises(ValueError):
        ganar_tiebreak(0.6, 0.6, 7, "C")
    with pytest.raises(ValueError):
        tabla_set(0.6, 0.6, "A", "sin_tiebreak")
    with pytest.raises(ValueError):
        distribucion_partido(0.6, 0.6, B3, saca_primero="nadie")


@pytest.mark.parametrize("formato", TODOS)
@pytest.mark.parametrize("pa,pb", [(0.02, 0.02), (0.98, 0.98), (0.02, 0.98), (0.98, 0.02), (0.5, 0.98)])
def test_extremos_admitidos_sin_nan_y_masa_uno(formato, pa, pb):
    d = distribucion_partido(pa, pb, formato)
    assert np.all(np.isfinite(d.prob)) and np.all(d.prob >= 0)
    assert abs(d.masa_total - 1.0) < 1e-12
    assert 0.0 <= d.gana_a <= 1.0 and math.isfinite(d.media_juegos)
    if (pa, pb) == (0.98, 0.02):
        assert d.gana_a > 1 - 1e-12
    if (pa, pb) == (0.02, 0.98):
        assert d.gana_a < 1e-12


@pytest.mark.parametrize("formato", [Formato(3, "tiebreak_7"), Formato(3, "tiebreak_10"), Formato(5, "tiebreak_10"),
                                     Formato(5, "tiebreak_7")])
def test_caso_isner_95_por_ciento_al_saque(formato):
    d = distribucion_partido(0.95, 0.95, formato)
    assert np.all(np.isfinite(d.prob)) and abs(d.masa_total - 1.0) < 1e-12
    assert abs(d.gana_a - 0.5) < 1e-12
    assert d.tiebreak_si > 0.999                                   # casi seguro algún tiebreak
    n_sets = d.sets_a + d.sets_b
    for n in np.unique(n_sets):                                    # juegos cerca del máximo (13 por set)
        m = n_sets == n
        assert (d.prob[m] * d.juegos[m]).sum() / d.prob[m].sum() > 13 * n - 0.05
    mezcla = distribucion_mezclada(0.95, 0.95, formato, FD)
    assert abs(mezcla.masa_total - 1.0) < 1e-12 and abs(mezcla.gana_a - 0.5) < 1e-12


def test_caso_isner_con_set_decisivo_de_ventaja_declara_la_cola():
    d = distribucion_partido(0.95, 0.95, Formato(5, "ventaja"))
    assert abs(d.masa_total - 1.0) < 1e-12 and abs(d.gana_a - 0.5) < 1e-12
    assert d.masa_cola > 0.1                                       # 5.º set de más de 50 juegos: frecuente
    assert d.media_juegos > 4 * 13 + 2 * 50                        # cola con su media cerrada
    with pytest.raises(ValueError):
        d.juegos_mas_de(200.5)                                     # línea dentro de la cola: no se inventa


def test_inversion_rechaza_lo_inalcanzable_y_lo_mal_formado():
    with pytest.raises(ValueError, match="inalcanzable"):
        invertir(0.06, 0.9, B3, FD)                                 # p_A ≤ 0,04: no llega a 0,9
    for s, pi in ((1.25, 0.0), (1.25, 1.0), (1.25, math.nan), (2.0, 0.6), (0.03, 0.5), (math.inf, 0.5)):
        with pytest.raises(ValueError):
            invertir(s, pi, B3, FD)


def test_incertidumbre_mal_formada():
    for inc in (Incertidumbre(-0.1, 0.0), Incertidumbre(0.2, 1.5), Incertidumbre(math.nan, 0.0),
                Incertidumbre(0.2, 0.0, ((0.01, 0.02), (0.0, 0.01))), Incertidumbre(0.0, 0.0, ((-1.0, 0.0), (0.0, 0.0)))):
        with pytest.raises(ValueError):
            prob_ganar(0.6, 0.6, B3, inc)
    with pytest.raises(ValueError):
        prob_ganar(0.6, 0.6, B3, FD, q=0)


def test_sin_incertidumbre_es_el_par_exacto():
    assert prob_ganar(0.66, 0.60, B3, SIN_INCERTIDUMBRE) == pytest.approx(distribucion_partido(0.66, 0.60, B3).gana_a,
                                                                         abs=1e-14)


def test_correlacion_perfecta_es_semidefinida_y_se_admite():
    assert math.isfinite(prob_ganar(0.66, 0.60, B3, Incertidumbre(0.22, -1.0)))
