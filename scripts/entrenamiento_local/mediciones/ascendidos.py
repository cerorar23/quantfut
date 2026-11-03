"""Prior de ascendidos: ¿los equipos que vuelven a la liga tras ≥1 temporada fuera están sobrevalorados por el modelo?

    ascendidos.py <oos.pkl> [salida.json]

Marca, de forma point-in-time y solo con los datos del catálogo, a los equipos en el primer tramo tras un hueco de más de 270 días
sin partidos (ascenso o regreso) y mide: (1) el sesgo del modelo base en sus partidos, (2) una corrección multiplicativa de λ y μ
(ataque `a` y defensa `d` del ascendido, que se desvanece con los partidos jugados, f = exp(-jugados/τ)) ajustada por
validación cruzada de bloques anuales (se ajusta en dos años y se evalúa en el tercero, rotando).
"""
import json
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from qf.model.train import load_training_data
from _comun import cargar_oos, delta, logver_marcador, probs_de_lambdas, rps

oos = cargar_oos(sys.argv[1])
df = load_training_data()
largo = pd.concat([
    df[["match_id", "kickoff_utc", "home_team_id"]].rename(columns={"home_team_id": "tid"}).assign(lado="h"),
    df[["match_id", "kickoff_utc", "away_team_id"]].rename(columns={"away_team_id": "tid"}).assign(lado="a"),
]).sort_values(["tid", "kickoff_utc", "match_id"]).reset_index(drop=True)
hueco = largo.groupby("tid")["kickoff_utc"].diff().dt.days
largo["spell"] = (hueco.isna() | (hueco > 270)).groupby(largo["tid"]).cumsum()
largo["jugados"] = largo.groupby(["tid", "spell"]).cumcount()
largo["inicio"] = largo.groupby(["tid", "spell"])["kickoff_utc"].transform("min")
largo["edad"] = (largo["kickoff_utc"] - largo["inicio"]).dt.days
# la primera aparición absoluta del equipo en la base no es un ascenso: no hay referencia previa
primera = largo.groupby("tid")["kickoff_utc"].transform("min")
largo["nuevo_catalogo"] = largo["inicio"] == primera
for lado in ("h", "a"):
    t = largo[largo.lado == lado].set_index("match_id")[["jugados", "edad", "nuevo_catalogo"]].add_suffix("_" + lado)
    oos = oos.merge(t, left_on="match_id", right_index=True, how="left")
# El inicio de la base (hace 12 años) no cuenta como regreso: solo spells posteriores a un hueco real
for lado in ("h", "a"):
    oos["asc_" + lado] = (~oos["nuevo_catalogo_" + lado].fillna(True).astype(bool)) & (oos["edad_" + lado] < 330)
print(f"OOS {len(oos)} filas; con ascendido local {int(oos.asc_h.sum())}, visitante {int(oos.asc_a.sum())}, "
      f"alguno {int((oos.asc_h | oos.asc_a).sum())}")

lam, mu, rho = oos.lam.to_numpy(float), oos.mu.to_numpy(float), oos.rho.to_numpy(float)
hg, ag, y = oos.home_goals.to_numpy(int), oos.away_goals.to_numpy(int), oos.outcome.to_numpy(int)
base = probs_de_lambdas(lam, mu, rho)
r0 = rps(base, y)
oos["año"] = ((oos.kickoff_utc - oos.kickoff_utc.min()).dt.days // 365).clip(upper=2)
print("\n== Sesgo del modelo base por grupo (goles reales / λ esperado) ==")
grupos = {"ninguno asc.": ~(oos.asc_h | oos.asc_a), "local asc.": oos.asc_h & ~oos.asc_a,
          "visitante asc.": oos.asc_a & ~oos.asc_h, "ambos asc.": oos.asc_h & oos.asc_a}
for nombre, m in grupos.items():
    m = m.to_numpy()
    if m.sum() == 0:
        continue
    print(f"{nombre:14s} n={m.sum():5d} RPS={r0[m].mean():.4f} goles_loc/λ={hg[m].sum() / lam[m].sum():.3f} "
          f"goles_vis/μ={ag[m].sum() / mu[m].sum():.3f} empate pred={base[m, 1].mean():.3f} real={(y[m] == 1).mean():.3f}")

jug_h, jug_a = oos.jugados_h.fillna(99).to_numpy(float), oos.jugados_a.fillna(99).to_numpy(float)
ah, aa = oos.asc_h.to_numpy(float), oos.asc_a.to_numpy(float)


def ajustado(par, tau, i=None):
    a, d = par
    fh, fa = ah * np.exp(-jug_h / tau), aa * np.exp(-jug_a / tau)
    return lam * np.exp(a * fh + d * fa), mu * np.exp(a * fa + d * fh)


def ajustar(tau, filas):
    f = lambda p: -logver_marcador(*(v[filas] for v in ajustado(p, tau)), rho[filas], hg[filas], ag[filas])  # noqa: E731
    o = minimize(f, [0.0, 0.0], method="Nelder-Mead", options={"xatol": 1e-3, "fatol": 1e-7})
    return o.x


print("\n== Corrección por validación cruzada de bloques anuales ==")
res = {}
for tau in (5.0, 10.0, 20.0, 1e9):
    p_cv = np.zeros_like(base)
    pars = []
    for k in range(3):
        te = (oos["año"] == k).to_numpy()
        if te.sum() == 0:
            continue
        par = ajustar(tau, np.where(~te)[0])
        pars.append(par)
        l2, m2 = ajustado(par, tau)
        p_cv[te] = probs_de_lambdas(l2[te], m2[te], rho[te])
    ok = p_cv.sum(axis=1) > 0
    dl, p95 = delta(base[ok], p_cv[ok], y[ok])
    afect = ((ah + aa) > 0) & ok
    dl2, p952 = delta(base[afect], p_cv[afect], y[afect])
    ajuste_final = ajustar(tau, np.arange(len(y)))
    res[str(tau)] = {"dRPS_total": dl, "p95": p95, "dRPS_afectados": dl2, "p95_afectados": p952, "n_afectados": int(afect.sum()),
                     "a_d_toda_la_muestra": [round(float(v), 4) for v in ajuste_final],
                     "a_d_por_bloque": [[round(float(v), 4) for v in p] for p in pars]}
    print(f"tau={tau:>6}: total ΔRPS {dl:+.5f} (p95 {p95:+.5f}) | afectados n={afect.sum()} ΔRPS {dl2:+.5f} (p95 {p952:+.5f}) "
          f"| a,d toda la muestra {np.round(ajuste_final, 3)} | por bloque {[list(np.round(p, 3)) for p in pars]}")
if len(sys.argv) > 2:
    json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
