"""Research reference: conditional participation, no market superiority claim."""
import math
from datetime import date
import numpy as np
from scipy.stats import nbinom, poisson


def previous(history, as_of, season, season_type="regular"):
    date.fromisoformat(as_of)
    return sorted((r for r in history if r["date"] < as_of and r["season"] == season
                   and r["season_type"] == season_type and r["participated"]),
                  key=lambda r: (r["date"], r["game_id"]))


def forecast(history, as_of, season, protocol, minutes_scenario=None):
    rows = previous(history, as_of, season, protocol["season_type"])[-protocol["history_window"]:]
    if len(rows) < protocol["minimum_previous_appearances"]:
        return {"status": "abstain", "reason": "insufficient_previous_appearances", "history_count": len(rows)}
    mins = np.array([r["minutes"] for r in rows])
    rebounds = np.array([r["rebounds"] for r in rows])
    baseline_minutes = float(mins[-protocol["minutes_baseline_window"]:].mean())
    projected = float((mins[-5:].sum() + 5 * mins.mean()) / 10)
    if minutes_scenario is not None:
        if not math.isfinite(minutes_scenario) or not 0 < minutes_scenario <= 48:
            raise ValueError("scenario minutes must be in (0,48]")
        projected = float(minutes_scenario)
    minute_samples = np.clip(mins - mins.mean() + projected, 0.1, 48)
    alpha = rebounds.sum() + protocol["rate_prior_minutes"] * protocol["rate_prior_rebounds_per_minute"]
    beta = mins.sum() + protocol["rate_prior_minutes"]
    success = beta / (beta + minute_samples)
    maximum = int(max(100, np.max(nbinom.ppf(1 - 1e-10, alpha, success))))
    grid = np.arange(maximum + 1)
    pmf = nbinom.pmf(grid[:, None], alpha, success[None, :]).mean(axis=1)
    baseline_mean = float(rebounds[-protocol["minutes_baseline_window"]:].mean())
    baseline_pmf = poisson.pmf(grid, baseline_mean)
    if 1 - pmf.sum() > 1e-8 or 1 - baseline_pmf.sum() > 1e-8:
        raise ValueError("distribution tail exceeded tolerance")
    return dict(status="research_only", history_count=len(rows), history_max_date=rows[-1]["date"],
                minutes_mean=float(minute_samples.mean()), minutes_baseline=baseline_minutes,
                rebounds_mean=float(np.dot(grid, pmf)), baseline_mean=baseline_mean,
                pmf=pmf.tolist(), baseline_pmf=baseline_pmf.tolist(),
                conditional_on_participation=True, actionable=False)


def scores(pmf, outcome):
    pmf = np.asarray(pmf)
    if outcome < 0 or outcome >= len(pmf):
        raise ValueError("outcome outside evaluated distribution")
    cdf = np.cumsum(pmf)
    grid = np.arange(len(pmf))
    lower, upper = int(np.searchsorted(cdf, 0.1)), int(np.searchsorted(cdf, 0.9))
    return dict(crps=float(np.square(cdf - (grid >= outcome)).sum()),
                nll=float(-np.log(max(pmf[outcome], 1e-300))),
                mae=float(abs(np.dot(grid, pmf) - outcome)), covered80=int(lower <= outcome <= upper))


def contract_probabilities(pmf, line):
    if not math.isfinite(line) or line < 0:
        raise ValueError("invalid line")
    grid = np.arange(len(pmf))
    return dict(under=float(np.asarray(pmf)[grid < line].sum()),
                push=float(np.asarray(pmf)[grid == line].sum()),
                over=float(np.asarray(pmf)[grid > line].sum()),
                conditional_on_participation=True, void_probability=None)
