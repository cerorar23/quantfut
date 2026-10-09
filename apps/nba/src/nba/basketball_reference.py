"""Bounded daily-page recovery and strict NBA identity/statistic reconciliation."""
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import time
import unicodedata

import httpx
import pyarrow.parquet as pq

from .audit import canonical, digest, write_json
from .ingest import game_id, load_manifest, minutes, normalize, read_dataset
from .sportsdataverse import load_release

VERSION = "bref-daily-v2"
BASE = "https://www.basketball-reference.com"
TEAM_CODES = dict(zip(range(1610612737, 1610612767),
    ("ATL", "BOS", "CLE", "NOP", "CHI", "DAL", "DEN", "GSW", "HOU", "LAC",
     "LAL", "MIA", "MIL", "MIN", "BRK", "NYK", "ORL", "IND", "PHI", "PHO",
     "POR", "SAC", "SAS", "OKC", "TOR", "UTA", "MEM", "WAS", "DET", "CHO")))
ALLOWED_TYPES = {"002", "004", "005"}


def daily_url(day):
    d = date.fromisoformat(day)
    if not 2000 <= d.year <= datetime.now(UTC).year or d.isoformat() != day:
        raise ValueError("invalid historical day")
    return f"{BASE}/friv/dailyleaders.fcgi?month={d.month}&day={d.day}&year={d.year}"


def _clock(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("receipt requires timezone")
    return dt.astimezone(UTC)


class DailyTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.row = self.cell = None
        self.rows = []
        self.tables = 0
        self.in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "table" and attrs.get("id") == "stats":
            self.tables += 1
            self.active = True
        if not self.active:
            return
        if tag == "tr":
            self.row = {}
        if tag in ("td", "th") and self.row is not None:
            self.cell = dict(stat=attrs.get("data-stat"), text="", attrs=attrs, links=[])
        if tag == "a" and self.cell is not None:
            self.cell["links"].append(attrs.get("href"))

    def handle_data(self, text):
        if self.in_title:
            self.title += text
        if self.active and self.cell is not None:
            self.cell["text"] += text

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if not self.active:
            return
        if tag in ("td", "th") and self.cell is not None:
            if self.cell["stat"] in self.row:
                raise ValueError("duplicate table cell")
            self.cell["text"] = self.cell["text"].strip()
            self.row[self.cell["stat"]] = self.cell
            self.cell = None
        if tag == "tr" and self.row is not None:
            if self.row.get("player", {}).get("links"):
                self.rows.append(self.row)
            self.row = None
        if tag == "table":
            self.active = False


def parse_day(raw, day):
    """A successful HTTP code alone does not prove the requested game date."""
    daily_url(day)
    parser = DailyTable()
    parser.feed(raw.decode("utf-8"))
    d = date.fromisoformat(day)
    expected_title = f"NBA Daily Stats Leaders for {d.strftime('%B')} {d.day}, {d.year} | Basketball-Reference.com"
    if parser.title.strip() != expected_title or parser.tables != 1 or parser.active or not parser.rows:
        raise ValueError("wrong date or unsupported daily table")
    rows, seen = [], set()
    for row in parser.rows:
        name = row["player"]["text"]
        pid = row["player"]["attrs"].get("data-append-csv", "")
        if not name or not re.fullmatch(r"[a-z0-9]{5,16}", pid) or pid in seen:
            raise ValueError("invalid or duplicate Basketball Reference identity")
        if row["player"]["links"] != [f"/players/{pid[0]}/{pid}.html"]:
            raise ValueError("player link mismatch")
        seen.add(pid)
        team, opponent = row["team_id"]["text"], row["opp_id"]["text"]
        location = row["game_location"]["text"]
        if team not in TEAM_CODES.values() or opponent not in TEAM_CODES.values() or team == opponent or location not in ("", "@"):
            raise ValueError("unsupported team or venue")
        home = opponent if location == "@" else team
        link = f"/boxscores/{d.strftime('%Y%m%d')}0{home}.html"
        if row["game_result"]["links"] != [link]:
            raise ValueError("boxscore date/home link mismatch")
        mins = row["mp"]["text"]
        parsed_minutes = minutes(mins)
        csk = row["mp"]["attrs"].get("csk")
        if csk is not None and (not re.fullmatch(r"\d+", csk) or abs(int(csk) - parsed_minutes * 60) > 1e-6):
            raise ValueError("displayed minutes and seconds key disagree")
        stats = {}
        for source, target in (("pts", "points"), ("trb", "rebounds"), ("ast", "assists"), ("orb", "orb"), ("drb", "drb")):
            text = row[source]["text"]
            if not re.fullmatch(r"\d+", text):
                raise ValueError("missing or invalid statistics")
            stats[target] = int(text)
        if stats["rebounds"] != stats["orb"] + stats["drb"]:
            raise ValueError("rebound components disagree")
        if parsed_minutes == 0 and any(stats.values()):
            raise ValueError("zero displayed minutes with statistics")
        rows.append(dict(bref_id=pid, name=name, team_code=team, opponent_code=opponent,
            home_away="away" if location else "home", game_date=day, boxscore_link=link,
            minutes_raw=mins, points=stats["points"], rebounds=stats["rebounds"], assists=stats["assists"]))
    return rows


def _cached(root, day):
    folder = Path(root) / "days" / day
    entry = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
    file = folder / "page.html"
    if entry["date"] != day or entry["url"] != daily_url(day) or entry["bytes"] != file.stat().st_size or entry["sha256"] != digest(file):
        raise ValueError("cached daily page integrity mismatch")
    _clock(entry["first_received_at_utc"])
    if entry["http_status"] != 200:
        raise ValueError("cached provider denial; no automatic retry")
    parse_day(file.read_bytes(), day)
    return dict(entry, path=file.as_posix())


def seed_cache(root, manifest_path):
    """Reuse the already captured pilot with its original receipt, not today's clock."""
    path = Path(manifest_path)
    meta = json.loads(path.read_text(encoding="utf-8"))
    for entry in meta["files"]:
        match = re.fullmatch(r"bref_(\d{4})(\d{2})(\d{2})\.html", entry["name"])
        if not match:
            continue
        day = "-".join(match.groups())
        file = path.parent / entry["name"]
        if entry["url"] != daily_url(day) or entry["status"] != 200 or file.stat().st_size != entry["bytes"] or digest(file) != entry["sha256"]:
            raise ValueError("seed capture integrity mismatch")
        received = entry["received_at_utc"]
        _clock(received)
        parse_day(file.read_bytes(), day)
        folder = Path(root) / "days" / day
        if folder.exists():
            _cached(root, day)
            continue
        folder.mkdir(parents=True)
        shutil.copyfile(file, folder / "page.html")
        write_json(folder / "receipt.json", dict(source="basketball_reference", date=day,
            url=entry["url"], http_status=200, bytes=entry["bytes"], sha256=entry["sha256"],
            first_received_at_utc=received, seed_manifest_sha256=digest(path),
            published_at_if_available=None, original_pregame_availability_known=False))


def capture_days(root, days, delay=6, transport=None):
    if not days or len(days) > 20 or len(set(days)) != len(days) or delay < 6:
        raise ValueError("1-20 distinct dates and delay >=6 seconds required")
    for day in days:
        daily_url(day)
    root = Path(root)
    config = dict(version=VERSION, dates=sorted(days), minimum_delay_seconds=delay)
    folder = root / "batches" / hashlib.sha256(canonical(config).encode()).hexdigest()
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / "manifest.json"
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        for entry in previous["files"]:
            _cached(root, entry["date"])
        return manifest_path
    manifest = dict(configuration=config, files=[], errors=[], status="partial",
        odds_api_credits=0, original_pregame_availability_known=False)
    write_json(manifest_path, manifest)
    block = root / "provider_stop.json"
    pace = root / "last_request.json"
    with httpx.Client(timeout=httpx.Timeout(15, connect=8), transport=transport,
                      headers={"User-Agent": "QuantNBAResearch/0.1"}) as client:
        for day in sorted(days):
            daily_folder = root / "days" / day
            try:
                if daily_folder.exists():
                    manifest["files"].append(_cached(root, day))
                    write_json(manifest_path, manifest)
                    continue
                if block.exists():
                    raise ValueError("provider stop is recorded; no further requests")
                if pace.exists():
                    elapsed = (datetime.now(UTC) - _clock(json.loads(pace.read_text())["at_utc"])).total_seconds()
                    if elapsed < -1:
                        raise ValueError("local capture clock moved backwards")
                    time.sleep(max(0, delay - elapsed))
                write_json(pace, dict(at_utc=datetime.now(UTC).isoformat()))
                with client.stream("GET", daily_url(day)) as response:
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 2_000_000:
                            raise ValueError("daily page exceeds 2MB")
                daily_folder.mkdir(parents=True)
                file = daily_folder / "page.html"
                file.write_bytes(body)
                entry = dict(source="basketball_reference", date=day, url=daily_url(day),
                    bytes=len(body), sha256=digest(file), http_status=response.status_code,
                    first_received_at_utc=datetime.now(UTC).isoformat(),
                    published_at_if_available=None, original_pregame_availability_known=False)
                write_json(daily_folder / "receipt.json", entry)
                if response.status_code != 200:
                    raise ValueError(f"provider HTTP {response.status_code}")
                parse_day(bytes(body), day)
                manifest["files"].append(dict(entry, path=file.as_posix()))
                write_json(manifest_path, manifest)
            except (ValueError, KeyError, UnicodeError, httpx.HTTPError) as exc:
                error = dict(date=day, kind=type(exc).__name__, reason=str(exc), at_utc=datetime.now(UTC).isoformat())
                manifest["errors"].append(error)
                manifest["status"] = "stopped_after_failure"
                if not block.exists():
                    write_json(block, error)
                write_json(manifest_path, manifest)
                return manifest_path
    manifest["status"] = "received_date_verified"
    write_json(manifest_path, manifest)
    return manifest_path


def _name_key(name):
    return "".join(c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn")


def _name_variant(name):
    text = _name_key(name)
    suffix = re.search(r" (Jr\.?|Sr\.?|II|III|IV)$", text)
    generation = suffix[1].replace(".", "") if suffix else None
    base = text[:suffix.start()] if suffix else text
    # Only omitted generation labels and periods in initials, never nicknames,
    # token similarity, surname-only matching, or conflicting generations.
    return base.replace(".", ""), generation


def reconcile_game(refs, prior, daily, provenance):
    """Ignore invalid prior minutes; identities and P/R/A still need agreement."""
    if len(refs) != 2 or len({r["team_id"] for r in refs}) != 2:
        raise ValueError("two distinct team references required")
    gid = game_id(refs[0]["game_id"])
    if gid[:3] not in ALLOWED_TYPES or any(r["game_id"] != gid for r in refs):
        raise ValueError("unsupported game/type")
    dates = {datetime.fromisoformat(r["game_date"]).date().isoformat() for r in refs}
    if len(dates) != 1:
        raise ValueError("reference dates disagree")
    day = dates.pop()
    identities = {}
    for row in prior:
        key = row["team_id"], _name_key(row["first_name"] + " " + row["family_name"])
        if row["game_id"] != gid or key in identities or row["person_id"] <= 0:
            raise ValueError("ambiguous same-game NBA identity")
        identities[key] = row
    venues = {}
    codes = {r["team_id"]: TEAM_CODES[r["team_id"]] for r in refs}
    for ref in refs:
        if ref["season_year"] != f"20{gid[3:5]}-{(int(gid[3:5])+1):02d}":
            raise ValueError("reference season mismatch")
        text = ref.get("matchup", "")
        if " vs. " in text:
            venue = "home"
        elif " @ " in text:
            venue = "away"
        else:
            raise ValueError("reference venue unknown")
        venues[ref["team_id"]] = venue
    if set(venues.values()) != {"home", "away"}:
        raise ValueError("reference venues disagree")
    home = next(t for t, v in venues.items() if v == "home")
    link = f"/boxscores/{day.replace('-', '')}0{codes[home]}.html"
    selected = [r for r in daily if r["boxscore_link"] == link]
    if not selected:
        raise ValueError("game absent from daily page")
    adapted, mappings, seen = [], [], set()
    for row in selected:
        tids = [t for t, code in codes.items() if code == row["team_code"]]
        if len(tids) != 1:
            raise ValueError("unexpected team on boxscore")
        tid = tids[0]
        opponent = next(t for t in codes if t != tid)
        if row["game_date"] != day or row["home_away"] != venues[tid] or row["opponent_code"] != codes[opponent]:
            raise ValueError("date, opponent or venue mismatch")
        raw = identities.get((tid, _name_key(row["name"])))
        method = "unique exact accent-normalized name"
        if raw is None:
            base, generation = _name_variant(row["name"])
            candidates = []
            for (team, nba_name), candidate in identities.items():
                nba_base, nba_generation = _name_variant(nba_name)
                if team == tid and base == nba_base and (generation is None or nba_generation is None or generation == nba_generation):
                    candidates.append(candidate)
            if len(candidates) == 1:
                raw = candidates[0]
                method = "unique same-game name with omitted generation label or periods in initials"
        if raw is None or raw["person_id"] in seen:
            raise ValueError("unresolved or duplicate NBA player")
        seen.add(raw["person_id"])
        if (row["points"], row["rebounds"], row["assists"]) != (raw["points"], raw["rebounds_total"], raw["assists"]):
            raise ValueError("player P/R/A sources disagree")
        adapted.append(dict(gameId=gid, teamId=tid, personId=raw["person_id"], firstName=raw["first_name"],
            familyName=raw["family_name"], minutes=row["minutes_raw"], comment="", points=row["points"],
            reboundsTotal=row["rebounds"], assists=row["assists"]))
        mappings.append(dict(nba_id=raw["person_id"], bref_id=row["bref_id"], nba_original_minutes=raw["minutes"],
            bref_minutes=row["minutes_raw"], nba_name=raw["first_name"] + " " + raw["family_name"], bref_name=row["name"],
            identity_method=method + "; game/date/team/locality and P/R/A corroborated"))
    # Missing known participants cannot be silently replaced by an incomplete daily table.
    for raw in prior:
        status = str(raw.get("comment") or "")
        if raw["person_id"] not in seen and (raw.get("minutes") not in (None, "", "0:00", "00:00")
                or any(raw[s] > 0 for s in ("points", "rebounds_total", "assists"))
                or not status.startswith(("DNP", "DND", "NWT", "Inactive"))):
            raise ValueError("known participant missing from page")
    accepted, audit = normalize(refs, adapted)
    if not accepted or audit["issues"] or audit["quarantined_games"]:
        raise ValueError("replacement failed existing strict team reconciliation")
    by_id = {m["nba_id"]: m for m in mappings}
    for row in accepted:
        row.update(id_namespace="nba", provenance=dict(provenance,
            source="basketball_reference", boxscore_link=link, **by_id[row["player_id"]]),
            original_pregame_availability_known=False)
    return accepted, mappings


def recover_dataset(cache_root, inventory_path, release_path, team_path, base_report_path, output):
    """New immutable version; never replace accepted rows or infer missing DNPs."""
    output = Path(output)
    if output.exists():
        raise ValueError("choose a new output directory; preserve prior versions")
    inv = json.loads(Path(inventory_path).read_text())
    base = json.loads(Path(base_report_path).read_text())
    if digest(base["dataset_path"]) != base["dataset_sha256"] or inv["base_dataset_sha256"] != base["dataset_sha256"]:
        raise ValueError("base dataset and inventory hashes disagree")
    for path in (release_path, team_path, base_report_path):
        if inv["source_hashes"][str(path)] != digest(path):
            raise ValueError("inventory source hash mismatch")
    baseline = read_dataset(base["dataset_path"])
    accepted_ids = {r["game_id"] for r in baseline}
    pending = inv["pending_games"]
    years = sorted({int(g["season"][:4]) + 1 for g in pending if g["game_id"][:3] in ALLOWED_TYPES})
    _, release = load_release(release_path, years)
    _, team_files = load_manifest(team_path)
    references, prior = defaultdict(list), defaultdict(list)
    for year in years:
        for r in pq.read_table(team_files[f"gamelog_{year}.parquet"]).to_pylist():
            references[r["game_id"]].append(r)
        for r in pq.read_table(release[year]).to_pylist():
            prior[str(r["game_id"])].append(r)
    pages, added, resolved, unresolved = {}, [], [], []
    for game in pending:
        gid, day = game["game_id"], game["date"][:10]
        if gid in accepted_ids:
            raise ValueError("pending census includes already accepted game")
        try:
            if gid[:3] not in ALLOWED_TYPES:
                raise ValueError("daily recovery does not certify preseason coverage")
            if day not in pages:
                entry = _cached(cache_root, day)
                parsed = parse_day(Path(entry["path"]).read_bytes(), day)
                pages[day] = entry, parsed
            entry, parsed = pages[day]
            prov = dict(url=entry["url"], page_sha256=entry["sha256"], first_received_at_utc=entry["first_received_at_utc"],
                nba_identity_manifest_sha256=digest(release_path), nba_team_manifest_sha256=digest(team_path))
            rows, mappings = reconcile_game(references[gid], prior[gid], parsed, prov)
            added.extend(rows)
            resolved.append(dict(game_id=gid, player_rows=len(rows), participants=sum(r["participated"] for r in rows), mappings=mappings))
        except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
            unresolved.append(dict(game_id=gid, date=day, reason=str(exc), kind=type(exc).__name__))
    merged = sorted(baseline + added, key=lambda r: (r["date"], r["game_id"], r["player_id"]))
    if len({(r["game_id"], r["player_id"]) for r in merged}) != len(merged):
        raise ValueError("merged dataset duplicate identity")
    output.mkdir(parents=True)
    dataset = output / "player_games.jsonl.gz"
    with dataset.open("wb") as file:
        with gzip.GzipFile(filename="", mode="wb", fileobj=file, mtime=0) as stream:
            for row in merged:
                stream.write((canonical(row) + "\n").encode())
    report = dict(version=VERSION, created_at_utc=datetime.now(UTC).isoformat(),
        source_hashes={str(p): digest(p) for p in (inventory_path, release_path, team_path, base_report_path)},
        base_dataset_path=base["dataset_path"], base_dataset_sha256=base["dataset_sha256"], base_rows=len(baseline),
        dataset_path=dataset.as_posix(), dataset_sha256=digest(dataset), rows=len(merged),
        recovered_games=resolved, unresolved_games=unresolved,
        summary=dict(recovered_games=len(resolved), added_player_rows=len(added), added_participants=sum(r["participated"] for r in added), pending_games=len(unresolved),
            recovered_by_type=dict(Counter(g["game_id"][:3] for g in resolved)),
            remaining_by_type=dict(Counter(g["game_id"][:3] for g in unresolved))),
        inherited_row_lineage=base["dataset_sha256"], new_row_lineage="provenance field; no inferred nonparticipant rows",
        previous_dataset_replaced=False, original_pregame_availability_known=False,
        odds_api_credits=0, actionable=False)
    write_json(output / "recovery.json", report)
    return report
