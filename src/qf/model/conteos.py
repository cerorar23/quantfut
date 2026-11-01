"""
Motor C del rediseño: conteos de partido (córners y tarjetas) con regresión binomial negativa.

    y ~ BN(μ, κ),  log μ = Xβ,  log κ = γ0 + Zγ   (Var = μ + μ²/κ)

Yip et al. (arXiv:2112.13001) para córners: la binomial negativa con dispersión variable gana a la Poisson y la
covariable clave son los goles esperados. Dawson et al. (JRSS-A 2007) para tarjetas: árbitro, igualdad del
partido y local. Cada lado se modela por separado; el total sale de convolucionar las dos distribuciones
(independencia entre lados, simplificación a medir).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import nbinom


def _con_constante(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return np.column_stack([np.ones(len(x)), x]) if x.size else np.ones((len(x), 1))


class RegresionNB:
    def __init__(self, ridge: float = 1e-3):
        self.ridge = ridge
        self.beta: np.ndarray | None = None
        self.gamma: np.ndarray | None = None

    @property
    def kappa(self) -> float:
        return float(np.exp(self.gamma[0]))

    def _partes(self, x, z):
        X = _con_constante(x)
        Z = _con_constante(np.empty((len(X), 0)) if z is None else z)
        return X, Z

    def _nll(self, theta, X, Z, y):
        kb = X.shape[1]
        b, g = theta[:kb], theta[kb:]
        mu = np.exp(np.clip(X @ b, -10, 10)); k = np.exp(np.clip(Z @ g, -6, 12))
        ll = (gammaln(y + k) - gammaln(k) - gammaln(y + 1) + k * np.log(k / (k + mu)) + y * np.log(mu / (k + mu)))
        return -ll.sum() + self.ridge * np.sum(theta[1:kb] ** 2)

    def fit(self, x, y, z=None) -> "RegresionNB":
        X, Z = self._partes(x, z)
        y = np.asarray(y, dtype=float)
        t0 = np.zeros(X.shape[1] + Z.shape[1]); t0[0] = np.log(max(y.mean(), 1e-3)); t0[X.shape[1]] = 2.0
        r = minimize(self._nll, t0, args=(X, Z, y), method="L-BFGS-B")
        self.beta, self.gamma = r.x[:X.shape[1]], r.x[X.shape[1]:]
        return self

    def nll(self, x, y, z=None) -> float:
        X, Z = self._partes(x, z)
        return float(self._nll(np.concatenate([self.beta, self.gamma]), X, Z, np.asarray(y, float)))

    def media(self, x) -> np.ndarray:
        return np.exp(_con_constante(x) @ self.beta)

    def pmf(self, x, maximo: int, z=None) -> np.ndarray:
        """Distribución (n, maximo + 1); la cola por encima de `maximo` se suma a la última casilla."""
        X, Z = self._partes(x, z)
        mu = np.exp(X @ self.beta); k = np.exp(Z @ self.gamma)
        g = np.arange(maximo + 1)
        p = nbinom.pmf(g[None, :], k[:, None], (k / (k + mu))[:, None])
        p[:, -1] += np.clip(1 - p.sum(1), 0, None)
        return p


def pmf_suma(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Distribución de la suma de dos conteos independientes, fila a fila."""
    n, m = a.shape[1], b.shape[1]
    out = np.zeros((a.shape[0], n + m - 1))
    for j in range(m):
        out[:, j:j + n] += a * b[:, j:j + 1]
    return out
