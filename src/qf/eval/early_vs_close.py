"""
¿Sabe el modelo algo que la cuota TEMPRANA de Pinnacle todavía no sabe?

`w_model = 0,0001` (README) se midió contra el CIERRE. Que el cierre ya
contenga todo lo que sabe el modelo no implica que lo contenga la cuota de uno
a tres días antes, que es la que se puede tomar. Si el modelo anticipa hacia
dónde se mueve el mercado, apostar temprano da CLV, que es lo que mide la
puerta comercial.

Regla fijada ANTES de ver resultados (harness/tareas.md, "Ideas de la
literatura", punto 1):

  - Prueba principal: pendiente de `logit p_cierre − logit p_temprana` sobre
    `logit p_modelo − logit p_temprana`, una fila por partido y selección.
    No necesita el resultado del partido, así que tiene mucho menos ruido que
    el RPS. Con 0 el modelo no anticipa nada; con 1 el mercado acaba
    exactamente donde decía el modelo.
  - "Hay señal" si el IC95 por semanas de la pendiente está ENTERO por encima
    de cero, la pendiente es positiva en al menos 4 de las 7 ligas, y el EV
    contra el cierre justo de apostar al precio temprano de Pinnacle cuando el
    modelo ve ≥2 % de ventaja tiene el IC95 entero por encima de cero.
  - Informativas: `w_model` contra la temprana y contra el cierre (estimado en
    el 70 % antiguo, RPS en el 30 % reciente). El del cierre es el control:
    debe salir ≈0, como en el README.

DATOS
-----
Cuotas: los CSV del formato principal de football-data.co.uk ya cacheados en
`.local/fd_cache` (7 ligas, 2019/20-2024/25). `PSH/PSD/PSA` se toman el
viernes por la tarde (fin de semana) o el martes (entre semana): entre uno y
tres días antes del inicio. Modelo: `kalman.predict_sequential` sobre
`train.load_training_data()`, con xG, prediciendo cada partido antes de
aprenderlo. Se cruzan por `match_id`, que el cargador del histórico construye de forma
determinista desde las mismas filas.

FUGAS
-----
`predict_sequential` estima el nivel de goles y la ventaja de local de cada
liga con TODO el histórico que recibe. Aquí se fijan con los partidos
anteriores al primer partido evaluado (`_KalmanSinFuturo`): sin eso, el
modelo vería el futuro de esos dos números y podría fabricar una pendiente
positiva. La selección de apuestas solo lee modelo y cuota temprana
(`tests/test_early_vs_close.py` lo comprueba alterando cierre y resultado).

Solo lectura: no toca producción, artefactos ni la base.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..model.kalman import DynamicRatings
from ..model.meta import _fit_weight
from ..normalize import slugify
from .backtest import check_leakage
from .comparison import _rps_per_match
from .metrics import blend_logit
from .soft_vs_sharp import (DEFAULT_SEASONS, MAX_SHARP_DEVIATION, MARKETS,
                            _devig_rows, _sharp_deviation, _weekly_ci,
                            load_csvs, main_format_leagues)

log = logging.getLogger(__name__)

MIN_EDGE = 0.02
HOLDOUT = 0.3
MIN_LIGAS_POSITIVAS = 4
SEL = ("home", "draw", "away")
EPS = 1e-6


def _parse_date(row) -> datetime | None:
    d = str(row.get("Date", "")).strip()
    t = str(row.get("Time", "")).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(d, fmt)
            break
        except ValueError:
            continue
    else:
        return None
    if t and ":" in t:
        try:
            hh, mm = t.split(":")[:2]
            dt = dt.replace(hour=int(hh), minute=int(mm))
        except ValueError:
            dt = dt.replace(hour=19)
    else:
        # Sin hora: se marca a las 19:00 UTC. El backtest debe saber que el
        # orden intra-jornada es arbitrario (ver check_leakage).
        dt = dt.replace(hour=19)
    return dt.replace(tzinfo=timezone.utc)


def match_id(league_id: str, season: str, home: str, away: str, ko) -> str:
    """El mismo identificador de partido que usa el cargador del histórico."""
    return (f"{league_id}:{season}:"
            f"{slugify(home)[:12].replace(' ', '')}-"
            f"{slugify(away)[:12].replace(' ', '')}:"
            f"{ko.strftime('%Y%m%d')}")


def mercado(raw: pd.DataFrame, method: str | None = None) -> pd.DataFrame:
    """Una fila por partido con Pinnacle completo antes y al cierre."""
    spec = MARKETS["h2h"]
    early, close = spec["cols"]("PS", False), spec["cols"]("PS", True)
    df = raw.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]).copy()
    if not set(early + close) <= set(df.columns):
        return pd.DataFrame()
    df[early + close] = df[early + close].apply(pd.to_numeric, errors="coerce")
    df = df.dropna(subset=early + close)
    df = df[(df[early + close] > 1.0).all(axis=1)].reset_index(drop=True)

    ko = df.apply(_parse_date, axis=1)
    df = df[ko.notna()].reset_index(drop=True)
    ko = ko[ko.notna()].reset_index(drop=True)
    pe = df[early].to_numpy(float)
    p_early = _devig_rows(pe, method)
    p_close = _devig_rows(df[close].to_numpy(float), method)
    out = pd.DataFrame({
        "match_id": [match_id(lg, s, h, a, k) for lg, s, h, a, k in zip(
            df["league_id"], df["season"], df["HomeTeam"], df["AwayTeam"], ko)],
        "league_id": df["league_id"].to_numpy(),
        "week": pd.Series(ko).dt.tz_localize(None).dt.to_period("W").astype(str).to_numpy(),
        "sharp_dev_early": _sharp_deviation(df, spec, p_early, method),
    })
    for j, s in enumerate(SEL):
        out[f"price_early_{s}"] = pe[:, j]
        out[f"pe_{s}"] = p_early[:, j]
        out[f"pc_{s}"] = p_close[:, j]
    hg, ag = df["FTHG"].to_numpy(float), df["FTAG"].to_numpy(float)
    out["outcome"] = np.where(hg > ag, 0, np.where(hg == ag, 1, 2))
    return out


class _KalmanSinFuturo(DynamicRatings):
    """Nivel de goles y ventaja de local de cada liga solo con el pasado."""

    def __init__(self, corte, config=None):
        super().__init__(config)
        self._corte = corte

    def _estimate_league_params(self, df) -> None:
        super()._estimate_league_params(df[df["kickoff_utc"] < self._corte])


def unir(oos: pd.DataFrame, mk: pd.DataFrame) -> pd.DataFrame:
    """Partidos con modelo y mercado, y la guarda de Pinnacle de soft_vs_sharp."""
    cols = ["match_id", "kickoff_utc", "p_home", "p_draw", "p_away"]
    cols += [c for c in ("lam", "mu") if c in oos.columns]
    d = oos[cols].merge(mk, on="match_id", how="inner")
    d = d[d["sharp_dev_early"] <= MAX_SHARP_DEVIATION]
    return d.sort_values("kickoff_utc").reset_index(drop=True)


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def _largo(d: pd.DataFrame) -> pd.DataFrame:
    """Una fila por partido y selección: desacuerdo y movimiento en logit."""
    filas = []
    for s, col in zip(SEL, ("p_home", "p_draw", "p_away")):
        filas.append(pd.DataFrame({
            "league_id": d["league_id"].to_numpy(),
            "week": d["week"].to_numpy(),
            "x": _logit(d[col].to_numpy(float)) - _logit(d[f"pe_{s}"].to_numpy(float)),
            "y": _logit(d[f"pc_{s}"].to_numpy(float)) - _logit(d[f"pe_{s}"].to_numpy(float)),
        }))
    return pd.concat(filas, ignore_index=True)


def _pendiente(x: np.ndarray, y: np.ndarray) -> float:
    xc = x - x.mean()
    return float((xc * (y - y.mean())).sum() / max((xc * xc).sum(), 1e-12))


def movimiento(d: pd.DataFrame, iterations: int = 1000) -> dict:
    """Pendiente del movimiento hacia el modelo, con IC95 remuestreando semanas."""
    lg = _largo(d)
    x, y = lg["x"].to_numpy(), lg["y"].to_numpy()
    grupos = list(lg.groupby("week").indices.values())
    rng = np.random.default_rng(42)
    est = []
    for _ in range(iterations):
        idx = np.concatenate([grupos[i] for i in rng.integers(0, len(grupos), len(grupos))])
        est.append(_pendiente(x[idx], y[idx]))
    lo, hi = np.percentile(est, [2.5, 97.5])
    por_liga = {str(k): {"n": int(len(g)),
                         "pendiente": round(_pendiente(g["x"].to_numpy(), g["y"].to_numpy()), 4)}
                for k, g in lg.groupby("league_id")}
    return {"n_filas": int(len(lg)), "n_semanas": len(grupos),
            "pendiente": round(_pendiente(x, y), 4),
            "ic95": [round(float(lo), 4), round(float(hi), 4)],
            "corr": round(float(np.corrcoef(x, y)[0, 1]), 4),
            "ligas_positivas": sum(v["pendiente"] > 0 for v in por_liga.values()),
            "por_liga": por_liga}


def seleccionar(d: pd.DataFrame, min_edge: float = MIN_EDGE) -> pd.DataFrame:
    """
    La mejor selección de cada partido si el modelo ve `min_edge` contra el
    precio temprano de Pinnacle. Solo lee modelo y cuota temprana.
    """
    edges = np.column_stack([
        d[col].to_numpy(float) * d[f"price_early_{s}"].to_numpy(float) - 1.0
        for s, col in zip(SEL, ("p_home", "p_draw", "p_away"))])
    j = edges.argmax(axis=1)
    ok = edges[np.arange(len(d)), j] >= min_edge
    sel = d[ok].copy()
    sel["sel"] = j[ok]
    sel["edge_modelo"] = edges[ok, j[ok]]
    return sel.reset_index(drop=True)


def ev_cierre(sel: pd.DataFrame) -> dict:
    """EV de 1 unidad al precio temprano contra el cierre JUSTO, y el ROI."""
    if sel.empty:
        return {"n": 0}
    i = np.arange(len(sel))
    price = np.column_stack([sel[f"price_early_{s}"] for s in SEL])[i, sel["sel"]]
    pc = np.column_stack([sel[f"pc_{s}"] for s in SEL])[i, sel["sel"]]
    ev = (price * pc - 1.0) * 100
    roi = np.where(sel["outcome"].to_numpy() == sel["sel"].to_numpy(), price - 1.0, -1.0) * 100
    weeks = sel["week"].to_numpy()
    return {"n": int(len(sel)),
            "edge_modelo": round(float(sel["edge_modelo"].mean()) * 100, 3),
            "ev_cierre": round(float(ev.mean()), 3), "ev_cierre_ic95": _weekly_ci(ev, weeks),
            "roi": round(float(roi.mean()), 3), "roi_ic95": _weekly_ci(roi, weeks),
            "por_liga": {str(k): {"n": int(len(g)), "ev_cierre": round(float(ev[g.index].mean()), 3)}
                         for k, g in sel.groupby("league_id")}}


def control(d: pd.DataFrame) -> dict:
    """Pinnacle temprano en todas las selecciones: el EV al cierre debe ser ≈ −margen."""
    pe = np.column_stack([d[f"price_early_{s}"] for s in SEL])
    pc = np.column_stack([d[f"pc_{s}"] for s in SEL])
    return {"n": int(pe.size), "ev_cierre": round(float((pe * pc - 1.0).mean() * 100), 3)}


def pesos(d: pd.DataFrame, holdout: float = HOLDOUT) -> dict:
    """`w_model` contra la temprana y contra el cierre, mismo corte temporal."""
    cut = int(len(d) * (1 - holdout))
    fit, val = d.iloc[:cut], d.iloc[cut:]
    mp = lambda x: x[["p_home", "p_draw", "p_away"]].to_numpy(float)  # noqa: E731
    out = {"n_ajuste": int(len(fit)), "n_validacion": int(len(val))}
    for nombre, pref in (("temprana", "pe"), ("cierre", "pc")):
        kp = lambda x: x[[f"{pref}_{s}" for s in SEL]].to_numpy(float)  # noqa: E731
        w = _fit_weight(mp(fit), kp(fit), fit["outcome"].to_numpy(int))
        o = val["outcome"].to_numpy(int)
        r_mkt = _rps_per_match(kp(val), o)
        r_mix = _rps_per_match(blend_logit(mp(val), kp(val), w), o)
        out[nombre] = {"w_model": round(w, 4),
                       "rps_mercado": round(float(r_mkt.mean()), 5),
                       "rps_mezcla": round(float(r_mix.mean()), 5),
                       "rps_modelo": round(float(_rps_per_match(mp(val), o).mean()), 5),
                       "delta_ic95": _weekly_ci(r_mix - r_mkt, val["week"].to_numpy())}
    return out


def veredicto(mov: dict, ev: dict) -> str:
    ci_ev = ev.get("ev_cierre_ic95")
    if (mov["ic95"][0] > 0 and mov["ligas_positivas"] >= MIN_LIGAS_POSITIVAS
            and ci_ev and ci_ev[0] > 0):
        return "HAY SEÑAL"
    return "SIN SEÑAL"


def run(cache_dir: Path = Path(".local/fd_cache")) -> dict:
    raw, dataset = load_csvs(main_format_leagues(), DEFAULT_SEASONS, cache_dir)
    mk = mercado(raw, settings.devig_method)

    from ..model.train import load_training_data
    df = load_training_data()
    corte = pd.Timestamp("2019-07-01", tz="UTC")
    oos = _KalmanSinFuturo(corte).predict_sequential(df)
    oos = oos[oos["kickoff_utc"] >= corte]
    d = unir(oos, mk)

    mov = movimiento(d)
    ev = ev_cierre(seleccionar(d))
    return {"dataset": {**dataset, "partidos_con_pinnacle": int(len(mk)),
                        "cruzados_con_modelo": int(len(d)),
                        "sin_cruzar": int(len(mk) - mk["match_id"].isin(oos["match_id"]).sum())},
            "fugas": check_leakage(df),
            "control_pinnacle_sin_criterio": control(d),
            "movimiento": mov,
            f"apuestas_edge_{int(MIN_EDGE * 100)}": ev,
            "apuestas_edge_0": {k: v for k, v in ev_cierre(seleccionar(d, 0.0)).items()
                                if k != "por_liga"},
            "pesos": pesos(d),
            "veredicto": veredicto(mov, ev)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--cache", default=".local/fd_cache")
    args = ap.parse_args()
    print(json.dumps(run(Path(args.cache)), ensure_ascii=False, indent=1, default=str))
