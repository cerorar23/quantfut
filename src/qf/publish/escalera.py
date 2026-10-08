"""
Reto escalera: cada escalón apuesta TODO el saldo a un pronóstico; el reto se
completa al ganar `PASOS` escalones y se pierde al fallar uno (pedido del
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
4. Un escalón al día como máximo y solo cuando el anterior está liquidado.
   Si ningún partido cumple, no se apuesta: un reto puede durar semanas.
5. Freeroll: al llegar a `FREEROLL_X` veces el stake se retira la inversión y
   el resto sigue sin riesgo propio.

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
PASOS = 6
STAKE = Decimal("10.00")
FREEROLL_X = 2.5
EV_MIN = 0.0
MAX_EDAD_PRECIO = timedelta(hours=6)
HORIZONTE = timedelta(hours=36)
# Líneas de goles candidatas: las validadas para alta probabilidad más la 2,5,
# que es la línea que Pinnacle cotiza directamente (sin ajuste).
LINEAS_GOLES: tuple[tuple[str, float], ...] = (
    ("over", 1.5), ("under", 3.5), ("over", 2.5), ("under", 2.5))
MERCADOS = ("h2h", "totals", "team_totals_home", "team_totals_away")
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


def valida(o: Opcion, cuota_min: float = CUOTA_MIN, cuota_max: float = CUOTA_MAX,
           ev_min: float = EV_MIN) -> bool:
    return (o.cand.market in MERCADOS and cuota_min <= o.price <= cuota_max
            and o.ev >= ev_min)


def elegir(opciones: list[Opcion], **limites) -> Opcion | None:
    """El de mayor valor esperado; a igualdad, el más probable."""
    dentro = [o for o in opciones if valida(o, **limites)]
    if not dentro:
        return None
    return max(dentro, key=lambda o: (round(o.ev, 6), o.cand.prob, -o.price))


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

    Un escalón 'void' (partido aplazado) no cuenta y no mueve el saldo.
    """
    stake = Decimal(stake)
    saldo, retirado, ganados = stake, Decimal("0"), 0
    for p in sorted(pasos, key=lambda p: p.paso):
        if p.outcome is None:
            return {"estado": "esperando", "saldo": _q(saldo), "retirado": _q(retirado),
                    "ganados": ganados, "en_juego": _q(saldo), "ganancia": None}
        if p.outcome == "void":
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
