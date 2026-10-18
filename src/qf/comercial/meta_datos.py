"""user_data de Conversions API normalizado y cifrado como pide Meta
(«Customer information parameters»). Puro: sin BD ni red.

Cifrados con SHA-256: em, external_id, fn, ln, country. Sin cifrar: madid, anon_id,
client_ip_address, client_user_agent. No se recoge teléfono: nunca se manda `ph`.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

EXTINFO_LEN = 16
_PUNTUACION = re.compile(r"[^\w\s]", re.UNICODE)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def external_id(account_id: int) -> str:
    return sha256(f"qf:{account_id}")


def _name_part(value: str) -> str:
    value = unicodedata.normalize("NFC", value).lower()
    return _PUNTUACION.sub("", value).strip()


def split_name(display_name: str | None) -> tuple[str | None, str | None]:
    parts = (display_name or "").split(None, 1)
    if not parts:
        return None, None
    first = _name_part(parts[0]) or None
    last = " ".join(_name_part(parts[1]).split()) if len(parts) > 1 else ""
    return first, last or None


def _latin(value: str) -> str:
    """a-z en minúsculas, sin acentos, puntuación ni espacios (ct y st fuera de EE. UU.)."""
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", text)


def norm_city(value: str | None) -> str | None:
    return _latin(value) or None


def norm_state(value: str | None) -> str | None:
    return _latin(value) or None


def norm_zip(value: str | None, country: str | None = None) -> str | None:
    text = re.sub(r"[\s-]", "", (value or "").lower())
    if (country or "").lower() == "us":
        text = text[:5]
    return text or None


def norm_phone(value: str | None) -> str | None:
    """Solo dígitos, sin ceros a la izquierda; debe incluir el código de país (E.164 sin «+»)."""
    digits = re.sub(r"\D", "", value or "").lstrip("0")
    return digits if 7 <= len(digits) <= 15 else None


def user_data(account: dict, identity: dict | None, country: str | None,
              extra: dict | None = None) -> dict:
    out: dict = {"external_id": [external_id(account["account_id"])]}
    email = (account.get("email") or "").strip().lower()
    if "@" in email:
        out["em"] = [sha256(email)]
    first, last = split_name(account.get("display_name"))
    if first:
        out["fn"] = [sha256(first)]
    if last:
        out["ln"] = [sha256(last)]
    if country and re.fullmatch(r"[A-Za-z]{2}", country):
        out["country"] = [sha256(country.lower())]
    # Datos de facturación del comprador (Whop): ciudad, estado, código postal y teléfono.
    extra = extra or {}
    for key, value in (("ct", norm_city(extra.get("ct"))), ("st", norm_state(extra.get("st"))),
                       ("zp", norm_zip(extra.get("zp"), country)), ("ph", norm_phone(extra.get("ph")))):
        if value:
            out[key] = [sha256(value)]
    if identity:
        out["anon_id"] = identity["anon_id"]
        for src, dst in (("madid", "madid"), ("client_ip", "client_ip_address"),
                         ("user_agent", "client_user_agent")):
            if identity.get(src):
                out[dst] = identity[src]
    return out


def valid_extinfo(values: list[str], platform: str) -> list[str]:
    if len(values) != EXTINFO_LEN:
        raise ValueError("extinfo debe tener 16 posiciones")
    if values[0] != {"android": "a2", "ios": "i2"}[platform]:
        raise ValueError("extinfo[0] no corresponde a la plataforma")
    if any(not isinstance(v, str) or len(v) > 100 for v in values):
        raise ValueError("extinfo con valores no válidos")
    return values
