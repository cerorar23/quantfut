"""Inversión (plan D.4) y sensibilidad (plan G.7)."""
import numpy as np
import pytest

from tenis.simulador import Formato, Incertidumbre, SIN_INCERTIDUMBRE, prob_ganar
from tenis.simulador.inversion import invertir
from tenis.simulador.sensibilidad import sensibilidad

B3, B5 = Formato(3, "tiebreak_7"), Formato(5, "tiebreak_10")
FD = Incertidumbre(0.22, -0.45)


@pytest.mark.parametrize("formato", [B3, B5, Formato(3, "tiebreak_10"), Formato(3, "super_tiebreak_10")])
@pytest.mark.parametrize("suma,delta", [(1.25, 0.04), (1.12, -0.07), (1.30, 0.0005), (0.9, 0.2)])
def test_inversion_recupera_delta(formato, suma, delta):
    pi = prob_ganar(suma / 2 + delta, suma / 2 - delta, formato, FD)
    inv = invertir(suma, pi, formato, FD)
    assert abs(inv.delta - delta) < 1e-9
    assert abs(inv.p_a + inv.p_b - suma) < 1e-14
    assert abs(inv.pi_logrado - pi) < 1e-9


def test_inversion_con_pi_medio_da_delta_cero():
    assert abs(invertir(1.27, 0.5, B3, FD).delta) < 1e-10


def test_sensibilidad_signos_y_amplificacion():
    for inc in (SIN_INCERTIDUMBRE, FD):
        s3 = sensibilidad(0.64, 0.62, B3, inc)
        s5 = sensibilidad(0.64, 0.62, B5, inc)
        assert s3.d_gana_pa > 0 and s3.d_gana_pb < 0 and s3.d_primer_set_pa > 0
        assert s5.d_gana_pa > s3.d_gana_pa                       # el mejor de 5 amplifica más
        assert abs(s3.d_gana_pa + s3.d_gana_pb) < 0.1 * s3.d_gana_pa   # ≈ solo importa la diferencia
    sin, con = sensibilidad(0.64, 0.62, B3, SIN_INCERTIDUMBRE), sensibilidad(0.64, 0.62, B3, FD)
    assert con.d_gana_pa < sin.d_gana_pa                          # la forma del día amortigua


def test_sensibilidad_coincide_con_diferencias_de_prob_ganar():
    s = sensibilidad(0.66, 0.60, B3, FD)
    h = 1e-3
    ref = (prob_ganar(0.66 + h, 0.60, B3, FD) - prob_ganar(0.66 - h, 0.60, B3, FD)) / (2 * h)
    assert abs(s.d_gana_pa - ref) < 1e-4 * abs(ref) + 1e-6
    assert np.isfinite(s.d_juegos_pa) and np.isfinite(s.d_juegos_pb)
    assert set(s.por_punto_porcentual()) == {"d_gana_pa", "d_gana_pb", "d_primer_set_pa", "d_primer_set_pb",
                                             "d_juegos_pa", "d_juegos_pb"}
