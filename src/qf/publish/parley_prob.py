"""Parley por probabilidad mínima (rediseño de la auditoría del 19-nov-2026), EN SOMBRA.

El parley v2.1 (``parley_v2``) persigue cuotas fijas (2,10 · 3,10 · 8,20 · 12,10) con la
probabilidad del mercado sin margen, así que cada boleto acierta ≈ 1 / cuota: los dos
escalones altos están hechos para perder 9 de cada 10 veces (medido: 0 de 20). Este
selector invierte la regla: primero la PROBABILIDAD del boleto y después la cuota.

* Tres niveles (``NIVELES``) con número fijo de patas, probabilidad conjunta mínima y una
  cuota total mínima para que el boleto tenga sentido. Dentro de cada nivel se maximiza la
  probabilidad conjunta (prudente, si hay artefacto de calibración).
* Solo patas de probabilidad alta (``P_PATA``) en los mercados que cumplen lo que prometen
  (``MERCADOS``): fuera ambos marcan, córners y tarjetas (sobreprometen 1-10 pp en
  ``alta_prob_ext``), asistencias NBA y el ganador de tenis por debajo de ``P_TENIS_GANADOR``.
* Una pata por evento y ningún evento repetido entre niveles; se resuelve del nivel más
  seguro al más arriesgado, para que el seguro se quede con las mejores patas.

Módulo puro, sin base de datos: el lote en sombra lo guarda ``parley_v2_datos``.
Simulación sobre ``alta_prob_ext`` (1-oct a 18-nov, patas 0,78-0,92): 2 patas aciertan 69 %
a cuota 1,54 y 3 patas 54 % a 1,83 (24-26 días: muestra chica, no se promete rendimiento).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import parley_v2 as v2
from .escalera import Opcion

ESTRATEGIA = "parley_probabilidad"
VERSION = "v3-sombra"


@dataclass(frozen=True)
class Nivel:
    indice: int
    nombre: str
    patas: int
    p_min: float          # probabilidad conjunta mínima del boleto
    cuota_min: float      # cuota total mínima: por debajo no compensa combinar


NIVELES: tuple[Nivel, ...] = (
    Nivel(1, "seguro", 2, 0.60, 1.40),
    Nivel(2, "medio", 3, 0.45, 1.80),
    Nivel(3, "arriesgado", 4, 0.33, 2.40),
)

P_PATA = (0.72, 0.93)          # fuera de aquí no entra ninguna pata
CUOTA_PATA_MIN = 1.15          # por debajo la pata solo añade riesgo
P_TENIS_GANADOR = 0.75         # ganador de tenis: solo favoritos claros
MERCADOS = {
    "futbol": {"h2h", "double_chance", "spreads", "totals", "team_totals_home", "team_totals_away"},
    "nba": {"h2h", "spreads", "totals", "player_points", "player_rebounds", "player_threes"},
    "tenis": {"h2h", "handicap_games", "total_games", "spreads", "totals"},
}

_PASO = 0.005                  # resolución del logaritmo de la cuota en la búsqueda
_HAZ = 3                       # combinaciones guardadas por estado
_POR_EVENTO = 3                # patas por evento que entran en la búsqueda


def deporte(op: Opcion) -> str:
    return getattr(op, "deporte", None) or "futbol"


def p_pata(op: Opcion, calibracion: dict | None = None) -> float:
    """Probabilidad prudente (cota inferior del artefacto) o, sin artefacto, la del candidato."""
    return v2._p(op, calibracion)


def elegible(op: Opcion, calibracion: dict | None = None) -> bool:
    if not (math.isfinite(op.price) and op.price >= CUOTA_PATA_MIN):
        return False
    dep, mercado = deporte(op), op.cand.market
    if mercado not in MERCADOS.get(dep, set()):
        return False
    p = p_pata(op, calibracion)
    if not (P_PATA[0] <= p <= P_PATA[1]):
        return False
    return not (dep == "tenis" and mercado == "h2h" and p < P_TENIS_GANADOR)


@dataclass(frozen=True)
class Boleto:
    nivel: Nivel
    legs: tuple[Opcion, ...]
    cuota: float
    p: float


def _buscar(grupos: dict[str, list[Opcion]], nivel: Nivel, calibracion: dict | None) -> Boleto | None:
    """Máxima probabilidad conjunta con exactamente ``nivel.patas`` eventos y cuota ≥ ``cuota_min``.

    Programación dinámica por evento: estado = (patas, cuota acumulada discretizada y topada en
    la mínima). Topar la cuota hace la búsqueda casi exacta y barata; la cuota real se comprueba
    al final contra el mínimo.
    """
    qmin = math.log(nivel.cuota_min)
    tope = int(qmin / _PASO) + 1
    estados: dict[tuple[int, int], list[tuple[float, tuple, float]]] = {(0, 0): [(0.0, (), 0.0)]}
    for opts in grupos.values():
        nuevos = {k: list(v) for k, v in estados.items()}
        for (n, _), lista in estados.items():
            if n >= nivel.patas:
                continue
            for lp, legs, lq in lista:
                for o in opts:
                    q = lq + math.log(o.price)
                    celda = nuevos.setdefault((n + 1, min(int(q / _PASO), tope)), [])
                    celda.append((lp + math.log(p_pata(o, calibracion)), legs + (o,), q))
                    celda.sort(key=lambda e: (-e[0], tuple(x.match_id for x in e[1])))
                    del celda[_HAZ:]
        estados = nuevos
    finales = [e for (n, _), lista in estados.items() if n == nivel.patas for e in lista if e[2] >= qmin - 1e-12]
    if not finales:
        return None
    # Más probable y, a igualdad, la cuota más baja (la entrada es determinista: eventos ordenados).
    lp, legs, lq = max(finales, key=lambda e: (round(e[0], 12), -e[2]))
    p = math.exp(lp)
    if p < nivel.p_min:
        return None
    return Boleto(nivel, tuple(legs), math.exp(lq), p)


def armar(ops: list[Opcion], calibracion: dict | None = None) -> tuple[list[Boleto], list[tuple[Nivel, str]]]:
    """Boletos de los tres niveles sin repetir eventos, y los niveles sin boleto con su motivo."""
    usados: set[str] = set()
    boletos, sin = [], []
    for nivel in NIVELES:
        grupos: dict[str, list[Opcion]] = {}
        for o in ops:
            if o.match_id not in usados and elegible(o, calibracion):
                grupos.setdefault(o.match_id, []).append(o)
        grupos = {m: sorted(lista, key=lambda o: (-p_pata(o, calibracion), -o.price, o.cand.market))[:_POR_EVENTO]
                  for m, lista in sorted(grupos.items())}
        if len(grupos) < nivel.patas:
            sin.append((nivel, f"solo {len(grupos)} eventos con patas elegibles"))
            continue
        b = _buscar(grupos, nivel, calibracion)
        if b is None:
            sin.append((nivel, f"ninguna combinación llega a p ≥ {nivel.p_min:.2f} con cuota ≥ {nivel.cuota_min:.2f}"))
            continue
        boletos.append(b)
        usados |= {o.match_id for o in b.legs}
    return boletos, sin


def _p_central(op: Opcion, calibracion: dict | None) -> float:
    cal = (calibracion or {}).get(v2._clave(op))
    return cal.p_calibrada if cal is not None and cal.p_calibrada is not None else p_pata(op, calibracion)


def a_plan(ops: list[Opcion], calibracion: dict | None = None) -> v2.Plan:
    """Mismo formato que el v2 (``v2.Plan``) para reutilizar el sellado y la liquidación.

    ``target`` = cuota mínima del nivel (única por lote, como exige la tabla). Todo boleto queda
    ``solo_referencia``: es una sombra y no se publica.
    """
    boletos, sin = armar(ops, calibracion)
    tickets = []
    for b in boletos:
        motivos = (f"sombra · nivel {b.nivel.nombre}: {b.nivel.patas} patas, p ≥ {b.nivel.p_min:.2f}, "
                   f"cuota ≥ {b.nivel.cuota_min:.2f}",
                   "patas de probabilidad alta en mercados que cumplen lo prometido")
        p_central = math.prod(_p_central(o, calibracion) for o in b.legs)
        tickets.append(v2.Ticket(b.nivel.cuota_min, b.legs, b.cuota, p_central, estrategia=ESTRATEGIA,
                                 version=VERSION, estado="solo_referencia", motivos=motivos, p_prudente=b.p))
    abst = tuple(v2.Abstencion(n.cuota_min, motivo) for n, motivo in sin)
    return v2.Plan(tuple(tickets), abst, {"niveles": [n.nombre for n in NIVELES],
                                          "elegibles": sum(1 for o in ops if elegible(o, calibracion))})
