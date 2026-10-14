"""
Parley del día (pedido del usuario, 2026-10-11).

Cada día, 1 a 5 parlays de cuota total 1,90-5,00: uno por ESCALÓN de cuota y,
en cada escalón, la combinación MÁS PROBABLE de todos los mercados que ya
calcula la escalera. Decisiones del usuario: escalones de cuota; un partido en
un solo parlay del día; solo probabilidad, sin filtro de valor.

LO QUE NO PROMETE: elegir por probabilidad sube el acierto, no el valor. El
margen de la casa se paga en CADA pata y se multiplica: a la larga los
parlays pierden aunque acierten lo prometido. El historial lo enseña entero.

Probabilidad del parlay = producto de sus patas (partidos distintos). Un sesgo
pequeño por pata se multiplica; por eso el control por escalón (`control`)
pausa el escalón que acierte por debajo de lo prometido.

Este módulo es la parte pura. La base de datos está en `parley_datos.py`.
"""
from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime

from ..eval.soft_vs_sharp import MIN_WEEKS, _weekly_ci
from . import alta_prob as ap
from .escalera import MERCADOS, Opcion

ESCALONES: tuple[tuple[int, float, float], ...] = (
    (1, 1.90, 2.20), (2, 2.20, 2.70), (3, 2.70, 3.40), (4, 3.40, 4.30), (5, 4.30, 5.00))
# La doble oportunidad solo entra en el parley (cuota real de API-Football desde el 2026-10-12).
MERCADOS_PARLEY = MERCADOS + ("double_chance",)
# Cuota de CADA pata (decisión del usuario, 2026-10-13): de 1,20 a 1,80, o sea pronósticos de
# probabilidad alta/media y sin patas largas. La cuota TOTAL del parley sigue en ESCALONES.
CUOTA_MIN_PATA, CUOTA_MAX_PATA = 1.20, 1.80
# Valor esperado por encima del cual la cuota se da por error de la casa
# (11-oct: William Hill pagaba a Deportivo a 19,00 con el mercado en ~5).
EV_ERRONEA = 0.25
MIN_PATAS, MAX_PATAS = 2, 6
# Rejilla de la búsqueda: ancho de celda en ln(cuota) y combinaciones por celda.
_CELDA = 0.002
_POR_CELDA = 2


def en_escalon(cuota: float, escalon: int) -> bool:
    """Redondeado a 6 decimales: 1,25 × 1,76 es 2,20 y va al escalón 2, no al 1."""
    _, lo, hi = ESCALONES[escalon - 1]
    cuota = round(cuota, 6)
    ultimo = escalon == ESCALONES[-1][0]
    return lo <= cuota and (cuota < hi or (ultimo and cuota <= hi))


def filtrar(opciones: list[Opcion], now: datetime) -> list[Opcion]:
    """
    Patas que pueden entrar: mercado conocido, cuota entre `CUOTA_MIN_PATA` y
    `CUOTA_MAX_PATA`, sin cuota errónea, sin fuga. La cuota llega de columnas REAL (float4: 1,76 es 1,7599999…) y
    se redondea a 4 decimales, que es como la cotizan las casas.
    """
    return [replace(o, price=round(o.price, 4)) for o in opciones
            if o.cand.market in MERCADOS_PARLEY
            and CUOTA_MIN_PATA <= round(o.price, 4) <= CUOTA_MAX_PATA
            and o.ev <= EV_ERRONEA
            and (o.odds_as_of is None or o.odds_as_of <= now)]


def _meter(estados: dict, clave: tuple[int, int], e: tuple) -> None:
    lista = estados.setdefault(clave, [])
    lista.append(e)
    lista.sort(key=lambda x: -x[0])
    del lista[_POR_CELDA:]


def _clave_orden(sel: tuple[Opcion, ...]) -> tuple:
    """Más probable; luego menos patas; luego match_id ascendente."""
    return (-round(math.prod(o.cand.prob for o in sel), 12), len(sel),
            sorted(o.match_id for o in sel))


def buscar(patas: list[Opcion], escalon: int) -> tuple[Opcion, ...] | None:
    """
    La combinación más probable del escalón: como mucho una pata por partido,
    de MIN_PATAS a MAX_PATAS patas. Mochila de elección múltiple sobre
    ln(cuota): cada celda (patas, ln cuota) guarda sus `_POR_CELDA` mejores
    combinaciones con la suma exacta, y al final se verifica la cuota exacta.
    No se podan patas "dominadas" (más baratas y menos probables): con techo
    de cuota, la más barata puede ser la única que no se pasa del escalón.
    """
    por_partido: dict[str, list[Opcion]] = {}
    for o in patas:
        por_partido.setdefault(o.match_id, []).append(o)
    _, lo, hi = ESCALONES[escalon - 1]
    techo = math.log(hi) + 1e-12
    estados: dict[tuple[int, int], list[tuple]] = {(0, 0): [(0.0, 0.0, ())]}
    for mid in sorted(por_partido):
        opciones = por_partido[mid]
        nuevos = {k: list(v) for k, v in estados.items()}
        for (k, _), lista in estados.items():
            if k == MAX_PATAS:
                continue
            for lp, s, sel in lista:
                for o in opciones:
                    s2 = s + math.log(o.price)
                    if s2 > techo:
                        continue
                    _meter(nuevos, (k + 1, int(s2 // _CELDA)),
                           (lp + math.log(o.cand.prob), s2, sel + (o,)))
        estados = nuevos
    finales = [sel for (k, _), lista in estados.items() if k >= MIN_PATAS
               for _, _, sel in lista
               if en_escalon(math.prod(o.price for o in sel), escalon)]
    return min(finales, key=_clave_orden) if finales else None


def armar_dia(patas: list[Opcion], pausados: set[int] | frozenset = frozenset()
              ) -> list[tuple[int, tuple[Opcion, ...]]]:
    """Del escalón más bajo al más alto, sin repetir partido; el que no sale se salta."""
    usados: set[str] = set()
    out = []
    for escalon, _, _ in ESCALONES:
        if escalon in pausados:
            continue
        sel = buscar([o for o in patas if o.match_id not in usados], escalon)
        if sel is None:
            continue
        out.append((escalon, sel))
        usados |= {o.match_id for o in sel}
    return out


def liquidar(patas: list[tuple[str | None, float, float]]) -> dict | None:
    """(outcome, cuota, prob) de cada pata → resultado del ticket, o None si falta alguna."""
    if any(outcome is None for outcome, _, _ in patas):
        return None
    factor = 1.0
    for outcome, price, _ in patas:
        factor *= price if outcome == "win" else 0.0 if outcome == "loss" else 1.0
    outcomes = {outcome for outcome, _, _ in patas}
    res = "perdido" if "loss" in outcomes else "ganado" if "win" in outcomes else "nulo"
    return {"outcome": res, "factor_pago": round(factor, 4),
            "prob_efectiva": math.prod(p for o, _, p in patas if o in ("win", "loss"))}


def _contados(liquidados: list[dict]) -> list[dict]:
    """Los nulos no cuentan; 'ganado' es el acierto."""
    return [{**r, "outcome": "win" if r["outcome"] == "ganado" else "loss"}
            for r in liquidados if r["outcome"] != "nulo"]


def control(liquidados: list[dict]) -> dict:
    """
    ¿Promete de más algún escalón? Mismo criterio que la alta probabilidad
    (`alta_prob.control`): con n ≥ MIN_N_CONTROL, fallo grosero (z ≤ Z_GROSERO)
    pausa ya; con ≥ MIN_SEMANAS_CONTROL semanas, IC99 de (acertado − prometido)
    entero bajo cero pausa. `liquidados`: escalon, prob (efectiva), outcome, kickoff_utc.
    """
    filas = _contados(liquidados)
    if not filas:
        return {"pausados": [], "motivos": ["Sin parlays liquidados todavía"]}
    f = ap._marco(filas)
    pausados, motivos = [], []
    for escalon, g in f.groupby("escalon"):
        nombre = f"escalón {int(escalon)}"
        if len(g) < ap.MIN_N_CONTROL:
            motivos.append(f"{nombre}: muestra insuficiente ({len(g)} < {ap.MIN_N_CONTROL})")
            continue
        z = ap._z(g)
        if z <= ap.Z_GROSERO:
            pausados.append(int(escalon))
            motivos.append(f"{nombre}: acierto real muy por debajo del prometido "
                           f"(z {z:.1f}, {len(g)} parlays)")
            continue
        if g["week"].nunique() < ap.MIN_SEMANAS_CONTROL:
            motivos.append(f"{nombre}: muestra insuficiente "
                           f"(menos de {ap.MIN_SEMANAS_CONTROL} semanas)")
            continue
        ic = _weekly_ci(g["diff"].to_numpy(float), g["week"].to_numpy(),
                        level=ap.NIVEL_IC_CONTROL)
        if ic is None:
            motivos.append(f"{nombre}: muestra insuficiente (menos de {MIN_WEEKS} semanas)")
            continue
        if ic[1] < 0:
            pausados.append(int(escalon))
            motivos.append(f"{nombre}: acierto real por debajo del prometido "
                           f"(IC99 {ic[0] * 100:+.1f} a {ic[1] * 100:+.1f} puntos)")
    return {"pausados": sorted(pausados), "motivos": motivos}


def _bloque(filas: list[dict]) -> dict:
    n = len(filas)
    if not n:
        return {"n": 0, "aciertos": 0, "prob_media": None, "acierto_real": None,
                "unidades": 0.0, "roi": None}
    aciertos = sum(1 for r in filas if r["outcome"] == "ganado")
    unidades = sum(float(r["factor_pago"]) - 1.0 for r in filas)
    return {"n": n, "aciertos": aciertos,
            "prob_media": round(sum(float(r["prob"]) for r in filas) / n * 100, 1),
            "acierto_real": round(aciertos / n * 100, 1),
            "unidades": round(unidades, 2), "roi": round(unidades / n * 100, 1)}


def resumen(liquidados: list[dict]) -> dict:
    """A 1 unidad por parlay; sin nulos."""
    filas = [r for r in liquidados if r["outcome"] != "nulo"]
    escalones = sorted({int(r["escalon"]) for r in filas})
    return {"total": _bloque(filas),
            "por_escalon": {str(e): _bloque([r for r in filas if int(r["escalon"]) == e])
                            for e in escalones}}
