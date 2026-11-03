"""Estructura del marcador en el anclaje al mercado: DC (rho) frente a Poisson bivariado (lambda3 > 0).

Muestra aleatoria de 5.000 partidos de football-data con 1X2 y más/menos 2,5 de cierre de Pinnacle. Solo lectura.
"""
import glob
import io
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

sys.path.insert(0, "src")
from qf.model.devig import devig  # noqa: E402

G = 11
g = np.arange(G)
ii, jj = np.meshgrid(g, g, indexing="ij")
frames = []
for p in sorted(glob.glob(f"{sys.argv[1]}/*.csv")):
    raw = open(p, "rb").read().removeprefix(b"\xef\xbb\xbf")
    frames.append(pd.read_csv(io.BytesIO(raw), encoding="latin-1"))
df = pd.concat(frames, ignore_index=True).dropna(subset=["PSCH", "PSCD", "PSCA", "PC>2.5", "PC<2.5", "FTHG", "FTAG"])
df = df[(df[["PSCH", "PSCD", "PSCA", "PC>2.5", "PC<2.5"]] > 1).all(axis=1)].sample(5000, random_state=0).reset_index(drop=True)


def mat_dc(l1, l2, rho):
    m = np.outer(poisson.pmf(g, l1), poisson.pmf(g, l2))
    m[0, 0] *= 1 - l1 * l2 * rho; m[0, 1] *= 1 + l1 * rho; m[1, 0] *= 1 + l2 * rho; m[1, 1] *= 1 - rho
    m = np.clip(m, 1e-12, None)
    return m / m.sum()


def mat_bp(l1, l2, l3):
    # Poisson bivariado: X = A + C, Y = B + C, con C ~ Poisson(l3) común (covarianza l3 > 0)
    m = np.zeros((G, G))
    pa, pb, pc = poisson.pmf(g, l1), poisson.pmf(g, l2), poisson.pmf(g, l3)
    for k in range(G):
        m[k:, k:] += pc[k] * np.outer(pa[:G - k], pb[:G - k])
    m = np.clip(m, 1e-12, None)
    return m / m.sum()


def resumen(m):
    return np.array([np.tril(m, -1).sum(), np.trace(m), np.triu(m, 1).sum(), 1 - m[(ii + jj) <= 2].sum()])


variantes = {"DC rho=-0,06 (prod)": lambda a, b: mat_dc(a, b, -0.06), "DC rho=0": lambda a, b: mat_dc(a, b, 0.0),
             "bivariado l3=0,08": lambda a, b: mat_bp(a, b, 0.08), "bivariado l3=0,15": lambda a, b: mat_bp(a, b, 0.15),
             "bivariado l3=0,25": lambda a, b: mat_bp(a, b, 0.25)}
hg, ag = df.FTHG.astype(int).clip(0, G - 1).to_numpy(), df.FTAG.astype(int).clip(0, G - 1).to_numpy()
objetivos = []
for r in df.itertuples(index=False):
    p = devig([r.PSCH, r.PSCD, r.PSCA], "shin")
    q = devig([r[list(df.columns).index("PC>2.5")], r[list(df.columns).index("PC<2.5")]], "shin")[0]
    objetivos.append(np.array([p[0], p[1], p[2], q]))
print("partidos:", len(df))
print("variante | residuo mediano | marcador LL | ambos marcan p/y | local marca p/y | visita marca p/y | local por 2+ p/y | 0-0 p/y | 2-2 p/y")
for nombre, fm in variantes.items():
    res, M = [], []
    for t in objetivos:
        def coste(x):
            return float(np.sum((resumen(fm(np.exp(x[0]), np.exp(x[1]))) - t) ** 2))
        x0 = np.log([max(1.35 + (t[0] - t[2]), 0.3), max(1.35 - (t[0] - t[2]), 0.3)])
        x = minimize(coste, x0, method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-11}).x
        m = fm(np.exp(x[0]), np.exp(x[1]))
        res.append(np.max(np.abs(resumen(m) - t)))
        M.append(m)
    M = np.array(M)
    n = np.arange(len(M))
    ll = -np.mean(np.log(M[n, hg, ag]))
    btts = M[:, 1:, 1:].sum((1, 2)); h05 = 1 - M[:, 0, :].sum(1); a05 = 1 - M[:, :, 0].sum(1)
    hm2 = np.array([np.tril(m, -2).sum() for m in M])
    print(f"{nombre:20s} | {np.median(res):.4f} | {ll:.5f} | {btts.mean():.3f}/{((hg > 0) & (ag > 0)).mean():.3f} | "
          f"{h05.mean():.3f}/{(hg > 0).mean():.3f} | {a05.mean():.3f}/{(ag > 0).mean():.3f} | {hm2.mean():.3f}/{(hg - ag >= 2).mean():.3f} | "
          f"{M[:, 0, 0].mean():.4f}/{((hg == 0) & (ag == 0)).mean():.4f} | {M[:, 2, 2].mean():.4f}/{((hg == 2) & (ag == 2)).mean():.4f}", flush=True)
