"""Correo transaccional por SMTP: verificación de cuenta y restablecimiento.

Proveedor: Proton Mail (decisión del usuario, 2026-10-07). Dos formas, el
código es el mismo y solo cambia la configuración:

- Envío SMTP de Proton (recomendado): `smtp.protonmail.ch:587`, STARTTLS,
  usuario = la dirección del dominio propio, contraseña = un token SMTP
  (Ajustes → IMAP/SMTP → Tokens SMTP). Exige plan de pago y dominio propio
  verificado en Proton.
- Proton Mail Bridge en Docker (servicio `protonmail-bridge` de
  docker-compose.yml, perfil `proton-bridge`): `protonmail-bridge:25`,
  STARTTLS con certificado autofirmado (`SMTP_TLS_VERIFY=0`, solo dentro de
  la red de Compose). Sirve con una dirección @proton.me.

Proton no está pensado para envíos masivos y limita por reputación de la
cuenta: aquí solo salen correos uno a uno disparados por el propio cliente.
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from . import cuentas

_log = logging.getLogger(__name__)


class CorreoNoConfigurado(RuntimeError):
    pass


def _cfg() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "user": os.getenv("SMTP_USERNAME", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("SMTP_FROM", ""),
        "from_name": os.getenv("SMTP_FROM_NAME", "QuantFut"),
        "security": os.getenv("SMTP_SECURITY", "starttls"),   # starttls | ssl
        "verify": os.getenv("SMTP_TLS_VERIFY", "1") not in ("0", "false", "False"),
    }


def configurado() -> bool:
    c = _cfg()
    return bool(c["host"] and c["from"])


def base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL") or f"https://{os.getenv('DOMAIN', 'localhost')}"


def send(to: str, subject: str, text: str) -> None:
    """Texto plano a propósito: llega mejor a la bandeja de entrada y no
    necesita plantillas HTML que mantener."""
    c = _cfg()
    if not configurado():
        raise CorreoNoConfigurado("Falta SMTP_HOST o SMTP_FROM")
    if c["security"] not in ("starttls", "ssl"):
        raise CorreoNoConfigurado("SMTP_SECURITY debe ser starttls o ssl")
    msg = EmailMessage()
    msg["From"] = formataddr((c["from_name"], c["from"]))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=c["from"].rpartition("@")[2] or None)
    msg.set_content(text)

    ctx = ssl.create_default_context()
    if not c["verify"]:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    if c["security"] == "ssl":
        smtp = smtplib.SMTP_SSL(c["host"], c["port"], timeout=20, context=ctx)
    else:
        smtp = smtplib.SMTP(c["host"], c["port"], timeout=20)
    with smtp:
        if c["security"] == "starttls":
            # Sin STARTTLS no se manda nada: la contraseña no viaja en claro.
            smtp.starttls(context=ctx)
        if c["user"]:
            smtp.login(c["user"], c["password"])
        smtp.send_message(msg)


def send_safely(to: str, subject: str, text: str) -> bool:
    """Para tareas en segundo plano: un fallo de SMTP queda en el log y no
    cambia la respuesta al cliente (que no debe delatar si la cuenta existe)."""
    try:
        send(to, subject, text)
        return True
    except Exception:  # noqa: BLE001
        _log.exception("No se pudo enviar el correo '%s'", subject)
        return False


# --- Mensajes ----------------------------------------------------------------

def verification_message(token: str, horas: int) -> tuple[str, str]:
    url = f"{base_url()}/cuenta/verificar?token={token}"
    return ("Confirma tu correo en QuantFut", f"""Hola:

Para confirmar este correo en tu cuenta de QuantFut, abre este enlace:

{url}

El enlace caduca en {horas} horas y solo sirve una vez. Si no creaste una
cuenta, ignora este mensaje.

QuantFut
""")


def reset_message(token: str, minutos: int) -> tuple[str, str]:
    url = f"{base_url()}/cuenta/restablecer?token={token}"
    return ("Restablece tu contraseña de QuantFut", f"""Hola:

Alguien pidió restablecer la contraseña de tu cuenta de QuantFut. Si fuiste
tú, abre este enlace y elige una nueva:

{url}

El enlace caduca en {minutos} minutos y solo sirve una vez. Al cambiarla se
cierran todas tus sesiones abiertas. Si no lo pediste, ignora este mensaje:
tu contraseña no cambia.

QuantFut
""")


def enviar_verificacion(account_id: int, email: str) -> bool:
    """Emite el enlace y lo envía. Sin SMTP configurado no emite nada."""
    if not configurado():
        return False
    subject, text = verification_message(
        cuentas.issue_email_token(account_id, "verify"), cuentas.VERIFY_TTL_HOURS)
    return send_safely(email, subject, text)


def enviar_restablecimiento(account_id: int, email: str) -> bool:
    if not configurado():
        return False
    subject, text = reset_message(
        cuentas.issue_email_token(account_id, "reset"), cuentas.RESET_TTL_MINUTES)
    return send_safely(email, subject, text)
