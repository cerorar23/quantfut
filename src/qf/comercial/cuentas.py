"""Cuentas y sesiones de clientes.

Dos tokens opacos, ninguno firmado por el cliente:
- acceso (15 min): solo vive en Redis como sha256 → session_id. Cada
  petición comprueba además en Postgres que la sesión y la cuenta siguen
  activas, así que suspender o cerrar sesiones corta en el acto.
- refresh (30 días): solo su sha256 en `sessions`. Se rota en cada uso; si
  un refresh ya rotado vuelve a aparecer, alguien lo copió y se revoca la
  sesión entera.
"""
from __future__ import annotations

import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from ..db import conn, query_one
from .auditoria import audit

ACCESS_TTL_SECONDS = 15 * 60
REFRESH_TTL_DAYS = 30
PASSWORD_MIN, PASSWORD_MAX = 10, 128

_ph = PasswordHasher()
# Mismo coste cuando el correo no existe: sin esto, el tiempo de respuesta
# dice qué correos tienen cuenta.
_DUMMY_HASH = _ph.hash(secrets.token_hex(16))
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s.]{2,}$")


class CuentaError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_email(email: str) -> str:
    email = (email or "").strip()
    if len(email) > 254 or not _EMAIL.match(email):
        raise CuentaError("email_invalido", "Correo no válido")
    return email


def validate_password(password: str) -> None:
    if not PASSWORD_MIN <= len(password or "") <= PASSWORD_MAX:
        raise CuentaError("password_invalida",
                          f"La contraseña debe tener entre {PASSWORD_MIN} y {PASSWORD_MAX} caracteres")


def _hash(token: str) -> bytes:
    return hashlib.sha256(token.encode()).digest()


def _access_key(token: str) -> str:
    return f"qf:acc:{_hash(token).hex()}"


_PUBLIC = ("account_id, email::text AS email, display_name, status, email_verified_at, created_at, "
           "store_account_token::text AS store_account_token")


def create_account(email: str, password: str, display_name: str | None = None,
                   web_context: dict | None = None) -> dict:
    email = normalize_email(email)
    validate_password(password)
    name = (display_name or "").strip()[:80] or None
    with conn() as c:
        row = c.execute(
            f"""INSERT INTO accounts (email, password_hash, display_name)
                VALUES (%s, %s, %s) ON CONFLICT (email) DO NOTHING
                RETURNING {_PUBLIC}""",
            (email, _ph.hash(password), name)).fetchone()
        if row is not None:
            from . import meta_capi
            meta_capi.enqueue(c, row["account_id"], "CompleteRegistration",
                              f"reg:{row['account_id']}", {"registration_method": "email"},
                              **meta_capi.web_kwargs(web_context))
    if row is None:
        raise CuentaError("email_en_uso", "Ya existe una cuenta con ese correo")
    return row


def authenticate(email: str, password: str) -> dict | None:
    """La cuenta si la contraseña es correcta (activa o no), si no None."""
    try:
        email = normalize_email(email)
    except CuentaError:
        return None
    row = query_one(f"SELECT {_PUBLIC}, password_hash FROM accounts WHERE email = %s", (email,))
    try:
        _ph.verify((row["password_hash"] if row else None) or _DUMMY_HASH, password or "")
    except (VerificationError, InvalidHashError):
        return None
    if row is None or row["password_hash"] is None:
        return None
    stored = row.pop("password_hash")
    with conn() as c:
        if _ph.check_needs_rehash(stored):
            c.execute("UPDATE accounts SET password_hash = %s WHERE account_id = %s",
                      (_ph.hash(password), row["account_id"]))
        c.execute("UPDATE accounts SET last_login_at = now() WHERE account_id = %s",
                  (row["account_id"],))
    return row


def _issue_access(redis_client, session_id: int) -> str:
    token = secrets.token_urlsafe(32)
    redis_client.setex(_access_key(token), ACCESS_TTL_SECONDS, session_id)
    return token


def _tokens(access: str, refresh: str | None) -> dict:
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer",
            "expires_in": ACCESS_TTL_SECONDS}


def open_session(redis_client, account_id: int, user_agent: str | None, ip: str | None) -> dict:
    refresh = secrets.token_urlsafe(32)
    with conn() as c:
        sid = c.execute(
            """INSERT INTO sessions (account_id, refresh_hash, expires_at, user_agent, ip)
               VALUES (%s, %s, now() + make_interval(days => %s), %s, %s)
               RETURNING session_id""",
            (account_id, _hash(refresh), REFRESH_TTL_DAYS, (user_agent or "")[:300], ip),
        ).fetchone()["session_id"]
    return _tokens(_issue_access(redis_client, sid), refresh)


def rotate_refresh(redis_client, refresh: str, grace_seconds: int = 0) -> dict:
    """`grace_seconds` > 0 solo para la web: dos pestañas que arrancan a la vez
    mandan la misma cookie, y la segunda llega con el refresh que la primera
    acaba de rotar. Dentro de esa ventana se le da un acceso nuevo sin rotar
    (el navegador ya guarda la cookie nueva); fuera de ella, es reuso."""
    old = _hash(refresh or "")
    new = secrets.token_urlsafe(32)
    reused = False
    with conn() as c:
        row = c.execute(
            """SELECT s.session_id, s.revoked_at, s.expires_at > now() AS vigente, a.status
               FROM sessions s JOIN accounts a USING (account_id)
               WHERE s.refresh_hash = %s FOR UPDATE OF s""", (old,)).fetchone()
        if row is None:
            retired = c.execute(
                """SELECT t.session_id,
                          t.retired_at > now() - make_interval(secs => %s) AS en_gracia,
                          s.revoked_at IS NULL AND s.expires_at > now() AND a.status = 'active' AS viva
                   FROM session_retired_tokens t JOIN sessions s USING (session_id)
                   JOIN accounts a USING (account_id)
                   WHERE t.token_hash = %s""", (grace_seconds, old)).fetchone()
            if retired and retired["en_gracia"] and retired["viva"]:
                return _tokens(_issue_access(redis_client, retired["session_id"]), None)
            if retired:
                # El revocado tiene que confirmarse: por eso no se lanza aquí dentro.
                c.execute("""UPDATE sessions SET revoked_at = now(), revoke_reason = 'reuso_refresh'
                             WHERE session_id = %s AND revoked_at IS NULL""",
                          (retired["session_id"],))
                reused = True
        elif row["revoked_at"] is None and row["vigente"] and row["status"] == "active":
            c.execute("INSERT INTO session_retired_tokens (token_hash, session_id) VALUES (%s, %s)",
                      (old, row["session_id"]))
            c.execute("""UPDATE sessions SET refresh_hash = %s, last_used_at = now()
                         WHERE session_id = %s""", (_hash(new), row["session_id"]))
            return _tokens(_issue_access(redis_client, row["session_id"]), new)
    raise CuentaError("refresh_reusado" if reused else "refresh_invalido", "Sesión no válida")


def account_from_access(redis_client, token: str) -> dict | None:
    if not token:
        return None
    sid = redis_client.get(_access_key(token))
    if sid is None:
        return None
    return query_one(
        f"""SELECT {', '.join('a.' + c.strip() for c in _PUBLIC.split(','))}, s.session_id
            FROM sessions s JOIN accounts a USING (account_id)
            WHERE s.session_id = %s AND s.revoked_at IS NULL AND s.expires_at > now()
              AND a.status = 'active'""", (int(sid),))


def logout(redis_client, access_token: str, session_id: int) -> None:
    redis_client.delete(_access_key(access_token))
    with conn() as c:
        c.execute("""UPDATE sessions SET revoked_at = now(), revoke_reason = 'logout'
                     WHERE session_id = %s AND revoked_at IS NULL""", (session_id,))


# --- Acciones del panel. Cada una deja rastro en admin_audit en la misma
# transacción: si la auditoría falla, la acción no ocurre.

def set_status(account_id: int, status: str, actor: str) -> bool:
    if status not in ("active", "suspended"):
        raise CuentaError("estado_invalido", "Estado no válido")
    with conn() as c:
        changed = c.execute("UPDATE accounts SET status = %s WHERE account_id = %s AND status <> %s",
                            (status, account_id, status)).rowcount
        if changed:
            audit(c, actor, f"cuenta.{status}", account_id)
            if status == "suspended":
                _revoke_all(c, account_id, "suspendida")
    return bool(changed)


def mark_email_verified(account_id: int, actor: str) -> bool:
    with conn() as c:
        changed = c.execute("""UPDATE accounts SET email_verified_at = now()
                               WHERE account_id = %s AND email_verified_at IS NULL""",
                            (account_id,)).rowcount
        if changed:
            audit(c, actor, "cuenta.verificar_correo", account_id)
    return bool(changed)


def _revoke_all(c, account_id: int, reason: str) -> int:
    return c.execute("""UPDATE sessions SET revoked_at = now(), revoke_reason = %s
                        WHERE account_id = %s AND revoked_at IS NULL""",
                     (reason, account_id)).rowcount


def revoke_all_sessions(account_id: int, actor: str) -> int:
    with conn() as c:
        n = _revoke_all(c, account_id, "panel")
        audit(c, actor, "cuenta.cerrar_sesiones", account_id, {"sesiones": n})
    return n


# --- Enlaces por correo (db/044) ---------------------------------------------

VERIFY_TTL_HOURS = 48
RESET_TTL_MINUTES = 60


def issue_email_token(account_id: int, purpose: str) -> str:
    if purpose not in ("verify", "reset"):
        raise ValueError(purpose)
    token = secrets.token_urlsafe(32)
    ttl = f"{VERIFY_TTL_HOURS} hours" if purpose == "verify" else f"{RESET_TTL_MINUTES} minutes"
    with conn() as c:
        # Solo vale el último enlace pedido: los anteriores quedan anulados.
        c.execute("""UPDATE email_tokens SET used_at = now()
                     WHERE account_id = %s AND purpose = %s AND used_at IS NULL""",
                  (account_id, purpose))
        c.execute("""INSERT INTO email_tokens (token_hash, account_id, purpose, expires_at)
                     VALUES (%s, %s, %s, now() + %s::interval)""",
                  (_hash(token), account_id, purpose, ttl))
    return token


def email_token_valid(token: str, purpose: str) -> bool:
    """Sin consumirlo: para enseñar el formulario o avisar de que caducó."""
    return query_one(
        """SELECT 1 AS ok FROM email_tokens
           WHERE token_hash = %s AND purpose = %s AND used_at IS NULL AND expires_at > now()""",
        (_hash(token or ""), purpose)) is not None


def _consume(c, token: str, purpose: str) -> int | None:
    row = c.execute(
        """UPDATE email_tokens SET used_at = now()
           WHERE token_hash = %s AND purpose = %s AND used_at IS NULL AND expires_at > now()
           RETURNING account_id""", (_hash(token or ""), purpose)).fetchone()
    return row["account_id"] if row else None


def confirm_email(token: str) -> bool:
    with conn() as c:
        aid = _consume(c, token, "verify")
        if aid is None:
            return False
        c.execute("""UPDATE accounts SET email_verified_at = coalesce(email_verified_at, now())
                     WHERE account_id = %s""", (aid,))
    return True


def account_for_reset(email: str) -> dict | None:
    """Solo cuentas activas: una suspendida no recupera el acceso por correo."""
    try:
        email = normalize_email(email)
    except CuentaError:
        return None
    return query_one(f"SELECT {_PUBLIC} FROM accounts WHERE email = %s AND status = 'active'",
                     (email,))


def reset_password(token: str, new_password: str) -> bool:
    validate_password(new_password)   # antes de consumir: un error no gasta el enlace
    with conn() as c:
        aid = _consume(c, token, "reset")
        if aid is None:
            return False
        c.execute("UPDATE accounts SET password_hash = %s WHERE account_id = %s",
                  (_ph.hash(new_password), aid))
        # Quien tuviera la contraseña vieja pierde también sus sesiones.
        _revoke_all(c, aid, "cambio_password")
    return True
