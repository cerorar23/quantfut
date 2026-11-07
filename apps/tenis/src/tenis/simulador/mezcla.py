"""M̄_f: probabilidad de ganar y conjunta MEZCLADAS sobre la incertidumbre del partido (plan D.2, D.7, G.3).

(u_A, u_B) ~ N₂(0, Σ) en logit, Σ = Σ_ε (forma del día: σ_ε, ρ_ε) + V (incertidumbre de parámetros, opcional).
Cuadratura de Gauss–Hermite probabilista, Q nodos por eje (Q² en total), u = L·x con L·Lᵀ = Σ
(raíz simétrica, ver `raiz`). Los nodos son deterministas: no hay semilla.
Por nodo, juegos, tiebreaks y tablas de set se calculan una sola vez (vectorizado) y se reutilizan en ambos
primeros sacadores y en todos los sets; los nodos de Q se guardan en caché.
"""
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from numpy.polynomial.hermite_e import hermegauss

from ._comun import validar_p
from .formato import Formato, validar_formato
from .partido import SACA_DESCONOCIDO, conjunta, pesos_primer_sacador, prob_ganar_nodos, tablas
from .resultado import DistPartido
from .set_ import MAX_JUEGOS_CONTRATO

# 11 nodos por eje (121 en total): con 9 la cuadratura falla por 2,6–3,3e-4 en mejor de 5 con desviación total ≥ ~0,33 en
# logit (medido por `verificar_cuadratura`); con 11 cumple < 1e-4. Cuesta ~1,5 veces más que con 9 (mejor de 5: < 200 ms).
Q_POR_DEFECTO = 11


@dataclass(frozen=True)
class Incertidumbre:
    """Σ en escala logit. Sin valores por omisión: sigma_eps = 0 significa explícitamente «sin efecto del partido»."""
    sigma_eps: float
    rho_eps: float
    cov_parametros: tuple | None = None   # ((v11, v12), (v21, v22)) del método delta (plan D.7)

    def matriz(self) -> np.ndarray:
        s, r = float(self.sigma_eps), float(self.rho_eps)
        if not (np.isfinite(s) and np.isfinite(r)) or s < 0 or not -1.0 <= r <= 1.0:
            raise ValueError("σ_ε debe ser ≥ 0 y ρ_ε ∈ [−1, 1], finitos")
        m = s * s * np.array([[1.0, r], [r, 1.0]])
        if self.cov_parametros is not None:
            v = np.asarray(self.cov_parametros, dtype=float)
            if v.shape != (2, 2) or not np.all(np.isfinite(v)) or abs(v[0, 1] - v[1, 0]) > 1e-12:
                raise ValueError("cov_parametros debe ser una matriz 2x2 simétrica y finita")
            m = m + v
        return m


SIN_INCERTIDUMBRE = Incertidumbre(0.0, 0.0)


@lru_cache(maxsize=None)
def _gh(q: int) -> tuple[np.ndarray, np.ndarray]:
    x, w = hermegauss(q)
    return x, w / w.sum()


def raiz(sigma: np.ndarray) -> np.ndarray:
    """Raíz SIMÉTRICA L = V·√Λ·Vᵀ (L·Lᵀ = Σ). Frente a Cholesky, conserva la simetría A↔B de la rejilla de nodos:
    con p_A = p_B y varianzas iguales, M̄_f = 0,5 exacto y M̄(p_A, p_B) + M̄(p_B, p_A) = 1 sin error de cuadratura.
    Admite Σ semidefinida (ρ = ±1)."""
    val, vec = np.linalg.eigh(sigma)
    if val.min() < -1e-12 * max(1.0, abs(val.max())):
        raise ValueError("la covarianza no es semidefinida positiva")
    return (vec * np.sqrt(np.clip(val, 0.0, None))) @ vec.T


def nodos(p_a, p_b, inc: Incertidumbre, q: int = Q_POR_DEFECTO):
    """(p_A, p_B, peso) en los Q² nodos; con Σ = 0, un solo nodo de peso 1."""
    if isinstance(q, bool) or not isinstance(q, (int, np.integer)) or q < 1:
        raise ValueError("Q debe ser un entero ≥ 1")
    pa, pb = float(validar_p(p_a, "p_a")), float(validar_p(p_b, "p_b"))
    if not isinstance(inc, Incertidumbre):
        raise TypeError("la incertidumbre debe ser explícita (Incertidumbre; SIN_INCERTIDUMBRE si no hay)")
    sigma = inc.matriz()
    if not sigma.any():
        return np.array([pa]), np.array([pb]), np.ones(1)
    x, w = _gh(int(q))
    gx, gy = np.meshgrid(x, x, indexing="ij")
    u = raiz(sigma) @ np.vstack([gx.ravel(), gy.ravel()])
    la, lb = np.log(pa / (1 - pa)) + u[0], np.log(pb / (1 - pb)) + u[1]
    na, nb = 1.0 / (1.0 + np.exp(-la)), 1.0 / (1.0 + np.exp(-lb))
    validar_p(na, "p_a de un nodo"); validar_p(nb, "p_b de un nodo")
    return na, nb, np.outer(w, w).ravel()


def prob_ganar(p_a, p_b, formato: Formato, inc: Incertidumbre, q: int = Q_POR_DEFECTO,
               max_juegos: int = MAX_JUEGOS_CONTRATO) -> float:
    """M̄_f(p_A, p_B; Σ): solo el ganador, por la forma de sets (neutralidad del saque). ≈ 1 ms con 81 nodos."""
    formato = validar_formato(formato)
    na, nb, w = nodos(p_a, p_b, inc, q)
    return float(w @ prob_ganar_nodos(na, nb, formato, max_juegos))


def verificar_cuadratura(p_a, p_b, formato: Formato, inc: Incertidumbre, q: int = Q_POR_DEFECTO, q_ref: int = 21,
                         max_juegos: int = MAX_JUEGOS_CONTRATO) -> float:
    """Compuerta del plan G.5: máxima |P_Q − P_{Q_ref}| sobre ganador, 1.er set, tiebreak, totales de juegos
    (líneas x,5 de 12,5 a 64,5) y hándicap de juegos (−12,5 … 12,5). Debe quedar < 1e-4."""
    a = distribucion_mezclada(p_a, p_b, formato, inc, q, max_juegos=max_juegos)
    b = distribucion_mezclada(p_a, p_b, formato, inc, q_ref, max_juegos=max_juegos)
    dif = [abs(a.gana_a - b.gana_a), abs(a.primer_set_a_prob - b.primer_set_a_prob), abs(a.tiebreak_si - b.tiebreak_si)]
    tope = 2 * max_juegos if formato.decisivo == "ventaja" else 66
    dif += [abs(a.juegos_mas_de(x) - b.juegos_mas_de(x)) for x in np.arange(12.5, min(64.5, tope - 1), 1.0)]
    dif += [abs(a.handicap_juegos(h) - b.handicap_juegos(h)) for h in np.arange(-12.5, 13.0, 1.0)]
    return float(max(dif))


def distribucion_mezclada(p_a, p_b, formato: Formato, inc: Incertidumbre, q: int = Q_POR_DEFECTO,
                          saca_primero: str = SACA_DESCONOCIDO, max_juegos: int = MAX_JUEGOS_CONTRATO) -> DistPartido:
    """Conjunta completa del partido integrada sobre Σ (mezcla 50/50 del primer sacador)."""
    formato = validar_formato(formato)
    na, nb, w = nodos(p_a, p_b, inc, q)
    reg, dec = tablas(na, nb, formato, max_juegos)
    return conjunta(formato, reg, dec, w, pesos_primer_sacador(saca_primero))
