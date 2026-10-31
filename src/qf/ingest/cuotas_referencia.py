"""Mejor cuota de referencia de una observación del archivo PropLine (núcleo puro, sin red ni disco).

Decisión del titular (31-oct-2026): la cuota mostrada es el MAYOR precio decimal entre todas las casas
no DFS que cotizan la misma línea y el mismo lado, partido completo, sin intercambios ni en juego.
Empate de precio: gana la casa alfabéticamente menor. Sin precio válido: None (nunca se inventa).

`outcomes` son las filas que emite `propline_shared.quotes()` (una por resultado de casa), con estos campos:
  bookmaker, name, side, point, price_decimal, period, team, flags, dfs_odds_type, payout_multiplier.
`flags` ya trae DFS / intercambio / en juego / suspendida / precio inválido (propline_shared.py quotes());
`period` no nulo = no es el partido completo. El llamador filtra antes el mercado, el evento y, en
jugadores, el `player_id`; aquí solo se elige entre casas.

`side`: "home"/"away" (campo `side` de la fila), "over"/"under"/"yes"/"no" (campo `name`, sin mayúsculas) o
"A"/"B" (el llamador etiqueta la fila con `side="A"|"B"`, p. ej. tras `provider_pair` del tenis).
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from qf.ingest.propline_shared import DFS_BOOKS, EXCHANGES, stamp

_OPUESTO = {"home": "away", "away": "home", "over": "under", "under": "over",
            "A": "B", "B": "A", "yes": "no", "no": "yes"}
# Hándicap: el lado contrario cotiza la línea con signo cambiado (home -3,5 / away +3,5).
_INVIERTE_LINEA = {"home", "away", "A", "B"}


@dataclass(frozen=True)
class Quote:
    price: float
    book: str
    as_of: str      # received_at ISO de la observación
    books: int      # casas elegibles que cotizan esa línea y lado (con ambos lados)


def _es_lado(fila: Mapping, lado: str) -> bool:
    if lado in ("A", "B"):
        return fila.get("side") == lado
    return lado in {str(fila.get("side") or "").lower(), str(fila.get("name") or "").lower()}


def _misma_linea(punto, linea) -> bool:
    if linea is None or punto is None:
        return linea is None and punto is None
    try:
        return math.isclose(float(punto), float(linea), abs_tol=1e-9)
    except (TypeError, ValueError):
        return False


def _precio(fila: Mapping):
    try:
        p = float(fila.get("price_decimal"))
    except (TypeError, ValueError):
        return None
    return p if math.isfinite(p) and p > 1.0 else None


def elegible(fila: Mapping) -> bool:
    # Mismos criterios que apps/nba/src/nba/prop_lines.py:book_lines (flags, DFS por campos, periodo).
    return (not fila.get("flags") and fila.get("period") is None and not fila.get("dfs_odds_type")
            and fila.get("payout_multiplier") is None
            and fila.get("bookmaker") not in DFS_BOOKS and fila.get("bookmaker") not in EXCHANGES)


_elegible = elegible  # nombre anterior


def best_quote(outcomes: Iterable[Mapping], *, line: float | None, side: str,
               sealed_at: datetime, received_at: datetime) -> Quote | None:
    if side not in _OPUESTO or received_at > sealed_at:
        return None
    contra = _OPUESTO[side]
    linea_contra = -line if line is not None and side in _INVIERTE_LINEA else line
    propios: dict[str, float] = {}
    con_contra: set[str] = set()
    for fila in outcomes:
        if not elegible(fila) or _precio(fila) is None or not fila.get("bookmaker"):
            continue
        casa = fila["bookmaker"]
        if _es_lado(fila, side) and _misma_linea(fila.get("point"), line):
            propios[casa] = max(propios.get(casa, 0.0), _precio(fila))
        elif _es_lado(fila, contra) and _misma_linea(fila.get("point"), linea_contra):
            con_contra.add(casa)
    # Una casa con un solo lado no cuenta (mismo criterio que two_way_feed).
    validas = {c: p for c, p in propios.items() if c in con_contra}
    if not validas:
        return None
    casa, precio = min(validas.items(), key=lambda kv: (-kv[1], kv[0]))
    return Quote(price=precio, book=casa, as_of=stamp(received_at), books=len(validas))
