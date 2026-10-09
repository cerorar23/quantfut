"""Finite free-statistics recovery; original archives and gates stay unchanged."""
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import time

import httpx

from .audit import canonical, digest, write_json
from .ingest import game_id, integer, minutes, normalize, load_manifest, read_dataset
from .sportsdataverse import adapt_rows, load_release

VERSION = "free-backfill-v1"
ENDPOINTS = {
    "boxscore": "https://stats.nba.com/stats/boxscoretraditionalv3",
    "rotation": "https://stats.nba.com/stats/gamerotation",
}


def build_inventory(release_path, team_path, base_report_path, years, output):
    import pyarrow.parquet as pq

    output = Path(output)
    if output.exists():
        raise ValueError("preserve previous inventory; choose a new output")
    base = json.loads(Path(base_report_path).read_text(encoding="utf-8"))
    if digest(base["dataset_path"]) != base["dataset_sha256"]:
        raise ValueError("base dataset integrity mismatch")
    accepted = read_dataset(base["dataset_path"])
    accepted_ids = {r["game_id"] for r in accepted}
    _, releases = load_release(release_path, years)
    _, team_files = load_manifest(team_path)
    pending = []
    for year in sorted(releases):
        teams = pq.read_table(team_files[f"gamelog_{year}.parquet"]).to_pylist()
        players = pq.read_table(releases[year]).to_pylist()
        pending.extend(pending_games(teams, players, accepted_ids, year))
    report = dict(version=VERSION, pending_games=pending,
        summary=dict(pending_games=len(pending),
            pending_by_prefix=dict(Counter(r["game_id"][:3] for r in pending)),
            regular_invalid_references=sum(r["reference_invalid"] for r in pending if r["game_id"].startswith("002")),
            regular_with_invalid_minutes=sum(bool(r["invalid_minutes"]) for r in pending if r["game_id"].startswith("002"))),
        source_hashes={str(p): digest(p) for p in (release_path, team_path, base_report_path)},
        base_dataset_sha256=base["dataset_sha256"], created_at_utc=datetime.now(UTC).isoformat(),
        source_coverage="known team references only; earlier playoff calendars not complete",
        previous_dataset_replaced=False, odds_api_credits=0, actionable=False)
    write_json(output, report)
    return report


def pending_games(team_rows, release_rows, accepted_ids, ending_year):
    """Diagnose every known game without repairing source values."""
    teams, players = defaultdict(list), defaultdict(list)
    for row in team_rows:
        gid = game_id(row["game_id"])
        if gid[3:5] != str(ending_year - 1)[-2:]:
            raise ValueError("reference season mismatch")
        teams[gid].append(row)
    for row in release_rows:
        players[str(row.get("game_id", ""))].append(row)
    result = []
    for gid, refs in sorted(teams.items()):
        if gid in accepted_ids or gid.startswith("003"):
            continue
        raw = players[gid]
        keys = {(gid, r["team_id"]) for r in refs}
        adapted, adapter = adapt_rows(raw, ending_year, keys)
        rows, audit = normalize(refs, adapted)
        if rows:
            raise ValueError("accepted census and strict replay disagree")
        invalid_minutes = []
        for row in raw:
            try:
                minutes(row.get("minutes"), row.get("comment"))
            except (ValueError, TypeError):
                invalid_minutes.append(dict(player_id=row.get("person_id"),
                    minutes_raw=row.get("minutes"), comment_raw=row.get("comment")))
        reference_invalid = bool(audit["issues"].get("invalid_team_row")
                                 or audit["issues"].get("game_without_two_teams")
                                 or audit["issues"].get("conflicting_game_date")
                                 or audit["issues"].get("conflicting_team_duplicate"))
        result.append(dict(game_id=gid, season=f"{ending_year-1}-{str(ending_year)[-2:]}",
            date=refs[0]["game_date"], teams=[dict(team_id=r["team_id"],
                name=r.get("team_name"), matchup=r.get("matchup")) for r in refs],
            reference_invalid=reference_invalid, raw_player_rows=len(raw),
            adapter_issues=adapter, reconciliation_issues=audit["issues"],
            invalid_minutes=invalid_minutes, needs_new_reference=reference_invalid,
            reason="raw_boxscore_absent" if not raw else "strict_validation_failed"))
    return result


def capture_batch(root, ids, kind, delay=1, transport=None):
    """At most 20 requests; stop on any failure, resume verified successes only."""
    if kind not in ENDPOINTS or not ids or len(ids) > 20 or len(ids) != len(set(ids)):
        raise ValueError("one endpoint and 1-20 distinct game IDs required")
    for gid in ids:
        game_id(gid)
    config = dict(version=VERSION, kind=kind, game_ids=list(ids))
    folder = Path(root) / hashlib.sha256(canonical(config).encode()).hexdigest()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "manifest.json"
    meta = json.loads(path.read_text(encoding="utf-8")) if path.exists() else dict(
        source="NBA_official_stats", configuration=config, files=[], errors=[],
        status="partial", mode="retrospective_corrected_statistics", odds_api_credits=0,
        original_pregame_availability_known=False)
    if meta["configuration"] != config:
        raise ValueError("capture configuration mismatch")
    completed = set()
    for entry in meta["files"]:
        raw = folder / entry["name"]
        if raw.stat().st_size != entry["bytes"] or digest(raw) != entry["sha256"]:
            raise ValueError("capture raw integrity mismatch")
        if entry["http_status"] == 200:
            completed.add(entry["game_id"])
    if meta["status"] == "stopped_after_failure":
        return path
    write_json(path, meta)
    with httpx.Client(timeout=httpx.Timeout(12, connect=8), transport=transport,
                      headers={"User-Agent": "QuantNBAResearch/0.1", "Referer": "https://www.nba.com/"}) as client:
        for gid in ids:
            if gid in completed:
                continue
            params = {"GameID": gid}
            params.update({"LeagueID": "00"} if kind == "rotation" else dict(
                StartPeriod=0, EndPeriod=0, StartRange=0, EndRange=0, RangeType=0))
            try:
                with client.stream("GET", ENDPOINTS[kind], params=params) as response:
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 8_000_000:
                            raise ValueError("response exceeds 8MB capture cap")
                name = f"{kind}_{gid}.json"
                raw = folder / name
                if raw.exists():
                    raise ValueError("refuse to overwrite untracked raw file")
                raw.write_bytes(body)
                meta["files"].append(dict(name=name, game_id=gid, url=ENDPOINTS[kind],
                    parameters=params, bytes=len(body), sha256=digest(raw),
                    http_status=response.status_code, server_date=response.headers.get("Date"),
                    first_received_at_utc=datetime.now(UTC).isoformat()))
                if response.status_code != 200:
                    raise ValueError(f"provider HTTP {response.status_code}")
                payload = json.loads(body)
                if not isinstance(payload, dict):
                    raise ValueError("unsupported provider envelope")
                completed.add(gid)
            except (httpx.HTTPError, ValueError) as exc:
                meta["errors"].append(dict(game_id=gid, kind=type(exc).__name__,
                    reason=str(exc), attempted_at_utc=datetime.now(UTC).isoformat()))
                meta["status"] = "stopped_after_failure"
                write_json(path, meta)
                return path
            write_json(path, meta)
            if gid != ids[-1]:
                time.sleep(delay)
    meta["status"] = "received_not_validated"
    write_json(path, meta)
    return path


def audit_boxscore(payload, gid, references):
    """Compare official V3 nested payload with dated team rows, then reconcile."""
    game_id(gid)
    body = payload["boxScoreTraditional"]
    if body["gameId"] != gid or not references or any(r["game_id"] != gid for r in references):
        raise ValueError("boxscore identity mismatch")
    refs = {integer(r["team_id"]): r for r in references}
    if len(refs) != 2 or len(references) != 2:
        raise ValueError("exactly two dated team references required")
    rows, team_ids = [], set()
    for side in ("homeTeam", "awayTeam"):
        team = body[side]
        tid = integer(team["teamId"])
        if tid not in refs or tid in team_ids:
            raise ValueError("boxscore team mismatch")
        team_ids.add(tid)
        for field, target in (("points", "pts"), ("reboundsTotal", "reb"), ("assists", "ast")):
            if integer(team["statistics"][field]) != refs[tid][target]:
                raise ValueError("provider/reference team statistics disagree")
        for player in team["players"]:
            s = player["statistics"]
            rows.append(dict(gameId=gid, teamId=tid, personId=player["personId"],
                firstName=player["firstName"], familyName=player["familyName"],
                comment=player.get("comment", ""), minutes=s.get("minutes"),
                points=s["points"], reboundsTotal=s["reboundsTotal"], assists=s["assists"]))
    accepted, report = normalize(references, rows)
    if not accepted or report["quarantined_games"] or report["issues"]:
        raise ValueError("replacement boxscore failed existing strict reconciliation")
    for row in accepted:
        row["id_namespace"] = "nba"
    return accepted


def audit_stints(payload, gid, box_rows):
    """Infer clock units only if one scale reconciles; reject lineup gaps."""
    game_id(gid)
    if not box_rows or any(r["game_id"] != gid for r in box_rows):
        raise ValueError("matching boxscore required")
    box = {(r["team_id"], r["player_id"]): r for r in box_rows}
    if len(box) != len(box_rows) or len({k[0] for k in box}) != 2:
        raise ValueError("ambiguous boxscore identities")
    tables = payload["resultSets"]
    if {t["name"] for t in tables} != {"AwayTeam", "HomeTeam"} or len(tables) != 2:
        raise ValueError("both rotation teams required")
    records = []
    for table in tables:
        for values in table["rowSet"]:
            if len(values) != len(table["headers"]) or len(set(table["headers"])) != len(table["headers"]):
                raise ValueError("rotation schema mismatch")
            row = dict(zip(table["headers"], values))
            key = integer(row["TEAM_ID"]), integer(row["PERSON_ID"])
            if key not in box or not box[key]["participated"]:
                raise ValueError("unknown/wrong-team/DNP rotation player")
            start, end = integer(row["IN_TIME_REAL"]), integer(row["OUT_TIME_REAL"])
            if start >= end:
                raise ValueError("invalid stint interval")
            records.append(dict(team_id=key[0], player_id=key[1], raw_start=start, raw_end=end))
    candidates = []
    for scale in (1, 0.1):
        totals, count = Counter(), Counter()
        for r in records:
            key = r["team_id"], r["player_id"]
            totals[key] += (r["raw_end"] - r["raw_start"]) * scale
            count[key] += 1
        if all(abs(totals[k] - (row["minutes"] or 0) * 60) <= count[k] for k, row in box.items()):
            candidates.append(scale)
    if len(candidates) != 1:
        raise ValueError("rotation units/minutes not uniquely reconciled")
    scale = candidates[0]
    output = []
    for tid in sorted({k[0] for k in box}):
        stints = [r for r in records if r["team_id"] == tid]
        duration = sum((r["minutes"] or 0) * 60 for r in box_rows if r["team_id"] == tid) / 5
        # Quantization is checked against a legal NBA game duration, never rescaled.
        legal = [2880 + 300 * n for n in range(7)]
        matches = [v for v in legal if abs(v - duration) <= 9]
        if len(matches) != 1:
            raise ValueError("invalid rotation game duration")
        duration = matches[0]
        bounds = sorted({0, duration} | {r[k] * scale for r in stints for k in ("raw_start", "raw_end")})
        if bounds[0] != 0 or bounds[-1] != duration:
            raise ValueError("stints exceed game boundaries")
        for start, end in zip(bounds, bounds[1:]):
            active = [r["player_id"] for r in stints if r["raw_start"] * scale <= start < r["raw_end"] * scale]
            if len(active) != 5 or len(set(active)) != 5:
                raise ValueError("rotation gap/overlap or non-five-player lineup")
            output.append(dict(game_id=gid, team_id=tid, start_seconds=start,
                               end_seconds=end, nba_player_ids=sorted(active)))
    return dict(game_id=gid, clock_seconds_per_unit=scale, raw_stints=records,
                chronological_lineups=output, historically_available_before_game=False)
