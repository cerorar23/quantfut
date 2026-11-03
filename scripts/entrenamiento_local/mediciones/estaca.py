"""Motivación / «nada en juego» al final de temporada (Scarf y Shi; Buraimo y Forrest) medida contra el DC y contra el mercado.

    estaca.py <carpeta>

Para las ligas de liga regular a doble vuelta (Inglaterra, España, Italia, Alemania, Francia, Países Bajos, Portugal, Brasil) se arma
la tabla de posiciones solo con partidos anteriores y, desde el 60 % de la temporada, se marca por equipo si cada carrera sigue viva:
título (a ≤ 3·partidos restantes puntos del líder), puestos de Champions (4.º) y descenso (los tres últimos). `muerto` = ninguna viva.
Características: muerto local/visitante, carreras vivas de cada uno y fracción de temporada. Se evalúan con el mismo origen rodante
que apilado.py, sobre el DC y sobre el mercado. Es una aproximación a la «importancia» de la literatura, que exige simulación.
"""
import sys

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from qf.model.train import load_training_data
from _comun import delta

carpeta = sys.argv[1]
X = pd.read_pickle(f"{carpeta}/apilado_X.pkl")
LIGAS = ["gb.premier_league", "es.laliga", "it.serie_a", "de.bundesliga", "fr.ligue_1", "nl.eredivisie", "pt.primeira", "br.serie_a"]
df = load_training_data()
df = df[df.league_id.isin(LIGAS) & (df.league_id == df.home_league)].sort_values(["kickoff_utc", "match_id"])

filas = {}
for liga, g in df.groupby("league_id"):
    g = g.reset_index(drop=True)
    # temporada = tramo sin huecos de más de 60 días
    nueva = g.kickoff_utc.diff().dt.days.fillna(999) > 60
    for _, s in g.groupby(nueva.cumsum()):
        equipos = sorted(set(s.home_team_id) | set(s.away_team_id))
        n = len(equipos)
        total = 2 * (n - 1)
        pts = dict.fromkeys(equipos, 0)
        jug = dict.fromkeys(equipos, 0)
        for r in s.itertuples(index=False):
            tabla = sorted(pts.values(), reverse=True)
            f = {}
            for lado, t in (("local", r.home_team_id), ("visita", r.away_team_id)):
                rest = total - jug[t]
                avance = jug[t] / total
                vivo = [0, 0, 0]
                if avance >= 0.6 and n >= 8:
                    margen = 3 * rest
                    vivo[0] = int(tabla[0] - pts[t] <= margen)                      # título
                    vivo[1] = int(abs(pts[t] - tabla[3]) <= margen)                 # puestos de Champions
                    vivo[2] = int(abs(pts[t] - tabla[n - 4]) <= margen)             # descenso (tres últimos)
                f[f"vivas_{lado}"] = sum(vivo)
                f[f"muerto_{lado}"] = int(avance >= 0.6 and sum(vivo) == 0)
                f[f"avance_{lado}"] = avance
            filas[r.match_id] = f
            if r.home_goals == r.home_goals:
                h, a = r.home_team_id, r.away_team_id
                pts[h] += 3 if r.home_goals > r.away_goals else 1 if r.home_goals == r.away_goals else 0
                pts[a] += 3 if r.away_goals > r.home_goals else 1 if r.home_goals == r.away_goals else 0
                jug[h] += 1
                jug[a] += 1
E = pd.DataFrame.from_dict(filas, orient="index")
E.index.name = "match_id"
X = X.join(E, on="match_id")
X["liga_ok"] = X.league_id.isin(LIGAS)
for c in ("muerto_local", "muerto_visita", "vivas_local", "vivas_visita"):
    X[c] = X[c].where(X.liga_ok, 0.0).fillna(0.0)
X["muerto_dif"] = X.muerto_local - X.muerto_visita
X["vivas_dif"] = X.vivas_local - X.vivas_visita
print(f"partidos con tabla: {int(X.liga_ok.sum())}; con algún muerto: {int(((X.muerto_local + X.muerto_visita) > 0).sum())} "
      f"(local {int(X.muerto_local.sum())}, visita {int(X.muerto_visita.sum())})")
COLS = ["muerto_local", "muerto_visita", "vivas_dif"]
y = X.outcome.to_numpy(int)
P = X[["p_home", "p_draw", "p_away"]].to_numpy(float)
Mk = X[["mk_home", "mk_draw", "mk_away"]].to_numpy(float)


def lg(p):
    return np.column_stack([np.log(p[:, 0] / p[:, 1]), np.log(p[:, 2] / p[:, 1])])


def correr(base, extra, mask):
    Z = np.column_stack([lg(base)] + ([X[COLS].to_numpy(float)] if extra else []))
    p = np.full_like(base, np.nan)
    for k in (1, 2):
        tr, te = ((X["año"] < k) & mask).to_numpy(), ((X["año"] == k) & mask).to_numpy()
        m = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.05, max_iter=2000))
        m.fit(Z[tr], y[tr])
        p[te] = m.predict_proba(Z[te])
    return p


print("\nResultados en partidos de la fase final (≥ 60 % de la temporada) de las ligas con tabla:")
tarde = ((X.avance_local.fillna(0) >= 0.6) & X.liga_ok).to_numpy()
for nombre, d in (("muerto local", X.muerto_local > 0), ("muerto visita", X.muerto_visita > 0), ("ninguno muerto", (X.muerto_local + X.muerto_visita) == 0)):
    m = (d.to_numpy() & tarde)
    if m.sum():
        print(f"  {nombre:15s} n={m.sum():4d} local gana {np.mean(y[m] == 0):.3f} (DC {P[m, 0].mean():.3f}) empate {np.mean(y[m] == 1):.3f} (DC {P[m, 1].mean():.3f}) "
              f"visita gana {np.mean(y[m] == 2):.3f} (DC {P[m, 2].mean():.3f})")
print(f"\n{'configuración':34s}{'año 2: ΔRPS (p95)':>24s}{'año 3: ΔRPS (p95)':>24s}{'años 2-3: ΔRPS (p95)':>26s}")
todo = np.ones(len(X), bool)
for nombre, base, mask in (("sobre el DC (todas las filas)", P, todo),
                           ("sobre el mercado", Mk / Mk.sum(axis=1, keepdims=True), ~np.isnan(Mk).any(axis=1))):
    if np.isnan(base).any():
        base = np.where(np.isnan(base), 1 / 3, base)
    p0 = correr(base, False, mask)
    p1 = correr(base, True, mask)
    out = []
    for per in ((X["año"] == 1), (X["año"] == 2), (X["año"] >= 1)):
        m = (per.to_numpy() & mask)
        out.append(delta(p0[m], p1[m], y[m]))
    print(f"{'estaca ' + nombre:34s}" + "".join(f"{d:+14.5f} ({p95:+.5f})" for d, p95 in out))
