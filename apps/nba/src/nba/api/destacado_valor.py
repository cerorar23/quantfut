"""Pronóstico destacado: «probabilidad máxima segura» (decisión del titular, 2026-11-05), igual en fútbol, NBA y tenis.

El objetivo del destacado en el producto es que el usuario vea muchos aciertos (>= 80 %), no maximizar el valor esperado
(la regla de valor esperado del mismo día bajó el acierto visible y se abandonó). Entre los mercados de un partido:
1. Filtro: cuota de referencia >= 1,20 Y probabilidad del modelo >= 75 %.
2. Elección: gana la MAYOR PROBABILIDAD. La cuota no multiplica nada.
3. Desempate: ante igual probabilidad, la mayor cuota de referencia; si aun así empatan, el primero de la lista.
4. Si nadie pasa el filtro no hay destacado (None): mejor no destacar nada que destacar algo que va a fallar.

Sin cuota de casa la de referencia es la del modelo (1 ÷ probabilidad), así que la cuota mínima 1,20 equivale a un tope de
probabilidad de 83,3 %: el destacado sale de la franja 75 %–83,3 %. Con cuota real de una casa el tope lo pone lo que paga la casa.

Copia idéntica de `src/qf/api/destacado_valor.py` (aquí NBA es otro paquete); si se cambia una, se cambia la otra.
"""
from __future__ import annotations

import math
from typing import Any, Callable, Iterable, Mapping

CUOTA_MIN = 1.20
PROB_MIN = 0.75

Campo = str | Callable[[Mapping], Any]


def _valor(item: Mapping, campo: Campo) -> float | None:
    v = campo(item) if callable(campo) else item.get(campo)
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def cumple_filtro(prob: float | None, precio: float | None) -> bool:
    return prob is not None and precio is not None and precio >= CUOTA_MIN and prob >= PROB_MIN


def elegir_destacado(items: Iterable[Mapping], *, prob: Campo = 'prob', precio: Campo = 'ref_price') -> dict | None:
    """El mercado ganador (copia) o None. `prob` y `precio` son nombre de campo o función."""
    mejor, mejor_clave = None, None
    for item in items:
        p, c = _valor(item, prob), _valor(item, precio)
        if not cumple_filtro(p, c):
            continue
        clave = (p, c)
        if mejor_clave is None or clave > mejor_clave:
            mejor, mejor_clave = item, clave
    return None if mejor is None else dict(mejor)
