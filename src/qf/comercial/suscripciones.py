"""Planes y suscripciones. El derecho Plus se deriva SIEMPRE de aquí, en el
servidor: ni la app ni la web lo deciden."""
from __future__ import annotations

from datetime import timezone

from ..db import conn, query, query_one
from .auditoria import audit
from .cuentas import CuentaError

_VIGENTE = ("s.revoked_at IS NULL AND s.starts_at <= now() "
            "AND (s.ends_at IS NULL OR s.ends_at > now())")


def plans(only_active: bool = False) -> list[dict]:
    return query(
        """SELECT plan_code, name, duration_days, price_cents, currency, active, sort_order,
                  play_product_id, play_base_plan_id, apple_product_id
           FROM plans WHERE active OR NOT %s ORDER BY sort_order, plan_code""", (only_active,))


def active_subscription(account_id: int) -> dict | None:
    """La que da el acceso más largo, si hay alguna vigente."""
    return query_one(
        f"""SELECT s.subscription_id, s.plan_code, p.name AS plan_name, s.starts_at, s.ends_at, s.source
            FROM subscriptions s JOIN plans p USING (plan_code)
            WHERE s.account_id = %s AND {_VIGENTE}
            ORDER BY s.ends_at DESC NULLS FIRST LIMIT 1""", (account_id,))


def history(account_id: int) -> list[dict]:
    return query(
        """SELECT s.*, p.name AS plan_name,
                  (s.revoked_at IS NULL AND s.starts_at <= now()
                   AND (s.ends_at IS NULL OR s.ends_at > now())) AS vigente
           FROM subscriptions s JOIN plans p USING (plan_code)
           WHERE s.account_id = %s ORDER BY s.created_at DESC""", (account_id,))


def grant(account_id: int, plan_code: str, actor: str, *, source: str = "manual",
          price_cents: int = 0, currency: str = "USD", note: str | None = None) -> dict:
    """Concede un plan. Si ya hay acceso vigente, el nuevo periodo empieza
    cuando acaba el último: renovar antes de tiempo no hace perder días."""
    with conn() as c:
        # Bloquear la cuenta serializa dos concesiones simultáneas: sin esto,
        # las dos verían el mismo final y se solaparían.
        if c.execute("SELECT 1 FROM accounts WHERE account_id = %s FOR UPDATE",
                     (account_id,)).fetchone() is None:
            raise CuentaError("cuenta_inexistente", "La cuenta no existe")
        plan = c.execute("SELECT plan_code, name, duration_days FROM plans WHERE plan_code = %s",
                         (plan_code,)).fetchone()
        if plan is None:
            raise CuentaError("plan_inexistente", "El plan no existe")
        cur = c.execute(
            f"""SELECT bool_or(s.ends_at IS NULL) AS de_por_vida,
                       greatest(now(), max(s.ends_at)) AS base
                FROM subscriptions s WHERE s.account_id = %s AND {_VIGENTE}""",
            (account_id,)).fetchone()
        if cur["de_por_vida"]:
            raise CuentaError("ya_de_por_vida", "La cuenta ya tiene acceso de por vida")
        days = plan["duration_days"]
        # De por vida empieza ya; un periodo, al final del acceso vigente.
        starts = cur["base"] if days else None
        row = c.execute(
            """INSERT INTO subscriptions (account_id, plan_code, starts_at, ends_at, source,
                                          price_cents, currency, note, created_by)
               VALUES (%s, %s, coalesce(%s, now()),
                       CASE WHEN %s::int IS NULL THEN NULL
                            ELSE coalesce(%s, now()) + make_interval(days => %s::int) END,
                       %s, %s, %s, %s, %s)
               RETURNING subscription_id, plan_code, starts_at, ends_at""",
            (account_id, plan_code, starts, days, starts, days,
             source, price_cents, currency, (note or "").strip()[:300] or None, actor),
        ).fetchone()
        audit(c, actor, "suscripcion.conceder", account_id,
              {"subscription_id": row["subscription_id"], "plan": plan_code, "source": source,
               "ends_at": row["ends_at"].astimezone(timezone.utc).isoformat() if row["ends_at"] else None})
    return row


def grant_store(c, account_id: int, plan_code: str, starts_at, ends_at, *, price_cents: int,
                currency: str, note: str, actor: str = "tienda") -> dict:
    """Periodo cobrado por una tienda: fechas reales de la tienda, en la transacción
    del cobro (la llama tiendas.compras, que ya bloqueó la suscripción)."""
    row = c.execute(
        """INSERT INTO subscriptions (account_id, plan_code, starts_at, ends_at, source,
                                      price_cents, currency, note, created_by)
           VALUES (%s, %s, %s, %s, 'payment', %s, %s, %s, %s)
           RETURNING subscription_id, plan_code, starts_at, ends_at""",
        (account_id, plan_code, starts_at, ends_at, price_cents, currency, note[:300], actor)).fetchone()
    audit(c, actor, "suscripcion.conceder", account_id,
          {"subscription_id": row["subscription_id"], "plan": plan_code, "source": "payment",
           "ends_at": row["ends_at"].astimezone(timezone.utc).isoformat()})
    return row


def revoke_in(c, subscription_id: int, actor: str, reason: str) -> dict | None:
    reason = (reason or "").strip()[:300]
    if not reason:
        raise CuentaError("motivo_requerido", "Indica el motivo de la revocación")
    row = c.execute(
        """UPDATE subscriptions SET revoked_at = now(), revoked_by = %s, revoke_reason = %s
           WHERE subscription_id = %s AND revoked_at IS NULL
           RETURNING subscription_id, account_id, plan_code""",
        (actor, reason, subscription_id)).fetchone()
    if row:
        audit(c, actor, "suscripcion.revocar", row["account_id"],
              {"subscription_id": subscription_id, "motivo": reason})
    return row


def revoke(subscription_id: int, actor: str, reason: str) -> dict | None:
    with conn() as c:
        return revoke_in(c, subscription_id, actor, reason)


def update_plan(plan_code: str, actor: str, *, active: bool, price_cents: int) -> bool:
    if price_cents < 0:
        raise CuentaError("precio_invalido", "El precio no puede ser negativo")
    with conn() as c:
        before = c.execute("SELECT active, price_cents FROM plans WHERE plan_code = %s FOR UPDATE",
                           (plan_code,)).fetchone()
        if before is None:
            return False
        c.execute("UPDATE plans SET active = %s, price_cents = %s WHERE plan_code = %s",
                  (active, price_cents, plan_code))
        audit(c, actor, "plan.editar", None,
              {"plan": plan_code, "antes": before, "despues": {"active": active,
                                                               "price_cents": price_cents}})
    return True
