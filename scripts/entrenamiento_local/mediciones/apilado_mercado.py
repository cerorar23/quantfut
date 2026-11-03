"""¿Algún factor añade información sobre el cierre de Pinnacle? Apilado anclado al mercado (origen rodante, sin fuga).

    apilado_mercado.py <carpeta>

Usa <carpeta>/apilado_X.pkl (lo escribe apilado.py). Base: logits del 1X2 des-margenado del mercado. Se añade (a) el logit del DC menos
el del mercado («el modelo») y (b) cada grupo de factores. Año 2: ajuste con el año 1; año 3: ajuste con los años 1-2.
ΔRPS frente al mercado puro (negativo = el factor añade información que el mercado no tenía).
"""
import sys

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from qf.model.features import FEATURE_GROUPS
from _comun import delta, rps

X = pd.read_pickle(f"{sys.argv[1]}/apilado_X.pkl")
X = X.dropna(subset=["mk_home", "mk_draw", "mk_away"]).reset_index(drop=True)
GRUPOS = dict(FEATURE_GROUPS)
GRUPOS["pi"] = ["pi_exp_gd", "pi_home_h", "pi_away_a"]
GRUPOS["xg_forma"] = [f"{k}_{n}" for n in (5, 10) for k in ("xg_for_diff", "xg_against_diff", "xg_net_diff", "fin_diff")]
GRUPOS["viaje"] = ["viaje_log_km", "viaje_este_h", "viaje_tz_h"]
M = X[["mk_home", "mk_draw", "mk_away"]].to_numpy(float)
M = M / M.sum(axis=1, keepdims=True)
P = X[["p_home", "p_draw", "p_away"]].to_numpy(float)
lm = np.column_stack([np.log(M[:, 0] / M[:, 1]), np.log(M[:, 2] / M[:, 1])])
ld = np.column_stack([np.log(P[:, 0] / P[:, 1]), np.log(P[:, 2] / P[:, 1])])
y = X.outcome.to_numpy(int)
print(f"{len(X)} partidos con mercado; RPS mercado {rps(M, y).mean():.5f}, DC {rps(P, y).mean():.5f}")


def modelo(c):
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=c, max_iter=2000))


def correr(extra, grupos, c):
    cols = [k for g in grupos for k in GRUPOS[g]]
    Z = np.column_stack([lm] + ([ld - lm] if extra else []) + ([X[cols].to_numpy(float)] if cols else []))
    p = np.full_like(M, np.nan)
    for k in (1, 2):
        tr, te = (X["año"] < k).to_numpy(), (X["año"] == k).to_numpy()
        m = modelo(c).fit(Z[tr], y[tr])
        p[te] = m.predict_proba(Z[te])
    return p


print(f"\n{'configuración':38s}{'año 2: ΔRPS (p95)':>24s}{'año 3: ΔRPS (p95)':>24s}{'años 2-3: ΔRPS (p95)':>26s}")
conf = [("solo recalibrar el mercado", False, []), ("mercado + modelo DC", True, [])]
conf += [(f"mercado + {g}", False, [g]) for g in GRUPOS]
conf += [("mercado + modelo + tiros", True, ["shots"]), ("mercado + todo", True, list(GRUPOS))]
for c in (0.05,):
    for nombre, extra, grupos in conf:
        p = correr(extra, grupos, c)
        out = []
        for m in ((X["año"] == 1), (X["año"] == 2), (X["año"] >= 1)):
            m = m.to_numpy()
            out.append(delta(M[m], p[m], y[m]))
        print(f"{nombre:38s}" + "".join(f"{d:+14.5f} ({p95:+.5f})" for d, p95 in out), flush=True)
