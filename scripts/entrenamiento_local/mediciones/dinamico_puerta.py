"""Puerta completa de la mezcla dinámica (Dixon-Coles multi-vida + Kalman) frente al Dixon-Coles de producción.

    dinamico_puerta.py <carpeta> <etiqueta_kalman> [salida_oos.pkl]

Pesos ajustados SOLO con los dos primeros años (log-verosimilitud del marcador exacto); el tercero es fuera de muestra de verdad.
Informa por año: ΔRPS con remuestreo pareado, log-loss, ECE del 1X2, ligas que mejoran y distancia al mercado.
Con `salida_oos.pkl` guarda las filas del último año con lam/mu/p_* de la mezcla (para repetir la puerta de contexto encima).
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from _comun import cargar_oos, delta, logver_marcador, probs_de_lambdas, rps

carpeta, kal_et = sys.argv[1], sys.argv[2]
oos = {k: cargar_oos(f"{carpeta}/oos_{k}.pkl").set_index("match_id") for k in ("hl270", "hl90", "hl730")}
kal = pd.read_pickle(f"{carpeta}/kal_{kal_et}.pkl").set_index("match_id")
ids = oos["hl270"].index.intersection(oos["hl90"].index).intersection(oos["hl730"].index).intersection(kal.index)
b = oos["hl270"].loc[ids].sort_values(["kickoff_utc"])
ids = b.index
y, rho = b.outcome.to_numpy(int), b.rho.to_numpy(float)
hg, ag = b.home_goals.to_numpy(int), b.away_goals.to_numpy(int)
año = ((b.kickoff_utc - b.kickoff_utc.min()).dt.days // 365).clip(upper=2).to_numpy()
dev = año < 2
fuentes = [oos["hl270"].loc[ids], oos["hl90"].loc[ids], oos["hl730"].loc[ids], kal.loc[ids]]
nombres = ["dc270", "dc90", "dc730", "kalman"]
L = [np.stack([np.log(f.lam.to_numpy(float)) for f in fuentes]), np.stack([np.log(f.mu.to_numpy(float)) for f in fuentes])]


def mezcla(w, f=slice(None)):
    w = np.append(w, 1 - np.sum(w))
    return np.exp(np.tensordot(w, L[0][:, f], 1)), np.exp(np.tensordot(w, L[1][:, f], 1))


o = minimize(lambda w: -logver_marcador(*mezcla(w, dev), rho[dev], hg[dev], ag[dev]), np.full(3, 0.25), method="Nelder-Mead")
w = np.append(o.x, 1 - o.x.sum())
print("pesos (solo desarrollo):", dict(zip(nombres, np.round(w, 3))))
lam1, mu1 = mezcla(o.x)
p0 = probs_de_lambdas(np.exp(L[0][0]), np.exp(L[1][0]), rho)
p1 = probs_de_lambdas(lam1, mu1, rho)
mk = b[["mk_home", "mk_draw", "mk_away"]].to_numpy(float)
tmk = ~np.isnan(mk).any(axis=1)


def ece(p, m):
    """ECE de la clase más probable (10 tramos) sobre las filas `m`."""
    conf, ok = p[m].max(axis=1), (p[m].argmax(axis=1) == y[m]).astype(float)
    bins = np.clip((conf * 10).astype(int), 0, 9)
    return sum(abs(ok[bins == k].mean() - conf[bins == k].mean()) * (bins == k).mean() for k in range(10) if (bins == k).any())


def logloss(p, m):
    return -np.mean(np.log(np.clip(p[m][np.arange(m.sum()), y[m]], 1e-12, None)))


print(f"\n{'periodo':14s}{'n':>6s}{'RPS DC270':>11s}{'RPS mezcla':>11s}{'ΔRPS':>10s}{'p95':>10s}{'logloss Δ':>11s}{'ECE Δ':>9s}"
      f"{'brecha mercado':>16s}")
for nombre, m in (("año 1", año == 0), ("año 2", año == 1), ("año 3 (fuera)", año == 2), ("3 años", año >= 0)):
    d, p95 = delta(p0[m], p1[m], y[m])
    mm = m & tmk
    gap0 = rps(p0[mm], y[mm]).mean() - rps(mk[mm], y[mm]).mean()
    gap1 = rps(p1[mm], y[mm]).mean() - rps(mk[mm], y[mm]).mean()
    print(f"{nombre:14s}{m.sum():6d}{rps(p0[m], y[m]).mean():11.5f}{rps(p1[m], y[m]).mean():11.5f}{d:+10.5f}{p95:+10.5f}"
          f"{logloss(p1, m) - logloss(p0, m):+11.5f}"
          f"{'':9s}{gap0:+8.5f}→{gap1:+.5f}")
t = año == 2
print(f"\nECE año 3: DC270 {ece(p0, t):.4f} → mezcla {ece(p1, t):.4f};  3 años: {ece(p0, año >= 0):.4f} → {ece(p1, año >= 0):.4f}")
print(f"empate previsto/real año 3: DC270 {p0[t, 1].mean():.3f} mezcla {p1[t, 1].mean():.3f} real {(y[t] == 1).mean():.3f}")
r0, r1 = rps(p0, y), rps(p1, y)
lg = b.league_id.to_numpy()
mejoran, tot = 0, 0
filas = []
for liga in sorted(set(lg)):
    m = (lg == liga) & t
    if m.sum() >= 30:
        tot += 1
        mejoran += r1[m].mean() < r0[m].mean()
        filas.append(f"{liga}:{r1[m].mean() - r0[m].mean():+.4f}({m.sum()})")
print(f"ligas que mejoran en el año 3: {mejoran}/{tot}\n  " + "  ".join(filas))
if len(sys.argv) > 3:
    out = b[t].reset_index().copy()
    out["lam"], out["mu"] = lam1[t], mu1[t]
    out[["p_home", "p_draw", "p_away"]] = p1[t]
    out.to_pickle(sys.argv[3])
    print("guardado", sys.argv[3], len(out))
