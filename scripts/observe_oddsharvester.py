r"""Collect experimental OddsHarvester 1X2 snapshots without touching QuantFut's DB.

Usage (Windows):
    .local\oddsharvester_venv\Scripts\python.exe scripts\observe_oddsharvester.py

Raw responses, logs, normalized quotes, and coverage summaries stay under
the ignored .local/oddsharvester_observations directory.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
OBSERVATIONS = ROOT / ".local" / "oddsharvester_observations"
BOOKMAKER_REGIONS = {
    "mexico": "mexico-liga-mx",
    "brasil": "brazil-serie-a",
    "argentina": "football/argentina/superliga",
}
REGIONAL_DOMAIN = "https://www.cuotasahora.com"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S UTC").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def decimal_odd(value: object) -> float | None:
    try:
        odd = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not odd.is_finite() or not 1 < odd < 1000:
        return None
    return float(odd)


def executable() -> Path:
    if os.name == "nt":
        return ROOT / ".local" / "oddsharvester_venv" / "Scripts" / "oddsharvester.exe"
    return ROOT / ".local" / "oddsharvester_venv" / "bin" / "oddsharvester"


def browser_path() -> Path:
    return ROOT / ".local" / "pw-browsers"


def collect(league: str, slug: str, run_dir: Path, timeout_seconds: int) -> dict:
    raw_file = run_dir / f"{league}.json"
    log_file = run_dir / f"{league}.log"
    command = [
        str(executable()), "upcoming", "-s", "football", "-l", slug,
        "-m", "1x2", "--base-url", REGIONAL_DOMAIN, "--headless",
        "--full-scrape", "-f", "json", "-o", str(raw_file),
    ]
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_path())
    result = {"league": league, "slug": slug, "raw_file": str(raw_file),
              "log_file": str(log_file), "exit_code": None, "error": None}
    try:
        completed = subprocess.run(
            command, cwd=ROOT, env=env, capture_output=True, text=True,
            errors="replace", timeout=timeout_seconds, check=False,
        )
        log_text = completed.stdout + "\n" + completed.stderr
        log_file.write_text(log_text, encoding="utf-8")
        result["exit_code"] = completed.returncode
        scrape_total = re.search(r"Scraping complete: (\d+)/(\d+) successful", log_text)
        if scrape_total:
            result["match_pages_attempted"] = int(scrape_total.group(2))
            result["match_pages_failed"] = (
                int(scrape_total.group(2)) - int(scrape_total.group(1))
            )
    except subprocess.TimeoutExpired as exc:
        log_file.write_text(str(exc), encoding="utf-8")
        result["error"] = f"Timeout after {timeout_seconds} seconds"
    except OSError as exc:
        log_file.write_text(str(exc), encoding="utf-8")
        result["error"] = str(exc)

    if raw_file.exists():
        try:
            data = json.loads(raw_file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("Expected a list of matches")
            result["matches_raw"] = len(data)
            result["data"] = data
        except (json.JSONDecodeError, ValueError) as exc:
            result["error"] = f"Invalid raw JSON: {exc}"
    else:
        result["matches_raw"] = 0
        result["data"] = []
        if result["exit_code"] != 0 and result["error"] is None:
            result["error"] = "No output file; see log"
    if result["exit_code"] not in (None, 0) and result["error"] is None:
        result["error"] = f"OddsHarvester exited with code {result['exit_code']}; see log"
    return result


def normalize(result: dict, run_id: str) -> tuple[list[dict], dict]:
    quotes = []
    bookies: Counter[str] = Counter()
    matched = 0
    missing_date = 0
    past_or_started = 0
    invalid_market_rows = 0
    for match in result["data"]:
        kickoff = parse_utc(match.get("match_date"))
        captured = parse_utc(match.get("scraped_date")) or utc_now()
        if kickoff is None:
            missing_date += 1
            continue
        if kickoff <= captured:
            past_or_started += 1
            continue
        match_quotes = []
        for item in match.get("1x2_market") or []:
            if item.get("period") != "FullTime":
                invalid_market_rows += 1
                continue
            odds = {selection: decimal_odd(item.get(selection)) for selection in ("1", "X", "2")}
            bookie = str(item.get("bookmaker_name", "")).strip()
            if not bookie or any(value is None for value in odds.values()):
                invalid_market_rows += 1
                continue
            match_quotes.append({
                "run_id": run_id, "source": REGIONAL_DOMAIN,
                "league": result["league"], "match_link": match.get("match_link"),
                "home_team": match.get("home_team"), "away_team": match.get("away_team"),
                "kickoff_utc": kickoff.isoformat(), "captured_utc": captured.isoformat(),
                "bookmaker": bookie, "market": "1x2", "period": "full_time",
                "home": odds["1"], "draw": odds["X"], "away": odds["2"],
            })
            bookies[bookie] += 1
        if match_quotes:
            matched += 1
            quotes.extend(match_quotes)
    coverage = {
        "matches_raw": result["matches_raw"], "matches_with_quotes": matched,
        "quotes": len(quotes), "bookmakers": dict(sorted(bookies.items())),
        "match_pages_attempted": result.get("match_pages_attempted"),
        "match_pages_failed": result.get("match_pages_failed"),
        "missing_kickoff": missing_date, "past_or_started": past_or_started,
        "invalid_market_rows": invalid_market_rows,
        "exit_code": result["exit_code"], "error": result["error"],
        "raw_file": result["raw_file"], "log_file": result["log_file"],
    }
    return quotes, coverage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leagues", nargs="+", choices=BOOKMAKER_REGIONS,
                        default=list(BOOKMAKER_REGIONS))
    parser.add_argument("--timeout-seconds", type=int, default=600)
    args = parser.parse_args()
    if not executable().is_file() or not browser_path().is_dir():
        parser.error("OddsHarvester virtualenv or Playwright browsers are missing under .local")

    run_id = utc_now().strftime("%Y%m%dT%H%M%SZ")
    run_dir = OBSERVATIONS / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    all_quotes = []
    coverage = {}
    for league in args.leagues:
        result = collect(league, BOOKMAKER_REGIONS[league], run_dir, args.timeout_seconds)
        quotes, coverage[league] = normalize(result, run_id)
        all_quotes.extend(quotes)
        print(f"{league}: {coverage[league]['matches_with_quotes']} matches, "
              f"{coverage[league]['quotes']} complete 1X2 quotes", flush=True)

    quotes_file = run_dir / "quotes.jsonl"
    with quotes_file.open("w", encoding="utf-8") as handle:
        for quote in all_quotes:
            handle.write(json.dumps(quote, ensure_ascii=False) + "\n")
    summary = {"run_id": run_id, "captured_utc": utc_now().isoformat(),
               "source": REGIONAL_DOMAIN, "status": "ok", "coverage": coverage,
               "quotes_file": str(quotes_file)}
    if any(item["error"] for item in coverage.values()):
        summary["status"] = "partial_failure" if all_quotes else "failure"
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    latest_temp = OBSERVATIONS / "latest.tmp"
    latest_temp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_temp.replace(OBSERVATIONS / "latest.json")
    print(json.dumps({"run_id": run_id, "status": summary["status"],
                      "quotes": len(all_quotes), "run_dir": str(run_dir)}, ensure_ascii=False))
    return 1 if summary["status"] == "failure" else 0


if __name__ == "__main__":
    sys.exit(main())
