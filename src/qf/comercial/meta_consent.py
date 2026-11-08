"""Consentimiento de la medición publicitaria de la web (Pixel de Meta y Conversions API).

Dos regímenes, decididos por el país de la visita:

- ``opt-in``  EEE, Reino Unido, Suiza y país desconocido: nada se mide hasta que la persona acepta.
- ``opt-out`` resto: la medición está activa salvo que la persona la rechace (decisión del titular,
  2026-10-15, ver harness/progreso.md).

En ambos, una señal de privacidad del navegador (Global Privacy Control o Do Not Track) o un
«Rechazar» explícito gana siempre. La decisión viaja en la cookie propia ``qf_ads`` (``si`` | ``no``),
que el navegador escribe y el servidor lee, para que rechazar también corte los eventos de servidor.
"""
from __future__ import annotations

import os

COOKIE = "qf_ads"

# Espacio Económico Europeo (UE 27 + Islandia, Liechtenstein, Noruega), Reino Unido y Suiza.
OPT_IN_COUNTRIES = frozenset(
    "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE "
    "IS LI NO GB CH".split())
# Cloudflare manda XX (sin dato) o T1 (Tor); sin país no se puede afirmar que no sea europeo.
UNKNOWN_COUNTRIES = frozenset({"", "XX", "T1"})


def _extra_opt_in() -> frozenset[str]:
    """Países añadidos por configuración (p. ej. META_OPTIN_EXTRA=BR,CA), sin tocar el código."""
    raw = os.getenv("META_OPTIN_EXTRA", "")
    return frozenset(code.strip().upper() for code in raw.split(",") if code.strip())


def regimen(country: str | None) -> str:
    code = (country or "").strip().upper()
    if code in UNKNOWN_COUNTRIES or code in OPT_IN_COUNTRIES or code in _extra_opt_in():
        return "opt-in"
    return "opt-out"


def ads_consent(cookie: str | None, *, country: str | None, gpc: str | None = None,
                dnt: str | None = None) -> bool:
    """¿Se puede medir a esta visita? ``cookie`` es el valor de ``qf_ads`` (o None si no eligió)."""
    if (gpc or "").strip() == "1" or (dnt or "").strip() == "1":
        return False
    choice = (cookie or "").strip().lower()
    if choice == "no":
        return False
    if regimen(country) == "opt-in":
        return choice == "si"
    return True


def from_request(request) -> bool:
    """Lo mismo, leyendo la petición de FastAPI (cookie, cabeceras de privacidad y país de Cloudflare)."""
    h = request.headers
    return ads_consent(request.cookies.get(COOKIE), country=h.get("cf-ipcountry"),
                       gpc=h.get("sec-gpc"), dnt=h.get("dnt"))


def regimen_from_request(request) -> str:
    return regimen(request.headers.get("cf-ipcountry"))
