"""
Prueba histórica de la línea de alta probabilidad (diseño 2026-10-05, §4.1).

Repite la selección sobre football-data con el 1X2 (PSH/PSD/PSA) y el 2,5
(P>2.5 / P<2.5) de Pinnacle PRE-CIERRE (de uno a tres días antes) y compara la
probabilidad prometida con lo ocurrido, por mercado y tramo.

CRITERIO, fijado ANTES de ver los resultados: un mercado pasa si
  (a) en cada tramo con n ≥ MIN_N_TRAMO, real ≥ prometido − 2·SE, y
  (b) en conjunto, real − prometido ≥ −MAX_DEFICIT_PTS puntos.
Solo los mercados de goles que pasan entran en
`alta_prob.MERCADOS_GOLES_HABILITADOS`. El 1X2 y la doble oportunidad se
miden igual para dejar constancia. "Marca el local / el visitante" (más de 0,5
goles de cada equipo, `team_totals_home` / `team_totals_away`) se mide con el
mismo criterio y entra en `alta_prob.MERCADOS_EQUIPO_HABILITADOS`.
"Regla completa" mide la regla DESPLEGADA (solo con los mercados habilitados),
no todo lo que se mide.

AMPLIACIÓN 2026-10-09 (pedida por el usuario): se miden también ambos marcan
(sí/no), más/menos 2,5, hándicap asiático (`ap.LINEAS_HANDICAP`, del mismo
ajuste; las devoluciones no cuentan, la probabilidad es condicionada) y
córners (modelo de `model/estadisticas_mercado.py`). Córners SOLO en las
temporadas que el modelo no vio al fijar sus parámetros (φ en 2019-21,
encogimiento en 2021/22: ver eval/escalera_estadistica.py), así que la regla
con córners se mide aparte en 2022-2025. El recorte de córners a la
probabilidad del mercado (`alta_prob_datos`) no se puede medir aquí:
football-data no trae cuotas de córners.

LÍMITE: football-data solo trae la línea 2,5. Las de cuarto y gol entero que
Pinnacle cotiza en vivo no se pueden validar aquí; las cubre el control en
vivo por mercado (`alta_prob.control`).

FUGAS: la selección solo lee cuotas pre-cierre; el resultado solo se usa al
evaluar.

Uso: python -m qf.eval.alta_prob_calibracion [--rho -0.0613]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..model import estadisticas_mercado as em
from ..model.devig import devig, two_way_devig
from ..publish import alta_prob as ap
from . import soft_vs_sharp as sv
from .clv import _settle_outcome

# Las 7 ligas de formato principal (leagues.fd_code con fd_extra = FALSE).
LIGAS = {"de.bundesliga": "D1", "es.laliga": "SP1", "fr.ligue_1": "F1",
         "gb.premier_league": "E0", "it.serie_a": "I1", "nl.eredivisie": "N1",
         "pt.primeira": "P1"}
COLS = ["PSH", "PSD", "PSA", "P>2.5", "P<2.5"]
TRAMOS = ((0.80, 0.85), (0.85, 0.90), (0.90, 0.95 + 1e-9))
MIN_N_TRAMO = 100
MAX_DEFICIT_PTS = 1.0
# rho del modelo activo el 2026-10-05 (2026.09.27-010508, /model-card).
RHO_POR_DEFECTO = -0.0613


def temporadas_corners() -> tuple[str, ...]:
    """Temporadas en las que el modelo de córners no fijó nada (sin fugas)."""
    from . import escalera_estadistica as ee     # importa este módulo: aquí no
    return tuple(t for t in sv.DEFAULT_SEASONS
                 if t not in ee.TEMPORADAS_PHI + ee.TEMPORADA_AJUSTE)


def _nombre(c: ap.Candidato) -> str:
    if c.market in ("totals", "corners", "corners_home", "corners_away"):
        return f"{c.market} {c.selection} {c.line:g}"
    if c.market == "btts":
        return f"btts {c.selection}"
    if c.market == "spreads":
        return f"spreads {c.line:+g}"
    return c.market


def habilitado(c: ap.Candidato) -> bool:
    """¿Lo publica la regla DESPLEGADA?"""
    if c.market == "totals":
        return (c.selection, c.line) in ap.MERCADOS_GOLES_HABILITADOS
    if c.market.startswith("team_totals"):
        return c.market.removeprefix("team_totals_") in ap.MERCADOS_EQUIPO_HABILITADOS
    if c.market == "btts":
        return c.selection in ap.BTTS_HABILITADOS
    if c.market == "spreads":
        return c.line in ap.HANDICAP_HABILITADOS
    if c.market.startswith("corners"):
        return (c.market, c.selection, c.line) in ap.CORNERS_HABILITADOS
    return True


def medias_corners(df: pd.DataFrame) -> dict[str, tuple[float, float]]:
    """
    Córners esperados de cada partido (clave `match` de `sv._prepare`), con el
    acumulador PREGUNTADO antes de añadir el partido: sin fugas.
    """
    out: dict[str, tuple[float, float]] = {}
    if not {"HC", "AC"} <= set(df.columns):
        return out
    for _, liga in df.sort_values("date").groupby("league_id"):
        acc = em.acumulador("corners")
        for r in liga.to_dict("records"):
            if pd.isna(r["HC"]) or pd.isna(r["AC"]):
                continue
            lam = acc.lambdas(r["date"], r["HomeTeam"], r["AwayTeam"])
            if lam is not None:
                out[r["match"]] = lam
            acc.agregar(r["date"], r["HomeTeam"], r["AwayTeam"], int(r["HC"]), int(r["AC"]))
    return out


def filas(raw: pd.DataFrame, rho: float) -> pd.DataFrame:
    """
    Una fila por candidato dentro del rango, con si acertó y si era el elegido.

    Los candidatos son TODAS las líneas (`LINEAS_GOLES` y los dos lados de
    equipo): cada mercado se mide aunque no esté habilitado. Pero `elegido`
    sigue la regla DESPLEGADA: se calcula solo con los mercados habilitados
    (`MERCADOS_GOLES_HABILITADOS`, `MERCADOS_EQUIPO_HABILITADOS`), de modo que
    "regla completa" mide lo que se publica y una línea medida pero excluida
    (p. ej. "menos de 4,5") nunca es la elegida.
    """
    df = sv._prepare(raw)
    if not set(COLS) <= set(df.columns):
        return pd.DataFrame()
    df[COLS] = df[COLS].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=COLS)
    df = df[(df[COLS] > 1.0).all(axis=1)]
    from . import escalera_estadistica as ee
    corners, de_prueba = medias_corners(df), temporadas_corners()
    out = []
    for r in df.to_dict("records"):
        p1x2 = devig([r["PSH"], r["PSD"], r["PSA"]], settings.devig_method)
        p = {"home": float(p1x2[0]), "draw": float(p1x2[1]), "away": float(p1x2[2])}
        p_over, _ = two_way_devig(r["P>2.5"], r["P<2.5"], settings.devig_method)
        ajuste = ap.ajuste_goles(p, 2.5, p_over, rho)
        cands = (ap.candidatos_1x2(p) + ap.candidatos_doble(p)
                 + ap.candidatos_goles(ajuste, ap.LINEAS_GOLES)
                 + ap.candidatos_equipo(ajuste, ("home", "away"))
                 + ap.candidatos_btts(ajuste, ("yes", "no"))
                 + ap.candidatos_handicap(p, ajuste, ap.LINEAS_HANDICAP))
        hg, ag = int(r["FTHG"]), int(r["FTAG"])
        total_c = None
        reales = {}
        if r["match"] in corners and r.get("season") in de_prueba:
            lam = corners[r["match"]]
            total_c = int(r["HC"]) + int(r["AC"])
            reales = {"corners": total_c, "corners_home": int(r["HC"]),
                      "corners_away": int(r["AC"])}
            for lado in ("over", "under"):
                for linea in ee.LINEAS["corners"]:
                    cands.append(ap.Candidato("corners", lado, linea,
                                              em.prob("corners", lam, lado, linea)))
                for mercado in ("corners_home", "corners_away"):
                    for linea in ee.LINEAS_EQUIPO:
                        cands.append(ap.Candidato(mercado, lado, linea,
                                                  em.prob(mercado, lam, lado, linea)))
        elegido = ap.elegir([c for c in cands if habilitado(c)])
        for c in cands:
            if not ap.PROB_MIN <= c.prob <= ap.PROB_MAX:
                continue
            if c.market in reales:
                real = reales[c.market]
                outcome = "win" if (real > c.line) == (c.selection == "over") else "loss"
            else:
                outcome = _settle_outcome(c.market, c.selection, c.line, hg, ag)[0]
            if outcome not in ("win", "loss"):
                continue            # devolución: no cuenta (probabilidad condicionada)
            out.append({"mercado": _nombre(c), "prob": c.prob, "won": outcome == "win",
                        "elegido": c == elegido, "week": r["week"],
                        "con_corners": total_c is not None, "match": r["match"],
                        "prioridad": ap._PRIORIDAD[c.market]})
    return pd.DataFrame(out)


def evaluar(f: pd.DataFrame) -> dict[str, dict]:
    res = {}
    for nombre, g in f.groupby("mercado"):
        tramos, ok = [], True
        for lo, hi in TRAMOS:
            t = g[(g["prob"] >= lo) & (g["prob"] < hi)]
            if t.empty:
                continue
            prom, real = float(t["prob"].mean()), float(t["won"].mean())
            se = float(np.sqrt(prom * (1 - prom) / len(t)))
            decide = len(t) >= MIN_N_TRAMO
            pasa = (not decide) or real >= prom - 2 * se
            ok = ok and pasa
            tramos.append({"tramo": f"{lo:.2f}-{min(hi, 0.95):.2f}", "n": int(len(t)),
                           "prometido": round(prom * 100, 2), "real": round(real * 100, 2),
                           "se_pts": round(se * 100, 2), "decide": decide, "pasa": pasa})
        dif = round((float(g["won"].mean()) - float(g["prob"].mean())) * 100, 2)
        ok = ok and dif >= -MAX_DEFICIT_PTS
        res[str(nombre)] = {"n": int(len(g)), "prometido": round(float(g["prob"].mean()) * 100, 2),
                            "real": round(float(g["won"].mean()) * 100, 2),
                            "diferencia_pts": dif, "tramos": tramos, "pasa": bool(ok)}
    return res


def run(rho: float = RHO_POR_DEFECTO, cache_dir: Path = Path(".local/fd_cache")) -> dict:
    raw, dataset = sv.load_csvs(LIGAS, sv.DEFAULT_SEASONS, cache_dir)
    f = filas(raw, rho)
    elegidos = f[f["elegido"]].assign(mercado="regla completa")
    por_mercado = evaluar(f)
    return {"dataset_sha256": dataset["sha256"], "partidos": dataset["rows"], "rho": rho,
            "por_mercado": por_mercado,
            "regla_completa": evaluar(elegidos).get("regla completa"),
            # Córners solo tiene candidatos en 2022-2025: la regla se mide ahí también.
            "regla_completa_2022_25": evaluar(elegidos[elegidos["con_corners"]]).get("regla completa"),
            "elegidos_por_mercado": {str(k): int(v) for k, v in
                                     f[f["elegido"]]["mercado"].value_counts().items()},
            "que_pasan": sorted(k for k, v in por_mercado.items() if v["pasa"]),
            "que_no_pasan": sorted(k for k, v in por_mercado.items() if not v["pasa"])}


if __name__ == "__main__":
    ap_ = argparse.ArgumentParser(description="Prueba histórica de la línea de alta probabilidad")
    ap_.add_argument("--rho", type=float, default=RHO_POR_DEFECTO)
    ap_.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    a = ap_.parse_args()
    print(json.dumps(run(a.rho, a.cache), indent=2, ensure_ascii=False))
