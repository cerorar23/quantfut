"""Conversions API de Meta para eventos de app (action_source=app).

El servidor es la única fuente de los eventos de valor (registro, suscripción, cobros,
desbloqueos): ninguno sale también del SDK, así que no hay deduplicación de la que depender.
`enqueue` va dentro de la transacción del hecho; `send_pending` (cron cada 5 min) envía.
Apagado por defecto: META_CAPI_ENABLED=1 para encolar y enviar.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

from ..db import conn
from . import meta_datos

log = logging.getLogger(__name__)
GRAPH_VERSION = "v24.0"
MAX_ATTEMPTS = 5
ALERT_AT = 3
# Meta rechaza eventos con más de 7 días de antigüedad.
MAX_AGE = timedelta(days=7)


def enabled() -> bool:
    return os.getenv("META_CAPI_ENABLED", "0") == "1"


def allowed(c, account_id: int) -> bool:
    row = c.execute("SELECT ads_measurement FROM firebase_preferences WHERE account_id = %s",
                    (account_id,)).fetchone()
    return row is None or row["ads_measurement"] is not False


def value(price_micros: int) -> float:
    return price_micros / 1_000_000


def enqueue(c, account_id: int, event_name: str, event_id: str,
            custom_data: dict | None = None, *, action_source: str = "app",
            web_context: dict | None = None) -> bool:
    if not enabled() or not allowed(c, account_id):
        return False
    row = c.execute(
        """INSERT INTO meta_events (event_id, account_id, event_name, custom_data, action_source, web_context)
           VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (event_id) DO NOTHING RETURNING event_id""",
        (event_id, account_id, event_name, json.dumps(custom_data or {}), action_source,
         json.dumps(web_context) if web_context else None)).fetchone()
    return row is not None


def web_kwargs(web_context: dict | None) -> dict:
    """Argumentos de `enqueue` para un hecho que ocurrió en la web (vacío si fue en la app)."""
    if not web_context:
        return {}
    return {"action_source": "website", "web_context": web_context}


def _minimal_extinfo(platform: str) -> list[str]:
    values = [""] * meta_datos.EXTINFO_LEN
    values[0] = "i2" if platform == "ios" else "a2"
    values[1] = "com.saptain.quantfut"
    return values


def build_web_event(row: dict, account: dict) -> dict:
    """Evento de la web: action_source=website con el contexto del navegador (fbp, fbc, IP, UA, URL)."""
    ctx = row.get("web_context") or {}
    custom = dict(row["custom_data"] or {})
    country = custom.pop("_country", None)
    extra = {k: custom.pop(f"_{k}", None) for k in ("ct", "st", "zp", "ph")}
    user = meta_datos.user_data(account, None, country, extra)
    for src, dst in (("fbp", "fbp"), ("fbc", "fbc"), ("client_ip", "client_ip_address"),
                     ("user_agent", "client_user_agent")):
        if ctx.get(src):
            user[dst] = ctx[src]
    event = {
        "event_name": row["event_name"],
        "event_time": int(row["event_time"].timestamp()),
        "event_id": row["event_id"],
        "action_source": "website",
        "user_data": user,
        "custom_data": custom,
    }
    if ctx.get("source_url"):
        event["event_source_url"] = ctx["source_url"]
    return event


def build_event(row: dict, account: dict, identity: dict | None) -> dict:
    if row.get("action_source") == "website":
        return build_web_event(row, account)
    platform = identity["platform"] if identity else "android"
    tracking = bool(identity and identity["advertiser_tracking_enabled"])
    custom = dict(row["custom_data"] or {})
    country = custom.pop("_country", None)
    return {
        "event_name": row["event_name"],
        "event_time": int(row["event_time"].timestamp()),
        "event_id": row["event_id"],
        "action_source": "app",
        "user_data": meta_datos.user_data(account, identity, country),
        "app_data": {
            "advertiser_tracking_enabled": int(tracking),
            "application_tracking_enabled": 1,
            "extinfo": identity["extinfo"] if identity else _minimal_extinfo(platform),
        },
        "custom_data": custom,
    }


def _post(events: list[dict], client: httpx.Client) -> int:
    body = {"data": events, "access_token": os.environ["META_CAPI_TOKEN"]}
    if os.getenv("META_TEST_EVENT_CODE"):
        body["test_event_code"] = os.environ["META_TEST_EVENT_CODE"]
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{os.environ['META_DATASET_ID']}/events"
    r = client.post(url, json=body, timeout=20)
    r.raise_for_status()
    return int(r.json().get("events_received", 0))


def _alert(text: str) -> None:
    from ..publish import telegram
    telegram.alert(text)


def send_pending(limit: int = 500, client: httpx.Client | None = None) -> dict:
    counts = {"enviados": 0, "omitidos": 0, "fallidos": 0}
    if not enabled():
        return counts
    client = client or httpx.Client()
    with conn() as c:
        rows = c.execute(
            """SELECT e.*, a.email::text AS email, a.display_name
               FROM meta_events e JOIN accounts a USING (account_id)
               WHERE e.status = 'pendiente' ORDER BY e.created_at LIMIT %s
               FOR UPDATE OF e SKIP LOCKED""", (limit,)).fetchall()
        now = datetime.now(timezone.utc)
        batch, ids = [], []
        for row in rows:
            if not allowed(c, row["account_id"]) or now - row["event_time"] > MAX_AGE:
                c.execute("UPDATE meta_events SET status = 'omitido' WHERE event_id = %s",
                          (row["event_id"],))
                counts["omitidos"] += 1
                continue
            identity = None if row["action_source"] == "website" else c.execute(
                """SELECT * FROM meta_identities WHERE account_id = %s
                   ORDER BY updated_at DESC LIMIT 1""", (row["account_id"],)).fetchone()
            batch.append(build_event(row, row, identity))
            ids.append(row["event_id"])
        if not batch:
            return counts
        try:
            _post(batch, client)
        except Exception as exc:  # noqa: BLE001 — se reintenta en la siguiente pasada
            error = str(exc)[:300]
            failed = c.execute(
                """UPDATE meta_events SET attempts = attempts + 1, last_error = %s,
                          status = CASE WHEN attempts + 1 >= %s THEN 'fallido' ELSE 'pendiente' END
                   WHERE event_id = ANY(%s) RETURNING attempts""",
                (error, MAX_ATTEMPTS, ids)).fetchall()
            counts["fallidos"] = len(ids)
            if any(r["attempts"] == ALERT_AT for r in failed):
                _alert(f"Meta CAPI falla {ALERT_AT} veces seguidas: {error}")
            return counts
        c.execute("""UPDATE meta_events SET status = 'enviado', sent_at = now(),
                            attempts = attempts + 1, last_error = NULL
                     WHERE event_id = ANY(%s)""", (ids,))
        counts["enviados"] = len(ids)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("meta_capi: %s", send_pending())
