"""
Prueba histórica del hándicap asiático como escalón del reto escalera
(decisión del usuario, 2026-10-08: "hándicap protector, si pasa la prueba").

Pinnacle solo cotiza en nuestras fuentes su línea principal de hándicap; las
protectoras (+1, +1,5, +2...) que pagan 1,25-1,40 solo las dan las casas
blandas. Su probabilidad justa sale de los goles esperados que reproducen el
1X2 y el 2,5 de Pinnacle (`market_anchor.market_lambdas`), igual que "marca un
equipo" en alta probabilidad. Las líneas 0 y ±0,5 salen exactas del 1X2.

Aquí no hace falta ninguna cuota histórica de esas líneas: se mide si la
probabilidad PROMETIDA se cumple. El valor (cuota ≥ justa) se decide en vivo.

Solo líneas enteras y medias: las de cuarto liquidan medias ganadas o perdidas
y una escalera no las trata. En las enteras la probabilidad es la condicionada
a que no haya devolución (`pricing.market_asian_handicap`), y los partidos con
devolución no cuentan.

CRITERIO, fijado ANTES de ver los resultados (el de alta probabilidad):
  (a) en cada tramo con n ≥ MIN_N_TRAMO, real ≥ prometido − 2·SE, y
  (b) en conjunto, real − prometido ≥ −MAX_DEFICIT_PTS puntos.
Las líneas que pasan van a `escalera.LINEAS_HANDICAP`.

Uso: python -m qf.eval.escalera_handicap [--rho -0.0613]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import devig, two_way_devig
from ..model.pricing import market_asian_handicap, score_matrix
from ..publish import alta_prob as ap
from . import alta_prob_calibracion as apc
from . import soft_vs_sharp as sv
from .clv import _settle_outcome

LINEAS = (-1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0)
TRAMOS = ((0.60, 0.70), (0.70, 0.80), (0.80, 0.92))
MIN_N_TRAMO = apc.MIN_N_TRAMO
MAX_DEFICIT_PTS = apc.MAX_DEFICIT_PTS


def prob_handicap(p: dict[str, float], m: np.ndarray | None, lado: str, linea: float) -> float | None:
    """
    Probabilidad justa (sin devolución) de `lado` con hándicap `linea`. `m` es
    la matriz de marcadores del ajuste de goles (None si el ajuste falló).
    """
    if linea == 0.0:
        return p[lado] / (p["home"] + p["away"])
    if linea == 0.5:
        return p[lado] + p["draw"]
    if linea == -0.5:
        return p[lado]
    if m is None:
        return None
    linea_local = linea if lado == "home" else -linea
    return market_asian_handicap(m, linea_local)[lado]


def filas(raw: pd.DataFrame, rho: float) -> pd.DataFrame:
    df = sv._prepare(raw)
    if not set(apc.COLS) <= set(df.columns):
        return pd.DataFrame()
    df[apc.COLS] = df[apc.COLS].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=apc.COLS)
    df = df[(df[apc.COLS] > 1.0).all(axis=1)]
    out = []
    for r in df.to_dict("records"):
        p1x2 = devig([r["PSH"], r["PSD"], r["PSA"]], settings.devig_method)
        p = {"home": float(p1x2[0]), "draw": float(p1x2[1]), "away": float(p1x2[2])}
        p_over, _ = two_way_devig(r["P>2.5"], r["P<2.5"], settings.devig_method)
        ajuste = ap.ajuste_goles(p, 2.5, p_over, rho)
        m = (score_matrix(ajuste["lambda"], ajuste["mu"], ajuste["rho"])
             if ajuste is not None else None)
        hg, ag = int(r["FTHG"]), int(r["FTAG"])
        for lado in ("home", "away"):
            for linea in LINEAS:
                prob = prob_handicap(p, m, lado, linea)
                if prob is None or not TRAMOS[0][0] <= prob < TRAMOS[-1][1]:
                    continue
                outcome = _settle_outcome("spreads", lado, linea, hg, ag)[0]
                if outcome == "push":
                    continue
                out.append({"linea": f"{linea:+g}", "prob": prob, "won": outcome == "win"})
    return pd.DataFrame(out)


def evaluar(f: pd.DataFrame) -> dict[str, dict]:
    res = {}
    for nombre, g in f.groupby("linea"):
        tramos, ok = [], True
        for lo, hi in TRAMOS:
            t = g[(g["prob"] >= lo) & (g["prob"] < hi)]
            if t.empty:
                continue
            prom, real = float(t["prob"].mean()), float(t["won"].mean())
            se = float(np.sqrt(prom * (1 - prom) / len(t)))
            decide = len(t) >= MIN_N_TRAMO
            pasa = (not decide) or real >= prom - 2 * se
            ok = ok and pasa
            tramos.append({"tramo": f"{lo:.2f}-{hi:.2f}", "n": int(len(t)),
                           "prometido": round(prom * 100, 2), "real": round(real * 100, 2),
                           "se_pts": round(se * 100, 2), "decide": decide, "pasa": pasa})
        dif = round((float(g["won"].mean()) - float(g["prob"].mean())) * 100, 2)
        ok = ok and dif >= -MAX_DEFICIT_PTS
        res[str(nombre)] = {"n": int(len(g)), "prometido": round(float(g["prob"].mean()) * 100, 2),
                            "real": round(float(g["won"].mean()) * 100, 2),
                            "diferencia_pts": dif, "tramos": tramos, "pasa": bool(ok)}
    return res


def run(rho: float = apc.RHO_POR_DEFECTO, cache_dir: Path = Path(".local/fd_cache")) -> dict:
    raw, dataset = sv.load_csvs(apc.LIGAS, sv.DEFAULT_SEASONS, cache_dir)
    res = evaluar(filas(raw, rho))
    return {"dataset_sha256": dataset["sha256"], "rho": rho, "por_linea": res,
            "lineas_que_pasan": sorted((float(k) for k, v in res.items() if v["pasa"]))}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Prueba histórica del hándicap para la escalera")
    a.add_argument("--rho", type=float, default=apc.RHO_POR_DEFECTO)
    a.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    args = a.parse_args()
    print(json.dumps(run(args.rho, args.cache), indent=2, ensure_ascii=False))
