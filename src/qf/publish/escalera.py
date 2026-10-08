"""
Reto escalera: cada escalón apuesta TODO el saldo a un pronóstico; el reto se
completa al ganar sus escalones (3 a 6) y se pierde al fallar uno (pedido del
usuario, 2026-10-08). Es una apuesta combinada en la que cada partido se elige
cuando el anterior ya terminó.

LO QUE DECÍA LA REGLA DE PARTIDA Y LO QUE SE MIDIÓ
---------------------------------------------------
La regla del usuario: cuotas de 1,25 a 1,40, de 5 a 7 pasos, retirar la
inversión al llegar a ×2,5 y no forzar escalones. La probabilidad que daba
salía de la cuota (1 / cuota), es decir, CON el margen de la casa.

Medido sobre football-data (7 ligas, 2019-2025, pre-cierre, mejor de bet365 y
1xBet; `eval/escalera_prueba.py`): en 1,25-1,40 la probabilidad real (Pinnacle
sin margen) es 72,6 % y se acierta el 74,3 %, pero cada escalón pierde un
−3,4 % de valor esperado, y la escalera lo multiplica: 6 pasos se completan el
15,7 % de las veces y dejan −23,7 % por reto (−19,2 % retirando a ×2,5).

LA MEJORA
---------
1. Probabilidad real de Pinnacle sin margen, no la implícita en la cuota.
2. Solo escalones con cuota ≥ precio justo (`EV_MIN`): la escalera multiplica
   el valor de cada paso, así que un paso con margen en contra no se da.
3. La cuota es la mejor de las casas de la lista (`SOFT_BOOKS`) en el mismo
   instante: es la que se puede tomar y la que sube el saldo.
4. Un escalón al día como máximo por reto y solo cuando el anterior está
   liquidado. Si ningún partido cumple, no se apuesta: un reto puede durar semanas.
5. Freeroll: al llegar a `FREEROLL_X` veces el stake se retira la inversión y
   el resto sigue sin riesgo propio.
6. Retos de 3 a 6 escalones, varios a la vez (decisión del usuario,
   2026-10-08): `longitud_nuevo`. Acortar sube el % de retos completados pero
   NO el valor esperado (con escalones a precio justo es el mismo a cualquier
   longitud): solo cambia la varianza.
7. Hándicap asiático protector (+1, +1,5, +2...) solo en las líneas que
   pasaron la prueba de calibración (`eval/escalera_handicap.py`).

Lo que NO promete: con EV ≥ 0 el valor medido es casi nulo (+0,3 % en vivo),
no un beneficio garantizado. Lo que quita es el −3,4 % por escalón.

Este módulo es la parte pura. La base de datos está en `escalera_datos.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from .alta_prob import Candidato

CUOTA_MIN = 1.25
CUOTA_MAX = 1.40
# Longitudes posibles y tope de retos de 6 que pueden EMPEZAR en un mes natural
# (UTC). Ver `longitud_nuevo`.
LONGITUDES = (3, 4, 5, 6)
MAX_SEIS_MES = 3
STAKE = Decimal("10.00")
FREEROLL_X = 2.5
EV_MIN = 0.0
MAX_EDAD_PRECIO = timedelta(hours=6)
HORIZONTE = timedelta(hours=36)
# Líneas de goles candidatas: las validadas para alta probabilidad más la 2,5,
# que es la línea que Pinnacle cotiza directamente (sin ajuste).
LINEAS_GOLES: tuple[tuple[str, float], ...] = (
    ("over", 1.5), ("under", 3.5), ("over", 2.5), ("under", 2.5))
# Hándicap asiático: solo líneas enteras y medias (las de cuarto liquidan
# medias ganadas/perdidas). Prueba histórica del 2026-10-08
# (eval/escalera_handicap.py, firma d5cbc3151164, rho −0,0613, criterio de
# alta probabilidad): pasan −1, −0,5, 0, +0,5, +1, +1,5 y +2 (las protectoras
# se aciertan ~1 punto MÁS de lo prometido: +1 79,55→80,72; +1,5 79,94→80,98;
# +2 81,87→82,97). −1,5 no pasa (66,69→64,21) y queda fuera. Añadir una
# línea exige repetir la prueba.
LINEAS_HANDICAP: tuple[float, ...] = (-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0)
MERCADOS = ("h2h", "totals", "team_totals_home", "team_totals_away", "spreads")
_CENT = Decimal("0.01")


@dataclass(frozen=True)
class Opcion:
    """Un candidato con la cuota que de verdad se puede tomar."""
    match_id: str
    cand: Candidato
    price: float
    book: str
    odds_source: str = ""
    odds_as_of: datetime | None = None

    @property
    def ev(self) -> float:
        return self.cand.prob * self.price - 1.0


def prob_handicap(p: dict[str, float], m, lado: str, linea: float) -> float | None:
    """
    Probabilidad justa de `lado` con hándicap asiático `linea`, condicionada a
    que no haya devolución. 0 y ±0,5 salen exactas del 1X2; el resto, de la
    matriz de marcadores `m` del ajuste de goles (None si el ajuste falló).
    """
    if linea == 0.0:
        return p[lado] / (p["home"] + p["away"])
    if linea == 0.5:
        return p[lado] + p["draw"]
    if linea == -0.5:
        return p[lado]
    if m is None:
        return None
    from ..model.pricing import market_asian_handicap
    return market_asian_handicap(m, linea if lado == "home" else -linea)[lado]


def candidatos_handicap(p: dict[str, float], m, lineas: tuple[float, ...] | None = None
                        ) -> list[Candidato]:
    lineas = LINEAS_HANDICAP if lineas is None else lineas
    out = []
    for lado in ("home", "away"):
        for linea in lineas:
            prob = prob_handicap(p, m, lado, linea)
            if prob is not None:
                out.append(Candidato("spreads", lado, linea, prob))
    return out


def texto_handicap(selection: str, line: float, local: str, visitante: str) -> str:
    equipo = local if selection == "home" else visitante
    if line == 0:
        return f"{equipo} gana (empate devuelve)"
    if line == 0.5:
        return f"{equipo} o empate"
    if line == -0.5:
        return f"Gana {equipo}"
    return f"{equipo} {'+' if line > 0 else ''}{f'{line:g}'.replace('.', ',')} (hándicap asiático)"


def longitud_nuevo(abiertos: list[int], seis_en_mes: int) -> int | None:
    """
    Pasos del próximo reto, dados los pasos de los retos ABIERTOS y cuántos de
    6 empezaron este mes (decisión del usuario, 2026-10-08): 3 por defecto; si
    ya hay uno de 3 abierto, uno de 6 mientras vayan menos de MAX_SEIS_MES en
    el mes; después 4 y 5. Como mucho un reto abierto de cada longitud.
    """
    if 3 not in abiertos:
        return 3
    if 6 not in abiertos and seis_en_mes < MAX_SEIS_MES:
        return 6
    for n in (4, 5):
        if n not in abiertos:
            return n
    return None


def valida(o: Opcion, cuota_min: float = CUOTA_MIN, cuota_max: float = CUOTA_MAX,
           ev_min: float = EV_MIN) -> bool:
    return (o.cand.market in MERCADOS and cuota_min <= o.price <= cuota_max
            and o.ev >= ev_min)


def _orden(o: Opcion) -> tuple:
    return (round(o.ev, 6), o.cand.prob, -o.price)


def elegir(opciones: list[Opcion], **limites) -> Opcion | None:
    """El de mayor valor esperado; a igualdad, el más probable."""
    dentro = [o for o in opciones if valida(o, **limites)]
    if not dentro:
        return None
    return max(dentro, key=_orden)


def planificar(en_curso: list[tuple[int, int]], abiertos: list[int], seis_en_mes: int,
               opciones: list[Opcion], ocupados: set[str] = frozenset()
               ) -> list[tuple[int | None, int | None, Opcion]]:
    """
    Reparto del día: [(reto_id, None, opción)] para los retos que necesitan
    escalón y [(None, pasos, opción)] para los retos nuevos.

    - `en_curso`: (reto_id, escalones ganados) de los retos que esperan su
      siguiente escalón; se sirven primero, el más avanzado antes.
    - `abiertos`: pasos de TODOS los retos abiertos (también los que esperan
      resultado), para `longitud_nuevo`.
    - Un partido no se repite el mismo día ni coincide con un escalón aún sin
      liquidar (`ocupados`): dos retos no dependen del mismo resultado.
    """
    libres = sorted((o for o in opciones if valida(o)), key=_orden, reverse=True)
    usados = set(ocupados)

    def siguiente() -> Opcion | None:
        for o in libres:
            if o.match_id not in usados:
                usados.add(o.match_id)
                return o
        return None

    plan: list[tuple[int | None, int | None, Opcion]] = []
    for reto_id, _ in sorted(en_curso, key=lambda r: -r[1]):
        o = siguiente()
        if o is None:
            return plan
        plan.append((reto_id, None, o))
    abiertos = list(abiertos)
    while (n := longitud_nuevo(abiertos, seis_en_mes)) is not None:
        o = siguiente()
        if o is None:
            break
        plan.append((None, n, o))
        abiertos.append(n)
        seis_en_mes += n == 6
    return plan


@dataclass(frozen=True)
class Paso:
    paso: int
    price: float
    outcome: str | None        # None: sin liquidar · 'win' · 'loss' · 'void'


def _q(x: Decimal) -> Decimal:
    return x.quantize(_CENT, rounding=ROUND_HALF_UP)


def estado(stake: Decimal, objetivo: int, freeroll_x: float | None,
           pasos: list[Paso]) -> dict:
    """
    El estado de un reto a partir de sus escalones, sin guardar nada:

    - 'esperando': el último escalón no está liquidado (`en_juego` es lo apostado).
    - 'en_curso': hace falta elegir el siguiente escalón.
    - 'completado' / 'fallido': cerrado; `ganancia` = lo cobrado − stake.

    Un escalón 'void' (aplazado) o 'push' (hándicap entero devuelto) no cuenta
    y no mueve el saldo.
    """
    stake = Decimal(stake)
    saldo, retirado, ganados = stake, Decimal("0"), 0
    for p in sorted(pasos, key=lambda p: p.paso):
        if p.outcome is None:
            return {"estado": "esperando", "saldo": _q(saldo), "retirado": _q(retirado),
                    "ganados": ganados, "en_juego": _q(saldo), "ganancia": None}
        if p.outcome in ("void", "push"):
            continue
        if p.outcome == "loss":
            return {"estado": "fallido", "saldo": Decimal("0.00"), "retirado": _q(retirado),
                    "ganados": ganados, "en_juego": None, "ganancia": _q(retirado - stake)}
        saldo = _q(saldo * Decimal(str(p.price)))
        ganados += 1
        if freeroll_x and retirado == 0 and saldo >= Decimal(str(freeroll_x)) * stake:
            retirado, saldo = stake, saldo - stake
        if ganados >= objetivo:
            return {"estado": "completado", "saldo": _q(saldo), "retirado": _q(retirado),
                    "ganados": ganados, "en_juego": None,
                    "ganancia": _q(saldo + retirado - stake)}
    return {"estado": "en_curso", "saldo": _q(saldo), "retirado": _q(retirado),
            "ganados": ganados, "en_juego": None, "ganancia": None}


def resumen(retos: list[dict]) -> dict:
    """Historial de retos cerrados: cuántos se completan y lo que dejan."""
    cerrados = [r for r in retos if r["estado"] in ("completado", "fallido")]
    if not cerrados:
        return {"cerrados": 0, "completados": 0, "tasa_completados": None,
                "invertido": "0.00", "ganancia": "0.00", "roi": None}
    invertido = sum(Decimal(str(r["stake_inicial"])) for r in cerrados)
    ganancia = sum(Decimal(str(r["ganancia"])) for r in cerrados)
    completados = sum(1 for r in cerrados if r["estado"] == "completado")
    return {"cerrados": len(cerrados), "completados": completados,
            "tasa_completados": round(completados / len(cerrados) * 100, 1),
            "invertido": str(_q(invertido)), "ganancia": str(_q(ganancia)),
            "roi": round(float(ganancia / invertido) * 100, 1)}
