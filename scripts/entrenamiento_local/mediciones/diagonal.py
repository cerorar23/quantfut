"""Inflación diagonal (Karlis y Ntzoufras, 2003) sobre las predicciones fuera de muestra del walk-forward.

p'(i,j) = (1-d)·p(i,j) + d·[i=j]·p(i,i)/Σp(k,k): sube la masa de los empates sin cambiar su reparto entre marcadores.
d se ajusta por log-verosimilitud del marcador exacto en el 70 % antiguo y se evalúa en el 30 % final (RPS pareado).
Además: nivel de goles (factor común en λ y μ) y las dos juntas.
"""
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from qf.model import ajuste
from qf.model.calibration import score_matrices

a = pd.read_pickle(sys.argv[1])
a = a[a.outcome.notna() & a.home_goals.notna()].sort_values(["kickoff_utc", "match_id"]).reset_index(drop=True)
y = (a.outcome.map({"H": 0, "D": 1, "A": 2}) if a.outcome.dtype == object else a.outcome.astype(int)).to_numpy()
lam, mu, rho = a.lam.to_numpy(float), a.mu.to_numpy(float), a.rho.to_numpy(float)
hg, ag = a.home_goals.to_numpy(int), a.away_goals.to_numpy(int)
G = 10


def matrices(k, d):
    # rho varía por partido en el walk-forward: se agrupa por valor
    out = np.empty((len(lam), G + 1, G + 1))
    for r in np.unique(rho):
        i = rho == r
        out[i] = score_matrices(lam[i] * k, mu[i] * k, float(r))
    if d:
        diag = np.einsum("nii->ni", out)
        base = np.zeros_like(out)
        for i in range(G + 1):
            base[:, i, i] = diag[:, i] / diag.sum(axis=1)
        out = (1 - d) * out + d * base
    return out


def probs(m):
    idx = np.arange(G + 1)
    h = m[:, idx[:, None] > idx[None, :]].sum(axis=1)
    dr = np.einsum("nii->n", m)
    aw = m[:, idx[:, None] < idx[None, :]].sum(axis=1)
    p = np.stack([h, dr, aw], axis=1)
    return p / p.sum(axis=1, keepdims=True)


def ll(m, rows):
    return -np.mean(np.log(np.clip(m[rows, np.clip(hg[rows], 0, G), np.clip(ag[rows], 0, G)], 1e-12, None)))


corte = int(len(a) * 0.70)
tr, va = np.arange(corte), np.arange(corte, len(a))
print(f"n={len(a)} ajuste={len(tr)} validación={len(va)}")
res = {}
for nombre, usar_k, usar_d in (("base", False, False), ("diagonal", False, True), ("nivel", True, False),
                               ("nivel+diagonal", True, True)):
    k, d = 1.0, 0.0
    if usar_k and usar_d:
        from scipy.optimize import minimize
        f = lambda v: ll(matrices(v[0], max(v[1], 0.0)), tr)  # noqa: E731
        o = minimize(f, [1.0, 0.02], method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-7})
        k, d = float(o.x[0]), max(float(o.x[1]), 0.0)
    elif usar_k:
        k = float(minimize_scalar(lambda v: ll(matrices(v, 0.0), tr), bounds=(0.9, 1.15), method="bounded").x)
    elif usar_d:
        d = float(minimize_scalar(lambda v: ll(matrices(1.0, v), tr), bounds=(0.0, 0.3), method="bounded").x)
    p = probs(matrices(k, d))
    res[nombre] = (k, d, p)
base = res["base"][2]
print(f"{'variante':16s} {'k':>6s} {'d':>6s} | validación: RPS     dRPS   p95      | empate pred / real")
for nombre, (k, d, p) in res.items():
    rv = ajuste._rps_por_partido(p[va], y[va]).mean()
    dl, p95 = ajuste._delta_rps(base[va], p[va], y[va])
    print(f"{nombre:16s} {k:6.3f} {d:6.3f} | {rv:.5f} {dl:+.5f} {p95:+.5f} | {p[va, 1].mean():.3f} / {(y[va] == 1).mean():.3f}")
# estabilidad: misma d ajustada en el 70 % antiguo, evaluada en los últimos 40 % y 50 %
for frac in (0.5, 0.6, 0.8):
    c = int(len(a) * frac)
    tr2, va2 = np.arange(c), np.arange(c, len(a))
    d2 = float(minimize_scalar(lambda v: ll(matrices(1.0, v), tr2), bounds=(0.0, 0.3), method="bounded").x)
    p2 = probs(matrices(1.0, d2))
    dl, p95 = ajuste._delta_rps(base[va2], p2[va2], y[va2])
    print(f"diagonal ajustada hasta {frac:.0%}: d={d2:.3f} validación n={len(va2)} dRPS {dl:+.5f} p95 {p95:+.5f}")
