"""Respuesta pública de /web/deportes/{tenis,nba}/cuotas: overlay + `state`, `generated_at`, `source`.

Sin datos de cuenta. Nunca lanza: cualquier fallo devuelve `unavailable` (y se registra). La respuesta FINAL de
cada endpoint se guarda 60 s en memoria (una sola construcción aunque lleguen peticiones a la vez) para acotar el
coste de releer recibos pesados; un fallo no se guarda.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone

from qf.api import tenis_publico
from qf.api.cuotas_nba import load_cohorts, nba_overlay
from qf.api.cuotas_tenis import load_sealed, tennis_overlay
from qf.config import settings

log = logging.getLogger(__name__)
TTL = timedelta(seconds=60)
DIAS_NBA = 3
_ahora = lambda: datetime.now(timezone.utc)  # noqa: E731  (los tests lo sustituyen)
_lock = threading.Lock()
_entradas: dict[str, tuple[datetime, dict]] = {}
_candados: dict[str, threading.Lock] = {}


def clear_cache():
    with _lock:
        _entradas.clear()


def _no_disponible():
    return dict(state="unavailable", events={}, source="PropLine", generated_at=_ahora().isoformat())


def _fresca(clave):
    with _lock:
        e = _entradas.get(clave)
    return e[1] if e and _ahora() - e[0] < TTL else None


def _cacheada(clave, calcula):
    if (v := _fresca(clave)) is not None:
        return v
    with _lock:
        candado = _candados.setdefault(clave, threading.Lock())
    with candado:  # el segundo en llegar espera y reutiliza el resultado del primero
        if (v := _fresca(clave)) is not None:
            return v
        v = calcula()
        with _lock:
            _entradas[clave] = (_ahora(), v)
        return v


def _responde(clave, calcula):
    try:
        return _cacheada(clave, calcula)
    except Exception:
        log.exception("cuotas %s: no disponible", clave)
        return _no_disponible()


def _tenis():
    if not settings.propline_archive or not settings.tennis_sealed_dir:
        return _no_disponible()
    feed = tenis_publico.public_data()
    ids = [e.get("id") for e in feed.get("events", []) if isinstance(e, dict)]
    sellos = load_sealed(settings.tennis_sealed_dir, [i for i in ids if i is not None])
    return tennis_overlay(settings.propline_archive, feed, sealed=sellos, now=_ahora())


def _nba():
    if not settings.propline_archive or not settings.nba_cohorts_dir:
        return _no_disponible()
    cohortes = load_cohorts(settings.nba_cohorts_dir, dias=DIAS_NBA, now=_ahora())
    return nba_overlay(settings.propline_archive, cohortes, now=_ahora())


def tennis_response():
    return _responde("tenis", _tenis)


def nba_response():
    return _responde("nba", _nba)
