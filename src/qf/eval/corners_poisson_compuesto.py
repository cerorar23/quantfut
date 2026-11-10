"""
T6 (2026-11-09): ¿una Poisson compuesta (Pólya-Aeppli) mejora a la binomial negativa en córners?

Yip y otros (JORS 2024) modelan los córners como Poisson con tamaño de racimo geométrico. Aquí, con la MISMA media del
motor C (parámetros de producción: prior 120, media vida 365) y el MISMO φ (varianza/media = 1,175), solo cambia la
forma de la distribución: binomial negativa (producción) frente a Pólya-Aeppli, cuya media es λ/(1-θ) y cuyo
φ = (1+θ)/(1-θ), es decir θ = (φ-1)/(φ+1). Pérdida logarítmica sobre las líneas medias 7,5 a 12,5 en las temporadas
de prueba (las que no usan φ ni el ajuste), emparejada por partido, IC95 por bootstrap de partidos.
Criterio fijado antes de medir: entra si el IC95 de la mejora queda entero por encima de cero.
No incluye la línea de goles como variable (la otra mitad de la propuesta): requiere ampliar el motor.

Uso: python -m qf.eval.corners_poisson_compuesto [--cache .local/fd_cache]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import gammaln

from ..model import estadisticas_mercado as em
from . import alta_prob_calibracion as apc
from . import escalera_estadistica as ee
from . import soft_vs_sharp as sv

LINEAS = (7.5, 8.5, 9.5, 10.5, 11.5, 12.5)
KMAX = 80
REPLICAS = 2000


def cdf_polya_aeppli(media: float, phi: float, kmax: int = KMAX) -> np.ndarray:
    """P(N <= k) para k = 0..kmax, con media y φ = varianza/media dados."""
    theta = (phi - 1.0) / (phi + 1.0)
    lam = media * (1.0 - theta)
    ks = np.arange(kmax + 1)
    pmf = np.zeros(kmax + 1)
    pmf[0] = np.exp(-lam)
    for k in range(1, kmax + 1):
        j = np.arange(1, k + 1)
        logc = gammaln(k) - gammaln(j) - gammaln(k - j + 1)                    # C(k-1, j-1)
        logt = logc + j * (np.log1p(-theta) + np.log(lam)) + (k - j) * (np.log(theta) if theta > 0 else -np.inf) \
            - gammaln(j + 1)
        pmf[k] = np.exp(-lam) * np.exp(logt[np.isfinite(logt)]).sum()
    return np.cumsum(pmf)


def partidos(raw: pd.DataFrame) -> pd.DataFrame:
    p = em.PARAMETROS["corners"]
    out = []
    for _, liga in ee._partidos(raw).groupby("Div"):
        a = em.Acumulador(prior=p["prior"], media_vida=p["media_vida"])
        for d in liga.to_dict("records"):
            c = ee._conteos(d, "corners")
            if c is None:
                continue
            lam = a.lambdas(d["fecha"], d["HomeTeam"], d["AwayTeam"])
            if lam is not None:
                out.append({"temporada": d["temporada"], "media": lam[0] + lam[1], "total": c[0] + c[1]})
            a.agregar(d["fecha"], d["HomeTeam"], d["AwayTeam"], c[0], c[1])
    return pd.DataFrame(out)


def perdidas(m: pd.DataFrame, phi: float, modelo: str) -> np.ndarray:
    out = np.empty(len(m))
    for i, r in enumerate(m.itertuples()):
        if modelo == "nb":
            p_under = [em.prob_total(r.media, phi, l)["under"] for l in LINEAS]
        else:
            cdf = cdf_polya_aeppli(r.media, phi)
            p_under = [cdf[int(np.floor(l))] for l in LINEAS]
        ps = np.clip(np.array(p_under), 1e-6, 1 - 1e-6)
        out[i] = np.mean([-np.log(1 - p if r.total > l else p) for p, l in zip(ps, LINEAS)])
    return out


def run(cache: Path) -> dict:
    raw, dataset = sv.load_csvs(apc.LIGAS, sv.DEFAULT_SEASONS, cache)
    raw = raw.copy()
    raw["temporada"] = raw["season"]
    m = partidos(raw)
    m = m[~m["temporada"].isin(ee.TEMPORADAS_PHI + ee.TEMPORADA_AJUSTE)].reset_index(drop=True)
    phi = em.PARAMETROS["corners"]["phi"]
    nb, pa = perdidas(m, phi, "nb"), perdidas(m, phi, "pa")
    d = nb - pa                                         # > 0: gana Pólya-Aeppli
    rng = np.random.default_rng(7)
    medias = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(REPLICAS)]
    lo, hi = (float(v) for v in np.percentile(medias, [2.5, 97.5]))
    return {"dataset_sha256": dataset["sha256"], "partidos_prueba": int(len(m)), "phi": phi,
            "perdida_nb": round(float(nb.mean()), 5), "perdida_polya_aeppli": round(float(pa.mean()), 5),
            "mejora": round(float(d.mean()), 5), "mejora_ic95": [round(lo, 5), round(hi, 5)], "entra": lo > 0}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    print(json.dumps(run(ap.parse_args().cache), indent=1, ensure_ascii=False))
