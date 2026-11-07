"""Pieza C (plan D.4): δ* tal que M̄_f(Ŝ/2 + δ, Ŝ/2 − δ; Σ) = π, por bisección hasta |Δδ| < 1e-10.

M̄_f es estrictamente creciente en δ con la suma fija (B03; cada componente de la mezcla lo es), así que la
raíz es única. Si π no se alcanza con p_A, p_B ∈ [0,02; 0,98], se rechaza (el partido no se sella).
"""
from dataclasses import dataclass

import numpy as np

from .formato import Formato, validar_formato
from .mezcla import Q_POR_DEFECTO, Incertidumbre, prob_ganar

P_MIN, P_MAX, TOLERANCIA = 0.02, 0.98, 1e-10


@dataclass(frozen=True)
class Inversion:
    delta: float
    p_a: float
    p_b: float
    pi_logrado: float
    iteraciones: int


def invertir(suma: float, pi: float, formato: Formato, inc: Incertidumbre, q: int = Q_POR_DEFECTO,
             tol: float = TOLERANCIA) -> Inversion:
    formato = validar_formato(formato)
    s, pi = float(suma), float(pi)
    if not (np.isfinite(s) and np.isfinite(pi)):
        raise ValueError("Ŝ y π deben ser finitos")
    if not 0.0 < pi < 1.0:
        raise ValueError(f"π = {pi} fuera de (0, 1)")
    if not 2 * P_MIN < s < 2 * P_MAX:
        raise ValueError(f"Ŝ = {s} fuera de ({2 * P_MIN}, {2 * P_MAX}): no deja margen para δ")
    lo, hi = max(s / 2 - P_MAX, P_MIN - s / 2), min(P_MAX - s / 2, s / 2 - P_MIN)

    def m(d: float) -> float:
        return prob_ganar(s / 2 + d, s / 2 - d, formato, inc, q)

    m_lo, m_hi = m(lo), m(hi)
    if not m_lo < pi < m_hi:
        raise ValueError(f"π = {pi:.6f} inalcanzable con Ŝ = {s} y p ∈ [{P_MIN}; {P_MAX}] "
                         f"(rango [{m_lo:.6f}; {m_hi:.6f}])")
    try:
        from scipy.optimize import brentq
        res = brentq(lambda x: m(x) - pi, lo, hi, xtol=tol, rtol=tol, full_output=True)
        d = float(res[0])
        it = int(res[1].iterations)
        return Inversion(d, s / 2 + d, s / 2 - d, m(d), it)
    except Exception:
        it = 0
        while hi - lo > tol:
            mid = 0.5 * (lo + hi)
            if m(mid) < pi:
                lo = mid
            else:
                hi = mid
            it += 1
        d = 0.5 * (lo + hi)
        return Inversion(d, s / 2 + d, s / 2 - d, m(d), it)
