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
# Un evento de app espera este tiempo a que la app registre su dispositivo (POST /app/v1/meta/dispositivo).
DEVICE_WAIT = timedelta(minutes=15)


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
    # Única puerta del consentimiento web: quien rechazó la medición (o no la aceptó donde se exige)
    # no sale hacia Meta por ningún camino, ni siquiera con el correo cifrado. Ver meta_consent.py.
    if web_context is not None and web_context.get("ads_consent") is False:
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


def build_web_event(row: dict, account: dict) -> dict:
    """Evento de la web: action_source=website con el contexto del navegador (fbp, fbc, IP, UA, URL).

    Meta exige `client_user_agent` en los eventos `website`. Un cobro que llega sin navegador (una
    renovación, un pago sin checkout guardado) lo generó el sistema: va como `system_generated`."""
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
        "action_source": "website" if ctx.get("user_agent") else "system_generated",
        "user_data": user,
        "custom_data": custom,
    }
    if ctx.get("source_url"):
        event["event_source_url"] = ctx["source_url"]
    return event


def build_event(row: dict, account: dict, identity: dict | None) -> dict:
    if row.get("action_source") == "website":
        return build_web_event(row, account)
    custom = dict(row["custom_data"] or {})
    country = custom.pop("_country", None)
    if identity is None:
        # Sin dispositivo registrado no hay `extinfo` real, y Meta lo exige en los eventos de app. No se
        # inventa: el evento sale como `other`, emparejado por correo, nombre y external_id.
        return {
            "event_name": row["event_name"],
            "event_time": int(row["event_time"].timestamp()),
            "event_id": row["event_id"],
            "action_source": "other",
            "user_data": meta_datos.user_data(account, None, country),
            "custom_data": custom,
        }
    return {
        "event_name": row["event_name"],
        "event_time": int(row["event_time"].timestamp()),
        "event_id": row["event_id"],
        "action_source": "app",
        "user_data": meta_datos.user_data(account, identity, country),
        "app_data": {
            "advertiser_tracking_enabled": int(bool(identity["advertiser_tracking_enabled"])),
            "application_tracking_enabled": 1,
            "extinfo": identity["extinfo"],
        },
        "custom_data": custom,
    }


def _post(events: list[dict], client: httpx.Client) -> int:
    body = {"data": events, "access_token": os.environ["META_CAPI_TOKEN"]}
    if os.getenv("META_TEST_EVENT_CODE"):
        body["test_event_code"] = os.environ["META_TEST_EVENT_CODE"]
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{os.environ['META_DATASET_ID']}/events"
    r = client.post(url, json=body, timeout=20)
    if r.status_code >= 400:
        # El cuerpo trae el motivo de Meta (mensaje y subcódigo); no contiene el token.
        raise MetaError(r.status_code, f"HTTP {r.status_code}: {r.text[:260]}")
    return int(r.json().get("events_received", 0))


class MetaError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _send(c, events: list[dict], ids: list[str], client: httpx.Client, counts: dict) -> None:
    """Envía el lote. Meta rechaza el lote entero si un solo evento es inválido (400): en ese caso se
    reenvía de uno en uno para que el evento malo no arrastre a los demás."""
    try:
        _post(events, client)
    except Exception as exc:  # noqa: BLE001 — se reintenta en la siguiente pasada
        if len(events) > 1 and isinstance(exc, MetaError) and exc.status == 400:
            for event, event_id in zip(events, ids):
                _send(c, [event], [event_id], client, counts)
            return
        error = str(exc)[:300]
        failed = c.execute(
            """UPDATE meta_events SET attempts = attempts + 1, last_error = %s,
                      status = CASE WHEN attempts + 1 >= %s THEN 'fallido' ELSE 'pendiente' END
               WHERE event_id = ANY(%s) RETURNING attempts""",
            (error, MAX_ATTEMPTS, ids)).fetchall()
        counts["fallidos"] += len(ids)
        if any(r["attempts"] == ALERT_AT for r in failed):
            _alert(f"Meta CAPI falla {ALERT_AT} veces seguidas: {error}")
        return
    c.execute("""UPDATE meta_events SET status = 'enviado', sent_at = now(),
                        attempts = attempts + 1, last_error = NULL
                 WHERE event_id = ANY(%s)""", (ids,))
    counts["enviados"] += len(ids)


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
            if row["action_source"] == "app" and identity is None and now - row["created_at"] < DEVICE_WAIT:
                continue   # la app aún puede registrar el dispositivo; se envía en una pasada posterior
            batch.append(build_event(row, row, identity))
            ids.append(row["event_id"])
        if batch:
            _send(c, batch, ids, client, counts)
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("meta_capi: %s", send_pending())
