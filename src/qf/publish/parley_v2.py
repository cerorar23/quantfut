"""Selector v2 de parleys, sin supuesto de ventaja económica.

El módulo es puro: recibe candidatos ya validados por el ingestor y devuelve un
plan reproducible. No lee base de datos, no sella y no publica; el orden
predecir → seleccionar → sellar → publicar sigue siendo del pipeline diario.

Reglas (decisión del usuario, 2026-11-06; medición en
``docs/parley_topes_medicion_20261106.md``):

* Cuatro targets 2.10, 3.10, 8.20 y 12.10 con ±2 %. Se prioriza alcanzar el
  target, luego minimizar patas y después maximizar la probabilidad conjunta
  prudente. Sin filtro ni supuesto de +EV.
* Una pata por evento y ningún evento repetido entre los cuatro tickets.
* Rango de cuota por pata según el target y la familia del mercado
  (``POLITICA``). Targets bajos: 1.20-1.80. Targets altos: hasta 2.50 en
  ganador y hasta 2.10 en líneas (goles, hándicap, córners, props). Lo no
  medido conserva 1.80; el 1T 1X2 queda fuera (margen del 9-11 %).
* Mejor cuota por contrato exacto entre casas, con protección contra cuotas
  atípicas (``consolidar``).
* Los cuatro tickets se resuelven a la vez (``armar_plan``), no uno tras otro.
* ``publicado`` solo si cada pata trae probabilidad calibrada con
  incertidumbre de un artefacto aprobado; si no, ``solo_referencia``. Sin
  combinación válida, ``abstencion``. El same-game solo es ejecutable con
  distribución conjunta validada y cuota real del paquete.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime

from .escalera import Opcion

ESTRATEGIA = "parley_objetivo"
VERSION = "v2.1"

TARGETS: tuple[float, ...] = (2.10, 3.10, 8.20, 12.10)
TARGET_TOLERANCE = 0.02
MIN_LEGS, MAX_LEGS = 2, 6

LEG_FLOOR = 1.20
LOW_TARGETS = 2                    # los dos primeros targets son «bajos»
LOW_CAP = 1.80
LOW_CAP_LINEA = 1.95               # líneas de dos lados .5 (≈1.91) en targets bajos
CAP_GANADOR = 2.50
CAP_LINEA = 2.10
CAP_SIN_MEDIR = 1.80
OUTLIER_GUARD = 0.05               # mejor cuota > 2.ª mejor × 1.05 con ≥3 casas: se descarta
MIN_CASAS_GUARDA = 3

# Búsqueda: resolución del logaritmo de la cuota y anchura del haz por estado.
_STEP = 0.002
_BEAM = 3
_POR_N = 12                        # tickets candidatos por cardinalidad y target
_NODOS_MAX = 2_000_000
_MAX_OPCIONES = 6                   # por evento antes de podar por tramo de cuota
_BUCKETS = (1.2, 1.4, 1.6, 1.8, 2.1, 2.5, 3.0001)

GANADOR, LINEA, EXCLUIDO, SIN_MEDIR = "ganador", "linea", "excluido", "sin_medir"
_GANADOR = {"h2h", "moneyline", "winner", "ml"}
_LINEA = {"totals", "spreads", "corners", "team_totals_home", "team_totals_away",
          "team_totals", "total_games", "handicap_games", "player_points", "player_rebounds",
          "player_assists", "player_threes"}
_SUFIJOS_PERIODO = ("_1t", "_1h", "_h1", "_q1")


def familia(market: str) -> str:
    """Familia de política de un mercado. Lo no medido es ``sin_medir``."""
    m = market.lower()
    periodo = m.endswith(_SUFIJOS_PERIODO)
    base = m[:-3] if periodo else m
    if base in _GANADOR:
        return EXCLUIDO if periodo else GANADOR   # 1T 1X2: margen 9-11 %
    if base in _LINEA:                    # los demás player_* (combos, robos…) no están medidos
        return LINEA
    return SIN_MEDIR


def tope(op: Opcion, target_index: int) -> float | None:
    """Cuota máxima admitida para esa pata en ese target (None: no entra)."""
    fam = familia(op.cand.market)
    if fam == EXCLUIDO:
        return None
    bajo = target_index <= LOW_TARGETS
    if fam == GANADOR:
        return LOW_CAP if bajo else CAP_GANADOR
    if fam == LINEA:
        if not bajo:
            return CAP_LINEA
        medio = op.cand.line is not None and math.isclose(abs(op.cand.line) % 1, 0.5)
        return LOW_CAP_LINEA if medio else LOW_CAP
    return CAP_SIN_MEDIR


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
class Calibracion:
    """Probabilidad prudente de una pata y su intervalo (bootstrap del artefacto)."""
    p_prudente: float                    # la que usa la selección (cota inferior del intervalo)
    p_bajo: float
    p_alto: float
    artefacto: str = ""
    p_calibrada: float | None = None     # estimación central; si falta se informa la prudente


@dataclass(frozen=True)
class Ticket:
    target: float
    legs: tuple[Opcion, ...]
    quote: float
    probability: float
    estrategia: str = ESTRATEGIA
    version: str = VERSION
    tipo: str = "multievento"
    estado: str = "solo_referencia"
    p_bajo: float | None = None
    p_alto: float | None = None
    motivos: tuple[str, ...] = ()
    p_prudente: float | None = None      # producto de las p prudentes con las que se eligió


@dataclass(frozen=True)
class Abstencion:
    target: float
    motivo: str


@dataclass(frozen=True)
class Plan:
    tickets: tuple[Ticket, ...]
    abstenciones: tuple[Abstencion, ...]
    diagnostico: dict = field(default_factory=dict)


def _clave(op: Opcion) -> tuple:
    """Contrato exacto. En los props de jugador el jugador es parte del contrato: dos jugadores con
    el mismo mercado y línea NO son la misma oferta."""
    base = (op.match_id, op.cand.market, op.cand.selection, op.cand.line)
    jugador = getattr(op, "jugador", ())
    return base + (jugador[0],) if jugador else base


def _p(op: Opcion, calibracion: dict | None = None) -> float:
    """p prudente si hay artefacto; si no, p adjunta o p calibrada del candidato."""
    cal = (calibracion or {}).get(_clave(op))
    p = cal.p_prudente if cal is not None else getattr(op, "p_prudent", op.cand.prob)
    return min(max(float(p), 1e-9), 1 - 1e-9)


def consolidar(ofertas: list[Opcion]) -> list[Opcion]:
    """Una oferta por contrato exacto: la mejor cuota entre casas.

    Con ≥3 casas para el mismo contrato se descarta la mejor oferta mientras
    supere a la siguiente en más de ``OUTLIER_GUARD``: la cuota máxima entre
    casas puede ser un error o un precio caduco. Con menos casas no hay base
    para juzgarla y se conserva.
    """
    grupos: dict[tuple, list[Opcion]] = {}
    for o in ofertas:
        if o.price > 1 and math.isfinite(o.price):
            grupos.setdefault(_clave(o), []).append(o)
    out = []
    for lista in grupos.values():
        lista = sorted(lista, key=lambda o: (-o.price, o.book))
        while len(lista) >= MIN_CASAS_GUARDA and lista[0].price > lista[1].price * (1 + OUTLIER_GUARD):
            lista = lista[1:]
        out.append(lista[0])
    return sorted(out, key=lambda o: (o.match_id, o.cand.market, o.cand.selection, str(o.cand.line)))


def _elegibles(ops: list[Opcion], target: Target, usados: set[str],
               ahora: datetime | None) -> dict[str, list[Opcion]]:
    """Patas que cumplen la política del target.

    Un evento con más de ``_MAX_OPCIONES`` patas elegibles se poda a la de mayor
    probabilidad por tramo de cuota (lo medido: no cambia el resultado y acota
    el coste); con menos se conservan todas y la búsqueda es exacta en el evento.
    """
    grupos: dict[str, list[Opcion]] = {}
    for o in ops:
        if o.match_id in usados or not math.isfinite(o.price):
            continue
        if ahora is not None and (o.odds_as_of is None or o.odds_as_of > ahora):
            continue
        t = tope(o, target.index)
        if t is None or not (LEG_FLOOR <= o.price <= t):
            continue
        grupos.setdefault(o.match_id, []).append(o)
    out: dict[str, list[Opcion]] = {}
    for m, lista in sorted(grupos.items()):
        if len(lista) > _MAX_OPCIONES:
            por_tramo: dict[int, Opcion] = {}
            for o in lista:
                b = sum(o.price >= x for x in _BUCKETS)
                if b not in por_tramo or _p(o) > _p(por_tramo[b]):
                    por_tramo[b] = o
            lista = list(por_tramo.values())
        out[m] = sorted(lista, key=lambda o: (o.price, o.cand.market, o.cand.selection))
    return out


def _candidatos(grupos: dict[str, list[Opcion]], target: Target,
                calibracion: dict | None) -> list[tuple]:
    """Tickets factibles del target: DP exacta por evento con haz de ``_BEAM`` por estado.

    Estado = (nº de patas, cuota discretizada). Una pata por evento queda
    garantizada al procesar evento a evento. La cuota exacta se vuelve a
    comprobar contra la banda al final.
    """
    hi, lo = math.log(target.high), math.log(target.low)
    estados: dict[tuple, list[tuple]] = {(0, 0): [(0.0, (), 0.0)]}
    for opts in grupos.values():
        nuevos = {k: list(v) for k, v in estados.items()}
        for (n, _), lista in estados.items():
            if n >= MAX_LEGS:
                continue
            for lp, legs, lq in lista:
                for o in opts:
                    q = lq + math.log(o.price)
                    if q > hi:
                        continue
                    celda = nuevos.setdefault((n + 1, int(q / _STEP)), [])
                    celda.append((lp + math.log(_p(o, calibracion)), legs + (o,), q))
                    celda.sort(key=lambda e: -e[0])
                    del celda[_BEAM:]
        estados = nuevos
    por_n: dict[int, dict[tuple, tuple]] = {}
    for (n, _), lista in estados.items():
        if n < MIN_LEGS:
            continue
        for lp, legs, lq in lista:
            if lo <= lq <= hi:
                clave = tuple(sorted((o.match_id, o.cand.market, o.cand.selection, str(o.cand.line), o.price)
                                     for o in legs))
                cur = por_n.setdefault(n, {}).get(clave)
                if cur is None or lp > cur[0]:
                    por_n[n][clave] = (lp, legs, lq)
    out = []
    for n in sorted(por_n):
        orden = sorted(por_n[n].values(), key=lambda e: (-e[0], tuple(o.match_id for o in e[1])))
        out.extend(orden[:_POR_N])
    return out


def _ticket(target: Target, entrada: tuple, calibracion: dict | None) -> Ticket:
    _, legs, _ = entrada
    quote = math.prod(o.price for o in legs)
    cals = [(calibracion or {}).get(_clave(o)) for o in legs]
    prudente = math.prod(_p(o, calibracion) for o in legs)
    prob = math.prod(c.p_calibrada if c is not None and c.p_calibrada is not None else _p(o, calibracion)
                     for o, c in zip(legs, cals))
    calibrado = all(c is not None for c in cals)
    motivos = [f"{len(legs)} patas: mínimo que alcanza el target {target.value:.2f}"
               if len(legs) == MIN_LEGS else f"{len(legs)} patas"]
    altas = [o for o in legs if o.price > LOW_CAP]
    if altas and target.index > LOW_TARGETS:
        motivos.append(f"{len(altas)} pata(s) con cuota 1.80-2.50 para reducir patas")
    if calibrado:
        estado, lo, hi = "publicado", math.prod(c.p_bajo for c in cals), math.prod(c.p_alto for c in cals)
        motivos.append("todas las patas con probabilidad calibrada e incertidumbre")
    else:
        estado, lo, hi = "solo_referencia", None, None
        motivos.append("sin artefacto de calibración aprobado para todas las patas")
    return Ticket(target.value, tuple(legs), quote, prob, estado=estado,
                  p_bajo=lo, p_alto=hi, motivos=tuple(motivos), p_prudente=prudente if calibrado else None)


def _clave_plan(tickets: list[tuple]) -> tuple:
    """Orden del plan: más targets cubiertos, menos patas, más probabilidad, más cerca, ids estables."""
    cubiertos = len(tickets)
    patas = sum(len(e[1]) for _, e in tickets)
    prob = sum(math.exp(e[0]) for _, e in tickets)
    dist = sum(abs(math.log(math.prod(o.price for o in e[1]) / t.value)) for t, e in tickets)
    ids = tuple(sorted(o.match_id for _, e in tickets for o in e[1]))
    return (-cubiertos, patas, -prob, dist, ids)


def armar_plan(ops: list[Opcion], calibracion: dict | None = None,
               ahora: datetime | None = None) -> Plan:
    """Resuelve los cuatro targets a la vez, sin repetir eventos, con la política por mercado."""
    targets = [Target(i, v) for i, v in enumerate(TARGETS, 1)]
    ops = [o for o in ops if o.price > 1]
    grupos_t = {t.index: _elegibles(ops, t, set(), ahora) for t in targets}
    pools = {t.index: _candidatos(grupos_t[t.index], t, calibracion) for t in targets}
    nodos = 0
    mejor: tuple | None = None
    completa = True

    def dfs(i: int, usados: frozenset, elegidos: list) -> None:
        nonlocal nodos, mejor, completa
        if nodos > _NODOS_MAX:
            completa = False
            return
        nodos += 1
        if i == len(targets):
            clave = _clave_plan(elegidos)
            if mejor is None or clave < mejor[0]:
                mejor = (clave, list(elegidos))
            return
        t = targets[i]
        for e in pools[t.index]:
            ids = {o.match_id for o in e[1]}
            if ids & usados:
                continue
            elegidos.append((t, e))
            dfs(i + 1, usados | ids, elegidos)
            elegidos.pop()
        dfs(i + 1, usados, elegidos)          # target sin ticket: abstención

    dfs(0, frozenset(), [])
    elegidos = mejor[1] if mejor else []
    tickets = tuple(_ticket(t, e, calibracion) for t, e in elegidos)
    cubiertos = {t.value for t, _ in elegidos}
    abst = tuple(Abstencion(t.value, "sin combinación válida con la política de cuotas y eventos libres"
                            if pools[t.index] else "sin patas elegibles que alcancen el target")
                 for t in targets if t.value not in cubiertos)
    diag = {"candidatos": {t.value: len(pools[t.index]) for t in targets},
            "eventos_elegibles": {t.value: len(grupos_t[t.index]) for t in targets},
            "busqueda_completa": completa, "nodos": nodos, "haz": _BEAM,
            "nota": "Haz por estado y tope por cardinalidad: no se afirma optimalidad global."}
    return Plan(tickets, abst, diag)


def buscar(ops: list[Opcion], target: Target, used: set[str] | None = None,
           complexity_penalty: float = 0.0) -> Ticket | None:
    """Mejor ticket de un solo target: mínimas patas y, entre ellas, mayor probabilidad."""
    grupos = _elegibles([o for o in ops if o.price > 1], target, used or set(), None)
    pool = _candidatos(grupos, target, None)
    if not pool:
        return None
    mejor = min(pool, key=lambda e: (len(e[1]), -(e[0] - complexity_penalty * len(e[1])),
                                     abs(math.log(math.prod(o.price for o in e[1]) / target.value)),
                                     tuple(sorted(o.match_id for o in e[1]))))
    return _ticket(target, mejor, None)


def armar_dia(ops: list[Opcion], complexity_penalty: float = 0.0) -> list[Ticket]:
    """Compatibilidad con ``parley_datos``: los tickets del plan de cuatro targets."""
    return list(armar_plan(ops).tickets)


def same_game(legs: list[Opcion], cuota_paquete: float | None = None,
              prob_conjunta: float | None = None, target: float = 0.0) -> Ticket:
    """Parley de un solo partido. Ejecutable solo con cuota real del paquete y
    distribución conjunta validada; el producto de marginales no se usa nunca."""
    if len({o.match_id for o in legs}) != 1:
        raise ValueError("un same-game exige todas las patas del mismo partido")
    quote = cuota_paquete if cuota_paquete else math.prod(o.price for o in legs)
    prob = prob_conjunta if prob_conjunta is not None else math.nan
    motivos = []
    if not cuota_paquete:
        motivos.append("sin cuota real del paquete")
    if prob_conjunta is None:
        motivos.append("sin distribución conjunta validada: no se multiplican marginales")
    estado = "solo_referencia" if motivos else "publicado"
    return Ticket(target, tuple(legs), quote, prob, tipo="same_game", estado=estado,
                  motivos=tuple(motivos) or ("cuota real del paquete y modelo conjunto validado",))


def resumen(ticket: Ticket) -> dict:
    """Registro auditable del ticket con los campos pedidos (cuota, casa, hora, mercado, selección, p)."""
    return {
        "estrategia": ticket.estrategia, "version": ticket.version, "target": ticket.target,
        "tipo": ticket.tipo, "estado": ticket.estado, "n_patas": len(ticket.legs),
        "cuota_total": round(ticket.quote, 4),
        "probabilidad_conjunta": None if math.isnan(ticket.probability) else round(ticket.probability, 6),
        "probabilidad_prudente": None if ticket.p_prudente is None else round(ticket.p_prudente, 6),
        "incertidumbre": None if ticket.p_bajo is None else [round(ticket.p_bajo, 6), round(ticket.p_alto, 6)],
        "motivos": list(ticket.motivos),
        "patas": [{"match_id": o.match_id, "mercado": o.cand.market, "seleccion": o.cand.selection,
                   "linea": o.cand.line, "cuota": o.price, "casa": o.book,
                   "cuota_en": o.odds_as_of.isoformat() if o.odds_as_of else None,
                   "prob": round(o.cand.prob, 4)} for o in ticket.legs],
    }


def log_totals(ticket: Ticket) -> dict[str, float]:
    """Auditoría numéricamente estable de cuota y probabilidad del ticket."""
    return {"log_quote": sum(math.log(o.price) for o in ticket.legs),
            "log_probability": sum(math.log(min(max(float(getattr(o, "p_prudent", o.cand.prob)), 1e-9), 1 - 1e-9))
                                   for o in ticket.legs)}
