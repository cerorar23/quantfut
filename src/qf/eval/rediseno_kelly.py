"""
Del pronóstico a la apuesta, solo como DIAGNÓSTICO (el producto publica probabilidades; los picks de valor están
apagados): Kelly fraccional contra el cierre real (Vélez Jiménez et al. 2026; KellyBench 2026) y la mezcla con el
mercado de Benter, con el peso estimado cada semana solo con el pasado.

Regla de Kelly por partido (tres resultados excluyentes): se apuesta, como mucho, al resultado de mayor ventaja
p·o − 1 > 0, con la fracción `fraccion` del Kelly simple (p·o − 1)/(o − 1). Las apuestas de una semana se pagan
juntas y se reinvierte; la exposición semanal se limita a `tope`.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import blend_logit


def kelly_semana(p: np.ndarray, cuota: np.ndarray, fraccion: float = 0.25) -> np.ndarray:
    """Fracción del capital por partido y resultado (n, 3)."""
    p = np.asarray(p, float); o = np.asarray(cuota, float)
    ventaja = p * o - 1
    k = ventaja.argmax(1)
    f = np.zeros_like(p)
    fila = np.arange(len(p))
    ok = ventaja[fila, k] > 0
    f[fila[ok], k[ok]] = fraccion * ventaja[fila[ok], k[ok]] / (o[fila[ok], k[ok]] - 1)
    return f


def simular(df: pd.DataFrame, probs: pd.DataFrame, fraccion: float = 0.25, tope: float = 0.5,
            reps: int = 2000, semilla: int = 0) -> dict:
    """Capital final, rentabilidad sobre lo apostado e IC95 por bootstrap de semanas (sin reinversión en el IC)."""
    x = df.merge(probs, on="match_id").dropna(subset=["odd_home", "odd_draw", "odd_away", "p_home"])
    x = x.sort_values("kickoff_utc")
    capital, apostado, ganancia_sem = 1.0, 0.0, []
    for _, g in x.groupby("semana", sort=False):
        f = kelly_semana(g[["p_home", "p_draw", "p_away"]].to_numpy(), g[["odd_home", "odd_draw", "odd_away"]].to_numpy(),
                         fraccion)
        total = f.sum()
        if total > tope:
            f *= tope / total
        o = g[["odd_home", "odd_draw", "odd_away"]].to_numpy(); y = g["outcome"].to_numpy(int)
        gana = f[np.arange(len(g)), y] * o[np.arange(len(g)), y]
        neto = gana.sum() - f.sum()  # en fracción del capital
        ganancia_sem.append((f.sum(), neto))
        apostado += f.sum() * capital
        capital *= 1 + neto
    s = np.array(ganancia_sem)
    rng = np.random.default_rng(semilla)
    idx = rng.integers(0, len(s), (reps, len(s)))
    roi_b = s[idx, 1].sum(1) / np.clip(s[idx, 0].sum(1), 1e-12, None)
    return {"capital_final": capital, "apuestas_semanas": int((s[:, 0] > 0).sum()),
            "roi_sobre_apostado": float(s[:, 1].sum() / max(s[:, 0].sum(), 1e-12)),
            "roi_ic95": (float(np.quantile(roi_b, 0.025)), float(np.quantile(roi_b, 0.975)))}


def mezcla_benter(pred: pd.DataFrame, df: pd.DataFrame, modelo: str, nuevo: str, minimo: int = 600) -> pd.DataFrame:
    """Modelo y mercado mezclados en logit con el peso que minimiza el log-loss de las semanas ANTERIORES."""
    x = pred[pred["modelo"] == modelo].merge(df[["match_id", "kickoff_utc", "semana", "outcome", "mk_home", "mk_draw",
                                                 "mk_away"]], on="match_id").dropna(subset=["mk_home"])
    x = x.sort_values("kickoff_utc")
    rejilla = np.linspace(0, 1, 21)
    filas = []
    for _, g in x.groupby("semana", sort=False):
        antes = x[x["kickoff_utc"] < g["kickoff_utc"].min()]
        if len(antes) < minimo:
            continue
        mp, kp = antes[["p_home", "p_draw", "p_away"]].to_numpy(), antes[["mk_home", "mk_draw", "mk_away"]].to_numpy()
        y = antes["outcome"].to_numpy(int)
        ll = [-np.log(blend_logit(mp, kp, w)[np.arange(len(y)), y]).mean() for w in rejilla]
        w = rejilla[int(np.argmin(ll))]
        pm = blend_logit(g[["p_home", "p_draw", "p_away"]].to_numpy(), g[["mk_home", "mk_draw", "mk_away"]].to_numpy(), w)
        filas.append(pd.DataFrame({"match_id": g["match_id"].to_numpy(), "modelo": nuevo, "p_home": pm[:, 0],
                                   "p_draw": pm[:, 1], "p_away": pm[:, 2], "w_modelo": w}))
    return pd.concat(filas, ignore_index=True)
