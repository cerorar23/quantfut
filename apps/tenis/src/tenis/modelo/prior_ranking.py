"""Prior explícito de un jugador sin historia (plan D.6): θ₀ = b·(ln rank − ln 100), d ~ N(0, σ_d²·Ω).

Sin historia y sin ranking punto en el tiempo NO hay prior: el partido no se pronostica (nunca un promedio silencioso).
La marca `prior=ranking` dura mientras el jugador no tenga ninguna actualización con un resultado propio.
"""
import math

from .superficie import omega

RANK_CENTRO = 100.0


def theta0(rank: float, b_rank: float) -> float:
    return b_rank * (math.log(rank) - math.log(RANK_CENTRO))


def estado_inicial(rank, psi):
    """(media de 5, covarianza 5×5) o None si el ranking falta o no es válido."""
    if rank is None or rank != rank or rank < 1:
        return None
    om = omega(psi.r_omega)
    v = [[0.0] * 5 for _ in range(5)]
    v[0][0] = psi.sigma_theta0 ** 2
    for i in range(4):
        for j in range(4):
            v[i + 1][j + 1] = psi.sigma_d ** 2 * om[i][j]
    return [theta0(rank, psi.b_rank), 0.0, 0.0, 0.0, 0.0], v
