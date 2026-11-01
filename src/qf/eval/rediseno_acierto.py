"""
Objetivo del producto según el titular (1-nov-2026): **no ganar al mercado, sino publicar el pronóstico con mayor
probabilidad de acertar** y que el porcentaje anunciado sea verdad. Este módulo mide exactamente eso:

- `seleccion_diaria`: cada día se publica el `cobertura` más probable de cada fuente; se mide cuántos aciertan y
  cuánto se anunció (si se anunció 78 % y acertó 71 %, la fuente es mala aunque acierte mucho).
- `calibracion_alta`: en las probabilidades altas (0,6–1), ¿lo anunciado coincide con lo observado?

Una «opción» es cualquier pronóstico publicable de un partido (local, doble oportunidad, más de 2,5, más de 8,5
córners…). El mercado sin margen es una fuente más: si es la más fiable, se usa.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def mas_probable(p: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(p, float)
    k = p.argmax(1)
    return p[np.arange(len(p)), k], k


def wilson(aciertos: float, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    f = aciertos / n
    centro = (f + z * z / (2 * n)) / (1 + z * z / n)
    radio = z * np.sqrt(f * (1 - f) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centro - radio, centro + radio)


def seleccion_diaria(c: pd.DataFrame, coberturas=(0.05, 0.1, 0.2, 0.3, 0.5, 1.0)) -> pd.DataFrame:
    """`c`: una fila por opción candidata con `dia`, `prob` y `acierto` (0/1). Por cada día se toma el top `cobertura`."""
    c = c.dropna(subset=["prob", "acierto"]).copy()
    c["rango"] = c.groupby("dia")["prob"].rank(ascending=False, method="first")
    c["n_dia"] = c.groupby("dia")["prob"].transform("size")
    filas = []
    for cob in coberturas:
        sel = c[c["rango"] <= np.ceil(cob * c["n_dia"])]
        n, a = len(sel), float(sel["acierto"].sum())
        bajo, alto = wilson(a, n)
        filas.append({"cobertura": cob, "n": n, "acierto": a / n if n else np.nan, "ic95_bajo": bajo,
                      "ic95_alto": alto, "anunciado": sel["prob"].mean(),
                      "promesa_incumplida": sel["prob"].mean() - (a / n if n else np.nan)})
    return pd.DataFrame(filas)


def calibracion_alta(prob: np.ndarray, acierto: np.ndarray, cortes=(0.6, 0.7, 0.8, 0.9, 1.0001)) -> pd.DataFrame:
    prob, acierto = np.asarray(prob, float), np.asarray(acierto, float)
    filas = []
    for lo, hi in zip(cortes[:-1], cortes[1:]):
        m = (prob >= lo) & (prob < hi)
        n = int(m.sum())
        if n:
            bajo, alto = wilson(acierto[m].sum(), n)
            filas.append({"tramo": f"{lo:.1f}-{min(hi, 1):.1f}", "n": n, "anunciado": prob[m].mean(),
                          "observado": acierto[m].mean(), "ic95_bajo": bajo, "ic95_alto": alto})
    return pd.DataFrame(filas)
