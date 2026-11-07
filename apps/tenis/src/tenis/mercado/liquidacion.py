"""Liquidacin estricta de mercados con resultados propios (plan tcnico tenis, I.3, S5).

Regla de la casa de referencia (Pinnacle):
  - Solo lee resultados propios (tenis.resultado: y_estado, y_ganador, y_sets, y_juegos).
  - PROHIBIDO taxativamente leer la calificacin de PropLine (falla en ~1 de cada 10 partidos).
    Cualquier intento de suministrar o usar campos de PropLine para liquidar genera ValueError.
  - Desenlaces:
    * Completado: liquida ganador, 1.er set, hndicaps, totales, tiebreak.
    * Walkover / cancelado / descalificado: Nulo (None) para todos los mercados.
    * Retirada con >= 1 set completo: liquida ganador (gana quien avanza) y 1.er set;
      hndicaps, totales y tiebreak son Nulos (None).
    * Retirada con < 1 set completo: Nulo (None) para todos los mercados.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

CAMPOS_PROHIBIDOS_PROPLINE = frozenset({
    "propline_result",
    "propline_status",
    "propline_winner",
    "settled_by_propline",
    "calificacion_propline",
    "propline_qualification",
    "propline_settlement",
    "propline_score",
    "propline_evaluated",
})


def validar_resultado_propio(resultado: Mapping[str, Any]) -> None:
    """Verifica que el resultado provenga de las fuentes propias y no de PropLine."""
    if not isinstance(resultado, Mapping):
        raise TypeError(f"El resultado debe ser un mapeo/diccionario, recibido: {type(resultado)}")

    claves = set(resultado.keys())
    prohibidas = claves & CAMPOS_PROHIBIDOS_PROPLINE
    if prohibidas or any(str(k).startswith("propline_") for k in claves):
        raise ValueError(
            f"Liquidacin prohibida: se detectaron campos de calificacin de PropLine ({prohibidas}). "
            "Solo se permite liquidar con resultados propios de tenis (tenis.resultado)."
        )


def _parsear_sets(res: Mapping[str, Any]) -> list[list[int]] | None:
    """Extrae la lista de sets [[j1, j2], [j1, j2], ...]."""
    raw = res.get("y_sets") or res.get("sets")
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            val = json.loads(raw)
            if isinstance(val, list):
                return val
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def liquidar_ganador(resultado: Mapping[str, Any]) -> int | None:
    """Liquida el mercado de ganador (h2h): 1, 2, o None (nulo / anulado)."""
    validar_resultado_propio(resultado)
    estado = str(resultado.get("y_estado") or resultado.get("estado") or "").lower()
    ganador = resultado.get("y_ganador") or resultado.get("ganador")
    sets_comp = resultado.get("y_sets_completos") or resultado.get("sets_completos") or 0

    try:
        g = int(ganador)
        sc = int(sets_comp)
    except (ValueError, TypeError):
        return None

    if g not in (1, 2):
        return None

    if estado == "completado":
        return g
    elif estado == "retirada" and sc >= 1:
        # Retirada con >= 1 set completo: gana quien avanza
        return g
    else:
        # Walkover, cancelado, descalificado o retirada en set 1: Nulo
        return None


def liquidar_primer_set(resultado: Mapping[str, Any]) -> int | None:
    """Liquida el mercado de ganador del 1.er set: 1, 2 o None (nulo)."""
    validar_resultado_propio(resultado)
    estado = str(resultado.get("y_estado") or resultado.get("estado") or "").lower()
    sets_comp = resultado.get("y_sets_completos") or resultado.get("sets_completos") or 0
    sets = _parsear_sets(resultado)

    try:
        sc = int(sets_comp)
    except (ValueError, TypeError):
        sc = 0

    if sc < 1 or not sets or len(sets) < 1:
        return None

    s1 = sets[0]
    if len(s1) != 2:
        return None

    j1, j2 = s1[0], s1[1]
    if j1 > j2:
        return 1
    elif j2 > j1:
        return 2
    return None


def liquidar_handicap_sets(resultado: Mapping[str, Any], linea_h1: float) -> int | None:
    """Liquida el mercado de hndicap de sets para el lado 1.

    Solo partidos completados. Empate exacto = None (push). Retiradas = None.
    """
    validar_resultado_propio(resultado)
    estado = str(resultado.get("y_estado") or resultado.get("estado") or "").lower()
    if estado != "completado":
        return None

    sets = _parsear_sets(resultado)
    if not sets:
        return None

    sets_j1 = sum(1 for s in sets if len(s) == 2 and s[0] > s[1])
    sets_j2 = sum(1 for s in sets if len(s) == 2 and s[1] > s[0])

    diff = (sets_j1 + float(linea_h1)) - sets_j2
    if diff > 0:
        return 1
    elif diff < 0:
        return 2
    return None  # Push


def liquidar_totales_juegos(resultado: Mapping[str, Any], linea_total: float) -> str | None:
    """Liquida el total de juegos: 'over', 'under', o None (push o retirada).

    Solo partidos completados. Retiradas y walkovers = None (anulados).
    """
    validar_resultado_propio(resultado)
    estado = str(resultado.get("y_estado") or resultado.get("estado") or "").lower()
    if estado != "completado":
        return None

    j1 = resultado.get("y_juegos_1") or resultado.get("juegos_1")
    j2 = resultado.get("y_juegos_2") or resultado.get("juegos_2")
    if j1 is None or j2 is None:
        sets = _parsear_sets(resultado)
        if sets:
            j1 = sum(s[0] for s in sets if len(s) == 2)
            j2 = sum(s[1] for s in sets if len(s) == 2)

    try:
        total = float(j1) + float(j2)
    except (ValueError, TypeError):
        return None

    lt = float(linea_total)
    if total > lt:
        return "over"
    elif total < lt:
        return "under"
    return None  # Push


def liquidar_handicap_juegos(resultado: Mapping[str, Any], linea_h1: float) -> int | None:
    """Liquida el mercado de hndicap de juegos para el lado 1.

    Solo partidos completados. Retiradas = None. Empate = None (push).
    """
    validar_resultado_propio(resultado)
    estado = str(resultado.get("y_estado") or resultado.get("estado") or "").lower()
    if estado != "completado":
        return None

    j1 = resultado.get("y_juegos_1") or resultado.get("juegos_1")
    j2 = resultado.get("y_juegos_2") or resultado.get("juegos_2")
    if j1 is None or j2 is None:
        sets = _parsear_sets(resultado)
        if sets:
            j1 = sum(s[0] for s in sets if len(s) == 2)
            j2 = sum(s[1] for s in sets if len(s) == 2)

    try:
        diff = (float(j1) + float(linea_h1)) - float(j2)
    except (ValueError, TypeError):
        return None

    if diff > 0:
        return 1
    elif diff < 0:
        return 2
    return None  # Push


def liquidar_tiebreak(resultado: Mapping[str, Any]) -> bool | None:
    """Liquida si hubo algn tiebreak en el partido (True/False o None si no completado)."""
    validar_resultado_propio(resultado)
    estado = str(resultado.get("y_estado") or resultado.get("estado") or "").lower()
    if estado != "completado":
        return None

    sets = _parsear_sets(resultado)
    if not sets:
        return None

    for s in sets:
        if len(s) == 2:
            a, b = s[0], s[1]
            if (a == 7 and b == 6) or (a == 6 and b == 7) or (a >= 6 and b >= 6 and abs(a - b) <= 2 and max(a, b) >= 7):
                return True
    return False
