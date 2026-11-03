"""
Los mercados que pidió el titular (1-nov-2026, listas 1 y 2): probabilidad de cada opción y su liquidación real.

Todo sale de distribuciones ya medidas en el rediseño: la matriz de marcadores del partido (A0 con xG o el mercado
invertido con `market_anchor`), un modelo por mitades (cada mitad Poisson con la parte `f1` de los goles esperados,
estimada por liga con temporadas anteriores) y las distribuciones de córners (Yip) y amarillas (Dawson). Las líneas
asiáticas enteras devuelven el dinero si se cae justo en la línea; por eso cada opción da (P gana, P devuelve).
"""
from __future__ import annotations

import numpy as np
from scipy.stats import binom, poisson

G = 9  # goles 0..8 por equipo y mitad


def prob_linea(pmf: np.ndarray, soporte: np.ndarray, linea: float, direccion: str) -> tuple[np.ndarray, np.ndarray]:
    """(P gana, P devuelve) de «más/menos de `linea`» sobre una variable entera con distribución `pmf` (n, k)."""
    s = np.asarray(soporte)
    gana = s > linea if direccion == "mas" else s < linea
    devuelve = s == linea
    return pmf[:, gana].sum(1), pmf[:, devuelve].sum(1)


def liquidar(valor: np.ndarray, linea: float, direccion: str) -> np.ndarray:
    v = np.asarray(valor, float)
    gana = v > linea if direccion == "mas" else v < linea
    return np.where(v == linea, "devuelve", np.where(gana, "gana", "pierde"))


def matrices_mitades(lam, mu, f1: float | np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Matrices (n, G, G) de la primera y la segunda parte, Poisson independientes con f1 y 1 − f1 del total."""
    lam, mu = np.asarray(lam, float), np.asarray(mu, float)
    f1 = np.broadcast_to(np.asarray(f1, float), lam.shape)
    g = np.arange(G)

    def mat(a, b):
        m = poisson.pmf(g[None, :], a[:, None])[:, :, None] * poisson.pmf(g[None, :], b[:, None])[:, None, :]
        return m / m.sum((1, 2), keepdims=True)

    return mat(lam * f1, mu * f1), mat(lam * (1 - f1), mu * (1 - f1))


def pmf_suma(m: np.ndarray) -> np.ndarray:
    """Total de goles de una matriz (n, G, G) → (n, 2G − 1)."""
    n, a, b = m.shape
    out = np.zeros((n, a + b - 1))
    for i in range(a):
        out[:, i:i + b] += m[:, i, :]
    return out


def pmf_diferencia(m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Local − visita de una matriz (n, G, G): (pmf, soporte de −(G−1) a G−1)."""
    n, a, b = m.shape
    out = np.zeros((n, a + b - 1))
    for i in range(a):
        for j in range(b):
            out[:, i - j + b - 1] += m[:, i, j]
    return out, np.arange(-(b - 1), a)


def adelgazar(pmf: np.ndarray, s: float) -> np.ndarray:
    """Conteo de la primera parte si cada evento del partido cae en ella con probabilidad `s` (binomial)."""
    n_max = pmf.shape[1]
    k = np.arange(n_max)
    B = binom.pmf(k[None, :], k[:, None], s)  # (total, primera parte)
    return pmf @ B


def mitad_con_mas_goles(m1: np.ndarray, m2: np.ndarray) -> np.ndarray:
    """P(1.ª > 2.ª), P(igual), P(2.ª > 1.ª) en goles totales."""
    t1, t2 = pmf_suma(m1), pmf_suma(m2)
    c1, c2 = np.cumsum(t1, 1), np.cumsum(t2, 1)
    igual = (t1 * t2).sum(1)
    segunda = (t2[:, 1:] * c1[:, :-1]).sum(1)
    return np.stack([1 - igual - segunda, igual, segunda], 1)


def descanso_final(m1: np.ndarray, m2: np.ndarray) -> np.ndarray:
    """Matriz (n, 3, 3) de resultado al descanso × resultado final (L, X, V)."""
    n = m1.shape[0]
    out = np.zeros((n, 3, 3))
    for a in range(G):
        for b in range(G):
            p1 = m1[:, a, b]
            if p1.max() < 1e-9:
                continue
            ht = 0 if a > b else 1 if a == b else 2
            d2, sop = pmf_diferencia(m2)
            dif_final = a - b + sop
            out[:, ht, 0] += p1 * d2[:, dif_final > 0].sum(1)
            out[:, ht, 1] += p1 * d2[:, dif_final == 0].sum(1)
            out[:, ht, 2] += p1 * d2[:, dif_final < 0].sum(1)
    return out
