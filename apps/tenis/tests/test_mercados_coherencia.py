"""Pruebas unitarias de coherencia de mercados y distribución conjunta (§G.4, §G.6).

Verifica física del marcador, monotonicidad, simetría de jugadores, soporte físico exacto,
coherencia interna entre mercados derivados y la inversión conjunta exacta.
"""
import numpy as np
import pytest

from tenis.simulador.formato import Formato
from tenis.simulador.mezcla import Incertidumbre, distribucion_mezclada
from tenis.modelo.union import unir, sigma_m


@pytest.fixture
def inc_estandar():
    # Incertidumbre con covarianza entre saque/resto y varianza predictiva
    sig_eps = 0.18
    rho_eps = -0.68
    var_pred = 0.02
    return Incertidumbre(sig_eps, rho_eps, ((var_pred, -var_pred), (-var_pred, var_pred)))


@pytest.mark.parametrize("mejor_de,decisivo", [(3, "tiebreak_7"), (3, "tiebreak_10"), (5, "tiebreak_10")])
def test_suma_masas_unitarias(mejor_de, decisivo, inc_estandar):
    fmt = Formato(mejor_de, decisivo)
    d = distribucion_mezclada(0.65, 0.61, fmt, inc_estandar)

    # Suma de la conjunta total = 1.0 (dentro de tolerancia numérica de coma flotante)
    assert abs(d.masa_total - 1.0) < 1e-12

    # PMF discreta de juegos totales suma 1.0
    ok = ~d.cola
    jt = d.juegos[ok].round().astype(int)
    prob_juegos = np.bincount(jt, weights=d.prob[ok])
    assert abs(prob_juegos.sum() + d.masa_cola - 1.0) < 1e-12

    # PMF de diferencia de juegos suma 1.0
    dif = d.dif_juegos[ok].round().astype(int)
    dif_shift = dif - dif.min()
    prob_dif = np.bincount(dif_shift, weights=d.prob[ok])
    assert abs(prob_dif.sum() + d.masa_cola - 1.0) < 1e-12


@pytest.mark.parametrize("mejor_de,decisivo,t_min,t_max", [
    (3, "tiebreak_7", 12, 39),
    (3, "tiebreak_10", 12, 39),
    (5, "tiebreak_10", 18, 65),
])
def test_soporte_fisico_discreto(mejor_de, decisivo, t_min, t_max, inc_estandar):
    fmt = Formato(mejor_de, decisivo)
    d = distribucion_mezclada(0.66, 0.60, fmt, inc_estandar)
    ok = ~d.cola

    # Total de juegos dentro de soporte estricto [t_min, t_max]
    jt = d.juegos[ok].round().astype(int)
    assert np.all(jt >= t_min)
    assert np.all(jt <= t_max)

    # Si se juegan 3 sets en mejor de 3, T >= 18 (6-0, 0-6, 6-0)
    ns = d.sets_a[ok] + d.sets_b[ok]
    if mejor_de == 3:
        tres_sets = (ns == 3) & (d.prob[ok] > 0)
        assert np.all(jt[tres_sets] >= 18)

    # Si se juegan 4 o 5 sets en mejor de 5, T >= 24 y T >= 30
    if mejor_de == 5:
        cuatro_sets = (ns == 4) & (d.prob[ok] > 0)
        assert np.all(jt[cuatro_sets] >= 24)
        cinco_sets = (ns == 5) & (d.prob[ok] > 0)
        assert np.all(jt[cinco_sets] >= 30)

    # n_tb <= ns
    assert np.all(d.n_tb[ok] <= ns)


@pytest.mark.parametrize("mejor_de,decisivo", [(3, "tiebreak_7"), (5, "tiebreak_10")])
def test_monotonia_mercados(mejor_de, decisivo, inc_estandar):
    fmt = Formato(mejor_de, decisivo)
    d = distribucion_mezclada(0.67, 0.62, fmt, inc_estandar)

    # P(T > L) decreciente o no-creciente en L
    lineas_juegos = np.arange(15.5, 45.5, 1.0)
    probs_totales = [d.juegos_mas_de(L) for L in lineas_juegos]
    assert np.all(np.diff(probs_totales) <= 1e-15)

    # P(D + H > 0) no-decreciente en H
    lineas_handicap = np.arange(-8.5, 8.5, 1.0)
    probs_handicap = [d.handicap_juegos(H) for H in lineas_handicap]
    assert np.all(np.diff(probs_handicap) >= -1e-15)

    # Coherencia de hándicap de sets: P(hsets -1.5) <= P(ganador) <= P(hsets +1.5)
    p_gana = d.gana_a
    p_h_menos_1_5 = d.handicap_sets(-1.5)
    p_h_mas_1_5 = d.handicap_sets(1.5)
    assert p_h_menos_1_5 <= p_gana + 1e-15
    assert p_gana <= p_h_mas_1_5 + 1e-15
    assert abs(d.handicap_sets(0.0) - p_gana) < 1e-15


def test_simetria_jugadores(inc_estandar):
    fmt = Formato(3, "tiebreak_7")
    d_ab = distribucion_mezclada(0.68, 0.58, fmt, inc_estandar)
    d_ba = distribucion_mezclada(0.58, 0.68, fmt, inc_estandar)

    # P(A gana) + P(B gana) = 1.0
    assert abs(d_ab.gana_a + d_ba.gana_a - 1.0) < 1e-12

    # Primer set simétrico
    assert abs(d_ab.primer_set_a_prob + d_ba.primer_set_a_prob - 1.0) < 1e-12

    # Totales y tiebreak son invariantes al orden de los jugadores
    assert abs(d_ab.media_juegos - d_ba.media_juegos) < 1e-12
    assert abs(d_ab.tiebreak_si - d_ba.tiebreak_si) < 1e-12
    for L in (19.5, 21.5, 23.5):
        assert abs(d_ab.juegos_mas_de(L) - d_ba.juegos_mas_de(L)) < 1e-12

    # Hándicap reflejado: P(A gana por > h) == P(B pierde por > h)
    for h in (-2.5, -0.5, 1.5, 3.5):
        # A cubre -h significa D_A > h. Al invertir jugadores D_B = -D_A, luego D_B < -h -> 1 - P(D_B >= -h)
        assert abs(d_ab.handicap_juegos(h) - (1.0 - d_ba.handicap_juegos(-h))) < 1e-12


def test_inversion_coherencia_ganador():
    # Para cualquier (S_hat, pi_m) alcanzable, la inversión genera (p_A, p_B)
    # cuya conjunta reproduce pi_m a menos de 1e-8.
    sig_eps = 0.179
    rho_eps = -0.733
    var_pred = 0.008 + 0.0138  # con c_inf
    s_hat = 0.615
    fmt_idx = 0  # 3, tiebreak_7
    fmt = Formato(3, "tiebreak_7")

    for pi_objetivo in (0.25, 0.40, 0.50, 0.73, 0.88):
        u = unir(s_hat, pi_objetivo, fmt_idx, sig_eps, rho_eps, var_pred)
        inc = sigma_m(sig_eps, rho_eps, var_pred)
        dist = distribucion_mezclada(u.p_a, u.p_b, fmt, inc)
        assert abs(dist.gana_a - pi_objetivo) < 1e-7


def test_coherencia_marcador_sets_y_ganador(inc_estandar):
    fmt = Formato(3, "tiebreak_7")
    d = distribucion_mezclada(0.64, 0.60, fmt, inc_estandar)
    ok = ~d.cola

    p_2_0 = float(d.prob[ok & (d.sets_a == 2) & (d.sets_b == 0)].sum())
    p_2_1 = float(d.prob[ok & (d.sets_a == 2) & (d.sets_b == 1)].sum())
    p_0_2 = float(d.prob[ok & (d.sets_a == 0) & (d.sets_b == 2)].sum())
    p_1_2 = float(d.prob[ok & (d.sets_a == 1) & (d.sets_b == 2)].sum())

    # Suma de marcadores = 1
    assert abs((p_2_0 + p_2_1 + p_0_2 + p_1_2) - 1.0) < 1e-12

    # P(ganador A) = P(2-0) + P(2-1)
    assert abs(d.gana_a - (p_2_0 + p_2_1)) < 1e-12

    # P(hsets -1.5) = P(2-0)
    assert abs(d.handicap_sets(-1.5) - p_2_0) < 1e-12

    # P(hsets +1.5) = 1 - P(0-2)
    assert abs(d.handicap_sets(1.5) - (1.0 - p_0_2)) < 1e-12
