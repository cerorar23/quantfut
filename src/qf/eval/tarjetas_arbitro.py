"""
¿Arregla el árbitro el modelo de tarjetas? (pedido del usuario, 2026-10-10)

La prueba de `escalera_estadistica` (2026-10-08) dejó fuera casi todas las
líneas de tarjetas: prometían de 1 a 3 puntos de más, y fuera de la Premier
no había árbitro. Esta prueba usa solo las ligas inglesas, donde football-data
SÍ trae árbitro en cada partido (Premier y Championship), y compara el mismo
modelo con y sin el factor del árbitro.

DATOS: football-data E0 + E1, 2019/20-2024/25. Tarjetas = amarillas + rojas.

SIN FUGAS: mismo recorrido que `escalera_estadistica` (preguntar antes de
añadir) y los mismos tres tramos de temporadas:
  1. φ con 2019/20 y 2020/21;
  2. encogimiento de equipos, media vida y, en la variante con árbitro, el
     encogimiento del árbitro (`PRIORES_ARBITRO`), por pérdida logarítmica en
     2021/22, cada variante por separado;
  3. todo lo que decide, SOLO en 2022/23-2024/25.

CRITERIO, fijado ANTES de ver los resultados:
  (A) el árbitro ayuda solo si la pérdida logarítmica de prueba con árbitro
      es menor que sin él (todas las líneas de `LINEAS`, las dos ligas);
  (B) si (A) se cumple, una línea y lado se habilita para Inglaterra si pasa
      el criterio de calibración de siempre (`escalera_estadistica.evaluar`:
      cada tramo con n ≥ 50 dentro de 2·SE y déficit total ≤ 1 punto) con
      árbitro; por separado con los tramos de la escalera y los de alta
      probabilidad. Si (A) no se cumple, no se habilita nada.

Uso: python -m qf.eval.tarjetas_arbitro [--out ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..model import estadisticas_mercado as em
from . import escalera_estadistica as ee
from . import soft_vs_sharp as sv

LIGAS = {"gb.premier_league": "E0", "gb.championship": "E1"}
LINEAS = (1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5)
PRIORES_ARBITRO = (5.0, 10.0, 20.0, 40.0)


def medias(raw: pd.DataFrame, prior: float, vida: float, usar_arbitro: bool,
           prior_arbitro: float = em.PRIOR_ARBITRO) -> pd.DataFrame:
    out = []
    for div, liga in ee._partidos(raw).groupby("Div"):
        a = em.Acumulador(usar_arbitro=usar_arbitro, prior=prior, media_vida=vida,
                          prior_arbitro=prior_arbitro)
        for d in liga.to_dict("records"):
            c = ee._conteos(d, "cards")
            if c is None:
                continue
            arb = d.get("Referee") if isinstance(d.get("Referee"), str) else None
            lam = a.lambdas(d["fecha"], d["HomeTeam"], d["AwayTeam"], arb)
            if lam is not None:
                out.append({"div": div, "temporada": d["temporada"], "mercado": "cards",
                            "media": lam[0] + lam[1], "total": c[0] + c[1],
                            "arbitro": arb is not None})
            a.agregar(d["fecha"], d["HomeTeam"], d["AwayTeam"], c[0], c[1], arb)
    return pd.DataFrame(out)


def _phi(m: pd.DataFrame) -> float:
    f = m[m["temporada"].isin(ee.TEMPORADAS_PHI)]
    return round(float(((f["total"] - f["media"]) ** 2).sum() / f["media"].sum()), 4)


def perdida(m: pd.DataFrame, phi: float, temporadas) -> float:
    f = m[m["temporada"].isin(temporadas)]
    tot = []
    for r in f.to_dict("records"):
        for linea in LINEAS:
            p = min(max(em.prob_total(r["media"], phi, linea)["over"], 1e-6), 1 - 1e-6)
            tot.append(-np.log(p if r["total"] > linea else 1 - p))
    return float(np.mean(tot))


def filas(m: pd.DataFrame, phi: float, tramos) -> pd.DataFrame:
    f = m[~m["temporada"].isin(ee.TEMPORADAS_PHI + ee.TEMPORADA_AJUSTE)]
    out = []
    for r in f.to_dict("records"):
        for linea in LINEAS:
            pr = em.prob_total(r["media"], phi, linea)
            for lado in ("over", "under"):
                p = pr[lado]
                if tramos[0][0] <= p < tramos[-1][1]:
                    won = r["total"] > linea if lado == "over" else r["total"] < linea
                    out.append({"grupo": f"cards {lado} {linea:g}", "prob": p,
                                "won": won, "div": r["div"]})
    return pd.DataFrame(out)


def elegir(raw: pd.DataFrame, usar_arbitro: bool) -> dict:
    mejor = None
    priores = PRIORES_ARBITRO if usar_arbitro else (em.PRIOR_ARBITRO,)
    for prior, vida in ee.REJILLA:
        for pa in priores:
            m = medias(raw, prior, vida, usar_arbitro, pa)
            phi = _phi(m)
            ll = perdida(m, phi, ee.TEMPORADA_AJUSTE)
            if mejor is None or ll < mejor["perdida_ajuste"]:
                mejor = {"prior": prior, "media_vida": vida, "prior_arbitro": pa,
                         "phi": phi, "perdida_ajuste": round(ll, 5)}
    return mejor


def run(cache_dir: Path = Path(".local/fd_cache")) -> dict:
    raw, dataset = sv.load_csvs(LIGAS, sv.DEFAULT_SEASONS, cache_dir)
    raw = raw.copy()
    raw["temporada"] = raw["season"]
    prueba = tuple(t for t in sv.DEFAULT_SEASONS
                   if t not in ee.TEMPORADAS_PHI + ee.TEMPORADA_AJUSTE)
    out = {"dataset_sha256": dataset["sha256"], "ficheros": dataset["files"],
           "con_arbitro_pct": round(100 * float(raw["Referee"].notna().mean()), 1)}
    for nombre, usar in (("sin", False), ("con", True)):
        p = elegir(raw, usar)
        m = medias(raw, p["prior"], p["media_vida"], usar, p["prior_arbitro"])
        p["perdida_prueba"] = round(perdida(m, p["phi"], prueba), 5)
        esc = filas(m, p["phi"], ee.TRAMOS)
        alta = filas(m, p["phi"], ee.TRAMOS_ALTA)
        r_esc, r_alta = ee.evaluar(esc), ee.evaluar(alta, ee.TRAMOS_ALTA)
        p["escalera"] = r_esc
        p["escalera_que_pasan"] = sorted(k for k, v in r_esc.items() if v["pasa"])
        p["alta"] = r_alta
        p["alta_que_pasan"] = sorted(k for k, v in r_alta.items() if v["pasa"])
        p["por_liga"] = {div: sorted(k for k, v in ee.evaluar(g).items() if v["pasa"])
                         for div, g in esc.groupby("div")}
        out[nombre] = p
    ayuda = out["con"]["perdida_prueba"] < out["sin"]["perdida_prueba"]
    out["arbitro_ayuda"] = ayuda
    out["habilitar_escalera"] = out["con"]["escalera_que_pasan"] if ayuda else []
    out["habilitar_alta"] = out["con"]["alta_que_pasan"] if ayuda else []
    return out


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Tarjetas con y sin árbitro, ligas inglesas")
    a.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    txt = json.dumps(run(args.cache), indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(txt, encoding="utf-8")
    print(txt)
