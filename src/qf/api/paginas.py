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

from . import idiomas, og, seo, web_config

router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")
# `script-src 'self'`: Cloudflare ofusca los `mailto:` de estas páginas y su `email-decode.min.js` es del mismo origen; sin esto el texto del
# enlace se vería como «[email protected]». Las páginas no llevan scripts en línea ni de terceros (el JSON-LD son datos, no se ejecutan).
CSP = ("default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; "
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
# Portugués (F6.4, Brasil). Mismas tres páginas de confianza; slugs en portugués (`/pt/metodologia/`…). Igual que el inglés:
# no se indexa hasta que el titular abra el idioma y lea el texto (ver `idiomas.py`).
PAGINAS_PT: tuple[Pagina, ...] = (
    Pagina("pt/metodologia", "pt_metodologia.html",
           "Metodologia: como calculamos as probabilidades",
           "Como a QuantFut estima probabilidades de futebol, NBA e tênis, compara-as com o mercado, as sela com hashes e mede "
           "os próprios erros. Sem promessas de lucro.",
           "Metodologia", date(2026, 11, 10), idioma="pt", grupo="metodologia"),
    Pagina("pt/jogo-responsavel", "pt_jogo_responsavel.html",
           "Jogo responsável: limites e onde pedir ajuda",
           "A QuantFut não é uma casa de apostas nem garante resultados. Dicas para apostar dentro de limites, sinais de "
           "alerta e onde buscar apoio.",
           "Jogo responsável", date(2026, 11, 10), idioma="pt", grupo="juego-responsable"),
    Pagina("pt/sobre-nos", "pt_sobre_nos.html",
           "Sobre a QuantFut: quem está por trás e o que fazemos",
           "A QuantFut é um serviço da Saptain LTD que publica probabilidades estatísticas de esportes. O que fazemos, o que não "
           "fazemos e como nos contatar.",
           "Sobre nós", date(2026, 11, 10), "AboutPage", idioma="pt", grupo="sobre-nosotros"),
)
TODAS_LAS_PAGINAS = PAGINAS + PAGINAS_EN + PAGINAS_PT
EN_POR_IDIOMA = {"es": PAGINAS, "en": PAGINAS_EN, "pt": PAGINAS_PT}
INICIO = {"es": "Inicio", "en": "Home", "pt": "Início"}
for _q in TODAS_LAS_PAGINAS:
    idiomas.registrar(_q.grupo, _q.idioma, _q.ruta)


MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
MONTHS_PT = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")


def fecha_larga(d: date, idioma: str = "es") -> str:
    if idioma == "en":
        return f"{MONTHS_EN[d.month - 1]} {d.day}, {d.year}"
    if idioma == "pt":
        return f"{d.day} de {MONTHS_PT[d.month - 1]} de {d.year}"
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Las páginas en español y las de los idiomas ya abiertos (`on`); una en `off` o `preview` no se enumera."""
    return tuple((p.ruta, p.revision.isoformat()) for p in TODAS_LAS_PAGINAS if idiomas.estado(p.idioma) == "on")


def _jsonld(pagina: Pagina, url: str, base: str, cfg: dict | None = None) -> list[dict]:
    blocks = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": INICIO[pagina.idioma] if pagina.idioma == "es" else (cfg or {}).get("brand_name", "QuantFut"), "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": pagina.migas, "item": url},
        ]},
        {"@context": "https://schema.org", "@type": pagina.tipo_schema, "name": pagina.titulo, "url": url,
         "inLanguage": pagina.idioma, "dateModified": pagina.revision.isoformat(),
         "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
         "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}},
    ]
    return web_config.apply_org_jsonld(blocks, cfg)


def render(pagina: Pagina) -> str:
    base = seo.base_url()
    url = base + pagina.ruta
    ctx = web_config.base_template_ctx(lang=pagina.idioma)
    cfg = ctx["cfg"]
    pk = f"pagina:{pagina.grupo}"
    ov = web_config.get_page(pk, pagina.idioma)
    p_eff, body_override = web_config.apply_editorial_meta(pagina, pk, pagina.idioma)
    rev_date = pagina.revision
    if ov and ov.get("revision_date"):
        try:
            rev_date = date.fromisoformat(str(ov["revision_date"]).strip())
        except ValueError:
            pass
    robots = idiomas.robots_de(pagina.idioma)
    if robots is None and cfg.get("default_robots", "index,follow") != "index,follow":
        robots = cfg["default_robots"]
    if ov and not (ov.get("body_html") or "").strip():
        body_override = None
    return _env.get_template(pagina.plantilla).render(
        p=p_eff, url=url, base=base, jsonld=_jsonld(p_eff, url, base, cfg),
        revision_larga=fecha_larga(rev_date, pagina.idioma), revision_iso=rev_date.isoformat(),
        paginas=EN_POR_IDIOMA[pagina.idioma], og_imagen=og.url_marca() if pagina.idioma == "es" else None,   # la tarjeta de marca está en español
        idiomas_alt=idiomas.selector(pagina.ruta), robots=robots,
        body_override=body_override, **ctx)


def _responder(pagina: Pagina) -> HTMLResponse:
    estado = idiomas.estado(pagina.idioma)
    if estado == "off":
        raise HTTPException(404)
    secs = web_config.get_settings().get("public_cache_seconds", 300)
    cab = {"Cache-Control": f"public, max-age={secs}", "Content-Security-Policy": CSP}
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
