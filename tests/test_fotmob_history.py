"""Fechas, identidad, datos ausentes y reanudación del histórico FotMob."""
from datetime import date
from urllib.error import HTTPError

import pytest

from qf.ingest import fotmob_history as fm


def fixture():
    return {"league_id": "gb.premier_league", "fotmob_league_id": 47,
            "season": "2023/2024", "fotmob_match_id": "123", "kickoff_utc": "2024-01-02T02:00:00+00:00",
            "home_team_id": "1", "away_team_id": "2", "home_team": "A", "away_team": "B"}


def payload():
    return {"general": {"matchId": "123", "leagueId": 47, "matchTimeUTCDate": "2024-01-02T02:00:00Z",
                        "homeTeam": {"id": 1}, "awayTeam": {"id": 2}},
            "header": {"status": {"finished": True}},
            "content": {"stats": {"Periods": {
                "All": {"stats": [{"title": "Top stats", "stats": [
                    {"key": "expected_goals", "stats": ["1.23", "0.00"],
                     "rawStats": [{"value": 1.234}, {"value": 0}]},
                    {"key": "corners", "stats": [7, 0]}]}]},
                "FirstHalf": {"stats": [{"key": "expected_goals", "stats": [0.5, 0]}]},
            }}, "shotmap": {"shots": [{"expectedGoals": 1.234}]}}}


def test_full_match_xg_not_half_and_preserves_zero():
    row = fm.normalize_match(fixture(), payload(), "2026-10-03T12:00:00Z")
    assert row["home_xg"] == 1.234
    assert row["away_xg"] == 0
    assert row["away_corners"] == 0
    assert row["download_status"] == "with_xg"


def test_absent_xg_is_not_zero():
    data = payload()
    data["content"]["stats"] = None
    row = fm.normalize_match(fixture(), data, "2026-10-03T12:00:00Z")
    assert row["home_xg"] is None and row["away_xg"] is None
    assert row["download_status"] == "missing_xg"


def test_historical_tournament_belongs_to_explicit_parent_league():
    data = payload()
    data["general"].update(leagueId=889724, parentLeagueId=47)
    row = fm.normalize_match(fixture(), data, "2026-10-03T12:00:00Z")
    assert row["download_status"] == "with_xg"
    data["general"]["parentLeagueId"] = 230
    with pytest.raises(ValueError, match="Competición"):
        fm.normalize_match(fixture(), data, "2026-10-03T12:00:00Z")


@pytest.mark.parametrize("field,value", [("matchId", "124"), ("leagueId", 87), ("homeTeam", {"id": 2}),
                                          ("matchTimeUTCDate", "2024-02-02T02:00:00Z")])
def test_mismatched_identity_is_rejected(field, value):
    data = payload()
    data["general"][field] = value
    with pytest.raises(ValueError):
        fm.normalize_match(fixture(), data, "2026-10-03T12:00:00Z")


def test_only_finished_matches_within_mexico_dates():
    def match(mid, kickoff, finished=True):
        return {"id": mid, "home": {"id": 1, "name": "A"}, "away": {"id": 2, "name": "B"},
                "status": {"utcTime": kickoff, "finished": finished}}
    hub = {"details": {"id": 47, "selectedSeason": "2023/2024"}, "fixtures": {"allMatches": [
        match(1, "2024-01-01T02:00:00Z"),  # aún 31-dic en México
        match(2, "2024-01-02T02:00:00Z"),  # aún 1-ene en México
        match(3, "2024-01-01T20:00:00Z", False),
        match(4, "2024-01-02T20:00:00Z"),
    ]}}
    rows = fm.collect_fixtures(hub, "gb.premier_league", "2023/2024", date(2024, 1, 1), date(2024, 1, 1))
    assert [r["fotmob_match_id"] for r in rows] == ["2"]
    with pytest.raises(ValueError):
        fm.collect_fixtures(hub, "gb.premier_league", "2024/2025", date(2024, 1, 1), date(2026, 10, 3))


def test_season_crossing_start_year_is_included():
    hub = {"allAvailableSeasons": ["2026/2027", "2025/2026", "2024/2025", "2023/2024", "2022/2023"]}
    assert fm.season_labels(hub, date(2024, 1, 1), date(2026, 10, 3)) == hub["allAvailableSeasons"][:4]


@pytest.mark.parametrize("status", [401, 403, 429])
def test_access_denial_stops_without_retry(monkeypatch, tmp_path, status):
    calls = []
    def denied(request, **kwargs):
        calls.append(request.full_url)
        raise HTTPError(request.full_url, status, "denied", {}, None)
    monkeypatch.setattr(fm, "urlopen", denied)
    downloader = fm.Downloader(tmp_path, 0)
    with pytest.raises(fm.AccessDenied):
        downloader.fetch("matchDetails", {"matchId": 123}, tmp_path / "123.json.gz")
    with pytest.raises(fm.AccessDenied):
        downloader.fetch("matchDetails", {"matchId": 124}, tmp_path / "124.json.gz")
    assert len(calls) == 1
    assert fm.load_json(tmp_path / "access-denied.json")["http_status"] == status


def test_export_handles_success_error_and_pending(tmp_path):
    first, second, third = fixture(), dict(fixture(), fotmob_match_id="124"), dict(fixture(), fotmob_match_id="125")
    manifest = {"start": "2024-01-01", "end": "2026-10-03", "complete": True, "errors": [],
                "fixtures": [first, second, third]}
    rows = {"124": dict(second, download_status="error", error="HTTP 404"),
            "123": fm.normalize_match(first, payload(), "2026-10-03T12:00:00Z")}
    summary = fm.export(tmp_path, manifest, rows)
    assert not summary["download_complete"]
    assert summary["coverage"][0] == {"league_id": "gb.premier_league", "matches": 3,
                                      "with_xg": 1, "missing_xg": 0, "error": 1, "pending": 1}
    assert len(summary["coverage"]) == 23


def test_resume_uses_original_capture_time_without_network(monkeypatch, tmp_path):
    import gzip
    import json
    cache = tmp_path / "123.json.gz"
    with gzip.open(cache, "wt", encoding="utf-8") as handle:
        json.dump(payload(), handle)
    fm.save_json(cache.with_suffix(".gz.meta.json"), {"captured_at": "2026-10-01T12:00:00Z"})
    def unexpected(*args, **kwargs):
        raise AssertionError("No debería acceder a la red")
    monkeypatch.setattr(fm, "urlopen", unexpected)
    data, captured = fm.Downloader(tmp_path, 0).fetch("matchDetails", {"matchId": 123}, cache)
    assert data["general"]["matchId"] == "123"
    assert captured == "2026-10-01T12:00:00Z"
