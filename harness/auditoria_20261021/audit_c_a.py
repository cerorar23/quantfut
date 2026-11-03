"""Motor C con el contexto del MOTOR A (sin cuotas): ¿se mantiene la mejora en córners por equipo y tarjetas?

Lambdas del A punto en el tiempo: walk-forward nuevo (/srv/quantfut/artifacts/audit/wf_prodnuevo.pkl).
Base: Acumulador de producción alimentado en orden con los partidos de la base (como escalera_datos).
Ajuste de los coeficientes en el 60 % antiguo, prueba en el 40 % reciente. Solo lectura.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import nbinom, poisson

from qf.db import query
from qf.model import estadisticas_mercado as em

oos = pd.read_pickle("/srv/quantfut/artifacts/audit/wf_prodnuevo.pkl").drop_duplicates("match_id").set_index("match_id")
rows = query("""SELECT match_id, kickoff_utc, league_id, home_team_id, away_team_id, referee,
                       home_corners, away_corners, home_yellow, away_yellow, home_red, away_red
                FROM matches WHERE status='finished' AND kickoff_utc > now() - interval '9 years'
                ORDER BY kickoff_utc""")
df = pd.DataFrame(rows)
print("partidos en la base:", len(df))
acs, out = {}, []
for r in df.itertuples(index=False):
    t = r.kickoff_utc.to_pydatetime()
    for est in ("corners", "cards"):
        acs.setdefault((r.league_id, est), em.acumulador(est))
    ac, at = acs[(r.league_id, "corners")], acs[(r.league_id, "cards")]
    hay_c = pd.notna(r.home_corners) and pd.notna(r.away_corners)
    hay_t = pd.notna(r.home_yellow) and pd.notna(r.away_yellow)
    if r.match_id in oos.index:
        o = oos.loc[r.match_id]
        lc = ac.lambdas(t, r.home_team_id, r.away_team_id) if hay_c else None
        lt = at.lambdas(t, r.home_team_id, r.away_team_id, r.referee if isinstance(r.referee, str) else None) if hay_t else None
        out.append({"t": t, "lam": o.lam, "mu": o.mu, "ph": o.p_home, "pd": o.p_draw, "pa": o.p_away,
                    "ch": lc[0] if lc else np.nan, "ca": lc[1] if lc else np.nan,
                    "th": lt[0] if lt else np.nan, "ta": lt[1] if lt else np.nan,
                    "HC": r.home_corners, "AC": r.away_corners,
                    "T": r.home_yellow + r.away_yellow + np.nan_to_num(r.home_red) + np.nan_to_num(r.away_red) if hay_t else np.nan})
    if hay_c:
        ac.agregar(t, r.home_team_id, r.away_team_id, int(r.home_corners), int(r.away_corners))
    if hay_t:
        at.agregar(t, r.home_team_id, r.away_team_id, int(r.home_yellow + np.nan_to_num(r.home_red)),
                   int(r.away_yellow + np.nan_to_num(r.away_red)), r.referee if isinstance(r.referee, str) else None)
R = pd.DataFrame(out).sort_values("t").reset_index(drop=True)
R["sup"] = np.log(R.lam / R.mu)          # supremacía del A en escala log
R["absp"] = (R.ph - R.pa).abs()


def nb_lp(k, m, phi):
    if phi <= 1.0001:
        return poisson.logpmf(k, m)
    r = m / (phi - 1)
    return nbinom.logpmf(k, r, r / (r + m))


def ajusta(X, y):
    f = lambda b: -np.sum(y * (X @ b) - np.exp(X @ b))  # noqa: E731
    return minimize(f, np.zeros(X.shape[1]), method="BFGS").x


def phi_mom(y, m):
    return max(float(np.sum((y - m) ** 2) / np.sum(m)), 1.0)


for nombre, col, base, signo, phi0 in (("córners local", "HC", "ch", 1, em.PARAMETROS["corners_equipo"]["phi"]),
                                         ("córners visitante", "AC", "ca", -1, em.PARAMETROS["corners_equipo"]["phi"])):
    d = R.dropna(subset=[col, base]).reset_index(drop=True)
    c = int(len(d) * 0.6)
    tr, te = d.iloc[:c], d.iloc[c:]
    X = lambda x: np.column_stack([np.ones(len(x)), np.log(x[base]), signo * x.sup, np.log(x.lam + x.mu)])  # noqa: E731
    b = ajusta(X(tr), tr[col].to_numpy(float))
    m1 = np.exp(X(te) @ b)
    ph = phi_mom(tr[col].to_numpy(float), np.exp(X(tr) @ b))
    lp0 = np.mean(nb_lp(te[col].to_numpy(), te[base].to_numpy(), phi0))
    lp1 = np.mean(nb_lp(te[col].to_numpy(), m1, ph))
    print(f"{nombre}: n prueba {len(te)} | producción {lp0:.5f} | con contexto del A {lp1:.5f} (Δ {lp1 - lp0:+.5f}) | coef {np.round(b, 3)}")

d = R.dropna(subset=["T", "th"]).reset_index(drop=True)
c = int(len(d) * 0.6)
tr, te = d.iloc[:c], d.iloc[c:]
X = lambda x: np.column_stack([np.ones(len(x)), np.log(x.th + x.ta), x.absp, x.pd])  # noqa: E731
b = ajusta(X(tr), tr["T"].to_numpy(float))
m0 = (te.th + te.ta).to_numpy()
m1 = np.exp(X(te) @ b)
ph = phi_mom(tr["T"].to_numpy(float), np.exp(X(tr) @ b))
lp0 = np.mean(nb_lp(te["T"].to_numpy(), m0, em.PARAMETROS["cards"]["phi"]))
lp1 = np.mean(nb_lp(te["T"].to_numpy(), m1, ph))
print(f"tarjetas: n prueba {len(te)} | producción {lp0:.5f} | con contexto del A {lp1:.5f} (Δ {lp1 - lp0:+.5f}) | coef {np.round(b, 3)}")
for lado, ln in em.LINEAS_HABILITADAS["cards"]:
    p0 = np.array([em.prob_total(m, em.PARAMETROS["cards"]["phi"], ln)[lado] for m in m0])
    p1 = np.array([em.prob_total(m, ph, ln)[lado] for m in m1])
    y = (te["T"] < ln) if lado == "under" else (te["T"] > ln)
    print(f"   {lado} {ln}: real {y.mean():.3f} | prod p {p0.mean():.3f} Brier {np.mean((p0 - y) ** 2):.4f} | nuevo p {p1.mean():.3f} Brier {np.mean((p1 - y) ** 2):.4f}")
