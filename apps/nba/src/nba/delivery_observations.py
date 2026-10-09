"""Local F6 research: receipt-time cuts and observations, never inferred fills."""
from datetime import timedelta
import hashlib
import json
import sqlite3

import numpy as np

from .audit import canonical
from .context import utc
from .markets import number, revalidate_selection, validate_quote

VERSION = "nba-delivery-observations-v1"
STREAM = ("event_id", "player_id", "book", "market", "period", "source")
CONTRACT = STREAM + ("line", "rules_sha256", "payout_type", "overtime", "dnp_rule", "push_rule",
                     "early_exit_rule", "settlement_source")


def observation(quote, state="available", kind="synthetic"):
    """Fingerprint a normalized capture; the kind is a provenance label, not proof."""
    if state not in {"available", "suspended", "error"} or kind not in {"synthetic", "live_capture", "retrospective"}:
        raise ValueError("invalid observation kind or state")
    payload = dict(quote=quote, state=state, kind=kind)
    return dict(payload, observation_id=hashlib.sha256(canonical(payload).encode()).hexdigest())


def _ordered(rows, reference):
    accepted, seen, times = [], {}, {}
    for row in rows:
        expected = observation(row["quote"], row["state"], row["kind"])
        if row != expected:
            raise ValueError("observation integrity mismatch")
        if row["observation_id"] in seen:
            continue
        seen[row["observation_id"]] = row
        quote = row["quote"]
        if any(quote.get(k) != reference.get(k) for k in STREAM):
            continue
        if row["kind"] == "retrospective":
            raise ValueError("original receipt absent for retrospective data")
        received = utc(quote["first_received_at_utc"])
        if utc(quote["source_updated_at_utc"]) > received:
            raise ValueError("provider update after receipt")
        if row["state"] == "available":
            validate_quote(quote, received.isoformat())
        elif quote.get("available") is not False:
            raise ValueError("suspended/error observation cannot claim availability")
        if received in times and times[received] != row["observation_id"]:
            raise ValueError("conflicting versions at identical receipt time")
        times[received] = row["observation_id"]
        accepted.append(row)
    return sorted(accepted, key=lambda r: utc(r["quote"]["first_received_at_utc"]))


def _status(reference, row, target, side, minimum):
    if row is None or row["state"] == "error":
        return "unknown", None
    if row["state"] == "suspended":
        return "observed_suspended", False
    quote = row["quote"]
    if any(reference.get(k) != quote.get(k) for k in CONTRACT):
        return "contract_changed", False
    if quote[side + "_decimal"] < minimum:
        return "price_below_minimum", False
    try:
        revalidate_selection(reference, quote, side, minimum, target.isoformat())
    except ValueError:
        return "stale_or_post_tipoff", None
    return "acceptable_observation", True


def delay_replay(reference, rows, sealed_at, side="over", minimum_decimal=1.8,
                 delays=(0, 15, 30, 60, 120, 300)):
    """Use latest receipt <= each cut. Later observations never backfill a cut.

    'Acceptable' describes the last fresh capture, not continuous bookmaker
    availability, subscriber receipt, acceptance, or an executed wager.
    """
    seal = utc(sealed_at)
    validate_quote(reference, sealed_at)
    minimum = number(minimum_decimal)
    if side not in {"over", "under"} or not 1 < minimum <= reference[side + "_decimal"]:
        raise ValueError("invalid side or price threshold")
    if not delays or len(set(delays)) != len(delays) or any(
            isinstance(d, bool) or not isinstance(d, int) or not 0 <= d <= 3600 for d in delays):
        raise ValueError("distinct integer delays in 0..3600 required")
    ordered = _ordered(rows, reference)
    results = []
    for delay in delays:
        cut = seal + timedelta(seconds=delay)
        before = [r for r in ordered if utc(r["quote"]["first_received_at_utc"]) <= cut]
        after = [r for r in ordered if utc(r["quote"]["first_received_at_utc"]) > cut]
        latest = before[-1] if before else None
        status, acceptable = _status(reference, latest, cut, side, minimum)
        results.append(dict(delay_seconds=delay, cut_utc=cut.isoformat(), status=status,
            acceptable_last_observation=acceptable,
            observation_id=latest["observation_id"] if latest else None,
            observation_received_at_utc=latest["quote"]["first_received_at_utc"] if latest else None,
            input_age_seconds=(cut - utc(latest["quote"]["source_updated_at_utc"])).total_seconds() if latest else None,
            first_later_receipt_utc=after[0]["quote"]["first_received_at_utc"] if after else None,
            availability_at_exact_cut_verified=False, actionable=False))
    brackets = []
    # These bracket differing captures, not the first external price change.
    for earlier, later in zip(ordered, ordered[1:]):
        if "error" in {earlier["state"], later["state"]}:
            continue
        a, b = earlier["quote"], later["quote"]
        signature = lambda r: (r["state"], *(r["quote"].get(k) for k in CONTRACT),
                               r["quote"].get("over_decimal"), r["quote"].get("under_decimal"))
        if signature(earlier) != signature(later):
            brackets.append(dict(earlier_receipt_utc=a["first_received_at_utc"],
                later_receipt_utc=b["first_received_at_utc"],
                observation_gap_seconds=(utc(b["first_received_at_utc"]) - utc(a["first_received_at_utc"])).total_seconds(),
                external_change_time_known=False, exact_duration_known=False,
                earlier_id=earlier["observation_id"], later_id=later["observation_id"]))
    return dict(version=VERSION, delays=results, differing_observation_brackets=brackets,
                unique_stream_observations=len(ordered), kinds=sorted({r["kind"] for r in ordered}),
                continuous_availability_known=False, wager_acceptance_known=False, actionable=False)


def transport_metrics(outbox):
    """Measure local transport responses. Device receipt is never established."""
    outbox.ledger.verify()
    with sqlite3.connect(outbox.ledger.path) as db:
        events = [(received, kind, json.loads(payload)) for received, kind, payload in
                  db.execute("SELECT received_at,kind,payload FROM events ORDER BY seq")]
    seals, attempts, request_times, ack_times = {}, {}, [], []
    states, violations = {}, 0
    for received, kind, payload in events:
        identifier = payload.get("id")
        if kind == "notification_sealed_before_queue":
            seals[identifier] = utc(received)
        elif kind == "notification_send_attempt":
            attempts[identifier] = utc(payload["attempted_at_utc"])
        elif kind == "notification_send_result":
            result = payload["outcome"]
            states[result["state"]] = states.get(result["state"], 0) + 1
            duration = number(result["request_duration_seconds"])
            if duration < 0:
                raise ValueError("negative transport duration")
            request_times.append(duration)
            ack = result.get("acknowledged_at_utc") if result["state"] == "sent" else None
            if ack is not None:
                t = utc(ack)
                response = utc(result["response_recorded_at_utc"])
                if identifier not in seals or identifier not in attempts or not seals[identifier] <= attempts[identifier] <= t <= response:
                    violations += 1
                else:
                    ack_times.append((t - seals[identifier]).total_seconds())
    def summary(values):
        return dict(n=len(values), p50_seconds=float(np.quantile(values, .5)) if values else None,
                    p95_seconds=float(np.quantile(values, .95)) if values else None)
    return dict(attempts=len(attempts), result_states=states, transport_response_duration=summary(request_times),
                seal_to_service_acknowledgement=summary(ack_times), time_order_violations=violations,
                subscriber_receipt_verified=False, real_channel_latency_demonstrated=False)
