"""
Prueba histórica de la 1ª mitad (pedida por el usuario, 2026-10-12).

El modelo de la 1ª mitad es el de goles escalado: con los goles esperados de MERCADO
de cada partido (el mismo ajuste a Pinnacle que usa la alta probabilidad), los goles
del primer tiempo son Poisson independientes con media `s_local · lambda` y
`s_visit · mu`. `s` es la proporción de goles que cae en el 1T y se ajusta SOLO con
las temporadas de entreno; se mide en las posteriores (nada del periodo de medida
entra al ajuste).

CRITERIO, el mismo de `alta_prob_calibracion` y fijado antes de ver resultados: un
mercado pasa si en cada tramo con n >= MIN_N_TRAMO real >= prometido - 2·SE y, en
conjunto, real - prometido >= -MAX_DEFICIT_PTS. Los mercados de 1ª mitad solo se
publican si pasan; si no, no se muestran.

Uso: python -m qf.eval.primer_tiempo [--rho -0.0613]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ..config import settings
from ..model import primer_tiempo as modelo_1t
from ..model.devig import devig, two_way_devig
from ..publish import alta_prob as ap
from . import alta_prob_calibracion as ac
from . import soft_vs_sharp as sv

PROB_MIN = modelo_1t.PROB_MIN_VALIDADA
PROB_MAX = modelo_1t.PROB_MAX_VALIDADA
# Temporadas de ENTRENO de la proporción s; el resto es de medida.
ENTRENO = ("1920", "2021", "2122")


def _lambdas(raw: pd.DataFrame, rho: float) -> pd.DataFrame:
    """Una fila por partido con (lambda, mu) de mercado y los goles del 1T y del partido."""
    df = sv._prepare(raw)
    need = ac.COLS + ["HTHG", "HTAG"]
    if not set(need) <= set(df.columns):
        return pd.DataFrame()
    df[need] = df[need].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=need)
    df = df[(df[ac.COLS] > 1.0).all(axis=1)]
    out = []
    for r in df.to_dict("records"):
        p1x2 = devig([r["PSH"], r["PSD"], r["PSA"]], settings.devig_method)
        p = {"home": float(p1x2[0]), "draw": float(p1x2[1]), "away": float(p1x2[2])}
        p_over, _ = two_way_devig(r["P>2.5"], r["P<2.5"], settings.devig_method)
        fit = ap.ajuste_goles(p, 2.5, p_over, rho)
        if fit is None:
            continue
        out.append({"match": r["match"], "season": r.get("season"), "week": r["week"],
                    "lam": fit["lambda"], "mu": fit["mu"],
                    "hth": int(r["HTHG"]), "hta": int(r["HTAG"])})
    return pd.DataFrame(out)


def ajustar_proporcion(train: pd.DataFrame) -> tuple[float, float]:
    """(s_local, s_visit): goles del 1T entre goles esperados del partido, del entreno."""
    return float(train["hth"].sum() / train["lam"].sum()), float(train["hta"].sum() / train["mu"].sum())


def filas(df: pd.DataFrame, s: tuple[float, float]) -> pd.DataFrame:
    out = []
    for r in df.to_dict("records"):
        p = modelo_1t.probs(r["lam"], r["mu"], s)
        h, a = r["hth"], r["hta"]
        reales = {
            "gol_1t_si": h + a >= 1, "ambos_1t_si": h >= 1 and a >= 1, "mas_1_5_1t": h + a >= 2,
            "ganador_1t_local": h > a, "ganador_1t_empate": h == a, "ganador_1t_visita": h < a,
        }
        cands = []
        for k in ("gol_1t_si", "ambos_1t_si", "mas_1_5_1t"):
            cands.append((k.replace("_si", "") + " sí", p[k], reales[k]))
            cands.append((k.replace("_si", "") + " no", 1 - p[k], not reales[k]))
        for k in ("ganador_1t_local", "ganador_1t_empate", "ganador_1t_visita"):
            cands.append((k, p[k], reales[k]))
        for nombre, prob, won in cands:
            if PROB_MIN <= prob <= PROB_MAX:
                out.append({"mercado": nombre, "prob": prob, "won": bool(won), "week": r["week"]})
    return pd.DataFrame(out)


def run(rho: float = ac.RHO_POR_DEFECTO, cache_dir: Path = Path(".local/fd_cache")) -> dict:
    raw, dataset = sv.load_csvs(ac.LIGAS, sv.DEFAULT_SEASONS, cache_dir)
    d = _lambdas(raw, rho)
    train = d[d["season"].isin(ENTRENO)]
    test = d[~d["season"].isin(ENTRENO)]
    s = ajustar_proporcion(train)
    res = ac.evaluar(filas(test, s), ac.TRAMOS_AMPLIOS)
    return {"dataset_sha256": dataset["sha256"], "rho": rho, "entreno": list(ENTRENO),
            "partidos_entreno": int(len(train)), "partidos_medida": int(len(test)),
            "proporcion_1t": {"local": round(s[0], 4), "visita": round(s[1], 4)},
            "por_mercado": res,
            "que_pasan": sorted(k for k, v in res.items() if v["pasa"]),
            "que_no_pasan": sorted(k for k, v in res.items() if not v["pasa"])}


if __name__ == "__main__":
    ap_ = argparse.ArgumentParser(description="Prueba histórica de la 1ª mitad")
    ap_.add_argument("--rho", type=float, default=ac.RHO_POR_DEFECTO)
    ap_.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    print(json.dumps(run(ap_.parse_args().rho, ap_.parse_args().cache), indent=2, ensure_ascii=False))
