"""
Paso 3 (2026-11-09): ¿por qué la primera mitad promete de más en Liga MX y Champions, y se arregla por liga?

Datos: cierres de Pinnacle 1X2 y goles al descanso del servidor (export de solo lectura a un CSV local). Igual que
en producción, (λ, μ) se anclan al 1X2 sin margen (Shin) bajo Dixon-Coles con ρ = −0,0613 y los mercados de 1T salen
de `model.primer_tiempo.probs` (Poisson independientes con la proporción fija). Aquí el anclaje usa 2 objetivos
(P local, P visitante) con el solver rápido de `marcadores_sarmanov`, no `market_lambdas` (0,1 s por partido).
Muestra: todos los partidos de Liga MX, Champions y Europa League más un máximo de MAX_RESTO por cada otra liga.

Uso: python -m qf.eval.primer_tiempo_por_liga --csv .local/primer_tiempo_cierres.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.special import gammaln

from ..model import primer_tiempo as pt
from ..model.devig import shin
from . import marcadores_sarmanov as ms

ESPECIALES = ("mx.liga_mx", "eu.ucl", "eu.uel")
MAX_RESTO = 400
CORTE = pd.Timestamp("2025-07-01", tz="UTC")


def anclar2(objetivo: np.ndarray) -> tuple[float, float]:
    f = lambda z: ms.probs(ms.matriz("dc", np.exp(z[0]), np.exp(z[1])))[:2] - objetivo  # noqa: E731
    r = least_squares(f, np.array([0.3, 0.1]), xtol=1e-9, ftol=1e-9)
    return float(np.exp(r.x[0])), float(np.exp(r.x[1]))


def preparar(csv: Path) -> pd.DataFrame:
    d = pd.read_csv(csv, parse_dates=["kickoff_utc"])
    d = d.dropna(subset=["ph", "pd", "pa"])
    d = d[(d[["ph", "pd", "pa"]] > 1.0).all(axis=1)]
    resto = d[~d.league_id.isin(ESPECIALES)].groupby("league_id", group_keys=False).apply(
        lambda g: g.sample(n=min(len(g), MAX_RESTO), random_state=5))
    d = pd.concat([d[d.league_id.isin(ESPECIALES)], resto], ignore_index=True)
    filas = []
    for r in d.itertuples():
        p = shin(np.array([r.ph, r.pd, r.pa], float))
        lam, mu = anclar2(np.array([p[0], p[2]]))
        pr = pt.probs(lam, mu)
        gh, ga = r.home_goals_ht, r.away_goals_ht
        filas.append({"liga": r.league_id, "fecha": r.kickoff_utc, "lam": lam, "mu": mu,
                      "p_gol": pr["gol_1t_si"], "p_ambos": pr["ambos_1t_si"],
                      "gol": float(gh + ga >= 1), "ambos": float(gh >= 1 and ga >= 1),
                      "gh": gh, "ga": ga, "g1t": gh + ga, "g90": r.home_goals + r.away_goals})
    return pd.DataFrame(filas)


KS = (5.0, 10.0, 20.0, 40.0, 80.0, np.inf)
_g = np.arange(pt.MAX_GOLES_1T + 1)


def matriz_1t(lam: float, mu: float, k: float) -> np.ndarray:
    """Goles de 1T con un choque de ritmo común Gamma(k, media 1): corr. positiva; k = inf es el modelo de producción."""
    a, b = pt.PROPORCION_1T[0] * lam, pt.PROPORCION_1T[1] * mu
    if np.isinf(k):
        from scipy.stats import poisson
        m = np.outer(poisson.pmf(_g, a), poisson.pmf(_g, b))
    else:
        x, y = np.meshgrid(_g, _g, indexing="ij")
        s = k + a + b
        m = np.exp(gammaln(k + x + y) - gammaln(k) - gammaln(x + 1) - gammaln(y + 1)
                   + k * np.log(k / s) + x * np.log(a / s) + y * np.log(b / s))
    return m / m.sum()


def eventos(m: np.ndarray) -> tuple[float, float]:
    return float(1 - m[0, 0]), float(m[1:, 1:].sum())


def con_k(d: pd.DataFrame, k: float) -> pd.DataFrame:
    ev = np.array([eventos(matriz_1t(r.lam, r.mu, k)) for r in d.itertuples()])
    return d.assign(p_gol=ev[:, 0], p_ambos=ev[:, 1])


def loglik_marcador(d: pd.DataFrame, k: float) -> float:
    return float(np.mean([np.log(max(matriz_1t(r.lam, r.mu, k)[min(int(r.gh), 8), min(int(r.ga), 8)], 1e-12))
                          for r in d.itertuples()]))


def perdida_eventos(d: pd.DataFrame) -> np.ndarray:
    p1, p2 = np.clip(d.p_gol.to_numpy(), 1e-6, 1 - 1e-6), np.clip(d.p_ambos.to_numpy(), 1e-6, 1 - 1e-6)
    return (-(d.gol * np.log(p1) + (1 - d.gol) * np.log(1 - p1)) - (d.ambos * np.log(p2) + (1 - d.ambos) * np.log(1 - p2))).to_numpy() / 2


def tabla(d: pd.DataFrame) -> dict:
    out = {}
    for nombre, g in (("liga_mx", d[d.liga == "mx.liga_mx"]), ("champions", d[d.liga == "eu.ucl"]),
                      ("europa_league", d[d.liga == "eu.uel"]), ("resto_14_ligas", d[~d.liga.isin(ESPECIALES)])):
        if len(g) < 30:
            continue
        out[nombre] = {"n": int(len(g)),
                       "gol_1t_si": {"prometido": round(float(g.p_gol.mean()), 4), "real": round(float(g.gol.mean()), 4)},
                       "ambos_1t_no": {"prometido": round(float(1 - g.p_ambos.mean()), 4),
                                       "real": round(float(1 - g.ambos.mean()), 4)},
                       "prop_goles_1t": round(float(g.g1t.sum() / max(g.g90.sum(), 1)), 4),
                       "goles_90": round(float(g.g90.mean()), 3)}
    return out


def run(csv: Path) -> dict:
    d = preparar(csv)
    ent, prb = d[d.fecha < CORTE], d[d.fecha >= CORTE].reset_index(drop=True)
    ll = {("inf" if np.isinf(k) else str(int(k))): round(loglik_marcador(ent, k), 5) for k in KS}
    k_ok = max(KS, key=lambda k: loglik_marcador(ent, k))
    nuevo = con_k(prb, k_ok)
    base_l, nuevo_l = perdida_eventos(prb), perdida_eventos(nuevo)
    rng = np.random.default_rng(7)
    dif = nuevo_l - base_l
    ics = {}
    for nombre, mask in (("todo", np.ones(len(prb), bool)), ("liga_mx", (prb.liga == "mx.liga_mx").to_numpy()),
                         ("champions", (prb.liga == "eu.ucl").to_numpy())):
        v = dif[mask]
        medias = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(2000)]
        ics[nombre] = {"n": int(mask.sum()), "dif_perdida": round(float(v.mean()), 5),
                       "ic95": [round(float(np.percentile(medias, 2.5)), 5), round(float(np.percentile(medias, 97.5)), 5)]}
    return {"n_total": int(len(d)), "n_entreno": int(len(ent)), "n_prueba": int(len(prb)),
            "loglik_marcador_entreno_por_k": ll, "k_elegido": None if np.isinf(k_ok) else k_ok,
            "base_produccion": tabla(prb), "con_choque_comun": tabla(nuevo), "nuevo_menos_base_perdida": ics}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, default=Path(".local/primer_tiempo_cierres.csv"))
    print(json.dumps(run(ap.parse_args().csv), indent=1, ensure_ascii=False))
