import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tarfile

import httpx
import pytest

from nba.audit import Ledger, digest
from nba.config import Settings
from nba.github_archive import audit_tar_csv, select_shufinskiy
from nba.ingest import game_id, minutes, normalize, load_manifest, capture
from nba.model import forecast, scores, contract_probabilities
from nba.evaluate import backtest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / "protocol.json").read_text())


def history(n=12):
    return [dict(game_id=f"002250{i:04d}", player_id=1, season="2025-26", season_type="regular",
                 date=f"2025-11-{i+1:02d}", participated=True, minutes=25.0, rebounds=5)
            for i in range(n)]


def box_rows():
    teams, players = [], []
    for tid in (1, 2):
        teams.append(dict(game_id="0022500001", team_id=tid, game_date="2025-10-21T00:00:00",
                          season_year="2025-26", min=48, pts=50, reb=25, ast=10))
        for pid in range(5):
            players.append(dict(gameId="0022500001", teamId=tid, personId=tid * 10 + pid,
                                firstName="A", familyName=str(pid), minutes="48:00", comment="",
                                points=10, reboundsTotal=5, assists=2))
    return teams, players


def test_isolation(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "football_db")
    monkeypatch.setenv("TG_BOT_TOKEN", "football_token")
    monkeypatch.setenv("NBA_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("NBA_TELEGRAM_ENABLED", raising=False)
    monkeypatch.delenv("NBA_ODDS_ENABLED", raising=False)
    settings = Settings.load()
    assert settings.data_dir == tmp_path
    assert not settings.telegram_enabled and not settings.odds_enabled
    for path in (ROOT / "src/nba").glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert all(a.name.split(".")[0] != "qf" for a in node.names)
            if isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith("qf")


@pytest.mark.parametrize("value", ["225000001", "bad", "0092500001"])
def test_game_id_rejects(value):
    with pytest.raises(ValueError):
        game_id(value)


def test_dnp_is_not_zero_minutes():
    assert minutes("", "DNP - Coach's Decision") is None
    assert minutes("00:12") == pytest.approx(0.2)
    assert minutes("00:00") == 0
    for value in ("", "10:70", "NaN", "90:00"):
        with pytest.raises(ValueError):
            minutes(value)


def test_reconciliation_and_duplicates():
    teams, players = box_rows()
    rows, report = normalize(teams, players + [players[0]])
    assert len(rows) == 10 and report["issues"]["exact_player_duplicate"] == 1
    broken = copy.deepcopy(players)
    broken[0]["points"] = 11
    rows, report = normalize(teams, broken)
    assert not rows and report["quarantined_games"] == ["0022500001"]


def test_conflict_quarantines_whole_game():
    teams, players = box_rows()
    conflict = {**players[0], "teamId": 2}
    rows, report = normalize(teams, players + [conflict])
    assert not rows and report["issues"]["conflicting_player_duplicate"] == 1


def test_bad_team_duration_stays_in_raw_coverage_denominator():
    teams, players = box_rows()
    teams[0]["min"] = 42.75
    rows, report = normalize(teams, players)
    assert not rows
    assert report["coverage"][0]["raw_team_reference_games"] == 1
    assert report["coverage"][0]["fraction_of_raw_team_games"] == 0
    assert report["quarantined_games"] == ["0022500001"]


def test_raw_tamper_detected(tmp_path):
    file = tmp_path / "gamelog_2026.parquet"
    file.write_bytes(b"old")
    manifest = dict(source="llimllib/nba_data", commit="a" * 40,
                    files=[dict(name="data/gamelog_2026.parquet", sha256=digest(file))])
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    load_manifest(path)
    file.write_bytes(b"new")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_manifest(path)


def test_denied_capture_stops_without_retry(tmp_path, monkeypatch):
    calls = []
    def request(req):
        calls.append(str(req.url))
        if "api.github.com" in str(req.url):
            return httpx.Response(200, json={"sha": "a" * 40})
        return httpx.Response(403)
    original = httpx.Client
    monkeypatch.setattr("nba.ingest.httpx.Client", lambda **kw: original(transport=httpx.MockTransport(request), **kw))
    with pytest.raises(httpx.HTTPStatusError):
        capture(tmp_path, [2026])
    assert len(calls) == 2
    assert json.loads((tmp_path / ("a" * 40) / "manifest.json").read_text())["files"][0]["error"] == "HTTPStatusError"


def test_pit_excludes_same_day_future_and_other_regimes():
    past = history()
    base = forecast(past, "2025-11-13", "2025-26", PROTOCOL)
    contaminated = past + [dict(past[0], date="2025-11-13", rebounds=1000),
                           dict(past[0], date="2025-11-14", rebounds=1000),
                           dict(past[0], season_type="preseason", rebounds=1000),
                           dict(past[0], season="2024-25", rebounds=1000)]
    assert forecast(contaminated, "2025-11-13", "2025-26", PROTOCOL) == base
    assert base["history_max_date"] < "2025-11-13"


def test_distribution_push_and_abstention():
    result = forecast(history(), "2025-11-13", "2025-26", PROTOCOL)
    pmf = result["pmf"]
    assert sum(pmf) == pytest.approx(1, abs=1e-8)
    contract = contract_probabilities(pmf, 5)
    assert sum(contract[k] for k in ("under", "push", "over")) == pytest.approx(1, abs=1e-8)
    assert contract["push"] > 0
    assert contract["void_probability"] is None
    assert contract_probabilities(pmf, 5.5)["push"] == 0
    assert forecast(history(2), "2025-11-13", "2025-26", PROTOCOL)["status"] == "abstain"
    assert scores([0, 0, 1, 0], 2)["crps"] == 0


@pytest.mark.parametrize("mins", [0, -1, 49, float("nan")])
def test_bad_scenario_minutes(mins):
    with pytest.raises(ValueError):
        forecast(history(), "2025-11-13", "2025-26", PROTOCOL, mins)


def test_replay_same_day_batching():
    rows = history(14)
    rows += [dict(rows[-1], game_id="0022500999", date="2025-11-14", rebounds=40)]
    report, predictions = backtest(rows, PROTOCOL)
    today = [r for r in predictions if r["date"] == "2025-11-14"]
    assert len(today) == 2
    assert today[0]["projected_minutes"] == today[1]["projected_minutes"]
    assert all(r["history_max_date"] < r["date"] for r in predictions)
    assert report["promoted"] is False


def test_ledger_sealed_and_tamper_detected(tmp_path):
    ledger = Ledger(tmp_path / "audit.sqlite")
    ledger.append("forecast", {"rebounds": 5})
    ledger.append("evaluation", {"research": True})
    assert ledger.verify()["events"] == 2
    with sqlite3.connect(ledger.path) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE events SET kind='changed'")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM events")
        db.execute("DROP TRIGGER events_no_update")
        db.execute("UPDATE events SET kind='changed' WHERE seq=1")
    with pytest.raises(ValueError, match="chain mismatch"):
        ledger.verify()


def test_archive_selection_uses_one_pbp_source():
    inventory = {"files": [dict(path="datasets/" + n) for n in
                 ["nbastats_2024.tar.xz", "nbastatsv3_2024.tar.xz", "shotdetail_2024.tar.xz", "wnba_nbastats_2024.tar.xz"]]}
    names = [f["path"] for f in select_shufinskiy(inventory, 2024, 2024)]
    assert len(names) == 2 and "datasets/nbastats_2024.tar.xz" not in names


def test_tar_rejects_traversal_without_extraction(tmp_path):
    path = tmp_path / "nbastats_2024.tar.xz"
    with tarfile.open(path, mode="w:xz") as tar:
        member = tarfile.TarInfo("../outside.csv")
        data = b"GAME_ID,EVENTNUM\n0022300001,1\n"
        member.size = len(data)
        tar.addfile(member, io.BytesIO(data))
    with pytest.raises(ValueError, match="members"):
        audit_tar_csv(path)
    assert not (tmp_path.parent / "outside.csv").exists()


def test_tar_csv_inventory_counts_games(tmp_path):
    path = tmp_path / "nbastatsv3_2024.tar.xz"
    with tarfile.open(path, mode="w:xz") as tar:
        member = tarfile.TarInfo("nbastatsv3_2024.csv")
        data = b"GAME_ID,EVENTNUM\n0022400001,1\n0022400001,2\n0022400002,1\n"
        member.size = len(data)
        tar.addfile(member, io.BytesIO(data))
    result = audit_tar_csv(path)
    assert result["rows"] == 3 and result["unique_games"] == 2
    assert not result["validated_against_schedule"]


def test_hoopr_audit_keeps_espn_namespace(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from nba.coverage import audit_hoopr
    folder = tmp_path / "nba/player_box/parquet"
    folder.mkdir(parents=True)
    file = folder / "player_box_2023.parquet"
    pq.write_table(pa.table({"game_id": [401468001, 401468001], "athlete_id": [1, 2],
                            "team_id": [5, 5], "game_date": ["2023-01-01", "2023-01-01"],
                            "season_type": [2, 2]}), file)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps(dict(source="sportsdataverse/hoopR-data", commit="a" * 40,
        files=[dict(name="nba/player_box/parquet/player_box_2023.parquet", sha256=digest(file))])))
    result = audit_hoopr(manifest)
    assert result["id_namespace"] == "espn" and result["files"][0]["unique_games"] == 1
    assert result["normalized_into_nba_dataset"] is False
