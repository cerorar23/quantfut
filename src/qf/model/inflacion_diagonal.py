"""
Inflación diagonal de la matriz de marcadores (Karlis y Ntzoufras, JRSS-D 2003; JSS 2005).

    P'(x, y) = (1 − p)·P(x, y) + p·θ_x·1[x = y],   θ sobre {0-0, 1-1, 2-2}

Corrige un exceso de empates que la Poisson (o Dixon-Coles) no recoge. La τ de Dixon-Coles ya infla los cuatro
marcadores bajos; esto añade una masa libre en la diagonal. Se ajusta por máxima verosimilitud del MARCADOR con
predicciones fuera de muestra, como el calibrador afín, y se mide fuera de muestra.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .calibration import score_matrices

EPS = 1e-12
DIAG = 3  # 0-0, 1-1, 2-2


class InflacionDiagonal:
    def __init__(self):
        self.p = 0.0
        self.theta = np.array([1 / 3] * DIAG)

    @staticmethod
    def _desempaquetar(x):
        p = 1 / (1 + np.exp(-x[0]))
        t = np.exp(np.concatenate([[0.0], x[1:]])); t /= t.sum()
        return p, t

    def fit(self, lam, mu, rho, home_goals, away_goals) -> "InflacionDiagonal":
        m = score_matrices(np.asarray(lam, float), np.asarray(mu, float), float(rho))
        hg = np.clip(np.asarray(home_goals, int), 0, m.shape[1] - 1)
        ag = np.clip(np.asarray(away_goals, int), 0, m.shape[2] - 1)
        base = m[np.arange(len(hg)), hg, ag]
        diag = (hg == ag) & (hg < DIAG)

        def nll(x):
            p, t = self._desempaquetar(x)
            q = (1 - p) * base + np.where(diag, p * t[np.minimum(hg, DIAG - 1)], 0.0)
            return -np.log(np.clip(q, EPS, None)).sum()

        r = minimize(nll, np.array([-3.0, 0.0, 0.0]), method="L-BFGS-B")
        self.p, self.theta = self._desempaquetar(r.x)
        return self

    def probs_1x2(self, lam, mu, rho) -> np.ndarray:
        m = score_matrices(np.asarray(lam, float), np.asarray(mu, float), float(rho))
        g = np.arange(m.shape[1])
        home = m[:, g[:, None] > g[None, :]].sum(1); away = m[:, g[:, None] < g[None, :]].sum(1)
        draw = np.trace(m, axis1=1, axis2=2)
        out = (1 - self.p) * np.stack([home, draw, away], 1)
        out[:, 1] += self.p  # toda la masa inflada cae en la diagonal
        return out
