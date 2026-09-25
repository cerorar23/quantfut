"""
Fase 2.D — challengers de ESTRUCTURA de la matriz de marcadores.

Los brazos de conteo conservan las medias de Dixon-Coles fuera de muestra
(`lam`, `mu`) y cambian solo la forma de la matriz: dispersión (Conway-Maxwell-
Poisson, conteo Weibull) y dependencia (Poisson bivariante, cópula de Frank)
frente al parche `tau` de 1997. El probit ordenado es la ruta alternativa que
modela directamente la diferencia de goles.

Esperado honesto: 0,001–0,002 de RPS como mucho. Solo diagnóstico: nada de
aquí predice en producción ni se activa solo.

    python -m qf.model.structure            # walk-forward + informe
    python -m qf.model.structure --reuse    # reutiliza el walk-forward cacheado
"""
from __future__ import annotations

import logging
from typing import Callable

import numpy as np
import pandas as pd
from scipy import optimize, special, stats

log = logging.getLogger(__name__)

G = 10
_K = np.arange(G + 1)
EPS = 1e-12
MIN_FIT_ROWS = 500
_H, _A = np.meshgrid(_K, _K, indexing="ij")
_GD = np.clip(_H - _A, -3, 3) + 3          # 7 categorías: <=-3 … >=3


def _normalize(m: np.ndarray) -> np.ndarray:
    m = np.clip(m, 0.0, None)
    return m / m.sum(axis=(1, 2), keepdims=True)


def _poisson_pmf(rate: np.ndarray) -> np.ndarray:
    return stats.poisson.pmf(_K[None, :], rate[:, None])


# --- Brazos de conteo: (lam, mu, parámetros) -> matriz filas x 11 x 11 -------

def poisson_matrix(lam, mu) -> np.ndarray:
    return _normalize(_poisson_pmf(lam)[:, :, None] * _poisson_pmf(mu)[:, None, :])


def dc_tau_matrix(lam, mu, rho: float) -> np.ndarray:
    m = _poisson_pmf(lam)[:, :, None] * _poisson_pmf(mu)[:, None, :]
    m[:, 0, 0] *= 1 - lam * mu * rho
    m[:, 0, 1] *= 1 + lam * rho
    m[:, 1, 0] *= 1 + mu * rho
    m[:, 1, 1] *= 1 - rho
    return _normalize(m)


def bivariate_poisson_matrix(lam, mu, lam3: float) -> np.ndarray:
    """Karlis-Ntzoufras: X = X1 + X3, Y = X2 + X3. Medias lam y mu intactas."""
    l3 = np.minimum(lam3, 0.95 * np.minimum(lam, mu))
    p1, p2, p3 = _poisson_pmf(lam - l3), _poisson_pmf(mu - l3), _poisson_pmf(l3)
    m = np.zeros((len(lam), G + 1, G + 1))
    for k in range(G + 1):
        m[:, k:, k:] += (p3[:, k, None, None] * p1[:, :G + 1 - k, None]
                         * p2[:, None, :G + 1 - k])
    return _normalize(m)


_CMP_TERMS = np.arange(61)
_LOGR_GRID = np.linspace(-8.0, 8.0, 801)


def _cmp_logpmf(logr: np.ndarray, nu: float) -> np.ndarray:
    lw = (logr[:, None] * _CMP_TERMS[None, :]
          - nu * special.gammaln(_CMP_TERMS + 1)[None, :])
    return lw - special.logsumexp(lw, axis=1, keepdims=True)


def cmp_marginal(mean: np.ndarray, nu: float) -> np.ndarray:
    """CMP con la tasa que iguala la media pedida. nu=1 es Poisson."""
    grid_mean = np.maximum.accumulate(np.exp(_cmp_logpmf(_LOGR_GRID, nu)) @ _CMP_TERMS)
    logr = np.interp(mean, grid_mean, _LOGR_GRID)
    # Newton sobre la interpolación: d media / d log r = varianza.
    for _ in range(3):
        p = np.exp(_cmp_logpmf(logr, nu))
        m1 = p @ _CMP_TERMS
        var = p @ _CMP_TERMS**2 - m1**2
        logr = logr + (mean - m1) / np.maximum(var, EPS)
    return np.exp(_cmp_logpmf(logr, nu))[:, :G + 1]


def cmp_matrix(lam, mu, nu: float) -> np.ndarray:
    return _normalize(cmp_marginal(lam, nu)[:, :, None]
                      * cmp_marginal(mu, nu)[:, None, :])


_WB_J, _WB_N = 120, 25
_WB_LOG_SCALE = np.linspace(np.log(1e-3), np.log(12.0), 400)


def _weibull_beta(c: float) -> np.ndarray:
    """
    beta[j, n] = alpha_j^n / Gamma(cj+1) de la serie de McShane et al. (2008).
    Dividir por Gamma(cj+1) evita el desbordamiento de alpha para j grande.
    """
    j = np.arange(_WB_J + 1)
    lg = special.gammaln(c * j + 1)
    jj, mm = np.meshgrid(j, j, indexing="ij")
    d = jj - mm
    ok = d > 0
    w = np.zeros((_WB_J + 1, _WB_J + 1))
    w[ok] = np.exp(lg[mm[ok]] + special.gammaln(c * d[ok] + 1)
                   - special.gammaln(d[ok] + 1) - lg[jj[ok]])
    beta = np.zeros((_WB_J + 1, _WB_N + 1))
    beta[:, 0] = np.exp(-special.gammaln(j + 1))
    for n in range(_WB_N):
        beta[:, n + 1] = w @ beta[:, n]
    return beta


def _weibull_pmf(log_scale: np.ndarray, beta: np.ndarray) -> np.ndarray:
    j = np.arange(beta.shape[0])
    sign = np.where((j[:, None] + np.arange(beta.shape[1])[None, :]) % 2 == 0, 1.0, -1.0)
    return np.clip(np.exp(log_scale[:, None] * j[None, :]) @ (sign * beta), 0.0, None)


def weibull_marginal(mean: np.ndarray, c: float,
                     beta: np.ndarray | None = None) -> np.ndarray:
    """Conteo Weibull (forma c) con la escala que iguala la media. c=1 es Poisson."""
    beta = _weibull_beta(c) if beta is None else beta
    pmf = _weibull_pmf(_WB_LOG_SCALE, beta)
    mass = pmf.sum(axis=1)
    means = pmf @ np.arange(beta.shape[1]) / np.maximum(mass, EPS)
    # La serie alterna signos: donde deja de ser una distribución (masa lejos
    # de 1 o media que ya no crece) se ha perdido precisión y se corta ahí.
    bad = (np.abs(mass - 1) > 1e-6) | (np.diff(means, prepend=-np.inf) <= 0)
    stop = int(np.argmax(bad)) if bad.any() else len(means)
    log_scale = np.interp(mean, means[:stop], _WB_LOG_SCALE[:stop])
    # Newton sobre la interpolación, con la derivada exacta de la serie.
    j = np.arange(beta.shape[0])
    n = np.arange(beta.shape[1])
    signed = np.where((j[:, None] + n[None, :]) % 2 == 0, 1.0, -1.0) * beta
    for _ in range(3):
        e = np.exp(log_scale[:, None] * j[None, :])
        m1 = (e @ signed) @ n
        dm = ((e * j[None, :]) @ signed) @ n
        log_scale = np.clip(log_scale + (mean - m1) / np.maximum(dm, EPS),
                            _WB_LOG_SCALE[0], _WB_LOG_SCALE[max(stop - 1, 0)])
    return _weibull_pmf(log_scale, beta)[:, :G + 1]


def _frank(u: np.ndarray, v: np.ndarray, kappa: float) -> np.ndarray:
    if abs(kappa) < 1e-8:
        return u * v
    return -np.log1p(np.expm1(-kappa * u) * np.expm1(-kappa * v)
                     / np.expm1(-kappa)) / kappa


def copula_matrix(p: np.ndarray, q: np.ndarray, kappa: float) -> np.ndarray:
    """Matriz conjunta de dos marginales discretas unidas con cópula de Frank."""
    zero = np.zeros((len(p), 1))
    f = np.concatenate([zero, np.cumsum(p, axis=1)], axis=1)
    h = np.concatenate([zero, np.cumsum(q, axis=1)], axis=1)
    c = _frank(f[:, :, None], h[:, None, :], kappa)
    return _normalize(c[:, 1:, 1:] - c[:, :-1, 1:] - c[:, 1:, :-1] + c[:, :-1, :-1])


def weibull_copula_matrix(lam, mu, c: float, kappa: float) -> np.ndarray:
    beta = _weibull_beta(c)
    return copula_matrix(weibull_marginal(lam, c, beta),
                         weibull_marginal(mu, c, beta), kappa)


# --- Probit ordenado sobre la diferencia de goles ---------------------------

def probit_gd_probs(lam, mu, params, s0: float) -> np.ndarray:
    """
    P(diferencia de goles en <=-3, -2, …, >=3). Índice log(lam/mu) y escala
    que crece con log(lam+mu): bajo Poisson la varianza de la diferencia es
    lam+mu, y una escala fija la ignoraría.
    """
    beta, gamma, c0, *incs = params
    cuts = c0 + np.concatenate([[0.0], np.cumsum(np.exp(incs))])
    x = np.log(lam) - np.log(mu)
    sigma = np.exp(gamma * (np.log(lam + mu) - s0))
    cdf = stats.norm.cdf((cuts[None, :] - beta * x[:, None]) / sigma[:, None])
    n = len(lam)
    cdf = np.concatenate([np.zeros((n, 1)), cdf, np.ones((n, 1))], axis=1)
    return np.clip(np.diff(cdf, axis=1), EPS, None)


# --- Colapsos y pérdidas -----------------------------------------------------

def gd_from_matrix(m: np.ndarray) -> np.ndarray:
    return np.stack([m[:, _GD == k].sum(axis=1) for k in range(7)], axis=1)


def x12_from_gd(gd: np.ndarray) -> np.ndarray:
    """[local, empate, visitante], el orden de `outcome` en todo el proyecto."""
    return np.stack([gd[:, 4:].sum(axis=1), gd[:, 3], gd[:, :3].sum(axis=1)], axis=1)


def _rps_rows(p: np.ndarray, outcome: np.ndarray) -> np.ndarray:
    onehot = np.zeros_like(p)
    onehot[np.arange(len(outcome)), outcome] = 1.0
    return np.sum((np.cumsum(p, axis=1)[:, :-1]
                   - np.cumsum(onehot, axis=1)[:, :-1]) ** 2, axis=1) / 2.0


def _nll(p: np.ndarray, idx: np.ndarray) -> np.ndarray:
    return -np.log(np.clip(p[np.arange(len(idx)), idx], EPS, None))


def _losses(m_or_gd: np.ndarray, rows: dict, is_matrix: bool) -> dict:
    gd = gd_from_matrix(m_or_gd) if is_matrix else m_or_gd
    x12 = x12_from_gd(gd)
    out = {"gd_log_loss": _nll(gd, rows["gd"]),
           "rps_1x2": _rps_rows(x12, rows["outcome"]),
           "log_loss_1x2": _nll(x12, rows["outcome"])}
    if is_matrix:
        n = np.arange(len(rows["hg"]))
        out["score_log_loss"] = -np.log(np.clip(m_or_gd[n, rows["hg"], rows["ag"]],
                                                EPS, None))
        under = (m_or_gd * ((_H + _A) <= 2)).sum(axis=(1, 2))
        p = np.where(rows["hg"] + rows["ag"] <= 2, under, 1 - under)
        out["ou25_log_loss"] = -np.log(np.clip(p, EPS, None))
    return out


# --- Brazos: ajuste por máxima verosimilitud sobre filas anteriores ----------

def _fit_scalar(build: Callable, rows: dict, lo: float, hi: float) -> dict:
    nll = lambda t: float(np.mean(_nll(build(rows["lam"], rows["mu"], t)  # noqa: E731
                                       .reshape(len(rows["hg"]), -1),
                                       rows["hg"] * (G + 1) + rows["ag"])))
    return {"theta": float(optimize.minimize_scalar(nll, bounds=(lo, hi),
                                                    method="bounded").x)}


def _fit_weibull(rows: dict) -> dict:
    idx = rows["hg"] * (G + 1) + rows["ag"]

    def nll(t):
        m = weibull_copula_matrix(rows["lam"], rows["mu"], t[0], t[1])
        return float(np.mean(_nll(m.reshape(len(idx), -1), idx)))
    res = optimize.minimize(nll, x0=[1.0, 0.0], method="L-BFGS-B",
                            bounds=[(0.85, 1.4), (-5.0, 5.0)])
    return {"c": float(res.x[0]), "kappa": float(res.x[1])}


def _fit_probit(rows: dict) -> dict:
    s0 = float(np.mean(np.log(rows["lam"] + rows["mu"])))
    freq = np.bincount(rows["gd"], minlength=7) / len(rows["gd"])
    cuts = stats.norm.ppf(np.clip(np.cumsum(freq)[:-1], 1e-4, 1 - 1e-4))
    x0 = np.concatenate([[1.0, 0.5, cuts[0]],
                         np.log(np.maximum(np.diff(cuts), 1e-3))])
    nll = lambda p: float(np.mean(_nll(probit_gd_probs(  # noqa: E731
        rows["lam"], rows["mu"], p, s0), rows["gd"])))
    res = optimize.minimize(nll, x0=x0, method="L-BFGS-B",
                            bounds=[(-10, 10), (-3, 3)] + [(None, None)] * (len(x0) - 2))
    return {"params": [float(v) for v in res.x], "s0": s0}


ARMS: dict[str, dict] = {
    "poisson": {"fit": lambda r: {},
                "predict": lambda r, p: poisson_matrix(r["lam"], r["mu"]),
                "matrix": True},
    "dc_tau": {"fit": lambda r: _fit_scalar(dc_tau_matrix, r, -0.3, 0.3),
               "predict": lambda r, p: dc_tau_matrix(r["lam"], r["mu"], p["theta"]),
               "matrix": True},
    "bivariate_poisson": {
        "fit": lambda r: _fit_scalar(bivariate_poisson_matrix, r, 0.0, 0.5),
        "predict": lambda r, p: bivariate_poisson_matrix(r["lam"], r["mu"], p["theta"]),
        "matrix": True},
    "cmp": {"fit": lambda r: _fit_scalar(cmp_matrix, r, 0.3, 3.0),
            "predict": lambda r, p: cmp_matrix(r["lam"], r["mu"], p["theta"]),
            "matrix": True},
    "weibull_copula": {
        "fit": _fit_weibull,
        "predict": lambda r, p: weibull_copula_matrix(r["lam"], r["mu"],
                                                      p["c"], p["kappa"]),
        "matrix": True},
    "ordered_probit": {
        "fit": _fit_probit,
        "predict": lambda r, p: probit_gd_probs(r["lam"], r["mu"], p["params"], p["s0"]),
        "matrix": False},
}
BASELINE = "dc_tau"


def _rows(df: pd.DataFrame) -> dict:
    hg = df["home_goals"].to_numpy(dtype=int)
    ag = df["away_goals"].to_numpy(dtype=int)
    return {"lam": df["lam"].to_numpy(dtype=float),
            "mu": df["mu"].to_numpy(dtype=float),
            "hg": np.minimum(hg, G), "ag": np.minimum(ag, G),
            "gd": np.clip(hg - ag, -3, 3) + 3,
            "outcome": np.where(hg > ag, 0, np.where(hg == ag, 1, 2))}


def _weekly_delta(weeks: np.ndarray, base: np.ndarray, arm: np.ndarray,
                  iterations: int = 500) -> dict:
    """Pérdida del titular menos la del brazo: positivo favorece al brazo."""
    diff = base - arm
    out = {"estimate": round(float(diff.mean()), 5)}
    groups = list(pd.Series(np.arange(len(diff))).groupby(weeks).indices.values())
    if len(groups) < 8:
        out["ci95"] = None
        out["reason"] = "menos de ocho semanas independientes"
        return out
    rng = np.random.default_rng(42)
    draws = [float(diff[np.concatenate([groups[i] for i in
                                        rng.integers(0, len(groups), len(groups))])].mean())
             for _ in range(iterations)]
    out["ci95"] = [round(float(v), 5) for v in np.percentile(draws, [2.5, 97.5])]
    return out


def evaluate(oos: pd.DataFrame, min_fit_rows: int = MIN_FIT_ROWS) -> dict:
    """
    Ventana creciente mensual: los parámetros de cada brazo se ajustan con las
    filas fuera de muestra ANTERIORES al mes y se evalúan en ese mes. Todos los
    brazos se miden sobre exactamente las mismas filas.
    """
    df = (oos.dropna(subset=["lam", "mu", "home_goals", "away_goals"])
          .sort_values("kickoff_utc").reset_index(drop=True))
    if df.empty:
        return {"ok": False, "reason": "Sin predicciones fuera de muestra"}
    kick = pd.to_datetime(df["kickoff_utc"], utc=True)
    month = kick.dt.tz_convert(None).dt.to_period("M")
    rows_all = _rows(df)
    losses: dict[str, dict[str, np.ndarray]] = {}
    last_params: dict[str, dict] = {}
    evaluated = np.zeros(len(df), dtype=bool)

    for per in sorted(month.unique()):
        start = per.start_time.tz_localize("UTC")
        train = (kick < start).to_numpy()
        test = (month == per).to_numpy()
        if train.sum() < min_fit_rows:
            continue
        tr = {k: v[train] for k, v in rows_all.items()}
        te = {k: v[test] for k, v in rows_all.items()}
        evaluated |= test
        for name, arm in ARMS.items():
            params = arm["fit"](tr)
            last_params[name] = params
            for metric, vals in _losses(arm["predict"](te, params), te,
                                        arm["matrix"]).items():
                losses.setdefault(name, {}).setdefault(
                    metric, np.full(len(df), np.nan))[test] = vals

    if not evaluated.any():
        return {"ok": False, "reason": f"Menos de {min_fit_rows} filas previas "
                                       "para ajustar cualquier mes"}

    weeks = kick[evaluated].dt.tz_convert(None).dt.to_period("W").astype(str).to_numpy()
    arms_out, vs_base, mejoran = {}, {}, []
    base = {k: v[evaluated] for k, v in losses[BASELINE].items()}
    for name, arm in ARMS.items():
        mine = {k: v[evaluated] for k, v in losses[name].items()}
        arms_out[name] = {"params_ultimo_mes": last_params.get(name),
                          **{k: round(float(v.mean()), 5) for k, v in mine.items()}}
        if name == BASELINE:
            continue
        vs_base[name] = {k: _weekly_delta(weeks, base[k], v) for k, v in mine.items()}
        primary = "score_log_loss" if arm["matrix"] else "gd_log_loss"
        ci = vs_base[name][primary].get("ci95")
        ok = bool(ci and ci[0] > 0 and vs_base[name]["rps_1x2"]["estimate"] >= 0)
        vs_base[name]["mejora_con_ic"] = ok
        if ok:
            mejoran.append(name)

    published = {}
    if {"p_home", "p_draw", "p_away"} <= set(df.columns):
        p = df.loc[evaluated, ["p_home", "p_draw", "p_away"]].to_numpy(dtype=float)
        oc = rows_all["outcome"][evaluated]
        published = {"rps_1x2": round(float(_rps_rows(p, oc).mean()), 5),
                     "log_loss_1x2": round(float(_nll(p, oc).mean()), 5)}

    return {
        "ok": True,
        "n_obs": int(evaluated.sum()),
        "protocolo": ("Medias de Dixon-Coles fuera de muestra; forma ajustada "
                      "por ventana creciente mensual; deltas = pérdida de "
                      f"{BASELINE} menos la del brazo (positivo favorece al "
                      "brazo), IC por remuestreo de semanas"),
        "brazos": arms_out,
        "contra_titular": vs_base,
        "dixon_coles_publicado": published,
        "lectura": (f"Mejoran a {BASELINE} con el IC entero por encima de cero: "
                    + ", ".join(mejoran)) if mejoran else
                   (f"Ningún brazo mejora a {BASELINE} con el IC entero por "
                    "encima de cero. No se activa nada: solo diagnóstico."),
    }


def main() -> None:
    import argparse
    import json
    from datetime import timedelta
    from pathlib import Path

    from ..config import settings
    from ..eval.backtest import walk_forward_oos
    from .train import load_training_data

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--reuse", action="store_true",
                    help="reutilizar el walk-forward cacheado")
    args = ap.parse_args()
    cache = Path(settings.artifact_dir) / f"structure_oos_{args.days}d.pkl"
    if args.reuse and cache.exists():
        oos = pd.read_pickle(cache)
    else:
        df = load_training_data()
        start = df["kickoff_utc"].max() - timedelta(days=args.days)
        oos = walk_forward_oos(df, start, halflife=settings.decay_halflife_days,
                               xg_blend=settings.xg_blend)
        cache.parent.mkdir(parents=True, exist_ok=True)
        oos.to_pickle(cache)
    print(json.dumps(evaluate(oos), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    main()
