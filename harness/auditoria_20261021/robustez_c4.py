import glob

import numpy as np
import pandas as pd

rutas = sorted(glob.glob("/srv/quantfut/artifacts/ext/oos_*.pkl")) + ["/srv/quantfut/artifacts/oos_2026.10.19-131830.pkl"]
prod = pd.concat([pd.read_pickle(r) for r in rutas]).drop_duplicates("match_id").set_index("match_id")
for nombre in ("c4", "c1"):
    c = pd.read_pickle(f"/srv/quantfut/artifacts/audit/wf_{nombre}.pkl").drop_duplicates("match_id").set_index("match_id")
    idx = prod.index.intersection(c.index)

    def rps(d):
        P = d.loc[idx, ["p_home", "p_draw", "p_away"]].to_numpy(float)
        o = d.loc[idx].outcome.to_numpy()
        return np.sum((np.cumsum(P, 1)[:, :2] - np.cumsum(np.eye(3)[o], 1)[:, :2]) ** 2, 1) / 2

    dr = pd.Series(rps(c) - rps(prod), index=idx)
    k = prod.loc[idx].kickoff_utc
    sem = k.dt.year.astype(str) + "-S" + ((k.dt.month > 6) + 1).astype(str)
    print(f"== {nombre}: ΔRPS por semestre (negativo = mejor)")
    print(dr.groupby(sem.values).agg(["size", "mean"]).round(5).to_string())
    print(f"== {nombre}: ΔRPS por liga")
    print(dr.groupby(prod.loc[idx].league_id.values).agg(["size", "mean"]).round(5).sort_values("mean").to_string())
