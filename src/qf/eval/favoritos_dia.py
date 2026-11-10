"""
Diagnóstico (2026-11-09): ¿los favoritos de un mismo día fallan juntos más de
lo que dice el azar?

Decide si hace falta limitar patas por tipo de pick o por día en el parley
(propuesta de «clústeres de varianza»). Con p calibrada y partidos
independientes, las derrotas de un día suman media Σ(1-p) y varianza Σp(1-p).
El estadístico de dispersión Z = Σ_d (F_d - E_d)² / Σ_d V_d vale 1 si los
partidos del día son independientes; Z > 1 es correlación positiva entre
fallos. El valor p sale de simular los resultados con las propias p.

football-data, 7 ligas, 2019-2025, favorito 1X2 (Pinnacle sin margen).
Uso: python -m qf.eval.favoritos_dia [--cache .local/fd_cache] [--pmin 0.55]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import alta_prob_calibracion as apc
from . import soft_vs_sharp as sv
from .escalera_prueba import candidatos

SIMULACIONES = 2000


def dispersion(grupo: np.ndarray, p: np.ndarray, falla: np.ndarray) -> float:
    """Z de dispersión de fallos por grupo (día o semana)."""
    _, inv = np.unique(grupo, return_inverse=True)
    k = inv.max() + 1
    f = np.bincount(inv, weights=falla.astype(float), minlength=k)
    e = np.bincount(inv, weights=1 - p, minlength=k)
    v = np.bincount(inv, weights=p * (1 - p), minlength=k)
    return float(((f - e) ** 2).sum() / v.sum())


def evaluar(c: pd.DataFrame, pmin: float, seed: int = 11) -> dict:
    c = c[(c["market"] == "h2h") & (c["p"] >= pmin)]
    c = c.loc[c.groupby("evento")["p"].idxmax()]          # un favorito por partido
    p, falla = c["p"].to_numpy(), (~c["won"]).to_numpy()
    rng = np.random.default_rng(seed)
    out = {"pmin": pmin, "n": int(len(c)), "fallos_pct": round(float(falla.mean()) * 100, 2),
           "prometido_fallo_pct": round(float((1 - p).mean()) * 100, 2)}
    for nombre, grupo in (("dia", c["fecha"].dt.date.astype(str)),
                          ("semana", c["fecha"].dt.strftime("%G-%V"))):
        g = grupo.to_numpy()
        z = dispersion(g, p, falla)
        sim = np.array([dispersion(g, p, rng.uniform(size=len(p)) >= p)
                        for _ in range(SIMULACIONES)])
        out[nombre] = {"Z": round(z, 4), "Z_azar_p2.5_p97.5": [round(float(v), 4) for v in
                       np.percentile(sim, [2.5, 97.5])],
                       "valor_p": round(float((sim >= z).mean()), 4)}
    return out


def run(cache: Path, pmin: float) -> dict:
    raw, dataset = sv.load_csvs(apc.LIGAS, sv.DEFAULT_SEASONS, cache)
    c = candidatos(raw, 1.01, 10.0)
    return {"dataset": dataset, **evaluar(c, pmin)}


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    a.add_argument("--pmin", type=float, default=0.55)
    args = a.parse_args()
    print(json.dumps(run(args.cache, args.pmin), ensure_ascii=False, indent=1))
