"""Capa de recalibración OPCIONAL (plan D.4, §I G-recalibración): π' = expit(b·logit π).

Sin intercepto: los lados están en orden pseudoaleatorio, así que el intercepto es 0 por construcción (simetría A↔B).
Se ajusta SOLO con temporadas anteriores a la evaluada y se activa solo si su compuerta pasa (IC95 de Δ log-loss < 0).
"""
import numpy as np

EPS = 1e-12


def logit(p):
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p) - np.log1p(-p)


def ajustar_pendiente(p, y, iteraciones: int = 50) -> float:
    """b de máxima verosimilitud de y ~ Bernoulli(expit(b·logit p)) por Newton (1 parámetro)."""
    x, y = logit(p), np.asarray(y, dtype=float)
    b = 1.0
    for _ in range(iteraciones):
        q = 1 / (1 + np.exp(-b * x))
        g, h = np.sum((y - q) * x), np.sum(q * (1 - q) * x * x)
        paso = g / max(h, 1e-12)
        b += paso
        if abs(paso) < 1e-12:
            break
    return float(b)


def aplicar(p, b: float):
    return 1 / (1 + np.exp(-b * logit(p)))


def por_temporada(temporada, p, y, liquida, evaluar, desde: int):
    """Para cada temporada evaluada T: b ajustado con las temporadas desde..T−1 (liquidadas). Devuelve (p', {T: b})."""
    temporada, p, y, liquida = map(np.asarray, (temporada, p, y, liquida))
    out, bs = np.full(len(p), np.nan), {}
    for t in evaluar:
        tr = liquida & (temporada >= desde) & (temporada < t) & np.isfinite(p)
        bs[int(t)] = ajustar_pendiente(p[tr], y[tr])
        sel = temporada == t
        out[sel] = aplicar(p[sel], bs[int(t)])
    return out, bs
