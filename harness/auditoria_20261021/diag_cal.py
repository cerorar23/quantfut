"""Calibradores alternativos sobre el walk-forward ampliado (ajuste en el 60 % antiguo, prueba en el 40 % reciente).

(a) producción: afín en log-lambda minimizando log-loss del 1X2
(b) conjunto: afín en log-lambda + rho minimizando la log-verosimilitud del MARCADOR exacto
(c) (b) + inflación de la diagonal (empates) con parámetro propio
Solo lectura.
"""
import glob

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

import sys
if len(sys.argv) > 1:
    rutas = [f"/srv/quantfut/artifacts/audit/wf_{sys.argv[1]}.pkl"]
else:
    rutas = sorted(glob.glob("/srv/quantfut/artifacts/ext/oos_*.pkl")) + ["/srv/quantfut/artifacts/oos_2026.10.19-131830.pkl"]
d = pd.concat([pd.read_pickle(r) for r in rutas]).drop_duplicates("match_id").sort_values("kickoff_utc").reset_index(drop=True)
print("fuente:", rutas[0])
G = 11
g = np.arange(G)
hg = np.clip(d.home_goals.to_numpy(), 0, G - 1)
ag = np.clip(d.away_goals.to_numpy(), 0, G - 1)
o = d.outcome.to_numpy()
corte = int(len(d) * 0.6)
TR, TE = np.arange(corte), np.arange(corte, len(d))
print("ajuste", len(TR), "prueba", len(TE), "corte", d.kickoff_utc.iloc[corte])
ii, jj = np.meshgrid(g, g, indexing="ij")
HOME, DRAW = ii > jj, ii == jj


def matrices(lam, mu, rho, infl=0.0):
    ph = poisson.pmf(g[None, :], lam[:, None])
    pa = poisson.pmf(g[None, :], mu[:, None])
    m = ph[:, :, None] * pa[:, None, :]
    m[:, 0, 0] *= 1 - lam * mu * rho
    m[:, 0, 1] *= 1 + lam * rho
    m[:, 1, 0] *= 1 + mu * rho
    m[:, 1, 1] *= 1 - rho
    m = np.clip(m, 1e-12, None)
    if infl:
        m[:, DRAW] *= np.exp(infl)
    return m / m.sum(axis=(1, 2), keepdims=True)


def aplica(x, idx):
    a0, a1, b0, b1 = x[:4]
    lam = np.exp(a0 + a1 * np.log(d.lam.to_numpy()[idx]))
    mu = np.exp(b0 + b1 * np.log(d.mu.to_numpy()[idx]))
    rho = x[4] if len(x) > 4 else d.rho.to_numpy()[idx]
    infl = x[5] if len(x) > 5 else 0.0
    return matrices(lam, mu, rho, infl)


def p1x2(m):
    return np.stack([m[:, HOME].sum(1), m[:, DRAW].sum(1), m[:, ~HOME & ~DRAW].sum(1)], 1)


def metricas(nombre, m, idx):
    P = p1x2(m)
    oo = o[idx]
    c = np.cumsum(P, 1)[:, :2]
    co = np.cumsum(np.eye(3)[oo], 1)[:, :2]
    rps = np.mean(np.sum((c - co) ** 2, 1) / 2)
    ll = -np.mean(np.log(P[np.arange(len(oo)), oo]))
    over = 1 - m[:, (ii + jj) <= 2].sum(1)
    yo = (d.home_goals.to_numpy()[idx] + d.away_goals.to_numpy()[idx]) > 2.5
    llo = -np.mean(yo * np.log(over) + (1 - yo) * np.log(1 - over))
    btts = m[:, 1:, 1:].sum((1, 2))
    yb = (d.home_goals.to_numpy()[idx] > 0) & (d.away_goals.to_numpy()[idx] > 0)
    llb = -np.mean(yb * np.log(btts) + (1 - yb) * np.log(1 - btts))
    lls = -np.mean(np.log(m[np.arange(len(idx)), hg[idx], ag[idx]]))
    print(f"  {nombre:26s} RPS {rps:.5f} LL1x2 {ll:.5f} | +2.5 p {over.mean():.3f} y {yo.mean():.3f} LL {llo:.5f} | "
          f"BTTS p {btts.mean():.3f} y {yb.mean():.3f} LL {llb:.5f} | marcador LL {lls:.5f} | "
          f"0-0 {m[:, 0, 0].mean():.4f}/{((hg[idx] == 0) & (ag[idx] == 0)).mean():.4f} 2-2 {m[:, 2, 2].mean():.4f}/{((hg[idx] == 2) & (ag[idx] == 2)).mean():.4f}")


def obj_1x2(x):
    P = p1x2(aplica(x, TR))
    return -np.mean(np.log(np.clip(P[np.arange(len(TR)), o[TR]], 1e-12, None)))


def obj_marcador(x):
    m = aplica(x, TR)
    return -np.mean(np.log(m[np.arange(len(TR)), hg[TR], ag[TR]]))


print("\n== prueba (40 % reciente) ==")
metricas("crudo (sin calibrar)", aplica(np.array([0, 1, 0, 1.0]), TE), TE)
xa = minimize(obj_1x2, [0, 1, 0, 1], method="Nelder-Mead", options={"maxiter": 4000}).x
print("  (a) params", np.round(xa, 4))
metricas("(a) producción: 1X2", aplica(xa, TE), TE)
xb = minimize(obj_marcador, [0, 1, 0, 1, -0.06], method="Nelder-Mead", options={"maxiter": 6000}).x
print("  (b) params", np.round(xb, 4))
metricas("(b) marcador exacto", aplica(xb, TE), TE)
xc = minimize(obj_marcador, list(xb) + [0.0], method="Nelder-Mead", options={"maxiter": 8000}).x
print("  (c) params", np.round(xc, 4))
metricas("(c) marcador + empates", aplica(xc, TE), TE)
# Solo nivel de goles (2 parámetros, pendiente 1)
xd = minimize(lambda x: obj_marcador(np.array([x[0], 1, x[1], 1])), [0, 0], method="Nelder-Mead").x
print("  (d) params", np.round(xd, 4))
metricas("(d) solo nivel de goles", aplica(np.array([xd[0], 1, xd[1], 1]), TE), TE)
