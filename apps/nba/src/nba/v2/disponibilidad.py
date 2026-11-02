"""Disponibilidad: estado oficial → probabilidad de jugar (calibrada con la historia) → escenarios de un equipo.

La tabla `P_JUEGA` NO es una convención: se mide con los partes 2021-26 contra quién jugó de verdad
(`nba/v2/../ops/evaluar_s2.py`). Quien no figura en el parte usa `P_SIN_PARTE`.
"""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import product
import math

# Medidos con los partes oficiales 2024-25 y 2025-26 (docs/nba_rediseno_s2_resultados_20261102.md). Los extremos no se
# dejan en 0 para no declarar imposible lo que la historia solo dice que es rarísimo. «Available» y «sin parte» valen para
# cualquier jugador de la plantilla; falta condicionarlos al rol (minutos esperados).
P_JUEGA = {"Out": 0.001, "Doubtful": 0.01, "Questionable": 0.43, "Probable": 0.77, "Available": 0.845}
P_SIN_PARTE = 0.84


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson para una proporción k/n."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centro - margen), min(1.0, centro + margen)


def tabla_estados(pares: Iterable[tuple[str | None, bool]]) -> dict[str | None, dict]:
    """[(estado, jugó)] → por estado: n, k, p y su intervalo de Wilson al 95 %."""
    conteo: dict[str | None, list[int]] = {}
    for estado, jugo in pares:
        c = conteo.setdefault(estado, [0, 0])
        c[0] += 1
        c[1] += int(bool(jugo))
    salida = {}
    for estado, (n, k) in conteo.items():
        lo, hi = wilson(k, n)
        salida[estado] = {"n": n, "k": k, "p": k / n, "lo": lo, "hi": hi}
    return salida


def prob_juega(estado: str | None, tabla: Mapping[str, float] = P_JUEGA, sin_parte: float = P_SIN_PARTE) -> float:
    return tabla.get(estado, sin_parte) if estado is not None else sin_parte


@dataclass(frozen=True)
class Escenario:
    prob: float
    ausentes: frozenset[int]


def escenarios(probs: Mapping[int, float], max_inciertos: int = 3) -> list[Escenario]:
    """Escenarios de un equipo a partir de la probabilidad de jugar de cada jugador.

    Los `max_inciertos` jugadores con más incertidumbre se enumeran (2^k escenarios); el resto se fija en su resultado
    más probable. La suma de probabilidades es 1 y los casos de probabilidad 0 se descartan.
    """
    orden = sorted(probs, key=lambda j: -min(probs[j], 1 - probs[j]))
    inciertos = [j for j in orden[:max_inciertos] if 0 < probs[j] < 1]
    fijos_ausentes = frozenset(j for j in probs if j not in inciertos and probs[j] < 0.5)
    resultado = []
    for juegan in product((True, False), repeat=len(inciertos)):
        p = 1.0
        ausentes = set(fijos_ausentes)
        for j, juega in zip(inciertos, juegan):
            p *= probs[j] if juega else 1 - probs[j]
            if not juega:
                ausentes.add(j)
        if p > 0:
            resultado.append(Escenario(p, frozenset(ausentes)))
    total = sum(e.prob for e in resultado)
    return [Escenario(e.prob / total, e.ausentes) for e in sorted(resultado, key=lambda e: -e.prob)]
