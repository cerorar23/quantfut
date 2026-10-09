import json
from pathlib import Path

import pytest

from nba.model import forecast
from nba.startup import preceding_season, startup_forecast, startup_backtest
from test_pipeline import history, PROTOCOL

STARTUP = json.loads((Path(__file__).resolve().parents[1] / "startup_protocol.json").read_text())


def test_opening_season_can_forecast_from_explicit_previous_season():
    rows = history()
    assert forecast(rows, "2026-10-20", "2026-27", PROTOCOL)["status"] == "abstain"
    result = startup_forecast(rows, "2026-10-20", "2026-27", STARTUP)
    assert result["prior_season"] == "2025-26" and result["current_count"] == 0
    assert result["history_max_date"] < "2026-10-20"
    assert sum(result["pmf"]) == pytest.approx(1, abs=1e-8)
    assert not result["actionable"] and not result["availability_known"]


def test_startup_excludes_today_future_and_older_seasons():
    rows = history()
    base = startup_forecast(rows, "2026-10-20", "2026-27", STARTUP)
    contaminated = rows + [dict(rows[0], date="2026-10-20", rebounds=999, season="2026-27"),
                           dict(rows[0], date="2026-10-21", rebounds=999, season="2026-27"),
                           dict(rows[0], season="2024-25", rebounds=999),
                           dict(rows[0], season_type="preseason", rebounds=999)]
    assert startup_forecast(contaminated, "2026-10-20", "2026-27", STARTUP) == base


def test_rookies_abstain_and_existing_season_model_is_not_replaced():
    assert startup_forecast(history(2), "2026-10-20", "2026-27", STARTUP)["reason"] == "insufficient_previous_season"
    rows = history() + [dict(r, date=r["date"].replace("2025", "2026"), season="2026-27") for r in history()]
    assert startup_forecast(rows, "2026-12-01", "2026-27", STARTUP)["reason"] == "outside_startup_scope"


def test_startup_replay_same_day_predictions_before_updates():
    rows = [dict(r, season="2023-24", date=r["date"].replace("2025", "2023")) for r in history()]
    targets = [dict(rows[0], date="2024-10-22", season="2024-25", game_id="0022400001", rebounds=2),
               dict(rows[0], date="2024-10-22", season="2024-25", game_id="0022400002", rebounds=20)]
    report, predictions = startup_backtest(rows + targets, STARTUP)
    assert len(predictions) == 2 and all(r["current_count"] == 0 for r in predictions)
    assert predictions[0]["projected_minutes"] == predictions[1]["projected_minutes"]
    assert not report["promoted"]


@pytest.mark.parametrize("season", ["2026", "2026-26", "bad"])
def test_season_rollover_validated(season):
    with pytest.raises(ValueError):
        preceding_season(season)
