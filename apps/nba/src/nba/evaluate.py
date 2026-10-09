from collections import defaultdict
from itertools import groupby
import numpy as np

from .model import forecast, scores


def summarize(rows):
    if not rows:
        return {"evaluated_rows": 0}
    keys = [k for k in rows[0] if k.startswith(("candidate_", "baseline_"))]
    result = {"evaluated_rows": len(rows), "games": len({r["game_id"] for r in rows})}
    result.update({k: float(np.mean([r[k] for r in rows])) for k in keys})
    games = defaultdict(list)
    for row in rows:
        games[row["game_id"]].append(row["candidate_crps"] - row["baseline_crps"])
    # Resample whole games, retaining the observation-weighted estimand.
    sums = np.array([sum(v) for v in games.values()])
    counts = np.array([len(v) for v in games.values()])
    rng = np.random.default_rng(20261004)
    index = rng.integers(0, len(sums), size=(500, len(sums)))
    differences = sums[index].sum(axis=1) / counts[index].sum(axis=1)
    result["crps_difference_candidate_minus_baseline_ci95"] = np.quantile(differences, [0.025, 0.975]).tolist()
    return result


def backtest(dataset, protocol):
    history, predictions = defaultdict(list), []
    skipped = defaultdict(int)
    selected = sorted((r for r in dataset if r["season"] in protocol["evaluation_seasons"]
                       and r["season_type"] == protocol["season_type"]),
                      key=lambda r: (r["date"], r["game_id"], r["player_id"]))
    for date, group in groupby(selected, key=lambda r: r["date"]):
        today = list(group)
        for row in today:
            if not row["participated"]:
                skipped["nonparticipant_rows"] += 1
                continue
            predicted = forecast(history[row["player_id"]], date, row["season"], protocol)
            if predicted["status"] == "abstain":
                skipped[predicted["reason"]] += 1
                continue
            if predicted["history_max_date"] >= date:
                raise ValueError("future information in history")
            record = {k: row[k] for k in ("game_id", "player_id", "season", "date")}
            record.update(history_max_date=predicted["history_max_date"], actual_rebounds=row["rebounds"],
                          actual_minutes=row["minutes"], projected_minutes=predicted["minutes_mean"])
            for label, field in (("candidate", "pmf"), ("baseline", "baseline_pmf")):
                record.update({label + "_" + k: v for k, v in scores(predicted[field], row["rebounds"]).items()})
            record["candidate_minutes_mae"] = abs(predicted["minutes_mean"] - row["minutes"])
            record["baseline_minutes_mae"] = abs(predicted["minutes_baseline"] - row["minutes"])
            predictions.append(record)
        # All of a target date is predicted before any of its outcomes enter history.
        for row in today:
            history[row["player_id"]].append(row)
    seasons = {}
    for season in protocol["evaluation_seasons"]:
        rows = [r for r in predictions if r["season"] == season]
        dates = sorted({r["date"] for r in rows})
        blocks = np.array_split(dates, 3)
        seasons[season] = dict(overall=summarize(rows), blocks=[
            dict(start=str(b[0]), end=str(b[-1]), **summarize([r for r in rows if r["date"] in set(b)]))
            for b in blocks if len(b)])
    return dict(mode="retrospective_replay_conditional_on_participation", protocol_version=protocol["version"],
                summary=summarize(predictions), seasons=seasons, skipped=dict(skipped), promoted=False,
                limitations=["Retrospective source; original availability timestamps absent",
                             "Observed participants define evaluation subset; no availability model",
                             "Whole-game quarantine may bias the evaluated subset",
                             "No odds/news; no EV, CLV, ROI or commercial validation"]), predictions
