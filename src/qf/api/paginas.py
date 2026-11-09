"""Páginas públicas con HTML completo desde el servidor (F1.2 de docs/plan_seo_redes_web_20261108.md).

Cada página es una ruta real con barra final, su plantilla en `paginas/`, su `<head>` completo (título,
descripción, canonical, robots, Open Graph) y su BreadcrumbList. Entran solas en `/sitemap-paginas.xml`
con la fecha de su última revisión como `lastmod`: esa fecha es la que se muestra en la propia página,
así que lo declarado al buscador y lo que lee la persona no pueden diferir (lo comprueba una prueba).

El contenido de estas páginas es YMYL: cada afirmación debe estar respaldada por el código o por una
medición del proyecto. Al cambiar un texto, actualiza `revision` y deja constancia en harness/progreso.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import idiomas, og, seo

router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")
CSP = ("default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; "
       "frame-ancestors 'none'")


@dataclass(frozen=True)
class Pagina:
    slug: str                 # sin barras: "metodologia" → /metodologia/
    plantilla: str
    titulo: str               # sin la marca; la plantilla añade « | QuantFut »
    descripcion: str          # 130-160 caracteres
    migas: str                # nombre en la ruta de migas
    revision: date            # última revisión de contenido (= lastmod)
    tipo_schema: str = "WebPage"
    idioma: str = "es"
    grupo: str = ""           # la misma página en otros idiomas comparte grupo (hreflang)

    @property
    def ruta(self) -> str:
        return f"/{self.slug}/"


PAGINAS: tuple[Pagina, ...] = (
    Pagina("metodologia", "metodologia.html",
           "Metodología: cómo calculamos las probabilidades",
           "Cómo QuantFut estima probabilidades de fútbol, NBA y tenis, las compara con el mercado, las sella con hashes "
           "y mide sus fallos. Sin promesas de ganancia.",
           "Metodología", date(2026, 11, 8), grupo="metodologia"),
    Pagina("juego-responsable", "juego_responsable.html",
           "Juego responsable: límites y dónde pedir ayuda",
           "QuantFut no es una casa de apuestas ni garantiza resultados. Consejos para apostar con límites, señales de "
           "alerta y teléfonos de ayuda verificados por país.",
           "Juego responsable", date(2026, 11, 8), grupo="juego-responsable"),
    Pagina("sobre-nosotros", "sobre_nosotros.html",
           "Sobre QuantFut: quién está detrás y qué hacemos",
           "QuantFut es un servicio de Saptain LTD que publica probabilidades estadísticas de deporte. Qué hacemos, qué no "
           "hacemos y cómo contactarnos.",
           "Sobre nosotros", date(2026, 11, 8), "AboutPage", grupo="sobre-nosotros"),
)
POR_SLUG = {p.slug: p for p in PAGINAS}

# Inglés (F6.1). Mismo contenido que las tres páginas en español, escrito para lectores de habla inglesa; no se indexa hasta que el titular
# abra el idioma (ver `idiomas.py`). Las fechas de revisión son las de esta redacción.
PAGINAS_EN: tuple[Pagina, ...] = (
    Pagina("en/methodology", "en_methodology.html",
           "Methodology: how we calculate probabilities",
           "How QuantFut estimates football, NBA and tennis probabilities, compares them with the market, seals them with hashes "
           "and measures its misses. No promise of profit.",
           "Methodology", date(2026, 11, 9), idioma="en", grupo="metodologia"),
    Pagina("en/responsible-gambling", "en_responsible_gambling.html",
           "Responsible gambling: limits and where to get help",
           "QuantFut is not a bookmaker and guarantees no results. Tips for gambling within limits, warning signs and "
           "helplines checked by country.",
           "Responsible gambling", date(2026, 11, 9), idioma="en", grupo="juego-responsable"),
    Pagina("en/about", "en_about.html",
           "About QuantFut: who is behind it and what we do",
           "QuantFut is a service of Saptain LTD that publishes statistical sports probabilities. What we do, what we do not do "
           "and how to contact us.",
           "About", date(2026, 11, 9), "AboutPage", idioma="en", grupo="sobre-nosotros"),
)
TODAS_LAS_PAGINAS = PAGINAS + PAGINAS_EN
EN_POR_IDIOMA = {"es": PAGINAS, "en": PAGINAS_EN}
INICIO = {"es": "Inicio", "en": "Home"}
for _q in TODAS_LAS_PAGINAS:
    idiomas.registrar(_q.grupo, _q.idioma, _q.ruta)


MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def fecha_larga(d: date, idioma: str = "es") -> str:
    if idioma == "en":
        return f"{MONTHS_EN[d.month - 1]} {d.day}, {d.year}"
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Las páginas en español y las de los idiomas ya abiertos (`on`); una en `off` o `preview` no se enumera."""
    return tuple((p.ruta, p.revision.isoformat()) for p in TODAS_LAS_PAGINAS if idiomas.estado(p.idioma) == "on")


def _jsonld(pagina: Pagina, url: str, base: str) -> list[dict]:
    return [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": INICIO[pagina.idioma] if pagina.idioma == "es" else "QuantFut", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": pagina.migas, "item": url},
        ]},
        {"@context": "https://schema.org", "@type": pagina.tipo_schema, "name": pagina.titulo, "url": url,
         "inLanguage": pagina.idioma, "dateModified": pagina.revision.isoformat(),
         "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
         "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}},
    ]


def render(pagina: Pagina) -> str:
    base = seo.base_url()
    url = base + pagina.ruta
    return _env.get_template(pagina.plantilla).render(
        p=pagina, url=url, base=base, jsonld=_jsonld(pagina, url, base),
        revision_larga=fecha_larga(pagina.revision, pagina.idioma), revision_iso=pagina.revision.isoformat(),
        paginas=EN_POR_IDIOMA[pagina.idioma], og_imagen=og.url_marca() if pagina.idioma == "es" else None,   # la tarjeta de marca está en español
        idiomas_alt=idiomas.selector(pagina.ruta), robots=idiomas.robots_de(pagina.idioma))


def _responder(pagina: Pagina) -> HTMLResponse:
    estado = idiomas.estado(pagina.idioma)
    if estado == "off":
        raise HTTPException(404)
    cab = {"Cache-Control": "public, max-age=300", "Content-Security-Policy": CSP}
    if estado == "preview":       # revisión del titular en producción: nada la indexa ni la guarda en caché compartida
        cab.update({"Cache-Control": "no-store", "X-Robots-Tag": "noindex"})
    return HTMLResponse(render(pagina), headers=cab)


def _registrar(pagina: Pagina) -> None:
    nombre = pagina.slug.replace("/", "_")

    @router.api_route(pagina.ruta, methods=["GET", "HEAD"], name=f"pagina_{nombre}")
    def _pagina():
        return _responder(pagina)

    @router.api_route(f"/{pagina.slug}", methods=["GET", "HEAD"], name=f"pagina_{nombre}_sin_barra")
    def _sin_barra(request: Request):
        if idiomas.estado(pagina.idioma) == "off":
            raise HTTPException(404)
        # Una sola URL por página: la versión sin barra final redirige (301) a la canónica.
        destino = seo.base_url() + pagina.ruta + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(destino, status_code=301)


for _p in TODAS_LAS_PAGINAS:
    _registrar(_p)
