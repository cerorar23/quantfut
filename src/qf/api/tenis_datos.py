"""Datos de tenis para las páginas públicas (F3.2 de docs/plan_seo_redes_web_20261108.md).

Lee en el propio proceso el feed público que ya sirve `/web/deportes/tenis` (`tenis_publico.public_data()`): solo
pronósticos SELLADOS (cada evento trae su `seal` y `sealed_at` anterior al inicio, validado al exportarlo). No usa las
estadísticas de jugadores ni el motor de tenis: una página solo dice lo que dice el feed público.

Fecha de la URL: día UTC del inicio que publica el feed (los torneos están en husos distintos; UTC es verificable).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from . import nba_datos

log = logging.getLogger("qf.tenis_datos")

DIAS_ATRAS = 3          # mismos límites que la ventana de deportes de la app: -3..+3
DIAS_ADELANTE = 3
SLUG_PARTIDO = nba_datos.SLUG_PARTIDO
slug_texto = nba_datos.slug_texto
RESERVADOS = {"v2"}     # /tenis/v2/* es el motor, no una página


class TenisNoDisponible(Exception):
    """El feed público no está disponible (no existe, caducó o está roto)."""


def _inicio(ev: dict) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(ev["start"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def eventos() -> list[dict]:
    """Eventos del feed con inicio válido, cada uno con `_inicio` (datetime UTC)."""
    from . import tenis_publico
    try:
        feed = tenis_publico.public_data()
    except Exception as e:   # volumen ausente, JSON roto…
        log.warning("tenis: el feed falló: %s", e)
        raise TenisNoDisponible(str(e)) from e
    if feed.get("state") not in ("ok", "partial"):
        raise TenisNoDisponible(f"feed {feed.get('state')}")
    salida = []
    for ev in feed.get("events") or []:
        inicio = _inicio(ev)
        if inicio is not None and ev.get("home") and ev.get("away") and ev.get("league") and ev.get("seal"):
            salida.append({**ev, "_inicio": inicio.astimezone(timezone.utc)})
    return salida


def torneo_nombre(ev: dict) -> str:
    return str(ev["league"]).replace(" · ", " ")


def torneo_slug(ev: dict) -> str:
    return slug_texto(str(ev["league"]))


def fecha_utc(ev: dict) -> date:
    return ev["_inicio"].date()


def slug_partido(ev: dict) -> str:
    return f"{slug_texto(ev['home'])}-vs-{slug_texto(ev['away'])}-{fecha_utc(ev).isoformat()}"


def ruta_partido(ev: dict) -> str:
    return f"/tenis/{torneo_slug(ev)}/{slug_partido(ev)}/"


def hoy_utc(ahora: datetime | None = None) -> date:
    return (ahora or datetime.now(timezone.utc)).astimezone(timezone.utc).date()


def en_ventana(ev: dict, hoy: date) -> bool:
    return hoy - timedelta(days=DIAS_ATRAS) <= fecha_utc(ev) <= hoy + timedelta(days=DIAS_ADELANTE)


def ventana(hoy: date | None = None) -> list[dict]:
    hoy = hoy or hoy_utc()
    return [e for e in eventos() if en_ventana(e, hoy)]


def buscar_partido(torneo: str, slug: str) -> dict | None:
    """El evento de esa URL (cualquier fecha que aún esté en el feed). Todos los del feed están sellados."""
    if torneo in RESERVADOS or not SLUG_PARTIDO.match(slug):
        return None
    for ev in eventos():
        if slug_partido(ev) == slug and torneo_slug(ev) == torneo:
            return ev
    return None
