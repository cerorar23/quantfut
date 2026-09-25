"""Comparaciones probabilísticas sobre exactamente las mismas observaciones."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from .metrics import brier, ece, log_loss, rps


def _score(probs: np.ndarray, outcomes: np.ndarray) -> dict:
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(outcomes)), outcomes] = 1.0
    return {
        "rps": round(rps(probs, outcomes), 5),
        "log_loss": round(log_loss(probs, outcomes), 5),
        "brier": round(brier(probs, outcomes), 5),
        "ece": round(ece(probs.ravel(), onehot.ravel()), 5),
    }


def _rps_per_match(probs: np.ndarray, outcomes: np.ndarray) -> np.ndarray:
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(outcomes)), outcomes] = 1.0
    return np.sum((np.cumsum(probs, axis=1)[:, :-1]
                   - np.cumsum(onehot, axis=1)[:, :-1]) ** 2, axis=1) / 2.0


def _weekly_bootstrap(usable: pd.DataFrame, losses: dict[str, np.ndarray],
                      iterations: int = 500) -> dict:
    """Intervalos de RPS mediante remuestreo de semanas, no partidos sueltos."""
    weeks = (pd.to_datetime(usable["kickoff_utc"], utc=True)
             .dt.tz_convert(None).dt.to_period("W"))
    groups = list(usable.groupby(weeks, sort=True).indices.values())
    if len(groups) < 8:
        return {"reason": "menos de ocho semanas independientes"}
    rng = np.random.default_rng(42)
    out = {}
    base = losses["dixon_coles"]
    for other in ("elo", "market"):
        differences = losses[other] - base
        estimates = []
        for _ in range(iterations):
            draw = rng.integers(0, len(groups), size=len(groups))
            sample = np.concatenate([groups[i] for i in draw])
            estimates.append(float(np.mean(differences[sample])))
        lo, hi = np.percentile(estimates, [2.5, 97.5])
        out[f"rps_delta_vs_{other}"] = {
            "estimate": round(float(np.mean(differences)), 5),
            "ci95": [round(float(lo), 5), round(float(hi), 5)],
            "positive_favors_dixon_coles": True,
        }
    return out


def compare_elo_dc_market(dc_oos: pd.DataFrame,
                          elo_oos: pd.DataFrame) -> dict:
    """
    Evalúa Elo, Dixon-Coles y mercado sobre la intersección exacta.

    Las filas sin las tres cuotas de cierre se excluyen para TODOS los modelos;
    comparar cada uno con un ``n`` distinto produciría un ranking engañoso.
    """
    elo_cols = ["match_id", "elo_p_home", "elo_p_draw", "elo_p_away"]
    merged = dc_oos.merge(elo_oos[elo_cols], on="match_id", how="inner",
                          validate="one_to_one")
    needed = ["p_home", "p_draw", "p_away", "mk_home", "mk_draw", "mk_away",
              "elo_p_home", "elo_p_draw", "elo_p_away", "outcome"]
    usable = merged.dropna(subset=needed).sort_values(["kickoff_utc", "match_id"])
    if usable.empty:
        raise ValueError("No hay observaciones comunes con mercado, Elo y Dixon-Coles")

    outcomes = usable["outcome"].to_numpy(dtype=int)
    columns = {
        "dixon_coles": ["p_home", "p_draw", "p_away"],
        "elo": ["elo_p_home", "elo_p_draw", "elo_p_away"],
        "market": ["mk_home", "mk_draw", "mk_away"],
    }
    scores = {name: _score(usable[cols].to_numpy(dtype=float), outcomes)
              for name, cols in columns.items()}
    losses = {name: _rps_per_match(usable[cols].to_numpy(dtype=float), outcomes)
              for name, cols in columns.items()}

    by_league: dict[str, dict] = {}
    for league, group in usable.groupby("league_id"):
        oc = group["outcome"].to_numpy(dtype=int)
        by_league[str(league)] = {
            "n": int(len(group)),
            **{name: _score(group[cols].to_numpy(dtype=float), oc)
               for name, cols in columns.items()},
        }

    ids = "\n".join(usable["match_id"].astype(str)).encode()
    return {
        "n_obs": int(len(usable)),
        "first_kickoff_utc": usable["kickoff_utc"].iloc[0].isoformat(),
        "last_kickoff_utc": usable["kickoff_utc"].iloc[-1].isoformat(),
        "match_ids_sha256": hashlib.sha256(ids).hexdigest(),
        "models": scores,
        "by_league": by_league,
        "weekly_bootstrap": _weekly_bootstrap(usable, losses),
    }
