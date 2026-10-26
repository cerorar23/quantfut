"""Ratings dinámicos (Kalman, `qf.model.kalman`) en una pasada, SIN fuga de parámetros de liga, para varias configuraciones.

    kalman_var.py <carpeta> <etiqueta> process_var=2.5e-4 mean_rev=1e-3 init_var=0.25 xg_blend=0.65 [ini_atk=0 ini_def=0]

`DynamicRatings.predict_sequential` estima el nivel de goles y la ventaja de local con TODO el histórico (también el futuro del
partido que predice). Aquí se reestiman cada 30 días solo con los partidos anteriores al corte, como hace el walk-forward del
Dixon-Coles. Guarda <carpeta>/kal_<etiqueta>.pkl con match_id, lam y mu de los partidos de la ventana de 3 años.
"""
import sys
from datetime import timedelta

import numpy as np
import pandas as pd

from qf.model.kalman import DynamicRatings, KalmanConfig, TeamState
from qf.model.train import load_training_data

carpeta, etiqueta = sys.argv[1], sys.argv[2]
kw = dict(a.split("=") for a in sys.argv[3:])
ini = (float(kw.pop("ini_atk", 0.0)), float(kw.pop("ini_def", 0.0)))
cfg = KalmanConfig(process_var_per_day=float(kw.get("process_var", 2.5e-4)),
                   mean_reversion_per_day=float(kw.get("mean_rev", 1e-3)),
                   init_var=float(kw.get("init_var", 0.25)), xg_blend=float(kw.get("xg_blend", 0.65)))
df = load_training_data().dropna(subset=["home_goals", "away_goals"]).sort_values(["kickoff_utc", "match_id"]).reset_index(drop=True)
inicio = df["kickoff_utc"].max() - timedelta(days=1095)
m = DynamicRatings(cfg)
cortes = pd.date_range(inicio, df["kickoff_utc"].max() + timedelta(days=30), freq="30D", tz="UTC")
filas, k = [], 0
est_ant = None
for r in df.itertuples(index=False):
    ko = r.kickoff_utc
    ventana = ko >= inicio
    if ko < cortes[0]:
        if not m.leagues:                      # arranque: parámetros con el histórico previo al primer corte
            m._estimate_league_params(df[df["kickoff_utc"] < cortes[0]])
    else:
        while k + 1 < len(cortes) and ko >= cortes[k + 1]:
            k += 1
        if est_ant != k:                       # nuevo corte: parámetros de liga solo con lo anterior
            m._estimate_league_params(df[df["kickoff_utc"] < cortes[k]])
            est_ant = k
    lg_h = r.home_league if r.home_league is not None else r.league_id
    lg_a = r.away_league if r.away_league is not None else r.league_id
    h, a = m._state(lg_h, r.home_team), m._state(lg_a, r.away_team)
    for st in (h, a):
        if st.n_matches == 0 and st.last_seen is None and (ini[0] or ini[1]):
            st.attack, st.defence = ini
    if ventana:
        lam, mu = m.lambdas(r.home_team, r.away_team, r.league_id, lg_h, lg_a)
        filas.append((r.match_id, lam, mu, h.n_matches, a.n_matches, h.var_attack, a.var_attack))
    obs = r.xg_source is not None and r.xg_source == r.xg_source
    hx, ax = (None, None) if obs else (r.home_xg, r.away_xg)
    m.update_match(r.home_team, r.away_team, r.league_id, r.home_goals, r.away_goals, ko, hx, ax, lg_h, lg_a)
out = pd.DataFrame(filas, columns=["match_id", "lam", "mu", "n_h", "n_a", "var_h", "var_a"])
out.to_pickle(f"{carpeta}/kal_{etiqueta}.pkl")
print(etiqueta, cfg, ini, len(out), flush=True)
