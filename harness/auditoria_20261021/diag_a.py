"""Diagnósticos del Motor A sobre el walk-forward ampliado (solo lectura, auditoría 21-oct-2026)."""
import glob

import numpy as np
import pandas as pd
from scipy.stats import poisson

from qf.eval.metrics import rps
from qf.model.calibration import probs_1x2

rutas = sorted(glob.glob("/srv/quantfut/artifacts/ext/oos_*.pkl")) + ["/srv/quantfut/artifacts/oos_2026.10.19-131830.pkl"]
d = pd.concat([pd.read_pickle(r) for r in rutas]).drop_duplicates("match_id").sort_values("kickoff_utc").reset_index(drop=True)
P = d[["p_home", "p_draw", "p_away"]].to_numpy()
o = d["outcome"].to_numpy()
Y = np.eye(3)[o]
print("n", len(d), "desde", d.kickoff_utc.min(), "hasta", d.kickoff_utc.max())
mk = d[["mk_home", "mk_draw", "mk_away"]].to_numpy()
v = ~np.isnan(mk).any(axis=1)
print(f"RPS A {rps(P, o):.5f} | con mercado n={v.sum()} A {rps(P[v], o[v]):.5f} mercado {rps(mk[v], o[v]):.5f}")


def rel(nombre, p, y, bins=(0, .1, .2, .3, .4, .5, .6, .7, .8, 1)):
    print(f"-- fiabilidad {nombre}: tramo | n | predicho | real | z")
    idx = np.digitize(p, bins) - 1
    for b in range(len(bins) - 1):
        m = idx == b
        if m.sum() < 30:
            continue
        pp, yy = p[m].mean(), y[m].mean()
        z = (yy - pp) / np.sqrt(np.sum(p[m] * (1 - p[m]))) * m.sum()
        print(f"   {bins[b]:.1f}-{bins[b+1]:.1f} | {m.sum():5d} | {pp:.3f} | {yy:.3f} | {z:+.1f}")


print("\n== 1. Calibración por resultado (A) ==")
for j, n in enumerate(["local", "empate", "visita"]):
    print(f"{n}: media predicha {P[:, j].mean():.4f} real {Y[:, j].mean():.4f}")
    rel(n, P[:, j], Y[:, j])
print("\n== 1b. Mercado (mismas filas con cuota) ==")
for j, n in enumerate(["local", "empate", "visita"]):
    print(f"{n}: A {P[v, j].mean():.4f} mercado {mk[v, j].mean():.4f} real {Y[v, j].mean():.4f}")

print("\n== 2. Goles: media y dispersión ==")
lam, mu = d["lam"].to_numpy(), d["mu"].to_numpy()
hg, ag = d["home_goals"].to_numpy(), d["away_goals"].to_numpy()
print(f"local: λ medio {lam.mean():.3f} real {hg.mean():.3f} | visita: μ medio {mu.mean():.3f} real {ag.mean():.3f}")
# Pearson: var(y-λ)/λ ≈ 1 si Poisson con λ correcto
print(f"dispersión de Pearson local {np.mean((hg - lam) ** 2 / lam):.3f} visita {np.mean((ag - mu) ** 2 / mu):.3f}")
# Totales: P(over 2.5) predicho vs real, por tramos
from qf.model.pricing import score_matrix, market_totals
pov = np.array([market_totals(score_matrix(a, b, r), 2.5)["over"] for a, b, r in zip(lam, mu, d["rho"])])
yov = (hg + ag > 2.5).astype(float)
print(f"over 2.5: predicho {pov.mean():.4f} real {yov.mean():.4f}")
rel("over 2.5", pov, yov)
# Marcadores bajos: frecuencias predichas vs reales
for (i, j) in [(0, 0), (1, 1), (1, 0), (0, 1), (2, 2), (2, 1), (1, 2)]:
    pr = np.array([score_matrix(a, b, r)[i, j] for a, b, r in zip(lam, mu, d["rho"])])
    real = ((hg == i) & (ag == j)).mean()
    print(f"marcador {i}-{j}: predicho {pr.mean():.4f} real {real:.4f} z {(real - pr.mean()) / np.sqrt(np.sum(pr * (1 - pr))) * len(pr):+.1f}")
print("ρ por paso: min", d["rho"].min(), "max", d["rho"].max())

print("\n== 3. Exceso de confianza: ¿encoger hacia la media mejora? (pendiente de calibración logit) ==")
from scipy.optimize import minimize_scalar


def ll(p, y):
    return -np.mean(np.log(np.clip((p * y).sum(1), 1e-12, None)))


def temp(P, t):
    L = np.log(np.clip(P, 1e-12, None)) * t
    E = np.exp(L - L.max(1, keepdims=True))
    return E / E.sum(1, keepdims=True)


r = minimize_scalar(lambda t: ll(temp(P, t), Y), bounds=(0.5, 1.5), method="bounded")
print(f"temperatura óptima (todo) {r.x:.3f}; log-loss {ll(P, Y):.5f} -> {ll(temp(P, r.x), Y):.5f}; RPS {rps(P, o):.5f} -> {rps(temp(P, r.x), o):.5f}")
mitad = len(d) // 2
r1 = minimize_scalar(lambda t: ll(temp(P[:mitad], t), Y[:mitad]), bounds=(0.5, 1.5), method="bounded")
print(f"temperatura ajustada en 1ª mitad {r1.x:.3f} aplicada a 2ª: RPS {rps(P[mitad:], o[mitad:]):.5f} -> {rps(temp(P[mitad:], r1.x), o[mitad:]):.5f}")

print("\n== 4. Por muestra efectiva del equipo menos conocido (si existe la columna) ==")
if "home_eff" in d:
    e = np.minimum(d.home_eff, d.away_eff)
    for a, b in [(0, 5), (5, 10), (10, 20), (20, 1e9)]:
        m = (e >= a) & (e < b) & v
        if m.sum() > 30:
            print(f"   eff {a}-{b}: n={m.sum()} brecha {rps(P[m], o[m]) - rps(mk[m], o[m]):+.4f}")
else:
    print("   sin columna; se mide en el barrido")

print("\n== 5. Brecha por mes del año (inicio de temporada) ==")
mes = d.kickoff_utc.dt.month.to_numpy()
for mm in range(1, 13):
    m = (mes == mm) & v
    if m.sum() > 100:
        print(f"   mes {mm:2d}: n={m.sum():5d} A {rps(P[m], o[m]):.4f} mercado {rps(mk[m], o[m]):.4f} brecha {rps(P[m], o[m]) - rps(mk[m], o[m]):+.4f}")

print("\n== 6. Mezcla A+mercado (logit), peso por mitades ==")
from qf.eval.metrics import blend_logit
for w in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3):
    b = blend_logit(P[v], mk[v], w)
    print(f"   w={w:.2f} RPS {rps(b, o[v]):.5f}")

print("\n== 7. Ventaja de local por año (real vs predicha) ==")
yr = d.kickoff_utc.dt.year.to_numpy()
for y_ in sorted(set(yr)):
    m = yr == y_
    print(f"   {y_}: n={m.sum()} local real {Y[m,0].mean():.3f} pred {P[m,0].mean():.3f} | goles reales {(hg[m]+ag[m]).mean():.3f} pred {(lam[m]+mu[m]).mean():.3f}")
