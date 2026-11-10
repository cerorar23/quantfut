"""
T11 (2026-11-09): ¿una dispersión φ propia por árbitro mejora las tarjetas?

`tarjetas_arbitro.py` (10-oct) midió el árbitro en la MEDIA: mejora la pérdida
logarítmica solo 0,0011 por partido. Aquí se mide la otra mitad: el motor C usa
un φ único (`PARAMETROS["cards"]["phi"]`). Variante: φ_r = (S_r + K·φ)/(M_r + K),
con S_r = Σ(y-μ)² y M_r = Σμ de los partidos ANTERIORES del árbitro (misma
definición de φ del motor: varianza/media), contraído hacia el φ global con
peso K en «tarjetas esperadas». Parámetros del motor sin retocar; K se elige
con la temporada de ajuste y se juzga en las de prueba, con el mismo recorrido
sin fugas de `tarjetas_arbitro`. Criterio fijado antes de ver el resultado: la
variante entra solo si la mejora de pérdida de prueba tiene el IC95 por
bootstrap de partidos ENTERO por encima de cero.

Uso: python -m qf.eval.tarjetas_dispersion_arbitro [--cache .local/fd_cache]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from ..model import estadisticas_mercado as em
from . import escalera_estadistica as ee
from . import soft_vs_sharp as sv
from .tarjetas_arbitro import LIGAS, LINEAS

KS = (100.0, 300.0, 1000.0)
REPLICAS = 2000


def partidos(raw: pd.DataFrame) -> pd.DataFrame:
    """media del motor (con árbitro, parámetros de producción) y conteo, sin fugas."""
    p = em.PARAMETROS["cards"]
    out = []
    for div, liga in ee._partidos(raw).groupby("Div"):
        a = em.Acumulador(usar_arbitro=True, prior=p["prior"], media_vida=p["media_vida"])
        for d in liga.to_dict("records"):
            c = ee._conteos(d, "cards")
            if c is None:
                continue
            arb = d.get("Referee") if isinstance(d.get("Referee"), str) else None
            lam = a.lambdas(d["fecha"], d["HomeTeam"], d["AwayTeam"], arb)
            if lam is not None:
                out.append({"temporada": d["temporada"], "fecha": d["fecha"], "arbitro": arb,
                            "media": lam[0] + lam[1], "total": c[0] + c[1]})
            a.agregar(d["fecha"], d["HomeTeam"], d["AwayTeam"], c[0], c[1], arb)
    return pd.DataFrame(out).sort_values("fecha").reset_index(drop=True)


def perdidas(m: pd.DataFrame, k: float | None) -> np.ndarray:
    """Pérdida media sobre `LINEAS` por partido; `k` None = φ global del motor."""
    phi_g = em.PARAMETROS["cards"]["phi"]
    s, mu = defaultdict(float), defaultdict(float)
    out = np.empty(len(m))
    for i, r in enumerate(m.itertuples()):
        phi = phi_g
        if k is not None and r.arbitro:
            phi = max((s[r.arbitro] + k * phi_g) / (mu[r.arbitro] + k), 1.0001)
        ps = [min(max(em.prob_total(r.media, phi, l)["over"], 1e-6), 1 - 1e-6) for l in LINEAS]
        out[i] = np.mean([-np.log(p if r.total > l else 1 - p) for p, l in zip(ps, LINEAS)])
        if r.arbitro:                      # se aprende DESPUÉS de predecir
            s[r.arbitro] += (r.total - r.media) ** 2
            mu[r.arbitro] += r.media
    return out


def run(cache: Path) -> dict:
    raw, dataset = sv.load_csvs(LIGAS, sv.DEFAULT_SEASONS, cache)
    raw = raw.copy()
    raw["temporada"] = raw["season"]
    m = partidos(raw)
    base = perdidas(m, None)
    ajuste = (m["temporada"].isin(ee.TEMPORADA_AJUSTE)).to_numpy()
    prueba = (~m["temporada"].isin(ee.TEMPORADAS_PHI + ee.TEMPORADA_AJUSTE)).to_numpy()
    cand = {k: perdidas(m, k) for k in KS}
    k_ok = min(KS, key=lambda k: cand[k][ajuste].mean())
    d = (base - cand[k_ok])[prueba]                          # > 0: gana la variante
    rng = np.random.default_rng(7)
    medias = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(REPLICAS)]
    lo, hi = (float(v) for v in np.percentile(medias, [2.5, 97.5]))
    return {"dataset_sha256": dataset["sha256"], "partidos_prueba": int(prueba.sum()),
            "K_elegido": k_ok, "perdida_prueba_global": round(float(base[prueba].mean()), 5),
            "perdida_prueba_variante": round(float(cand[k_ok][prueba].mean()), 5),
            "mejora": round(float(d.mean()), 5), "mejora_ic95": [round(lo, 5), round(hi, 5)],
            "entra": lo > 0}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    print(json.dumps(run(ap.parse_args().cache), indent=1, ensure_ascii=False))
