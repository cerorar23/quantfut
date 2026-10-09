"""Discrete calibration diagnostics on fixed retrospective startup predictions."""
from collections import defaultdict
import hashlib

import numpy as np

from .startup import startup_forecast
from .model import scores

VERSION = "startup-calibration-diagnostic-v1"
LINES = (4.5, 7.5, 10.5)


def diagnostics(pmf, actual, key):
    p = np.asarray(pmf, dtype=float)
    if (p.ndim != 1 or not np.isfinite(p).all() or (p < 0).any()
            or abs(p.sum() - 1) > 1e-8 or not isinstance(actual, int) or not 0 <= actual < len(p)):
        raise ValueError("invalid outcome distribution")
    cdf = np.cumsum(p)
    low, high = (int(np.searchsorted(cdf, q)) for q in (.1, .9))
    # Stable randomization independent of iteration order; discretization-aware PIT.
    uniform = (int.from_bytes(hashlib.sha256(("20261005:" + key).encode()).digest()[:8], "big") + .5) / 2**64
    below = float(cdf[actual - 1]) if actual else 0.0
    return dict(randomized_pit=below + uniform * float(p[actual]),
                covered80=int(low <= actual <= high), interval_mass=float(p[low:high + 1].sum()),
                interval_width=high - low,
                overs={str(line): dict(probability=float(p[int(line) + 1:].sum()),
                                      actual=int(actual > line)) for line in LINES})


def calibration_report(dataset, predictions, protocol, replicates=500):
    histories = defaultdict(list)
    outcomes = {}
    for row in dataset:
        histories[row["player_id"]].append(row)
        key = (row["game_id"], row["player_id"])
        if key in outcomes:
            raise ValueError("ambiguous normalized outcome")
        outcomes[key] = row
    rows = []
    seen = set()
    for record in predictions:
        key = (record["game_id"], record["player_id"])
        actual = outcomes.get(key)
        if (key in seen or actual is None or actual["date"] != record["date"]
                or actual["season"] != record["season"] or actual["rebounds"] != record["actual_rebounds"]
                or actual["minutes"] != record["actual_minutes"]):
            raise ValueError("prediction/outcome integrity mismatch")
        seen.add(key)
        forecast = startup_forecast(histories[record["player_id"]], record["date"], record["season"], protocol)
        if forecast["status"] == "abstain" or forecast["history_max_date"] >= record["date"]:
            raise ValueError("replay scope or PIT mismatch")
        if abs(forecast["minutes_mean"] - record["projected_minutes"]) > 1e-8:
            raise ValueError("sealed forecast does not reproduce")
        for label, field in (("candidate", "pmf"), ("baseline", "baseline_pmf")):
            metric = scores(forecast[field], record["actual_rebounds"])
            if any(abs(metric[m] - record[label + "_" + m]) > 1e-8 for m in ("crps", "nll")):
                raise ValueError("sealed distribution does not reproduce")
        key = f"{record['game_id']}:{record['player_id']}"
        rows.append(dict(game_id=record["game_id"], season=record["season"],
                         candidate=diagnostics(forecast["pmf"], record["actual_rebounds"], key),
                         baseline=diagnostics(forecast["baseline_pmf"], record["actual_rebounds"], key)))

    def summarize(selected, label):
        values = [r[label] for r in selected]
        residuals = np.array([v["covered80"] - v["interval_mass"] for v in values])
        clusters = defaultdict(list)
        for row, residual in zip(selected, residuals):
            clusters[row["game_id"]].append(residual)
        aggregates = np.array([(sum(v), len(v)) for v in clusters.values()])
        rng = np.random.default_rng(20261005)
        draws = []
        for _ in range(replicates):
            sampled = aggregates[rng.integers(0, len(aggregates), len(aggregates))]
            draws.append(float(sampled[:, 0].sum() / sampled[:, 1].sum()))
        reliability = {}
        for line in LINES:
            bins = []
            for index in range(10):
                members = [v["overs"][str(line)] for v in values
                           if min(int(v["overs"][str(line)]["probability"] * 10), 9) == index]
                bins.append(dict(range=[index / 10, (index + 1) / 10], n=len(members),
                                 mean_probability=float(np.mean([v["probability"] for v in members])) if members else None,
                                 observed_rate=float(np.mean([v["actual"] for v in members])) if members else None))
            reliability[str(line)] = bins
        return dict(n=len(values), games=len(clusters),
                    coverage80=float(np.mean([v["covered80"] for v in values])),
                    expected_discrete_interval_mass=float(np.mean([v["interval_mass"] for v in values])),
                    coverage_minus_mass=float(residuals.mean()),
                    coverage_minus_mass_game_bootstrap_ci95=np.quantile(draws, [.025, .975]).tolist(),
                    mean_interval_width=float(np.mean([v["interval_width"] for v in values])),
                    randomized_pit_bins=np.histogram([v["randomized_pit"] for v in values], bins=np.linspace(0, 1, 11))[0].tolist(),
                    line_reliability=reliability)
    if not rows:
        raise ValueError("no diagnostic observations")
    groups = {"all": rows, **{s: [r for r in rows if r["season"] == s] for s in sorted({r['season'] for r in rows})}}
    return dict(version=VERSION, summaries={s: {label: summarize(v, label) for label in ("candidate", "baseline")}
                                          for s, v in groups.items()},
                seed=20261005, bootstrap_replicates=replicates, promoted=False,
                limits=["Fixed diagnostic, no parameter fitting or selection", "Previously inspected historical seasons are exploratory",
                        "Game bootstrap does not capture all temporal/player dependence", "Reliability at fixed research thresholds is not odds profitability",
                        "Observed participant selection excludes unknown availability and DNP risk"])
