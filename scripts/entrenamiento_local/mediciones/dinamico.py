"""Modelo dinámico: Kalman y mezclas de Dixon-Coles con varias medias vidas frente al Dixon-Coles de producción (media vida 270).

    dinamico.py <carpeta> [salida.json]

Lee <carpeta>/oos_hl*.pkl (walk-forward del DC, 3 años) y <carpeta>/kal_*.pkl (Kalman en una pasada, ver kalman_var.py), une por
partido y mide, con el MISMO protocolo: las combinaciones se eligen en los 2 primeros años (desarrollo) y se evalúan en el último
año (el de la puerta de producción), con remuestreo pareado de ΔRPS. Negativo = mejor que el DC 270.
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from _comun import cargar_oos, delta, logver_marcador, probs_de_lambdas, rps

carpeta = sys.argv[1]
oos = {os.path.basename(f)[4:-4]: cargar_oos(f) for f in sorted(glob.glob(f"{carpeta}/oos_hl*.pkl"))}
base = oos["hl270"]
kal = {os.path.basename(f)[4:-4]: pd.read_pickle(f).set_index("match_id") for f in sorted(glob.glob(f"{carpeta}/kal_*.pkl"))}
ids = set(base.match_id)
for o in oos.values():
    ids &= set(o.match_id)
for k in kal.values():
    ids &= set(k.index)
base = base[base.match_id.isin(ids)].reset_index(drop=True)
mid = base.match_id.to_numpy()
y, rho = base.outcome.to_numpy(int), base.rho.to_numpy(float)
hg, ag = base.home_goals.to_numpy(int), base.away_goals.to_numpy(int)
año = ((base.kickoff_utc - base.kickoff_utc.min()).dt.days // 365).clip(upper=2).to_numpy()
dev, test = año < 2, año == 2
print(f"partidos comunes {len(base)} (desarrollo {dev.sum()}, prueba {test.sum()})")

modelos = {"dc270": (base.lam.to_numpy(float), base.mu.to_numpy(float))}
for k, o in oos.items():
    if k != "hl270":
        o = o.set_index("match_id").loc[mid]
        modelos["dc" + k[2:]] = (o.lam.to_numpy(float), o.mu.to_numpy(float))
for k, d in kal.items():
    d = d.loc[mid]
    modelos[k] = (d.lam.to_numpy(float), d.mu.to_numpy(float))

P = {k: probs_de_lambdas(l, m, rho) for k, (l, m) in modelos.items()}
r_base = rps(P["dc270"], y)
mk = base[["mk_home", "mk_draw", "mk_away"]].to_numpy(float)
tiene_mk = ~np.isnan(mk).any(axis=1)
print(f"mercado en {tiene_mk.sum()} partidos: RPS DC270 {r_base[tiene_mk].mean():.5f} "
      f"mercado {rps(mk[tiene_mk], y[tiene_mk]).mean():.5f}")


def fila(nombre, p):
    r = rps(p, y)
    d3, p3 = delta(P["dc270"], p, y)
    dt, pt = delta(P["dc270"][test], p[test], y[test])
    return (f"{nombre:30s} RPS 3 años {r.mean():.5f} (Δ {d3:+.5f} p95 {p3:+.5f}) | desarrollo {r[dev].mean():.5f} "
            f"| prueba {r[test].mean():.5f} (Δ {dt:+.5f} p95 {pt:+.5f}) | mercado-set Δ vs mercado {r[tiene_mk].mean() - rps(mk[tiene_mk], y[tiene_mk]).mean():+.5f}")


print("\n== Modelos solos ==")
for k in modelos:
    print(fila(k, P[k]))

res = {}
print("\n== Mezcla log-lineal DC270 + Kalman (peso w del Kalman elegido en desarrollo) ==")
lam0, mu0 = modelos["dc270"]
for k in [k for k in modelos if k.startswith("k_")]:
    lk, mk_ = modelos[k]
    mejor = None
    for w in np.arange(0.0, 1.01, 0.1):
        l, m = np.exp((1 - w) * np.log(lam0) + w * np.log(lk)), np.exp((1 - w) * np.log(mu0) + w * np.log(mk_))
        r = rps(probs_de_lambdas(l, m, rho[dev]) if False else probs_de_lambdas(l[dev], m[dev], rho[dev]), y[dev]).mean()
        if mejor is None or r < mejor[0]:
            mejor = (r, w)
    w = mejor[1]
    l, m = np.exp((1 - w) * np.log(lam0) + w * np.log(lk)), np.exp((1 - w) * np.log(mu0) + w * np.log(mk_))
    p = probs_de_lambdas(l, m, rho)
    res[f"mezcla_dc270+{k}"] = {"w": round(float(w), 2)}
    print(fila(f"dc270+{k} w={w:.1f}", p))

print("\n== Mezcla de varias medias vidas del DC (pesos suma 1, elegidos por log-verosimilitud en desarrollo) ==")
claves = [k for k in modelos if k.startswith("dc")]
L = np.stack([np.log(modelos[k][0]) for k in claves]), np.stack([np.log(modelos[k][1]) for k in claves])


def mezcla(w, filas=slice(None)):
    w = np.append(w, 1 - np.sum(w))
    return np.exp(np.tensordot(w, L[0][:, filas], 1)), np.exp(np.tensordot(w, L[1][:, filas], 1))


f = lambda w: -logver_marcador(*mezcla(w, dev), rho[dev], hg[dev], ag[dev])  # noqa: E731
o = minimize(f, np.full(len(claves) - 1, 1 / len(claves)), method="Nelder-Mead")
w = np.append(o.x, 1 - o.x.sum())
print("pesos", dict(zip(claves, np.round(w, 3))))
res["dc_multivida"] = dict(zip(claves, [round(float(v), 4) for v in w]))
print(fila("dc multi-vida", probs_de_lambdas(*mezcla(o.x), rho)))

print("\n== DC multi-vida + mejor Kalman (todo elegido en desarrollo) ==")
for k in [k for k in modelos if k.startswith("k_")]:
    L2 = (np.vstack([L[0], np.log(modelos[k][0])]), np.vstack([L[1], np.log(modelos[k][1])]))
    nn = len(claves) + 1

    def mez2(w, filas=slice(None)):
        w = np.append(w, 1 - np.sum(w))
        return np.exp(np.tensordot(w, L2[0][:, filas], 1)), np.exp(np.tensordot(w, L2[1][:, filas], 1))

    o2 = minimize(lambda w: -logver_marcador(*mez2(w, dev), rho[dev], hg[dev], ag[dev]), np.full(nn - 1, 1 / nn), method="Nelder-Mead")
    w2 = np.append(o2.x, 1 - o2.x.sum())
    print(fila(f"multi-vida+{k}", probs_de_lambdas(*mez2(o2.x), rho)), "pesos", dict(zip(claves + [k], np.round(w2, 2))))
if len(sys.argv) > 2:
    json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
