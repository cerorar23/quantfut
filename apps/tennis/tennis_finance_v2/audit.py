"""Offline evidence inventory and reproducible prospective paper evaluation.

Observed prices, expected return and historical model scores are not realized
profit. All snapshots remain an inventory, never independent bets. This module
does not certify fills or grant permission to place bets.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from tennis_engine.operations import now, utc
from tennis_engine.paper_validation import (
    digest, evaluate_paper, load_policy, quote_receipt_from_archive,
)
from tennis_engine.shadow import verify_record


def read(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path: Path, value: Any) -> None:
    """Exclusive creation preserves earlier observations and reports."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)


def quote_inventory(roots: list[Path], as_of: str) -> dict:
    """Verify originals, count unique events, preserve repeated observations.

    Duplicating a directory in configuration cannot enlarge the sample. A later
    receipt is excluded from an as-of inventory even if physically present.
    """
    receipts = set()
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            raise ValueError("Configured snapshot root is absent")
        receipts.update(p.resolve() for p in root.rglob("receipt.json"))
    errors = Counter()
    events, books, markets = set(), set(), set()
    manifest = {}
    count = observations = fresh = 0
    for path in sorted(receipts):
        manifest[str(path)] = digest(path)
        try:
            receipt = read(path)
            endpoint = receipt["path"]
            if not endpoint.startswith("sports/tennis_") or not endpoint.endswith("/odds"):
                continue
            archived = quote_receipt_from_archive(path)
            source = Path(archived["source_path"])
            manifest[str(source)] = digest(source)
            requested, received = utc(archived["requested_at"]), utc(archived["received_at"])
            if requested > received:
                raise ValueError("Invalid archive chronology")
            if received > utc(as_of):
                errors["not_available_as_of"] += 1
                continue
            body = read(source)
            rows = body if isinstance(body, list) else [body]
            if len({row["id"] for row in rows}) != len(rows):
                raise ValueError("Duplicate event in response")
            local_events, local_books, local_markets = set(), set(), set()
            local_observations = local_fresh = 0
            for event in rows:
                if not event["sport_key"].startswith("tennis_"):
                    raise ValueError("Non-tennis event in tennis response")
                local_events.add(event["id"])
                for book in event.get("bookmakers", []):
                    local_books.add(book["key"])
                    for market in book.get("markets", []):
                        local_markets.add(market["key"])
                        for outcome in market.get("outcomes", []):
                            price = outcome.get("price")
                            if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 1:
                                raise ValueError("Invalid observed price")
                            local_observations += 1
                            updated = utc(market.get("last_update") or book["last_update"])
                            if updated <= received <= utc(as_of) < utc(event["commence_time"]) and (utc(as_of)-updated).total_seconds() <= 900 and (utc(as_of)-received).total_seconds() <= 900:
                                local_fresh += 1
            count += 1
            events.update(local_events)
            books.update(local_books)
            markets.update(local_markets)
            observations += local_observations
            fresh += local_fresh
        except (ValueError, KeyError, TypeError, OSError):
            errors["invalid_archive"] += 1
    return dict(verified_odds_responses=count, distinct_event_ids=len(events),
                raw_outcome_observations=observations, fresh_observations=fresh,
                distinct_bookmakers=len(books), observed_market_keys=sorted(markets),
                errors=dict(errors), input_sha256=manifest,
                observations_are_not_bets=True)


def cost_sensitivity(rows: list[dict]) -> list[dict]:
    """Additional friction per originally committed unit, including voids.

    These are explicit stress assumptions, not measured bookmaker charges.
    Pending selections prevent reporting a full-ledger return. Denominator is
    every originally committed stake; action-only ROI is a different metric.
    """
    if any(not isinstance(r.get("stake"), (int, float)) or isinstance(r["stake"], bool)
           or not math.isfinite(r["stake"]) or r["stake"] <= 0 for r in rows):
        raise ValueError("Positive finite stakes required")
    known = [r for r in rows if r.get("net_profit") is not None]
    if any(isinstance(r["net_profit"], bool) or not isinstance(r["net_profit"], (int, float))
           or not math.isfinite(r["net_profit"]) for r in known):
        raise ValueError("Finite settled profit required")
    stake = sum(r["stake"] for r in rows)
    complete = bool(rows) and len(known) == len(rows)
    return [dict(additional_cost_fraction_of_stake=cost, orders=len(rows),
                 settled=len(known), pending=len(rows)-len(known),
                 full_ledger_net_roi=(sum(r["net_profit"] for r in known)/stake-cost) if complete else None,
                 assumptions_only=True)
            for cost in (0., .005, .01, .02)]


def sample_planning() -> list[dict]:
    """Illustrative normal approximation, two-sided alpha .05, power .80.

    Assumes independent flat bets at decimal 2, no voids or costs. Tournament
    and player dependence can increase the requirement. This neither changes
    the frozen minimum nor guarantees statistical power of the actual study.
    """
    return [dict(target_net_roi=edge, assumed_decimal_odds=2.,
                 approximate_independent_orders=math.ceil((1.959963984540054+0.8416212335729143)**2 * (1-edge**2)/edge**2),
                 assumptions="Independent even-money bets; normal approximation; alpha=.05 two-sided; power=.80; no costs/voids",
                 frozen_policy_unchanged=True) for edge in (.01, .03, .05)]


def audit(config_path: Path, *, as_of: str | None = None) -> dict:
    stamp = as_of or now()
    config = read(config_path)
    policy_path = Path(config["policy_path"])
    if digest(policy_path) != config["policy_sha256"]:
        raise ValueError("Configured policy changed")
    policy = load_policy(policy_path)
    for path, expected in policy["artifacts"].items():
        if digest(path) != expected:
            raise ValueError("Frozen model artifact changed")
    orders = Path(config["orders_root"])
    if not orders.is_dir():
        raise ValueError("Configured order ledger is absent; do not substitute an empty ledger")
    results_path, closings_path = Path(config["results_path"]), Path(config["closings_path"])
    results, closes = read(results_path), read(closings_path)
    if not isinstance(results, list) or not isinstance(closes, list):
        raise ValueError("Explicit result and closing lists required")
    closings = [dict(event_id=r["event_id"], receipt=quote_receipt_from_archive(Path(r["receipt_path"]))) for r in closes]
    inputs = {str(Path(p).resolve()): digest(p) for p in [config_path, policy_path, results_path, closings_path, *orders.glob("*.json")]}
    inputs.update(policy["artifacts"])
    import tennis_engine.paper_validation as candidate
    inputs.update({str((Path(candidate.__file__).parent/name).resolve()): sha
                   for name, sha in policy["candidate_code_sha256"].items()})
    inputs[policy["model_protocol_path"]] = policy["model_protocol_sha256"]
    for receipt in closings:
        r = receipt["receipt"]
        inputs[r["archive_receipt_path"]] = r["archive_receipt_sha256"]
        inputs[r["source_path"]] = r["sha256"]
    financial = evaluate_paper(policy_path, orders, results_path, closings=closings, as_of=stamp)
    inventory = quote_inventory([Path(p) for p in config.get("snapshot_roots", [])], stamp)
    inputs.update(inventory.pop("input_sha256"))
    legacy = Counter()
    legacy_paths = set()
    for root in config.get("shadow_roots", []):
        if not Path(root).is_dir():
            raise ValueError("Configured prediction root is absent")
        legacy_paths.update(p.resolve() for p in Path(root).rglob("record.json"))
    for path in sorted(legacy_paths):
        inputs[str(path)] = digest(path)
        try:
            record = verify_record(path)
            if not record.get("prediction_sealed_at"):
                legacy["unsealed_records"] += 1
            elif utc(record["prediction_sealed_at"]) > utc(stamp):
                legacy["records_not_available_as_of"] += 1
            else:
                legacy["sealed_research_records"] += 1
                legacy["outside_frozen_financial_period"] += sum(
                    not utc(policy["evaluation_start"]) <= utc(r["event"]["commence_time"]) < utc(policy["evaluation_end"])
                    for r in record.get("events", []))
        except (ValueError, KeyError, TypeError, OSError):
            legacy["invalid_records"] += 1
    research_files = []
    for path in sorted({Path(p).resolve() for p in config.get("research_prediction_files", [])}):
        inputs[str(path)] = digest(path)
        value = read(path)
        checksum = value.pop("payload_sha256", None)
        if checksum is not None:
            body = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()
            if hashlib.sha256(body).hexdigest() != checksum:
                raise ValueError("Research prediction checksum changed")
        research_files.append(dict(path=str(path), predictions=len(value.get("forecasts", [])) if "forecasts" in value else 1,
            locally_hashed=checksum is not None, prospective_financial_orders=0,
            reason="Research or integration output is not a sealed order under this financial policy"))
    # Include referenced order evidence even when stored outside configured archives.
    for path in orders.glob("*.json"):
        order = read(path)
        for key in ("record_path",):
            if order.get(key) and Path(order[key]).is_file():
                inputs[str(Path(order[key]).resolve())] = digest(order[key])
        receipt = order.get("quote_receipt") or {}
        for key in ("archive_receipt_path", "source_path"):
            if receipt.get(key) and Path(receipt[key]).is_file():
                inputs[str(Path(receipt[key]).resolve())] = digest(receipt[key])
    for result in results:
        if result.get("source_path") and Path(result["source_path"]).is_file():
            inputs[str(Path(result["source_path"]).resolve())] = digest(result["source_path"])
    if any(digest(path) != sha for path, sha in inputs.items()):
        raise ValueError("Evidence changed during evaluation")
    blockers = []
    if utc(stamp) < utc(policy["evaluation_start"]): blockers.append("financial_period_not_started")
    if not financial["evaluation_period_complete"]: blockers.append("fixed_financial_period_not_complete")
    if inventory["errors"].get("invalid_archive"): blockers.append("invalid_original_quote_archive")
    if financial["rejected"]: blockers.append("rejected_order_result_or_close_evidence")
    for circuit, summary in financial["by_circuit"].items():
        if summary["settled"] < policy["minimum_events_per_circuit"]: blockers.append(circuit+":insufficient_settled_events")
        if summary["competitions"] < policy["minimum_competitions_per_circuit"]: blockers.append(circuit+":insufficient_competition_blocks")
        if summary["closing_coverage"] < 1: blockers.append(circuit+":incomplete_closing_coverage")
        if summary["pending"]: blockers.append(circuit+":unsettled_orders")
        for field in ("net_paper_roi_ci95", "closing_return_ci95"):
            if not summary[field] or summary[field][0] <= 0: blockers.append(circuit+":"+field+"_not_positive")
    # A passing paper study still cannot prove fills, costs or future returns.
    blockers.extend(["actual_account_fills_costs_limits_not_verified", "independent_source_and_timestamp_attestation_not_verified"])
    return dict(schema="tennis-financial-evidence-audit-v2", evaluated_at=stamp,
                status="profitability_not_accredited", profitability_accredited=False,
                paper_study_gate_passed=financial["status"] == "candidate_for_execution_review",
                real_money_approved=False, actual_execution_verified=False,
                policy_period=[policy["evaluation_start"], policy["evaluation_end"]],
                financial_report=financial, quote_inventory=inventory,
                legacy_record_inventory=dict(legacy), blockers=blockers,
                additional_research_prediction_files=research_files,
                cost_sensitivity_by_circuit={c: cost_sensitivity([r for r in financial["rows"] if r["circuit"] == c]) for c in ("ATP", "WTA")},
                sample_planning_illustration=sample_planning(),
                scope=dict(confirmatory_contracts=["pinnacle:h2h"],
                           other_market_financial_validation=False,
                           context_unused_by_candidate=["travel", "weather", "load"],
                           local_hashes_are_not_external_timestamp_proofs=True,
                           source_hashes_do_not_prove_parsed_field_correctness=True),
                input_sha256=inputs, new_odds_requests=0, actual_wagers_placed=0)
