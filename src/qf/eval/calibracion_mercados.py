"""
Prometido frente a real por mercado (2026-10-14).

Reúne los pronósticos LIQUIDADOS Y SELLADOS de todas las líneas que publican una
probabilidad (alta probabilidad, ampliada, escalera, parley) y del seguimiento sin publicar
de tarjetas, y compara por mercado la probabilidad media prometida con el acierto real, con el
intervalo de Wilson al 95 % del acierto. Solo lectura: no decide nada ni bloquea nada; el
control de cada línea sigue siendo `alta_prob.control` y `parley.control`.

Cómo leerlo:
- Un mismo pronóstico (partido, mercado, selección, línea) puede estar en varias líneas
  (la ampliada y el parley eligen cosas parecidas). En el total por mercado se cuenta UNA vez,
  con la primera fuente de `FUENTES`; el desglose por fuente no deduplica.
- Los nulos y devueltos (`void`, `push`) no cuentan.
- Con menos de `MIN_N` casos no se dice nada: la diferencia es ruido.

    python -m qf.eval.calibracion_mercados [--json]
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict

from ..db import query

MIN_N = 30
Z95 = 1.96
FUENTES = ("alta_prob", "alta_ext", "escalera", "parley", "tarjetas_seg")


def wilson(aciertos: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Intervalo de Wilson de una proporción."""
    if n == 0:
        return (0.0, 1.0)
    p = aciertos / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centro - margen), min(1.0, centro + margen))


def _bloque(filas: list[dict]) -> dict:
    n = len(filas)
    aciertos = sum(1 for f in filas if f["outcome"] == "win")
    prom = sum(float(f["prob"]) for f in filas) / n
    real = aciertos / n
    lo, hi = wilson(aciertos, n)
    if n < MIN_N:
        veredicto = "muestra insuficiente"
    elif prom > hi:
        veredicto = "por debajo de lo prometido"
    elif prom < lo:
        veredicto = "por encima de lo prometido"
    else:
        veredicto = "dentro de lo prometido"
    return {"n": n, "aciertos": aciertos, "prometido": round(prom * 100, 1),
            "real": round(real * 100, 1), "diferencia_pts": round((real - prom) * 100, 1),
            "ic95": [round(lo * 100, 1), round(hi * 100, 1)], "veredicto": veredicto}


def resumir(filas: list[dict]) -> dict:
    """
    `filas`: fuente, match_id, market, selection, line, prob, outcome. Solo win/loss.
    Devuelve el total por mercado (sin duplicados entre fuentes) y el desglose por fuente.
    """
    filas = [f for f in filas if f["outcome"] in ("win", "loss")]
    prioridad = {f: i for i, f in enumerate(FUENTES)}
    vistos: dict[tuple, dict] = {}
    for f in sorted(filas, key=lambda f: prioridad.get(f["fuente"], len(FUENTES))):
        vistos.setdefault((f["match_id"], f["market"], f["selection"], f["line"]), f)
    por_mercado: dict[str, list[dict]] = defaultdict(list)
    for f in vistos.values():
        por_mercado[f["market"]].append(f)
    por_fuente: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for f in filas:
        por_fuente[f["market"]][f["fuente"]].append(f)
    return {
        "min_n": MIN_N,
        "mercados": {m: {**_bloque(fs),
                         "fuentes": {s: _bloque(g) for s, g in sorted(por_fuente[m].items())}}
                     for m, fs in sorted(por_mercado.items(), key=lambda kv: -len(kv[1]))}}


def _filas() -> list[dict]:
    from ..publish import alta_prob_datos as ad
    from ..publish import alta_prob_ext as ae
    from ..publish import escalera_datos as ed
    from ..publish import parley_datos as pd
    from ..publish import tarjetas_seg as ts
    consultas = {
        "alta_prob": f"""SELECT a.match_id, a.market, a.selection, a.line, a.prob, r.outcome
            FROM alta_prob_picks a JOIN alta_prob_results r ON r.alta_id = a.alta_id
            {ad._sql_sellado()}""",
        "alta_ext": f"""SELECT a.match_id, a.market, a.selection, a.line, a.prob, r.outcome
            FROM alta_prob_ext a JOIN alta_prob_ext_results r ON r.ext_id = a.ext_id
            {ae.sql_sellado()}""",
        "escalera": f"""SELECT p.match_id, p.market, p.selection, p.line, p.prob, r.outcome
            FROM escalera_pasos p JOIN escalera_resultados r ON r.paso_id = p.paso_id
            {ed._sql_sellado()}""",
        "parley": f"""SELECT p.match_id, p.market, p.selection, p.line, p.prob, r.outcome
            FROM parley_patas p
            JOIN parley_tickets t ON t.ticket_id = p.ticket_id
            {pd._sql_sellado()}
            JOIN parley_resultados_pata r ON r.pata_id = p.pata_id""",
        "tarjetas_seg": f"""SELECT a.match_id, a.market, a.selection, a.line, a.prob, r.outcome
            FROM tarjetas_seg a JOIN tarjetas_seg_results r ON r.seg_id = a.seg_id
            {ts.sql_sellado()}""",
    }
    return [{**row, "fuente": fuente} for fuente, sql in consultas.items()
            for row in query(sql + " WHERE r.outcome IN ('win', 'loss')")]


def informe() -> dict:
    return resumir(_filas())


def _texto(inf: dict) -> str:
    lineas = [f"Prometido frente a real por mercado (solo liquidados y sellados; "
              f"{inf['min_n']} casos mínimo para opinar)\n",
              f"{'mercado':<18}{'n':>5}{'prometido':>11}{'real':>8}{'dif':>8}  IC95 real        veredicto"]
    for mercado, b in inf["mercados"].items():
        lineas.append(f"{mercado:<18}{b['n']:>5}{b['prometido']:>10}%{b['real']:>7}%"
                      f"{b['diferencia_pts']:>+8}  {b['ic95'][0]:>5}-{b['ic95'][1]:<5}%   {b['veredicto']}")
        for fuente, g in b["fuentes"].items():
            lineas.append(f"    {fuente:<14}{g['n']:>5}{g['prometido']:>10}%{g['real']:>7}%{g['diferencia_pts']:>+8}")
    return "\n".join(lineas)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Prometido frente a real por mercado")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    inf = informe()
    print(json.dumps(inf, ensure_ascii=False, indent=2) if args.json else _texto(inf))
