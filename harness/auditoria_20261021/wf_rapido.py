"""Walk-forward 2024-01 -> 2026-10 con DixonColesRapido para varias configuraciones (auditoría, solo lectura).

Uso: python wf_rapido.py nombre:hl:xb:ridge_crudo:activos[:maxiter] ...
  ridge_crudo = '-' para el ridge de producción.
"""
import os
import sys
import time
from datetime import timedelta

import numpy as np
import pandas as pd

sys.path.insert(0, "/tmp")
from dc_rapido import DixonColesRapido  # noqa: E402
from qf.config import settings  # noqa: E402
from qf.model.calibration import probs_1x2  # noqa: E402
from qf.model.devig import devig  # noqa: E402
from qf.model.train import load_training_data  # noqa: E402

CARPETA = "/srv/quantfut/artifacts/audit"
os.makedirs(CARPETA, exist_ok=True)
df = load_training_data()
df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
df = df.sort_values("kickoff_utc").reset_index(drop=True)
end = df["kickoff_utc"].max()
for spec in sys.argv[1:]:
    partes = spec.split(":")
    nombre, hl, xb, rc, act = partes[:5]
    maxiter = int(partes[5]) if len(partes) > 5 else 5000
    destino = f"{CARPETA}/wf_{nombre}.pkl"
    if os.path.exists(destino):
        print("ya existe", destino, flush=True)
        continue
    t0 = time.time()
    cutoff = pd.Timestamp("2024-01-01", tz="UTC")
    rows = []
    while cutoff < end:
        nxt = cutoff + timedelta(days=30)
        train = df[df["kickoff_utc"] < cutoff]
        test = df[(df["kickoff_utc"] >= cutoff) & (df["kickoff_utc"] < nxt)]
        if test.empty:
            cutoff = nxt
            continue
        m = DixonColesRapido(halflife_days=float(hl), xg_blend=float(xb),
                             ridge_crudo=None if rc == "-" else float(rc), suma_cero_activos=act == "1", maxiter=maxiter)
        m.fit(train, as_of=cutoff.to_pydatetime())
        lam, mu, effh, effa = [], [], [], []
        for r in test.itertuples(index=False):
            a, b = m.lambdas(r.home_team, r.away_team, r.league_id, r.home_league, r.away_league)
            lam.append(a); mu.append(b)
            effh.append(m.effective_n(r.home_team, r.home_league or r.league_id))
            effa.append(m.effective_n(r.away_team, r.away_league or r.league_id))
        P = probs_1x2(np.array(lam), np.array(mu), m.params.rho)
        for k, r in enumerate(test.itertuples(index=False)):
            if pd.notna(r.odds_home) and pd.notna(r.odds_draw) and pd.notna(r.odds_away):
                mk = devig([r.odds_home, r.odds_draw, r.odds_away], settings.devig_method)
            else:
                mk = [np.nan] * 3
            hg, ag = int(r.home_goals), int(r.away_goals)
            rows.append({"match_id": r.match_id, "kickoff_utc": r.kickoff_utc, "league_id": r.league_id,
                         "p_home": P[k, 0], "p_draw": P[k, 1], "p_away": P[k, 2], "lam": lam[k], "mu": mu[k],
                         "rho": m.params.rho, "home_eff": effh[k], "away_eff": effa[k],
                         "mk_home": mk[0], "mk_draw": mk[1], "mk_away": mk[2],
                         "outcome": 0 if hg > ag else 1 if hg == ag else 2, "home_goals": hg, "away_goals": ag,
                         "conv": bool(m.resultado.success)})
        cutoff = nxt
    pd.DataFrame(rows).to_pickle(destino)
    print(f"FIN {nombre}: {len(rows)} filas en {(time.time() - t0) / 60:.1f} min", flush=True)
