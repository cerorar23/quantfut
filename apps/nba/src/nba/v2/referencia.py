"""Referencia del mercado (fichas 5, 22, 23, 67): cuotas decimales → probabilidades sin margen.

Solo es una comparación y un ancla opcional; el método elegido se registra en `version_modelo` del pronóstico, no en la cuota.
Una referencia pública nunca sale de [10 %, 90 %] (ficha 16).
"""
from collections.abc import Sequence
from typing import Literal

import numpy as np

Metodo = Literal["proporcional", "potencia", "shin"]
METODOS: tuple[Metodo, ...] = ("proporcional", "potencia", "shin")


def _bisecar(f, lo: float, hi: float, iteraciones: int = 80) -> float:
    """Raíz de una función monótona decreciente con f(lo) >= 0 >= f(hi)."""
    for _ in range(iteraciones):
        medio = (lo + hi) / 2
        lo, hi = (medio, hi) if f(medio) > 0 else (lo, medio)
    return (lo + hi) / 2


def quitar_margen(cuotas: Sequence[float], metodo: Metodo = "proporcional") -> list[float]:
    """Probabilidades que suman 1 a partir de las cuotas de todos los resultados de un mercado.

    * proporcional: reparte el margen en proporción a la probabilidad implícita.
    * potencia: eleva las implícitas a k ≥ 1 hasta sumar 1 (carga más margen en los resultados improbables).
    * shin: modelo de Shin (1993) con proporción z de apostadores informados.
    """
    if len(cuotas) < 2 or any(c <= 1.0 for c in cuotas):
        raise ValueError("hacen falta al menos dos cuotas decimales mayores que 1")
    q = np.array([1.0 / c for c in cuotas])
    suma = q.sum()
    if metodo == "proporcional":
        p = q / suma
    elif metodo == "potencia":
        if suma <= 1.0:
            p = q / suma
        else:
            k = _bisecar(lambda k: (q ** k).sum() - 1.0, 1.0, 60.0)
            p = q ** k
    elif metodo == "shin":
        if suma <= 1.0:
            p = q / suma
        else:
            def prob(z):
                return (np.sqrt(z * z + 4 * (1 - z) * q * q / suma) - z) / (2 * (1 - z))
            z = _bisecar(lambda z: prob(z).sum() - 1.0, 0.0, 0.999)
            p = prob(z)
            p = p / p.sum()
    else:
        raise ValueError(f"método desconocido: {metodo}")
    return p.tolist()


def limitar_publicacion(p: float, minimo: float = 0.10, maximo: float = 0.90) -> float:
    """Una referencia pública no se muestra fuera de [10 %, 90 %]."""
    return min(max(p, minimo), maximo)
