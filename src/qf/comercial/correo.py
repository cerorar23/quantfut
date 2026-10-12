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

IDIOMAS = ("es", "en", "pt", "fr", "it", "de")

# {url} y {n} se rellenan al enviar. Regla del proyecto: todo texto visible va en los 6 idiomas.
_VERIFICACION = {
    "es": ("Confirma tu correo en QuantFut", """Hola:

Para confirmar este correo en tu cuenta de QuantFut, abre este enlace:

{url}

El enlace caduca en {n} horas y solo sirve una vez. Si no creaste una
cuenta, ignora este mensaje.

QuantFut
"""),
    "en": ("Confirm your email for QuantFut", """Hello,

To confirm this email address on your QuantFut account, open this link:

{url}

The link expires in {n} hours and can only be used once. If you did not
create an account, ignore this message.

QuantFut
"""),
    "pt": ("Confirme seu e-mail na QuantFut", """Olá,

Para confirmar este e-mail na sua conta da QuantFut, abra este link:

{url}

O link expira em {n} horas e só pode ser usado uma vez. Se você não criou
uma conta, ignore esta mensagem.

QuantFut
"""),
    "fr": ("Confirmez votre e-mail sur QuantFut", """Bonjour,

Pour confirmer cette adresse e-mail sur votre compte QuantFut, ouvrez ce lien :

{url}

Le lien expire dans {n} heures et ne peut être utilisé qu'une seule fois.
Si vous n'avez pas créé de compte, ignorez ce message.

QuantFut
"""),
    "it": ("Conferma la tua email su QuantFut", """Ciao,

Per confermare questo indirizzo email sul tuo account QuantFut, apri questo link:

{url}

Il link scade tra {n} ore e può essere usato una sola volta. Se non hai
creato un account, ignora questo messaggio.

QuantFut
"""),
    "de": ("Bestätige deine E-Mail bei QuantFut", """Hallo,

um diese E-Mail-Adresse in deinem QuantFut-Konto zu bestätigen, öffne diesen Link:

{url}

Der Link läuft in {n} Stunden ab und kann nur einmal verwendet werden. Wenn
du kein Konto erstellt hast, ignoriere diese Nachricht.

QuantFut
"""),
}

_RESTABLECIMIENTO = {
    "es": ("Restablece tu contraseña de QuantFut", """Hola:

Alguien pidió restablecer la contraseña de tu cuenta de QuantFut. Si fuiste
tú, abre este enlace y elige una nueva:

{url}

El enlace caduca en {n} minutos y solo sirve una vez. Al cambiarla se
cierran todas tus sesiones abiertas. Si no lo pediste, ignora este mensaje:
tu contraseña no cambia.

QuantFut
"""),
    "en": ("Reset your QuantFut password", """Hello,

Someone asked to reset the password of your QuantFut account. If it was
you, open this link and choose a new one:

{url}

The link expires in {n} minutes and can only be used once. Changing the
password signs you out of all open sessions. If you did not ask for this,
ignore this message: your password does not change.

QuantFut
"""),
    "pt": ("Redefina sua senha da QuantFut", """Olá,

Alguém pediu para redefinir a senha da sua conta da QuantFut. Se foi você,
abra este link e escolha uma nova:

{url}

O link expira em {n} minutos e só pode ser usado uma vez. Ao alterá-la, todas
as suas sessões abertas são encerradas. Se você não pediu isso, ignore esta
mensagem: sua senha não muda.

QuantFut
"""),
    "fr": ("Réinitialisez votre mot de passe QuantFut", """Bonjour,

Quelqu'un a demandé la réinitialisation du mot de passe de votre compte
QuantFut. Si c'était vous, ouvrez ce lien et choisissez-en un nouveau :

{url}

Le lien expire dans {n} minutes et ne peut être utilisé qu'une seule fois.
Le changement déconnecte toutes vos sessions ouvertes. Si vous n'êtes pas à
l'origine de cette demande, ignorez ce message : votre mot de passe ne change pas.

QuantFut
"""),
    "it": ("Reimposta la tua password di QuantFut", """Ciao,

Qualcuno ha chiesto di reimpostare la password del tuo account QuantFut. Se
sei stato tu, apri questo link e scegline una nuova:

{url}

Il link scade tra {n} minuti e può essere usato una sola volta. Cambiandola,
tutte le tue sessioni aperte vengono chiuse. Se non l'hai chiesto tu, ignora
questo messaggio: la tua password non cambia.

QuantFut
"""),
    "de": ("Setze dein QuantFut-Passwort zurück", """Hallo,

jemand hat darum gebeten, das Passwort deines QuantFut-Kontos zurückzusetzen.
Falls du das warst, öffne diesen Link und wähle ein neues:

{url}

Der Link läuft in {n} Minuten ab und kann nur einmal verwendet werden. Beim
Ändern werden alle offenen Sitzungen beendet. Falls du das nicht angefordert
hast, ignoriere diese Nachricht: Dein Passwort bleibt unverändert.

QuantFut
"""),
}


def _render(plantillas: dict, lang: str, url: str, n: int) -> tuple[str, str]:
    asunto, cuerpo = plantillas.get(lang) or plantillas["es"]
    return asunto, cuerpo.format(url=url, n=n)


def verification_message(token: str, horas: int, lang: str = "es") -> tuple[str, str]:
    return _render(_VERIFICACION, lang, f"{base_url()}/cuenta/verificar?token={token}", horas)


def reset_message(token: str, minutos: int, lang: str = "es") -> tuple[str, str]:
    return _render(_RESTABLECIMIENTO, lang, f"{base_url()}/cuenta/restablecer?token={token}", minutos)


def enviar_verificacion(account_id: int, email: str, lang: str = "es") -> bool:
    """Emite el enlace y lo envía. Sin SMTP configurado no emite nada."""
    if not configurado():
        return False
    subject, text = verification_message(
        cuentas.issue_email_token(account_id, "verify"), cuentas.VERIFY_TTL_HOURS, lang)
    return send_safely(email, subject, text)


def enviar_restablecimiento(account_id: int, email: str, lang: str = "es") -> bool:
    if not configurado():
        return False
    subject, text = reset_message(
        cuentas.issue_email_token(account_id, "reset"), cuentas.RESET_TTL_MINUTES, lang)
    return send_safely(email, subject, text)
