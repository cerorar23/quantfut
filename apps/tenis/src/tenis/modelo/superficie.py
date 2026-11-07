"""Superficie (plan D.3, D.5): estructura de Ω y multiplicador del diferencial con contextos.

d_{i,s} ~ N₄(0, σ_d²·Ω) con Ω equicorrelada (un parámetro r_Ω estimado; prior en lugar de LKJ, declarado en el
informe). κ^R_{c,Hard} ≡ 1. Los contextos (semana previa GS, equipos, JJOO) modifican el multiplicador: (1 + Σ γ_k z_k).
"""


def omega(r: float) -> list:
    return [[1.0 if i == j else r for j in range(4)] for i in range(4)]


def multiplicador(kappa: tuple, sup: int, gamma: tuple, z: tuple) -> float:
    """κ_s · (1 + Σ γ_k z_k); z = (semana previa GS, equipos, JJOO)."""
    return kappa[sup] * (1.0 + sum(g * x for g, x in zip(gamma, z)))
