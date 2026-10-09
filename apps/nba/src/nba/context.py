"""Conservative identity joins and current context, never inferred availability."""
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
from pathlib import Path
import re
from uuid import uuid4
import unicodedata

import numpy as np
import pyarrow.parquet as pq
import httpx

from .audit import digest, write_json
from .ingest import read_dataset
from .startup import startup_forecast

VERSION = "current-context-v1"
TEAM_ALIASES = {"GS": "GSW", "NO": "NOP", "NY": "NYK", "SA": "SAS", "UTAH": "UTA", "WSH": "WAS"}


def utc(value):
    time = datetime.fromisoformat(value)
    if time.tzinfo is None:
        raise ValueError("timezone required")
    return time.astimezone(UTC)


def name_key(value):
    # Preserve suffixes and tokens; never edit distance or drop Jr/III.
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", "", value).split())


def nba_players(html):
    match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        raise ValueError("NBA page data absent")
    players = json.loads(match[1])["props"]["pageProps"]["players"]
    ids = [r["PERSON_ID"] for r in players]
    if not players or len(ids) != len(set(ids)):
        raise ValueError("NBA identities empty or duplicated")
    return players


def identity_join(espn, official, references, teams):
    by_name, births = defaultdict(list), defaultdict(set)
    for row in official:
        by_name[name_key(row["PLAYER_FIRST_NAME"] + " " + row["PLAYER_LAST_NAME"])].append(row)
    for row in references:
        if row.get("birth_date"):
            births[int(row["player_id"])].add(datetime.strptime(row["birth_date"], "%b %d, %Y").date().isoformat())
    team_map = {}
    for team in teams:
        abbr = TEAM_ALIASES.get(team["abbreviation"], team["abbreviation"])
        ids = {r["TEAM_ID"] for r in official if r["TEAM_ABBREVIATION"] == abbr}
        if len(ids) != 1:
            raise ValueError("ambiguous team abbreviation mapping")
        team_map["espn:" + str(team["id"])] = ids.pop()
    results = []
    for row in espn:
        candidates = by_name[name_key(row["name"])]
        result = dict(row, nba_player_id=None, identity_verified=False,
                      current_membership_verified=False, reason="no_unique_exact_name")
        if len(candidates) == 1:
            match = candidates[0]
            pid = int(match["PERSON_ID"])
            result.update(candidate_nba_player_id=pid, nba_team_id=match["TEAM_ID"])
            dob = row.get("date_of_birth")
            reference = births[pid]
            if dob and reference == {dob}:
                result.update(nba_player_id=pid, identity_verified=True, reason="exact_name_and_birth_date")
                membership = team_map.get(row["team_id"]) == match["TEAM_ID"] and not row.get("membership_conflict")
                result.update(current_membership_verified=membership)
                if not membership:
                    result["reason"] = "identity_verified_membership_conflict"
            else:
                result["reason"] = "birth_reference_missing_or_conflicting"
        results.append(result)
    counts = Counter(r["nba_player_id"] for r in results if r["identity_verified"])
    for row in results:
        if row["identity_verified"] and counts[row["nba_player_id"]] > 1:
            row.update(identity_verified=False, current_membership_verified=False,
                       nba_player_id=None, reason="duplicate_identity_crosswalk")
    return results


def availability_at(records, player_id, event_id, as_of, max_age_seconds=3600):
    """Only verified, game-specific records available at decision time count."""
    now = utc(as_of)
    accepted = []
    for row in records:
        if (row.get("player_id") != player_id or row.get("event_id") != event_id
                or row.get("source_verified") is not True):
            continue
        published, received = utc(row["published_at_utc"]), utc(row["first_received_at_utc"])
        if published <= received <= now and 0 <= (now - published).total_seconds() <= max_age_seconds:
            if row.get("status") in {"out", "available", "questionable", "doubtful", "probable"}:
                accepted.append(row)
    if not accepted:
        return dict(status="unknown", verified=False, reason="no_fresh_verified_game_record")
    latest = max(utc(r["published_at_utc"]) for r in accepted)
    rows = [r for r in accepted if utc(r["published_at_utc"]) == latest]
    if len({r["status"] for r in rows}) != 1:
        return dict(status="unknown", verified=False, reason="conflicting_designations")
    return dict(status=rows[0]["status"], verified=True, evidence=rows[0])


def coherent_minutes(priors, available, total=240.0, maximum=48.0):
    """Research scenario: Euclidean projection to bounded regulation minutes."""
    x = np.asarray(priors, dtype=float)
    if any(type(value) is not bool for value in available) or not 0 < maximum <= 48:
        raise ValueError("explicit boolean eligibility and regulation bound required")
    mask = np.asarray(available, dtype=bool)
    if x.ndim != 1 or mask.shape != x.shape or not np.isfinite(x).all() or (x < 0).any():
        raise ValueError("invalid minute priors")
    if not 0 < total <= mask.sum() * maximum:
        raise ValueError("insufficient eligible roster capacity")
    low, high = -float(x.max()) - maximum, float(total) + maximum
    for _ in range(100):
        shift = (low + high) / 2
        projected = np.where(mask, np.clip(x + shift, 0, maximum), 0)
        if projected.sum() < total:
            low = shift
        else:
            high = shift
    if abs(projected.sum() - total) > 1e-7:
        raise ValueError("minute conservation failed")
    return projected.tolist()


def verified_files(manifest_path):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    files = {}
    for row in manifest["files"]:
        name = row["name"]
        if Path(name).name != name or name in files:
            raise ValueError("unsafe capture filename")
        path = manifest_path.parent / name
        if digest(path) != row["sha256"]:
            raise ValueError("capture hash mismatch")
        utc(row.get("first_received_at_utc", row.get("received_at_utc")))
        files[name] = (path, row)
    return manifest, files


def build_context(roster_manifest, probe_manifest, dataset, protocol, as_of, profile_manifest=None):
    now = utc(as_of)
    roster_meta, roster_files = verified_files(roster_manifest)
    _, probes = verified_files(probe_manifest)
    if roster_meta["source"] != "ESPN_public_site_api" or roster_meta["status"] != "complete":
        raise ValueError("complete ESPN capture required")
    # Check every input's receipt, including identity reference; no historical backdating.
    for _, entry in list(roster_files.values()) + list(probes.values()):
        if utc(entry.get("first_received_at_utc", entry.get("received_at_utc"))) > now:
            raise ValueError("context uses future capture")
    official = nba_players(probes["nba_players.html"][0].read_text(encoding="utf-8"))
    references = pq.read_table(probes["rosters_2026.parquet"][0]).to_pylist()
    profile_files = {}
    if profile_manifest is not None:
        profile_meta, profile_files = verified_files(profile_manifest)
        if profile_meta.get("source") != "NBA_public_player_profiles":
            raise ValueError("unverified identity profile source")
        for name, (path, entry) in profile_files.items():
            if utc(entry["received_at_utc"]) > now:
                raise ValueError("future identity profile capture")
            match = re.fullmatch(r"nba_profile_(\d+)\.html", name)
            if not match or not entry["url"].startswith(f"https://www.nba.com/player/{match[1]}/"):
                raise ValueError("profile URL identity mismatch")
            data = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', path.read_text(encoding="utf-8"), re.S)
            info = json.loads(data[1])["props"]["pageProps"]["player"]["info"] if data else {}
            if info.get("PERSON_ID") != int(match[1]):
                raise ValueError("profile content identity mismatch")
            birth = datetime.fromisoformat(info["BIRTHDATE"]).strftime("%b %d, %Y")
            references.append(dict(player_id=info["PERSON_ID"], birth_date=birth))
    catalog = json.loads(roster_files["teams.json"][0].read_text())
    teams = [r["team"] for r in catalog["sports"][0]["leagues"][0]["teams"]]
    espn = []
    for tid in roster_meta["expected_team_ids"]:
        path, entry = roster_files[f"roster_{tid}.json"]
        payload = json.loads(path.read_text())
        if payload["season"]["year"] != roster_meta["season_year"] or str(payload["team"]["id"]) != tid:
            raise ValueError("roster identity mismatch")
        for player in payload["athletes"]:
            espn.append(dict(player_id="espn:" + str(player["id"]), team_id="espn:" + tid,
                             name=player["displayName"], date_of_birth=player.get("dateOfBirth", "")[:10] or None,
                             first_received_at_utc=entry["first_received_at_utc"]))
    crosswalk = identity_join(espn, official, references, teams)
    event_path = next(path for name, (path, _) in probes.items() if name.startswith("scoreboard_"))
    calendar = json.loads(event_path.read_text())
    events = []
    for event in calendar["events"]:
        if event["season"]["year"] != roster_meta["season_year"]:
            raise ValueError("calendar season mismatch")
        events.append(dict(event_id="espn:" + event["id"], tipoff_utc=utc(event["date"]).isoformat(),
                           season_type=event["season"]["slug"], name=event["name"],
                           state=event["status"]["type"]["state"]))
    history = defaultdict(list)
    for row in read_dataset(dataset):
        history[row["player_id"]].append(row)
    scenarios = []
    for row in crosswalk:
        if not row["identity_verified"] or not row["current_membership_verified"]:
            continue
        pid = row["nba_player_id"]
        forecast = startup_forecast(history[pid], now.date().isoformat(), "2026-27", protocol)
        forecast.pop("pmf", None)
        forecast.pop("baseline_pmf", None)
        past = [r for r in history[pid] if r["date"] < now.date().isoformat() and r["participated"]]
        last_team = max(past, key=lambda r: (r["date"], r["game_id"]))["team_id"] if past else None
        scenarios.append(dict(player_id=pid, name=row["name"], nba_team_id=row["nba_team_id"],
                              previous_observed_team_id=last_team, team_changed=(last_team != row["nba_team_id"]) if last_team else None,
                              availability="unknown", role_verified=False, forecast=forecast, actionable=False))
    counts = Counter(r["reason"] for r in crosswalk)
    return dict(version=VERSION, as_of=as_of, crosswalk=crosswalk, scenarios=scenarios, calendar=events,
                summary=dict(espn_players=len(espn), nba_page_players=len(official),
                             identities_verified=sum(r["identity_verified"] for r in crosswalk),
                             memberships_verified=sum(r["current_membership_verified"] for r in crosswalk),
                             unresolved_reasons=dict(counts),
                             conditional_scenarios=sum(s["forecast"]["status"] != "abstain" for s in scenarios),
                             team_changes=sum(s["team_changed"] is True for s in scenarios),
                             previous_team_unknown=sum(s["team_changed"] is None for s in scenarios),
                             nba_ids_without_verified_espn_join=sorted(set(r["PERSON_ID"] for r in official)
                                                                     - {r["nba_player_id"] for r in crosswalk if r["identity_verified"]}),
                             medical_availability_verified=0, actionable=0),
                input_hashes={str(p): digest(p) for p in (roster_manifest, probe_manifest, dataset,
                                                        *([profile_manifest] if profile_manifest else []))},
                limits=["Historical roster used for identity/DOB only, never current membership",
                        "Exact normalized name + unique DOB + current official ID required",
                        "Roster membership does not establish participation or role",
                        "ESPN injuries have no verified game-specific publication semantics",
                        "Regular-season prior scenarios do not predict preseason usage",
                        "No automatic injury redistribution, coach adjustment or model promotion"])


def capture_public_context(root, date, reference_manifest):
    """Finite public snapshot for repeatable prospective data collection."""
    day = datetime.strptime(date, "%Y-%m-%d").strftime("%Y%m%d")
    _, references = verified_files(reference_manifest)
    reference_path, reference_entry = references["rosters_2026.parquet"]
    folder = Path(root) / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:8])
    folder.mkdir(parents=True)
    manifest = dict(source="NBA_ESPN_public_context", files=[], errors=[], status="partial", date_requested=date)
    (folder / "rosters_2026.parquet").write_bytes(reference_path.read_bytes())
    manifest["files"].append(dict(reference_entry, inherited_from_manifest_sha256=digest(reference_manifest)))
    urls = [("nba_players.html", "https://www.nba.com/players"),
            (f"scoreboard_{day}.json", f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day}&limit=1000"),
            ("espn_injuries.json", "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries")]
    write_json(folder / "manifest.json", manifest)
    with httpx.Client(timeout=25, follow_redirects=True, headers={"User-Agent": "QuantNBAResearch/0.1"}) as client:
        for name, url in urls:
            try:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 5_000_000:
                            raise ValueError("public response cap exceeded")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                path = folder / name
                path.write_bytes(raw)
                manifest["files"].append(dict(name=name, url=url, bytes=size, sha256=digest(path),
                                             received_at_utc=datetime.now(UTC).isoformat(),
                                             published_at_if_available=None, server_date_header=response.headers.get("Date")))
            except Exception as exc:
                manifest["errors"].append(dict(name=name, kind=type(exc).__name__))
                write_json(folder / "manifest.json", manifest)
                raise
            write_json(folder / "manifest.json", manifest)
    manifest["status"] = "captured_not_medically_verified"
    write_json(folder / "manifest.json", manifest)
    return dict(manifest_path=str(folder / "manifest.json"), sha256=digest(folder / "manifest.json"), actionable=False)
