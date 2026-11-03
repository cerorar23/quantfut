"""Compara las configuraciones del barrido con el walk-forward de producción en los mismos partidos (bootstrap pareado)."""
import glob
import sys

import numpy as np
import pandas as pd

rutas = sorted(glob.glob("/srv/quantfut/artifacts/ext/oos_*.pkl")) + ["/srv/quantfut/artifacts/oos_2026.10.19-131830.pkl"]
prod = pd.concat([pd.read_pickle(r) for r in rutas]).drop_duplicates("match_id").set_index("match_id")
confs = {p.rsplit("wf_", 1)[1][:-4]: pd.read_pickle(p).drop_duplicates("match_id").set_index("match_id")
         for p in sorted(glob.glob("/srv/quantfut/artifacts/audit/wf_*.pkl"))}
comunes = prod.index
for c in confs.values():
    comunes = comunes.intersection(c.index)
print("partidos comunes:", len(comunes))


def por_partido(d):
    d = d.loc[comunes]
    P = d[["p_home", "p_draw", "p_away"]].to_numpy(float)
    o = d.outcome.to_numpy()
    c = np.cumsum(P, 1)[:, :2]
    co = np.cumsum(np.eye(3)[o], 1)[:, :2]
    rps = np.sum((c - co) ** 2, 1) / 2
    ll = -np.log(np.clip(P[np.arange(len(o)), o], 1e-12, None))
    return rps, ll, P


rp, lp, Pp = por_partido(prod)
mk = prod.loc[comunes, ["mk_home", "mk_draw", "mk_away"]].to_numpy(float)
v = ~np.isnan(mk).any(1)
o = prod.loc[comunes].outcome.to_numpy()
cm = np.cumsum(mk, 1)[:, :2]
co = np.cumsum(np.eye(3)[o], 1)[:, :2]
rm = np.sum((cm - co) ** 2, 1) / 2
rng = np.random.default_rng(0)
B = rng.integers(0, len(comunes), (2000, len(comunes)))
print(f"producción: RPS {rp.mean():.5f} LL {lp.mean():.5f} | con mercado n={v.sum()} brecha {rp[v].mean() - rm[v].mean():+.5f}")
ext = (Pp.max(1) > 0.85)
print(f"producción: predicciones > 0,85: {ext.sum()}")
print("config | RPS | ΔRPS vs prod [IC95] | ΔLL vs prod | brecha mercado | máx prob > 0,85 (n, acierto prom., real) | conv")
for k, d in confs.items():
    r, l, P = por_partido(d)
    dr = r - rp
    bs = dr[B].mean(1)
    e = P.max(1) > 0.85
    idx = P.argmax(1)
    real = (idx[e] == o[e]).mean() if e.any() else float("nan")
    conv = d.loc[comunes, "conv"].mean()
    print(f"{k:6s} | {r.mean():.5f} | {dr.mean():+.5f} [{np.percentile(bs, 2.5):+.5f}, {np.percentile(bs, 97.5):+.5f}] | "
          f"{(l - lp).mean():+.5f} | {r[v].mean() - rm[v].mean():+.5f} | {e.sum()}, {P.max(1)[e].mean() if e.any() else 0:.3f}, {real:.3f} | {conv:.2f}")
# Equipos poco conocidos
for k in ("r1", "r3"):
    if k in confs:
        d = confs[k].loc[comunes]
        poco = np.minimum(d.home_eff, d.away_eff).to_numpy() < 5
        r, _, _ = por_partido(confs[k])
        print(f"{k}: partidos con algún equipo eff<5: n={poco.sum()} RPS prod {rp[poco].mean():.5f} -> {r[poco].mean():.5f} | mercado {np.nanmean(np.where(v, rm, np.nan)[poco]):.5f}")
