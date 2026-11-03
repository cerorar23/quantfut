"""Mide si usar xg_corregido en lugar del xG original cambia algo. Solo local; no toca producción ni modelos activos.

A) Calidad del dato: ¿cuál de los dos xG explica mejor los goles de esos 375 partidos? (Poisson, IC por bootstrap)
B) Sensibilidad del modelo: dos ajustes de DixonColes (parámetros de producción) y diferencia de predicciones en los
   partidos de los próximos 7 días.
C) Fuera de muestra: ajuste con datos hasta el 26-oct y evaluación en los partidos terminados desde el 27-oct.
"""
import sys, time, warnings
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from scipy.special import gammaln

warnings.filterwarnings("ignore")
sys.path.insert(0, "src")
D = sys.argv[1]
from qf.model.dixon_coles import DixonColes

df = pd.read_pickle(f"{D}/medicion_train.pkl")
fx = pd.read_pickle(f"{D}/medicion_fx.pkl")
xc = pd.read_pickle(f"{D}/medicion_xc.pkl")
df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)

# ---------- versiones del dataset
corr = df.copy()
m = xc.set_index("match_id")
idx = corr["match_id"].isin(m.index)
print(f"partidos del entrenamiento: {len(df)} | con xg_corregido dentro de él: {int(idx.sum())} de {len(xc)}")
corr.loc[idx, "home_xg"] = corr.loc[idx, "match_id"].map(m["home_xg"]).astype(float).values
corr.loc[idx, "away_xg"] = corr.loc[idx, "match_id"].map(m["away_xg"]).astype(float).values
corr.loc[idx, "xg_source"] = "fotmob"
corr.loc[idx, "xg_recorded_at"] = pd.to_datetime(corr.loc[idx, "match_id"].map(m["capturado_en"]), utc=True).values


def pois_ll(y, mu):
    mu = np.clip(mu, 0.05, None)
    return y * np.log(mu) - mu - gammaln(y + 1)


# ---------- A) calidad del dato
a = df[idx].copy()
b = corr[idx].copy()
y = np.concatenate([a["home_goals"].to_numpy(float), a["away_goals"].to_numpy(float)])
xo = np.concatenate([a["home_xg"].to_numpy(float), a["away_xg"].to_numpy(float)])
xn = np.concatenate([b["home_xg"].to_numpy(float), b["away_xg"].to_numpy(float)])
src = np.concatenate([a["xg_source"].to_numpy(), a["xg_source"].to_numpy()])
print("\nA) Calidad del dato (¿qué xG explica mejor los goles?). ll = log-verosimilitud de Poisson por equipo-partido")
rng = np.random.default_rng(7)


def comparar(mask, etiqueta):
    d = pois_ll(y[mask], xn[mask]) - pois_ll(y[mask], xo[mask])
    boots = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    rmse_o = np.sqrt(np.mean((y[mask] - xo[mask]) ** 2)); rmse_n = np.sqrt(np.mean((y[mask] - xn[mask]) ** 2))
    print(f"  {etiqueta:14s} n={mask.sum():4d} | ll medio original {pois_ll(y[mask], xo[mask]).mean():+.4f} corregido "
          f"{pois_ll(y[mask], xn[mask]).mean():+.4f} | mejora {d.mean():+.4f} IC95 [{lo:+.4f}, {hi:+.4f}] | RMSE {rmse_o:.3f} -> {rmse_n:.3f}")


comparar(np.ones(len(y), bool), "todos")
for s in ("sofascore", "api_football", "fotmob"):
    comparar(src == s, s)

# ---------- B) sensibilidad del modelo
print("\nB) Sensibilidad del modelo (ajuste final con todos los datos, parámetros de producción)")
t0 = time.time()
as_of = datetime.now(timezone.utc)
m0 = DixonColes(halflife_days=270.0, xg_blend=0.65).fit(df, as_of=as_of)
print(f"  ajuste original en {time.time()-t0:.0f} s")
t0 = time.time()
m1 = DixonColes(halflife_days=270.0, xg_blend=0.65).fit(corr, as_of=as_of)
print(f"  ajuste con xg_corregido en {time.time()-t0:.0f} s")
rows = []
for r in fx.itertuples():
    try:
        p0 = m0.predict(r.home_team, r.away_team, r.league_id, r.home_league, r.away_league)
        p1 = m1.predict(r.home_team, r.away_team, r.league_id, r.home_league, r.away_league)
    except Exception:
        continue
    if not (p0["_meta"]["both_teams_known"] and p1["_meta"]["both_teams_known"]):
        continue
    rows.append((r.league_id, p0["1x2"]["home"], p0["1x2"]["draw"], p0["1x2"]["away"], p1["1x2"]["home"], p1["1x2"]["draw"],
                 p1["1x2"]["away"], p0["totals"]["2.5"]["over"], p1["totals"]["2.5"]["over"],
                 p0["_meta"]["home_lambda"] + p0["_meta"]["away_lambda"], p1["_meta"]["home_lambda"] + p1["_meta"]["away_lambda"]))
R = pd.DataFrame(rows, columns=["liga", "h0", "d0", "a0", "h1", "d1", "a1", "o0", "o1", "t0", "t1"])
dp = np.abs(R[["h1", "d1", "a1"]].to_numpy() - R[["h0", "d0", "a0"]].to_numpy()).max(axis=1)
print(f"  partidos próximos comparables: {len(R)} de {len(fx)}")
print(f"  cambio máximo en P(1X2): media {dp.mean()*100:.2f} pp | p90 {np.percentile(dp,90)*100:.2f} pp | máximo {dp.max()*100:.2f} pp | "
      f"> 1 pp en {(dp>.01).sum()} | > 2 pp en {(dp>.02).sum()}")
do = np.abs(R["o1"] - R["o0"])
print(f"  cambio en P(más de 2,5): media {do.mean()*100:.2f} pp | máximo {do.max()*100:.2f} pp | goles esperados: "
      f"media {np.abs(R['t1']-R['t0']).mean():.3f} (máx {np.abs(R['t1']-R['t0']).max():.3f})")
print("  cambio medio de P(1X2) por liga (pp):", {k: round(float(v) * 100, 2) for k, v in
      pd.Series(dp, index=R["liga"]).groupby(level=0).mean().sort_values(ascending=False).head(5).items()})

# ---------- C) fuera de muestra
print("\nC) Fuera de muestra: ajuste con partidos hasta el 26-oct, evaluación en los terminados desde el 27-oct")
corte = pd.Timestamp("2026-10-27", tz="UTC")
tr0, te = df[df["kickoff_utc"] < corte], df[df["kickoff_utc"] >= corte].dropna(subset=["home_goals", "away_goals"])
tr1 = corr[corr["kickoff_utc"] < corte]
asof = corte.to_pydatetime()
c0 = DixonColes(halflife_days=270.0, xg_blend=0.65).fit(tr0, as_of=asof)
c1 = DixonColes(halflife_days=270.0, xg_blend=0.65).fit(tr1, as_of=asof)


def rps_ll(model, rows):
    rps, ll, n = [], [], 0
    for r in rows.itertuples():
        try:
            p = model.predict(r.home_team, r.away_team, r.league_id, r.home_league, r.away_league)
        except Exception:
            continue
        if not p["_meta"]["both_teams_known"]:
            continue
        pr = np.array([p["1x2"]["home"], p["1x2"]["draw"], p["1x2"]["away"]])
        o = np.array([1, 0, 0]) if r.home_goals > r.away_goals else np.array([0, 1, 0]) if r.home_goals == r.away_goals else np.array([0, 0, 1])
        rps.append(float(np.sum((np.cumsum(pr) - np.cumsum(o))[:2] ** 2) / 2)); ll.append(-np.log(max(pr[o.argmax()], 1e-9)))
    return np.array(rps), np.array(ll)


r0, l0 = rps_ll(c0, te)
r1, l1 = rps_ll(c1, te)
n = min(len(r0), len(r1))
d = r1[:n] - r0[:n]
boots = [d[rng.integers(0, n, n)].mean() for _ in range(4000)]
print(f"  partidos evaluados: {n}")
print(f"  RPS original {r0.mean():.5f} | con corregido {r1.mean():.5f} | diferencia {d.mean():+.5f} (negativa = mejor con corregido) "
      f"IC95 [{np.percentile(boots,2.5):+.5f}, {np.percentile(boots,97.5):+.5f}]")
print(f"  log-loss original {l0.mean():.5f} | con corregido {l1.mean():.5f}")
