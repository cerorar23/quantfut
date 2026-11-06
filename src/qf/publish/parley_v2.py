"""Selector v2 de parleys, sin supuesto de ventaja económica.

El módulo es deliberadamente puro: recibe candidatos ya validados por el
ingestor y devuelve un plan reproducible. La cuota se optimiza en logaritmos,
se minimizan patas antes de maximizar la probabilidad calibrada y no existe un
filtro ``+EV``. La probabilidad prudente es una entrada opcional del pipeline;
si falta, se usa la probabilidad calibrada del candidato.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

from .escalera import Opcion

TARGETS: tuple[float, ...] = (2.10, 3.10, 8.20, 12.10)
TARGET_TOLERANCE = 0.02
MIN_LEGS, MAX_LEGS = 2, 6


@dataclass(frozen=True)
class Target:
    index: int
    value: float

    @property
    def low(self) -> float:
        return self.value * (1 - TARGET_TOLERANCE)

    @property
    def high(self) -> float:
        return self.value * (1 + TARGET_TOLERANCE)


@dataclass(frozen=True)
class Ticket:
    target: float
    legs: tuple[Opcion, ...]
    quote: float
    probability: float


def _p(op: Opcion) -> float:
    """Lee p_prudent si el calibrador la adjuntó; si no, p calibrada."""
    p = getattr(op, "p_prudent", op.cand.prob)
    return min(max(float(p), 1e-9), 1 - 1e-9)


def _key(legs: tuple[Opcion, ...], target: Target, complexity_penalty: float) -> tuple:
    quote = math.prod(o.price for o in legs)
    probability = math.prod(_p(o) for o in legs)
    # La prioridad estructural es mínima cantidad de patas; la penalización
    # solo desempata políticas que permiten expansión y no representa EV.
    score = math.log(probability) - complexity_penalty * len(legs)
    return (len(legs), -score, abs(math.log(quote / target.value)),
            tuple(sorted(o.match_id for o in legs)))


def _candidates_by_match(ops: list[Opcion], used: set[str]) -> dict[str, list[Opcion]]:
    groups: dict[str, list[Opcion]] = {}
    for op in ops:
        if op.match_id in used or op.price <= 1 or not math.isfinite(op.price):
            continue
        groups.setdefault(op.match_id, []).append(op)
    return groups


def buscar(ops: list[Opcion], target: Target, used: set[str] | None = None,
           complexity_penalty: float = 0.0) -> Ticket | None:
    """Busca exactamente una combinación válida para ``target``.

    Es una búsqueda exhaustiva por evento (una pata por partido), acotada a
    seis patas. Para cada cardinalidad se conservan todas las combinaciones
    factibles; así no se confunde una poda heurística con una prueba de
    factibilidad. El llamador debe imponer un límite de tiempo si el universo
    de candidatos es muy grande.
    """
    groups = _candidates_by_match(ops, used or set())
    items = sorted(groups.items())
    for n in range(MIN_LEGS, MAX_LEGS + 1):
        best: tuple[tuple, Ticket] | None = None
        for selected_groups in itertools.combinations(items, n):
            for legs in itertools.product(*(vals for _, vals in selected_groups)):
                quote = math.prod(o.price for o in legs)
                if not (target.low <= quote <= target.high):
                    continue
                probability = math.prod(_p(o) for o in legs)
                ticket = Ticket(target.value, tuple(legs), quote, probability)
                key = _key(ticket.legs, target, complexity_penalty)
                if best is None or key < best[0]:
                    best = (key, ticket)
        if best is not None:
            return best[1]
    return None


def armar_dia(ops: list[Opcion], complexity_penalty: float = 0.0) -> list[Ticket]:
    """Construye hasta cuatro tickets sin reutilizar eventos."""
    tickets: list[Ticket] = []
    used: set[str] = set()
    for index, value in enumerate(TARGETS, 1):
        ticket = buscar(ops, Target(index, value), used, complexity_penalty)
        if ticket is None:
            continue
        tickets.append(ticket)
        used.update(o.match_id for o in ticket.legs)
    return tickets


def log_totals(ticket: Ticket) -> dict[str, float]:
    """Auditoría numéricamente estable de cuota y probabilidad del ticket."""
    return {"log_quote": sum(math.log(o.price) for o in ticket.legs),
            "log_probability": sum(math.log(_p(o)) for o in ticket.legs)}
