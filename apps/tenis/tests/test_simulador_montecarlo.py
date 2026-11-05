"""Monte Carlo punto a punto (semilla fija) frente al cálculo exacto: verificación independiente de extremo a extremo
(incluida la regla de quién saca el set siguiente, que en Monte Carlo emerge de alternar juego a juego).
Criterio: |MC − exacto| ≤ 4,5 errores estándar en cada mercado y marcador frecuente (semilla fija: determinista)."""
import numpy as np
import pytest

from tenis.simulador import Formato, Incertidumbre, SIN_INCERTIDUMBRE, distribucion_mezclada
from tenis.simulador.montecarlo import simular

N = 60_000
Z = 4.5
CASOS = [(Formato(3, "tiebreak_7"), 0.64, 0.61, SIN_INCERTIDUMBRE, 11),
         (Formato(3, "tiebreak_10"), 0.70, 0.66, SIN_INCERTIDUMBRE, 12),
         (Formato(3, "super_tiebreak_10"), 0.62, 0.64, SIN_INCERTIDUMBRE, 13),
         (Formato(3, "ventaja"), 0.60, 0.57, SIN_INCERTIDUMBRE, 14),
         (Formato(5, "tiebreak_10"), 0.67, 0.63, SIN_INCERTIDUMBRE, 15),
         (Formato(3, "tiebreak_7"), 0.66, 0.60, Incertidumbre(0.22, -0.45), 16),
         (Formato(5, "tiebreak_10"), 0.95, 0.95, SIN_INCERTIDUMBRE, 17)]


def _cerca(est_ee, exacto):
    est, ee = est_ee
    ee = max(ee, np.sqrt(max(exacto * (1 - exacto), 1e-12) / N))
    return abs(est - exacto) <= Z * ee


@pytest.mark.parametrize("formato,pa,pb,inc,semilla", CASOS)
def test_montecarlo_frente_a_exacto(formato, pa, pb, inc, semilla):
    sim = simular(pa, pb, formato, N, semilla, inc=inc)
    ex = distribucion_mezclada(pa, pb, formato, inc, max_juegos=40)
    assert _cerca(sim.gana_a(), ex.gana_a)
    assert _cerca(sim.primer_set_a(), ex.primer_set_a_prob)
    for linea in (18.5, 21.5, 22.5, 24.5, 26.5, 38.5):
        assert _cerca(sim.juegos_mas_de(linea), ex.juegos_mas_de(linea)), linea
    freq = sim.marcadores()
    exactos = ex.marcadores()
    for m in sorted(exactos, key=exactos.get, reverse=True)[:15]:
        assert _cerca((freq.get(m, 0.0), 0.0), exactos[m]), m


def test_montecarlo_reproducible_con_semilla():
    a = simular(0.63, 0.6, Formato(3, "tiebreak_7"), 2000, 7)
    b = simular(0.63, 0.6, Formato(3, "tiebreak_7"), 2000, 7)
    assert np.array_equal(a.sets, b.sets)


def test_montecarlo_rechaza_entradas_malas():
    with pytest.raises(ValueError):
        simular(1.0, 0.6, Formato(3, "tiebreak_7"), 10, 1)
    with pytest.raises(ValueError):
        simular(0.6, 0.6, Formato(3, "tiebreak_7"), 10, 1, saca_primero="C")
    with pytest.raises(TypeError):
        simular(0.6, 0.6, None, 10, 1)
