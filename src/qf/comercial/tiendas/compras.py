"""Aplica cobros ya verificados con la tienda. Idempotente por (store, order_id):
la app y la notificación de la tienda pueden llegar en cualquier orden y repetidas."""
from __future__ import annotations

import json

from ...db import conn
from .. import meta_capi, suscripciones
from . import Cobro, TiendaError


def _plan(c, cobro: Cobro) -> str:
    if cobro.store == "google_play":
        row = c.execute("SELECT plan_code FROM plans WHERE play_product_id = %s AND play_base_plan_id = %s",
                        (cobro.product_id, cobro.base_plan_id)).fetchone()
    else:
        row = c.execute("SELECT plan_code FROM plans WHERE apple_product_id = %s",
                        (cobro.product_id,)).fetchone()
    if row is None:
        raise TiendaError("producto_desconocido", "No se reconoce el producto comprado")
    return row["plan_code"]


def _owner(c, cobro: Cobro, account_id: int | None) -> int:
    if not cobro.account_token:
        raise TiendaError("compra_sin_cuenta", "La compra no está asociada a ninguna cuenta")
    row = c.execute("SELECT account_id FROM accounts WHERE store_account_token::text = %s",
                    (cobro.account_token,)).fetchone()
    if row is None:
        raise TiendaError("compra_sin_cuenta", "La compra no está asociada a ninguna cuenta")
    if account_id is not None and row["account_id"] != account_id:
        raise TiendaError("compra_de_otra_cuenta", "Esta compra pertenece a otra cuenta")
    return row["account_id"]


def aplicar(cobro: Cobro, account_id: int | None) -> dict:
    with conn() as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                  (f"tienda:{cobro.store}:{cobro.original_id}",))
        owner = _owner(c, cobro, account_id)
        done = c.execute("SELECT period_end FROM store_transactions WHERE store = %s AND order_id = %s",
                         (cobro.store, cobro.order_id)).fetchone()
        if done:
            return {"estado": "concedido", "ends_at": done["period_end"], "account_id": owner}
        if cobro.state != "activa":
            return {"estado": cobro.state, "ends_at": None, "account_id": owner}
        plan_code = _plan(c, cobro)
        prev = c.execute(
            """SELECT count(*) AS n,
                      max(period_end) FILTER (WHERE period_end < %s) AS last_end
               FROM store_transactions WHERE store = %s AND original_id = %s""",
            (cobro.period_end, cobro.store, cobro.original_id)).fetchone()
        start = max(cobro.period_start, prev["last_end"]) if prev["last_end"] else cobro.period_start
        if cobro.period_end <= start:
            return {"estado": "sin_acceso", "ends_at": None, "account_id": owner}
        price_cents = round(cobro.price_micros / 10_000) if cobro.price_micros is not None else 0
        sub = suscripciones.grant_store(c, owner, plan_code, start, cobro.period_end,
                                        price_cents=price_cents, currency=cobro.currency or "USD",
                                        note=f"{cobro.store}:{cobro.order_id}")
        c.execute(
            """INSERT INTO store_transactions (store, order_id, original_id, account_id, plan_code,
                   product_id, base_plan_id, period_start, period_end, price_micros, currency,
                   region_code, environment, subscription_id, verified_payload)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (cobro.store, cobro.order_id, cobro.original_id, owner, plan_code, cobro.product_id,
             cobro.base_plan_id, start, cobro.period_end, cobro.price_micros, cobro.currency,
             cobro.region_code, cobro.environment, sub["subscription_id"], json.dumps(cobro.payload)))
        if cobro.environment == "production" and cobro.price_micros is not None and cobro.currency:
            custom = {"currency": cobro.currency, "value": meta_capi.value(cobro.price_micros),
                      "content_ids": [plan_code], "content_type": "product", "num_items": 1,
                      "_country": cobro.region_code}
            meta_capi.enqueue(c, owner, "Purchase", f"pur:{cobro.order_id}", custom)
            if prev["n"] == 0:
                meta_capi.enqueue(c, owner, "Subscribe", f"sub:{cobro.order_id}",
                                  {**custom, "order_id": cobro.order_id})
        return {"estado": "concedido", "ends_at": cobro.period_end, "account_id": owner}


def revocar_orden(store: str, order_id: str, motivo: str) -> bool:
    with conn() as c:
        row = c.execute("SELECT subscription_id FROM store_transactions WHERE store = %s AND order_id = %s",
                        (store, order_id)).fetchone()
        if not row or row["subscription_id"] is None:
            return False
        return suscripciones.revoke_in(c, row["subscription_id"], "tienda", motivo) is not None


def revocar_original(store: str, original_id: str, motivo: str) -> int:
    with conn() as c:
        rows = c.execute(
            """SELECT subscription_id FROM store_transactions
               WHERE store = %s AND original_id = %s AND period_end > now()""",
            (store, original_id)).fetchall()
        return sum(1 for r in rows
                   if suscripciones.revoke_in(c, r["subscription_id"], "tienda", motivo))
