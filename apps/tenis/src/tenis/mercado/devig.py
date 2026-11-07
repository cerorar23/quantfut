"""Clculo de margen y des-marginado proporcional estricto (plan tcnico tenis, I.0, S5).

El mtodo de quitar margen es proporcional (sin parmetros libres ni supuestos Shin/potencia que solo
aaden fracciones de diez milsimas; aud. 6.2).
Las cuotas absurdas (cuota <= 1.0, americana |x| < 100) o de un solo lado se rechazan estrictamente.
"""
from __future__ import annotations

import math
from typing import Sequence


def cuota_americana_a_decimal(cuota_am: float | int | str) -> float:
    """Convierte cuota americana a decimal. Rechaza |x| < 100, 0 o valores no numricos."""
    try:
        val = float(cuota_am)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Cuota americana no numrica: {cuota_am}") from exc

    if math.isnan(val) or math.isinf(val):
        raise ValueError(f"Cuota americana no finita: {cuota_am}")

    if abs(val) < 100:
        raise ValueError(f"Cuota americana absurda en (-100, 100): {cuota_am}")

    if val > 0:
        return 1.0 + val / 100.0
    else:
        return 1.0 + 100.0 / (-val)


def cuota_decimal_a_americana(cuota_dec: float | int | str) -> int:
    """Convierte cuota decimal a americana. Rechaza cuotas <= 1.0."""
    try:
        val = float(cuota_dec)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Cuota decimal no numrica: {cuota_dec}") from exc

    if math.isnan(val) or math.isinf(val) or val <= 1.0:
        raise ValueError(f"Cuota decimal absurda o <= 1.0: {cuota_dec}")

    if val >= 2.0:
        return int(round((val - 1.0) * 100.0))
    else:
        return -int(round(100.0 / (val - 1.0)))


def calcular_margen(cuotas: Sequence[float | int]) -> float:
    """Calcula el margen total (overround) sum(1/o_i) - 1.

    Rechaza mercados de un solo lado o con cuotas <= 1.0.
    """
    if len(cuotas) < 2:
        raise ValueError("Mercado de un solo lado: no se puede calcular margen sin ambos lados")

    inversas = []
    for c in cuotas:
        try:
            val = float(c)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Cuota no numrica en mercado: {c}") from exc
        if math.isnan(val) or math.isinf(val) or val <= 1.0:
            raise ValueError(f"Cuota decimal absurda o <= 1.0: {c}")
        inversas.append(1.0 / val)

    return sum(inversas) - 1.0


def devig_proporcional(cuotas: Sequence[float | int]) -> list[float]:
    """Des-margina cuotas mediante el mtodo proporcional estricto: p_i = (1/O_i) / sum(1/O_j).

    Validaciones absurdas:
      - Menos de dos cuotas -> rechazo (un mercado de un solo lado carece de probabilidad sin margen).
      - Cuota <= 1.0, NaN o inf -> rechazo.
      - Margen no realista (< -0.5 o > 1.0) -> rechazo.
    Garantiza sum(p_i) == 1.0 dentro de tolerancia numrica.
    """
    if len(cuotas) < 2:
        raise ValueError("Mercado de un solo lado: sin probabilidad sin margen")

    inversas = []
    for c in cuotas:
        try:
            val = float(c)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Cuota no numrica: {c}") from exc
        if math.isnan(val) or math.isinf(val) or val <= 1.0:
            raise ValueError(f"Cuota decimal invlida o <= 1.0: {c}")
        inversas.append(1.0 / val)

    suma_inv = sum(inversas)
    margen = suma_inv - 1.0
    if margen < -0.5 or margen > 1.0 or suma_inv <= 0.0:
        raise ValueError(f"Margen de mercado absurdo ({margen:.4f})")

    probs = [inv / suma_inv for inv in inversas]
    return probs


def devig_dos_vias(o1: float | int | None, o2: float | int | None) -> tuple[float | None, float | None, float | None]:
    """Des-margina un mercado de 2 resultados (o1, o2).

    Retorna (p1, p2, margen). Si alguna cuota falta, es <= 1.0 o es invlida, retorna (None, None, None).
    """
    if o1 is None or o2 is None:
        return (None, None, None)
    try:
        v1, v2 = float(o1), float(o2)
        if math.isnan(v1) or math.isnan(v2) or v1 <= 1.0 or v2 <= 1.0:
            return (None, None, None)
        inv1, inv2 = 1.0 / v1, 1.0 / v2
        s = inv1 + inv2
        margen = s - 1.0
        if margen < -0.5 or margen > 1.0 or s <= 0.0:
            return (None, None, None)
        return (inv1 / s, inv2 / s, margen)
    except (ValueError, TypeError):
        return (None, None, None)
