"""Utilidades comunes de las mediciones del modelo dinámico y del prior de ascendidos (26-oct-2026)."""
import numpy as np
import pandas as pd

from qf.model import ajuste
from qf.model.calibration import score_matrices

G = 10


def probs_de_lambdas(lam, mu, rho):
    """1X2 desde (λ, μ, ρ). `rho` puede ser escalar o un vector (el walk-forward reajusta ρ cada mes)."""
    lam, mu = np.asarray(lam, float), np.asarray(mu, float)
    rho = np.broadcast_to(np.asarray(rho, float), lam.shape)
    out = np.empty((len(lam), 3))
    idx = np.arange(G + 1)
    for r in np.unique(rho):
        i = rho == r
        m = score_matrices(lam[i], mu[i], float(r), G)
        h = m[:, idx[:, None] > idx[None, :]].sum(axis=1)
        d = np.einsum("nii->n", m)
        a = m[:, idx[:, None] < idx[None, :]].sum(axis=1)
        p = np.stack([h, d, a], axis=1)
        out[i] = p / p.sum(axis=1, keepdims=True)
    return out


def logver_marcador(lam, mu, rho, hg, ag):
    """Log-verosimilitud media del marcador exacto (la que usan las puertas del calibrador)."""
    lam, mu = np.asarray(lam, float), np.asarray(mu, float)
    rho = np.broadcast_to(np.asarray(rho, float), lam.shape)
    out = np.empty(len(lam))
    for r in np.unique(rho):
        i = rho == r
        m = score_matrices(lam[i], mu[i], float(r), G)
        out[i] = np.log(np.clip(m[np.arange(i.sum()), np.clip(hg[i], 0, G), np.clip(ag[i], 0, G)], 1e-12, None))
    return float(out.mean())


def rps(p, y):
    return ajuste._rps_por_partido(p, y)


def delta(p_base, p_nuevo, y):
    """ΔRPS (negativo = mejora) y percentil 95 del remuestreo pareado."""
    return ajuste._delta_rps(p_base, p_nuevo, y)


def cargar_oos(ruta):
    a = pd.read_pickle(ruta)
    a = a[a.outcome.notna()].sort_values(["kickoff_utc", "match_id"]).reset_index(drop=True)
    return a
