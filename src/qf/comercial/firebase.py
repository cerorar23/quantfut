"""Firebase identities, never automatic email-based account linking."""
from __future__ import annotations

import os
import threading

from ..db import conn, query_one
from .cuentas import CuentaError, _PUBLIC, normalize_email

CONSENT_VERSION = "2026-10-16"
# La app publicada antes del cambio envia 2026-10-12: se acepta mientras se actualiza
# (spec 2026-10-15). Retirar la anterior cuando la version nueva de la app sea la minima.
ACCEPTED_CONSENT_VERSIONS = frozenset({"2026-10-12", CONSENT_VERSION})
_admin_lock = threading.Lock()


def project_id() -> str:
    value = os.getenv("FIREBASE_PROJECT_ID", "")
    if not value:
        raise CuentaError("firebase_no_configurado", "El acceso con Google todavía no está disponible")
    return value


def admin_app():
    import firebase_admin
    with _admin_lock:
        try:
            return firebase_admin.get_app("quantfut")
        except ValueError:
            return firebase_admin.initialize_app(
                options={"projectId": project_id(), "httpTimeout": 15}, name="quantfut")


def verify_identity(token: str) -> dict:
    if os.getenv("FIREBASE_AUTH_ENABLED", "0") != "1":
        raise CuentaError("firebase_deshabilitado", "El acceso con Google todavía no está disponible")
    from firebase_admin import auth
    try:
        claims = auth.verify_id_token(token, app=admin_app(), check_revoked=True)
    except (auth.InvalidIdTokenError, auth.RevokedIdTokenError, auth.UserDisabledError, ValueError):
        raise CuentaError("firebase_token_invalido", "La sesión caducó. Vuelve a iniciar sesión") from None
    except CuentaError:
        raise
    except Exception:
        raise CuentaError("firebase_no_disponible", "No se pudo comprobar la sesión. Inténtalo de nuevo") from None
    if claims.get("aud") != project_id() or not claims.get("uid"):
        raise CuentaError("firebase_token_invalido", "Sesión no válida")
    return claims


def identity_account(claims: dict) -> dict | None:
    return query_one(
        f"""SELECT {', '.join('a.' + part.strip() for part in _PUBLIC.split(','))}
            FROM firebase_identities f JOIN accounts a USING (account_id)
            WHERE f.project_id = %s AND f.firebase_uid = %s AND a.status = 'active'""",
        (project_id(), claims["uid"]))


def connect_identity(claims: dict, terms_version: str | None,
                     privacy_version: str | None, language: str,
                     existing_account: dict | None = None) -> dict:
    email = normalize_email(claims.get("email", ""))
    if not claims.get("email_verified"):
        raise CuentaError("firebase_correo_no_verificado", "Verifica tu correo antes de continuar")
    uid, project = claims["uid"], project_id()
    provider = claims.get("firebase", {}).get("sign_in_provider", "unknown")
    with conn() as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"firebase:{project}:{uid}",))
        linked = c.execute(
            """SELECT a.* FROM firebase_identities f JOIN accounts a USING (account_id)
               WHERE f.project_id = %s AND f.firebase_uid = %s FOR UPDATE OF a""",
            (project, uid)).fetchone()
        if linked:
            if linked["status"] != "active":
                raise CuentaError("cuenta_suspendida", "Esta cuenta no está disponible")
            if existing_account and existing_account["account_id"] != linked["account_id"]:
                raise CuentaError("firebase_conflicto", "Google ya está vinculado a otra cuenta")
            account_id = linked["account_id"]
        else:
            if terms_version not in ACCEPTED_CONSENT_VERSIONS or privacy_version != terms_version:
                raise CuentaError("consentimiento_requerido", "Acepta los términos y la política de privacidad")
            if existing_account:
                account_id = existing_account["account_id"]
                account = c.execute("SELECT status FROM accounts WHERE account_id = %s FOR UPDATE",
                                    (account_id,)).fetchone()
                if not account or account["status"] != "active":
                    raise CuentaError("cuenta_suspendida", "Esta cuenta no está disponible")
                occupied = c.execute(
                    "SELECT 1 FROM firebase_identities WHERE project_id = %s AND account_id = %s",
                    (project, account_id)).fetchone()
                if occupied:
                    raise CuentaError("firebase_conflicto", "La cuenta ya tiene otra identidad Google")
            else:
                row = c.execute(
                    """INSERT INTO accounts (email, display_name, password_hash, email_verified_at)
                       VALUES (%s, %s, NULL, now()) ON CONFLICT (email) DO NOTHING RETURNING account_id""",
                    (email, (claims.get("name") or "")[:80] or None)).fetchone()
                if not row:
                    raise CuentaError("vinculacion_requerida", "Accede a tu cuenta existente para vincular Google")
                account_id = row["account_id"]
                from . import meta_capi
                meta_capi.enqueue(c, account_id, "CompleteRegistration", f"reg:{account_id}",
                                  {"registration_method": "google"})
            c.execute(
                """INSERT INTO firebase_identities (project_id, firebase_uid, account_id, provider)
                   VALUES (%s, %s, %s, %s)""", (project, uid, account_id, provider))
        if terms_version in ACCEPTED_CONSENT_VERSIONS and privacy_version == terms_version:
            c.execute(
                """INSERT INTO account_consents (account_id, terms_version, privacy_version)
                   VALUES (%s, %s, %s) ON CONFLICT DO NOTHING""",
                (account_id, terms_version, privacy_version))
        c.execute(
            """INSERT INTO firebase_preferences (account_id, language) VALUES (%s, %s)
               ON CONFLICT (account_id) DO UPDATE SET language = EXCLUDED.language, updated_at = now()""",
            (account_id, language))
        c.execute("UPDATE accounts SET last_login_at = now() WHERE account_id = %s", (account_id,))
        return c.execute(f"SELECT {_PUBLIC} FROM accounts WHERE account_id = %s", (account_id,)).fetchone()
