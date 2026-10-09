import json
from pathlib import Path

import httpx
import pytest

from nba.current import capture_rosters, parse_roster


def roster(team="1", year=2027):
    return dict(season=dict(year=year, type=1), team=dict(id=team),
                timestamp="2026-10-05T19:00:00Z",
                athletes=[dict(id=str(100 + int(team)), displayName="Player " + team,
                               status=dict(name="Active"), injuries=[])])


def transport(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr("nba.current.httpx.Client",
                        lambda **kw: original(transport=httpx.MockTransport(handler), **kw))


def test_roster_is_espn_membership_not_medical_availability():
    rows = parse_roster(roster(), "1", 2027, "2026-10-05T19:01:00+00:00")
    assert rows[0]["player_id"] == "espn:101"
    assert rows[0]["team_id"] == "espn:1"
    assert rows[0]["nba_player_id"] is None and rows[0]["pregame_availability"] is None
    assert rows[0]["first_received_at_utc"] > rows[0]["provider_timestamp"]


@pytest.mark.parametrize("payload,received", [
    (roster(year=2026), "2026-10-05T19:01:00+00:00"),
    (roster(team="2"), "2026-10-05T19:01:00+00:00"),
    (roster(), "2026-10-05T19:01:00"),
    ({**roster(), "athletes": roster()["athletes"] * 2}, "2026-10-05T19:01:00+00:00")])
def test_stale_wrong_or_ambiguous_roster_rejected(payload, received):
    with pytest.raises(ValueError):
        parse_roster(payload, "1", 2027, received)


@pytest.mark.parametrize("status", [401, 403, 429])
def test_capture_denial_preserves_receipt_and_never_retries(tmp_path, monkeypatch, status):
    calls = []
    def handle(request):
        calls.append(str(request.url))
        return httpx.Response(status)
    transport(monkeypatch, handle)
    with pytest.raises(httpx.HTTPStatusError):
        capture_rosters(tmp_path, 2027, delay=0)
    assert len(calls) == 1
    manifest = json.loads(next(tmp_path.glob("*/manifest.json")).read_text())
    assert manifest["status"] == "partial" and manifest["errors"]


def test_current_capture_quarantines_cross_team_membership(tmp_path, monkeypatch):
    def handle(request):
        if request.url.path.endswith("/teams"):
            return httpx.Response(200, json=dict(sports=[dict(leagues=[dict(slug="nba",
                season=dict(year=2027), teams=[dict(team=dict(id=str(i))) for i in range(1, 31)])])]))
        tid = request.url.path.split("/")[-2]
        body = roster(team=tid)
        if tid == "2":
            body["athletes"][0]["id"] = "101"
        return httpx.Response(200, json=body)
    transport(monkeypatch, handle)
    report = capture_rosters(tmp_path, 2027, delay=0)
    assert report["teams_schema_verified"] == 30 and report["rows"] == 30
    assert report["duplicate_memberships"] == ["espn:101"]
    assert not report["complete_source_snapshot"] and not report["actionable"]
    rows = json.loads(Path(report["rosters_path"]).read_text())
    assert sum(r["membership_conflict"] for r in rows) == 2
