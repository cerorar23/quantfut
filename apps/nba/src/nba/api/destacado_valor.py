"""Pronóstico destacado por valor esperado (decisión del titular, 2026-11-05), igual en fútbol, NBA y tenis.

Entre los mercados de un partido:
1. Filtro: cuota de referencia >= 1,20 Y probabilidad del modelo >= 55 %. Así el destacado se acierta más de lo que se falla.
2. Puntuación: score_destacado = probabilidad × cuota de referencia (valor esperado por unidad apostada).
3. Gana el de mayor puntuación; en empate, el de mayor probabilidad; si aun así empatan, el primero de la lista.
4. Si nadie pasa el filtro no hay destacado (None).

Con cuota del modelo (1 ÷ probabilidad) la puntuación vale 1 en todos los mercados: ahí manda el desempate, o sea la mayor
probabilidad que todavía paga 1,20. El valor esperado solo discrimina cuando hay cuota real de una casa.

Copia idéntica de `src/qf/api/destacado_valor.py` (aquí NBA es otro paquete); si se cambia una, se cambia la otra.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Iterable, Mapping

CUOTA_MIN = 1.20
PROB_MIN = 0.55
_DECIMALES = 9          # 0,6 × 1/0,6 no da exactamente 1: sin redondear, el ruido decidiría los empates

Campo = str | Callable[[Mapping], Any]


def _valor(item: Mapping, campo: Campo) -> float | None:
    v = campo(item) if callable(campo) else item.get(campo)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def cumple_filtro(prob: float | None, precio: float | None) -> bool:
    return prob is not None and precio is not None and precio >= CUOTA_MIN and prob >= PROB_MIN


def score_destacado(prob: float, precio: float) -> float:
    return round(prob * precio, _DECIMALES)


def elegir_destacado(items: Iterable[Mapping], *, prob: Campo = 'prob', precio: Campo = 'ref_price') -> dict | None:
    """El mercado ganador (copia con `score_destacado`) o None. `prob` y `precio` son nombre de campo o función."""
    mejor, mejor_clave = None, None
    for item in items:
        p, c = _valor(item, prob), _valor(item, precio)
        if not cumple_filtro(p, c):
            continue
        clave = (score_destacado(p, c), p)
        if mejor_clave is None or clave > mejor_clave:
            mejor, mejor_clave = item, clave
    return None if mejor is None else dict(mejor, score_destacado=mejor_clave[0])
