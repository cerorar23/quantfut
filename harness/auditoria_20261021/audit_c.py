"""Auditoría Motor C con football-data: ¿mejora el pronóstico de córners/tarjetas al añadir el contexto del partido?

Base: Acumulador de producción (estadisticas_mercado, PARAMETROS). Variante: regresión log-lineal sobre la base con
(a) supremacía del 1X2 y (b) goles esperados (logit del más de 2,5), ajustada en 2019-2022 y evaluada en 2022/23-2024/25.
Solo lectura. Uso: python audit_c.py <carpeta_csv>
"""
import glob
import io
import math
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import nbinom, poisson

sys.path.insert(0, "src")
from qf.model import estadisticas_mercado as em  # noqa: E402
from qf.model.devig import devig  # noqa: E402

carpeta = sys.argv[1]
frames = []
for p in sorted(glob.glob(f"{carpeta}/*.csv")):
    raw = open(p, "rb").read().removeprefix(b"\xef\xbb\xbf")
    d = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    d["liga"] = p.replace("\\", "/").rsplit("/", 1)[-1].split("_")[0]
    d["temporada"] = p.rsplit("_", 1)[-1][:4]
    frames.append(d)
df = pd.concat(frames, ignore_index=True)
df["fecha"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["fecha", "HC", "AC", "HY", "AY", "HR", "AR", "PSCH", "PSCD", "PSCA"]).sort_values("fecha").reset_index(drop=True)
df = df[df.liga != "E1"].reset_index(drop=True)   # producción no usa Championship
print("partidos:", len(df))
_ok = df["PC>2.5"].gt(1) & df["PC<2.5"].gt(1)
df["po"] = np.where(_ok, (1 / df["PC>2.5"]) / (1 / df["PC>2.5"] + 1 / df["PC<2.5"]), np.nan)
df["po"] = [devig([a, b], "shin")[0] if ok else np.nan for a, b, ok in zip(df["PC>2.5"], df["PC<2.5"], _ok)]

rows = []
acs = {}
for r in df.itertuples(index=False):
    for est in ("corners", "cards"):
        acs.setdefault((r.liga, est), em.acumulador(est))
    ac, at = acs[(r.liga, "corners")], acs[(r.liga, "cards")]
    t = r.fecha.to_pydatetime()
    lc = ac.lambdas(t, r.HomeTeam, r.AwayTeam)
    ref = r.Referee if isinstance(getattr(r, "Referee", None), str) else None
    lt = at.lambdas(t, r.HomeTeam, r.AwayTeam, ref)
    p = devig([r.PSCH, r.PSCD, r.PSCA], "shin")
    po = r.po if pd.notna(r.po) else None
    if lc and lt and po is not None:
        rows.append({"temporada": r.temporada, "liga": r.liga, "ch": lc[0], "ca": lc[1], "th": lt[0], "ta": lt[1],
                     "sup": p[0] - p[2], "goles": math.log(po / (1 - po)), "draw": p[1],
                     "HC": r.HC, "AC": r.AC, "T": r.HY + r.AY + r.HR + r.AR})
    ac.agregar(t, r.HomeTeam, r.AwayTeam, int(r.HC), int(r.AC))
    at.agregar(t, r.HomeTeam, r.AwayTeam, int(r.HY + r.HR), int(r.AY + r.AR), ref)
R = pd.DataFrame(rows)
tr = R[R.temporada.isin(["1920", "2021", "2122"])]
te = R[R.temporada.isin(["2223", "2324", "2425"])]
print("ajuste", len(tr), "prueba", len(te))


def nb_logpmf(k, mean, phi):
    if phi <= 1.0001:
        return poisson.logpmf(k, mean)
    rr = mean / (phi - 1)
    return nbinom.logpmf(k, rr, rr / (rr + mean))


def phi_mom(y, mean):
    return max(float(np.sum((y - mean) ** 2) / np.sum(mean)), 1.0)


def fit_poisson(X, y, off):
    def f(b):
        eta = off + X @ b
        return -np.sum(y * eta - np.exp(eta))
    return minimize(f, np.zeros(X.shape[1]), method="BFGS").x


def evaluar(nombre, y, mean, phi, lineas):
    lp = np.mean([nb_logpmf(k, m, phi) for k, m in zip(y, mean)])
    out = f"  {nombre:28s} log-verosimilitud {lp:.5f} | φ {phi:.3f} |"
    for lado, ln in lineas:
        pr = np.array([em.prob_total(m, phi, ln)[lado] for m in mean])
        yy = (y > ln) if lado == "over" else (y < ln)
        br = np.mean((pr - yy) ** 2)
        out += f" {lado[0]}{ln}: p {pr.mean():.3f} y {yy.mean():.3f} B {br:.4f} |"
    print(out)


print("\n== Córners totales ==")
lineas_c = em.LINEAS_HABILITADAS["corners"]
base_te = (te.ch + te.ca).to_numpy()
evaluar("producción", te.HC + te.AC, base_te, em.PARAMETROS["corners"]["phi"], lineas_c)
# Variante: cada lado por separado con supremacía y goles
Xh = np.column_stack([np.ones(len(tr)), np.log(tr.ch), tr.sup, tr.goles])
Xa = np.column_stack([np.ones(len(tr)), np.log(tr.ca), -tr.sup, tr.goles])
bh = fit_poisson(Xh, tr.HC.to_numpy(float), np.zeros(len(tr)))
ba = fit_poisson(Xa, tr.AC.to_numpy(float), np.zeros(len(tr)))
print("  coef local [cte, log base, sup, goles]", np.round(bh, 3), "| visita", np.round(ba, 3))
mh = lambda d, b: np.exp(np.column_stack([np.ones(len(d)), np.log(d.ch), d.sup, d.goles]) @ b)  # noqa: E731
ma = lambda d, b: np.exp(np.column_stack([np.ones(len(d)), np.log(d.ca), -d.sup, d.goles]) @ b)  # noqa: E731
mtr = mh(tr, bh) + ma(tr, ba)
phi_v = phi_mom((tr.HC + tr.AC).to_numpy(), mtr)
evaluar("con supremacía y goles", te.HC + te.AC, mh(te, bh) + ma(te, ba), phi_v, lineas_c)
# Solo recalibrar la base (sin contexto), para separar el efecto
X0 = np.column_stack([np.ones(len(tr)), np.log(tr.ch + tr.ca)])
b0 = fit_poisson(X0, (tr.HC + tr.AC).to_numpy(float), np.zeros(len(tr)))
m0 = lambda d: np.exp(np.column_stack([np.ones(len(d)), np.log(d.ch + d.ca)]) @ b0)  # noqa: E731
evaluar("base recalibrada", te.HC + te.AC, m0(te), phi_mom((tr.HC + tr.AC).to_numpy(), m0(tr)), lineas_c)

print("\n== Córners por equipo ==")
for lado, col, base, f, b in (("local", "HC", "ch", mh, bh), ("visita", "AC", "ca", ma, ba)):
    lp0 = np.mean([nb_logpmf(k, m, em.PARAMETROS["corners_equipo"]["phi"]) for k, m in zip(te[col], te[base])])
    mm = f(te, b)
    ph = phi_mom(tr[col].to_numpy(), f(tr, b))
    lp1 = np.mean([nb_logpmf(k, m, ph) for k, m in zip(te[col], mm)])
    print(f"  {lado}: producción {lp0:.5f} | con contexto {lp1:.5f} (φ {ph:.3f})")

print("\n== Tarjetas ==")
lineas_t = em.LINEAS_HABILITADAS["cards"]
evaluar("producción", te["T"], (te.th + te.ta).to_numpy(), em.PARAMETROS["cards"]["phi"], lineas_t)
Xt = lambda d: np.column_stack([np.ones(len(d)), np.log(d.th + d.ta), np.abs(d.sup), d.draw])  # noqa: E731
bt = fit_poisson(Xt(tr), tr["T"].to_numpy(float), np.zeros(len(tr)))
print("  coef [cte, log base, |sup|, p empate]", np.round(bt, 3))
mt = lambda d: np.exp(Xt(d) @ bt)  # noqa: E731
evaluar("con igualdad del partido", te["T"], mt(te), phi_mom(tr["T"].to_numpy(), mt(tr)), lineas_t)
X1 = lambda d: np.column_stack([np.ones(len(d)), np.log(d.th + d.ta)])  # noqa: E731
b1 = fit_poisson(X1(tr), tr["T"].to_numpy(float), np.zeros(len(tr)))
m1 = lambda d: np.exp(X1(d) @ b1)  # noqa: E731
evaluar("base recalibrada", te["T"], m1(te), phi_mom(tr["T"].to_numpy(), m1(tr)), lineas_t)
print("  tarjetas medias por temporada:", R.groupby("temporada")["T"].mean().round(2).to_dict())
print("  predicho producción por temporada:", R.assign(p=R.th + R.ta).groupby("temporada")["p"].mean().round(2).to_dict())
