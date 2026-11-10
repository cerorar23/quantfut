"""Paso 1 del plan de calibración (2026-11-09): ¿una pendiente de calibración por segmento arregla el 0,90 de ATP?

Uso: python apps/tenis/ops/evaluar_recal_segmentos.py [--circuito atp] [--reps 2000]
Diagnóstico previo (evaluacion_filas.parquet, ATP 2019-2024): la pendiente de π es 0,902 y la de la capa actual
(`pi_recal`) 0,935. Falla sobre todo en Challenger (0,84) y en historia corta < 20 partidos (0,81); en Grand Slam (1,17)
y mejor de 5 (1,21) el modelo es TÍMIDO. Candidatas: p = expit(b_celda · logit π), con b_celda ajustada por máxima
verosimilitud SOLO con temporadas anteriores (hacia adelante, desde 2021, con 2019-2020 como primer entrenamiento):
  A = celdas {Challenger, resto} × {historia < 20, ≥ 20}; B = A + celda de mejor de 5.
Base de comparación: `pi_recal` (lo que hoy sale). Criterio fijado antes de medir: la candidata entra si la mejora de
pérdida logarítmica tiene el IC95 (bootstrap por día) entero bajo cero, el ECE no empeora y la pendiente global del
conjunto de prueba (2021-2024) incluye 1 en su IC95. La reserva 2025-26 no se lee.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

RUTA = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\modelo_s3\evaluacion_filas.parquet")
EPS = 1e-6


def logit(p):
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def expit(z):
    return 1 / (1 + np.exp(-z))


def pendiente_cero(x, y, b0=1.0):
    """Pendiente b de P(y)=expit(b·x) por Newton (sin intercepto: el diagnóstico mostró intercepto ≈ 0)."""
    b = b0
    for _ in range(40):
        p = expit(b * x)
        g, h = (x * (y - p)).sum(), (x * x * p * (1 - p)).sum()
        if h <= 0:
            break
        b += g / h
    return float(b)


def logistica(x, y):
    X = np.c_[np.ones(len(x)), x]
    b = np.zeros(2)
    for _ in range(30):
        p = expit(X @ b)
        H = X.T @ (X * (p * (1 - p))[:, None])
        b = b + np.linalg.solve(H, X.T @ (y - p))
    return b, np.sqrt(np.diag(np.linalg.inv(H)))


def perdida(p, y):
    p = np.clip(p, EPS, 1 - EPS)
    return -(y * np.log(p) + (1 - y) * np.log1p(-p))


def ece(p, y, bins=10):
    conf, hit = np.where(p >= 0.5, p, 1 - p), (y == 1) == (p >= 0.5)
    idx = np.minimum((conf * bins).astype(int), bins - 1)
    return float(sum(abs(hit[idx == k].mean() - conf[idx == k].mean()) * (idx == k).mean()
                     for k in range(bins) if (idx == k).any()))


def celdas(g: pd.DataFrame, esquema: str) -> np.ndarray:
    c = np.where(g.categoria == "Challenger", "Ch", "Ot") + np.where(g.n_prev_min < 20, "_corta", "_larga")
    if esquema == "B":
        c = np.where(g.mejor_de.astype(str) == "5", "Bo5", c)
    return c


def ic_dia(diff, dias, reps, rng):
    _, inv = np.unique(dias, return_inverse=True)
    k = inv.max() + 1
    s, n = np.bincount(inv, weights=diff, minlength=k), np.bincount(inv, minlength=k)
    m = [s[j].sum() / n[j].sum() for j in (rng.integers(0, k, k) for _ in range(reps))]
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--circuito", default="atp")
    ap.add_argument("--reps", type=int, default=2000)
    a = ap.parse_args()
    f = pd.read_parquet(RUTA)
    f = f[(f.circuito == a.circuito) & f.liquida & f.pi_lado1.notna() & (f.temporada <= 2024)].copy()
    f["y"] = f.y1.astype(float)
    f["dia"] = f.corte_ns // (86400 * 10**9)
    rng = np.random.default_rng(20261109)
    informe = {"circuito": a.circuito}
    for esq in ("A", "B"):
        cand = np.full(len(f), np.nan)
        celda = celdas(f, esq)
        pendientes = {}
        for t in range(2021, 2025):
            tr, te = (f.temporada < t).to_numpy(), (f.temporada == t).to_numpy()
            for c in np.unique(celda):
                m = tr & (celda == c)
                b = pendiente_cero(logit(f.pi_lado1.to_numpy()[m]), f.y.to_numpy()[m]) if m.sum() >= 500 else 1.0
                pendientes[f"{t}:{c}"] = round(b, 3)
                mt = te & (celda == c)
                cand[mt] = expit(b * logit(f.pi_lado1.to_numpy()[mt]))
        s = f.temporada >= 2021
        y, base, nuevo = f.y[s].to_numpy(), f.pi_recal[s].to_numpy(), cand[s.to_numpy()]
        diff = perdida(nuevo, y) - perdida(base, y)
        lo, hi = ic_dia(diff, f.dia[s].to_numpy(), a.reps, rng)
        b_glob, se = logistica(logit(nuevo), y)
        informe[esq] = {"n_prueba": int(s.sum()), "logloss_base": round(float(perdida(base, y).mean()), 5),
                        "logloss_candidata": round(float(perdida(nuevo, y).mean()), 5),
                        "dif": round(float(diff.mean()), 5), "ic95": [round(lo, 5), round(hi, 5)],
                        "ece_base": round(ece(base, y), 5), "ece_candidata": round(ece(nuevo, y), 5),
                        "pendiente_candidata": round(float(b_glob[1]), 3),
                        "pendiente_ic95": [round(float(b_glob[1] - 1.96 * se[1]), 3), round(float(b_glob[1] + 1.96 * se[1]), 3)],
                        "pendientes_celda_2024": {k.split(":")[1]: v for k, v in pendientes.items() if k.startswith("2024")}}
        bb, sb = logistica(logit(base), y)
        informe["pendiente_base_2021_2024"] = round(float(bb[1]), 3)
        informe[esq]["entra"] = bool(hi < 0 and informe[esq]["ece_candidata"] <= informe[esq]["ece_base"]
                                     and informe[esq]["pendiente_ic95"][0] <= 1 <= informe[esq]["pendiente_ic95"][1])
    print(json.dumps(informe, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
