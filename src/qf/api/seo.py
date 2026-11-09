"""SEO técnico de la web pública (F1.1 de docs/plan_seo_redes_web_20261108.md).

- `robots.txt` y mapas del sitio (`/sitemap.xml` es un índice; hoy solo cuelga `sitemap-paginas.xml`).
- Qué rutas no se indexan (panel, cuentas, API, JSON públicos): cabecera `X-Robots-Tag: noindex`.
  No se bloquean en `robots.txt`: si se bloquearan, Google no vería el `noindex`.
- Un único host: `www.` redirige al dominio sin `www`, y `api.` se marca entera como `noindex`
  (hoy sirve la misma web que el dominio principal).
- 404 en HTML para quien navega; los clientes de la API y las rutas privadas siguen recibiendo JSON.

Los mapas solo listan URLs reales: nada de rutas con `#`, que Google no puede resolver. Se añadirán
páginas aquí a medida que existan (F1.2 en adelante). `lastmod` se omite mientras no haya una fecha de
cambio verificable: Google lo ignora si no es fiable y mentirlo cuenta en contra.
"""
from __future__ import annotations

import os
from html import escape
from xml.sax.saxutils import escape as xml_escape

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

router = APIRouter(include_in_schema=False)

# Primer segmento de ruta de lo que NO es contenido público indexable.
NOINDEX_SEGMENTS = frozenset({
    # panel, cuentas y flujos con sesión o con código de un solo uso
    "control", "admin", "cuenta", "verificar", "restablecer", "i", "rewards", "webhooks",
    # API de la web, la app móvil y los motores
    "app", "mobile", "og", "v1", "web", "static", "vendor", "health",
    # JSON públicos de la raíz (no son páginas)
    "alta-probabilidad", "calibration", "chain", "escalera", "leagues", "matches", "model-card", "parley", "picks",
    "teams", "track-record",
})

# URLs reales e indexables que no salen de `paginas.py`. (ruta, lastmod ISO o None). Mantener alineado
# con `web.py` / `legal.py`: tests/test_seo_base.py comprueba que ninguna lleve `noindex`.
PAGINAS: tuple[tuple[str, str | None], ...] = (
    ("/", None),
    ("/legal/terminos", None),
    ("/legal/privacidad", None),
)

CONTENT_SIGNAL = "search=yes, ai-input=yes, ai-train=no"   # decisión del titular, 8-nov-2026


def dominio() -> str:
    return os.getenv("DOMAIN", "localhost")


def base_url() -> str:
    """Origen canónico, sin barra final. `PUBLIC_BASE_URL` lo fuerza; por defecto https://$DOMAIN."""
    forzado = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if forzado:
        return forzado
    host = dominio()
    return f"http://{host}" if host in ("localhost", "127.0.0.1") else f"https://{host}"


def _host(request: Request) -> str:
    # Detrás de Cloudflare y Caddy el host que pidió la persona llega en X-Forwarded-Host o en Host.
    raw = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    return raw.split(",")[0].split(":")[0].strip().lower()


def es_host_api(request: Request) -> bool:
    return _host(request).startswith("api.")


def es_host_www(request: Request) -> bool:
    return _host(request) == f"www.{dominio().lower()}"


def primer_segmento(path: str) -> str:
    return path.lstrip("/").split("/", 1)[0].lower()


# Prefijos que sí son API aunque su primer segmento también lo use una página pública (`/nba/`, `/tenis/` y `/futbol/`
# son páginas de deporte; sus motores cuelgan de `/nba/v1`, `/nba/v2` y `/tenis/v2`).
NOINDEX_PREFIJOS = ("/nba/v1", "/nba/v2", "/tenis/v2")


def _bajo_prefijo(path: str, prefijo: str) -> bool:
    return path == prefijo or path.startswith(prefijo + "/")


def noindex(request: Request) -> bool:
    path = request.url.path
    return (es_host_api(request) or primer_segmento(path) in NOINDEX_SEGMENTS
            or any(_bajo_prefijo(path, q) for q in NOINDEX_PREFIJOS))


def redireccion_www(request: Request) -> Response | None:
    """www → dominio sin www, conservando ruta y consulta. 301 en lecturas y 308 en el resto,
    para que un POST que aún apunte a www conserve su método."""
    if not es_host_www(request):
        return None
    destino = base_url() + request.url.path + (f"?{request.url.query}" if request.url.query else "")
    return RedirectResponse(destino, status_code=301 if request.method in ("GET", "HEAD") else 308)


def aplicar_cabeceras(request: Request, response: Response) -> None:
    if noindex(request):
        response.headers["X-Robots-Tag"] = "noindex"


# --- robots.txt y mapas del sitio ---------------------------------------------------------------

def robots_txt(request: Request) -> str:
    lineas = ["User-agent: *", f"Content-Signal: {CONTENT_SIGNAL}", "Allow: /", ""]
    if not es_host_api(request):
        lineas.append(f"Sitemap: {base_url()}/sitemap.xml")
    return "\n".join(lineas) + "\n"


def sitemap_index() -> str:
    hijos = [f"{base_url()}/sitemap-paginas.xml"]
    items = "".join(f"<sitemap><loc>{xml_escape(u)}</loc></sitemap>" for u in hijos)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</sitemapindex>\n')


def todas_las_paginas() -> tuple[tuple[str, str | None], ...]:
    from . import futbol_paginas, nba_paginas, paginas, rutas_web, tenis_paginas   # import tardío: todos importan este módulo
    return PAGINAS + rutas_web.entradas_sitemap() + paginas.entradas_sitemap() + nba_paginas.entradas_sitemap() + futbol_paginas.entradas_sitemap() + tenis_paginas.entradas_sitemap()


def sitemap_paginas() -> str:
    filas = []
    for ruta, lastmod in todas_las_paginas():
        mod = f"<lastmod>{xml_escape(lastmod)}</lastmod>" if lastmod else ""
        filas.append(f"<url><loc>{xml_escape(base_url() + ruta)}</loc>{mod}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{"".join(filas)}</urlset>\n')


def _texto(cuerpo: str, tipo: str, cache: str) -> Response:
    return Response(cuerpo, media_type=tipo, headers={"Cache-Control": cache})


@router.api_route("/robots.txt", methods=["GET", "HEAD"])
def robots(request: Request):
    return _texto(robots_txt(request), "text/plain; charset=utf-8", "public, max-age=3600")


@router.api_route("/sitemap.xml", methods=["GET", "HEAD"])
def sitemap():
    return _texto(sitemap_index(), "application/xml; charset=utf-8", "public, max-age=300")


@router.api_route("/sitemap-paginas.xml", methods=["GET", "HEAD"])
def sitemap_de_paginas():
    return _texto(sitemap_paginas(), "application/xml; charset=utf-8", "public, max-age=300")


# --- 404 -----------------------------------------------------------------------------------------

def quiere_html(request: Request) -> bool:
    """¿Una persona o un rastreador navegando a una página inexistente? Los clientes de la API (la propia
    web con `fetch`, la app) piden JSON o `*/*`, y las rutas privadas nunca revelan que existan."""
    if request.method not in ("GET", "HEAD") or noindex(request):
        return False
    return "text/html" in request.headers.get("accept", "").lower()


def pagina_404() -> HTMLResponse:
    cuerpo = (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex">'
        '<title>Página no encontrada · QuantFut</title>'
        '<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#0a0a0f;color:#e6edf3;'
        'font:16px/1.6 system-ui,sans-serif;text-align:center;padding:24px}main{max-width:480px}'
        'h1{font-size:28px;margin:0 0 8px}p{margin:0 0 20px;color:#9aa7b4}'
        'a{color:#34d399;text-decoration:underline}nav{display:flex;gap:16px;justify-content:center;flex-wrap:wrap}</style>'
        '</head><body><main><h1>Página no encontrada</h1>'
        '<p>Esta dirección no existe o ya no está disponible.</p>'
        f'<nav><a href="{escape(base_url())}/">Ir al inicio</a>'
        f'<a href="{escape(base_url())}/legal/terminos">Términos</a>'
        f'<a href="{escape(base_url())}/legal/privacidad">Privacidad</a></nav></main></body></html>'
    )
    return HTMLResponse(cuerpo, status_code=404, headers={
        "Cache-Control": "public, max-age=60",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    })
