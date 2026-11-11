"""`/verificacion/` (F8 y §2 de docs/plan_seo_redes_web_20261108.md): auditoría pública de la cadena SHA-256.

Explica cómo se sellan los lotes antes del partido, comprueba desde el servidor los últimos lotes reales de
`prediction_batches` (sin fabricar datos cuando la base no está disponible) y ofrece verificación en el propio
navegador mediante Web Crypto (`static/verificar-cadena.js`) sobre `/chain`.
"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import idiomas, og, paginas, seo

log = logging.getLogger("qf.verificacion")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

GENESIS = "0" * 64
_RE_HASH = re.compile(r"^[0-9a-f]{64}$")
RUTA = "/verificacion/"
REVISION = date(2026, 11, 10)
SCRIPT = "/static/verificar-cadena.js"
ARCHIVO_SCRIPT = Path(__file__).with_name("static") / "verificar-cadena.js"
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; "
    "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)

_PAGINAS: dict[str, paginas.Pagina] = {
    "es": paginas.Pagina(
        "verificacion",
        "verificacion.html",
        "Verificación criptográfica de pronósticos sellados",
        "Comprueba la cadena SHA-256 de lotes sellados antes de cada partido, valida enlaces y audita /chain en tu navegador o sin dependencias.",
        "Verificación",
        REVISION,
        idioma="es",
        grupo="verificacion",
    ),
    "en": paginas.Pagina(
        "en/verification",
        "en_verificacion.html",
        "Cryptographic verification of sealed forecasts",
        "Verify the SHA-256 hash chain of batches sealed before kickoff, check consecutive links and audit /chain in your browser or offline.",
        "Verification",
        REVISION,
        idioma="en",
        grupo="verificacion",
    ),
    "pt": paginas.Pagina(
        "pt/verificacao",
        "pt_verificacao.html",
        "Verificação criptográfica de previsões seladas",
        "Confira a cadeia SHA-256 dos lotes selados antes das partidas, valide os elos e audite /chain no navegador ou sem dependências.",
        "Verificação",
        REVISION,
        idioma="pt",
        grupo="verificacion",
    ),
}
for _cod, _pag in _PAGINAS.items():
    idiomas.registrar("verificacion", _cod, _pag.ruta)


def sha256_hex(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _es_hash(valor: Any) -> bool:
    return isinstance(valor, str) and bool(_RE_HASH.match(valor))


def carga_lotes(limite: int = 90) -> list[dict[str, Any]] | None:
    """Lee los últimos lotes reales de `prediction_batches`; devuelve None si no hay base accesible."""
    try:
        from ..db import query
        return list(
            query(
                """SELECT batch_date, batch_kind, match_id, n_predictions, n_picks,
                          payload_sha256, prev_sha256, chain_sha256, created_at
                   FROM prediction_batches ORDER BY seq DESC LIMIT %s""",
                (limite,),
            )
        )
    except Exception as exc:
        log.info("Lectura SSR de prediction_batches omitida en /verificacion/: %s", exc)
        return None


def verificar_ventana(lotes_desc: list[dict[str, Any]] | None) -> SimpleNamespace:
    """Comprueba la consistencia de `lotes_desc` (ordenado `seq DESC`) sin inventar datos."""
    if lotes_desc is None:
        return SimpleNamespace(
            estado="sin_conexion",
            ok=None,
            total=0,
            desde_genesis=False,
            errores=[],
            filas=[],
            primer_hash=None,
            ultimo_hash=None,
        )
    if not lotes_desc:
        return SimpleNamespace(
            estado="vacio",
            ok=None,
            total=0,
            desde_genesis=False,
            errores=[],
            filas=[],
            primer_hash=None,
            ultimo_hash=None,
        )

    cron = list(reversed(lotes_desc))
    errores: list[str] = []
    filas: list[SimpleNamespace] = []

    for i, lote in enumerate(cron):
        fecha = str(lote.get("batch_date") or "?")
        tipo = str(lote.get("batch_kind") or "diario")
        payload = lote.get("payload_sha256")
        prev = lote.get("prev_sha256")
        chain = lote.get("chain_sha256")
        valido = True

        if not (_es_hash(payload) and _es_hash(prev) and _es_hash(chain)):
            valido = False
            errores.append(f"#{i + 1} ({fecha} {tipo}): hash SHA-256 inválido o ausente")
        else:
            if i > 0:
                anterior = cron[i - 1].get("chain_sha256")
                if anterior and prev != anterior:
                    valido = False
                    errores.append(f"#{i + 1} ({fecha} {tipo}): enlace prev_sha256 roto")
            if chain != sha256_hex(prev + payload):
                valido = False
                errores.append(f"#{i + 1} ({fecha} {tipo}): hash chain_sha256 inconsistente")

        filas.append(
            SimpleNamespace(
                fecha=fecha,
                tipo=tipo,
                match_id=lote.get("match_id") or "—",
                n_predictions=lote.get("n_predictions"),
                n_picks=lote.get("n_picks"),
                payload_corto=f"{payload[:16]}…" if isinstance(payload, str) else "—",
                chain_corto=f"{chain[:16]}…" if isinstance(chain, str) else "—",
                valido=valido,
            )
        )

    return SimpleNamespace(
        estado="ok" if not errores else "fallo",
        ok=not errores,
        total=len(cron),
        desde_genesis=cron[0].get("prev_sha256") == GENESIS,
        errores=errores,
        filas=list(reversed(filas))[:12],
        primer_hash=cron[0].get("chain_sha256"),
        ultimo_hash=cron[-1].get("chain_sha256"),
    )


def script_url() -> str:
    try:
        return f"{SCRIPT}?v={hashlib.sha1(ARCHIVO_SCRIPT.read_bytes()).hexdigest()[:10]}"
    except OSError:
        return SCRIPT


def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    return tuple((p.ruta, p.revision.isoformat()) for p in _PAGINAS.values() if idiomas.estado(p.idioma) == "on")


def _jsonld(p: paginas.Pagina, url: str, base: str) -> list[dict[str, Any]]:
    return [
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": paginas.INICIO[p.idioma], "item": f"{base}/"},
                {"@type": "ListItem", "position": 2, "name": p.migas, "item": url},
            ],
        },
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": p.titulo,
            "url": url,
            "inLanguage": p.idioma,
            "description": p.descripcion,
            "dateModified": p.revision.isoformat(),
            "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
            "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"},
        },
    ]


def render(idioma: str = "es") -> str:
    p = _PAGINAS[idioma]
    base = seo.base_url()
    url = base + p.ruta
    resumen = verificar_ventana(carga_lotes())
    return _env.get_template(p.plantilla).render(
        p=p,
        url=url,
        base=base,
        jsonld=_jsonld(p, url, base),
        paginas=paginas.EN_POR_IDIOMA[idioma],
        og_imagen=og.url_marca() if idioma == "es" else None,
        idiomas_alt=idiomas.selector(p.ruta),
        robots=idiomas.robots_de(idioma),
        revision_iso=p.revision.isoformat(),
        revision_larga=paginas.fecha_larga(p.revision, idioma),
        resumen=resumen,
        genesis=GENESIS,
        script=script_url(),
    )


def _servir(idioma: str) -> HTMLResponse:
    cab = {"Cache-Control": "no-cache, must-revalidate", "Content-Security-Policy": CSP, **idiomas.puerta(idioma)}
    return HTMLResponse(render(idioma), headers=cab)


def _sin_barra(request: Request, idioma: str) -> RedirectResponse:
    if idiomas.estado(idioma) == "off":
        raise HTTPException(404)
    destino = seo.base_url() + _PAGINAS[idioma].ruta + (f"?{request.url.query}" if request.url.query else "")
    return RedirectResponse(destino, status_code=301)


@router.api_route(RUTA, methods=["GET", "HEAD"], name="verificacion")
def verificacion_pagina():
    return _servir("es")


@router.api_route("/verificacion", methods=["GET", "HEAD"], name="verificacion_sin_barra")
def verificacion_sin_barra(request: Request):
    return _sin_barra(request, "es")


@router.api_route(_PAGINAS["en"].ruta, methods=["GET", "HEAD"], name="verificacion_en")
def verificacion_en_pagina():
    return _servir("en")


@router.api_route(f"/{_PAGINAS['en'].slug}", methods=["GET", "HEAD"], name="verificacion_en_sin_barra")
def verificacion_en_sin_barra(request: Request):
    return _sin_barra(request, "en")


@router.api_route(_PAGINAS["pt"].ruta, methods=["GET", "HEAD"], name="verificacion_pt")
def verificacion_pt_pagina():
    return _servir("pt")


@router.api_route(f"/{_PAGINAS['pt'].slug}", methods=["GET", "HEAD"], name="verificacion_pt_sin_barra")
def verificacion_pt_sin_barra(request: Request):
    return _sin_barra(request, "pt")
