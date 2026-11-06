"""Probabilidad de referencia a partir de las casas que cotizan un contrato, sin exigir Pinnacle.

Decisión del usuario (2026-11-06): Pinnacle no es necesario; hay más casas y esto
vale para todos los deportes y mercados del parley. Cada casa que cotiza el
contrato COMPLETO (todos los resultados) se limpia de margen por separado y se
promedian las probabilidades (``consensus_devig``). Si Pinnacle cotiza el
contrato conserva el peso que ya le daba el proyecto (0,6); si no, pesan igual.

Una sola casa no basta para un consenso: hacen falta ``MIN_CASAS`` casas, salvo
que la única sea la preferida (Pinnacle), que era la referencia aceptada antes.
"""
from __future__ import annotations

import math

from ..config import settings
from ..model.devig import consensus_devig

MIN_CASAS = 2


def probabilidades(cotizaciones: dict[str, dict[str, float]], selecciones: tuple[str, ...],
                   preferida: str | None = None, metodo: str | None = None,
                   min_casas: int = MIN_CASAS) -> tuple[dict[str, float], dict] | None:
    """(probabilidades sin margen, procedencia) o None si no hay referencia suficiente.

    ``cotizaciones``: {casa: {resultado: cuota}}. Una casa que no trae todos los
    ``selecciones`` o con una cuota no válida no cuenta (un mercado a medias no
    permite quitar el margen).
    """
    sel = tuple(selecciones)
    validas: dict[str, dict[str, float]] = {}
    for casa, q in cotizaciones.items():
        try:
            fila = {s: float(q[s]) for s in sel}
        except (KeyError, TypeError, ValueError):
            continue
        if all(math.isfinite(v) and v > 1.0 for v in fila.values()):
            validas[casa] = fila
    if not validas:
        return None
    pref = preferida if preferida in validas else None
    if pref is None and len(validas) < min_casas:
        return None
    p = consensus_devig(validas, metodo or settings.devig_method, sharp_book=pref)
    if not p or not all(0 < v < 1 for v in p.values()):
        return None
    return p, {"casas": len(validas), "referencia": "preferida" if pref else "consenso"}
