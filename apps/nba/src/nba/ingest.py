"""Public archive capture and strict box-score reconciliation."""
from collections import Counter, defaultdict
from datetime import UTC, datetime
import gzip
import hashlib
import json
import re
import time
from pathlib import Path

import httpx
import pyarrow.parquet as pq

from .audit import canonical, digest, write_json

SOURCE = "llimllib/nba_data"
TYPES = {"001": "preseason", "002": "regular", "003": "all_star",
         "004": "playoffs", "005": "play_in", "006": "cup_final"}


def game_id(value):
    value = str(value)
    if not re.fullmatch(r"\d{10}", value) or value[:3] not in TYPES:
        raise ValueError("invalid game ID/type")
    return value


def minutes(value, comment=""):
    if value in (None, ""):
        if comment and str(comment).startswith(("DNP", "DND", "NWT", "Inactive")):
            return None
        raise ValueError("missing minutes without nonparticipation status")
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(value))
    if not match or int(match[2]) >= 60:
        raise ValueError("invalid minutes")
    result = int(match[1]) + int(match[2]) / 60
    if result > 78:
        raise ValueError("minutes out of range")
    return result


def capture(root, years):
    """One pinned public GitHub commit; no retry on denied access."""
    root = Path(root)
    with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": "QuantNBAResearch/0.1"}) as client:
        response = client.get(f"https://api.github.com/repos/{SOURCE}/commits/main")
        response.raise_for_status()
        commit = response.json()["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("invalid source commit")
        folder = root / commit
        folder.mkdir(parents=True, exist_ok=True)
        manifest_path = folder / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
            "source": SOURCE, "commit": commit, "mode": "retrospective_archive", "files": []}
        entries = {e["name"]: e for e in manifest["files"]}
        names = ["README.md", "data/metadata.json"] + [f"data/{p}_{y}.parquet" for y in years for p in ("gamelog", "playerlog")]
        for name in names:
            path = folder / Path(name).name
            previous = entries.get(name)
            if previous and path.exists() and "sha256" in previous:
                if digest(path) != previous["sha256"]:
                    raise ValueError("raw hash mismatch; refuse overwrite")
                continue
            if path.exists():
                raise ValueError("untracked raw file; receipt time cannot be recovered")
            url = f"https://raw.githubusercontent.com/{SOURCE}/{commit}/{name}"
            try:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 50_000_000:
                            raise ValueError("source exceeds research download cap")
                        chunks.append(chunk)
                raw = b"".join(chunks)
                temporary = path.with_suffix(path.suffix + ".tmp")
                temporary.write_bytes(raw)
                temporary.replace(path)
                entries[name] = dict(name=name, url=url, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                                     first_received_at_utc=datetime.now(UTC).isoformat(), path=path.as_posix())
            except Exception as exc:
                entries[name] = dict(name=name, url=url, error=type(exc).__name__)
                manifest["files"] = list(entries.values())
                write_json(manifest_path, manifest)
                raise
            manifest["files"] = list(entries.values())
            write_json(manifest_path, manifest)
            time.sleep(0.5)
    return manifest_path


def load_manifest(path):
    path = Path(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["source"] != SOURCE or not re.fullmatch(r"[0-9a-f]{40}", manifest["commit"]):
        raise ValueError("unsupported archive")
    files = {}
    for entry in manifest["files"]:
        if "sha256" not in entry:
            continue
        file = path.parent / Path(entry["name"]).name
        if digest(file) != entry["sha256"]:
            raise ValueError(f"raw hash mismatch: {file.name}")
        files[file.name] = file
    return manifest, files


def integer(value):
    if value is None or isinstance(value, bool) or int(value) != value or value < 0:
        raise ValueError("invalid count")
    return int(value)


def normalize(team_rows, player_rows, *, subsecond_sources=()):
    # An optional proof changes only source-verified zero clocks. Default
    # archive imports retain their existing behavior and quarantine rules.
    from .participation import subsecond_proofs
    proofs = subsecond_proofs(subsecond_sources, team_rows, player_rows)
    teams, bad_games, issues = {}, set(), Counter()
    raw_reference = defaultdict(set)
    for row in team_rows:
        gid = None
        try:
            gid = game_id(row["game_id"])
            raw_reference[(row["season_year"], TYPES[gid[:3]])].add(gid)
            key = gid, integer(row["team_id"])
            date = datetime.fromisoformat(row["game_date"]).date().isoformat()
            t = dict(game_id=gid, team_id=key[1], date=date, season=row["season_year"],
                     season_type=TYPES[gid[:3]], minutes=float(row["min"]),
                     points=integer(row["pts"]), rebounds=integer(row["reb"]), assists=integer(row["ast"]))
            if not 48 <= t["minutes"] <= 78:
                raise ValueError("invalid team duration")
            if key in teams and teams[key] != t:
                bad_games.add(gid)
                issues["conflicting_team_duplicate"] += 1
            teams[key] = t
        except (KeyError, ValueError, TypeError):
            issues["invalid_team_row"] += 1
            if gid is not None:
                bad_games.add(gid)
    game_teams = defaultdict(set)
    for gid, tid in teams:
        game_teams[gid].add(tid)
    for gid, tids in game_teams.items():
        if len(tids) != 2:
            bad_games.add(gid)
            issues["game_without_two_teams"] += 1
        elif len({teams[(gid, tid)]["date"] for tid in tids}) != 1:
            bad_games.add(gid)
            issues["conflicting_game_date"] += 1
    players, groups, raw_games = {}, defaultdict(list), set()
    for row in player_rows:
        gid = str(row.get("gameId", ""))
        raw_games.add(gid)
        try:
            gid = game_id(gid)
            tid, pid = integer(row["teamId"]), integer(row["personId"])
            if (gid, tid) not in teams:
                issues["player_without_team_log"] += 1
                continue
            t = teams[(gid, tid)]
            mins = minutes(row["minutes"], row.get("comment"))
            p = dict(game_id=gid, team_id=tid, player_id=pid, date=t["date"], season=t["season"],
                     season_type=t["season_type"], name=(row["firstName"] + " " + row["familyName"]).strip(),
                     minutes=mins, participated=mins is not None and mins > 0,
                     status=str(row.get("comment") or ""),
                     rebounds=integer(row["reboundsTotal"]), points=integer(row["points"]), assists=integer(row["assists"]))
            if (gid, pid) in proofs:
                proof = proofs[(gid, pid)]
                if mins != 0 or p["status"].strip():
                    raise ValueError("subsecond proof contradicts reported participation")
                mins = proof["official_played_seconds"] / 60
                p.update(minutes=mins, participated=True, reported_minutes=0.0,
                         minutes_raw=row["minutes"], subsecond_minutes_evidence=proof)
            if (mins is None or mins == 0) and any(p[s] > 0 for s in ("rebounds", "points", "assists")):
                raise ValueError("nonparticipant with statistics")
            key = gid, pid
            if key in players:
                if players[key] != p:
                    bad_games.add(gid)
                    issues["conflicting_player_duplicate"] += 1
                else:
                    issues["exact_player_duplicate"] += 1
                continue
            players[key] = p
        except (KeyError, ValueError, TypeError):
            issues["invalid_player_row"] += 1
            bad_games.add(gid)
    for p in players.values():
        groups[(p["game_id"], p["team_id"])].append(p)
    for gid in raw_games & game_teams.keys():
        for tid in game_teams[gid]:
            group = groups[(gid, tid)]
            t = teams[(gid, tid)]
            if (abs(sum(p["minutes"] or 0 for p in group) - 5 * t["minutes"]) > 0.15
                    or any(sum(p[s] for p in group) != t[s] for s in ("points", "rebounds", "assists"))):
                bad_games.add(gid)
                issues["failed_team_reconciliation"] += 1
    accepted = sorted((p for p in players.values() if p["game_id"] not in bad_games),
                      key=lambda p: (p["date"], p["game_id"], p["player_id"]))
    coverage = []
    for season, kind in sorted(raw_reference):
        reference = {t["game_id"] for t in teams.values() if (t["season"], t["season_type"]) == (season, kind)}
        rows = [p for p in accepted if (p["season"], p["season_type"]) == (season, kind)]
        usable = {p["game_id"] for p in rows}
        dates = sorted({p["date"] for p in rows})
        coverage.append(dict(season=season, season_type=kind, team_reference_games=len(reference),
                             raw_team_reference_games=len(raw_reference[(season, kind)]),
                             raw_player_games=len(reference & raw_games), reconciled_games=len(usable),
                             rows=len(rows), participants=sum(p["participated"] for p in rows),
                             first_date=dates[0] if dates else None, last_date=dates[-1] if dates else None,
                             fraction=len(usable) / len(reference) if reference else None,
                             fraction_of_raw_team_games=len(usable) / len(raw_reference[(season, kind)])))
    return accepted, dict(issues=dict(issues), quarantined_games=sorted(bad_games), coverage=coverage,
                         raw_player_rows=len(player_rows), accepted_rows=len(accepted),
                         unsupported_by_team_log_games=len(raw_games - game_teams.keys()))


def import_archive(manifest_path, output):
    manifest, files = load_manifest(manifest_path)
    teams, players = [], []
    for name, file in sorted(files.items()):
        if name.startswith("gamelog_"):
            teams.extend(pq.read_table(file).to_pylist())
        elif name.startswith("playerlog_"):
            players.extend(pq.read_table(file).to_pylist())
    rows, report = normalize(teams, players)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    dataset = output / "player_games.jsonl.gz"
    # Fixed gzip metadata enables reproducible content hashes.
    with dataset.open("wb") as file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=file, mtime=0) as stream:
            for row in rows:
                stream.write((canonical(row) + "\n").encode())
    report.update(source=SOURCE, source_commit=manifest["commit"], mode="retrospective_archive",
                  imported_at_utc=datetime.now(UTC).isoformat(), dataset_sha256=digest(dataset),
                  manifest_sha256=digest(manifest_path), original_pregame_availability_known=False)
    write_json(output / "coverage.json", report)
    return report


def read_dataset(path):
    with gzip.open(path, "rt", encoding="utf-8") as file:
        return [json.loads(line) for line in file]
