"""Respuesta pública de /web/deportes/{tenis,nba}/cuotas: overlay + `state`, `generated_at`, `source`.

Sin datos de cuenta. Nunca lanza ni cuelga: cualquier fallo o espera excesiva devuelve `unavailable` (y se registra).

Tamaño: se OMITEN las entradas sin ningún precio (ausente = «sin cuota» para el cliente; `state` ya refleja el
`partial`). El cuerpo es JSON compacto y se sirve en gzip si el cliente lo acepta. NBA tiene un tope duro
(`MAX_BYTES`): si el cuerpo lo supera se descartan primero los eventos de las cohortes más antiguas y la respuesta
sale `state: "partial"` con `truncated: true`.
Medido en la fixture sintética (3 cohortes x 1 partido x 8 filas): 15 filas con precio = 3.784 B planos, 392 B en gzip
(≈ 250 B por fila con precio; `test_tamano_en_la_fixture_multicohorte`).
El tamaño REAL en producción NO está medido: se mide al desplegar.

Tiempo: la respuesta final se guarda `TTL` (60 s). El cálculo corre en un hilo aparte, uno solo por clave
(single-flight). Mientras recalcula, o en los `BACKOFF` s posteriores a un fallo, se sirve la ÚLTIMA buena si tiene
menos de `STALE_MAX` s; sin ella se espera como máximo `ESPERA_MAX` s y se responde `unavailable`. Tras un fallo no
se reintenta antes de `BACKOFF` s (los que esperaban no reejecutan el cálculo en serie).
"""
from __future__ import annotations

import gzip
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Response

from qf.api import tenis_publico
from qf.api.cuotas_nba import load_cohorts, nba_overlay
from qf.api.cuotas_tenis import load_sealed, tennis_overlay
from qf.config import settings
from qf.ingest import cuotas_respaldo

log = logging.getLogger(__name__)
TTL = timedelta(seconds=60)
STALE_MAX = timedelta(seconds=900)
BACKOFF = timedelta(seconds=5)
ESPERA_MAX = 20.0  # segundos reales que un llamador espera un cálculo en curso
MAX_BYTES = 2_000_000
DIAS_NBA = 3
_ahora = lambda: datetime.now(timezone.utc)  # noqa: E731  (los tests lo sustituyen)
_lock = threading.Lock()
_estado: dict[str, dict] = {}


@dataclass(frozen=True)
class Cuerpo:
    plano: bytes
    gz: bytes


class _Trabajo:
    def __init__(self):
        self.fin = threading.Event()
        self.cuerpo: Cuerpo | None = None


def clear_cache():
    with _lock:
        _estado.clear()


def _json(value) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _cuerpo(value) -> Cuerpo:
    plano = _json(value)
    return Cuerpo(plano, gzip.compress(plano, mtime=0))


def _no_disponible() -> dict:
    return dict(state="unavailable", events={}, source="PropLine", generated_at=_ahora().isoformat())


def _con_precio(row) -> bool:
    return isinstance(row, dict) and any(v is not None for v in row.values())


def _poda_tenis(out: dict) -> dict:
    eventos = {}
    for eid, mercados in (out.get("events") or {}).items():
        con = {mid: q for mid, q in mercados.items() if q is not None}
        if con:
            eventos[eid] = con
    return dict(out, events=eventos)


def _poda_nba(out: dict) -> dict:
    eventos = {}
    for eid, ev in (out.get("events") or {}).items():
        filas = {k: r for k, r in ev.get("quotes", {}).items() if _con_precio(r)}
        if filas:
            eventos[eid] = dict(ev, quotes=filas)
    return dict(out, events=eventos)


def _tope_nba(out: dict) -> dict:
    """Si el cuerpo supera MAX_BYTES, quita los eventos de las cohortes más antiguas hasta que quepa."""
    if len(_json(out)) <= MAX_BYTES:
        return out
    eventos = out["events"]
    orden = sorted(eventos, key=lambda e: (str(eventos[e].get("sealed_at") or ""),
                                           str(eventos[e].get("cohort") or ""), e))
    tam = {e: len(_json(eventos[e])) + len(_json(e)) + 2 for e in orden}
    total = len(_json(dict(out, events={}, truncated=True, state="partial"))) + sum(tam.values())
    quitar = 0
    while quitar < len(orden) and total > MAX_BYTES:
        total -= tam[orden[quitar]]
        quitar += 1
    fuera = set(orden[:quitar])
    return dict(out, state="partial", truncated=True, events={e: v for e, v in eventos.items() if e not in fuera})


def _tenis() -> Cuerpo:
    if not settings.propline_archive or not settings.tennis_sealed_dir:
        return _cuerpo(_no_disponible())
    feed = tenis_publico.public_data()
    ids = [e.get("id") for e in feed.get("events", []) if isinstance(e, dict)]
    sellos = load_sealed(settings.tennis_sealed_dir, [i for i in ids if i is not None])
    out = tennis_overlay(settings.propline_archive, feed, sealed=sellos, now=_ahora())
    return _cuerpo(_poda_tenis(cuotas_respaldo.aplica_tenis(out, cuotas_respaldo.leer_cache(settings.cuotas_respaldo_cache))))


def _nba() -> Cuerpo:
    if not settings.propline_archive or not settings.nba_cohorts_dir:
        return _cuerpo(_no_disponible())
    cohortes = load_cohorts(settings.nba_cohorts_dir, dias=DIAS_NBA, now=_ahora())
    out = nba_overlay(settings.propline_archive, cohortes, now=_ahora())
    # Respaldo: solo lee la caché que escribe el comando por lotes; PropLine gana siempre (rellena lados en None).
    out = cuotas_respaldo.aplica_nba(out, cuotas_respaldo.leer_cache(settings.cuotas_respaldo_cache))
    return _cuerpo(_tope_nba(_poda_nba(out)))


def _ejecuta(clave: str, calcula, trabajo: _Trabajo):
    try:
        cuerpo = calcula()
        with _lock:
            _estado[clave].update(bueno=(_ahora(), cuerpo), fallo=None)
        trabajo.cuerpo = cuerpo
    except Exception:
        log.exception("cuotas %s: no disponible", clave)
        with _lock:
            if clave in _estado:
                _estado[clave]["fallo"] = _ahora()
    finally:
        with _lock:
            if clave in _estado:
                _estado[clave]["trabajo"] = None
        trabajo.fin.set()


def _obtener(clave: str, calcula) -> Cuerpo:
    arranca = False
    with _lock:
        est = _estado.setdefault(clave, dict(bueno=None, fallo=None, trabajo=None))
        ahora, bueno = _ahora(), est["bueno"]
        if bueno and ahora - bueno[0] < TTL:
            return bueno[1]
        rancio = bueno[1] if bueno and ahora - bueno[0] < STALE_MAX else None
        trabajo = est["trabajo"]
        if trabajo is None:
            if est["fallo"] is not None and ahora - est["fallo"] < BACKOFF:
                return rancio or _cuerpo(_no_disponible())
            trabajo = est["trabajo"] = _Trabajo()
            arranca = True
        elif rancio:
            return rancio  # ya se está recalculando: no esperar
    if not arranca and not rancio:
        return _cuerpo(_no_disponible())  # solo espera quien lanza el cálculo: no agotar el threadpool compartido
    if arranca:
        threading.Thread(target=_ejecuta, args=(clave, calcula, trabajo), daemon=True).start()
    trabajo.fin.wait(ESPERA_MAX)
    return trabajo.cuerpo or rancio or _cuerpo(_no_disponible())


def _acepta_gzip(cabecera: str | None) -> bool:
    for parte in (cabecera or "").split(","):
        nombre, _, q = parte.partition(";")
        if nombre.strip().lower() in ("gzip", "*"):
            return q.strip().replace(" ", "") not in ("q=0", "q=0.0", "q=0.00", "q=0.000")
    return False


def _respuesta(clave: str, calcula, accept_encoding: str | None) -> Response:
    try:
        cuerpo = _obtener(clave, calcula)
    except Exception:
        log.exception("cuotas %s: no disponible", clave)
        cuerpo = _cuerpo(_no_disponible())
    cabeceras = {"Cache-Control": "no-store", "Vary": "Accept-Encoding"}
    if _acepta_gzip(accept_encoding):
        cabeceras["Content-Encoding"] = "gzip"
        return Response(cuerpo.gz, media_type="application/json", headers=cabeceras)
    return Response(cuerpo.plano, media_type="application/json", headers=cabeceras)


def tennis_response(accept_encoding: str | None = None) -> Response:
    return _respuesta("tenis", _tenis, accept_encoding)


def nba_response(accept_encoding: str | None = None) -> Response:
    return _respuesta("nba", _nba, accept_encoding)
