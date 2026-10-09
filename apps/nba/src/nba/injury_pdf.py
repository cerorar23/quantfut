"""Strict pilot parser for the NBA's seven-column injury PDF layout."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .audit import canonical, digest, write_json

VERSION = "injury-pdf-seven-columns-v1"
STATES = {"Out", "Doubtful", "Questionable", "Probable", "Available"}


def capture_reports(root, urls, transport=None):
    import httpx

    if not urls or len(urls) > 10 or len(set(urls)) != len(urls):
        raise ValueError("1-10 distinct report URLs required")
    for url in urls:
        u = urlparse(url)
        if (u.scheme != "https" or u.netloc != "ak-static.cms.nba.com" or u.query or u.fragment
                or not re.fullmatch(r"/referee/injury/Injury-Report_\d{4}-\d{2}-\d{2}_\d{2}(?:_\d{2})?(?:AM|PM)\.pdf", u.path)):
            raise ValueError("canonical official report URL required")
    config = dict(version=VERSION, urls=urls)
    folder = Path(root) / hashlib.sha256(canonical(config).encode()).hexdigest()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "manifest.json"
    meta = json.loads(path.read_text(encoding="utf-8")) if path.exists() else dict(
        source="NBA_official_injury_PDF", configuration=config, status="partial",
        files=[], errors=[], mode="retrospective_archive", odds_api_credits=0)
    if meta["configuration"] != config:
        raise ValueError("report configuration mismatch")
    completed = set()
    for e in meta["files"]:
        p = folder / e["name"]
        if p.stat().st_size != e["bytes"] or digest(p) != e["sha256"]:
            raise ValueError("report raw integrity mismatch")
        if e["http_status"] == 200:
            completed.add(e["url"])
    if meta["status"] == "stopped_after_failure":
        return path
    write_json(path, meta)
    with httpx.Client(timeout=httpx.Timeout(12, connect=8), transport=transport,
                      headers={"User-Agent": "QuantNBAResearch/0.1"}) as client:
        for url in urls:
            if url in completed:
                continue
            try:
                with client.stream("GET", url) as response:
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > 8_000_000:
                            raise ValueError("PDF capture exceeds 8MB cap")
                name = Path(urlparse(url).path).name
                raw = folder / name
                if raw.exists():
                    raise ValueError("refuse to overwrite untracked report")
                raw.write_bytes(data)
                meta["files"].append(dict(name=name, url=url, http_status=response.status_code,
                    bytes=len(data), sha256=digest(raw), first_received_at_utc=datetime.now(UTC).isoformat(),
                    server_date=response.headers.get("Date")))
                if response.status_code != 200 or not data.startswith(b"%PDF-"):
                    raise ValueError(f"provider HTTP {response.status_code} or non-PDF response")
            except (httpx.HTTPError, ValueError) as exc:
                meta["errors"].append(dict(url=url, kind=type(exc).__name__, reason=str(exc)))
                meta["status"] = "stopped_after_failure"
                write_json(path, meta)
                return path
            write_json(path, meta)
    meta["status"] = "received_not_parsed"
    write_json(path, meta)
    return path


def report_clock(header):
    match = re.fullmatch(r"Injury\s+Report:\s+(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})\s+(AM|PM)", header)
    if not match:
        raise ValueError("unsupported report header clock")
    naive = datetime.strptime(" ".join(match.groups()), "%m/%d/%y %I:%M %p")
    tz = ZoneInfo("America/New_York")
    first, second = naive.replace(tzinfo=tz, fold=0), naive.replace(tzinfo=tz, fold=1)
    if first.utcoffset() != second.utcoffset():
        raise ValueError("ambiguous/nonexistent report clock")
    return first.astimezone(UTC).isoformat()


def records_from_cells(pages):
    context, records, seen = {}, [], set()
    for page_number, cells in pages:
        for values in cells:
            if len(values) != 7:
                raise ValueError("expected seven PDF columns")
            date, clock, matchup, team, name, status, reason = values
            if matchup and matchup != context.get("matchup"):
                context.pop("team", None)
            for key, value in zip(("game_date", "game_clock_raw", "matchup", "team"), values[:4]):
                if value:
                    context[key] = value
            if not all(context.get(k) for k in ("game_date", "game_clock_raw", "matchup", "team")):
                raise ValueError("missing carried game/team context")
            datetime.strptime(context["game_date"], "%m/%d/%Y")
            if not re.fullmatch(r"[A-Z]{2,3}@[A-Z]{2,3}", context["matchup"]):
                raise ValueError("invalid PDF matchup")
            if not re.fullmatch(r"\d{2}:\d{2}\s*\(ET\)", context["game_clock_raw"]):
                raise ValueError("invalid PDF game display clock")
            submitted = reason != "NOT YET SUBMITTED"
            if submitted and (status not in STATES or not name or "," not in name or not reason):
                raise ValueError("unknown injury status or malformed player row")
            if not submitted and (name or status):
                raise ValueError("unsubmitted team has player status")
            key = context["game_date"], context["matchup"], context["team"], name
            if key in seen:
                raise ValueError("duplicate injury entity")
            seen.add(key)
            records.append(dict(context, player_name_raw=name or None, status_raw=status or None,
                reason_raw=reason, report_submitted=submitted, source_page=page_number,
                nba_player_id=None, nba_game_id=None, game_tipoff_utc=None,
                pregame_availability_verified=False))
    return records


def extract_report(pdf, url, received_at):
    # Optional dependency: run with the bundled PDF runtime, not football's environment.
    import pdfplumber

    pdf = Path(pdf)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "ak-static.cms.nba.com" or not parsed.path.startswith("/referee/injury/Injury-Report_"):
        raise ValueError("official injury PDF URL required")
    received = datetime.fromisoformat(received_at)
    if received.tzinfo is None or not pdf.read_bytes().startswith(b"%PDF-"):
        raise ValueError("timezone receipt and original PDF required")
    pages, headers, boundaries = [], [], None
    with pdfplumber.open(pdf) as document:
        if not 1 <= len(document.pages) <= 30:
            raise ValueError("PDF page count outside pilot cap")
        for page in document.pages:
            words = page.extract_words(x_tolerance=1)
            header_words = [w for w in words if w["top"] < 80]
            header = " ".join(w["text"] for w in header_words)
            headers.append(header)
            if boundaries is None:
                headings = [w for w in words if 90 < w["top"] < 125]
                vocabulary = [w["text"] for w in headings]
                if vocabulary != ["Game", "Date", "Game", "Time", "Matchup", "Team", "Player", "Name", "Current", "Status", "Reason"]:
                    raise ValueError("unsupported injury PDF layout")
                indexes = (0, 2, 4, 5, 6, 8, 10)
                boundaries = [headings[i]["x0"] - 4 for i in indexes] + [page.width - 19]
                minimum = max(w["bottom"] for w in headings)
            else:
                minimum = 75.4
            rules = sorted({round(e["top"], 2) for e in page.edges if e["orientation"] == "h"
                and boundaries[4] - 2 <= e["x0"] < boundaries[5]
                and e["x1"] - e["x0"] > 150 and e["top"] > minimum})
            if not rules:
                raise ValueError("missing PDF row separators")
            if page.page_number > 1:
                rules.insert(0, minimum)
            cells = []
            for top, bottom in zip(rules, rules[1:]):
                row = []
                for left, right in zip(boundaries, boundaries[1:]):
                    selected = [w for w in words if left <= w["x0"] < right
                                and top <= (w["top"] + w["bottom"]) / 2 < bottom]
                    selected.sort(key=lambda w: (round(w["top"], 1), w["x0"]))
                    row.append(" ".join(w["text"] for w in selected))
                if any(row):
                    cells.append(row)
            pages.append((page.page_number, cells))
    if len(set(headers)) != 1:
        raise ValueError("PDF pages disagree on report timestamp")
    clock = report_clock(headers[0])
    if datetime.fromisoformat(clock) > received:
        raise ValueError("report clock after receipt")
    rows = records_from_cells(pages)
    return dict(version=VERSION, source_url=url, pdf_path=pdf.as_posix(), pdf_sha256=digest(pdf),
        report_header=headers[0], report_timestamp_utc=clock, source_timezone="America/New_York",
        first_received_at_utc=received_at, original_historical_receipt_known=False,
        page_count=len(pages), rows=rows, named_players=sum(bool(r["player_name_raw"]) for r in rows),
        unsubmitted_teams=sum(not r["report_submitted"] for r in rows), actionable=False,
        limits=["pilot layout only", "game clocks have no AM/PM; tipoffs and official IDs unverified",
                "retrospective receipt is not proof of original source availability"])


def select_report(reports, as_of, *, retrospective=False):
    cutoff = datetime.fromisoformat(as_of)
    if cutoff.tzinfo is None:
        raise ValueError("timezone decision cutoff required")
    eligible = []
    for report in reports:
        timestamp = datetime.fromisoformat(report["report_timestamp_utc"])
        if timestamp.tzinfo is None:
            raise ValueError("timezone report clock required")
        received = datetime.fromisoformat(report["first_received_at_utc"])
        if received.tzinfo is None:
            raise ValueError("timezone receipt required")
        if timestamp <= cutoff and (retrospective or received <= cutoff):
            eligible.append(report)
    return max(eligible, key=lambda r: datetime.fromisoformat(r["report_timestamp_utc"])) if eligible else None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit one captured PDF using the bundled PDF runtime")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("preserve previous PDF audit; choose a new output")
    meta = json.loads(args.manifest.read_text(encoding="utf-8"))
    entries = [e for e in meta["files"] if e["name"] == args.name]
    if len(entries) != 1 or Path(args.name).name != args.name:
        raise ValueError("one safe captured PDF entry required")
    entry = entries[0]
    raw = args.manifest.parent / args.name
    if entry["http_status"] != 200 or raw.stat().st_size != entry["bytes"] or digest(raw) != entry["sha256"]:
        raise ValueError("captured PDF failed status/integrity check")
    result = extract_report(raw, entry["url"], entry["first_received_at_utc"])
    result["source_manifest_sha256"] = digest(args.manifest)
    write_json(args.output, result)
    print(json.dumps({k: result[k] for k in ("report_timestamp_utc", "named_players", "unsubmitted_teams", "page_count")}))
