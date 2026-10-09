"""Exploratory opening-season priors; never an available-player prediction."""
from collections import defaultdict
from itertools import groupby
import re

import numpy as np
from scipy.stats import nbinom, poisson

from .evaluate import summarize
from .model import previous, scores


def preceding_season(season):
    if not re.fullmatch(r"20\d{2}-\d{2}", season):
        raise ValueError("invalid season")
    start = int(season[:4])
    if season[-2:] != str(start + 1)[-2:]:
        raise ValueError("invalid season end")
    return f"{start-1}-{str(start)[-2:]}"


def startup_forecast(history, as_of, season, protocol):
    prior = previous(history, as_of, preceding_season(season), protocol["season_type"])
    prior = prior[-protocol["previous_season_window"]:]
    current = previous(history, as_of, season, protocol["season_type"])
    if len(current) >= protocol["startup_appearances"]:
        return dict(status="abstain", reason="outside_startup_scope", current_count=len(current))
    if len(prior) < protocol["minimum_previous_season_appearances"]:
        return dict(status="abstain", reason="insufficient_previous_season", prior_count=len(prior))
    prior_minutes = np.array([r["minutes"] for r in prior])
    recent = current[-protocol["current_minutes_window"]:]
    projected = (sum(r["minutes"] for r in recent)
                 + protocol["minutes_prior_games"] * prior_minutes.mean())
    projected /= len(recent) + protocol["minutes_prior_games"]
    pool = prior + current
    exposure = np.array([r["minutes"] for r in pool])
    minute_samples = np.clip(exposure - exposure.mean() + projected, 0.1, 48)
    weight = protocol["previous_season_rate_weight"]
    alpha = (protocol["rate_prior_minutes"] * protocol["rate_prior_rebounds_per_minute"]
             + weight * sum(r["rebounds"] for r in prior) + sum(r["rebounds"] for r in current))
    beta = (protocol["rate_prior_minutes"] + weight * prior_minutes.sum()
            + sum(r["minutes"] for r in current))
    success = beta / (beta + minute_samples)
    baseline = pool[-protocol["baseline_window"]:]
    baseline_mean = float(np.mean([r["rebounds"] for r in baseline]))
    maximum = int(max(100, np.max(nbinom.ppf(1 - 1e-10, alpha, success)),
                      poisson.ppf(1 - 1e-10, baseline_mean)))
    grid = np.arange(maximum + 1)
    pmf = nbinom.pmf(grid[:, None], alpha, success[None, :]).mean(axis=1)
    baseline_pmf = poisson.pmf(grid, baseline_mean)
    if 1 - pmf.sum() > 1e-8 or 1 - baseline_pmf.sum() > 1e-8:
        raise ValueError("startup distribution tail exceeded tolerance")
    cdf = np.cumsum(pmf)
    return dict(status="research_only", protocol_version=protocol["version"],
                prior_season=preceding_season(season), prior_count=len(prior), current_count=len(current),
                history_max_date=max(r["date"] for r in pool),
                minutes_mean=float(minute_samples.mean()),
                minutes_baseline=float(np.mean([r["minutes"] for r in baseline])),
                rebounds_mean=float(np.dot(grid, pmf)),
                rebounds_central80=[int(np.searchsorted(cdf, q)) for q in (0.1, 0.9)],
                pmf=pmf.tolist(), baseline_pmf=baseline_pmf.tolist(),
                current_team_or_role_known=False, availability_known=False,
                conditional_on_participation=True, actionable=False)


def startup_backtest(dataset, protocol):
    seasons = set(protocol["evaluation_seasons"])
    needed = seasons | {preceding_season(s) for s in seasons}
    selected = sorted((r for r in dataset if r["season"] in needed
                       and r["season_type"] == protocol["season_type"]),
                      key=lambda r: (r["date"], r["game_id"], r["player_id"]))
    history, skipped, predictions = defaultdict(list), defaultdict(int), []
    for date, group in groupby(selected, key=lambda r: r["date"]):
        today = list(group)
        for row in today:
            if row["season"] not in seasons:
                continue
            if not row["participated"]:
                skipped["nonparticipant_rows"] += 1
                continue
            predicted = startup_forecast(history[row["player_id"]], date, row["season"], protocol)
            if predicted["status"] == "abstain":
                skipped[predicted["reason"]] += 1
                continue
            if predicted["history_max_date"] >= date:
                raise ValueError("future information in startup history")
            record = {k: row[k] for k in ("game_id", "player_id", "date", "season")}
            record.update(prior_count=predicted["prior_count"], current_count=predicted["current_count"],
                          history_max_date=predicted["history_max_date"], actual_rebounds=row["rebounds"],
                          actual_minutes=row["minutes"], projected_minutes=predicted["minutes_mean"])
            for label, field in (("candidate", "pmf"), ("baseline", "baseline_pmf")):
                record.update({label + "_" + k: v for k, v in scores(predicted[field], row["rebounds"]).items()})
            record["candidate_minutes_mae"] = abs(predicted["minutes_mean"] - row["minutes"])
            record["baseline_minutes_mae"] = abs(predicted["minutes_baseline"] - row["minutes"])
            predictions.append(record)
        for row in today:
            history[row["player_id"]].append(row)
    return dict(mode="exploratory_startup_conditional_on_participation", protocol_version=protocol["version"],
                summary=summarize(predictions), seasons={s: summarize([r for r in predictions if r["season"] == s])
                                                        for s in protocol["evaluation_seasons"]},
                skipped=dict(skipped), promoted=False,
                limitations=["Historical data already inspected; exploration, not confirmation",
                             "No current team/role, injuries, opponent or availability model",
                             "Evaluation only on observed participants with sufficient previous-season history",
                             "Rookies and insufficient previous-season histories abstain",
                             "No quotes, settlement rules, EV, CLV, ROI or live delivery"]), predictions
