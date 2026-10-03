"""
¿Gana un modelo entrenado para NO parecerse al mercado? (idea 4).

Hubáček y Šír (International Journal of Forecasting, 2023; arXiv 2010.12508,
§4.5 y §5) entrenan con

    pérdida = Σ (t − y)² − γ · Σ (t − m)²

donde `t` es la probabilidad del modelo, `y` el resultado y `m` la del
bookmaker. Con γ > 0 el modelo se aparta del mercado justo donde su propia
información no coincide con él, que es donde una apuesta puede tener valor.

Aquí: segunda etapa softmax lineal sobre la información de Kalman (log de sus
tres probabilidades y de las dos lambdas), sin cuotas como variable, con `m`
el justo de Pinnacle TEMPRANO, que es contra quien se apuesta. Apuesta
uniforme al precio temprano de Pinnacle. Walk-forward por temporadas con γ
elegido en la temporada anterior. Regla fijada antes de ver resultados en
harness/tareas.md, idea 4.

Solo lectura.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .early_vs_close import (SEL, _KalmanSinFuturo, mercado, unir)
from .soft_vs_sharp import DEFAULT_SEASONS, _weekly_ci, load_csvs, main_format_leagues

log = logging.getLogger(__name__)

GAMMAS = (0.0, 0.2, 0.4, 0.6, 0.8)
L2 = 1e-3
TEMPORADAS_PRUEBA = ("2122", "2223", "2324", "2425")
MIN_LIGAS_POSITIVAS = 4


def temporada(ko: pd.Series) -> pd.Series:
    """'2122' para un partido entre julio de 2021 y junio de 2022."""
    ko = pd.to_datetime(ko, utc=True)
    inicio = ko.dt.year - (ko.dt.month < 7).astype(int)
    return (inicio % 100).astype(str).str.zfill(2) + ((inicio + 1) % 100).astype(str).str.zfill(2)


def variables(d: pd.DataFrame) -> np.ndarray:
    """Solo información del modelo: nada del mercado entra como variable."""
    p = np.clip(d[["p_home", "p_draw", "p_away"]].to_numpy(float), 1e-6, 1)
    lam = np.log(np.clip(d[["lam", "mu"]].to_numpy(float), 1e-3, None))
    return np.column_stack([np.log(p), lam])


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


class Decorrelado:
    """Softmax lineal entrenado con la pérdida de Hubáček y Šír."""

    def __init__(self, gamma: float, l2: float = L2):
        self.gamma, self.l2 = float(gamma), float(l2)

    def _diseno(self, X: np.ndarray) -> np.ndarray:
        return np.column_stack([np.ones(len(X)), (X - self.mu) / self.sd])

    def fit(self, X: np.ndarray, y: np.ndarray, m: np.ndarray) -> "Decorrelado":
        self.mu, self.sd = X.mean(axis=0), X.std(axis=0) + 1e-9
        A = self._diseno(X)
        Y = np.eye(3)[y]
        n, k = A.shape

        def perdida(w):
            W = w.reshape(k, 3)
            t = _softmax(A @ W)
            L = ((t - Y) ** 2).sum() - self.gamma * ((t - m) ** 2).sum()
            g = 2 * (t - Y) - 2 * self.gamma * (t - m)          # ∂L/∂t
            dz = t * (g - (g * t).sum(axis=1, keepdims=True))   # softmax
            grad = A.T @ dz / n + 2 * self.l2 * W
            return L / n + self.l2 * (W ** 2).sum(), grad.ravel()

        res = minimize(perdida, np.zeros(k * 3), jac=True, method="L-BFGS-B")
        self.W = res.x.reshape(k, 3)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return _softmax(self._diseno(X) @ self.W)


def _m(d: pd.DataFrame) -> np.ndarray:
    return d[[f"pe_{s}" for s in SEL]].to_numpy(float)


def apuestas(d: pd.DataFrame, t: np.ndarray) -> pd.DataFrame:
    """Uniforme: la selección de mayor t·cuota − 1 de cada partido, si es > 0."""
    precio = d[[f"price_early_{s}" for s in SEL]].to_numpy(float)
    edge = t * precio - 1.0
    j = edge.argmax(axis=1)
    i = np.arange(len(d))
    ok = edge[i, j] > 0
    pc = d[[f"pc_{s}" for s in SEL]].to_numpy(float)
    return pd.DataFrame({
        "league_id": d["league_id"].to_numpy()[ok], "week": d["week"].to_numpy()[ok],
        "ev": (precio[i, j] * pc[i, j] - 1.0)[ok] * 100,
        "roi": np.where(d["outcome"].to_numpy() == j, precio[i, j] - 1.0, -1.0)[ok] * 100})


def medir(ap: pd.DataFrame) -> dict:
    if ap.empty:
        return {"n": 0}
    por_liga = ap.groupby("league_id")["ev"].mean()
    return {"n": int(len(ap)), "ev_cierre": round(float(ap["ev"].mean()), 3),
            "ev_cierre_ic95": _weekly_ci(ap["ev"].to_numpy(), ap["week"].to_numpy()),
            "roi": round(float(ap["roi"].mean()), 3),
            "roi_ic95": _weekly_ci(ap["roi"].to_numpy(), ap["week"].to_numpy()),
            "ligas_positivas": int((por_liga > 0).sum()),
            "por_liga": {str(k): round(float(v), 3) for k, v in por_liga.items()}}


def _ajustar(d: pd.DataFrame, gamma: float) -> Decorrelado:
    return Decorrelado(gamma).fit(variables(d), d["outcome"].to_numpy(int), _m(d))


def walk_forward(d: pd.DataFrame, gammas=GAMMAS,
                 prueba=TEMPORADAS_PRUEBA) -> dict:
    d = d.assign(temporada=temporada(d["kickoff_utc"]))
    orden = sorted(d["temporada"].unique())
    elegidas, fijos = [], {g: [] for g in gammas}
    detalle = []
    for s in prueba:
        previa = orden[orden.index(s) - 1]
        antes = d[d["temporada"] < previa]
        val = d[d["temporada"] == previa]
        ev_val = {g: medir(apuestas(val, _ajustar(antes, g).predict(variables(val))))
                  .get("ev_cierre", -np.inf) for g in gammas}
        g_star = max(ev_val, key=ev_val.get)
        entreno, test = d[d["temporada"] < s], d[d["temporada"] == s]
        for g in gammas:
            t = _ajustar(entreno, g).predict(variables(test))
            ap = apuestas(test, t)
            fijos[g].append(ap)
            if g == g_star:
                elegidas.append(ap)
                corr = float(np.corrcoef(t[:, 0], _m(test)[:, 0])[0, 1])
        detalle.append({"temporada": s, "gamma_elegido": g_star, "corr_mercado_local": round(corr, 3),
                        "ev_validacion": {str(g): round(v, 3) for g, v in ev_val.items()}})
    principal = medir(pd.concat(elegidas, ignore_index=True))
    ci = principal.get("ev_cierre_ic95")
    hay = bool(ci and ci[0] > 0 and principal["ligas_positivas"] >= MIN_LIGAS_POSITIVAS)
    return {"gamma_elegido_en_validacion": principal, "por_temporada": detalle,
            "por_gamma_fijo": {str(g): {k: v for k, v in medir(pd.concat(a, ignore_index=True)).items()
                                        if k != "por_liga"} for g, a in fijos.items()},
            "veredicto": "HAY SEÑAL" if hay else "SIN SEÑAL"}


def run(cache_dir: Path = Path(".local/fd_cache")) -> dict:
    from ..model.train import load_training_data
    raw, dataset = load_csvs(main_format_leagues(), DEFAULT_SEASONS, cache_dir)
    corte = pd.Timestamp("2019-07-01", tz="UTC")
    oos = _KalmanSinFuturo(corte).predict_sequential(load_training_data())
    d = unir(oos[oos["kickoff_utc"] >= corte], mercado(raw))
    return {"dataset": {"sha256": dataset["sha256"], "partidos": int(len(d))},
            **walk_forward(d)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--cache", default=".local/fd_cache")
    print(json.dumps(run(Path(ap.parse_args().cache)), ensure_ascii=False, indent=1,
                     default=str))
