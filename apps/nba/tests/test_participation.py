import copy
import json

import pytest

from nba.audit import digest
from nba.ingest import normalize
from test_pipeline import box_rows


def case(tmp_path, change=None):
    teams, players = box_rows()
    teams[0]["reb"] += 1
    players.append(dict(gameId="0022500001", teamId=1, personId=16,
                        firstName="Sub", familyName="Second", minutes="00:00", comment="",
                        points=0, reboundsTotal=1, assists=0))
    headers = ["GAME_ID", "TEAM_ID", "PERSON_ID", "PLAYER_FIRST", "PLAYER_LAST",
               "IN_TIME_REAL", "OUT_TIME_REAL", "PLAYER_PTS"]
    tables = []
    for tid, name in ((1, "HomeTeam"), (2, "AwayTeam")):
        rows = [[p["gameId"], tid, p["personId"], p["firstName"], p["familyName"],
                 0, 28798 if p["personId"] == 10 else 28800, p["points"]]
                for p in players if p["teamId"] == tid and p["personId"] != 16]
        if tid == 1:
            rows.append(["0022500001", tid, 16, "Sub", "Second", 28798, 28800, 0])
        tables.append(dict(name=name, headers=headers, rowSet=rows))
    obj = dict(resource="gamerotation", parameters=dict(GameID="0022500001"), resultSets=tables)
    if change:
        change(obj, teams, players)
    path = tmp_path / "rotation.json"
    path.write_text(json.dumps(obj), encoding="utf-8")
    return teams, players, [dict(path=str(path), sha256=digest(path))]


def test_exact_tracking_resolves_zero_clock_and_preserves_original(tmp_path):
    teams, players, sources = case(tmp_path)
    before = copy.deepcopy(players)
    rows, report = normalize(teams, players, subsecond_sources=sources)
    assert len(rows) == 11 and not report["issues"] and not report["quarantined_games"]
    p = next(r for r in rows if r["player_id"] == 16)
    assert p["participated"] and p["minutes"] == pytest.approx(0.2 / 60)
    assert p["reported_minutes"] == 0 and p["minutes_raw"] == "00:00" and p["rebounds"] == 1
    assert p["subsecond_minutes_evidence"]["official_played_seconds"] == 0.2
    assert p["subsecond_minutes_evidence"]["source_sha256"] == sources[0]["sha256"]
    assert players == before


def test_zero_clock_statistics_without_source_still_quarantine_game(tmp_path):
    teams, players, _ = case(tmp_path)
    rows, report = normalize(teams, players)
    assert not rows and report["quarantined_games"] == ["0022500001"]


def test_dnp_cannot_be_overridden(tmp_path):
    teams, players, sources = case(tmp_path)
    players[-1]["comment"] = "DNP - Coach's Decision"
    with pytest.raises(ValueError, match="DNP/status"):
        normalize(teams, players, subsecond_sources=sources)


def test_source_hash_cannot_be_replaced_by_unverified_seconds(tmp_path):
    teams, players, sources = case(tmp_path)
    sources[0]["sha256"] = "a" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        normalize(teams, players, subsecond_sources=sources)


@pytest.mark.parametrize("failure", ["game", "team", "person", "name", "points", "overlap",
                                    "gap", "long_zero", "outside", "missing_player", "schema"])
def test_corrupt_tracking_rejected(tmp_path, failure):
    def change(obj, teams, players):
        rows = obj["resultSets"][0]["rowSet"]
        if failure == "game": rows[-1][0] = "0022500002"
        elif failure == "team": rows[-1][1] = 2
        elif failure == "person": rows[-1][2] = 999
        elif failure == "name": rows[-1][4] = "Different"
        elif failure == "points": rows[-1][7] = 1
        elif failure == "overlap": rows.append(copy.deepcopy(rows[0]))
        elif failure == "gap": rows[0][6] = 28797
        elif failure == "long_zero": rows[0][6] = rows[-1][5] = 28789
        elif failure == "outside": rows[-1][6] = 28801
        elif failure == "missing_player": rows.pop(0)
        elif failure == "schema": obj["resultSets"][0]["headers"].append("PERSON_ID")
    teams, players, sources = case(tmp_path, change)
    with pytest.raises(ValueError):
        normalize(teams, players, subsecond_sources=sources)


def test_positive_rebound_still_needs_team_reconciliation(tmp_path):
    teams, players, sources = case(tmp_path)
    players[-1]["reboundsTotal"] = 2
    rows, report = normalize(teams, players, subsecond_sources=sources)
    assert not rows and report["quarantined_games"] == ["0022500001"]


def test_duplicate_sources_rejected(tmp_path):
    teams, players, sources = case(tmp_path)
    with pytest.raises(ValueError, match="duplicate rotation source"):
        normalize(teams, players, subsecond_sources=sources + sources)
