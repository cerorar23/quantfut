"""Cifras del dashboard del panel. Solo lectura."""
from __future__ import annotations

from ..db import query, query_one


def cuentas() -> dict:
    return query_one(
        """SELECT count(*) AS total,
                  count(*) FILTER (WHERE status = 'active') AS activas,
                  count(*) FILTER (WHERE status = 'suspended') AS suspendidas,
                  count(*) FILTER (WHERE email_verified_at IS NULL) AS sin_verificar,
                  count(*) FILTER (WHERE created_at > now() - interval '7 days') AS nuevas_7d,
                  count(*) FILTER (WHERE last_login_at > now() - interval '30 days') AS activas_30d
           FROM accounts""")


def suscripciones() -> dict:
    return query_one(
        """WITH vig AS (
               SELECT * FROM subscriptions
               WHERE revoked_at IS NULL AND starts_at <= now()
                 AND (ends_at IS NULL OR ends_at > now()))
           SELECT (SELECT count(DISTINCT account_id) FROM vig) AS con_plus,
                  (SELECT count(DISTINCT account_id) FROM vig WHERE ends_at IS NULL) AS de_por_vida,
                  (SELECT count(DISTINCT v.account_id) FROM vig v
                   WHERE v.ends_at < now() + interval '7 days'
                     AND NOT EXISTS (SELECT 1 FROM subscriptions s
                                     WHERE s.account_id = v.account_id AND s.revoked_at IS NULL
                                       AND (s.ends_at IS NULL OR s.ends_at > now() + interval '7 days')))
                      AS vencen_7d,
                  (SELECT count(*) FROM subscriptions WHERE created_at > now() - interval '30 days')
                      AS concedidas_30d,
                  (SELECT count(*) FROM sessions WHERE revoked_at IS NULL AND expires_at > now())
                      AS sesiones_abiertas""")


def ingresos_30d() -> list[dict]:
    """Solo lo cobrado por procesador: una concesión manual no es un ingreso."""
    return query(
        """SELECT currency, sum(price_cents) AS cents, count(*) AS n
           FROM subscriptions
           WHERE source = 'payment' AND revoked_at IS NULL
             AND created_at > now() - interval '30 days'
           GROUP BY currency ORDER BY currency""")


def serie_diaria(dias: int = 30, *, periodo: str = "30d") -> list[dict]:
    """Altas por día: últimos N días, mes actual o semana desde el lunes."""
    return query(
        """SELECT d::date AS dia,
                  (SELECT count(*) FROM accounts a WHERE a.created_at::date = d::date) AS altas,
                  (SELECT count(*) FROM subscriptions s WHERE s.created_at::date = d::date) AS suscripciones
           FROM generate_series(
               CASE %s
                 WHEN 'mes' THEN date_trunc('month', current_date)::date
                 WHEN 'semana' THEN date_trunc('week', current_date)::date
                 ELSE current_date - (%s - 1)
               END, current_date, interval '1 day') AS d
           ORDER BY d""", (periodo, dias))


def operacion() -> dict:
    """Lo que antes había que buscar en el JSON de /control/sistema."""
    return query_one(
        """SELECT
             (SELECT count(*) FROM picks p JOIN matches m USING (match_id)
              LEFT JOIN pick_results r USING (pick_id)
              WHERE r.pick_id IS NULL AND m.kickoff_utc < now()) AS picks_sin_liquidar,
             (SELECT count(*) FROM picks p JOIN matches m USING (match_id)
              WHERE m.kickoff_utc > now()) AS picks_proximos,
             (SELECT count(*) FROM unresolved_names WHERE NOT resolved) AS nombres_sin_resolver,
             (SELECT count(*) FROM matches WHERE status = 'scheduled'
                AND kickoff_utc BETWEEN now() AND now() + interval '48 hours') AS partidos_48h,
             (SELECT model_version FROM model_artifacts WHERE is_active LIMIT 1) AS modelo_activo,
             (SELECT json_build_object('ok', ok, 'run_at', run_at)
              FROM health_runs ORDER BY run_at DESC LIMIT 1) AS ultima_salud""")


# --- Listados del panel ------------------------------------------------------

_FILTROS_CUENTAS = {
    "todas": "TRUE",
    "activas": "a.status = 'active'",
    "suspendidas": "a.status = 'suspended'",
    "sin_verificar": "a.email_verified_at IS NULL",
    "plus": "v.ends_at IS NOT NULL OR v.de_por_vida",
    "sin_plus": "v.account_id IS NULL",
}

# Acceso vigente por cuenta: fin del último periodo vigente o de por vida.
_VIGENCIA = """
    LEFT JOIN (
        SELECT account_id, max(ends_at) AS ends_at, bool_or(ends_at IS NULL) AS de_por_vida
        FROM subscriptions
        WHERE revoked_at IS NULL AND starts_at <= now() AND (ends_at IS NULL OR ends_at > now())
        GROUP BY account_id) v ON v.account_id = a.account_id"""


def lista_cuentas(q: str = "", filtro: str = "todas", page: int = 1, per_page: int = 50) -> dict:
    where = _FILTROS_CUENTAS.get(filtro, "TRUE")
    patron = f"%{q.strip()}%" if q.strip() else None
    params = (patron, patron, patron)
    base = f"""FROM accounts a {_VIGENCIA}
               WHERE ({where})
                 AND (%s::text IS NULL OR a.email ILIKE %s OR a.display_name ILIKE %s)"""
    total = query_one(f"SELECT count(*) AS n {base}", params)["n"]
    rows = query(
        f"""SELECT a.account_id, a.email::text AS email, a.display_name, a.status,
                   a.email_verified_at, a.created_at, a.last_login_at,
                   v.ends_at AS plus_hasta, coalesce(v.de_por_vida, false) AS de_por_vida
            {base} ORDER BY a.created_at DESC LIMIT %s OFFSET %s""",
        (*params, per_page, (max(page, 1) - 1) * per_page))
    return {"rows": rows, "total": total, "page": max(page, 1),
            "pages": max(1, -(-total // per_page))}


def cuenta(account_id: int) -> dict | None:
    return query_one(
        f"""SELECT a.account_id, a.email::text AS email, a.display_name, a.status,
                   a.email_verified_at, a.created_at, a.last_login_at,
                   v.ends_at AS plus_hasta, coalesce(v.de_por_vida, false) AS de_por_vida
            FROM accounts a {_VIGENCIA} WHERE a.account_id = %s""", (account_id,))


def sesiones(account_id: int, limit: int = 20) -> list[dict]:
    return query(
        """SELECT session_id, created_at, last_used_at, expires_at, revoked_at, revoke_reason,
                  user_agent, ip, (revoked_at IS NULL AND expires_at > now()) AS abierta
           FROM sessions WHERE account_id = %s ORDER BY last_used_at DESC LIMIT %s""",
        (account_id, limit))


_FILTROS_SUBS = {
    "vigentes": "s.revoked_at IS NULL AND s.starts_at <= now() AND (s.ends_at IS NULL OR s.ends_at > now())",
    "vencen_7d": "s.revoked_at IS NULL AND s.ends_at BETWEEN now() AND now() + interval '7 days'",
    "futuras": "s.revoked_at IS NULL AND s.starts_at > now()",
    "revocadas": "s.revoked_at IS NOT NULL",
    "todas": "TRUE",
}


def lista_suscripciones(filtro: str = "vigentes", page: int = 1, per_page: int = 50) -> dict:
    where = _FILTROS_SUBS.get(filtro, _FILTROS_SUBS["vigentes"])
    total = query_one(f"SELECT count(*) AS n FROM subscriptions s WHERE {where}")["n"]
    rows = query(
        f"""SELECT s.subscription_id, s.account_id, a.email::text AS email, s.plan_code,
                   p.name AS plan_name, s.starts_at, s.ends_at, s.source, s.price_cents,
                   s.currency, s.created_by, s.created_at, s.revoked_at, s.revoke_reason
            FROM subscriptions s JOIN accounts a USING (account_id) JOIN plans p USING (plan_code)
            WHERE {where} ORDER BY s.created_at DESC LIMIT %s OFFSET %s""",
        (per_page, (max(page, 1) - 1) * per_page))
    return {"rows": rows, "total": total, "page": max(page, 1),
            "pages": max(1, -(-total // per_page))}


def auditoria(account_id: int | None = None, limit: int = 200) -> list[dict]:
    return query(
        """SELECT x.audit_id, x.at, x.actor, x.action, x.account_id, a.email::text AS email, x.detail
           FROM admin_audit x LEFT JOIN accounts a USING (account_id)
           WHERE %s::bigint IS NULL OR x.account_id = %s
           ORDER BY x.at DESC LIMIT %s""", (account_id, account_id, limit))


def ultimas_cuentas(limit: int = 8) -> list[dict]:
    return query(
        """SELECT account_id, email::text AS email, display_name, status, created_at
           FROM accounts ORDER BY created_at DESC LIMIT %s""", (limit,))
