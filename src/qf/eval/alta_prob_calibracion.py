"""
Prueba histórica de la línea de alta probabilidad (diseño 2026-10-05, §4.1).

Repite la selección sobre football-data con el 1X2 (PSH/PSD/PSA) y el 2,5
(P>2.5 / P<2.5) de Pinnacle PRE-CIERRE (de uno a tres días antes) y compara la
probabilidad prometida con lo ocurrido, por mercado y tramo.

CRITERIO, fijado ANTES de ver los resultados: un mercado pasa si
  (a) en cada tramo con n ≥ MIN_N_TRAMO, real ≥ prometido − 2·SE, y
  (b) en conjunto, real − prometido ≥ −MAX_DEFICIT_PTS puntos.
Solo los mercados de goles que pasan entran en
`alta_prob.MERCADOS_GOLES_HABILITADOS`. El 1X2 y la doble oportunidad se
miden igual para dejar constancia.

LÍMITE: football-data solo trae la línea 2,5. Las de cuarto y gol entero que
Pinnacle cotiza en vivo no se pueden validar aquí; las cubre el control en
vivo por mercado (`alta_prob.control`).

FUGAS: la selección solo lee cuotas pre-cierre; el resultado solo se usa al
evaluar.

Uso: python -m qf.eval.alta_prob_calibracion [--rho -0.0613]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import devig, two_way_devig
from ..publish import alta_prob as ap
from . import soft_vs_sharp as sv
from .clv import _settle_outcome

# Las 7 ligas de formato principal (leagues.fd_code con fd_extra = FALSE).
LIGAS = {"de.bundesliga": "D1", "es.laliga": "SP1", "fr.ligue_1": "F1",
         "gb.premier_league": "E0", "it.serie_a": "I1", "nl.eredivisie": "N1",
         "pt.primeira": "P1"}
COLS = ["PSH", "PSD", "PSA", "P>2.5", "P<2.5"]
TRAMOS = ((0.80, 0.85), (0.85, 0.90), (0.90, 0.95 + 1e-9))
MIN_N_TRAMO = 100
MAX_DEFICIT_PTS = 1.0
# rho del modelo activo el 2026-10-05 (2026.09.27-010508, /model-card).
RHO_POR_DEFECTO = -0.0613


def _nombre(c: ap.Candidato) -> str:
    return c.market if c.market != "totals" else f"totals {c.selection} {c.line:g}"


def filas(raw: pd.DataFrame, rho: float) -> pd.DataFrame:
    """Una fila por candidato dentro del rango, con si acertó y si era el elegido."""
    df = sv._prepare(raw)
    if not set(COLS) <= set(df.columns):
        return pd.DataFrame()
    df[COLS] = df[COLS].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=COLS)
    df = df[(df[COLS] > 1.0).all(axis=1)]
    out = []
    for r in df.to_dict("records"):
        p1x2 = devig([r["PSH"], r["PSD"], r["PSA"]], settings.devig_method)
        p = {"home": float(p1x2[0]), "draw": float(p1x2[1]), "away": float(p1x2[2])}
        p_over, _ = two_way_devig(r["P>2.5"], r["P<2.5"], settings.devig_method)
        ajuste = ap.ajuste_goles(p, 2.5, p_over, rho)
        cands = (ap.candidatos_1x2(p) + ap.candidatos_doble(p)
                 + ap.candidatos_goles(ajuste, ap.LINEAS_GOLES))
        elegido = ap.elegir(cands)
        hg, ag = int(r["FTHG"]), int(r["FTAG"])
        for c in cands:
            if not ap.PROB_MIN <= c.prob <= ap.PROB_MAX:
                continue
            out.append({"mercado": _nombre(c), "prob": c.prob,
                        "won": _settle_outcome(c.market, c.selection, c.line, hg, ag)[0] == "win",
                        "elegido": c == elegido, "week": r["week"]})
    return pd.DataFrame(out)


def evaluar(f: pd.DataFrame) -> dict[str, dict]:
    res = {}
    for nombre, g in f.groupby("mercado"):
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
            tramos.append({"tramo": f"{lo:.2f}-{min(hi, 0.95):.2f}", "n": int(len(t)),
                           "prometido": round(prom * 100, 2), "real": round(real * 100, 2),
                           "se_pts": round(se * 100, 2), "decide": decide, "pasa": pasa})
        dif = round((float(g["won"].mean()) - float(g["prob"].mean())) * 100, 2)
        ok = ok and dif >= -MAX_DEFICIT_PTS
        res[str(nombre)] = {"n": int(len(g)), "prometido": round(float(g["prob"].mean()) * 100, 2),
                            "real": round(float(g["won"].mean()) * 100, 2),
                            "diferencia_pts": dif, "tramos": tramos, "pasa": bool(ok)}
    return res


def run(rho: float = RHO_POR_DEFECTO, cache_dir: Path = Path(".local/fd_cache")) -> dict:
    raw, dataset = sv.load_csvs(LIGAS, sv.DEFAULT_SEASONS, cache_dir)
    f = filas(raw, rho)
    elegidos = f[f["elegido"]].assign(mercado="regla completa")
    return {"dataset_sha256": dataset["sha256"], "partidos": dataset["rows"], "rho": rho,
            "por_mercado": evaluar(f),
            "regla_completa": evaluar(elegidos).get("regla completa"),
            "goles_que_pasan": sorted(k for k, v in evaluar(f).items()
                                      if k.startswith("totals") and v["pasa"])}


if __name__ == "__main__":
    ap_ = argparse.ArgumentParser(description="Prueba histórica de la línea de alta probabilidad")
    ap_.add_argument("--rho", type=float, default=RHO_POR_DEFECTO)
    ap_.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    a = ap_.parse_args()
    print(json.dumps(run(a.rho, a.cache), indent=2, ensure_ascii=False))
