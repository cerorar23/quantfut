"""Córners por equipo repartidos por la supremacía del Motor A: ajuste de gamma y prueba de líneas.

m_local = T·e^{γs}·b_l / (e^{γs}·b_l + e^{-γs}·b_v), m_visit = T − m_local, con T = b_l + b_v (el total del C no cambia)
y s = log(λ/μ) del Motor A (walk-forward nuevo, punto en el tiempo). γ se ajusta en el 60 % antiguo; la prueba de
líneas (criterio de eval/alta_prob_calibracion: cada tramo con n >= 100 real >= prometido − 2·SE y déficit total
>= −1 punto) se hace en el 40 % reciente, igual para el modelo actual (γ = 0) y el nuevo. Solo lectura.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import nbinom

from qf.db import query
from qf.model import estadisticas_mercado as em

oos = pd.read_pickle("/srv/quantfut/artifacts/audit/wf_prodnuevo.pkl").drop_duplicates("match_id").set_index("match_id")
df = pd.DataFrame(query("""SELECT match_id, kickoff_utc, league_id, home_team_id, away_team_id, home_corners, away_corners
                           FROM matches WHERE status='finished' AND kickoff_utc > now() - interval '9 years'
                           ORDER BY kickoff_utc"""))
acs, out = {}, []
for r in df.itertuples(index=False):
    if pd.isna(r.home_corners) or pd.isna(r.away_corners):
        continue
    t = r.kickoff_utc.to_pydatetime()
    ac = acs.setdefault(r.league_id, em.acumulador("corners"))
    if r.match_id in oos.index:
        lc = ac.lambdas(t, r.home_team_id, r.away_team_id)
        o = oos.loc[r.match_id]
        if lc and bool(o.both_known):
            out.append({"t": t, "liga": r.league_id, "bl": lc[0], "bv": lc[1], "s": np.log(o.lam / o.mu),
                        "HC": int(r.home_corners), "AC": int(r.away_corners)})
    ac.agregar(t, r.home_team_id, r.away_team_id, int(r.home_corners), int(r.away_corners))
R = pd.DataFrame(out).sort_values("t").reset_index(drop=True)
corte = int(len(R) * 0.6)
TR, TE = R.iloc[:corte], R.iloc[corte:]
PHI = em.PARAMETROS["corners_equipo"]["phi"]
print(f"partidos: {len(R)} (ajuste {len(TR)} hasta {TR.t.max():%Y-%m-%d}, prueba {len(TE)})")




def nb_lp(k, m, phi):
    r = m / (phi - 1)
    return nbinom.logpmf(k, r, r / (r + m))


def ll(d, g):
    ml, mv = reparto(d, g)
    return float(np.mean(nb_lp(d.HC, ml, PHI) + nb_lp(d.AC, mv, PHI)))


from scipy.optimize import minimize as _min


def nll_lado(x, d, col, base, signo):
    m = d[base] * np.exp(x[0] + signo * x[1] * d.s)
    return -float(np.mean(nb_lp(d[col], m, PHI)))


PL = _min(nll_lado, [0, 0.2], args=(TR, "HC", "bl", 1), method="Nelder-Mead").x
PV = _min(nll_lado, [0, 0.2], args=(TR, "AC", "bv", -1), method="Nelder-Mead").x
print("local [c, γ] =", np.round(PL, 4), "| visitante [c, γ] =", np.round(PV, 4))


def reparto(d, g):
    if g == 0:
        return d.bl, d.bv
    return d.bl * np.exp(PL[0] + PL[1] * d.s), d.bv * np.exp(PV[0] - PV[1] * d.s)


g = 1.0
print(f"log-verosimilitud prueba (local+visitante): actual {ll(TE, 0):.5f} -> nuevo {ll(TE, g):.5f} (Δ {ll(TE, g) - ll(TE, 0):+.5f})")
# Mitades del periodo de prueba y por liga: que no dependa de un tramo
m = len(TE) // 2
for nombre, d in (("prueba 1ª mitad", TE.iloc[:m]), ("prueba 2ª mitad", TE.iloc[m:])):
    print(f"   {nombre}: Δ {ll(d, g) - ll(d, 0):+.5f}")
mejor = sum(ll(d, g) > ll(d, 0) for _, d in TE.groupby("liga") if len(d) > 100)
total = sum(1 for _, d in TE.groupby("liga") if len(d) > 100)
print(f"   ligas con n > 100 que mejoran: {mejor} de {total}")
# Cuánto se ajusta cada lado frente a la supremacía (por quintiles de s)
TE = TE.assign(q=pd.qcut(TE.s, 5, labels=False))
ml0, mv0 = reparto(TE, 0)
ml1, mv1 = reparto(TE, g)
print("quintil de supremacía | córners local real / actual / nuevo | visitante real / actual / nuevo")
for q, d in TE.groupby("q"):
    i = d.index
    print(f"   q{q}: {d.HC.mean():.2f} / {ml0[i].mean():.2f} / {ml1[i].mean():.2f} | {d.AC.mean():.2f} / {mv0[i].mean():.2f} / {mv1[i].mean():.2f}")

TRAMOS = ((0.62, 0.67), (0.67, 0.72), (0.72, 0.76), (0.76, 0.80), (0.80, 0.85), (0.85, 0.90), (0.90, 0.95 + 1e-9))
LINEAS = [("corners_home", lado, x) for lado in ("over", "under") for x in (1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5)] + \
         [("corners_away", lado, x) for lado in ("over", "under") for x in (1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5)]


def prueba(mercado, lado, x, gam, pmin=0.62):
    ml, mv = reparto(TE, gam)
    lam = ml if mercado == "corners_home" else mv
    real = TE.HC if mercado == "corners_home" else TE.AC
    p = np.array([em.prob_total(v, PHI, x)[lado] for v in lam])
    y = (real > x) if lado == "over" else (real < x)
    sel = (p >= pmin) & (p <= 0.95)
    p, y = p[sel], y.to_numpy()[sel]
    if len(p) < 30:
        return None
    ok, peor = True, ""
    for a, b in TRAMOS:
        k = (p >= a) & (p < b)
        if k.sum() >= 100:
            se = np.sqrt(np.sum(p[k] * (1 - p[k]))) / k.sum()
            if y[k].mean() < p[k].mean() - 2 * se:
                ok, peor = False, f"tramo {a:.2f}: {100 * p[k].mean():.1f}->{100 * y[k].mean():.1f}"
    deficit = 100 * (y.mean() - p.mean())
    if deficit < -1.0:
        ok = False
    return ok, len(p), 100 * p.mean(), 100 * y.mean(), peor


f = lambda r: "—" if r is None else f"{'PASA' if r[0] else 'no  '} n={r[1]:4d} {r[2]:.1f}->{r[3]:.1f} {r[4]}"  # noqa: E731
for pmin in (0.80, 0.75):
    print(f"\n== rango {pmin:.2f}-0.95 | línea | actual (pasa, n, prometido -> real) | nuevo")
    for mk, lado, x in LINEAS:
        a, b = prueba(mk, lado, x, 0.0, pmin), prueba(mk, lado, x, g, pmin)
        if a is None and b is None:
            continue
        print(f"  {mk} {lado} {x}: {f(a)} | {f(b)}")
