"""Evaluación única (fichas 5, 34, 64): todas las métricas de los sprints salen de aquí, con intervalos y contra una línea base.

Los scripts de `apps/nba/ops/evaluar_s*.py` importan estas funciones; ninguno define sus propias métricas.
"""
from collections.abc import Mapping

import numpy as np

from .props import pit_aleatorio


def rmse(a, b) -> float:
    return float(np.sqrt(np.mean((np.asarray(a, float) - np.asarray(b, float)) ** 2)))


def brier(p, y) -> float:
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def logloss(p, y) -> float:
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def pendiente_calibracion(p, y) -> tuple[float, float]:
    """Regresión logística de y sobre logit(p) (Newton): pendiente 1 e intercepto 0 = calibrado."""
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    x = np.log(p / (1 - p))
    y = np.asarray(y, float)
    b = np.array([0.0, 1.0])
    for _ in range(50):
        q = 1 / (1 + np.exp(-(b[0] + b[1] * x)))
        w = q * (1 - q)
        g = np.array([np.sum(y - q), np.sum((y - q) * x)])
        h = np.array([[np.sum(w), np.sum(w * x)], [np.sum(w * x), np.sum(w * x * x)]])
        paso = np.linalg.solve(h + 1e-9 * np.eye(2), g)
        b += paso
        if np.abs(paso).max() < 1e-9:
            break
    return float(b[1]), float(b[0])


def ic_diferencia(p_a, p_b, y, n: int = 2000, semilla: int = 0, grupos=None) -> tuple[float, float, float]:
    """Brier(A) − Brier(B), remuestreando grupos completos y preservando el estimando por observación."""
    p_a, p_b, y = (np.asarray(v, float) for v in (p_a, p_b, y))
    if p_a.ndim != 1 or p_a.shape != p_b.shape or p_a.shape != y.shape or not len(y):
        raise ValueError("observaciones incompatibles")
    if grupos is None:
        raise ValueError("se requiere declarar la unidad independiente en grupos")
    grupos = np.asarray(grupos)
    if grupos.shape != y.shape or n < 2:
        raise ValueError("grupos de remuestreo incompatibles")
    if not np.isfinite([p_a, p_b, y]).all() or (p_a < 0).any() or (p_a > 1).any() or (p_b < 0).any() or (p_b > 1).any():
        raise ValueError("probabilidades inválidas")
    d = (p_a - y) ** 2 - (p_b - y) ** 2
    _, indice = np.unique(grupos, return_inverse=True)
    k = int(indice.max()) + 1
    if k < 2:
        raise ValueError("al menos dos grupos independientes para estimar incertidumbre")
    total, cuenta = np.bincount(indice, weights=d), np.bincount(indice)
    rng = np.random.default_rng(semilla)
    medias = np.empty(n)
    for i in range(n):
        seleccion = rng.integers(0, k, k)
        medias[i] = total[seleccion].sum() / cuenta[seleccion].sum()
    return float(d.mean()), float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5))


def informe_binario(p, y, base=None, estratos: Mapping[str, np.ndarray] | None = None, grupos=None) -> dict:
    """Brier, log-pérdida y calibración de P(y=1); con `base` (probabilidades de referencia) añade la diferencia con su intervalo;
    con `estratos` ({nombre: etiqueta por fila}) repite Brier y n por estrato."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    pend, inter = pendiente_calibracion(p, y)
    r = {"n": int(len(y)), "brier": brier(p, y), "logloss": logloss(p, y), "pendiente": pend, "intercepto": inter,
         "tasa_observada": float(y.mean()), "prob_media": float(p.mean())}
    if base is not None:
        d, lo, hi = ic_diferencia(p, base, y, grupos=grupos)
        r["base"] = {"brier": brier(base, y), "logloss": logloss(base, y)}
        r["dif_brier"], r["dif_ic95"] = d, [lo, hi]
        r["grupos_independientes"] = len(np.unique(grupos))
    if estratos:
        r["estratos"] = {}
        for nombre, etiquetas in estratos.items():
            etiquetas = np.asarray(etiquetas)
            r["estratos"][nombre] = {str(e): {"n": int((etiquetas == e).sum()), "brier": brier(p[etiquetas == e], y[etiquetas == e])}
                                     for e in np.unique(etiquetas)}
    return r


def informe_conteo(pmf, y, base_media, semilla: int = 0) -> dict:
    """Distribuciones de conteo (R, techo+1) contra lo observado: cobertura 80/50 con PIT aleatorizado, MASE contra la media base
    y regresión de Mincer-Zarnowitz (y sobre la media del pronóstico: pendiente 1 e intercepto 0 = sin sesgo)."""
    pmf, y, base_media = np.asarray(pmf, float), np.asarray(y, float), np.asarray(base_media, float)
    media = (pmf * np.arange(pmf.shape[1])).sum(axis=1) / pmf.sum(axis=1)
    pit = pit_aleatorio(pmf, y, semilla)
    pendiente, intercepto = np.polyfit(media, y, 1)
    return {"n": int(len(y)), "cobertura80": float(np.mean((pit > 0.1) & (pit < 0.9))), "cobertura50": float(np.mean((pit > 0.25) & (pit < 0.75))),
            "MASE": float(np.abs(y - media).mean() / np.abs(y - base_media).mean()),
            "mincer_zarnowitz": {"pendiente": float(pendiente), "intercepto": float(intercepto)}}
