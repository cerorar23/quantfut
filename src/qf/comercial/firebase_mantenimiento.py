"""Daily expiry of disposable Firebase records; never edits the business ledger."""
from ..db import conn


def clean() -> dict[str, int]:
    with conn() as c:
        # Remove dependent queue rows before notifications or devices.
        queue = c.execute(
            """DELETE FROM notification_outbox o
               WHERE EXISTS (SELECT 1 FROM account_notifications n
                             WHERE n.notification_id=o.notification_id
                             AND n.expires_at < now()-interval '30 days')
                  OR EXISTS (SELECT 1 FROM push_devices d
                             WHERE d.installation_id=o.installation_id
                             AND d.updated_at < now()-interval '90 days')""").rowcount
        notifications = c.execute(
            "DELETE FROM account_notifications WHERE expires_at < now()-interval '30 days'").rowcount
        devices = c.execute(
            "DELETE FROM push_devices WHERE updated_at < now()-interval '90 days'").rowcount
    return {"queue": queue, "notifications": notifications, "devices": devices}


if __name__ == "__main__":
    import json
    print(json.dumps(clean()))
