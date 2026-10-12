"""
Prueba histórica de los mercados estadísticos de la escalera (decisión del
usuario, 2026-10-08): córners y tarjetas (amarillas + rojas) con
`model/estadisticas_mercado.py`, sin cuotas; y ambos anotan / goles con el
ajuste de goles de Pinnacle (el mismo de alta probabilidad).

DATOS: football-data, las 7 ligas de formato principal, 2019-2025 (córners
HC/AC, tarjetas HY/AY/HR/AR; árbitro solo en la Premier).

SIN FUGAS: se recorre por fecha y cada partido se PREGUNTA al acumulador
antes de AÑADIRLO. Tres tramos de temporadas que no se mezclan:
  1. φ (sobredispersión) con 2019/20 y 2020/21;
  2. el encogimiento y la media vida (`REJILLA`) por pérdida logarítmica en
     2021/22, con el φ de (1) recalculado para cada combinación;
  3. el criterio de calibración SOLO en 2022/23-2024/25, que ni (1) ni (2) ven.
Primera versión (encogimiento 6, media vida 180): prometía de más en los
extremos (dice 84 %, sale 80 %), por eso existe el paso (2).

CRITERIO, fijado ANTES de ver los resultados (el de alta probabilidad), por
mercado, línea y lado:
  (a) en cada tramo con n ≥ MIN_N_TRAMO, real ≥ prometido − 2·SE, y
  (b) en conjunto, real − prometido ≥ −MAX_DEFICIT_PTS puntos.

CÓRNERS DE CADA EQUIPO y "más de 6,5" (2026-10-09, pedido del usuario): el
mismo acumulador da los córners esperados de cada lado; su φ se estima aparte
con 2019-21 (la dispersión de un equipo no es la del total). Se evalúan con
los tramos de la escalera y con los de alta probabilidad (80-95 %).

Uso: python -m qf.eval.escalera_estadistica [--goles] [--fijos] [--out ...]
(--goles añade ambos anotan y goles: ~40 min por el ajuste de cada partido;
--fijos usa `em.PARAMETROS` en vez de volver a elegirlos).
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
from ..model.pricing import score_matrix
from ..publish import alta_prob as ap
from . import alta_prob_calibracion as apc
from . import soft_vs_sharp as sv

TEMPORADAS_PHI = ("1920", "2021")
TEMPORADA_AJUSTE = ("2122",)
REJILLA = [(prior, vida) for prior in (6.0, 12.0, 20.0, 30.0, 50.0, 80.0, 120.0, 200.0)
           for vida in (180.0, 365.0)]
LINEAS = {"corners": (6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5),
          "cards": (1.5, 2.5, 3.5, 4.5, 5.5, 6.5)}
COLUMNAS = {"corners": ("HC", "AC"), "cards": None}
TRAMOS = ((0.60, 0.70), (0.70, 0.80), (0.80, 0.90), (0.90, 0.97))
TRAMOS_ALTA = ((0.80, 0.85), (0.85, 0.90), (0.90, 0.95 + 1e-9))
LINEAS_EQUIPO = (1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5)
MIN_N_TRAMO = apc.MIN_N_TRAMO
MAX_DEFICIT_PTS = apc.MAX_DEFICIT_PTS


def _conteos(d: dict, mercado: str) -> tuple[int, int] | None:
    try:
        if mercado == "corners":
            v = (d["HC"], d["AC"])
        else:
            v = (d["HY"] + d["HR"], d["AY"] + d["AR"])
        if any(pd.isna(x) for x in v):
            return None
        return int(v[0]), int(v[1])
    except (KeyError, TypeError, ValueError):
        return None


def _partidos(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["fecha"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["fecha", "HomeTeam", "AwayTeam"])
    return df.sort_values("fecha")


def medias(raw: pd.DataFrame, prior: float = em.PRIOR_PARTIDOS,
           vida: float = em.MEDIA_VIDA_DIAS) -> pd.DataFrame:
    """Una fila por partido y mercado con la media predicha y el total real."""
    out = []
    for div, liga in _partidos(raw).groupby("Div"):
        acc = {"corners": em.Acumulador(prior=prior, media_vida=vida),
               "cards": em.Acumulador(usar_arbitro=True, prior=prior, media_vida=vida)}
        for d in liga.to_dict("records"):
            arb = d.get("Referee") if isinstance(d.get("Referee"), str) else None
            for mercado, a in acc.items():
                c = _conteos(d, mercado)
                if c is None:
                    continue
                lam = a.lambdas(d["fecha"], d["HomeTeam"], d["AwayTeam"], arb)
                if lam is not None:
                    out.append({"div": div, "temporada": d["temporada"], "mercado": mercado,
                                "media": lam[0] + lam[1], "total": c[0] + c[1],
                                "arbitro": arb is not None,
                                "lam_l": lam[0], "lam_v": lam[1], "c_l": c[0], "c_v": c[1]})
                a.agregar(d["fecha"], d["HomeTeam"], d["AwayTeam"], c[0], c[1], arb)
    return pd.DataFrame(out)


def phi(m: pd.DataFrame) -> dict[str, float]:
    """φ = Σ(y − μ)² / Σμ en las temporadas de ajuste."""
    f = m[m["temporada"].isin(TEMPORADAS_PHI)]
    return {k: round(float(((g["total"] - g["media"]) ** 2).sum() / g["media"].sum()), 4)
            for k, g in f.groupby("mercado")}


def phi_equipo(m: pd.DataFrame) -> float:
    """φ de los córners de UN equipo, con los dos lados, en las temporadas de φ."""
    f = m[m["temporada"].isin(TEMPORADAS_PHI) & (m["mercado"] == "corners")]
    y = pd.concat([f["c_l"], f["c_v"]]).to_numpy(float)
    mu = pd.concat([f["lam_l"], f["lam_v"]]).to_numpy(float)
    return round(float(((y - mu) ** 2).sum() / mu.sum()), 4)


def filas_equipo(m: pd.DataFrame, phi_e: float, tramos=TRAMOS) -> pd.DataFrame:
    """Córners de cada equipo ("corners_home over 3.5"), solo temporadas de prueba."""
    f = m[~m["temporada"].isin(TEMPORADAS_PHI + TEMPORADA_AJUSTE) & (m["mercado"] == "corners")]
    out = []
    for r in f.to_dict("records"):
        for lado, lam, real in (("home", r["lam_l"], r["c_l"]), ("away", r["lam_v"], r["c_v"])):
            for linea in LINEAS_EQUIPO:
                pr = em.prob_total(lam, phi_e, linea)
                for sel in ("over", "under"):
                    p = pr[sel]
                    if tramos[0][0] <= p < tramos[-1][1]:
                        won = real > linea if sel == "over" else real < linea
                        out.append({"grupo": f"corners_{lado} {sel} {linea:g}", "prob": p, "won": won})
    return pd.DataFrame(out)


def perdida(m: pd.DataFrame, phis: dict[str, float], mercado: str) -> float:
    """Pérdida logarítmica media de todas las líneas en la temporada de ajuste."""
    f = m[m["temporada"].isin(TEMPORADA_AJUSTE) & (m["mercado"] == mercado)]
    tot = []
    for r in f.to_dict("records"):
        for linea in LINEAS[mercado]:
            pr = em.prob_total(r["media"], phis[mercado], linea)["over"]
            pr = min(max(pr, 1e-6), 1 - 1e-6)
            tot.append(-np.log(pr if r["total"] > linea else 1 - pr))
    return float(np.mean(tot))


def elegir_parametros(raw: pd.DataFrame) -> dict[str, dict]:
    elegidos = {}
    for mercado in ("corners", "cards"):
        mejor = None
        for prior, vida in REJILLA:
            m = medias(raw, prior, vida)
            phis = phi(m)
            ll = perdida(m, phis, mercado)
            if mejor is None or ll < mejor["perdida"]:
                mejor = {"prior": prior, "media_vida": vida, "phi": phis[mercado],
                         "perdida": round(ll, 5)}
        elegidos[mercado] = mejor
    return elegidos


def filas(m: pd.DataFrame, phis: dict[str, float], tramos=TRAMOS) -> pd.DataFrame:
    f = m[~m["temporada"].isin(TEMPORADAS_PHI + TEMPORADA_AJUSTE)]
    out = []
    for r in f.to_dict("records"):
        for linea in LINEAS[r["mercado"]]:
            pr = em.prob_total(r["media"], phis[r["mercado"]], linea)
            for lado in ("over", "under"):
                p = pr[lado]
                if tramos[0][0] <= p < tramos[-1][1]:
                    won = r["total"] > linea if lado == "over" else r["total"] < linea
                    out.append({"grupo": f"{r['mercado']} {lado} {linea:g}", "prob": p, "won": won})
    return pd.DataFrame(out)


def filas_goles(raw: pd.DataFrame, rho: float) -> pd.DataFrame:
    """Ambos anotan y goles desde el ajuste de goles de Pinnacle pre-cierre."""
    df = sv._prepare(raw)
    df[apc.COLS] = df[apc.COLS].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=apc.COLS)
    df = df[(df[apc.COLS] > 1.0).all(axis=1)]
    out = []
    for r in df.to_dict("records"):
        q = devig([r["PSH"], r["PSD"], r["PSA"]], settings.devig_method)
        p = {"home": float(q[0]), "draw": float(q[1]), "away": float(q[2])}
        p_over, _ = two_way_devig(r["P>2.5"], r["P<2.5"], settings.devig_method)
        aj = ap.ajuste_goles(p, 2.5, p_over, rho)
        if aj is None:
            continue
        mat = score_matrix(aj["lambda"], aj["mu"], aj["rho"])
        si = float(1.0 - mat[0, :].sum() - mat[:, 0].sum() + mat[0, 0])
        hg, ag = int(r["FTHG"]), int(r["FTAG"])
        for grupo, prob, won in (("btts yes", si, hg > 0 and ag > 0),
                                 ("btts no", 1.0 - si, not (hg > 0 and ag > 0))):
            if TRAMOS[0][0] <= prob < TRAMOS[-1][1]:
                out.append({"grupo": grupo, "prob": prob, "won": won})
    return pd.DataFrame(out)


def evaluar(f: pd.DataFrame, tramos_eval=TRAMOS) -> dict[str, dict]:
    res = {}
    for nombre, g in f.groupby("grupo"):
        tramos, ok = [], True
        for lo, hi in tramos_eval:
            t = g[(g["prob"] >= lo) & (g["prob"] < hi)]
            if t.empty:
                continue
            prom, real = float(t["prob"].mean()), float(t["won"].mean())
            se = float(np.sqrt(prom * (1 - prom) / len(t)))
            decide = len(t) >= MIN_N_TRAMO
            pasa = (not decide) or real >= prom - 2 * se
            ok = ok and pasa
            tramos.append({"tramo": f"{lo:.2f}-{hi:.2f}", "n": int(len(t)),
                           "prometido": round(prom * 100, 2), "real": round(real * 100, 2),
                           "se_pts": round(se * 100, 2), "decide": decide, "pasa": pasa})
        dif = round((float(g["won"].mean()) - float(g["prob"].mean())) * 100, 2)
        ok = ok and dif >= -MAX_DEFICIT_PTS
        res[str(nombre)] = {"n": int(len(g)), "prometido": round(float(g["prob"].mean()) * 100, 2),
                            "real": round(float(g["won"].mean()) * 100, 2),
                            "diferencia_pts": dif, "tramos": tramos, "pasa": bool(ok)}
    return res


def run(goles: bool = False, rho: float = apc.RHO_POR_DEFECTO,
        cache_dir: Path = Path(".local/fd_cache"), fijos: bool = False) -> dict:
    raw, dataset = sv.load_csvs(apc.LIGAS, sv.DEFAULT_SEASONS, cache_dir)
    raw = raw.copy()
    raw["temporada"] = raw["season"] if "season" in raw.columns else raw.get("Season")
    params = ({k: dict(em.PARAMETROS[k]) for k in ("corners", "cards")} if fijos
              else elegir_parametros(raw))
    filas_test = []
    for mercado, pm in params.items():
        m = medias(raw, pm["prior"], pm["media_vida"])
        filas_test.append(filas(m[m["mercado"] == mercado], {mercado: pm["phi"]}))
    res = evaluar(pd.concat(filas_test, ignore_index=True))
    phis = {k: v["phi"] for k, v in params.items()}
    if goles:
        res.update(evaluar(filas_goles(raw, rho)))
    # Córners de cada equipo y la misma prueba en el rango de alta probabilidad.
    mc = medias(raw, params["corners"]["prior"], params["corners"]["media_vida"])
    phi_e = phi_equipo(mc)
    res.update(evaluar(filas_equipo(mc, phi_e)))
    alta = evaluar(pd.concat([filas(mc[mc["mercado"] == "corners"],
                                    {"corners": params["corners"]["phi"]}, TRAMOS_ALTA),
                              filas_equipo(mc, phi_e, TRAMOS_ALTA)], ignore_index=True),
                   TRAMOS_ALTA)
    return {"dataset_sha256": dataset["sha256"], "phi": phis, "parametros": params,
            "phi_corners_equipo": phi_e,
            "alta_probabilidad": alta,
            "alta_que_pasan": sorted(k for k, v in alta.items() if v["pasa"]),
            "partidos_con_media": {k: int(v) for k, v in m["mercado"].value_counts().items()},
            "con_arbitro": int(m[(m["mercado"] == "cards") & m["arbitro"]].shape[0]),
            "por_grupo": res,
            "que_pasan": sorted(k for k, v in res.items() if v["pasa"])}


if __name__ == "__main__":
    a = argparse.ArgumentParser(description="Prueba histórica de córners, tarjetas y ambos anotan")
    a.add_argument("--goles", action="store_true")
    a.add_argument("--fijos", action="store_true")
    a.add_argument("--rho", type=float, default=apc.RHO_POR_DEFECTO)
    a.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    txt = json.dumps(run(args.goles, args.rho, args.cache, args.fijos), indent=2,
                     ensure_ascii=False)
    if args.out:
        args.out.write_text(txt, encoding="utf-8")
    print(txt)
