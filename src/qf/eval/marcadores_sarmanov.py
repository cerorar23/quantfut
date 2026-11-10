"""
T7 (2026-11-09): ¿una dependencia tipo Sarmanov mejora la matriz de marcadores de Dixon-Coles?

Michels, Ötting y Karlis (JRSS-C 2025) generalizan Dixon-Coles con una familia bivariada tipo Sarmanov. Aquí, la
versión mínima con núcleo exponencial: f(x,y) = pX(x)·pY(y)·[1 + ω·(e^-x − E_X)(e^-y − E_Y)], con E = E[e^-X], y
marginales Poisson. Se compara con (a) independencia y (b) Dixon-Coles de producción (τ con ρ = −0,0613).
Igual que el motor B, (λ, μ) se ANCLAN al mercado: mínimos cuadrados sobre P(local), P(visitante) y P(más de 2,5) de
Pinnacle al cierre sin margen (Shin), con la misma rutina para las tres familias. ω se ajusta con 2019/20-2022/23 (rejilla,
máxima verosimilitud del marcador, 1.500 partidos) y se juzga en 2023/24-2024/25. Medidas de prueba: log-verosimilitud
del marcador exacto y pérdida logarítmica de los mercados que el ancla NO fija: más de 1,5, más de 3,5 y ambos marcan.
Criterio fijado antes de medir: Sarmanov entra si mejora a Dixon-Coles con IC95 (bootstrap de partidos) entero positivo
en la log-verosimilitud del marcador y no empeora ninguno de los tres mercados.

Uso: python -m qf.eval.marcadores_sarmanov [--cache .local/fd_cache]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import poisson

from ..model.devig import shin
from ..model.pricing import dc_tau
from . import alta_prob_calibracion as apc
from . import soft_vs_sharp as sv

G = 10
RHO_DC = -0.0613
OMEGAS = (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0)
ENTRENO = ("1920", "2021", "2122", "2223")
PRUEBA = ("2324", "2425")
MUESTRA_AJUSTE = 1500
REPLICAS = 2000
_g = np.arange(G + 1)
_hg, _ag = np.meshgrid(_g, _g, indexing="ij")


def matriz(familia: str, lam: float, mu: float, omega: float = 0.0) -> np.ndarray:
    ph, pa = poisson.pmf(_g, lam), poisson.pmf(_g, mu)
    m = np.outer(ph, pa)
    if familia == "dc":
        m = m * dc_tau(_hg, _ag, lam, mu, RHO_DC)
    elif familia == "sarmanov":
        e1, e2 = np.exp(lam * (np.exp(-1) - 1)), np.exp(mu * (np.exp(-1) - 1))
        m = m * (1 + omega * np.outer(np.exp(-_g) - e1, np.exp(-_g) - e2))
        m = np.clip(m, 1e-12, None)
    return m / m.sum()


def probs(m: np.ndarray) -> np.ndarray:
    return np.array([np.tril(m, -1).sum(), np.triu(m, 1).sum(), m[(_hg + _ag) > 2.5].sum()])


def anclar(familia: str, objetivo: np.ndarray, omega: float = 0.0, x0=(0.3, 0.1)) -> tuple[float, float]:
    f = lambda z: probs(matriz(familia, np.exp(z[0]), np.exp(z[1]), omega)) - objetivo  # noqa: E731
    r = least_squares(f, np.array(x0), xtol=1e-9, ftol=1e-9)
    return float(np.exp(r.x[0])), float(np.exp(r.x[1]))


def preparar(raw: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for d in raw.to_dict("records"):
        q = [d.get(k) for k in ("PSCH", "PSCD", "PSCA", "PC>2.5", "PC<2.5", "FTHG", "FTAG")]
        try:
            q = [float(v) for v in q]
        except (TypeError, ValueError):
            continue
        if not all(np.isfinite(q)) or min(q[:5]) <= 1.0:
            continue
        p3, p2 = shin(np.array(q[:3], float)), shin(np.array(q[3:5], float))
        filas.append({"temporada": d["season"], "obj": np.array([p3[0], p3[2], p2[0]]),
                      "x": min(int(q[5]), G), "y": min(int(q[6]), G)})
    return pd.DataFrame(filas)


def evaluar_familia(d: pd.DataFrame, familia: str, omega: float = 0.0) -> dict:
    ll, l15, l35, lbt = [], [], [], []
    for r in d.itertuples():
        lam, mu = anclar(familia, r.obj, omega)
        m = matriz(familia, lam, mu, omega)
        tot = r.x + r.y
        pr = lambda p, gana: -np.log(np.clip(p if gana else 1 - p, 1e-9, 1))  # noqa: E731
        ll.append(np.log(max(m[r.x, r.y], 1e-12)))
        l15.append(pr(m[(_hg + _ag) > 1.5].sum(), tot > 1.5))
        l35.append(pr(m[(_hg + _ag) > 3.5].sum(), tot > 3.5))
        lbt.append(pr(m[1:, 1:].sum(), r.x > 0 and r.y > 0))
    return {"ll": np.array(ll), "o15": np.array(l15), "o35": np.array(l35), "btts": np.array(lbt)}


def ic(dif: np.ndarray, rng) -> list[float]:
    m = [dif[rng.integers(0, len(dif), len(dif))].mean() for _ in range(REPLICAS)]
    return [round(float(np.percentile(m, 2.5)), 5), round(float(np.percentile(m, 97.5)), 5)]


def run(cache: Path) -> dict:
    raw, dataset = sv.load_csvs(apc.LIGAS, sv.DEFAULT_SEASONS, cache)
    d = preparar(raw)
    ent = d[d.temporada.isin(ENTRENO)].sample(n=MUESTRA_AJUSTE, random_state=3)
    prb = d[d.temporada.isin(PRUEBA)].reset_index(drop=True)
    ajuste = {w: float(evaluar_familia(ent, "sarmanov", w)["ll"].mean()) for w in OMEGAS}
    omega = max(ajuste, key=ajuste.get)
    res = {"independiente": evaluar_familia(prb, "ind"), "dixon_coles": evaluar_familia(prb, "dc"),
           "sarmanov": evaluar_familia(prb, "sarmanov", omega)}
    rng = np.random.default_rng(7)
    out = {"dataset_sha256": dataset["sha256"], "n_prueba": int(len(prb)), "omega": omega,
           "ajuste_ll": {str(w): round(v, 5) for w, v in ajuste.items()}, "medias": {}}
    for nombre, r in res.items():
        out["medias"][nombre] = {k: round(float(v.mean()), 5) for k, v in r.items()}
    dc, sa = res["dixon_coles"], res["sarmanov"]
    out["sarmanov_menos_dc"] = {"ll_marcador": {"dif": round(float((sa["ll"] - dc["ll"]).mean()), 5),
                                                "ic95": ic(sa["ll"] - dc["ll"], rng)}}
    for k in ("o15", "o35", "btts"):
        out["sarmanov_menos_dc"][k + "_perdida"] = {"dif": round(float((sa[k] - dc[k]).mean()), 5),
                                                     "ic95": ic(sa[k] - dc[k], rng)}
    s = out["sarmanov_menos_dc"]
    out["entra"] = bool(s["ll_marcador"]["ic95"][0] > 0 and all(s[k + "_perdida"]["dif"] <= 0 for k in ("o15", "o35", "btts")))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    print(json.dumps(run(ap.parse_args().cache), indent=1, ensure_ascii=False))
