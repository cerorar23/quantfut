"""Shin/Power y umbrales 1X2 en sombra sobre el MISMO histórico pre-cierre.

No certifica una estrategia nueva: estos CSV ya se usaron para diseñar el
criterio actual. La vara de todos los brazos es SIEMPRE el cierre de Pinnacle
sin margen por Shin; cambiar método de selección no mueve la meta.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import settings
from ..publish import picks
from . import soft_vs_sharp as svs

METHODS = ("shin", "power")
THRESHOLDS = (0.01, 0.015, 0.02, 0.025, 0.03)


def _calibration(quotes: pd.DataFrame) -> dict:
    """Log-loss/RPS temprano en todos los partidos, no solo en los elegidos."""
    unique = quotes.drop_duplicates(["match", "selection"])
    probs = unique.pivot(index="match", columns="selection", values="p_fair_early")
    wins = unique.pivot(index="match", columns="selection", values="won")
    order = ["home", "draw", "away"]
    probs, wins = probs.reindex(columns=order), wins.reindex(columns=order)
    valid = probs.notna().all(axis=1) & wins.notna().all(axis=1)
    p = probs.loc[valid].to_numpy(float)
    y = wins.loc[valid].to_numpy(bool)
    if not len(p):
        return {"n_matches": 0, "log_loss": None, "rps": None}
    outcome = y.argmax(axis=1)
    log_loss = -np.log(np.clip(p[np.arange(len(p)), outcome], 1e-12, 1)).mean()
    cumulative = np.cumsum(p, axis=1)[:, :2]
    target = np.cumsum(y, axis=1)[:, :2]
    rps = np.mean(np.mean((cumulative - target) ** 2, axis=1))
    return {"n_matches": len(p), "log_loss": round(float(log_loss), 6),
            "rps": round(float(rps), 6)}


def _threshold(price: pd.Series, rule: str) -> pd.Series:
    if rule == "dynamic_v1":
        # Hipótesis prefijada, nunca una configuración recomendada de producción.
        return pd.Series(np.where(price < 1.8, 0.015,
                                  np.where(price < 3.5, 0.02, 0.03)),
                         index=price.index)
    return pd.Series(float(rule), index=price.index)


def select_candidates(quotes: pd.DataFrame, rule: str,
                      books: tuple[str, ...]) -> pd.DataFrame:
    """Proxy offline: una selección por partido, sin inventar precios vigentes."""
    q = svs._verified(quotes)
    q = q[q["market"].eq("h2h") & q["book"].isin(books)].copy()
    if q.empty:
        return q
    q["raw_edge"] = q["price_early"] * q["p_fair_early"] - 1.0
    q = q[q["raw_edge"] >= _threshold(q["price_early"], rule)].copy()
    if q.empty:
        return q
    q["persistence"] = q["book"].map(picks.PERSISTENCE).fillna(
        picks.UNMEASURED_PERSISTENCE)
    q["expected_edge"] = q["raw_edge"] * q["persistence"]
    p_exp = (1 + q["expected_edge"]) / q["price_early"]
    q["stake_units"] = [picks.kelly(float(p), float(price),
                                    settings.kelly_fraction,
                                    settings.max_stake_units)
                        for p, price in zip(p_exp, q["price_early"])]
    q = q[q["stake_units"] > picks.MIN_STAKE_UNITS]
    if q.empty:
        return q
    # Como en select_daily, gana el edge esperado de mayor tamaño; no se
    # simula el tope diario porque el CSV no dice cuándo estuvo disponible.
    return (q.sort_values(["match", "expected_edge", "price_early"],
                          ascending=[True, False, False])
             .drop_duplicates("match").reset_index(drop=True))


def compare(raw: pd.DataFrame, dataset: dict,
            books: tuple[str, ...] | None = None) -> dict:
    books = books or settings.soft_books
    by_method = {method: svs.build_quotes(raw, method=method)
                 for method in METHODS}
    shin = by_method["shin"]
    if shin.empty:
        return {"dataset": dataset, "status": "sin_1x2_comparable"}
    shin = shin[shin["market"] == "h2h"].reset_index(drop=True)
    methods = {}
    common = ["match", "selection", "book", "price_early"]
    for method, all_quotes in by_method.items():
        q = all_quotes[all_quotes["market"] == "h2h"].reset_index(drop=True).copy()
        if not q[common].equals(shin[common]):
            raise ValueError("Shin y Power no usan exactamente las mismas cuotas")
        calibration = _calibration(q)
        # Cierre independiente y fijo: no favorece al método que elige.
        q["p_fair_close"] = shin["p_fair_close"].to_numpy(float)
        selected_by_rule = {}
        for rule in [*(str(t) for t in THRESHOLDS), "dynamic_v1"]:
            selected_by_rule[rule] = select_candidates(q, rule, books)
        baseline_matches = set(selected_by_rule["0.02"]["match"])
        baseline_choice = {
            r["match"]: (r["book"], r["selection"])
            for _, r in selected_by_rule["0.02"].iterrows()
        }
        variants = {}
        for rule, selected in selected_by_rule.items():
            extra = selected[~selected["match"].isin(baseline_matches)]
            extra_eval = svs.evaluate(extra)
            changed = sum(
                r["match"] in baseline_choice
                and (r["book"], r["selection"]) != baseline_choice[r["match"]]
                for _, r in selected.iterrows()
            )
            variants[rule] = {**svs.evaluate(selected),
                              "new_matches_vs_2pct": int(len(extra)),
                              "new_matches_ev_close": extra_eval.get("ev_close"),
                              "new_matches_ev_close_ci95": extra_eval.get("ev_close_ci95"),
                              "changed_picks_vs_2pct": int(changed),
                              "by_book_n": {str(k): int(v) for k, v in
                                            selected["book"].value_counts().items()}}
        methods[method] = {"calibration": calibration, "variants": variants}
    return {"dataset": dataset, "status": "historico_exploratorio_no_promocion",
            "books": list(books), "market": "h2h",
            "close_reference": "pinnacle_shin_constant",
            "selection": "una_por_partido; persistencia estimada al 2%; "
                         "sin disponibilidad ni tope diario",
            "methods": methods}


def run_cache(cache_dir: Path = Path(".local/fd_cache"),
              seasons: tuple[str, ...] = svs.DEFAULT_SEASONS,
              books: tuple[str, ...] | None = None) -> dict:
    """Usa solo CSV ya guardados; jamás descarga ni cambia producción."""
    codes = sorted({p.name.split("_")[0] for p in cache_dir.glob("*.csv")})
    leagues = {code: code for code in codes
               if all((cache_dir / f"{code}_{season}.csv").is_file()
                      for season in seasons)}
    if not leagues:
        raise FileNotFoundError("No hay temporadas completas en la caché local")
    raw, dataset = svs.load_csvs(leagues, seasons, cache_dir)
    dataset["league_labels"] = "codigos_football_data_sin_postgres"
    return compare(raw, dataset, books)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    parser.add_argument("--seasons", nargs="+", default=list(svs.DEFAULT_SEASONS))
    args = parser.parse_args()
    print(json.dumps(run_cache(args.cache, tuple(args.seasons)),
                     ensure_ascii=False, indent=2))
