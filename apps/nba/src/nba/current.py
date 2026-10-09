"""Experimental public ESPN roster snapshots, separate from NBA identities."""
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import time
from uuid import uuid4

import httpx

from .audit import digest, write_json

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
VERSION = "espn-roster-v1"


def parse_roster(payload, expected_team_id, season_year, received_at):
    if (payload.get("season", {}).get("year") != season_year
            or str(payload.get("team", {}).get("id")) != expected_team_id):
        raise ValueError("roster team/season mismatch")
    if datetime.fromisoformat(received_at).tzinfo is None:
        raise ValueError("receipt must have timezone")
    athletes = payload.get("athletes")
    if not isinstance(athletes, list) or not athletes:
        raise ValueError("empty or unsupported roster")
    result, seen = [], set()
    for athlete in athletes:
        pid = str(athlete["id"])
        if not re.fullmatch(r"[1-9]\d*", pid) or pid in seen:
            raise ValueError("invalid or duplicate ESPN athlete")
        seen.add(pid)
        result.append(dict(id_namespace="espn", team_id="espn:" + expected_team_id,
                           player_id="espn:" + pid, name=athlete["displayName"],
                           season_year=season_year,
                           provider_season_type=payload["season"].get("type"),
                           first_received_at_utc=received_at,
                           provider_timestamp=payload.get("timestamp"),
                           roster_status=athlete.get("status"),
                           injury_designations_raw=athlete.get("injuries"),
                           pregame_availability=None, nba_player_id=None))
    return result


def capture_rosters(root, season_year, delay=0.25):
    """One finite capture, no retry after denial; persist raw before parsing."""
    if not isinstance(season_year, int) or not 2000 <= season_year <= 2100:
        raise ValueError("invalid season ending year")
    folder = Path(root) / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:8])
    folder.mkdir(parents=True)
    manifest_path = folder / "manifest.json"
    manifest = dict(source="ESPN_public_site_api", mode="prospective_received_snapshot",
                    parser_version=VERSION, season_year=season_year, files=[],
                    status="partial", errors=[])
    write_json(manifest_path, manifest)
    normalized, verified_teams = [], []
    with httpx.Client(timeout=25, follow_redirects=True,
                      headers={"User-Agent": "QuantNBAResearch/0.1"}) as client:
        def receive(name, url):
            try:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    body, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 5_000_000:
                            raise ValueError("roster response exceeds capture cap")
                        body.append(chunk)
                    raw = b"".join(body)
                    received = datetime.now(UTC).isoformat()
                    server_date = response.headers.get("Date")
                file = folder / name
                file.write_bytes(raw)
                entry = dict(name=name, url=url, bytes=len(raw), sha256=digest(file),
                             first_received_at_utc=received, server_date_header=server_date,
                             published_at_if_available=None, clock_offset_if_available=None,
                             feed_resolution="unknown", clock_precision="local UTC timestamp")
                manifest["files"].append(entry)
                write_json(manifest_path, manifest)
                return json.loads(raw), received
            except Exception as exc:
                manifest["errors"].append(dict(url=url, kind=type(exc).__name__))
                write_json(manifest_path, manifest)
                raise

        catalog, _ = receive("teams.json", BASE + "/teams?limit=1000")
        league = catalog["sports"][0]["leagues"][0]
        if league["slug"] != "nba" or league.get("season", {}).get("year") != season_year:
            raise ValueError("catalog league/season mismatch")
        tids = [str(r["team"]["id"]) for r in league["teams"]]
        if (len(tids) != 30 or len(set(tids)) != 30
                or any(not re.fullmatch(r"[1-9]\d*", tid) for tid in tids)):
            raise ValueError("expected 30 distinct NBA ESPN teams")
        manifest["expected_team_ids"] = tids
        write_json(manifest_path, manifest)
        for tid in tids:
            time.sleep(delay)
            payload, received = receive(f"roster_{tid}.json", BASE + f"/teams/{tid}/roster?season={season_year}")
            try:
                normalized.extend(parse_roster(payload, tid, season_year, received))
                verified_teams.append("espn:" + tid)
            except (KeyError, ValueError, TypeError) as exc:
                manifest["errors"].append(dict(team_id="espn:" + tid, kind=type(exc).__name__,
                                               reason=str(exc)))
                write_json(manifest_path, manifest)
    counts = Counter(r["player_id"] for r in normalized)
    conflicts = sorted(pid for pid, count in counts.items() if count > 1)
    for row in normalized:
        row["membership_conflict"] = row["player_id"] in conflicts
    complete = len(verified_teams) == 30 and not conflicts and not manifest["errors"]
    manifest["status"] = "complete" if complete else "partial_quarantined"
    write_json(manifest_path, manifest)
    write_json(folder / "rosters.json", normalized)
    report = dict(source=manifest["source"], parser_version=VERSION, season_year=season_year,
                  manifest_path=manifest_path.as_posix(), manifest_sha256=digest(manifest_path),
                  rosters_path=(folder / "rosters.json").as_posix(),
                  rosters_sha256=digest(folder / "rosters.json"),
                  teams_received=len(manifest["files"]) - 1, teams_schema_verified=len(verified_teams),
                  rows=len(normalized), unique_players=len(counts), duplicate_memberships=conflicts,
                  complete_source_snapshot=complete, errors=manifest["errors"],
                  first_received_range=[min(r["first_received_at_utc"] for r in normalized),
                                        max(r["first_received_at_utc"] for r in normalized)] if normalized else [],
                  usable_as_of="only at/after each row's first_received_at_utc",
                  nba_identity_crosswalk_verified=False, official_roster_verified=False,
                  pregame_availability_verified=False, actionable=False)
    write_json(folder / "coverage.json", report)
    return report
