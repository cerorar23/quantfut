import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from nba.audit import digest
from nba.ingest import read_dataset
from nba.sportsdataverse import adapt_rows, import_release, load_release
from test_pipeline import box_rows


def archives(tmp_path):
    teams, players = box_rows()
    team_file = tmp_path / "gamelog_2026.parquet"
    pq.write_table(pa.Table.from_pylist(teams), team_file)
    team_manifest = tmp_path / "teams.json"
    team_manifest.write_text(json.dumps(dict(source="llimllib/nba_data", commit="a" * 40,
        files=[dict(name=team_file.name, sha256=digest(team_file))])))
    mapping = {"gameId": "game_id", "teamId": "team_id", "personId": "person_id",
               "firstName": "first_name", "familyName": "family_name", "minutes": "minutes",
               "comment": "comment", "points": "points", "reboundsTotal": "rebounds_total",
               "assists": "assists"}
    release_rows = [{**{mapping[k]: v for k, v in row.items()}, "season": 2026,
                     "season_type_id": "2"} for row in players]
    release_file = tmp_path / "player_boxscores_2026.parquet"
    pq.write_table(pa.Table.from_pylist(release_rows), release_file)
    release_manifest = tmp_path / "release.json"
    release_manifest.write_text(json.dumps(dict(source="sportsdataverse/sportsdataverse-data",
        release_id=1, tag="nba_stats_player_boxscores", files=[dict(name=release_file.name,
        bytes=release_file.stat().st_size, sha256=digest(release_file),
        first_received_at_utc="2026-10-05T19:00:00+00:00")])))
    return release_manifest, team_manifest, release_rows


def test_import_joins_dates_and_preserves_snapshot(tmp_path):
    release, teams, _ = archives(tmp_path)
    output = tmp_path / "normalized"
    result = import_release(release, teams, output, [2026])
    rows = read_dataset(result["dataset_path"])
    assert len(rows) == 10 and all(r["id_namespace"] == "nba" for r in rows)
    assert all(r["date"] == "2025-10-21" for r in rows)
    assert not result["original_pregame_availability_known"]
    assert result["coverage"][0]["reconciled_games"] == 1
    assert import_release(release, teams, output, [2026]) == result
    separate = import_release(release, teams, tmp_path / "another_output", [2026])
    assert separate["dataset_sha256"] == result["dataset_sha256"]


def test_even_nonparticipant_with_foreign_team_is_quarantined(tmp_path):
    _, _, rows = archives(tmp_path)
    rows.append({**rows[0], "team_id": 999, "person_id": 999,
                 "minutes": "", "comment": "DNP - Coach's Decision",
                 "points": 0, "rebounds_total": 0, "assists": 0})
    adapted, issues = adapt_rows(rows, 2026, {("0022500001", 1), ("0022500001", 2)})
    from nba.ingest import normalize
    teams, _ = box_rows()
    accepted, report = normalize(teams, adapted)
    assert issues["invalid_release_row"] == 1 and not accepted
    assert report["quarantined_games"] == ["0022500001"]


@pytest.mark.parametrize("field,value", [("season", 2025), ("season_type_id", "4"),
                                          ("game_id", "225000001")])
def test_no_silent_season_or_type_or_id_repairs(tmp_path, field, value):
    _, _, rows = archives(tmp_path)
    rows[0][field] = value
    adapted, issues = adapt_rows(rows, 2026)
    assert issues["invalid_release_row"] == 1
    assert adapted[0] == {"gameId": str(rows[0]["game_id"])}


def test_bad_minutes_still_quarantine_whole_game(tmp_path):
    _, _, release_rows = archives(tmp_path)
    release_rows[0]["minutes"] = "47:60"
    adapted, _ = adapt_rows(release_rows, 2026)
    from nba.ingest import normalize
    teams, _ = box_rows()
    rows, report = normalize(teams, adapted)
    assert not rows and report["quarantined_games"] == ["0022500001"]


def test_release_hash_and_member_validation(tmp_path):
    release, _, _ = archives(tmp_path)
    original = json.loads(release.read_text())
    for altered in [dict(original, files=original["files"] * 2),
                    dict(original, files=[{**original["files"][0], "name": "../outside.parquet"}])]:
        release.write_text(json.dumps(altered))
        with pytest.raises(ValueError):
            load_release(release, [2026])
    release.write_text(json.dumps(original))
    (tmp_path / "player_boxscores_2026.parquet").write_bytes(b"altered")
    with pytest.raises(ValueError, match="integrity"):
        load_release(release, [2026])


def test_reference_season_mismatch_and_missing_year_abort(tmp_path):
    release, team_manifest, _ = archives(tmp_path)
    with pytest.raises(ValueError, match="years missing"):
        import_release(release, team_manifest, tmp_path / "output", [2025])
    rows, _ = box_rows()
    rows[0]["season_year"] = "2024-25"
    file = tmp_path / "gamelog_2026.parquet"
    pq.write_table(pa.Table.from_pylist(rows), file)
    manifest = json.loads(team_manifest.read_text())
    manifest["files"][0]["sha256"] = digest(file)
    team_manifest.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="reference season mismatch"):
        import_release(release, team_manifest, tmp_path / "output", [2026])


def test_normalized_tampering_not_replaced(tmp_path):
    release, teams, _ = archives(tmp_path)
    result = import_release(release, teams, tmp_path / "output", [2026])
    from pathlib import Path
    dataset = Path(result["dataset_path"])
    dataset.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="snapshot integrity"):
        import_release(release, teams, tmp_path / "output", [2026])
    assert dataset.read_bytes() == b"tampered"
