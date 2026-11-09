"""Lectura de `nba-api` para las páginas públicas de NBA (F2.1 de docs/plan_seo_redes_web_20261108.md).

Solo LEE lo que `nba-api` ya publica sin cuenta (`/nba/v1/cartelera`, `/nba/v1/partido/{id}/estadisticas`): no calcula
probabilidades, no toca el sello y no reordena `predecir → sellar → publicar`. Si el motor no responde, las páginas
devuelven 503 (nunca 404: un fallo pasajero no debe sacar una página del índice) y se sirve el último dato bueno
guardado mientras exista.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

log = logging.getLogger("qf.nba_datos")

TIMEOUT_S = 4.0
TTL_VIVO_S = 60          # día en curso o futuro: el sello y el marcador cambian
TTL_PASADO_S = 600       # días ya cerrados
MAX_ENTRADAS = 96
ET = ZoneInfo("America/New_York")
SLUG_PARTIDO = re.compile(r"^(?P<local>[a-z0-9]+(?:-[a-z0-9]+)*)-vs-(?P<visit>[a-z0-9]+(?:-[a-z0-9]+)*)-(?P<fecha>\d{4}-\d{2}-\d{2})$")


class NbaNoDisponible(Exception):
    """`nba-api` no respondió y no hay copia guardada."""


_lock = threading.Lock()
_cache: dict[str, tuple[float, object]] = {}


def base_api() -> str:
    return os.getenv("NBA_API_URL", "http://nba-api:8000").rstrip("/")


def hoy_et(ahora: datetime | None = None) -> date:
    return (ahora or datetime.now(timezone.utc)).astimezone(ET).date()


def _pedir(ruta: str, params: dict | None = None) -> object:
    try:
        r = httpx.get(base_api() + ruta, params=params, timeout=TIMEOUT_S)
        r.raise_for_status()
        return r.json()
    except Exception as e:   # red, 5xx, JSON roto: todo cuenta como «no disponible»
        raise NbaNoDisponible(str(e)) from e


def _con_cache(clave: str, ttl: float, ruta: str, params: dict | None = None) -> object:
    ahora = time.monotonic()
    with _lock:
        previo = _cache.get(clave)
    if previo and ahora - previo[0] < ttl:
        return previo[1]
    try:
        valor = _pedir(ruta, params)
    except NbaNoDisponible:
        if previo:
            log.warning("nba-api no responde; se sirve la copia guardada de %s", clave)
            return previo[1]
        raise
    with _lock:
        _cache[clave] = (ahora, valor)
        if len(_cache) > MAX_ENTRADAS:
            for k in sorted(_cache, key=lambda k: _cache[k][0])[: len(_cache) - MAX_ENTRADAS]:
                _cache.pop(k, None)
    return valor


def vaciar_cache() -> None:
    with _lock:
        _cache.clear()


def cartelera(fecha: date, hoy: date | None = None) -> list[dict]:
    """Partidos de un día (fecha ET del partido). Días cerrados se guardan más tiempo."""
    cerrado = fecha < (hoy or hoy_et()) - timedelta(days=1)
    datos = _con_cache(f"cartelera:{fecha.isoformat()}", TTL_PASADO_S if cerrado else TTL_VIVO_S,
                       "/nba/v1/cartelera", {"fecha": fecha.isoformat()})
    partidos = datos.get("partidos") if isinstance(datos, dict) else None
    if not isinstance(partidos, list):
        raise NbaNoDisponible("respuesta de cartelera sin lista de partidos")
    return partidos


def cartelera_ventana(desde: date, hasta: date) -> dict[date, list[dict]]:
    """Varios días a la vez. Un día que falle se omite; si fallan todos, NbaNoDisponible."""
    dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
    hoy = hoy_et()

    def uno(d: date):
        try:
            return d, cartelera(d, hoy)
        except NbaNoDisponible:
            return d, None

    with ThreadPoolExecutor(max_workers=min(6, len(dias) or 1)) as pool:
        resultados = dict(pool.map(uno, dias))
    ok = {d: v for d, v in resultados.items() if v is not None}
    if not ok:
        raise NbaNoDisponible("ningún día de la ventana respondió")
    return ok


def estadisticas(partido_id: int, fecha: date) -> dict | None:
    """Récord y forma a la fecha del partido. Mejora el contenido, pero la página no depende de ello."""
    cerrado = fecha < hoy_et() - timedelta(days=1)
    try:
        datos = _con_cache(f"estadisticas:{partido_id}", TTL_PASADO_S if cerrado else TTL_VIVO_S,
                           f"/nba/v1/partido/{int(partido_id)}/estadisticas")
    except NbaNoDisponible:
        return None
    return datos if isinstance(datos, dict) else None


# --- Identidad de la URL -------------------------------------------------------------------------

def slug_texto(nombre: str) -> str:
    base = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-")


def slug_partido(p: dict) -> str:
    return f"{slug_texto(p['local']['nombre'])}-vs-{slug_texto(p['visitante']['nombre'])}-{p['fecha']}"


def buscar_partido(slug: str) -> dict | None:
    """El partido de esa URL, solo si tiene pronóstico sellado (plan §3.2: sin sello, la página no existe)."""
    m = SLUG_PARTIDO.match(slug)
    if not m:
        return None
    try:
        dia = date.fromisoformat(m["fecha"])
    except ValueError:
        return None
    for p in cartelera(dia):
        if p.get("pronostico") and slug_partido(p) == slug:
            return p
    return None
