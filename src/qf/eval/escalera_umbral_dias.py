"""
T5 (2026-11-09): ¿un umbral de probabilidad que depende de los días que quedan
mejora la escalera? (solo medición; no toca `escalera.py`)

Hoy `escalera.umbral` solo mira la probabilidad ya ganada y los escalones que
faltan. Se prueban dos familias sobre el mismo simulador de
`escalera_multideporte.simular` (mismos candidatos, tope por deporte, plazo y
un escalón al día):
  * exigente al inicio: umbral = base + a·(días_restantes-1)/(DIAS_MAX-1);
  * afloja al final:   umbral = base − b·(1 − (días_restantes-1)/(DIAS_MAX-1)),
    sin bajar de PROB_MIN.
Se ve en una ventana (fútbol+tenis 2019-2025) y se confirma en otra
independiente (tres deportes 2023-2025). Criterio fijado antes de medir: una
política entra si, en AMBAS ventanas, baja los expirados sin subir los fallidos
y no baja los completados.

Uso: python -m qf.eval.escalera_umbral_dias [--cache .local/fd_cache]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ..publish import escalera as es
from . import escalera_multideporte as em

POLITICAS = {"base": (0.0, 0.0), "inicio+0.02": (0.02, 0.0), "inicio+0.04": (0.04, 0.0),
             "final-0.02": (0.0, 0.02), "final-0.04": (0.0, 0.04),
             "inicio+0.02/final-0.02": (0.02, 0.02)}


def umbral(objetivo: float, prob: float, restantes: int, dias_rest: int, a: float, b: float) -> float:
    base = es.umbral(objetivo, prob, restantes)
    f = (dias_rest - 1) / (es.DIAS_MAX - 1)             # 1 el primer día, 0 el último
    return max(es.PROB_MIN, base + a * f - b * (1 - f))


def simular(c: pd.DataFrame, deportes, desde: str, hasta: str, a: float, b: float,
            pasos: int = 2) -> dict:
    d = c[c["deporte"].isin(deportes) & (c["price"] >= es.CUOTA_MIN)
          & (c["price"] <= es.CUOTA_MAX) & (c["p"] <= c["deporte"].map(em.TOPE))]
    d = d[(d["fecha"] >= desde) & (d["fecha"] <= hasta)].assign(dia=lambda x: x["fecha"].dt.normalize())
    pool = {k: g.sort_values(["p", "price"], ascending=False) for k, g in d.groupby("dia")}
    calendario = pd.date_range(pd.Timestamp(desde), pd.Timestamp(hasta), freq="D")
    retos, i = [], 0
    while i < len(calendario):
        g = pool.get(calendario[i])
        if g is None or not (g["p"] >= umbral(es.PROB_RETO, 1.0, pasos, es.DIAS_MAX, a, b)).any():
            i += 1
            continue
        saldo, prob, n, estado, fin = 1.0, 1.0, 0, "expirado", es.DIAS_MAX - 1
        for j in range(min(es.DIAS_MAX, len(calendario) - i)):
            g = pool.get(calendario[i + j])
            usados, hoy = set(), 0
            for row in ([] if g is None else g.itertuples()):
                if hoy >= es.POR_DIA:
                    break
                if row.evento in usados or row.p < umbral(es.PROB_RETO, prob, pasos - n,
                                                          es.DIAS_MAX - j, a, b):
                    continue
                usados.add(row.evento)
                hoy, n, prob = hoy + 1, n + 1, prob * row.p
                if not row.won:
                    estado = "fallido"
                    break
                saldo *= row.price
                if n >= pasos:
                    estado = "completado"
                    break
            if estado != "expirado":
                fin = j
                break
        retos.append({"estado": estado, "dias": fin + 1, "prob": prob,
                      "ganancia": -1.0 if estado == "fallido" else saldo - 1.0})
        i += fin + 1
    r = pd.DataFrame(retos)
    pct = lambda e: round(float((r["estado"] == e).mean()) * 100, 1)  # noqa: E731
    return {"retos": int(len(r)), "completados_pct": pct("completado"), "fallidos_pct": pct("fallido"),
            "expirados_pct": pct("expirado"), "dias_medios": round(float(r["dias"].mean()), 1),
            "roi_pct": round(float(r["ganancia"].mean()) * 100, 1)}


def run(cache: Path, nba: Path, tenis: Path) -> dict:
    c = em.candidatos(cache, nba, tenis)
    out = {}
    for ventana in ("futbol_tenis_2019_2025", "tres_deportes_2023_2025"):
        deps, desde, hasta = em.VENTANAS[ventana]
        out[ventana] = {n: simular(c, deps, desde, hasta, a, b) for n, (a, b) in POLITICAS.items()}
    entran = []
    for n in POLITICAS:
        if n == "base":
            continue
        ok = all(out[v][n]["expirados_pct"] < out[v]["base"]["expirados_pct"]
                 and out[v][n]["fallidos_pct"] <= out[v]["base"]["fallidos_pct"]
                 and out[v][n]["completados_pct"] >= out[v]["base"]["completados_pct"] for v in out)
        if ok:
            entran.append(n)
    out["entran"] = entran
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    ap.add_argument("--nba", type=Path, default=em.NBA)
    ap.add_argument("--tenis", type=Path, default=em.TENIS)
    a = ap.parse_args()
    print(json.dumps(run(a.cache, a.nba, a.tenis), indent=1, ensure_ascii=False))
