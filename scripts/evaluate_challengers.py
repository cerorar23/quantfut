"""Evaluación de solo lectura: Elo, Dixon-Coles, mercado y ablaciones.

Ejemplo local (con PYTHONPATH=src y Postgres configurado):
    python scripts/evaluate_challengers.py --years 6 --validation-days 180

No registra artefactos, no cambia el modelo activo y no publica picks.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import timedelta

from qf.eval.backtest import check_leakage, walk_forward_oos
from qf.eval.comparison import compare_elo_dc_market
from qf.model.elo import sequential_elo
from qf.model.features import build_pit_features, merge_pit_features
from qf.model.multinomial import fit_and_validate, run_ablations
from qf.model.train import load_training_data


def evaluate(years: int, validation_days: int, step_days: int) -> dict:
    df = load_training_data(years=years)
    if df.empty:
        raise RuntimeError("No hay partidos históricos en Postgres")
    latest_match = df["kickoff_utc"].max()
    market_complete = df[["odds_home", "odds_draw", "odds_away"]].notna().all(axis=1)
    if not market_complete.any():
        raise RuntimeError("No hay cuotas sharp 1X2 completas en el histórico")
    market_end = df.loc[market_complete, "kickoff_utc"].max()
    # El walk-forward de tres vías termina donde aún hay mercado. Partidos
    # posteriores no deben entrar ni en el fit del modelo ni en Elo/features.
    df = df[df["kickoff_utc"] <= market_end].copy()
    problems = check_leakage(df)

    start = market_end - timedelta(days=validation_days)
    oos = walk_forward_oos(df, start, step_days=step_days)
    elo = sequential_elo(df)
    common = compare_elo_dc_market(oos, elo)
    features = build_pit_features(df, elo)
    enriched = merge_pit_features(oos, features)

    reports = {}
    for name, anchored in (("sport", False), ("market", True)):
        _, reports[name] = fit_and_validate(enriched, anchored=anchored)
    return {
        "years_loaded": years,
        "validation_days": validation_days,
        "step_days": step_days,
        "historical_matches": int(len(df)),
        "market_end": market_end.isoformat(),
        "market_age_days_vs_latest_match": int((latest_match - market_end).days),
        "promotion_eligible": False,
        "oos_predictions": int(len(oos)),
        "comparison": common,
        "leakage_diagnostics": problems,
        "multinomial": reports,
        "ablations": run_ablations(enriched),
        "status": "read_only_experiment",
    }


def compact_summary(report: dict) -> dict:
    """Resultado legible sin perder tamaño de muestra ni puertas de validez."""
    comparison = report["comparison"]
    return {
        "market_end": report["market_end"],
        "market_age_days_vs_latest_match": report["market_age_days_vs_latest_match"],
        "promotion_eligible": report["promotion_eligible"],
        "historical_matches": report["historical_matches"],
        "oos_predictions": report["oos_predictions"],
        "common_n": comparison["n_obs"],
        "common_match_ids_sha256": comparison["match_ids_sha256"],
        "scores": comparison["models"],
        "weekly_bootstrap": comparison["weekly_bootstrap"],
        "multinomial": {
            name: {key: value for key, value in item.items()
                   if key in ("ok", "reason", "n_fit", "n_val", "before", "after")}
            for name, item in report["multinomial"].items()
        },
        "ablations": {
            name: {key: value for key, value in item.items()
                   if key in ("ok", "reason", "n_fit", "n_val", "before", "after")}
            for name, item in report["ablations"].items()
        },
        "leakage_diagnostics": report["leakage_diagnostics"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--validation-days", type=int, default=180)
    parser.add_argument("--step-days", type=int, default=90)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    report = evaluate(args.years, args.validation_days, args.step_days)
    print(json.dumps(compact_summary(report) if args.compact else report,
                     indent=2, default=str))
