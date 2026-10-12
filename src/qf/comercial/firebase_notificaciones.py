"""Durable, bounded FCM delivery; notifications never contain protected picks.

Run `python -m qf.comercial.firebase_notificaciones --limit 30` from the trusted
server once configured. Scheduling and selecting publishing events are separate
operational decisions. Delivery is at least once if the network acknowledgement
or database commit is lost; event_id remains stable across retries.
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone

from ..db import conn
from .firebase import admin_app

_MATCH = re.compile(r"^[A-Za-z0-9_-]{1,100}$")
_TEXT = {
    "es": ("Nuevo aviso de QuantFut", "Abre la app para consultar la información disponible."),
    "en": ("New QuantFut update", "Open the app to view the available information."),
    "pt": ("Novo aviso do QuantFut", "Abra o aplicativo para consultar as informações disponíveis."),
    "fr": ("Nouvelle information QuantFut", "Ouvrez l’application pour consulter les informations disponibles."),
    "it": ("Nuovo avviso QuantFut", "Apri l’app per consultare le informazioni disponibili."),
    "de": ("Neue QuantFut-Mitteilung", "Öffne die App, um verfügbare Informationen anzusehen."),
}


def enqueue(account_id: int, event_key: str, expires_at: datetime,
            match_id: str | None = None) -> int:
    """Only trusted server code may enqueue an already-authorized publication."""
    if not event_key or len(event_key) > 200:
        raise ValueError("Invalid event key")
    if expires_at.tzinfo is None or expires_at <= datetime.now(timezone.utc):
        raise ValueError("Notification must expire in the future")
    if match_id is not None and not _MATCH.fullmatch(match_id):
        raise ValueError("Invalid match identifier")
    with conn() as c:
        prefs = c.execute("SELECT language FROM firebase_preferences WHERE account_id=%s", (account_id,)).fetchone()
        title, body = _TEXT.get(prefs["language"] if prefs else "es", _TEXT["es"])
        notification = c.execute(
            """INSERT INTO account_notifications (account_id,event_key,title,body,match_id,expires_at)
               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (account_id,event_key)
               DO NOTHING RETURNING notification_id""",
            (account_id, event_key, title, body, match_id, expires_at)).fetchone()
        if not notification:
            return c.execute("SELECT notification_id FROM account_notifications WHERE account_id=%s AND event_key=%s",
                             (account_id, event_key)).fetchone()["notification_id"]
        notification_id = notification["notification_id"]
        c.execute(
            """INSERT INTO notification_outbox (notification_id,installation_id,account_id)
               SELECT %s,d.installation_id,d.account_id FROM push_devices d
               JOIN firebase_preferences p USING (account_id)
               JOIN accounts a USING (account_id)
               WHERE d.account_id=%s AND d.enabled AND p.push_enabled AND a.status='active'
               ON CONFLICT DO NOTHING""", (notification_id, account_id))
        return notification_id


def message_for(row: dict):
    from firebase_admin import messaging
    title, body = _TEXT.get(row["language"], _TEXT["es"])
    data = {"event_id": str(row["notification_id"])}
    if row["match_id"]:
        data.update(route="match", match_id=row["match_id"])
    ttl = max(0, int((row["expires_at"] - datetime.now(timezone.utc)).total_seconds()))
    from datetime import timedelta
    return messaging.Message(
        token=row["token"], data=data,
        notification=messaging.Notification(title=title, body=body),
        android=messaging.AndroidConfig(ttl=timedelta(seconds=ttl),
            notification=messaging.AndroidNotification(channel_id="quantfut_predictions", tag=data["event_id"])),
        apns=messaging.APNSConfig(headers={"apns-expiration":str(int(row["expires_at"].timestamp()))}),
    )


def deliver(limit: int = 30) -> dict:
    from firebase_admin import messaging
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    summary = {"sent": 0, "retry": 0, "discarded": 0}
    for _ in range(limit):
        with conn() as c:
            # Lock the outbox item and the device until delivery is acknowledged;
            # ownership/preferences are rechecked for every attempt.
            item = c.execute(
                """SELECT o.* FROM notification_outbox o WHERE sent_at IS NULL AND attempts<8
                   AND next_attempt_at<=now() ORDER BY outbox_id LIMIT 1
                   FOR UPDATE SKIP LOCKED""").fetchone()
            if not item:
                break
            row = c.execute(
                """SELECT d.token,d.language,n.notification_id,n.match_id,n.expires_at
                   FROM push_devices d JOIN firebase_preferences p USING(account_id)
                   JOIN accounts a USING(account_id)
                   JOIN account_notifications n ON n.notification_id=%s AND n.account_id=d.account_id
                   WHERE d.installation_id=%s AND d.account_id=%s AND d.enabled AND p.push_enabled
                   AND a.status='active' AND n.expires_at>now() FOR UPDATE OF d,p,a""",
                (item["notification_id"], item["installation_id"], item["account_id"])).fetchone()
            if not row:
                c.execute("UPDATE notification_outbox SET attempts=8,last_error='expired_or_disabled' WHERE outbox_id=%s",
                          (item["outbox_id"],))
                summary["discarded"] += 1
                continue
            try:
                messaging.send(message_for(row), app=admin_app())
            except (messaging.UnregisteredError, messaging.SenderIdMismatchError):
                c.execute("UPDATE push_devices SET enabled=false WHERE installation_id=%s AND account_id=%s",
                          (item["installation_id"], item["account_id"]))
                c.execute("UPDATE notification_outbox SET attempts=8,last_error='invalid_token' WHERE outbox_id=%s",
                          (item["outbox_id"],))
                summary["discarded"] += 1
            except Exception:
                # Do not store exception text: provider messages can contain tokens.
                delay = min(3600, 30 * 2 ** item["attempts"])
                c.execute("UPDATE notification_outbox SET attempts=attempts+1,last_error='delivery_failed',"
                          "next_attempt_at=now()+make_interval(secs=>%s) WHERE outbox_id=%s",
                          (delay, item["outbox_id"]))
                summary["retry"] += 1
            else:
                c.execute("UPDATE notification_outbox SET sent_at=now(),attempts=attempts+1,last_error=NULL WHERE outbox_id=%s",
                          (item["outbox_id"],))
                summary["sent"] += 1
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30)
    print(deliver(parser.parse_args().limit))
