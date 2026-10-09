import copy
import json

import httpx
import pytest

from nba.backfill import audit_boxscore, audit_stints, capture_batch, pending_games
from nba.ingest import normalize
from test_pipeline import box_rows


def v3_fixture():
    teams, players = box_rows()
    body = dict(gameId="0022500001")
    for side, team in zip(("homeTeam", "awayTeam"), teams):
        body[side] = dict(teamId=team["team_id"], statistics=dict(points=50, reboundsTotal=25, assists=10), players=[])
        for p in players:
            if p["teamId"] == team["team_id"]:
                body[side]["players"].append(dict(personId=p["personId"], firstName=p["firstName"],
                    familyName=p["familyName"], comment=p["comment"], statistics=dict(minutes=p["minutes"],
                    points=p["points"], reboundsTotal=p["reboundsTotal"], assists=p["assists"])))
    return dict(boxScoreTraditional=body), teams


def rotation_fixture(overtime=0):
    teams, players = box_rows()
    duration = 48 + 5 * overtime
    for t in teams:
        t["min"] = duration
    for p in players:
        p["minutes"] = f"{duration}:00"
    box, _ = normalize(teams, players)
    headers = ["TEAM_ID", "PERSON_ID", "IN_TIME_REAL", "OUT_TIME_REAL"]
    data = dict(resultSets=[])
    for name, tid in (("HomeTeam", 1), ("AwayTeam", 2)):
        data["resultSets"].append(dict(name=name, headers=headers,
            rowSet=[[tid, p["personId"], 0, duration * 600] for p in players if p["teamId"] == tid]))
    return data, box


def test_box_replacement_must_match_reference_and_conserve_all_stats():
    payload, refs = v3_fixture()
    result = audit_boxscore(payload, "0022500001", refs)
    assert len(result) == 10 and sum(r["points"] for r in result) == 100
    assert all(r["id_namespace"] == "nba" for r in result)
    bad = copy.deepcopy(payload)
    bad["boxScoreTraditional"]["homeTeam"]["players"][0]["statistics"]["reboundsTotal"] += 1
    with pytest.raises(ValueError, match="reconciliation"):
        audit_boxscore(bad, "0022500001", refs)


@pytest.mark.parametrize("failure", ["game", "team", "minutes", "team_points"])
def test_box_identity_bad_minutes_and_disagreement_rejected(failure):
    payload, refs = v3_fixture()
    body = payload["boxScoreTraditional"]
    if failure == "game": body["gameId"] = "0022500002"
    elif failure == "team": body["homeTeam"]["teamId"] = 3
    elif failure == "minutes": body["homeTeam"]["players"][0]["statistics"]["minutes"] = "47:60"
    else: body["homeTeam"]["statistics"]["points"] = 51
    with pytest.raises(ValueError): audit_boxscore(payload, "0022500001", refs)


@pytest.mark.parametrize("overtime", [0, 2])
def test_stints_clock_units_and_overtime(overtime):
    payload, box = rotation_fixture(overtime)
    result = audit_stints(payload, "0022500001", box)
    assert result["clock_seconds_per_unit"] == 0.1
    assert len(result["chronological_lineups"]) == 2
    assert result["chronological_lineups"][0]["end_seconds"] == (48 + 5 * overtime) * 60
    assert not result["historically_available_before_game"]


@pytest.mark.parametrize("failure", ["gap", "overlap", "unknown", "minutes", "missing_team"])
def test_stints_cannot_promote_invalid_intervals(failure):
    payload, box = rotation_fixture()
    row = payload["resultSets"][0]["rowSet"][0]
    if failure == "gap": row[2] = 1
    elif failure == "overlap": payload["resultSets"][0]["rowSet"].append(row.copy())
    elif failure == "unknown": row[1] = 999
    elif failure == "minutes": row[3] -= 100
    else: payload["resultSets"].pop()
    with pytest.raises(ValueError): audit_stints(payload, "0022500001", box)


def test_capture_denial_stops_and_resume_does_not_repeat(tmp_path):
    calls = []
    def response(request):
        calls.append(request)
        return httpx.Response(403, text="denied")
    transport = httpx.MockTransport(response)
    ids = ["0022500001", "0022500002"]
    path = capture_batch(tmp_path, ids, "boxscore", delay=0, transport=transport)
    meta = json.loads(path.read_text())
    assert meta["status"] == "stopped_after_failure" and len(calls) == 1
    assert meta["files"][0]["http_status"] == 403
    assert meta["odds_api_credits"] == 0 and "apiKey" not in str(calls[0].url)
    assert capture_batch(tmp_path, ids, "boxscore", transport=transport) == path
    assert len(calls) == 1
    (path.parent / meta["files"][0]["name"]).write_text("changed")
    with pytest.raises(ValueError): capture_batch(tmp_path, ids, "boxscore", transport=transport)


def test_capture_timeout_is_preserved_and_stops(tmp_path):
    def timeout(request): raise httpx.ReadTimeout("test timeout", request=request)
    path = capture_batch(tmp_path, ["0022500001"], "rotation", transport=httpx.MockTransport(timeout))
    meta = json.loads(path.read_text())
    assert not meta["files"] and meta["errors"][0]["kind"] == "ReadTimeout"


def test_successful_capture_is_reusable_without_requests(tmp_path):
    calls = []
    def response(request):
        calls.append(request)
        return httpx.Response(200, json={"resultSets": []})
    t = httpx.MockTransport(response)
    path = capture_batch(tmp_path, ["0022500001"], "rotation", transport=t)
    assert json.loads(path.read_text())["status"] == "received_not_validated"
    capture_batch(tmp_path, ["0022500001"], "rotation", transport=t)
    assert len(calls) == 1


def test_pending_keeps_invalid_source_value_and_does_not_repair():
    teams, players = box_rows()
    release = [{"game_id":p["gameId"], "season":2026, "season_type_id":"2", "team_id":p["teamId"],
        "person_id":p["personId"], "first_name":p["firstName"], "family_name":p["familyName"],
        "minutes":p["minutes"], "comment":p["comment"], "points":p["points"],
        "rebounds_total":p["reboundsTotal"], "assists":p["assists"]} for p in players]
    release[0]["minutes"] = "47:60"
    result = pending_games(teams, release, set(), 2026)
    assert result[0]["invalid_minutes"][0]["minutes_raw"] == "47:60"
    assert not result[0]["reference_invalid"] and release[0]["minutes"] == "47:60"


@pytest.mark.parametrize("kind,ids", [("odds", ["0022500001"]), ("rotation", []),
    ("rotation", ["0022500001"]*2), ("rotation", ["invalid"]),
    ("rotation", [f"002250{i:04d}" for i in range(21)])])
def test_capture_rejects_unbounded_wrong_or_duplicate_work(tmp_path, kind, ids):
    with pytest.raises(ValueError): capture_batch(tmp_path, ids, kind)
