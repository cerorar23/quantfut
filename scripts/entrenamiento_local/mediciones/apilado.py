"""Apilado sobre el Dixon-Coles con factores de la literatura (origen rodante, sin fuga).

    apilado.py <carpeta> [salida.json]

Entrada: <carpeta>/oos_hl270.pkl (walk-forward del DC, 3 años). Se calculan, solo con partidos ANTERIORES a cada uno:
  elo, descanso, forma, tiros (qf.model.features), pi-ratings (Constantinou y Fenton, 2013), forma de xG (a favor/en contra,
  Wheatcroft), distancia de viaje y desfase horario del visitante (Gilbert et al., 2020).
Modelos: regresión logística multinomial y árboles de gradiente (HistGradientBoosting) con los logits del DC como entrada, de modo
que `solo recalibrar` (sin factores) queda como referencia. Año 2: se ajusta con el año 1 y se prueba en el 2; año 3: se ajusta con
los años 1-2 y se prueba en el 3. Negativo = mejor que el DC 270 sin tocar.
"""
import json
import math
import sys
from collections import defaultdict, deque

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from qf.db import query
from qf.model.elo import sequential_elo
from qf.model.features import FEATURE_GROUPS, build_pit_features
from qf.model.train import load_training_data
from _comun import cargar_oos, delta

carpeta = sys.argv[1]
oos = cargar_oos(f"{carpeta}/oos_hl270.pkl")
df = load_training_data().sort_values(["kickoff_utc", "match_id"]).reset_index(drop=True)
print(f"OOS {len(oos)} filas; datos {len(df)} partidos", flush=True)

# ---------------------------------------------------------------- características PIT existentes
elo = sequential_elo(df)
pit = build_pit_features(df, elo).set_index("match_id")

# ---------------------------------------------------------------- pi-ratings, forma de xG y viaje
coords = pd.DataFrame(query("SELECT match_id, celda_lat AS lat, celda_lon AS lon FROM clima_era5_partido")).set_index("match_id")
df = df.join(coords, on="match_id")
casa = df.dropna(subset=["lat"]).groupby("home_team_id")[["lat", "lon"]].median()
C, LAM, GAM = 3.0, 0.06, 0.5


def psi_inv(r):
    return math.copysign(10 ** (abs(r) / C) - 1, r)


def haversine(la1, lo1, la2, lo2):
    p = math.pi / 180
    a = math.sin((la2 - la1) * p / 2) ** 2 + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(a))


ph, pa = defaultdict(float), defaultdict(float)             # pi-rating como local / como visitante
hist = defaultdict(lambda: deque(maxlen=12))                # (xG a favor, xG en contra, disponible desde, goles a favor)
filas = {}
for r in df.itertuples(index=False):
    h, a, ko = r.home_team_id, r.away_team_id, r.kickoff_utc
    f = {}
    f["pi_exp_gd"] = psi_inv(ph[h]) - psi_inv(pa[a])
    f["pi_home_h"], f["pi_away_a"] = ph[h], pa[a]
    for lado, t in (("home", h), ("away", a)):
        xs = [x for x in hist[t] if x[2] <= ko]
        for n in (5, 10):
            u = [x for x in xs[-n:] if x[0] == x[0]]
            f[f"{lado}_xgf_{n}"] = float(np.mean([x[0] for x in u])) if u else np.nan
            f[f"{lado}_xga_{n}"] = float(np.mean([x[1] for x in u])) if u else np.nan
            f[f"{lado}_gmx_{n}"] = float(np.mean([x[3] - x[0] for x in u])) if u else np.nan   # goles - xG a favor
    for n in (5, 10):
        f[f"xg_for_diff_{n}"] = f[f"home_xgf_{n}"] - f[f"away_xgf_{n}"]
        f[f"xg_against_diff_{n}"] = f[f"home_xga_{n}"] - f[f"away_xga_{n}"]
        f[f"xg_net_diff_{n}"] = (f[f"home_xgf_{n}"] - f[f"home_xga_{n}"]) - (f[f"away_xgf_{n}"] - f[f"away_xga_{n}"])
        f[f"fin_diff_{n}"] = f[f"home_gmx_{n}"] - f[f"away_gmx_{n}"]
    if a in casa.index and r.lat == r.lat:
        la, lo = casa.loc[a, "lat"], casa.loc[a, "lon"]
        f["viaje_log_km"] = math.log1p(haversine(la, lo, r.lat, r.lon))
        f["viaje_este_h"] = (r.lon - lo) / 15.0                 # >0: el visitante viajó hacia el este
        f["viaje_tz_h"] = abs(r.lon - lo) / 15.0
    filas[r.match_id] = f
    if r.home_goals == r.home_goals:
        gd = float(r.home_goals - r.away_goals)
        e = abs(gd - f["pi_exp_gd"])
        d = C * math.log10(1 + e) * LAM * (1 if gd > f["pi_exp_gd"] else -1)
        ph[h] += d
        pa[h] += GAM * d
        pa[a] -= d
        ph[a] -= GAM * d
        # xG de la fuente nueva: solo visible desde su recepción real; el histórico anterior, desde 3 h tras el partido
        propio = ko + pd.Timedelta(hours=3)
        recibido = r.xg_recorded_at if (r.xg_source is not None and r.xg_source == r.xg_source) else None
        disponible = propio if recibido is None or recibido != recibido else max(recibido, propio)
        hist[h].append((r.home_xg, r.away_xg, disponible, r.home_goals))
        hist[a].append((r.away_xg, r.home_xg, disponible, r.away_goals))
nuevas = pd.DataFrame.from_dict(filas, orient="index")
nuevas.index.name = "match_id"
X = oos.join(pit[[c for c in pit.columns if c not in oos.columns]], on="match_id").join(nuevas, on="match_id")
X["año"] = ((X.kickoff_utc - X.kickoff_utc.min()).dt.days // 365).clip(upper=2)
print("cobertura:", {c: round(float(X[c].notna().mean()), 3) for c in ("elo_diff", "home_shots_for_5", "xg_net_diff_10", "viaje_log_km", "pi_exp_gd")}, flush=True)

GRUPOS = dict(FEATURE_GROUPS)
GRUPOS["pi"] = ["pi_exp_gd", "pi_home_h", "pi_away_a"]
GRUPOS["xg_forma"] = [f"{k}_{n}" for n in (5, 10) for k in ("xg_for_diff", "xg_against_diff", "xg_net_diff", "fin_diff")]
GRUPOS["viaje"] = ["viaje_log_km", "viaje_este_h", "viaje_tz_h"]
P0 = X[["p_home", "p_draw", "p_away"]].to_numpy(float)
BASE = np.column_stack([np.log(P0[:, 0] / P0[:, 1]), np.log(P0[:, 2] / P0[:, 1])])
y = X.outcome.to_numpy(int)


def matriz(grupos):
    cols = [c for g in grupos for c in GRUPOS[g]]
    return (np.column_stack([BASE, X[cols].to_numpy(float)]) if cols else BASE), cols


def logistica(c):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=c, max_iter=2000))


def arboles():
    return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.04, max_iter=150, min_samples_leaf=60,
                                          l2_regularization=5.0, random_state=0)


def evaluar(grupos, tipo, c=0.05):
    M, _ = matriz(grupos)
    p = np.full_like(P0, np.nan)
    for k in (1, 2):
        tr, te = (X["año"] < k).to_numpy(), (X["año"] == k).to_numpy()
        m = logistica(c) if tipo == "logit" else arboles()
        m.fit(M[tr], y[tr])
        p[te] = m.predict_proba(M[te])
    return p


res = {}
print(f"\n{'configuración':34s}{'año 2: ΔRPS (p95)':>24s}{'año 3: ΔRPS (p95)':>24s}{'años 2-3: ΔRPS (p95)':>26s}")
configs = [("solo recalibrar", [])] + [(g, [g]) for g in GRUPOS] + [
    ("elo+forma+tiros (lo que hay hoy)", ["elo", "rest", "form", "shots"]),
    ("pi+xg_forma", ["pi", "xg_forma"]),
    ("todo", list(GRUPOS)),
    ("todo salvo viaje", [g for g in GRUPOS if g != "viaje"])]
for tipo, c in (("logit", 0.05), ("arboles", None)):
    print(f"-- {tipo}")
    for nombre, grupos in configs:
        if tipo == "arboles" and nombre not in ("solo recalibrar", "elo+forma+tiros (lo que hay hoy)", "pi+xg_forma", "todo"):
            continue
        p = evaluar(grupos, tipo, c if c else 0)
        out = []
        for m in ((X["año"] == 1), (X["año"] == 2), (X["año"] >= 1)):
            m = m.to_numpy()
            out.append(delta(P0[m], p[m], y[m]))
        res[f"{tipo}:{nombre}"] = {"a2": out[0], "a3": out[1], "a23": out[2]}
        print(f"{nombre:34s}" + "".join(f"{d:+14.5f} ({p95:+.5f})" for d, p95 in out), flush=True)
if len(sys.argv) > 2:
    json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
X.to_pickle(f"{carpeta}/apilado_X.pkl")
