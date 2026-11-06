"""Backtest del parley (fase 2): A (anterior), B0, B1, B2 sobre días fuera de muestra.

    python backtest_parley.py futbol|tenis|nba

Entrada: cands.parquet de `construir_candidatos.py` (QF_PARLEY_OUT). Por pool:
  * se parte la historia por fecha; el artefacto de calibración se ajusta SOLO con el 80 % más
    antiguo (con su propia partición 60/20/20 y embargo) y los tickets se evalúan en el 20 % final,
    después de un embargo de 7 días;
  * A  = parley anterior (5 escalones 1,90-5,00, patas 1,20-1,80, probabilidad más alta);
  * B0 = targets nuevos con mínimo de patas (parley_v2, sin calibración);
  * B1 = B0 con calibración (p prudente en la selección; categorías sin artefacto con p cruda);
  * B2 = B1 con abstención (solo patas de categorías calibradas);
  * B3 (same-game con modelo conjunto): no evaluable, no hay cuota real de paquete ni distribución conjunta.
Se congelan los parámetros: no se reajusta nada con lo visto en el test. Es una medición, no una promoción.
"""
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "src"))
from qf.eval import parley_calibracion as pc  # noqa: E402
from qf.publish import parley as legado  # noqa: E402
from qf.publish import parley_ext as ext  # noqa: E402
from qf.publish import parley_v2 as v2  # noqa: E402
from qf.publish.alta_prob import Candidato  # noqa: E402

OUT = Path(os.environ.get("QF_PARLEY_OUT", Path(__file__).parent / "salida"))
AHORA = datetime(2026, 1, 1, tzinfo=timezone.utc)
MAPA = {
    ("futbol", "1X2"): "h2h", ("futbol", "Goles O/U 2.5"): "totals", ("futbol", "Handicap asiatico .5"): "spreads",
    ("tenis", "Ganador del partido"): "h2h",
    ("nba", "Ganador partido"): "h2h", ("nba", "Handicap partido"): "spreads", ("nba", "Total puntos partido"): "totals",
    ("nba", "Props puntos jugador"): "player_points", ("nba", "Props rebotes jugador"): "player_rebounds",
    ("nba", "Props asistencias jugador"): "player_assists", ("nba", "Props triples jugador"): "player_threes",
}
POOLS = {"futbol": ["futbol"], "tenis": ["tenis"], "nba": ["nba"]}


def cargar(pool: str) -> pd.DataFrame:
    c = pd.read_parquet(OUT / "cands.parquet")
    c = c[c.sport.isin(POOLS[pool])].copy()
    c["mkt"] = [MAPA.get((s, m)) for s, m in zip(c.sport, c.market)]
    c = c.dropna(subset=["mkt", "mid"])
    if pool == "tenis":
        c = c[c.date >= "2021-01-01"]
    if pool == "nba":
        c = c[c.date >= "2024-10-22"]          # los props empiezan ahí; el resto del pool es igual
    c["line"] = np.where(c.mkt == "h2h", np.nan, 0.5)
    return c


def opciones_del_dia(z: pd.DataFrame) -> tuple[list, dict]:
    ops, gana = [], {}
    for r in z.itertuples():
        linea = None if math.isnan(r.line) else float(r.line)
        o = ext.OpcionExterna(match_id=r.mid, cand=Candidato(r.mkt, str(r.sel), linea, float(r.p)),
                              price=float(r.price_best), book="mejor", odds_source="historico",
                              odds_as_of=AHORA, deporte=r.sport)
        ops.append(o)
        gana[v2._clave(o)] = bool(r.win)
    return ops, gana


def evaluar(tickets, gana, p_ticket):
    """Lista de dicts por ticket: cuota, patas, p central, gana."""
    out = []
    for target, legs in tickets:
        out.append({"target": target, "patas": len(legs), "cuota": math.prod(o.price for o in legs),
                    "p": p_ticket(legs), "gana": all(gana[v2._clave(o)] for o in legs)})
    return out


def resumen(filas, dias, n_targets):
    if not filas:
        return {"tickets": 0}
    p = np.clip(np.array([f["p"] for f in filas]), 1e-6, 1 - 1e-6)
    y = np.array([f["gana"] for f in filas], dtype=float)
    q = np.array([f["cuota"] for f in filas])
    return {"tickets": len(filas), "cobertura": round(len(filas) / (dias * n_targets), 3),
            "patas": round(float(np.mean([f["patas"] for f in filas])), 2), "cuota": round(float(q.mean()), 2),
            "p_media": round(float(p.mean()), 4), "acierto": round(float(y.mean()), 4),
            "brier": round(float(np.mean((p - y) ** 2)), 4),
            "logloss": round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 4),
            "roi_observado": round(float((y * q - 1).mean()), 4)}


def main(pool: str):
    c = cargar(pool)
    fechas = np.sort(c.date.unique())
    corte = fechas[int(len(fechas) * 0.8)]
    prueba_desde = corte + np.timedelta64(pc.EMBARGO_DIAS, "D")
    previo = c[c.date < corte]
    registros = [dict(fecha=r.date.to_datetime64(), deporte=r.sport, mercado=r.mkt, cuota=r.price_best, p=r.p, gana=r.win)
                 for r in previo.itertuples()]
    art = pc.construir_artefacto(registros, nombre=f"backtest-{pool}")
    (OUT / f"artefacto_calibracion_{pool}.json").write_text(json.dumps(art, indent=1, default=str), encoding="utf-8")
    cal = pc.Calibrador(art)
    estados = defaultdict(int)
    for v in art["categorias"].values():
        estados[v["estado"]] += 1
    print(pool, "categorías:", dict(estados), "| prueba desde", str(prueba_desde)[:10], "| días de prueba",
          int((fechas >= prueba_desde).sum()))
    prueba = c[c.date >= prueba_desde]
    res = {k: [] for k in ("A", "B0", "B1", "B2")}
    dias = 0
    for fecha, z in prueba.groupby("date"):
        ops, gana = opciones_del_dia(z)
        if len(ops) < 4:
            continue
        dias += 1
        crudo = lambda legs: math.prod(o.cand.prob for o in legs)
        centrado = lambda legs: math.prod(
            (cal.p_calibrada(o.deporte, o.cand.market, o.price, o.cand.prob) or o.cand.prob) for o in legs)
        if pool == "futbol":
            patas = legado.filtrar(ops, AHORA)
            res["A"] += evaluar(legado.armar_dia(patas), gana, crudo)
        res["B0"] += evaluar([(t.target, t.legs) for t in v2.armar_plan(ops).tickets], gana, crudo)
        mapa = cal.para_opciones(ops)
        res["B1"] += evaluar([(t.target, t.legs) for t in v2.armar_plan(ops, calibracion=mapa).tickets], gana, centrado)
        calibradas = pc.filtrar_calibradas(ops, mapa)
        if len(calibradas) >= 2:
            res["B2"] += evaluar([(t.target, t.legs) for t in v2.armar_plan(calibradas, calibracion=mapa).tickets],
                                 gana, centrado)
    informe = {"pool": pool, "dias_evaluados": dias, "prueba_desde": str(prueba_desde)[:10],
               "categorias": dict(estados),
               "estrategias": {k: resumen(v, dias, 5 if k == "A" else 4) for k, v in res.items() if v or k != "A"},
               "por_target": {k: {str(t): resumen([f for f in v if f["target"] == t], dias, 1)
                                  for t in sorted({f["target"] for f in v})} for k, v in res.items() if v},
               "B3": "no evaluable: sin cuota real del paquete ni distribución conjunta"}
    (OUT / f"backtest_{pool}.json").write_text(json.dumps(informe, indent=1), encoding="utf-8")
    print(json.dumps(informe["estrategias"], indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "futbol")
