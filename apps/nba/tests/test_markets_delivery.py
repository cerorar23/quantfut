import sqlite3

import pytest

from nba.delivery import Outbox, telegram_sender, football_alert_credentials
from nba.markets import price_contract, validate_quote, revalidate_selection
from nba.context import utc

NOW = "2026-10-05T19:00:30Z"


def quote():
    return dict(event_id="espn:1", player_id=203999, book="test_book", market="player_rebounds", period="full_game",
                line=1, over_decimal=1.9, under_decimal=1.9, tipoff_utc="2026-10-05T23:00:00Z",
                source_updated_at_utc="2026-10-05T19:00:00Z", first_received_at_utc="2026-10-05T19:00:05Z",
                rules_sha256="a"*64, rules_verified=True, available=True, source="synthetic_test_only",
                payout_type="cash", overtime="included", dnp_rule="void", push_rule="refund",
                early_exit_rule="action_after_participation",settlement_source="synthetic_fixture")


@pytest.mark.parametrize("changes", [{"source_updated_at_utc":"2026-10-05T18:58:00Z"},
                                    {"first_received_at_utc":"2026-10-05T19:00:31Z"},
                                    {"source_updated_at_utc":"2026-10-05T19:00:06Z"},
                                    {"tipoff_utc":"2026-10-05T19:00:00Z"},
                                    {"rules_verified":False}, {"line":float('nan')},
                                    {"payout_type":"fantasy_multiplier"}, {"available":False},
                                    {"over_decimal":True}, {"market":"player_points_rebounds_assists"}])
def test_reject_unusable_contract(changes):
    with pytest.raises(ValueError):
        validate_quote(dict(quote(), **changes), NOW)


def test_push_void_ev_are_separate():
    result = price_contract([.2,.3,.5], quote(), NOW)
    assert result["ev"] is None
    assert result["probabilities_conditional_on_participation"]["push"] == .3
    known = price_contract([.2,.3,.5], quote(), NOW, .1, "included")
    assert known["ev"]["over"] == pytest.approx(.9*(.5*.9-.2))
    with pytest.raises(ValueError):
        price_contract([.2,.3,.8], quote(), NOW)
    with pytest.raises(ValueError):
        price_contract([.2,.3,.5], quote(), NOW, .1, "excluded")


def test_revalidate_rejects_line_shift_and_price_deterioration():
    assert revalidate_selection(quote(),quote(),"over",1.83,NOW)["revalidated"]
    for change in ({"line":1.5},{"over_decimal":1.65},{"rules_sha256":"b"*64}):
        with pytest.raises(ValueError):
            revalidate_selection(quote(),dict(quote(),**change),"over",1.83,NOW)


@pytest.mark.parametrize('changes',[dict(settlement_source='another_official_feed'),dict(tipoff_utc='2026-10-06T23:00:00Z')])
def test_revalidation_rejects_changed_settlement_or_rescheduled_cut(changes):
    with pytest.raises(ValueError):revalidate_selection(quote(),dict(quote(),**changes),'over',1.83,NOW)


def test_queue_dedup_preview_and_expiry(tmp_path):
    outbox = Outbox(tmp_path)
    identifier = outbox.queue_test(NOW)
    assert outbox.queue_test(NOW) == identifier
    assert outbox.dispatch_test(identifier,NOW)["state"] == "dry_run"
    assert outbox.dispatch_test(identifier,"2026-10-05T19:10:00Z")["state"] == "rejected"
    with sqlite3.connect(outbox.path) as db:
        assert db.execute("SELECT count(*) FROM messages").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE messages SET payload='{}'")


def test_ambiguous_send_never_retries(tmp_path):
    outbox = Outbox(tmp_path,clock=lambda:utc(NOW))
    identifier = outbox.queue_test(NOW)
    calls = []
    def sender(text):
        calls.append(text)
        raise TimeoutError()
    assert outbox.dispatch_test(identifier,NOW,sender,False)["state"] == "unknown"
    assert outbox.dispatch_test(identifier,NOW,sender,False)["send_attempted"] is False
    assert len(calls) == 1


def test_claim_is_committed_before_send_and_sealed(tmp_path):
    outbox = Outbox(tmp_path,clock=lambda:utc(NOW))
    identifier = outbox.queue_test(NOW)
    def sender(text):
        assert outbox.dispatch_test(identifier,NOW,lambda _:pytest.fail("duplicate send"),False)["state"] == "sending"
        return dict(state="sent",message_id=1)
    assert outbox.dispatch_test(identifier,NOW,sender,False)["state"] == "sent"
    assert outbox.ledger.verify()["events"] >= 3


def test_live_send_cannot_bypass_expiration_with_backdated_as_of(tmp_path):
    outbox=Outbox(tmp_path,clock=lambda:utc("2026-10-05T20:00:00Z"))
    identifier=outbox.queue_test(NOW)
    result=outbox.dispatch_test(identifier,NOW,lambda _:pytest.fail("expired send"),False)
    assert result["state"]=="rejected" and not result["send_attempted"]


def test_pick_rejects_pending_gates_and_unknown_availability(tmp_path):
    outbox=Outbox(tmp_path)
    result=outbox.review_pick(dict(event_id="espn:1",player_id=203999,promoted=False,availability="unknown"),quote(),NOW,{})
    assert not result["enqueued"] and "model_not_promoted" in result["reasons"]
    assert "production_gates_pending" in result["reasons"]
    with sqlite3.connect(outbox.path) as db:
        assert db.execute("SELECT count(*) FROM messages").fetchone()[0] == 0


def test_global_football_credentials_not_used(monkeypatch):
    monkeypatch.delenv("NBA_TELEGRAM_BOT_TOKEN",raising=False)
    monkeypatch.delenv("NBA_TELEGRAM_CHAT_ID",raising=False)
    monkeypatch.setenv("NBA_TELEGRAM_ENABLED","true")
    monkeypatch.setenv("TG_BOT_TOKEN","football_token")
    with pytest.raises(ValueError):
        telegram_sender()


def test_football_bridge_only_when_explicit_and_literals(tmp_path,monkeypatch):
    import json
    for key in ("NBA_TELEGRAM_BOT_TOKEN","NBA_TELEGRAM_CHAT_ID","TG_BOT_TOKEN","TG_ALERT_CHAT"):
        monkeypatch.delenv(key,raising=False)
    env=tmp_path/"football.env"
    env.write_text("DATABASE_URL=unrelated\nTG_BOT_TOKEN='test-only-token' # comment\nTG_ALERT_CHAT=-100123\n")
    assert football_alert_credentials(env) == ("test-only-token","-100123")
    config=tmp_path/"link.json"
    config.write_text(json.dumps(dict(bot_source="football_alerts",destination_source="football_alert_chat",
                                     operational_test_enabled=True,football_env_path=str(env))))
    assert callable(telegram_sender(config))
    env.write_text("TG_BOT_TOKEN=$(unsafe)\nTG_ALERT_CHAT=-100123\n")
    with pytest.raises(ValueError):
        telegram_sender(config)
