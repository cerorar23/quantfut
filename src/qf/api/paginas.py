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

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import seo

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

    @property
    def ruta(self) -> str:
        return f"/{self.slug}/"


PAGINAS: tuple[Pagina, ...] = (
    Pagina("metodologia", "metodologia.html",
           "Metodología: cómo calculamos las probabilidades",
           "Cómo QuantFut estima probabilidades de fútbol, NBA y tenis, las compara con el mercado, las sella con hashes "
           "y mide sus fallos. Sin promesas de ganancia.",
           "Metodología", date(2026, 11, 8)),
    Pagina("juego-responsable", "juego_responsable.html",
           "Juego responsable: límites y dónde pedir ayuda",
           "QuantFut no es una casa de apuestas ni garantiza resultados. Consejos para apostar con límites, señales de "
           "alerta y teléfonos de ayuda verificados por país.",
           "Juego responsable", date(2026, 11, 8)),
    Pagina("sobre-nosotros", "sobre_nosotros.html",
           "Sobre QuantFut: quién está detrás y qué hacemos",
           "QuantFut es un servicio de Saptain LTD que publica probabilidades estadísticas de deporte. Qué hacemos, qué no "
           "hacemos y cómo contactarnos.",
           "Sobre nosotros", date(2026, 11, 8), "AboutPage"),
)
POR_SLUG = {p.slug: p for p in PAGINAS}


def fecha_larga(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    return tuple((p.ruta, p.revision.isoformat()) for p in PAGINAS)


def _jsonld(pagina: Pagina, url: str, base: str) -> list[dict]:
    return [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": pagina.migas, "item": url},
        ]},
        {"@context": "https://schema.org", "@type": pagina.tipo_schema, "name": pagina.titulo, "url": url,
         "inLanguage": "es", "dateModified": pagina.revision.isoformat(),
         "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
         "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}},
    ]


def render(pagina: Pagina) -> str:
    base = seo.base_url()
    url = base + pagina.ruta
    return _env.get_template(pagina.plantilla).render(
        p=pagina, url=url, base=base, jsonld=_jsonld(pagina, url, base),
        revision_larga=fecha_larga(pagina.revision), revision_iso=pagina.revision.isoformat(),
        paginas=PAGINAS)


def _responder(pagina: Pagina) -> HTMLResponse:
    return HTMLResponse(render(pagina), headers={"Cache-Control": "public, max-age=300",
                                                  "Content-Security-Policy": CSP})


def _registrar(pagina: Pagina) -> None:
    @router.api_route(pagina.ruta, methods=["GET", "HEAD"], name=f"pagina_{pagina.slug}")
    def _pagina():
        return _responder(pagina)

    @router.api_route(f"/{pagina.slug}", methods=["GET", "HEAD"], name=f"pagina_{pagina.slug}_sin_barra")
    def _sin_barra(request: Request):
        # Una sola URL por página: la versión sin barra final redirige (301) a la canónica.
        destino = seo.base_url() + pagina.ruta + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(destino, status_code=301)


for _p in PAGINAS:
    _registrar(_p)
