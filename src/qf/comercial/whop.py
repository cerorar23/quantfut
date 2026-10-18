"""Cobro web con Whop: checkout embebido + webhooks (spec 2026-10-18).

El acceso se concede SOLO desde el webhook `payment.succeeded`: el navegador nunca decide.
La `checkout_configuration` la crea el servidor con `metadata` propia, así que quién paga qué
no se puede falsificar desde el cliente.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import httpx

from ..db import conn
from . import meta_capi, suscripciones

log = logging.getLogger(__name__)
API_BASE = os.getenv("WHOP_API_BASE", "https://api.whop.com/api/v1")
TOLERANCE_SECONDS = 300  # Standard Webhooks: se rechaza lo que difiere más de 5 minutos.
ACTOR = "whop"


class WhopError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def enabled() -> bool:
    return bool(os.getenv("WHOP_API_KEY") and os.getenv("WHOP_WEBHOOK_SECRET"))


# --- Firma de webhooks (Standard Webhooks: HMAC-SHA256 de "{id}.{timestamp}.{cuerpo}") -------------

def verify_signature(secret: str, headers: dict, body: bytes, now: float | None = None) -> None:
    """Lanza WhopError si la firma o la marca de tiempo no valen. Cuerpo CRUDO, sin parsear."""
    msg_id = headers.get("webhook-id")
    stamp = headers.get("webhook-timestamp")
    sigs = headers.get("webhook-signature")
    if not (msg_id and stamp and sigs):
        raise WhopError("firma_ausente", "Faltan cabeceras de firma")
    try:
        sent = int(stamp)
    except ValueError:
        raise WhopError("firma_invalida", "Marca de tiempo no válida") from None
    if abs((now if now is not None else time.time()) - sent) > TOLERANCE_SECONDS:
        raise WhopError("firma_caducada", "La entrega está fuera de la ventana de 5 minutos")
    signed = f"{msg_id}.{stamp}.".encode() + body
    # Whop indica usar el secreto `ws_…` tal cual como clave, sin decodificarlo.
    expected = base64.b64encode(hmac.new(secret.encode(), signed, hashlib.sha256).digest()).decode()
    for part in sigs.split():
        version, _, value = part.partition(",")
        if version == "v1" and hmac.compare_digest(value, expected):
            return
    raise WhopError("firma_invalida", "La firma no coincide")


# --- Checkout (lo crea el servidor) ----------------------------------------------------------------

def _headers() -> dict:
    h = {"Authorization": f"Bearer {os.environ['WHOP_API_KEY']}", "Content-Type": "application/json"}
    if os.getenv("WHOP_API_VERSION_DATE"):
        h["Api-Version-Date"] = os.environ["WHOP_API_VERSION_DATE"]
    return h


def checkout_event_id(checkout_id: str) -> str:
    """Mismo event_id en el Pixel (navegador) y en la Conversions API: Meta deduplica por él."""
    return f"purchase:{checkout_id}"


def create_checkout(account: dict, plan_code: str, *, fbp: str | None, fbc: str | None,
                    client_ip: str | None, user_agent: str | None, source_url: str | None,
                    redirect_url: str | None = None, client: httpx.Client | None = None) -> dict:
    if not enabled():
        raise WhopError("pagos_deshabilitados", "Los pagos todavía no están disponibles")
    with conn() as c:
        plan = c.execute("SELECT plan_code, whop_plan_id, active FROM plans WHERE plan_code = %s",
                         (plan_code,)).fetchone()
    if not plan or not plan["active"]:
        raise WhopError("plan_inexistente", "Ese plan no está a la venta")
    if not plan["whop_plan_id"]:
        raise WhopError("plan_sin_whop", "Ese plan todavía no se puede pagar en línea")
    body = {"plan_id": plan["whop_plan_id"],
            "metadata": {"qf_account_id": str(account["account_id"]), "qf_plan_code": plan_code}}
    if os.getenv("WHOP_ACCOUNT_ID"):
        body["account_id"] = os.environ["WHOP_ACCOUNT_ID"]
    if redirect_url:
        body["redirect_url"] = redirect_url
    try:
        r = (client or httpx).post(f"{API_BASE}/checkout_configurations", json=body,
                                   headers=_headers(), timeout=15)
        r.raise_for_status()
        checkout_id = r.json()["id"]
    except Exception:  # noqa: BLE001 — el detalle de Whop no sale al cliente
        log.exception("whop: no se pudo crear la checkout_configuration")
        raise WhopError("whop_no_disponible", "No se pudo preparar el pago. Inténtalo de nuevo") from None
    event_id = checkout_event_id(checkout_id)
    with conn() as c:
        c.execute(
            """INSERT INTO whop_checkouts (checkout_id, account_id, plan_code, event_id, fbp, fbc,
                                           client_ip, user_agent, source_url)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (checkout_id) DO NOTHING""",
            (checkout_id, account["account_id"], plan_code, event_id, fbp, fbc, client_ip,
             user_agent, source_url))
        # InitiateCheckout también por servidor: si el Pixel se pierde (bloqueador, red), Meta lo recupera.
        # Mismo event_id que el que dispara el navegador al crear el pago (`ic:<ch>`).
        ctx = {k: v for k, v in (("fbp", fbp), ("fbc", fbc), ("client_ip", client_ip),
                                 ("user_agent", user_agent), ("source_url", source_url)) if v}
        price = c.execute("SELECT price_cents, currency FROM plans WHERE plan_code = %s", (plan_code,)).fetchone()
        meta_capi.enqueue(c, account["account_id"], "InitiateCheckout", f"ic:{checkout_id}",
                          {"currency": price["currency"], "value": price["price_cents"] / 100,
                           "content_ids": [plan_code], "content_type": "product", "num_items": 1},
                          action_source="website", web_context=ctx or None)
    return {"checkout_id": checkout_id, "event_id": event_id, "initiate_event_id": f"ic:{checkout_id}"}


# --- Webhooks ---------------------------------------------------------------------------------------

def _cents(money) -> int | None:
    try:
        return int((Decimal(str(money["amount"])) * 100).to_integral_value())
    except (TypeError, KeyError, InvalidOperation):
        return None


def _when(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _alert(text: str) -> None:
    from ..publish import telegram
    telegram.alert(text)


def _owner(c, data: dict) -> tuple[int | None, dict | None]:
    """Cuenta dueña del pago: metadata del servidor > checkout guardado > membresía ya conocida."""
    checkout = None
    if data.get("checkout_configuration_id"):
        checkout = c.execute("SELECT * FROM whop_checkouts WHERE checkout_id = %s",
                             (data["checkout_configuration_id"],)).fetchone()
    meta = data.get("metadata") or {}
    account_id = meta.get("qf_account_id")
    if account_id and str(account_id).isdigit():
        row = c.execute("SELECT account_id FROM accounts WHERE account_id = %s", (int(account_id),)).fetchone()
        if row:
            return row["account_id"], checkout
    if checkout:
        return checkout["account_id"], checkout
    if data.get("membership_id"):
        row = c.execute("SELECT account_id FROM whop_payments WHERE membership_id = %s LIMIT 1",
                        (data["membership_id"],)).fetchone()
        if row:
            return row["account_id"], None
    return None, None


def apply_payment(c, data: dict) -> dict:
    payment_id = data.get("id")
    if not payment_id:
        raise WhopError("pago_sin_id", "El pago no trae identificador")
    if data.get("status") not in (None, "paid"):
        return {"estado": "ignorado", "motivo": f"estado {data.get('status')}"}
    c.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"whop:{payment_id}",))
    if c.execute("SELECT 1 FROM whop_payments WHERE payment_id = %s", (payment_id,)).fetchone():
        return {"estado": "duplicado"}
    account_id, checkout = _owner(c, data)
    if account_id is None:
        _alert(f"Whop: pago {payment_id} sin cuenta asociada; revisar a mano")
        return {"estado": "sin_cuenta"}
    plan = c.execute("SELECT plan_code, name, duration_days FROM plans WHERE whop_plan_id = %s",
                     (data.get("plan_id"),)).fetchone()
    if plan is None or not plan["duration_days"]:
        _alert(f"Whop: pago {payment_id} con plan {data.get('plan_id')} sin plan equivalente")
        return {"estado": "plan_desconocido"}
    # Bloquear la cuenta serializa dos concesiones simultáneas (igual que suscripciones.grant).
    c.execute("SELECT 1 FROM accounts WHERE account_id = %s FOR UPDATE", (account_id,))
    paid_at = _when(data.get("paid_at"))
    last_end = c.execute(
        """SELECT max(ends_at) AS fin FROM subscriptions
           WHERE account_id = %s AND revoked_at IS NULL AND ends_at IS NOT NULL""",
        (account_id,)).fetchone()["fin"]
    start = max(paid_at, last_end) if last_end else paid_at
    end = start + timedelta(days=plan["duration_days"])
    amount = _cents(data.get("total")) or 0
    currency = (data.get("currency") or "usd").upper()
    sub = suscripciones.grant_store(c, account_id, plan["plan_code"], start, end,
                                    price_cents=amount, currency=currency,
                                    note=f"whop:{payment_id}", actor=ACTOR)
    previous = c.execute("SELECT 1 FROM whop_payments WHERE membership_id = %s LIMIT 1",
                         (data.get("membership_id"),)).fetchone() if data.get("membership_id") else None
    c.execute(
        """INSERT INTO whop_payments (payment_id, account_id, plan_code, subscription_id, checkout_id,
                                      membership_id, amount_cents, currency, billing_reason)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (payment_id, account_id, plan["plan_code"], sub["subscription_id"],
         data.get("checkout_configuration_id"), data.get("membership_id"), amount, currency,
         data.get("billing_reason")))
    _enqueue_meta(c, account_id, plan["plan_code"], data, checkout, amount, currency, bool(previous))
    return {"estado": "concedido", "account_id": account_id, "ends_at": end}


def _enqueue_meta(c, account_id: int, plan_code: str, data: dict, checkout: dict | None,
                  amount: int, currency: str, is_renewal: bool) -> None:
    ctx = {k: checkout[k] for k in ("fbp", "fbc", "client_ip", "user_agent", "source_url")
           if checkout and checkout.get(k)}
    if data.get("ip_address") and "client_ip" not in ctx:
        ctx["client_ip"] = data["ip_address"]
    billing = data.get("billing_address") or {}
    country = billing.get("country") or None
    custom = {"currency": currency, "value": amount / 100, "content_ids": [plan_code],
              "content_type": "product", "num_items": 1, "_country": country,
              "_ct": billing.get("city"), "_st": billing.get("state"), "_zp": billing.get("postal_code"),
              "_ph": data.get("customer_phone")}
    # Compra inicial: mismo event_id que el Pixel. Renovación: id propio del pago (el navegador no está).
    purchase_id = (checkout["event_id"] if checkout and not is_renewal
                   else f"purchase:{data['id']}")
    meta_capi.enqueue(c, account_id, "Purchase", purchase_id, custom,
                      action_source="website", web_context=ctx or None)
    if not is_renewal:
        meta_capi.enqueue(c, account_id, "Subscribe", f"subscribe:{data['id']}",
                          {**custom, "order_id": data["id"]},
                          action_source="website", web_context=ctx or None)


def apply_membership(c, data: dict, *, deactivated: bool = False) -> dict:
    """Sin acceso → se revocan los periodos futuros cobrados. `membership.deactivated` ya lo dice;
    en `membership.updated` solo cuenta el estado canceled/expired."""
    if not deactivated and data.get("status") not in ("canceled", "expired"):
        return {"estado": "ignorado"}
    rows = c.execute(
        """SELECT p.subscription_id FROM whop_payments p
           JOIN subscriptions s USING (subscription_id)
           WHERE p.membership_id = %s AND s.revoked_at IS NULL AND s.ends_at > now()""",
        (data.get("id"),)).fetchall()
    n = sum(1 for r in rows
            if suscripciones.revoke_in(c, r["subscription_id"], ACTOR, f"whop: membresía {data.get('status') or 'desactivada'}"))
    return {"estado": "revocado", "periodos": n}


def apply_refund(c, data: dict) -> dict:
    """refund.created / refund.updated con estado `succeeded`: se revoca el periodo que dio ese pago."""
    if data.get("status") != "succeeded":
        return {"estado": "ignorado", "motivo": f"estado {data.get('status')}"}
    row = c.execute("SELECT subscription_id FROM whop_payments WHERE payment_id = %s",
                    (data.get("payment_id"),)).fetchone()
    if not row or row["subscription_id"] is None:
        _alert(f"Whop: reembolso {data.get('id')} de un pago desconocido ({data.get('payment_id')})")
        return {"estado": "pago_desconocido"}
    done = suscripciones.revoke_in(c, row["subscription_id"], ACTOR, f"whop: reembolso {data.get('id')}")
    return {"estado": "revocado" if done else "ya_revocado"}


def handle_event(webhook_id: str, event: dict) -> dict:
    """Una sola transacción: si algo falla, el webhook-id no queda registrado y Whop reintenta."""
    etype = event.get("type", "")
    data = event.get("data") or {}
    with conn() as c:
        new = c.execute(
            "INSERT INTO whop_webhooks (webhook_id, event_type) VALUES (%s,%s) ON CONFLICT DO NOTHING RETURNING 1",
            (webhook_id, etype)).fetchone()
        if not new:
            return {"estado": "duplicado"}
        if etype == "payment.succeeded":
            return apply_payment(c, data)
        if etype in ("refund.created", "refund.updated"):
            return apply_refund(c, data)
        if etype in ("membership.updated", "membership.deactivated"):
            return apply_membership(c, data, deactivated=etype == "membership.deactivated")
        return {"estado": "ignorado", "tipo": etype}


def parse(body: bytes) -> dict:
    try:
        event = json.loads(body)
    except ValueError:
        raise WhopError("cuerpo_invalido", "El cuerpo no es JSON") from None
    if not isinstance(event, dict):
        raise WhopError("cuerpo_invalido", "El cuerpo no es un evento")
    return event


__all__ = ["WhopError", "verify_signature", "create_checkout", "handle_event", "parse",
           "enabled", "checkout_event_id"]
