"""Minutos de un jugador (fichas 9, 11, 18, 58): pronóstico puntual con decaimiento + residuos calibrados + masa en cero.

* Punto: media ponderada de sus últimos partidos jugados con peso `DECAIMIENTO` por partido hacia atrás. Los parámetros
  salen de medir el error en las temporadas 2023-24 y 2024-25 (ver docs/nba_rediseno_s2_resultados_20261102.md): con 0,70
  el error absoluto baja ≈ 3 % frente a la media de los últimos 5 partidos, estable en tres temporadas.
* Incertidumbre: cuantiles de los residuos (real - pronóstico) de temporadas anteriores, por tramo de minutos esperados;
  así la cobertura de los intervalos se calibra sola y la dispersión crece con los minutos esperados, como indica la ficha 58.
* No juega: con probabilidad `1 - p_juega` (capa de disponibilidad) la distribución pone 0 minutos.

Solo usa minutos de partidos ANTERIORES del propio jugador; la salida temprana y las entradas tardías ya están en sus residuos.
"""
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np

from .distribucion import Distribucion

MIN_PARTIDOS = 5          # sin esto no hay base para estimar minutos
VENTANA = 20              # partidos jugados que se consideran
DECAIMIENTO = 0.70        # peso de cada partido respecto del siguiente más reciente
CORTES = (15.0, 25.0)     # tramos de minutos esperados: < 15, 15-25, >= 25
N_CUANTILES = 99
MAXIMO = 60.0             # con prórrogas largas nadie pasa de aquí


@dataclass(frozen=True)
class Residuos:
    cortes: tuple[float, ...]
    cuantiles: tuple[np.ndarray, ...]       # por tramo: N_CUANTILES residuos ordenados (real - pronóstico)


def jugados_validos(jugados: Sequence[float | None]) -> list[float]:
    return [m for m in jugados if m is not None and m > 0]


def punto(jugados: Sequence[float | None], ventana: int = VENTANA, decaimiento: float = DECAIMIENTO) -> float | None:
    """Minutos esperados si juega; `jugados` va de más antiguo a más reciente. None si hay poca historia."""
    recientes = jugados_validos(jugados)[-ventana:]
    if len(recientes) < MIN_PARTIDOS:
        return None
    pesos = decaimiento ** np.arange(len(recientes) - 1, -1, -1)
    return float(np.dot(recientes, pesos) / pesos.sum())


def media_ultimos(jugados: Sequence[float | None], n: int = 5) -> float | None:
    """Línea base ingenua obligatoria (ficha 10): media de los últimos n partidos jugados."""
    recientes = jugados_validos(jugados)[-n:]
    return float(np.mean(recientes)) if len(recientes) >= min(n, MIN_PARTIDOS) else None


def tramo(pronostico: float, cortes: Sequence[float] = CORTES) -> int:
    return int(sum(pronostico >= c for c in cortes))


def ajustar_residuos(pares: Iterable[tuple[float, float]], cortes: Sequence[float] = CORTES) -> Residuos:
    """[(pronóstico, real)] de temporadas anteriores → cuantiles de residuo por tramo."""
    por_tramo: list[list[float]] = [[] for _ in range(len(cortes) + 1)]
    for pron, real in pares:
        por_tramo[tramo(pron, cortes)].append(real - pron)
    todos = [r for t in por_tramo for r in t]
    if not todos:
        raise ValueError("sin pares para ajustar residuos")
    niveles = (np.arange(N_CUANTILES) + 0.5) / N_CUANTILES
    return Residuos(tuple(cortes), tuple(np.quantile(t if len(t) >= 200 else todos, niveles) for t in por_tramo))


def condicionada(jugados: Sequence[float | None], residuos: Residuos) -> Distribucion | None:
    """Distribución de los minutos si juega."""
    p = punto(jugados)
    if p is None:
        return None
    muestras = np.clip(p + residuos.cuantiles[tramo(p, residuos.cortes)], 0.0, MAXIMO)
    return Distribucion.de_muestras(muestras)


def prediccion(jugados: Sequence[float | None], p_juega: float, residuos: Residuos) -> Distribucion | None:
    """Mezcla: con probabilidad 1 - p_juega no juega (0 minutos), con p_juega los minutos condicionados."""
    base = condicionada(jugados, residuos)
    if base is None:
        return None
    p = min(max(p_juega, 0.0), 1.0)
    if p >= 1.0:
        return base
    cero = Distribucion.de_muestras([0.0])
    if p <= 0.0:
        return cero
    return Distribucion.mezcla([(1 - p, cero), (p, base)])
