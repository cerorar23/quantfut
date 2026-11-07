"""Cifras publicadas (lit. C.i y lote 04: A26, A31, T32) y del plan (§D.4, §G.3), y la cuadratura (§G.5).

Tolerancia: medio dígito del último decimal impreso por los autores (más 1e-6), salvo que el plan fije otra."""
import numpy as np
import pytest
from numpy.polynomial.hermite_e import hermegauss

from tenis.simulador import Formato, Incertidumbre, SIN_INCERTIDUMBRE, distribucion_mezclada, distribucion_partido, prob_ganar
from tenis.simulador.inversion import invertir
from tenis.simulador.mezcla import verificar_cuadratura
from tenis.simulador.partido import prob_ganar_nodos
from test_simulador_referencia import ref_tiebreak
from tenis.simulador.juego import ganar_juego, ganar_juego_sin_ventaja, puntos_media_var as juego_mv
from tenis.simulador.set_ import tabla_set
from tenis.simulador.tiebreak import puntos_media_var as tb_mv

B3 = Formato(3, "tiebreak_7")
FD = Incertidumbre(0.22, -0.45)


def media_digito(impreso: str) -> float:
    return 0.5 * 10 ** -len(impreso.split(".")[1]) + 1e-6


@pytest.mark.parametrize("f,p,impreso", [(ganar_juego, 0.65, "0.830"), (ganar_juego, 0.6, "0.736"),
                                         (ganar_juego, 0.5, "0.5000"), (ganar_juego_sin_ventaja, 0.65, "0.800")])
def test_juego_a26_t32(f, p, impreso):
    assert abs(f(p) - float(impreso)) <= media_digito(impreso)


@pytest.mark.parametrize("p,media,var", [(0.5, "6.750", "7.6875"), (0.6, "6.484", "6.708")])
def test_puntos_del_juego_t32_tabla_2(p, media, var):
    m, v = juego_mv(p)
    assert abs(m - float(media)) <= media_digito(media) and abs(v - float(var)) <= media_digito(var)


def test_puntos_del_tiebreak_t32_teorema_3_5():
    for primero in "AB":
        m, v = tb_mv(0.5, 0.5, 7, primero)
        assert abs(m - 11.744) <= media_digito("11.744") and abs(np.sqrt(v) - 2.909) <= media_digito("2.909")


@pytest.mark.parametrize("pa,pb", [(0.9, 0.9), (0.6, 0.55), (0.95, 0.7)])
def test_puntos_del_tiebreak_igual_a_referencia(pa, pb):
    """T32 Fig. 5 da 16,07 / 8,48 para 0,9/0,9; el valor exacto (cerrado y referencia de puntos) es 16,177 / 8,792:
    la cifra de la figura no se reproduce (probablemente simulada o leída de la figura)."""
    for primero in "AB":
        fin, err = ref_tiebreak(pa, pb, 7, primero)
        m_ref = sum(v * (a + b) for (a, b), v in fin.items())
        v_ref = sum(v * (a + b) ** 2 for (a, b), v in fin.items()) - m_ref**2
        m, v = tb_mv(pa, pb, 7, primero)
        assert err < 1e-15 and abs(m - m_ref) < 1e-10 and abs(v - v_ref) < 1e-9


def test_set_t32_tabla_7():
    """p_A = 0,60, p_B = 0,55: set 0,66948 (teoría); 6-h según quién saca primero; P(6-6) 0,138 (plan: 0,1383)."""
    impresos = {"A": {(6, 1): "0.0947", (6, 2): "0.0952", (6, 3): "0.2042", (6, 4): "0.1053"},
                "B": {(6, 1): "0.0485", (6, 2): "0.1414", (6, 3): "0.1046", (6, 4): "0.2049"}}
    for s, tabla in impresos.items():
        t = tabla_set(0.60, 0.55, s, "tiebreak_7")
        d = dict(zip(t.marcadores, t.prob))
        assert abs(t.gana_a - 0.66948) <= media_digito("0.66948")
        assert abs(d[(7, 6, True)] + d[(6, 7, True)] - 0.1383) <= media_digito("0.1383")
        for (a, b), imp in tabla.items():
            assert abs(d[(a, b, False)] - float(imp)) <= media_digito(imp), (s, a, b)


def test_partido_t32_mejor_de_5_con_tb10_decisivo():
    d = distribucion_partido(0.60, 0.55, Formato(5, "tiebreak_10"))
    assert abs(d.gana_a - 0.7948) <= media_digito("0.7948")
    por_sets = {}
    for sa, sb, p in zip(d.sets_a, d.sets_b, d.prob):
        por_sets[(sa, sb)] = por_sets.get((sa, sb), 0.0) + p
    for clave, imp in (((3, 0), "0.300"), ((3, 1), "0.298"), ((3, 2), "0.197")):
        assert abs(por_sets[clave] - float(imp)) <= media_digito(imp), clave


def test_plan_g3_mejor_de_5_tb7_en_todos():
    d = distribucion_partido(0.60, 0.55, Formato(5, "tiebreak_7"))
    assert abs(d.gana_a - 0.7943) <= media_digito("0.7943")


@pytest.mark.parametrize("pa,pb,m5,m3", [(0.6, 0.5, "0.9513", "0.9079"), (0.5, 0.4, "0.9513", "0.9079"),
                                         (0.7, 0.6, "0.9380", "0.8909")])
def test_partido_a31_tablas_3_y_4(pa, pb, m5, m3):
    """A31 (2005): tiebreak a 7 en todos los sets. Tolerancia 2e-4 (plan G.6: redondeo de los autores)."""
    assert abs(prob_ganar(pa, pb, Formato(5, "tiebreak_7"), SIN_INCERTIDUMBRE) - float(m5)) <= 2e-4
    assert abs(prob_ganar(pa, pb, B3, SIN_INCERTIDUMBRE) - float(m3)) <= 2e-4


@pytest.mark.parametrize("formato,pa,pb,impreso", [(Formato(5, "ventaja"), 0.6824, 0.6663, "0.598"),
                                                   (Formato(3, "ventaja"), 0.6265, 0.5273, "0.906")])
def test_inversion_a26_wimbledon(formato, pa, pb, impreso):
    """A26 §5: Sampras–Becker 1995 y Graf–Novotna 1993 (Wimbledon: set final con ventaja), sin forma del día."""
    assert abs(prob_ganar(pa, pb, formato, SIN_INCERTIDUMBRE) - float(impreso)) <= media_digito(impreso)
    inv = invertir(pa + pb, float(impreso), formato, SIN_INCERTIDUMBRE)
    assert abs(inv.p_a - pa) < 1e-3 and abs(inv.p_b - pb) < 1e-3


def test_k_es_diagnostico_no_identidad():
    """Plan D.3: con 0,60/0,55 el cociente logit(m5)/logit(m3) es 1,263; varía con p (no es la constante √1,4)."""
    def k(pa, pb):
        m3, m5 = prob_ganar(pa, pb, B3, SIN_INCERTIDUMBRE), prob_ganar(pa, pb, Formato(5, "tiebreak_7"), SIN_INCERTIDUMBRE)
        return np.log(m5 / (1 - m5)) / np.log(m3 / (1 - m3))
    assert abs(k(0.60, 0.55) - 1.263) <= media_digito("1.263")
    assert abs(k(0.70, 0.55) - k(0.62, 0.60)) > 0.05


def test_plan_d4_inversion_y_efecto_del_partido():
    assert abs(prob_ganar(0.66, 0.60, B3, SIN_INCERTIDUMBRE) - 0.775) <= media_digito("0.775")
    assert abs(prob_ganar(0.66, 0.60, B3, FD) - 0.694) <= media_digito("0.694")
    inv = invertir(1.25, 0.70, B3, FD)
    assert abs(inv.delta - 0.0311) <= media_digito("0.0311")
    assert abs(inv.p_a - 0.6561) <= media_digito("0.6561") and abs(inv.p_b - 0.5939) <= media_digito("0.5939")
    assert abs(prob_ganar(inv.p_a, inv.p_b, B3, FD) - 0.70) < 1e-9
    assert abs(distribucion_mezclada(inv.p_a, inv.p_b, B3, FD).gana_a - 0.70) < 1e-9


@pytest.mark.parametrize("q,impreso", [(5, "0.693873"), (7, "0.693789"), (9, "0.693792"), (15, "0.693793")])
def test_plan_g3_cuadratura_por_q_con_cholesky(q, impreso):
    """El plan (G.3) calculó con L de Cholesky: se reproduce construyendo esos mismos nodos a mano."""
    x, w = hermegauss(q)
    w = np.outer(w, w).ravel() / w.sum() ** 2
    gx, gy = np.meshgrid(x, x, indexing="ij")
    u = np.linalg.cholesky(FD.matriz()) @ np.vstack([gx.ravel(), gy.ravel()])
    pa = 1 / (1 + np.exp(-(np.log(0.66 / 0.34) + u[0])))
    pb = 1 / (1 + np.exp(-(np.log(0.60 / 0.40) + u[1])))
    assert abs(w @ prob_ganar_nodos(pa, pb, B3) - float(impreso)) <= media_digito(impreso)


def test_raiz_simetrica_converge_al_mismo_valor():
    """La raíz simétrica (la del simulador) llega al mismo límite: Q = 9 frente a Q = 21 de Cholesky."""
    assert abs(prob_ganar(0.66, 0.60, B3, FD, 9) - 0.6937932) < 2e-7


INC_REALISTAS = [FD, Incertidumbre(0.18, -0.64), Incertidumbre(0.22, -0.45, ((0.01, 0.0), (0.0, 0.01))),
                 Incertidumbre(0.30, -0.45, ((0.02, 0.005), (0.005, 0.03)))]


@pytest.mark.parametrize("formato", [Formato(3, "tiebreak_7"), Formato(3, "tiebreak_10"), Formato(3, "ventaja"),
                                     Formato(3, "super_tiebreak_10"), Formato(5, "tiebreak_10")])
@pytest.mark.parametrize("inc", INC_REALISTAS)
def test_cuadratura_q9_frente_a_q21(formato, inc):
    """Plan G.5: |P_{Q=9} − P_{Q=21}| < 1e-4 en ganador, 1.er set, tiebreak, totales y hándicaps. En mejor de 5 con
    Σ grande (DE total en logit ≥ 0,33) Q = 9 NO basta: la compuerta lo detecta (prueba siguiente)."""
    grande = inc.cov_parametros is not None and inc.sigma_eps >= 0.3
    if formato.mejor_de == 5 and grande:
        pytest.skip("cubierto por test_compuerta_detecta_q_insuficiente")
    for pa, pb in ((0.66, 0.60), (0.55, 0.50), (0.72, 0.70), (0.45, 0.62)):
        assert verificar_cuadratura(pa, pb, formato, inc, 9, 21, max_juegos=20) < 1e-4


def test_compuerta_detecta_q_insuficiente_y_q11_la_cumple():
    inc = Incertidumbre(0.30, -0.45, ((0.02, 0.005), (0.005, 0.03)))
    f = Formato(5, "tiebreak_10")
    pares = ((0.66, 0.60), (0.55, 0.50), (0.72, 0.70), (0.45, 0.62), (0.80, 0.78), (0.62, 0.62))
    assert max(verificar_cuadratura(pa, pb, f, inc, 9, 21) for pa, pb in pares) > 1e-4
    assert max(verificar_cuadratura(pa, pb, f, inc, 11, 21) for pa, pb in pares) < 1e-4
