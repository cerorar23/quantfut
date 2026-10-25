"""Calibrador coherente: estira la supremacía s=(log λ - log μ)/2 por k, conserva m=(log λ + log μ)/2.

k se estima cada mes SOLO con partidos anteriores (log-verosimilitud del marcador exacto,
que identifica a la vez 1X2, goles y ambos marcan). Mide 1X2 (RPS/LL/Brier/ECE),
más/menos 2,5 y ambos marcan, con IC por bootstrap de días.
"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import poisson

D = sys.argv[1]
df = pd.read_pickle(f"{D}/wf_prodnuevo.pkl").sort_values("kickoff_utc").reset_index(drop=True)
df = df[df["outcome"].between(0, 2) & df["lam"].notna()].reset_index(drop=True)
G = 11
g = np.arange(G)


def matriz(lam, mu, rho):
    ph = poisson.pmf(g[None, :], lam[:, None])
    pa = poisson.pmf(g[None, :], mu[:, None])
    M = ph[:, :, None] * pa[:, None, :]
    M[:, 0, 0] *= 1 - lam * mu * rho
    M[:, 0, 1] *= 1 + lam * rho
    M[:, 1, 0] *= 1 + mu * rho
    M[:, 1, 1] *= 1 - rho
    return M / M.sum((1, 2), keepdims=True)


I, J = np.meshgrid(g, g, indexing="ij")


def mercados(M):
    p1 = (M * (I > J)).sum((1, 2)); px = (M * (I == J)).sum((1, 2)); p2 = (M * (I < J)).sum((1, 2))
    o25 = (M * ((I + J) > 2.5)).sum((1, 2)); btts = (M * ((I > 0) & (J > 0))).sum((1, 2))
    return np.c_[p1, px, p2], o25, btts


def ajusta(lam, mu, k):
    m, s = (np.log(lam) + np.log(mu)) / 2, (np.log(lam) - np.log(mu)) / 2
    return np.exp(m + k * s), np.exp(m - k * s)


def ll_marcador(sub, k):
    l, u = ajusta(sub["lam"].to_numpy(), sub["mu"].to_numpy(), k)
    M = matriz(l, u, sub["rho"].to_numpy())
    hg = np.minimum(sub["home_goals"].to_numpy(), G - 1); ag = np.minimum(sub["away_goals"].to_numpy(), G - 1)
    return np.log(np.clip(M[np.arange(len(sub)), hg, ag], 1e-12, 1)).mean()


mes = df["kickoff_utc"].dt.tz_convert(None).dt.to_period("M")
kk = np.full(len(df), np.nan)
hist = []
for m in mes.unique():
    te = (mes == m).to_numpy()
    tr = (df["kickoff_utc"] < df.loc[te, "kickoff_utc"].min()).to_numpy()
    if tr.sum() < 1500:
        continue
    sub = df[tr].iloc[-6000:]          # ventana reciente para que sea barato
    grid = np.linspace(0.9, 1.3, 41)
    k = grid[int(np.argmax([ll_marcador(sub, x) for x in grid]))]
    kk[te] = k
    hist.append((str(m), round(k, 3)))

v = ~np.isnan(kk)
d = df[v].reset_index(drop=True)
k = kk[v]
y = d["outcome"].to_numpy()
tot = (d["home_goals"] + d["away_goals"] > 2.5).to_numpy().astype(float)
bt = ((d["home_goals"] > 0) & (d["away_goals"] > 0)).to_numpy().astype(float)


def todo(lam, mu):
    p, o, b = mercados(matriz(lam, mu, d["rho"].to_numpy()))
    oh = np.eye(3)[y]
    rps = ((np.cumsum(p, 1)[:, :2] - np.cumsum(oh, 1)[:, :2]) ** 2).sum(1) / 2
    ll = -np.log(np.clip(p[np.arange(len(y)), y], 1e-12, 1))
    br = ((p - oh) ** 2).sum(1)
    llo = -(tot * np.log(o) + (1 - tot) * np.log(1 - o))
    llb = -(bt * np.log(b) + (1 - bt) * np.log(1 - b))
    return dict(rps=rps, ll=ll, brier=br, ll_o25=llo, ll_btts=llb, p=p)


base = todo(d["lam"].to_numpy(), d["mu"].to_numpy())
cal = todo(*ajusta(d["lam"].to_numpy(), d["mu"].to_numpy(), k))
dias = d["kickoff_utc"].dt.date.to_numpy()
rng = np.random.default_rng(3)
u = pd.unique(dias); pos = {x: i for i, x in enumerate(u)}; gi = np.array([pos[x] for x in dias])


def ci(diff):
    s = np.bincount(gi, diff); c = np.bincount(gi)
    r = [s[i].sum() / c[i].sum() for i in (rng.integers(0, len(u), len(u)) for _ in range(2000))]
    return np.percentile(r, [2.5, 97.5])


def ece(p):
    out = []
    for c in range(3):
        idx = np.minimum((p[:, c] * 10).astype(int), 9)
        out.append(sum(abs(p[idx == b, c].mean() - (y[idx == b] == c).mean()) * (idx == b).mean()
                       for b in range(10) if (idx == b).any()))
    return np.mean(out)


print("k por mes (últimos 6):", hist[-6:])
print(f"n evaluados: {v.sum()}  ({d['kickoff_utc'].min().date()} → {d['kickoff_utc'].max().date()})")
for key in ("rps", "ll", "brier", "ll_o25", "ll_btts"):
    diff = cal[key] - base[key]
    lo, hi = ci(diff)
    print(f"{key:8s} sin calibrar {base[key].mean():.5f}  calibrado {cal[key].mean():.5f}  Δ {diff.mean():+.5f}  IC95 [{lo:+.5f}, {hi:+.5f}]")
print(f"ECE 1X2  sin calibrar {ece(base['p']):.4f}  calibrado {ece(cal['p']):.4f}")
# Mitades temporales: estabilidad
mid = d["kickoff_utc"].quantile(0.5)
for nom, msk in (("1.ª mitad", (d["kickoff_utc"] < mid).to_numpy()), ("2.ª mitad", (d["kickoff_utc"] >= mid).to_numpy())):
    print(nom, " ".join(f"{key} Δ{(cal[key][msk]-base[key][msk]).mean():+.5f}" for key in ("rps", "ll", "ll_o25", "ll_btts")))
