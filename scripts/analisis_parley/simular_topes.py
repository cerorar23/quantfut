"""Simulación diaria del selector con topes por pata (DP exacta por partido).

Parte del análisis de topes de cuota del parley (2026-11-06). Informe y tablas:
docs/parley_topes_medicion_20261106.md. Investigación: no publica ni cambia
ningún motor. Las salidas van a QF_PARLEY_OUT (por defecto ./salida).
"""
from pathlib import Path
import math, sys, json, collections, random, os
import numpy as np, pandas as pd
from multiprocessing import Pool

S = os.environ.get("QF_PARLEY_OUT", str(Path(__file__).parent / "salida")) + "/"
TARGETS = [2.10, 3.10, 8.20, 12.10]
TOL, STEP, FLOOR, CAP_LO = 0.02, 0.004, 1.20, 1.80
BK = [1.2, 1.4, 1.6, 1.8, 2.1, 2.5, 3.0001]

POOLS = {
    "futbol": lambda c: c[c.sport == "futbol"],
    "tenis": lambda c: c[(c.sport == "tenis") & (c.date >= "2021-01-01")],
    "nba_partido": lambda c: c[(c.sport == "nba") & ~c.market.str.startswith("Props")],
    "nba_partido+props": lambda c: c[(c.sport == "nba") & (c.date >= "2024-10-22") & (c.date <= "2026-04-12")],
    "todos": lambda c: c[(c.date >= "2024-10-22") & (c.date <= "2025-05-25") & (c.sport.isin(["futbol", "tenis", "nba"]))],
}
import os
MAXDAYS = int(os.environ.get("MAXDAYS", 700))

def prune(z, cap):
    z = z[(z.price_best >= FLOOR) & (z.price_best <= cap)]
    if z.empty:
        return {}
    z = z.assign(b=np.digitize(z.price_best.values, BK))
    z = z.sort_values("p", ascending=False).groupby(["mid", "b"], sort=False).head(1)
    out = collections.defaultdict(list)
    for r in z.itertuples():
        out[r.mid].append((r.price_best, r.p, r.win, r.market + "|" + r.sel))
    return out

def best_ticket(cands, target, used):
    hi, lo = math.log(target * (1 + TOL)), math.log(target * (1 - TOL))
    states = {(0, 0): (0.0, (), 0.0)}
    for mid, opts in cands.items():
        if mid in used:
            continue
        new = dict(states)
        for (n, _), (lp, legs, lq) in states.items():
            if n >= 6:
                continue
            for (price, p, win, lab) in opts:
                q = lq + math.log(price)
                if q > hi:
                    continue
                key = (n + 1, int(q / STEP))
                val = lp + math.log(p)
                cur = new.get(key)
                if cur is None or val > cur[0]:
                    new[key] = (val, legs + ((mid, price, p, win),), q)
        states = new
    for n in range(2, 7):
        best = None
        for (nn, _), (lp, legs, lq) in states.items():
            if nn == n and lo <= lq <= hi and (best is None or lp > best[0]):
                best = (lp, legs, lq)
        if best:
            return best
    return None

def run_day(args):
    z, cap = args
    used, out = set(), []
    allc = prune(z, cap_all := max(cap, CAP_LO))
    for i, tg in enumerate(TARGETS):
        cp = CAP_LO if i < 2 else cap
        cands = {m: [o for o in v if o[0] <= cp] for m, v in allc.items()}
        cands = {m: v for m, v in cands.items() if v}
        if len(cands) < 2:
            out.append((tg, None)); continue
        r = best_ticket(cands, tg, used)
        if r is None:
            out.append((tg, None)); continue
        lp, legs, lq = r
        used.update(l[0] for l in legs)
        out.append((tg, (len(legs), math.exp(lq), math.exp(lp), all(l[3] for l in legs))))
    return out

def job(a):
    pool, cap = a
    C = pd.read_parquet(S + ("cands_b365.parquet" if pool == "futbol_b365" else "cands.parquet"))
    C = C if pool == "futbol_b365" else POOLS[pool](C)
    days = sorted(C.date.unique())
    random.Random(7).shuffle(days)
    days = sorted(days[:MAXDAYS])
    g = {k: v for k, v in C.groupby("date") if k in set(days)}
    res = collections.defaultdict(list)
    for d in days:
        for tg, t in run_day((g[d], cap)):
            res[tg].append(t)
    rows = []
    for tg in TARGETS:
        r = res[tg]; got = [x for x in r if x]
        if not got:
            rows.append(dict(pool=pool, cap=cap, target=tg, days=len(r), tickets=0)); continue
        n = np.array([x[0] for x in got]); q = np.array([x[1] for x in got])
        p = np.array([x[2] for x in got]); w = np.array([x[3] for x in got])
        rows.append(dict(pool=pool, cap=cap, target=tg, days=len(r), tickets=len(got), cov=len(got) / len(r),
                         legs=n.mean(), quote=q.mean(), p_fair=p.mean(), hit=w.mean(),
                         se=math.sqrt(max(w.mean() * (1 - w.mean()), 1e-9) / len(w)), margin_cost=(p * q).mean() - 1))
    return rows

if __name__ == "__main__":
    pools = sys.argv[1].split(",")
    caps = [float(c) for c in sys.argv[2].split(",")]
    tasks = [(p, c) for p in pools for c in caps]
    with Pool(min(len(tasks), 8)) as pl:
        allrows = sum(pl.map(job, tasks), [])
    pd.DataFrame(allrows).to_csv(S + f"sim_{sys.argv[3]}.csv", index=False)
    print("ok", len(allrows))
