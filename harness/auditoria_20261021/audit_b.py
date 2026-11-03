"""Auditoría Motor B con football-data (cierre Pinnacle): métodos de de-vig y mercados derivados del anclaje.

Solo lectura. Uso: python audit_b.py <carpeta_csv>
"""
import glob
import io
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from qf.model.devig import devig  # noqa: E402
from qf.model.market_anchor import market_lambdas  # noqa: E402
from qf.model.pricing import score_matrix  # noqa: E402

carpeta = sys.argv[1]
frames = []
for p in sorted(glob.glob(f"{carpeta}/*.csv")):
    raw = open(p, "rb").read().removeprefix(b"\xef\xbb\xbf")
    d = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    d["liga"] = p.replace("\\", "/").rsplit("/", 1)[-1].split("_")[0]
    d["temporada"] = p.rsplit("_", 1)[-1][:4]
    frames.append(d)
df = pd.concat(frames, ignore_index=True)
cols = ["PSCH", "PSCD", "PSCA", "FTHG", "FTAG"]
df = df.dropna(subset=cols)
df = df[(df[["PSCH", "PSCD", "PSCA"]] > 1).all(axis=1)].reset_index(drop=True)
o = np.where(df.FTHG > df.FTAG, 0, np.where(df.FTHG == df.FTAG, 1, 2))
Y = np.eye(3)[o]
print("partidos con cierre Pinnacle 1X2:", len(df))


def rps(P, o):
    c = np.cumsum(P, 1)[:, :2]
    co = np.cumsum(np.eye(3)[o], 1)[:, :2]
    return np.mean(np.sum((c - co) ** 2, 1) / 2)


def ll(P, Y):
    return -np.mean(np.log(np.clip((P * Y).sum(1), 1e-12, None)))


print("\n== 1. De-vig 1X2 (cierre Pinnacle) ==")
odds = df[["PSCH", "PSCD", "PSCA"]].to_numpy(float)
res = {}
for met in ("multiplicative", "additive", "power", "shin"):
    P = np.array([devig(r, met) for r in odds])
    P = np.clip(P, 1e-6, 1)
    P /= P.sum(1, keepdims=True)
    res[met] = P
    print(f"  {met:15s} RPS {rps(P, o):.5f}  log-loss {ll(P, Y):.5f}")
# Sesgo favorito-sorpresa: por tramos de probabilidad (todas las selecciones), shin vs multiplicativo
print("  calibración por tramo (todas las selecciones): tramo | n | real | mult | shin | power")
pm, ps, pp = res["multiplicative"].ravel(), res["shin"].ravel(), res["power"].ravel()
y = Y.ravel()
for a, b in [(0, .1), (.1, .2), (.2, .35), (.35, .5), (.5, .65), (.65, .8), (.8, 1)]:
    m = (ps >= a) & (ps < b)
    print(f"   {a:.2f}-{b:.2f} | {m.sum():5d} | {y[m].mean():.4f} | {pm[m].mean():.4f} | {ps[m].mean():.4f} | {pp[m].mean():.4f}")

print("\n== 2. Mercados derivados del anclaje (1X2 shin + más/menos 2,5 cierre) ==")
t = df.dropna(subset=["PC>2.5", "PC<2.5"]).reset_index(drop=True)
t = t[(t["PC>2.5"] > 1) & (t["PC<2.5"] > 1)].reset_index(drop=True)
print("partidos con 1X2 y totales:", len(t))
rows = []
for r in t.itertuples(index=False):
    p = devig([r.PSCH, r.PSCD, r.PSCA], "shin")
    q = devig([getattr(r, "_" + str(list(t.columns).index("PC>2.5"))) if False else r[list(t.columns).index("PC>2.5")],
               r[list(t.columns).index("PC<2.5")]], "shin")
    try:
        fit = market_lambdas(p[0], p[1], p[2], rho=-0.06, totals={2.5: q[0]})
    except ValueError:
        continue
    m = score_matrix(fit.lam, fit.mu, -0.06)
    hg, ag = int(r.FTHG), int(r.FTAG)
    rows.append({
        "res": fit.residual, "lam": fit.lam, "mu": fit.mu,
        "btts": 1 - m[0, :].sum() - m[:, 0].sum() + m[0, 0], "y_btts": (hg > 0) & (ag > 0),
        "h05": 1 - m[0, :].sum(), "y_h05": hg > 0,
        "a05": 1 - m[:, 0].sum(), "y_a05": ag > 0,
        "h15": 1 - m[:2, :].sum(), "y_h15": hg > 1,
        "a15": 1 - m[:, :2].sum(), "y_a15": ag > 1,
        "o15": 1 - sum(m[i, j] for i in range(2) for j in range(2) if i + j <= 1), "y_o15": hg + ag > 1,
        "o35": 1 - sum(m[i, j] for i in range(4) for j in range(4) if i + j <= 3), "y_o35": hg + ag > 3,
        "hm2": float(np.tril(m, -2).sum()), "y_hm2": hg - ag >= 2,
        "am2": float(np.triu(m, 2).sum()), "y_am2": ag - hg >= 2,
        "s00": m[0, 0], "y_s00": hg == 0 and ag == 0,
        "s11": m[1, 1], "y_s11": hg == 1 and ag == 1,
        "s22": m[2, 2], "y_s22": hg == 2 and ag == 2,
        "dr": float(np.trace(m)), "y_dr": hg == ag,
        "dmk": p[1],
    })
R = pd.DataFrame(rows)
print("ajustes:", len(R), "| residuo > 0,002:", int((R.res > 0.002).sum()), "| mediana residuo", round(R.res.median(), 5))
print("  mercado | predicho | real | z | log-loss")
for k in ("btts", "h05", "a05", "h15", "a15", "o15", "o35", "hm2", "am2", "s00", "s11", "s22", "dr"):
    pr, yy = R[k].to_numpy(float), R["y_" + k].to_numpy(float)
    z = (yy.sum() - pr.sum()) / np.sqrt(np.sum(pr * (1 - pr)))
    lo = -np.mean(yy * np.log(np.clip(pr, 1e-9, 1)) + (1 - yy) * np.log(np.clip(1 - pr, 1e-9, 1)))
    print(f"  {k:5s} | {pr.mean():.4f} | {yy.mean():.4f} | {z:+.1f} | {lo:.5f}")
print("  empate del ajuste vs empate de mercado:", round(R.dr.mean(), 4), round(R.dmk.mean(), 4))
for k, bins in (("btts", (0, .4, .5, .6, 1)), ("o35", (0, .2, .3, .4, 1)), ("h05", (0, .6, .7, .8, .9, 1)), ("a05", (0, .5, .6, .7, .8, 1))):
    print(f"  fiabilidad {k}:", end=" ")
    for a, b in zip(bins[:-1], bins[1:]):
        m = (R[k] >= a) & (R[k] < b)
        if m.sum() > 50:
            print(f"[{a:.1f}-{b:.1f} n={m.sum()} p={R[k][m].mean():.3f} y={R['y_' + k][m].mean():.3f}]", end=" ")
    print()
R.to_pickle(r"C:\Users\huye\AppData\Local\Temp\claude\C--Users-huye-Documents-apuesta-proyec\fea02813-85a0-4812-9a5c-7903861b7b3c\scratchpad\audit_b.pkl")
