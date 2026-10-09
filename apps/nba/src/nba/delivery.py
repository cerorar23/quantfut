"""NBA-only local outbox. Live path currently supports operational tests only."""
from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import time

import httpx

from .audit import Ledger, canonical
from .context import utc
from .markets import validate_quote


class Outbox:
    def __init__(self, root, clock=None):
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "outbox.sqlite"
        self.ledger = Ledger(root / "delivery_audit.sqlite")
        self.clock = clock or (lambda: datetime.now(UTC))
        with sqlite3.connect(self.path) as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, sealed_hash TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('queued','sending','sent','unknown','rejected')),
                outcome TEXT
            );
            CREATE TRIGGER IF NOT EXISTS payload_no_update BEFORE UPDATE OF id,payload,sealed_hash ON messages
            BEGIN SELECT RAISE(ABORT, 'immutable NBA message'); END;
            CREATE TRIGGER IF NOT EXISTS messages_no_delete BEFORE DELETE ON messages
            BEGIN SELECT RAISE(ABORT, 'immutable NBA message'); END;
            """)

    def queue_test(self, as_of, ttl_seconds=300):
        now = utc(as_of)
        if not 1 <= ttl_seconds <= 3600:
            raise ValueError("invalid message lifetime")
        payload = dict(kind="operational_test", created_at_utc=now.isoformat(),
                       expires_at_utc=(now + timedelta(seconds=ttl_seconds)).isoformat(),
                       text="PRUEBA TÉCNICA NBA — sin pick ni recomendación de apuesta.\nCanal NBA independiente.")
        return self._queue(payload)

    def _queue(self, payload):
        identifier = hashlib.sha256(canonical(payload).encode()).hexdigest()
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            if not db.execute("SELECT 1 FROM messages WHERE id=?", (identifier,)).fetchone():
                sealed = self.ledger.append("notification_sealed_before_queue", dict(id=identifier, payload=payload))
                db.execute("INSERT INTO messages VALUES (?,?,?,'queued',NULL)", (identifier, canonical(payload), sealed))
        return identifier

    def review_pick(self, forecast, quote, as_of, gate_registry):
        """Seal forecast, then select/reject; no research pick reaches dispatch."""
        self.ledger.append("forecast_before_selection", forecast)
        reasons = []
        if forecast.get("promoted") is not True:
            reasons.append("model_not_promoted")
        if forecast.get("availability") != "available" or forecast.get("availability_verified") is not True:
            reasons.append("availability_unverified")
        if forecast.get("identity_verified") is not True or forecast.get("role_verified") is not True:
            reasons.append("identity_or_role_unverified")
        if forecast.get("event_id") != quote.get("event_id") or forecast.get("player_id") != quote.get("player_id"):
            reasons.append("forecast_contract_identity_mismatch")
        phases = gate_registry.get("phases", [])
        gates = {p["gate"]["id"]: p["gate"] for p in phases if "gate" in p}
        if any(gates.get(f"G{i}", {}).get("status") != "passed" for i in range(10)):
            reasons.append("production_gates_pending")
        try:
            validate_quote(quote, as_of)
        except (ValueError, KeyError, TypeError) as exc:
            reasons.append("quote_rejected:" + str(exc))
        # Commercial signals deliberately await an independently reviewed publication service.
        reasons.append("pick_dispatch_not_promoted")
        result = dict(state="rejected", reasons=reasons, enqueued=False)
        self.ledger.append("pick_selection_rejected", result)
        return result

    def dispatch_test(self, identifier, as_of, sender=None, dry_run=True):
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload,sealed_hash,state FROM messages WHERE id=?", (identifier,)).fetchone()
            if row is None:
                raise ValueError("unknown notification")
            payload = json.loads(row[0])
            if hashlib.sha256(canonical(payload).encode()).hexdigest() != identifier:
                raise ValueError("outbox integrity mismatch")
            self.ledger.verify()
            with sqlite3.connect(self.ledger.path) as audit_db:
                sealed = audit_db.execute("SELECT payload FROM events WHERE event_hash=? AND kind='notification_sealed_before_queue'", (row[1],)).fetchone()
            if sealed is None or json.loads(sealed[0]) != dict(id=identifier, payload=payload):
                raise ValueError("notification seal absent or mismatched")
            if row[2] != "queued":
                return dict(state=row[2], send_attempted=False)
            # Simulation may use an as-of; actual sends always use the trusted wall clock.
            now = utc(as_of) if dry_run else utc(self.clock().isoformat())
            if payload["kind"] != "operational_test" or not utc(payload["created_at_utc"]) <= now < utc(payload["expires_at_utc"]):
                db.execute("UPDATE messages SET state='rejected',outcome=? WHERE id=?", (canonical(dict(reason="expired_or_invalid_kind")), identifier))
                self.ledger.append("notification_expired", dict(id=identifier))
                return dict(state="rejected", send_attempted=False)
            if dry_run:
                self.ledger.append("notification_local_preview", dict(id=identifier, text=payload["text"]))
                return dict(state="dry_run", send_attempted=False, text=payload["text"], latency_measured=False)
            if sender is None:
                raise ValueError("explicit NBA sender required")
            # Commit claim before network I/O. After crash/ambiguous timeout never auto-retry.
            db.execute("UPDATE messages SET state='sending' WHERE id=?", (identifier,))
        started = time.monotonic()
        now = utc(self.clock().isoformat())
        if not utc(payload["created_at_utc"]) <= now < utc(payload["expires_at_utc"]):
            outcome = dict(state="rejected", reason="expired_before_transport", send_attempted=False)
            self.ledger.append("notification_expired_before_transport", dict(id=identifier, observed_at_utc=now.isoformat()))
            with sqlite3.connect(self.path) as db:
                db.execute("UPDATE messages SET state='rejected',outcome=? WHERE id=?", (canonical(outcome), identifier))
            return outcome
        self.ledger.append("notification_send_attempt", dict(id=identifier, attempted_at_utc=now.isoformat(),
                                                            requested_as_of=as_of))
        try:
            outcome = sender(payload["text"])
            if outcome.get("state") not in {"sent", "rejected", "unknown"}:
                raise ValueError("invalid sender result")
        except Exception:
            outcome = dict(state="unknown", reason="ambiguous_transport_failure_no_retry")
        outcome["request_duration_seconds"] = time.monotonic() - started
        outcome["response_recorded_at_utc"] = utc(self.clock().isoformat()).isoformat()
        outcome["subscriber_receipt_verified"] = False
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE messages SET state=?,outcome=? WHERE id=?", (outcome["state"], canonical(outcome), identifier))
        self.ledger.append("notification_send_result", dict(id=identifier, outcome=outcome))
        return outcome

    def recover_expired_claims(self):
        """Make expired interrupted sends explicit; never reclaim or resend them.

        A fresh sending claim may still belong to a running worker. Recovery
        therefore only touches expired claims; the remote outcome stays unknown.
        """
        now = utc(self.clock().isoformat())
        recovered = []
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            for identifier, raw in db.execute("SELECT id,payload FROM messages WHERE state='sending'").fetchall():
                payload = json.loads(raw)
                if now < utc(payload["expires_at_utc"]):
                    continue
                if hashlib.sha256(canonical(payload).encode()).hexdigest() != identifier:
                    raise ValueError("outbox integrity mismatch")
                self.ledger.verify()
                outcome = dict(state="unknown", reason="expired_interrupted_claim_no_retry",
                               recovered_at_utc=now.isoformat(), automatic_retry=False)
                self.ledger.append("notification_interrupted_recovery", dict(id=identifier, outcome=outcome))
                db.execute("UPDATE messages SET state='unknown',outcome=? WHERE id=?", (canonical(outcome), identifier))
                recovered.append(identifier)
        return recovered


def football_alert_credentials(path):
    """Explicit opt-in bridge: only the two authorized football Telegram fields."""
    values = {}
    path = Path(path)
    if path.exists():
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip().removeprefix("export ")
            if line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key not in {"TG_BOT_TOKEN", "TG_ALERT_CHAT"}:
                continue
            if key in values:
                raise ValueError("duplicate football Telegram configuration")
            value = value.strip()
            if value[:1] in {"'", '"'}:
                quote = value[0]
                end = value.find(quote, 1)
                if end < 0 or value[end + 1:].strip() and not value[end + 1:].strip().startswith("#"):
                    raise ValueError("unsupported football Telegram literal")
                value = value[1:end]
            else:
                value = value.split(" #", 1)[0].strip()
            if "$" in value or "`" in value:
                raise ValueError("literal football Telegram values required")
            values[key] = value
    return (os.environ.get("TG_BOT_TOKEN") or values.get("TG_BOT_TOKEN"),
            os.environ.get("TG_ALERT_CHAT") or values.get("TG_ALERT_CHAT"))


def telegram_sender(config_path=None):
    """NBA credentials, or the user-authorized bot/chat bridge. Never log secrets."""
    token, destination = os.environ.get("NBA_TELEGRAM_BOT_TOKEN"), os.environ.get("NBA_TELEGRAM_CHAT_ID")
    enabled = os.environ.get("NBA_TELEGRAM_ENABLED", "false").lower() == "true"
    if config_path is not None and Path(config_path).exists():
        link = json.loads(Path(config_path).read_text())
        if link.get("bot_source") != "football_alerts" or link.get("destination_source") != "football_alert_chat":
            raise ValueError("unsupported Telegram bridge")
        shared_token, shared_chat = football_alert_credentials(link["football_env_path"])
        token, destination = token or shared_token, destination or shared_chat
        enabled = enabled or link.get("operational_test_enabled") is True
    if not enabled or not token or not destination:
        raise ValueError("NBA Telegram disabled or private configuration missing")

    def send(text):
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post("https://api.telegram.org/bot" + token + "/sendMessage",
                                       json=dict(chat_id=destination, text=text))
            body = response.json()
            if response.is_success and body.get("ok") is True and isinstance(body.get("result", {}).get("message_id"), int):
                return dict(state="sent", message_id=body["result"]["message_id"],
                            telegram_server_date=body["result"].get("date"),
                            acknowledged_at_utc=datetime.now(UTC).isoformat(), subscriber_receipt_verified=False)
            # API rejection is different from timeout; neither is automatically retried.
            if body.get("ok") is False and response.status_code < 500:
                return dict(state="rejected", error_code=body.get("error_code"), automatic_retry=False)
            return dict(state="unknown", reason="ambiguous_telegram_response_no_retry")
        except Exception:
            return dict(state="unknown", reason="ambiguous_transport_failure_no_retry")
    return send
