"""Motor A con el calibrador de producción aplicado + extremos (solo lectura)."""
import glob
import pickle

import numpy as np
import pandas as pd

from qf.config import settings
from qf.eval.metrics import rps
from qf.model.pricing import score_matrix, market_totals, market_1x2

rutas = sorted(glob.glob("/srv/quantfut/artifacts/ext/oos_*.pkl")) + ["/srv/quantfut/artifacts/oos_2026.10.19-131830.pkl"]
d = pd.concat([pd.read_pickle(r) for r in rutas]).drop_duplicates("match_id").sort_values("kickoff_utc").reset_index(drop=True)
print("modelo activo:", settings.model_path if hasattr(settings, "model_path") else "?")
cals = sorted(glob.glob(f"{settings.artifact_dir}/cal_*.pkl"))
print("calibradores:", [c.rsplit('/', 1)[-1] for c in cals][-4:])
import os
activo = None
for nombre in ("active_calibrator", "calibrator_path"):
    if hasattr(settings, nombre):
        activo = getattr(settings, nombre)
print("activo según settings:", activo)
from qf.model import calibration
with open(cals[-1], "rb") as f:
    c = pickle.load(f)
print("último cal:", c if isinstance(c, dict) else getattr(c, "__dict__", c))
cand = [x for x in cals if "2026.09.27" in x]
src = cand[0] if cand else cals[-1]
with open(src, "rb") as f:
    c = pickle.load(f)
cd = c if isinstance(c, dict) else c.__dict__
print("usado:", src, cd)
a0, a1, b0, b1 = (cd.get(k) for k in ("a0", "a1", "b0", "b1"))
lam = np.exp(a0 + a1 * np.log(d.lam.to_numpy()))
mu = np.exp(b0 + b1 * np.log(d.mu.to_numpy()))
hg, ag = d.home_goals.to_numpy(), d.away_goals.to_numpy()
o = d.outcome.to_numpy()
print(f"calibrado: λ {lam.mean():.3f} (real {hg.mean():.3f}) μ {mu.mean():.3f} (real {ag.mean():.3f})")
M = [score_matrix(a, b, r) for a, b, r in zip(lam, mu, d.rho)]
P = np.array([[market_1x2(m)[k] for k in ("home", "draw", "away")] for m in M])
P0 = d[["p_home", "p_draw", "p_away"]].to_numpy()
print(f"RPS crudo {rps(P0, o):.5f} calibrado {rps(P, o):.5f}")
pov = np.array([market_totals(m, 2.5)["over"] for m in M])
yov = (hg + ag > 2.5)
print(f"over 2.5 calibrado: predicho {pov.mean():.4f} real {yov.mean():.4f}")
bins = (0, .3, .4, .5, .6, .7, 1)
idx = np.digitize(pov, bins) - 1
for b in range(len(bins) - 1):
    m = idx == b
    if m.sum() > 30:
        print(f"   {bins[b]:.1f}-{bins[b+1]:.1f} n={m.sum()} pred {pov[m].mean():.3f} real {yov[m].mean():.3f}")
for (i, j) in [(0, 0), (1, 1), (2, 2), (0, 1), (1, 0)]:
    pr = np.array([m[i, j] for m in M])
    print(f"   {i}-{j}: pred {pr.mean():.4f} real {((hg == i) & (ag == j)).mean():.4f}")
print("\n== extremos: visitante >= 0.8 o local >= 0.85 ==")
x = d[(d.p_away >= 0.8) | (d.p_home >= 0.85)]
print(x.groupby("league_id").agg(n=("outcome", "size"), fav_gana=("outcome", lambda s: None)).n.to_string())
pa = x.p_away.where(x.p_away >= 0.8, x.p_home)
gana = np.where(x.p_away >= 0.8, x.outcome == 2, x.outcome == 0)
mkf = np.where(x.p_away >= 0.8, x.mk_away, x.mk_home)
print(f"n={len(x)} A promete {pa.mean():.3f} mercado {np.nanmean(mkf):.3f} real {gana.mean():.3f}")
print(x[["kickoff_utc", "league_id", "home_team", "away_team", "p_home", "p_away", "mk_home", "mk_away", "outcome"]].tail(12).to_string())
