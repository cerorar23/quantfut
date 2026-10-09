from datetime import timedelta
import sqlite3

import pytest

from nba.context import utc
from nba.delivery import Outbox
from nba.delivery_observations import delay_replay, observation, transport_metrics

NOW = "2026-10-07T19:00:00Z"


def quote(seconds=0, **changes):
    time = (utc(NOW) + timedelta(seconds=seconds)).isoformat()
    return dict(dict(event_id="nba:test", player_id=203999, book="synthetic_book", market="player_rebounds",
        period="full_game", line=7.5, over_decimal=1.9, under_decimal=1.9,
        tipoff_utc="2026-10-07T23:00:00Z", source_updated_at_utc=time, first_received_at_utc=time,
        rules_sha256="a" * 64, rules_verified=True, available=True, source="synthetic_test_only",
        payout_type="cash", overtime="included", dnp_rule="void", push_rule="refund",
        early_exit_rule="action_after_participation", settlement_source="synthetic_fixture"), **changes)


def test_late_version_never_backfills_earlier_cut():
    initial = observation(quote())
    changed = observation(quote(60, line=8.5))
    r = delay_replay(quote(), [changed, initial], NOW)
    assert [d["status"] for d in r["delays"][:4]] == ["acceptable_observation"] * 3 + ["contract_changed"]
    assert all(d["observation_id"] == initial["observation_id"] for d in r["delays"][:3])
    assert r["differing_observation_brackets"][0]["observation_gap_seconds"] == 60
    assert not r["continuous_availability_known"]


def test_duplicate_capture_is_not_more_information():
    row = observation(quote())
    a = delay_replay(quote(), [row], NOW)
    assert a == delay_replay(quote(), [row, row], NOW)
    assert a["delays"][-1]["status"] == "stale_or_post_tipoff"
    assert a["delays"][-1]["acceptable_last_observation"] is None


def test_next_observation_does_not_establish_cut_availability():
    r = delay_replay(quote(), [observation(quote(60, over_decimal=1.65))], NOW)
    assert r["delays"][0]["status"] == "unknown"
    assert r["delays"][0]["first_later_receipt_utc"]
    assert r["delays"][3]["status"] == "price_below_minimum"


@pytest.mark.parametrize("change", [dict(line=8), dict(rules_sha256="b" * 64),
    dict(overtime="excluded"), dict(settlement_source="another_fixture"), dict(under_decimal=1.7)])
def test_versioned_contract_and_two_sided_price_changes(change):
    r = delay_replay(quote(), [observation(quote()), observation(quote(60, **change))], NOW)
    expected = "acceptable_observation" if "under_decimal" in change else "contract_changed"
    assert r["delays"][3]["status"] == expected
    assert len(r["differing_observation_brackets"]) == 1


@pytest.mark.parametrize("state,expected", [("suspended", "observed_suspended"), ("error", "unknown")])
def test_error_and_suspension_do_not_reuse_previous_price(state, expected):
    r = delay_replay(quote(), [observation(quote()), observation(quote(30, available=False), state)], NOW)
    assert r["delays"][2]["status"] == expected


def test_provider_clock_cannot_replace_original_receipt():
    late = quote(60, source_updated_at_utc=NOW, line=8.5)
    r = delay_replay(quote(), [observation(quote()), observation(late)], NOW)
    assert r["delays"][2]["status"] == "acceptable_observation"
    assert r["delays"][3]["status"] == "contract_changed"


@pytest.mark.parametrize("mode", ["hash", "retro", "tie", "future_provider", "naive_time"])
def test_invalid_receipts_versions_and_integrity_are_rejected(mode):
    rows = [observation(quote())]
    if mode == "hash":
        rows[0]["quote"]["line"] = 10
    elif mode == "retro":
        rows = [observation(quote(), kind="retrospective")]
    elif mode == "tie":
        rows.append(observation(quote(line=8.5)))
    elif mode == "future_provider":
        rows = [observation(quote(source_updated_at_utc=quote(1)["first_received_at_utc"]))]
    else:
        rows = [observation(quote(first_received_at_utc="2026-10-07T19:00:00"))]
    with pytest.raises(ValueError):
        delay_replay(quote(), rows, NOW)


def test_other_operator_not_a_replacement_quote():
    assert delay_replay(quote(), [observation(quote(book="other_book"))], NOW)["delays"][0]["status"] == "unknown"


def test_only_expired_interrupted_claim_recovered_without_resend(tmp_path):
    clock = [utc(NOW)]
    outbox = Outbox(tmp_path, clock=lambda: clock[0])
    identifier = outbox.queue_test(NOW, ttl_seconds=30)
    class WorkerCrash(BaseException):
        pass
    def crash(_):
        raise WorkerCrash()
    with pytest.raises(WorkerCrash):
        outbox.dispatch_test(identifier, NOW, crash, False)
    restarted = Outbox(tmp_path, clock=lambda: clock[0])
    assert restarted.recover_expired_claims() == []
    clock[0] += timedelta(seconds=30)
    assert restarted.recover_expired_claims() == [identifier]
    assert restarted.recover_expired_claims() == []
    assert restarted.dispatch_test(identifier, NOW, lambda _: pytest.fail("blind retry"), False)["state"] == "unknown"


@pytest.mark.parametrize("state,code", [("sent", None), ("rejected", 429), ("unknown", None)])
def test_persistent_delivery_result_not_sent_again(tmp_path, state, code):
    box = Outbox(tmp_path, clock=lambda: utc(NOW))
    identifier = box.queue_test(NOW)
    calls = []
    def sender(text):
        calls.append(text)
        return dict(state=state, error_code=code)
    box.dispatch_test(identifier, "2000-01-01T00:00:00Z", sender, False)
    assert len(calls) == 1
    restart = Outbox(tmp_path, clock=lambda: utc(NOW))
    assert not restart.dispatch_test(identifier, NOW, sender, False)["send_attempted"]
    with sqlite3.connect(box.ledger.path) as db:
        import json
        raw = db.execute("SELECT payload FROM events WHERE kind='notification_send_attempt'").fetchone()[0]
        attempt = json.loads(raw)
        assert attempt["attempted_at_utc"] == utc(NOW).isoformat()
        assert attempt["requested_as_of"].startswith("2000-")


def test_expiry_after_claim_stops_transport(tmp_path):
    clocks = iter([utc(NOW), utc(NOW) + timedelta(seconds=30)])
    box = Outbox(tmp_path, clock=lambda: next(clocks))
    identifier = box.queue_test(NOW, ttl_seconds=30)
    assert box.dispatch_test(identifier, NOW, lambda _: pytest.fail("expired transport"), False)["reason"] == "expired_before_transport"


def test_two_workers_only_one_committed_claim(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    box = Outbox(tmp_path, clock=lambda: utc(NOW))
    identifier = box.queue_test(NOW)
    calls = []
    def sender(text):
        calls.append(text)
        return dict(state="sent")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: box.dispatch_test(identifier, NOW, sender, False), range(2)))
    assert len(calls) == 1
    assert sum(r.get("send_attempted") is False for r in results) == 1


def test_audit_failure_after_claim_cannot_trigger_duplicate_send(tmp_path, monkeypatch):
    clock = [utc(NOW)]
    box = Outbox(tmp_path, clock=lambda: clock[0])
    identifier = box.queue_test(NOW, ttl_seconds=30)
    append = box.ledger.append
    def broken(kind, payload):
        if kind == "notification_send_attempt":
            raise OSError("synthetic audit disk failure")
        return append(kind, payload)
    monkeypatch.setattr(box.ledger, "append", broken)
    with pytest.raises(OSError):
        box.dispatch_test(identifier, NOW, lambda _: pytest.fail("unsealed attempt"), False)
    restart = Outbox(tmp_path, clock=lambda: clock[0])
    assert restart.dispatch_test(identifier, NOW, lambda _: pytest.fail("duplicate send"), False)["state"] == "sending"
    clock[0] += timedelta(seconds=30)
    assert restart.recover_expired_claims() == [identifier]


def test_synthetic_old_clocks_excluded_from_service_ack_metrics(tmp_path):
    box = Outbox(tmp_path, clock=lambda: utc(NOW))
    identifier = box.queue_test(NOW)
    box.dispatch_test(identifier, NOW, lambda _: dict(state="sent", acknowledged_at_utc=NOW), False)
    r = transport_metrics(box)
    assert r["attempts"] == 1
    assert r["seal_to_service_acknowledgement"]["n"] == 0
    assert r["time_order_violations"] == 1
    assert not r["real_channel_latency_demonstrated"]


def test_post_tipoff_even_with_fresh_capture_is_unknown():
    r = delay_replay(quote(tipoff_utc=quote(15)["first_received_at_utc"]),
        [observation(quote(tipoff_utc=quote(15)["first_received_at_utc"]))], NOW)
    assert r["delays"][1]["status"] == "stale_or_post_tipoff"
