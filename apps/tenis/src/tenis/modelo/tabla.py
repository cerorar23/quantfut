"""Enlace EXACTO de la pieza R con el simulador (plan D.3), tabulado para que 260.000 actualizaciones sean abordables.

M_ε(ρ) = M̄_f(expit(ℓ̄ + ρ), expit(ℓ̄ − ρ); Σ_ε) = `simulador.mezcla.prob_ganar` (forma del día por cuadratura).
Se tabula L(ρ) = ln M_ε(ρ) en una rejilla fina y se interpola con un spline cúbico (pure Python en la evaluación).
La incertidumbre de parámetros entra como u ~ N(0, v) en ρ (J·V·Jᵀ con J = [1, −1]: ρ desplaza los dos logits en
sentidos opuestos), así que M̄(ρ, v) = E_u[M_ε(ρ + u)] es una convolución 1-D EXACTA, que se integra con Gauss–Hermite.
Por simetría A↔B, 1 − M_ε(ρ) = M_ε(−ρ): la probabilidad del perdedor se calcula como L(−ρ), sin cancelación.
"""
import math
from dataclasses import dataclass

import numpy as np
from numpy.polynomial.hermite_e import hermegauss
from scipy.interpolate import CubicSpline

from tenis.simulador.formato import Formato
from tenis.simulador.mezcla import Incertidumbre, nodos, prob_ganar
from tenis.simulador.partido import prob_ganar_nodos

R_MAX, PASO = 6.0, 0.01
# Gauss–Hermite 1-D para la incertidumbre de parámetros: 16 nodos con v ≤ 0,15 (error < 1e-7 frente a la cuadratura
# del simulador con Q = 61) y 64 nodos por encima (M_ε es casi un escalón en |ρ| ≲ 2 y 16 nodos ya no bastan).
V_CAMBIO = 0.15


def _gh(q: int) -> tuple:
    x, w = hermegauss(q)
    return tuple(zip(x.tolist(), (w / w.sum()).tolist()))


NODOS_V, NODOS_V_ANCHO = _gh(16), _gh(64)


def expit(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype=float)))


def m_exacto(rhos, lbar: float, formato: Formato, inc: Incertidumbre, bloque: int = 100) -> np.ndarray:
    """M_ε(ρ) con el simulador: los mismos nodos que `mezcla.prob_ganar` (`mezcla.nodos`), vectorizado por bloques."""
    rhos = np.asarray(rhos, dtype=float)
    out = np.empty(len(rhos))
    for i0 in range(0, len(rhos), bloque):
        trozo = rhos[i0:i0 + bloque]
        pares = [nodos(expit(lbar + r), expit(lbar - r), inc) for r in trozo]
        pg = prob_ganar_nodos(np.concatenate([a for a, _, _ in pares]), np.concatenate([b for _, b, _ in pares]), formato)
        out[i0:i0 + len(trozo)] = pg.reshape(len(trozo), -1) @ pares[0][2]
    return out


@dataclass(frozen=True)
class Tabla:
    lo: float
    paso: float
    coef: tuple          # 4 listas (t³, t², t, 1) por intervalo
    r_lim: float         # |ρ| se recorta aquí: M_ε(−r_lim) ≥ 1e-13, así π ∈ (0, 1) sin desbordar

    def log_m(self, r: float):
        """(L, L', L'') en ρ (recortado a ±r_lim)."""
        r = -self.r_lim if r < -self.r_lim else (self.r_lim if r > self.r_lim else r)
        i = int((r - self.lo) / self.paso)
        i = len(self.coef[0]) - 1 if i >= len(self.coef[0]) else i
        t = r - (self.lo + i * self.paso)
        a3, a2, a1, a0 = self.coef[0][i], self.coef[1][i], self.coef[2][i], self.coef[3][i]
        return ((a3 * t + a2) * t + a1) * t + a0, (3.0 * a3 * t + 2.0 * a2) * t + a1, 6.0 * a3 * t + 2.0 * a2

    def prob(self, rho: float, v: float) -> float:
        """π = M̄(ρ, v) normalizado con el perdedor por simetría: π(−ρ) = 1 − π(ρ) exacto."""
        lm = self.log_m
        if v <= 0.0:
            pw, pl = math.exp(lm(rho)[0]), math.exp(lm(-rho)[0])
        else:
            s, nod = math.sqrt(v), (NODOS_V if v <= V_CAMBIO else NODOS_V_ANCHO)
            pw = sum(w * math.exp(lm(rho + s * x)[0]) for x, w in nod)
            pl = sum(w * math.exp(lm(-rho + s * x)[0]) for x, w in nod)
        return pw / (pw + pl)


def construir(lbar: float, formato: Formato, inc: Incertidumbre, r_max: float = R_MAX, paso: float = PASO) -> Tabla:
    rej = np.round(np.arange(-r_max, r_max + paso / 2, paso), 10)
    m = m_exacto(rej, lbar, formato, inc)
    if not np.all((m > 0) & (m < 1)):
        raise ValueError("M_ε fuera de (0, 1) en la rejilla: amplía la precisión o reduce r_max")
    sp = CubicSpline(rej, np.log(m))
    ok = rej[(rej >= 0) & (m[::-1] >= 1e-13)]           # m[::-1] en ρ = M_ε(−ρ)
    return Tabla(float(rej[0]), paso, tuple(c.tolist() for c in sp.c), float(ok.max()))


def convolucionar(tb: Tabla, s2: float) -> Tabla:
    """Tabla de M_R(ρ) = E_u[M_ε(ρ + u)], u ~ N(0, s2): el enlace con la varianza extra del partido σ_R² en la Σ de
    M̄_f (dirección [1, −1], exacta como convolución 1-D). s2 = 0 devuelve la MISMA tabla (modelo anterior exacto)."""
    if s2 <= 0.0:
        return tb
    rej = tb.lo + tb.paso * np.arange(len(tb.coef[0]) + 1)
    s, nod = math.sqrt(s2), (NODOS_V if s2 <= V_CAMBIO else NODOS_V_ANCHO)
    m = np.array([sum(w * math.exp(tb.log_m(r + s * x)[0]) for x, w in nod) for r in rej])
    sp = CubicSpline(rej, np.log(m))
    ok = rej[(rej >= -1e-9) & (m[::-1] >= 1e-13)]
    return Tabla(float(rej[0]), tb.paso, tuple(c.tolist() for c in sp.c), float(ok.max()))


def construir_todas(lbar: tuple, sigma_eps: float, rho_eps: float) -> dict:
    """tablas[(fmt, sup)] para los 6 formatos soportados × 4 superficies (ℓ̄ por superficie; se reutiliza si coincide)."""
    from .datos import FORMATOS
    inc, cache, out = Incertidumbre(sigma_eps, rho_eps), {}, {}
    for f, (mejor_de, decisivo) in enumerate(FORMATOS):
        for s, lb in enumerate(lbar):
            clave = (f, float(lb))
            if clave not in cache:
                cache[clave] = construir(float(lb), Formato(mejor_de, decisivo), inc)
            out[(f, s)] = cache[clave]
    return out


def error_tabla(tabla: Tabla, lbar: float, formato: Formato, inc: Incertidumbre, rhos) -> float:
    """Máx |exp L_tabla(ρ) − M_ε(ρ) exacto| en puntos fuera de la rejilla (la compuerta pide < 1e-6)."""
    ex = m_exacto(rhos, lbar, formato, inc)
    tab = np.array([math.exp(tabla.log_m(r)[0]) for r in rhos])
    return float(np.max(np.abs(tab - ex)))


def error_con_v(tabla: Tabla, lbar: float, formato: Formato, inc: Incertidumbre, pares, q: int = 61) -> float:
    """Máx |M̄_tabla(ρ, v) − prob_ganar(Σ_ε + v·[[1,−1],[−1,1]], Q = q)|. Con el Q = 11 por omisión del simulador
    la referencia misma falla en ~5e-4 con v = 0,3 (DE de la mezcla ≥ 0,33: limitación ya documentada en G.5)."""
    dif = []
    for r, v in pares:
        total = Incertidumbre(inc.sigma_eps, inc.rho_eps, ((v, -v), (-v, v)))
        dif.append(abs(tabla.prob(r, v) - prob_ganar(float(expit(lbar + r)), float(expit(lbar - r)), formato, total, q=q)))
    return float(max(dif))
