from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from qf.ingest import xg_api_football as xg
from qf.model.xg import xg_at_cutoff
from qf.model.train import dataset_hash


def response(home="1.33", away="2.87"):
    return [{"team": {"id": tid}, "statistics": [
        {"type": "expected_goals", "value": value}]
    } for tid, value in ((10, home), (20, away))]


def test_zero_is_valid_and_teams_are_matched_by_id():
    assert xg.extract_xg(list(reversed(response("0.00", "2.87"))), 10, 20) == (0, 2.87)


@pytest.mark.parametrize("bad", [None, "", "abc", "NaN", "inf", "-0.2", True])
def test_invalid_or_absent_xg_never_becomes_zero(bad):
    assert xg.extract_xg(response(bad), 10, 20) is None


def test_missing_wrong_or_duplicate_team_is_rejected():
    r = response()
    assert xg.extract_xg(r[:1], 10, 20) is None
    assert xg.extract_xg(r, 10, 30) is None
    assert xg.extract_xg(r + r[:1], 10, 20) is None
    assert xg.extract_xg(r, 10, 10) is None
    r[0]["statistics"] *= 2
    assert xg.extract_xg(r, 10, 20) is None


def test_capture_preserves_decimal_pair_and_never_overwrites_existing(monkeypatch):
    calls = []
    monkeypatch.setattr(xg, "execute", lambda sql, params: calls.append((sql, params)) or 1)
    assert xg.record_capture("m1", response(), 10, 20) == 1
    sql, params = calls[-1]
    assert params == (1.33, 2.87, "m1")
    assert "home_xg IS NULL AND away_xg IS NULL" in sql
    assert "xg_recorded_at = now()" in sql
    assert "status = 'finished'" in sql


def test_missing_pair_only_records_attempt(monkeypatch):
    calls = []
    monkeypatch.setattr(xg, "execute", lambda sql, params: calls.append(sql) or 1)
    assert xg.record_capture("m1", response(None), 10, 20) == 0
    assert len(calls) == 1 and "home_xg" not in calls[0]


def frame():
    return pd.DataFrame({
        "home_xg": [1.1, 1.2, 1.3, 1.4], "away_xg": [0, 0.2, 0.3, 0.4],
        "xg_source": [None, "api_football", "api_football", "api_football"],
        "xg_recorded_at": ["2026-10-12", "2026-10-03", "2026-10-12", None]})


def test_cutoff_excludes_later_capture_and_unknown_time_but_keeps_legacy():
    df = frame()
    original = df.copy(deep=True)
    home, away = xg_at_cutoff(df, datetime(2026, 10, 4, tzinfo=timezone.utc))
    np.testing.assert_allclose(home, [1.1, 1.2, np.nan, np.nan], equal_nan=True)
    np.testing.assert_allclose(away, [0, 0.2, np.nan, np.nan], equal_nan=True)
    pd.testing.assert_frame_equal(df, original)
    np.testing.assert_allclose(xg_at_cutoff(df, "2026-10-12")[0],
                               [1.1, 1.2, 1.3, np.nan], equal_nan=True)


def test_api_source_without_timestamp_column_fails_closed():
    home, away = xg_at_cutoff(frame().drop(columns="xg_recorded_at"), "2026-11-01")
    np.testing.assert_allclose(home, [1.1, np.nan, np.nan, np.nan], equal_nan=True)
    np.testing.assert_allclose(away, [0, np.nan, np.nan, np.nan], equal_nan=True)


def test_capture_date_and_source_are_part_of_dataset_hash():
    df = frame()
    original = dataset_hash(df)
    df.loc[1, "xg_recorded_at"] = "2026-10-05"
    assert dataset_hash(df) != original
    df = frame()
    df.loc[1, "xg_source"] = None
    assert dataset_hash(df) != original


def test_player_target_also_respects_the_capture_cutoff():
    from qf.model.masmenos import objetivo
    df = frame().assign(home_goals=2, away_goals=1, away_xg=0.0)
    target = objetivo(df, 1.0, "2026-10-04")
    np.testing.assert_allclose(target, [1.1, 1.2, 1.0, 1.0])
    np.testing.assert_allclose(objetivo(df, 1.0, "2026-10-13"), [1.1, 1.2, 1.3, 1.0])


@pytest.mark.parametrize("meta,available", [
    ({"quota_remaining": "1125", "quota_limit": "7500"}, False),
    ({"quota_remaining": "1126", "quota_limit": "7500"}, True),
    ({"quota_remaining": None, "quota_limit": "7500"}, False),
    ({}, False)])
def test_quota_reserve(meta, available):
    assert xg.quota_available(meta) is available


def test_daily_recheck_stops_at_quota_reserve(monkeypatch):
    rows = [{"match_id": f"m{i}", "af_id": str(i), "home_af": 10, "away_af": 20}
            for i in range(3)]
    monkeypatch.setattr(xg, "query", lambda *args: rows)
    monkeypatch.setattr(xg, "execute", lambda *args: 1)
    calls = []
    def get(endpoint, params=None):
        calls.append(endpoint)
        remaining = "1126" if endpoint == "status" else "1125"
        return response(), {"quota_remaining": remaining, "quota_limit": "7500"}
    monkeypatch.setattr(xg.af, "get", get)
    report = xg._run(35, 100)
    assert report["requests"] == report["captured"] == 1
    assert report["quota_stopped"] is True
    assert calls == ["status", "fixtures/statistics"]


def test_provider_failure_stops_recheck_and_is_reported(monkeypatch):
    monkeypatch.setattr(xg, "query", lambda *args: [
        {"match_id": "m1", "af_id": "1", "home_af": 10, "away_af": 20}])
    monkeypatch.setattr(xg, "execute", lambda *args: 1)
    def get(endpoint, params=None):
        if endpoint == "status":
            return [], {"quota_remaining": "2000", "quota_limit": "7500"}
        raise RuntimeError("offline")
    monkeypatch.setattr(xg.af, "get", get)
    report = xg._run(35, 100)
    assert report["errors"] == 1 and report["captured"] == 0


def test_dixon_coles_uses_goals_until_xg_capture_then_uses_xg():
    from qf.model.dixon_coles import DixonColes
    df = pd.DataFrame([{
        "kickoff_utc": pd.Timestamp("2026-01-01", tz="UTC") + pd.Timedelta(days=i),
        "home_team": "A" if i % 2 else "B", "away_team": "B" if i % 2 else "A",
        "home_goals": 1 + i % 3, "away_goals": i % 2,
        "home_xg": 0.1, "away_xg": 4.0, "xg_source": "api_football",
        "xg_recorded_at": "2026-10-12T12:00:00Z"} for i in range(100)])
    before = datetime(2026, 10, 11, tzinfo=timezone.utc)
    missing = df.assign(home_xg=np.nan, away_xg=np.nan)
    base = DixonColes().fit(missing, as_of=before).predict("A", "B")["1x2"]
    guarded = DixonColes().fit(df, as_of=before).predict("A", "B")["1x2"]
    assert guarded == pytest.approx(base)
    after = DixonColes().fit(df, as_of=datetime(2026, 10, 13, tzinfo=timezone.utc))
    assert abs(after.predict("A", "B")["1x2"]["home"] - base["home"]) > 0.1


def test_sequential_replay_does_not_inject_late_api_xg():
    from qf.model.kalman import DynamicRatings
    df = pd.DataFrame([{
        "match_id": str(i), "league_id": "test",
        "kickoff_utc": pd.Timestamp("2026-01-01", tz="UTC") + pd.Timedelta(days=i),
        "home_team": "A" if i % 2 else "B", "away_team": "B" if i % 2 else "A",
        "home_goals": 1 + i % 3, "away_goals": i % 2,
        "home_xg": 0.1, "away_xg": 4.0, "xg_source": "api_football",
        "xg_recorded_at": "2026-10-12T12:00:00Z"} for i in range(100)])
    expected = DynamicRatings().predict_sequential(df.assign(home_xg=np.nan, away_xg=np.nan))
    actual = DynamicRatings().predict_sequential(df)
    pd.testing.assert_frame_equal(actual, expected)
