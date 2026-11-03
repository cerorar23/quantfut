"""Mercados de equipo derivados de UN marcador simulado (coherentes por construcción: fichas 27 y 28)."""
from typing import Literal

import numpy as np

from .nucleo import Marcador

Lado = Literal["local", "visit", "over", "under"]


def ganador(m: Marcador, lado: Literal["local", "visit"] = "local") -> float:
    p_local = float(np.mean(m.muestras[:, 0] > m.muestras[:, 1]))
    return p_local if lado == "local" else 1.0 - p_local


def handicap(m: Marcador, linea: float, lado: Literal["local", "visit"] = "local") -> float:
    """P(el lado cubre). `linea` es la del LOCAL (−4,5 = local da 4,5 puntos); el visitante tiene la opuesta.
    En líneas enteras el empate exacto (push) se reparte a mitades, como en `Distribucion.prob_mas_de`."""
    ajustado = m.muestras[:, 0] - m.muestras[:, 1] + linea
    p_local = float(np.mean(ajustado > 0) + 0.5 * np.mean(ajustado == 0))
    return p_local if lado == "local" else 1.0 - p_local


def total(m: Marcador, linea: float, lado: Literal["over", "under"] = "over") -> float:
    suma = m.muestras.sum(axis=1)
    p_over = float(np.mean(suma > linea) + 0.5 * np.mean(suma == linea))
    return p_over if lado == "over" else 1.0 - p_over


def total_equipo(m: Marcador, equipo: Literal["local", "visit"], linea: float, lado: Literal["over", "under"] = "over") -> float:
    pts = m.muestras[:, 0 if equipo == "local" else 1]
    p_over = float(np.mean(pts > linea) + 0.5 * np.mean(pts == linea))
    return p_over if lado == "over" else 1.0 - p_over


def margen_de_victoria(m: Marcador, cortes: tuple[int, ...] = (5, 10, 15)) -> dict[str, float]:
    """Probabilidad del margen del ganador por tramos: «1-5», «6-10», «11-15», «16+»; suma 1."""
    margen = np.abs(m.muestras[:, 0] - m.muestras[:, 1])
    limites = (0,) + cortes + (10_000,)
    nombres = [f"{a + 1}-{b}" for a, b in zip(limites[:-2], limites[1:-1])] + [f"{cortes[-1] + 1}+"]
    return {n: float(np.mean((margen > a) & (margen <= b))) for n, a, b in zip(nombres, limites[:-1], limites[1:])}
