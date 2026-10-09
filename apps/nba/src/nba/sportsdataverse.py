"""Pinned NBA box-score archives joined to a separate dated team reference."""
from collections import Counter
from datetime import UTC, datetime
import gzip
import hashlib
import json
from pathlib import Path
import re

import pyarrow.parquet as pq

from .audit import canonical, digest, write_json
from .ingest import game_id, load_manifest, normalize

SOURCE = "sportsdataverse/sportsdataverse-data"
ADAPTER_VERSION = "sportsdataverse-box-v2"


def load_release(path, years):
    path = Path(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (manifest.get("source") != SOURCE
            or manifest.get("tag") != "nba_stats_player_boxscores"
            or not isinstance(manifest.get("release_id"), int)):
        raise ValueError("unsupported box-score release")
    files = {}
    for entry in manifest["files"]:
        match = re.fullmatch(r"player_boxscores_(\d{4})\.parquet", entry["name"])
        if not match:
            raise ValueError("invalid release member")
        year = int(match[1])
        if year in files:
            raise ValueError("duplicate release year")
        file = path.parent / entry["name"]
        if (file.stat().st_size != entry["bytes"]
                or digest(file) != entry["sha256"]):
            raise ValueError("release raw integrity mismatch")
        received = datetime.fromisoformat(entry["first_received_at_utc"])
        if received.tzinfo is None:
            raise ValueError("receipt must have timezone")
        files[year] = file
    selected = sorted(set(years))
    if not selected or any(y not in files for y in selected):
        raise ValueError("selected release years missing")
    return manifest, {y: files[y] for y in selected}


def adapt_rows(rows, ending_year, team_keys=None):
    """Do not repair durations or IDs. Invalid rows quarantine their game."""
    adapted, issues = [], Counter()
    mapping = {"teamId": "team_id", "personId": "person_id",
               "firstName": "first_name", "familyName": "family_name",
               "minutes": "minutes", "comment": "comment",
               "points": "points", "reboundsTotal": "rebounds_total",
               "assists": "assists"}
    for row in rows:
        gid = str(row.get("game_id", ""))
        try:
            game_id(gid)
            if (gid[3:5] != str(ending_year - 1)[-2:]
                    or row["season"] != ending_year
                    or str(row["season_type_id"]) != str(int(gid[:3]))):
                raise ValueError("season/type mismatch")
            converted = {target: row[source] for target, source in mapping.items()}
            converted["gameId"] = gid
            if team_keys is not None and (gid, converted["teamId"]) not in team_keys:
                raise ValueError("player has no matching dated team reference")
            if not isinstance(converted["firstName"], str) or not isinstance(converted["familyName"], str):
                raise ValueError("missing player name")
            adapted.append(converted)
        except (KeyError, ValueError, TypeError):
            issues["invalid_release_row"] += 1
            # Passing the incomplete row through the strict reconciler ensures
            # even an invalid DNP row cannot silently disappear from a game.
            adapted.append({"gameId": gid})
    return adapted, dict(issues)


def import_release(release_path, team_manifest_path, output_root, years):
    manifest, files = load_release(release_path, years)
    team_manifest, reference_files = load_manifest(team_manifest_path)
    teams, players, adapter_issues = [], [], Counter()
    for year, file in files.items():
        reference_name = f"gamelog_{year}.parquet"
        if reference_name not in reference_files:
            raise ValueError(f"dated team reference missing for {year}")
        reference_rows = pq.read_table(reference_files[reference_name]).to_pylist()
        expected_season = f"{year-1}-{str(year)[-2:]}"
        if any(r["season_year"] != expected_season for r in reference_rows):
            raise ValueError("team reference season mismatch")
        teams.extend(reference_rows)
        team_keys = {(r["game_id"], r["team_id"]) for r in reference_rows}
        adapted, issues = adapt_rows(pq.read_table(file).to_pylist(), year, team_keys)
        players.extend(adapted)
        adapter_issues.update(issues)
    rows, report = normalize(teams, players)
    inputs = dict(adapter_version=ADAPTER_VERSION, years=sorted(files),
                  release_manifest_sha256=digest(release_path),
                  team_manifest_sha256=digest(team_manifest_path))
    key = hashlib.sha256(canonical(inputs).encode()).hexdigest()
    folder = Path(output_root) / key
    dataset, coverage = folder / "player_games.jsonl.gz", folder / "coverage.json"
    if folder.exists():
        previous = json.loads(coverage.read_text(encoding="utf-8"))
        if previous["inputs"] != inputs or digest(dataset) != previous["dataset_sha256"]:
            raise ValueError("normalized snapshot integrity mismatch")
        return previous
    folder.mkdir(parents=True)
    with dataset.open("wb") as file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=file, mtime=0) as stream:
            for row in rows:
                row["id_namespace"] = "nba"
                stream.write((canonical(row) + "\n").encode())
    report.update(source=SOURCE, release_id=manifest["release_id"],
                  team_source=team_manifest["source"], team_commit=team_manifest["commit"],
                  inputs=inputs, adapter_issues=dict(adapter_issues),
                  dataset_path=dataset.as_posix(), coverage_path=coverage.as_posix(),
                  dataset_sha256=digest(dataset), imported_at_utc=datetime.now(UTC).isoformat(),
                  original_pregame_availability_known=False,
                  mode="retrospective_archive", previous_dataset_replaced=False)
    write_json(coverage, report)
    return report
