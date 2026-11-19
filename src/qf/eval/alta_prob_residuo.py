"""
Medición del límite del ajuste de goles (`alta_prob.MAX_RESIDUO_AJUSTE`). Protocolo y criterio: docs/medicion_residuo_ajuste_20261118.md,
fijados ANTES de ejecutar esto.

Repite la prueba histórica de `alta_prob_calibracion` (football-data, Pinnacle PRE-CIERRE: 1X2 y línea 2,5) pero SIN el límite de residuo, y
reparte los candidatos que dependen del ajuste de goles por la calidad del ajuste de su partido. La prueba original aplicó el límite vigente
(0,01) y por eso solo validó los mercados de goles en los partidos donde el ajuste encaja.

Los candidatos de un partido no son independientes: todo error estándar y todo intervalo va POR PARTIDO.

Uso: python -m qf.eval.alta_prob_residuo --cache <carpeta de football-data> [--rho -0.0347] [--json salida.json]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..model.devig import devig, two_way_devig
from ..model.market_anchor import market_lambdas
from ..publish import alta_prob as ap
from . import alta_prob_calibracion as cal
from . import soft_vs_sharp as sv
from .clv import _settle_outcome

RHO_ACTIVO = -0.0347           # modelo activo en producción el 13-nov-2026
LINEA = 2.5                    # football-data solo trae esta línea
BASE = 0.010                   # límite vigente
GRUPOS = (("A", 0.0, 0.010), ("B", 0.010, 0.015), ("C", 0.015, 0.020), ("D", 0.020, 0.030), ("E", 0.030, math.inf))
LIMITES = (0.015, 0.020, 0.030)
# Criterio fijado en el protocolo:
MAX_DEFICIT_PTS = 1.0          # (1) brecha conjunta del incremento ≥ −1,0 punto
MAX_PEOR_QUE_BASE_PTS = 2.0    # (3) brecha(I_X) − brecha(A) ≥ −2,0 puntos
MIN_PARTIDOS = 300             # incremento mínimo para concluir
Z = 2.0                        # (2) real ≥ prometido − 2·SE (clúster)
MIN_N_TRAMO = cal.MIN_N_TRAMO
HABILITADOS_80 = {("totals", "over", 1.5), ("totals", "under", 3.5), ("totals", "over", 2.5)}   # alta_prob.MERCADOS_GOLES_HABILITADOS


def grupo_de(residuo: float) -> str:
    for nombre, _, hi in GRUPOS:
        if residuo <= hi:
            return nombre
    return "E"


def candidatos_dependientes(p: dict, ajuste: dict) -> list[ap.Candidato]:
    """Candidatos de la línea ampliada que existen CON ajuste y no sin él (el hándicap 0 sale del 1X2)."""
    con = (ap.candidatos_goles(ajuste, ap.GOLES_EXT) + ap.candidatos_equipo(ajuste, ap.MERCADOS_EQUIPO_HABILITADOS)
           + ap.candidatos_btts(ajuste, ap.BTTS_EXT) + ap.candidatos_handicap(p, ajuste, ap.HANDICAP_HABILITADOS))
    sin = {(c.market, c.selection, c.line) for c in ap.candidatos_handicap(p, None, ap.HANDICAP_HABILITADOS)}
    return [c for c in con if (c.market, c.selection, c.line) not in sin]


def _habilitado_80(c: ap.Candidato) -> bool:
    if c.market == "totals":
        return (c.market, c.selection, c.line) in HABILITADOS_80
    if c.market.startswith("team_totals"):
        return c.market.removeprefix("team_totals_") in ap.MERCADOS_EQUIPO_HABILITADOS
    if c.market == "spreads":
        return c.line in ap.HANDICAP_HABILITADOS
    return c.market == "btts" and c.selection in ap.BTTS_HABILITADOS


def medir_partidos(raw: pd.DataFrame, rho: float) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    (candidatos, partidos, conteos). `candidatos`: una fila por candidato dependiente del ajuste con 62-95 % y desenlace (sin
    devoluciones), con el residuo de su partido. `partidos`: residuo y si hay candidato independiente del ajuste en cada línea.
    """
    df = sv._prepare(raw)
    if not set(cal.COLS) <= set(df.columns):
        return pd.DataFrame(), pd.DataFrame(), {"partidos": 0}
    df[cal.COLS] = df[cal.COLS].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=cal.COLS)
    df = df[(df[cal.COLS] > 1.0).all(axis=1)]
    cands, partidos = [], []
    cuenta = {"partidos": 0, "sin_convergencia": 0, "valueerror": 0}
    for r in df.to_dict("records"):
        cuenta["partidos"] += 1
        p1 = devig([r["PSH"], r["PSD"], r["PSA"]], settings.devig_method)
        p = {"home": float(p1[0]), "draw": float(p1[1]), "away": float(p1[2])}
        p_over, _ = two_way_devig(r["P>2.5"], r["P<2.5"], settings.devig_method)
        try:
            fit = market_lambdas(p["home"], p["draw"], p["away"], rho=rho, totals={LINEA: p_over})
        except ValueError:
            cuenta["valueerror"] += 1
            continue
        if not fit.converged:
            cuenta["sin_convergencia"] += 1
            continue
        ajuste = {"lambda": fit.lam, "mu": fit.mu, "rho": rho, "linea": LINEA, "residuo": fit.residual}
        hg, ag = int(r["FTHG"]), int(r["FTAG"])
        indep = ap.candidatos_1x2(p) + ap.candidatos_doble(p) + [c for c in ap.candidatos_handicap(p, None, ap.HANDICAP_HABILITADOS)]
        dep = candidatos_dependientes(p, ajuste)
        partidos.append({"match": r["match"], "liga": r["league_id"], "residuo": float(fit.residual),
                         "indep_80": any(ap.PROB_MIN <= c.prob <= ap.PROB_MAX for c in indep),
                         "indep_ext": any(ap.PROB_MIN_EXT <= c.prob <= ap.PROB_MAX for c in indep),
                         "dep_80": any(_habilitado_80(c) and ap.PROB_MIN <= c.prob <= ap.PROB_MAX for c in dep),
                         "dep_ext": any(ap.PROB_MIN_EXT <= c.prob <= ap.PROB_MAX for c in dep)})
        for c in dep:
            if not ap.PROB_MIN_EXT <= c.prob <= ap.PROB_MAX:
                continue
            out = _settle_outcome(c.market, c.selection, c.line, hg, ag)[0]
            if out not in ("win", "loss"):
                continue
            cands.append({"match": r["match"], "liga": r["league_id"], "residuo": float(fit.residual),
                          "mercado": cal._nombre(c), "prob": c.prob, "won": out == "win"})
    return pd.DataFrame(cands), pd.DataFrame(partidos), cuenta


# --------------------------------------------------------------------------
# Estadística por partido (clúster)
# --------------------------------------------------------------------------

def _por_partido(g: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    d = (g["won"].astype(float) - g["prob"]).groupby(g["match"]).sum().to_numpy()
    n = g.groupby("match").size().to_numpy().astype(float)
    return d, n


def brecha(g: pd.DataFrame) -> dict:
    """Brecha real − prometido (puntos), su error estándar por partido, n de candidatos y de partidos."""
    if g.empty:
        return {"n": 0, "partidos": 0, "brecha_pts": float("nan"), "se_pts": float("nan"),
                "real": float("nan"), "prometido": float("nan")}
    d, n = _por_partido(g)
    tot, m = n.sum(), len(n)
    b = d.sum() / tot
    var = (m / (m - 1) if m > 1 else float("nan")) * float(((d - b * n) ** 2).sum()) / tot ** 2
    return {"n": int(tot), "partidos": int(m), "brecha_pts": float(b * 100), "se_pts": float(math.sqrt(var) * 100),
            "real": float(g["won"].mean() * 100), "prometido": float(g["prob"].mean() * 100)}


def diferencia_ic(a: pd.DataFrame, b: pd.DataFrame, reps: int = 2000, seed: int = 20261118) -> dict:
    """brecha(b) − brecha(a) en puntos, con intervalo del 95 % remuestreando partidos de cada grupo por separado."""
    rng = np.random.default_rng(seed)

    def reman(g):
        d, n = _por_partido(g)
        c = rng.multinomial(len(n), np.full(len(n), 1 / len(n)), size=reps)
        return (c @ d) / (c @ n)

    if a.empty or b.empty:
        return {"diff_pts": float("nan"), "ic95": [float("nan"), float("nan")]}
    dif = (reman(b) - reman(a)) * 100
    punto = brecha(b)["brecha_pts"] - brecha(a)["brecha_pts"]
    return {"diff_pts": float(punto), "ic95": [float(np.percentile(dif, 2.5)), float(np.percentile(dif, 97.5))]}


def tramos_por_mercado(g: pd.DataFrame) -> list[dict]:
    """La prueba por tramo de la prueba original, con error estándar por partido (criterio 2)."""
    filas = []
    for mercado, gm in g.groupby("mercado"):
        for lo, hi in cal.TRAMOS_AMPLIOS:
            t = gm[(gm["prob"] >= lo) & (gm["prob"] < hi)]
            if t.empty:
                continue
            b = brecha(t)
            decide = b["n"] >= MIN_N_TRAMO
            pasa = (not decide) or b["brecha_pts"] >= -Z * b["se_pts"]
            filas.append({"mercado": str(mercado), "tramo": f"{lo:.2f}-{min(hi, 0.95):.2f}", **b, "decide": decide, "pasa": bool(pasa)})
    return filas


def evaluar_limite(c: pd.DataFrame, x: float) -> dict:
    """Aplica el criterio del protocolo al incremento (BASE, x]."""
    base = c[c["residuo"] <= BASE]
    inc = c[(c["residuo"] > BASE) & (c["residuo"] <= x)]
    b_inc, b_base = brecha(inc), brecha(base)
    tramos = tramos_por_mercado(inc)
    dif = diferencia_ic(base, inc)
    cond1 = b_inc["n"] > 0 and b_inc["brecha_pts"] >= -MAX_DEFICIT_PTS
    cond2 = all(t["pasa"] for t in tramos if t["decide"])
    cond3 = dif["diff_pts"] >= -MAX_PEOR_QUE_BASE_PTS
    suficiente = b_inc["partidos"] >= MIN_PARTIDOS
    return {"limite": x, "incremento": b_inc, "base": b_base, "diferencia_vs_base": dif,
            "cond1_brecha_conjunta": bool(cond1), "cond2_tramos": bool(cond2), "cond3_no_peor_que_base": bool(cond3),
            "partidos_suficientes": bool(suficiente), "tramos_que_fallan": [t for t in tramos if t["decide"] and not t["pasa"]],
            "acepta": bool(cond1 and cond2 and cond3 and suficiente)}


def decision(c: pd.DataFrame) -> dict:
    evals = [evaluar_limite(c, x) for x in LIMITES]
    aceptados = [e["limite"] for e in evals if e["acepta"]]
    return {"evaluaciones": evals, "limite_propuesto": max(aceptados) if aceptados else BASE}


# --------------------------------------------------------------------------
# Informes
# --------------------------------------------------------------------------

def por_grupo(c: pd.DataFrame) -> dict:
    c = c.assign(grupo=c["residuo"].map(grupo_de))
    return {g: brecha(c[c["grupo"] == g]) for g, _, _ in GRUPOS}


def partidos_con_pick(p: pd.DataFrame) -> dict:
    """% de partidos con candidato elegible por probabilidad (sin exigir cuota) en cada línea, según el límite."""
    out = {}
    for lim in (BASE, *LIMITES, math.inf):
        ok = p["residuo"] <= lim
        out["sin_limite" if lim == math.inf else f"{lim:g}"] = {
            "linea_80": round(100 * float((p["indep_80"] | (ok & p["dep_80"])).mean()), 1),
            "linea_ampliada": round(100 * float((p["indep_ext"] | (ok & p["dep_ext"])).mean()), 1)}
    return out


def informe(raw: pd.DataFrame, rho: float) -> dict:
    c, p, cuenta = medir_partidos(raw, rho)
    rs = p["residuo"].to_numpy()
    q = lambda f: float(np.quantile(rs, f))
    banda = lambda g, lo, hi: g[(g["prob"] >= lo) & (g["prob"] < hi)]
    return {"rho": rho, "conteos": cuenta,
            "residuo": {"mediana": q(0.5), "p75": q(0.75), "p90": q(0.9), "p95": q(0.95), "max": float(rs.max()),
                        "pct_por_encima_de_0.01": round(100 * float((rs > BASE).mean()), 1)},
            "por_grupo": por_grupo(c),
            "decision": decision(c),
            "por_grupo_y_banda": {nombre: por_grupo(banda(c, lo, hi)) for nombre, (lo, hi) in
                                  {"0.62-0.80": (0.62, 0.80), "0.80-0.95": (0.80, 0.9500001)}.items()},
            "por_mercado_incremento_0.02": {m: brecha(g) for m, g in
                                            c[(c["residuo"] > BASE) & (c["residuo"] <= 0.02)].groupby("mercado")},
            "por_liga_incremento_0.02": {m: brecha(g) for m, g in
                                         c[(c["residuo"] > BASE) & (c["residuo"] <= 0.02)].groupby("liga")},
            "partidos_con_pick": partidos_con_pick(p)}


def main() -> None:
    ap_ = argparse.ArgumentParser(description="Medición del límite del ajuste de goles")
    ap_.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    ap_.add_argument("--rho", type=float, default=RHO_ACTIVO)
    ap_.add_argument("--json", type=Path, default=None)
    a = ap_.parse_args()
    raw, dataset = sv.load_csvs(cal.LIGAS, sv.DEFAULT_SEASONS, a.cache)
    res = {"dataset_sha256": dataset["sha256"], "filas": dataset["rows"], **informe(raw, a.rho)}
    texto = json.dumps(res, indent=2, ensure_ascii=False, default=float)
    if a.json:
        a.json.write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
