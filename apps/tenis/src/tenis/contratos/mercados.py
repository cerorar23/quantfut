"""Mercados derivados de la distribución conjunta (plan G.4).

Cada mercado se recalcula desde las entradas (marcadores con probabilidad) y se compara con el declarado:
si difieren más de 1e-9, el partido no se sella. Las claves de línea van como texto (JSON no tiene floats como clave).
"""
import math

from .base import Contrato, Prob

TOLERANCIA = 1e-9


class Mercados(Contrato):
    gana_a: Prob
    primer_set_a: Prob
    sets_mas_de: dict[str, Prob] = {}      # P(nº de sets > L), clave "L"
    juegos_mas_de: dict[str, Prob] = {}    # P(total de juegos > L), clave "L"
    handicap_sets: dict[str, Prob] = {}    # P(sets_A - sets_B + h > 0), clave "h"


def _numero(clave: str) -> float:
    try:
        valor = float(clave)
    except ValueError:
        raise ValueError(f"línea de mercado «{clave}» no numérica") from None
    if not math.isfinite(valor):
        raise ValueError(f"línea de mercado «{clave}» no finita")
    return valor


def _ganados(sets) -> tuple[int, int]:
    a = sum(1 for s in sets if s.juegos_a > s.juegos_b)
    return a, len(sets) - a


def _prob(entradas, condicion) -> float:
    return sum(e.probabilidad for e in entradas if condicion(e.sets))


def _cmp(nombre: str, declarado: float, calculado: float) -> None:
    if abs(declarado - calculado) > TOLERANCIA:
        raise ValueError(f"mercado «{nombre}» incoherente con la conjunta ({declarado:.12f} frente a {calculado:.12f})")


def validar_mercados(m: Mercados, entradas) -> None:
    _cmp("gana_a", m.gana_a, _prob(entradas, lambda s: _ganados(s)[0] > _ganados(s)[1]))
    _cmp("primer_set_a", m.primer_set_a, _prob(entradas, lambda s: s[0].juegos_a > s[0].juegos_b))
    for clave, valor in m.sets_mas_de.items():
        L = _numero(clave)
        _cmp(f"sets_mas_de[{clave}]", valor, _prob(entradas, lambda s, L=L: len(s) > L))
    for clave, valor in m.juegos_mas_de.items():
        L = _numero(clave)
        _cmp(f"juegos_mas_de[{clave}]", valor, _prob(entradas, lambda s, L=L: sum(x.juegos_a + x.juegos_b for x in s) > L))
    for clave, valor in m.handicap_sets.items():
        h = _numero(clave)
        _cmp(f"handicap_sets[{clave}]", valor, _prob(entradas, lambda s, h=h: _ganados(s)[0] - _ganados(s)[1] + h > 0))
