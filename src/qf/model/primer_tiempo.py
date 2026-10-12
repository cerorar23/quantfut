"""
Primera mitad a partir de los goles esperados del partido.

Los goles del 1T son Poisson independientes con media `PROPORCION_1T · (lambda, mu)`.
La proporción (local, visitante) se ajustó con football-data 2019/20-2021/22 y se midió
en 2022-2025 (`eval/primer_tiempo.py`, 6.236 partidos, cuotas de Pinnacle): solo
PASAN «ambos anotan 1T: no» y «gol en 1T: sí», por el lado y en el tramo medido
(62-95 %). Cambiar la proporción, el modelo o los mercados exige repetir esa prueba.
"""
from __future__ import annotations

import numpy as np
from scipy.stats import poisson

PROPORCION_1T = (0.4366, 0.4588)
MAX_GOLES_1T = 8
# Rango de probabilidad en el que se midió y, por tanto, el único donde se publica.
PROB_MIN_VALIDADA, PROB_MAX_VALIDADA = 0.62, 0.95


def probs(lam: float, mu: float, proporcion: tuple[float, float] = PROPORCION_1T) -> dict[str, float]:
    """Mercados de 1ª mitad desde los goles esperados del partido."""
    lh, la = proporcion[0] * lam, proporcion[1] * mu
    g = np.arange(MAX_GOLES_1T + 1)
    m = np.outer(poisson.pmf(g, lh), poisson.pmf(g, la))
    m = m / m.sum()
    total = np.add.outer(g, g)
    return {
        "gol_1t_si": float(1 - m[0, 0]),
        "ambos_1t_si": float(m[1:, 1:].sum()),
        "ganador_1t_local": float(np.tril(m, -1).sum()),
        "ganador_1t_empate": float(np.trace(m)),
        "ganador_1t_visita": float(np.triu(m, 1).sum()),
        "mas_1_5_1t": float(m[total > 1].sum()),
    }
