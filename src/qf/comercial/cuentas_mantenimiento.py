"""Limpieza diaria de sesiones y tokens de correo caducados.

Una sesión caducada o revocada ya no sirve para nada; se conserva un margen para
investigar abusos (p. ej. `reuso_refresh`) y luego se borra, con su IP y
user-agent. Nunca toca cuentas, suscripciones, monedas ni `admin_audit`.

Plazos (decisión 2026-10-12, documentada en docs/legal/OPERACION_PRIVACIDAD.md):
- sesiones: 30 días tras caducar o ser revocadas;
- tokens retirados de refresh: al borrar su sesión o al superar la vida máxima
  del refresh (`REFRESH_TTL_DAYS`): pasado ese tiempo su sesión ya caducó, así
  que la detección de reuso no pierde nada;
- tokens de correo (verificar/restablecer): 7 días tras caducar o usarse.
"""
from ..db import conn
from .cuentas import REFRESH_TTL_DAYS

SESSION_DAYS = 30
EMAIL_TOKEN_DAYS = 7

_SESION_VENCIDA = ("(s.expires_at < now() - make_interval(days => %(s)s) "
                   "OR s.revoked_at < now() - make_interval(days => %(s)s))")


def clean() -> dict[str, int]:
    params = {"s": SESSION_DAYS, "e": EMAIL_TOKEN_DAYS, "r": REFRESH_TTL_DAYS}
    with conn() as c:
        # Orden obligatorio: los tokens retirados dependen de su sesión (FK).
        retired_with_session = c.execute(
            f"""DELETE FROM session_retired_tokens t USING sessions s
                WHERE t.session_id = s.session_id AND {_SESION_VENCIDA}""", params).rowcount
        retired_old = c.execute(
            "DELETE FROM session_retired_tokens WHERE retired_at < now() - make_interval(days => %(r)s)",
            params).rowcount
        sessions = c.execute(
            f"DELETE FROM sessions s WHERE {_SESION_VENCIDA}", params).rowcount
        email = c.execute(
            """DELETE FROM email_tokens
               WHERE expires_at < now() - make_interval(days => %(e)s)
                  OR used_at < now() - make_interval(days => %(e)s)""", params).rowcount
    return {"sessions": sessions, "retired_tokens": retired_with_session + retired_old,
            "email_tokens": email}


if __name__ == "__main__":
    import json
    print(json.dumps(clean()))
