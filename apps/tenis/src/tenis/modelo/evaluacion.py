"""Métricas y protocolo de la línea base (plan §I.0, aud. §6.2): log-loss, Brier, IC95 por bootstrap POR PARTIDO
(2.000 réplicas), orígenes (temporadas) combinados por la inversa de la varianza, calibración conjunta (pendiente e
intercepto de la logística y ~ a + b·logit p) con IC por bootstrap. Nunca una sola temporada.
"""
import numpy as np

from .recalibracion import logit

EPS = 1e-12
REPS = 2000


def perdida(y, p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    y = np.asarray(y, dtype=float)
    return -(y * np.log(p) + (1 - y) * np.log1p(-p))


def brier(y, p):
    return (np.asarray(y, dtype=float) - np.asarray(p, dtype=float)) ** 2


def _medias_bootstrap(x: np.ndarray, rng, reps: int) -> np.ndarray:
    out = np.empty(reps)
    for i0 in range(0, reps, 100):
        k = min(100, reps - i0)
        out[i0:i0 + k] = x[rng.integers(len(x), size=(k, len(x)))].mean(axis=1)
    return out


def dif_bootstrap(y, p_m, p_r, rng, reps: int = REPS) -> dict:
    """Δ log-loss y Δ Brier (modelo − referencia) con IC95 bootstrap por partido y su varianza (para combinar)."""
    dl = perdida(y, p_m) - perdida(y, p_r)
    db = brier(y, p_m) - brier(y, p_r)
    bl, bb = _medias_bootstrap(dl, rng, reps), _medias_bootstrap(db, rng, reps)
    return {"n": int(len(dl)), "dif_logloss": float(dl.mean()), "lo": float(np.quantile(bl, 0.025)),
            "hi": float(np.quantile(bl, 0.975)), "var": float(bl.var()), "dif_brier": float(db.mean()),
            "brier_lo": float(np.quantile(bb, 0.025)), "brier_hi": float(np.quantile(bb, 0.975)), "var_brier": float(bb.var())}


def combinar(filas: list) -> dict:
    """Inversa de la varianza sobre orígenes (temporadas)."""
    if not filas:
        return {}
    w = np.array([1 / max(f["var"], 1e-14) for f in filas])
    m = float(np.dot(w, [f["dif_logloss"] for f in filas]) / w.sum()); se = float(np.sqrt(1 / w.sum()))
    wb = np.array([1 / max(f["var_brier"], 1e-14) for f in filas])
    mb = float(np.dot(wb, [f["dif_brier"] for f in filas]) / wb.sum()); seb = float(np.sqrt(1 / wb.sum()))
    return {"origenes": len(filas), "n": int(sum(f["n"] for f in filas)), "dif_logloss": m, "lo": m - 1.96 * se,
            "hi": m + 1.96 * se, "dif_brier": mb, "brier_lo": mb - 1.96 * seb, "brier_hi": mb + 1.96 * seb}


def por_origen(temporada, y, p_m, p_r, rng, reps: int = REPS) -> dict:
    temporada = np.asarray(temporada)
    filas = []
    for t in np.unique(temporada):
        s = temporada == t
        if s.sum() >= 50:
            filas.append({"temporada": int(t)} | dif_bootstrap(np.asarray(y)[s], np.asarray(p_m)[s], np.asarray(p_r)[s], rng, reps))
    return {"combinado": combinar(filas), "por_temporada": filas}


def logistica(x, y, iteraciones: int = 30) -> tuple[float, float]:
    """(intercepto, pendiente) de y ~ Bernoulli(expit(a + b·x)) por Newton."""
    a, b = 0.0, 1.0
    for _ in range(iteraciones):
        q = 1 / (1 + np.exp(-(a + b * x)))
        w = q * (1 - q)
        g = np.array([np.sum(y - q), np.sum((y - q) * x)])
        h = np.array([[w.sum(), np.dot(w, x)], [np.dot(w, x), np.dot(w, x * x)]])
        paso = np.linalg.solve(h, g)
        a, b = a + paso[0], b + paso[1]
        if np.max(np.abs(paso)) < 1e-10:
            break
    return float(a), float(b)


def calibracion(y, p, rng, reps: int = REPS) -> dict:
    x, y = logit(p), np.asarray(y, dtype=float)
    a, b = logistica(x, y)
    bs = np.array([logistica(x[i], y[i], 12) for i in (rng.integers(len(y), size=len(y)) for _ in range(reps))])
    return {"n": int(len(y)), "pendiente": b, "pend_lo": float(np.quantile(bs[:, 1], 0.025)),
            "pend_hi": float(np.quantile(bs[:, 1], 0.975)), "intercepto": a,
            "int_lo": float(np.quantile(bs[:, 0], 0.025)), "int_hi": float(np.quantile(bs[:, 0], 0.975))}


def metricas(y, p) -> dict:
    return {"n": int(len(y)), "logloss": float(perdida(y, p).mean()), "brier": float(brier(y, p).mean()),
            "acierto": float(np.mean((np.asarray(p) >= 0.5) == (np.asarray(y) == 1)))}
