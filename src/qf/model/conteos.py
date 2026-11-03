"""
Motor C del rediseño: conteos de partido (córners y tarjetas) con regresión binomial negativa.

    y ~ BN(μ, κ),  log μ = Xβ,  log κ = γ0 + Zγ   (Var = μ + μ²/κ)

Adaptación de Yip et al. (arXiv:2112.13001) para córners: se prueba la binomial negativa de dispersión variable; el
geométrico-Poisson del artículo no está implementado aquí. La
covariable clave son los goles esperados. Dawson et al. (JRSS-A 2007) para tarjetas: árbitro, igualdad del
partido y local. Cada lado se modela por separado; el total sale de convolucionar las dos distribuciones
(independencia entre lados, simplificación a medir).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln, digamma
from scipy.stats import nbinom
from .fit_checks import validar_ajuste


def _con_constante(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return np.column_stack([np.ones(len(x)), x]) if x.size else np.ones((len(x), 1))


class RegresionNB:
    def __init__(self, ridge: float = 1e-3):
        self.ridge = ridge
        self.beta: np.ndarray | None = None
        self.gamma: np.ndarray | None = None
        self.diagnostico: dict | None = None

    @property
    def kappa(self) -> float:
        return float(np.exp(np.clip(self.gamma[0], -6, 12)))

    def _partes(self, x, z):
        X = _con_constante(x)
        Z = _con_constante(np.empty((len(X), 0)) if z is None else z)
        return X, Z

    def _nll(self, theta, X, Z, y):
        return self._objetivo(theta,X,Z,y)[0]

    def _objetivo(self, theta, X, Z, y):
        kb = X.shape[1]
        b, g = theta[:kb], theta[kb:]
        eta, zeta = X @ b, Z @ g
        mu = np.exp(np.clip(eta, -10, 10)); k = np.exp(np.clip(zeta, -6, 12))
        ll = (gammaln(y + k) - gammaln(k) - gammaln(y + 1) + k * np.log(k / (k + mu)) + y * np.log(mu / (k + mu)))
        score_mu=k*(y-mu)/(k+mu) * ((eta>=-10)&(eta<=10))
        score_k=k*(digamma(y+k)-digamma(k)+np.log(k/(k+mu))+1-(k+y)/(k+mu)) * ((zeta>=-6)&(zeta<=12))
        grad=np.concatenate([-X.T @ score_mu,-Z.T @ score_k])
        grad[1:kb]+=2*self.ridge*theta[1:kb]
        return -ll.sum() + self.ridge * np.sum(theta[1:kb] ** 2),grad

    def fit(self, x, y, z=None) -> "RegresionNB":
        X, Z = self._partes(x, z)
        y = np.asarray(y, dtype=float)
        if not len(y) or len(y) != len(X) or len(Z) != len(X) or not np.isfinite(y).all() or (y < 0).any() or (y != np.floor(y)).any():
            raise ValueError('Se requieren conteos enteros no negativos y matrices alineadas')
        if not np.isfinite(X).all() or not np.isfinite(Z).all():
            raise ValueError('Las covariables deben ser finitas')
        t0 = np.zeros(X.shape[1] + Z.shape[1]); t0[0] = np.log(max(y.mean(), 1e-3)); t0[X.shape[1]] = 2.0
        self.beta = self.gamma = self.diagnostico = None
        r = minimize(self._objetivo, t0, args=(X, Z, y), jac=True, method="L-BFGS-B", options={'maxiter': 1000})
        self.diagnostico = validar_ajuste(r, 'Regresión NB')
        self.beta, self.gamma = r.x[:X.shape[1]], r.x[X.shape[1]:]
        return self

    def nll(self, x, y, z=None) -> float:
        X, Z = self._partes(x, z)
        return float(self._nll(np.concatenate([self.beta, self.gamma]), X, Z, np.asarray(y, float)))

    def media(self, x) -> np.ndarray:
        return np.exp(np.clip(_con_constante(x) @ self.beta, -10, 10))

    def pmf(self, x, maximo: int, z=None) -> np.ndarray:
        """Distribución (n, maximo + 1); la cola por encima de `maximo` se suma a la última casilla."""
        X, Z = self._partes(x, z)
        mu = np.exp(np.clip(X @ self.beta, -10, 10)); k = np.exp(np.clip(Z @ self.gamma, -6, 12))
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
