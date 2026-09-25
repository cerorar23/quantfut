"""
Eliminación del margen (de-vigging).

Convertir cuotas en probabilidades NO es 1/cuota. La suma de 1/cuota es > 1
(el overround). Cómo repartes ese exceso cambia materialmente las
probabilidades, sobre todo en underdogs, por el sesgo favorito-longshot.

Para 1X2, Shin suele calibrar mejor que el reparto proporcional, que es el
que usa casi todo el mundo y es el peor de los cuatro.

Referencia: Shin (1993), "Measuring the Incidence of Insider Trading in a
Market for State-Contingent Claims".
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq


def overround(prices: np.ndarray) -> float:
    return float(np.sum(1.0 / prices))


def multiplicative(prices: np.ndarray) -> np.ndarray:
    """Reparto proporcional. El más simple y el menos preciso."""
    raw = 1.0 / np.asarray(prices, dtype=float)
    return raw / raw.sum()


def additive(prices: np.ndarray) -> np.ndarray:
    """Reparto uniforme del exceso. Mejor que el multiplicativo en underdogs."""
    raw = 1.0 / np.asarray(prices, dtype=float)
    n = len(raw)
    p = raw - (raw.sum() - 1.0) / n
    return np.clip(p, 1e-6, 1.0) / np.clip(p, 1e-6, 1.0).sum()


def power(prices: np.ndarray) -> np.ndarray:
    """p_i = raw_i^k, resolviendo k tal que la suma sea 1."""
    raw = 1.0 / np.asarray(prices, dtype=float)

    def f(k: float) -> float:
        return float(np.sum(raw ** k) - 1.0)

    try:
        k = brentq(f, 0.35, 3.0, xtol=1e-10)
    except ValueError:
        return multiplicative(prices)
    p = raw ** k
    return p / p.sum()


def shin(prices: np.ndarray) -> np.ndarray:
    """
    Método de Shin. Modela la presencia de apostadores informados (insiders)
    con proporción z, y extrae la probabilidad "verdadera" bajo ese supuesto.

        pi_i = [sqrt(z^2 + 4(1-z) * raw_i^2 / S) - z] / (2(1-z))

    donde S = sum(raw) y z se resuelve para que sum(pi) = 1.
    """
    raw = 1.0 / np.asarray(prices, dtype=float)
    s = raw.sum()

    if s <= 1.0 + 1e-12:  # sin margen (o ya normalizado)
        return raw / s

    def pi_of_z(z: float) -> np.ndarray:
        inner = z * z + 4.0 * (1.0 - z) * (raw ** 2) / s
        return (np.sqrt(np.clip(inner, 0.0, None)) - z) / (2.0 * (1.0 - z))

    def f(z: float) -> float:
        return float(pi_of_z(z).sum() - 1.0)

    try:
        z = brentq(f, 1e-9, 0.35, xtol=1e-12)
    except ValueError:
        return power(prices)

    p = pi_of_z(z)
    p = np.clip(p, 1e-9, 1.0)
    return p / p.sum()


_METHODS = {
    "multiplicative": multiplicative,
    "additive": additive,
    "power": power,
    "shin": shin,
}


def devig(prices, method: str = "shin") -> np.ndarray:
    """Devuelve probabilidades sin margen. `prices` = cuotas decimales."""
    arr = np.asarray(prices, dtype=float)
    if np.any(arr <= 1.0):
        raise ValueError(f"Cuotas decimales inválidas: {prices}")
    fn = _METHODS.get(method)
    if fn is None:
        raise ValueError(f"Método desconocido: {method}. Opciones: {list(_METHODS)}")
    return fn(arr)


def fair_price(prob: float) -> float:
    return float("inf") if prob <= 0 else 1.0 / prob


def two_way_devig(price_a: float, price_b: float, method: str = "shin") -> tuple[float, float]:
    """Atajo para mercados binarios (totales, hándicap, BTTS)."""
    p = devig([price_a, price_b], method)
    return float(p[0]), float(p[1])


def consensus_devig(
    quotes: dict[str, dict[str, float]],
    method: str = "shin",
    sharp_book: str | None = None,
    sharp_weight: float = 0.6,
) -> dict[str, float]:
    """
    Consenso de mercado a partir de varias casas.

    quotes: {'pinnacle': {'home': 2.05, 'draw': 3.4, 'away': 3.9}, 'bet365': {...}}

    Si la casa sharp está presente, se le da `sharp_weight` y el resto se
    reparte el complemento. Promediar en espacio de probabilidad (no de cuota),
    que es lo correcto.
    """
    if not quotes:
        return {}
    selections = list(next(iter(quotes.values())).keys())
    accum, total_w = {s: 0.0 for s in selections}, 0.0

    others = [b for b in quotes if b != sharp_book]
    for book, prices in quotes.items():
        if set(prices) != set(selections):
            continue
        try:
            p = devig([prices[s] for s in selections], method)
        except ValueError:
            continue
        if sharp_book and book == sharp_book:
            w = sharp_weight
        elif sharp_book and others:
            w = (1.0 - sharp_weight) / len(others)
        else:
            w = 1.0 / len(quotes)
        for s, v in zip(selections, p):
            accum[s] += w * float(v)
        total_w += w

    if total_w == 0:
        return {}
    return {s: v / total_w for s, v in accum.items()}
