"""Secciones de la web con URL propia (F1.2b de docs/plan_seo_redes_web_20261108.md).

Cada sección pública (`/historial/`, `/pronosticos/`…) responde el MISMO `index.html` de la SPA, pero con:

- un `<head>` propio (título, descripción, canonical, robots, Open Graph, datos estructurados), que es lo
  único que leen los rastreadores de redes sociales y lo primero que lee Google;
- un HTML inicial dentro de `#app` (título, texto y enlaces) que la SPA sustituye al arrancar: es lo que ve
  un rastreador sin JavaScript y lo que se pinta mientras carga el módulo;
- rutas de recursos absolutas, porque `./styles.css` desde `/historial/` pediría `/historial/styles.css`.

Los DATOS siguen pintándolos la SPA y sus endpoints: no se duplica en Python la agregación de resultados
(`allResults`), que mezcla fútbol, NBA y tenis en el navegador. El texto del HTML inicial es explicativo y no
lleva cifras que puedan quedar desfasadas.

`ROUTE_PATH` de frontend/rutas.js debe coincidir con SECCIONES: tests/test_rutas_web.py lo comprueba.
Las rutas sin URL propia (cuenta, acceso, pago, análisis) siguen con `#` y no pasan por aquí.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from html import escape
from json import dumps
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import og, seo

log = logging.getLogger(__name__)
router = APIRouter(include_in_schema=False)
INDEX = Path(__file__).resolve().parents[3] / "frontend" / "index.html"

AVISO = ("QuantFut es un servicio de información estadística, no una casa de apuestas. Solo para mayores de 18 "
         "años. Una probabilidad estimada no garantiza un resultado.")


@dataclass(frozen=True)
class Seccion:
    ruta: str                 # id de la ruta en la SPA (routeTitle de app.js)
    path: str                 # URL limpia, con barra final
    titulo: str               # sin la marca; se añade « | QuantFut »
    descripcion: str          # 120-160 caracteres
    h1: str
    texto: tuple[str, ...]
    migas: str


SECCIONES: tuple[Seccion, ...] = (
    Seccion("inicio", "/",
            "Pronósticos de fútbol, NBA y tenis con probabilidades",
            "Probabilidades de fútbol, NBA y tenis comparadas con el mercado, selladas antes del partido y con historial "
            "completo, también de los fallos.",
            "Pronósticos de fútbol, NBA y tenis con probabilidades verificables",
            ("QuantFut estima la probabilidad de los resultados de cada partido, la compara con las cuotas del mercado y "
             "deja constancia de ella antes de que empiece el juego. Después publica lo que ocurrió, incluidos los fallos.",
             "Cubre once ligas y dos competiciones europeas de fútbol, la NBA y el tenis. Una probabilidad no garantiza un "
             "resultado: consulta la metodología para ver cómo se calcula y qué límites tiene."),
            "Inicio"),
    Seccion("partidos", "/partidos/",
            "Partidos de hoy: probabilidades y estadísticas",
            "Calendario de partidos de fútbol, NBA y tenis con la probabilidad estimada de cada resultado, estadísticas "
            "previas y el mercado de referencia.",
            "Partidos del día con probabilidades y estadísticas",
            ("Cada partido muestra la probabilidad estimada de los resultados principales, estadísticas previas de los "
             "equipos o jugadores y la cuota de referencia del mercado. El resultado se añade cuando termina el partido.",),
            "Partidos"),
    Seccion("picks", "/pronosticos/",
            "Pronósticos de hoy: probabilidades por mercado",
            "Pronósticos de fútbol, NBA y tenis con su probabilidad estimada, la cuota de referencia y el estado de cada "
            "uno: pendiente, acertado o fallado.",
            "Pronósticos de hoy",
            ("Aquí están los pronósticos del día con su probabilidad estimada y su cuota de referencia. Una parte es "
             "gratuita y otra requiere suscripción; todos se sellan antes del partido y su resultado se publica después.",),
            "Pronósticos"),
    Seccion("historial", "/historial/",
            "Historial de pronósticos: aciertos y fallos",
            "Historial público de pronósticos liquidados: resultado, cuota y acierto real frente a lo prometido. Los fallos "
            "se muestran igual que los aciertos.",
            "Historial de pronósticos",
            ("Todos los pronósticos liquidados, con su resultado, también los fallados. Comparamos el acierto real con el "
             "que habíamos estimado: una probabilidad bien calibrada se cumple cerca de las veces que dice.",
             "Una muestra pequeña no demuestra nada: lee las cifras junto con su número de casos. En la metodología "
             "explicamos cómo se sella cada pronóstico y qué limitaciones tiene."),
            "Historial"),
    Seccion("alta", "/pronosticos-alta-probabilidad/",
            "Pronósticos de alta probabilidad del día",
            "Selección diaria de los pronósticos con mayor probabilidad estimada, con su historial de aciertos y fallos. "
            "Alta probabilidad no es certeza.",
            "Pronósticos de alta probabilidad",
            ("Cada día seleccionamos los pronósticos con mayor probabilidad estimada y los publicamos con su historial "
             "completo. Parte de la selección es gratuita y parte es de suscripción.",
             "Que un pronóstico tenga alta probabilidad no significa que no pueda fallar: también mostramos los que fallan."),
            "Alta probabilidad"),
    Seccion("parley", "/parley-del-dia/",
            "Parley del día: combinadas de fútbol, tenis y NBA",
            "Combinadas con objetivos de cuota que mezclan fútbol, tenis y NBA, con el lote sellado antes de jugarse y el "
            "resultado de cada una.",
            "Parley del día",
            ("Un parley combina varios pronósticos en una sola apuesta con un objetivo de cuota. La probabilidad de que se "
             "cumplan todas las patas es siempre menor que la de cada una por separado.",
             "Cada lote se sella antes de jugarse y su resultado se publica, también cuando falla. Hay días sin parley."),
            "Parley del día"),
    Seccion("escalera", "/reto-escalera/",
            "Reto escalera: retos encadenados con resultados",
            "Retos de varios escalones con un pronóstico por escalón y un objetivo de cobro, con los retos completados y los "
            "fallidos a la vista.",
            "Reto escalera",
            ("Un reto encadena varios escalones: cada uno se juega con lo ganado en el anterior y el reto se completa solo si "
             "se aciertan todos. Un solo fallo lo pierde, así que es una dinámica de más riesgo que un pronóstico suelto.",
             "Mostramos los retos en curso, los completados y los fallidos, con la ganancia o pérdida acumulada."),
            "Reto escalera"),
    Seccion("paquetes", "/paquetes/",
            "Paquetes de pronósticos",
            "Paquetes de pronósticos de QuantFut: qué incluyen, cómo se contratan y por qué ningún paquete asegura "
            "resultados.",
            "Paquetes de pronósticos",
            ("Los paquetes dan acceso a pronósticos de suscripción durante un periodo. Ningún paquete asegura resultados: "
             "una probabilidad estimada no garantiza que algo ocurra.",),
            "Paquetes"),
    Seccion("planes", "/planes/",
            "Planes y suscripciones",
            "Planes gratuito y de suscripción de QuantFut: qué incluye cada uno. Una suscripción da acceso a más "
            "información, no asegura resultados.",
            "Planes y suscripciones",
            ("QuantFut tiene contenido gratuito y contenido de suscripción. Una suscripción da acceso a más pronósticos y "
             "herramientas; no asegura resultados ni ganancias.",),
            "Planes"),
)
POR_PATH = {s.path: s for s in SECCIONES}
INICIO = SECCIONES[0]


def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    # Sin lastmod: el contenido real de cada sección cambia a diario y el HTML inicial no es lo que cambia.
    return tuple((s.path, None) for s in SECCIONES if s.path != "/")


# --- construcción del HTML ----------------------------------------------------------------------------

_TITULO = re.compile(r"<title>.*?</title>", re.S)
_DESCRIPCION = re.compile(r'<meta\s+name="description"[^>]*>')
_APP = '<div id="app"></div>'
_HTML = re.compile(r"<html\b([^>]*)>")
_RELATIVOS = re.compile(r'\b(href|src)="\./')

_ESTILO = (
    "<style>.qf-inicial{max-width:820px;margin:0 auto;padding:20px;color:#e6edf3;font:16px/1.7 system-ui,sans-serif}"
    ".qf-inicial a{color:#34d399}.qf-inicial nav ul,.qf-inicial footer ul{display:flex;flex-wrap:wrap;gap:6px 16px;"
    "list-style:none;padding:0}.qf-inicial h1{font-size:clamp(26px,5vw,36px);line-height:1.2}"
    ".qf-inicial p{color:#d3dbe3}.qf-inicial .aviso{font-size:14px;color:#9aa7b4}"
    ".qf-inicial table{border-collapse:collapse;width:100%;margin:12px 0}.qf-inicial th,.qf-inicial td{border:1px solid #2a3340;padding:8px 10px;text-align:left}"
    ".qf-inicial .lista-partidos{list-style:none;padding:0}.qf-inicial .lista-partidos li{padding:8px 0;border-bottom:1px solid #2a3340}"
    ".qf-inicial .fallo{color:#fbbf24}</style>")

_leido: tuple[float, str] | None = None


def _index() -> str:
    """index.html de la SPA; se relee si cambia en disco (se despliega por copia de archivos)."""
    global _leido
    mtime = INDEX.stat().st_mtime
    if _leido is None or _leido[0] != mtime:
        _leido = (mtime, INDEX.read_text(encoding="utf-8"))
    return _leido[1]


def _jsonld(sec: Seccion, base: str) -> list[dict]:
    url = base + sec.path
    if sec.ruta == "inicio":
        return [{"@context": "https://schema.org", "@type": "WebSite", "name": "QuantFut", "url": f"{base}/",
                 "inLanguage": "es"},
                {"@context": "https://schema.org", "@type": "Organization", "name": "QuantFut",
                 "legalName": "Saptain LTD", "url": f"{base}/", "email": "admin@pronosticosdeportivos.pro"}]
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": sec.migas, "item": url}]}]


def _head(sec: Seccion, base: str) -> str:
    marca = og.url_marca()
    return _head_de(f"{sec.titulo} | QuantFut", sec.descripcion, base + sec.path, _jsonld(sec, base),
                    (marca, "QuantFut: pronósticos de fútbol, NBA y tenis con probabilidades verificables") if marca else None)


def _meta_imagen(imagen: tuple[str, str] | None) -> str:
    """Etiquetas de la tarjeta para redes. Sin imagen (Pillow no instalado) queda la tarjeta `summary` de siempre."""
    if not imagen:
        return '<meta name="twitter:card" content="summary" />'
    url, alt = imagen
    return (f'<meta property="og:image" content="{escape(url)}" /><meta property="og:image:type" content="image/jpeg" />'
            f'<meta property="og:image:width" content="{og.ANCHO}" /><meta property="og:image:height" content="{og.ALTO}" />'
            f'<meta property="og:image:alt" content="{escape(alt)}" />'
            f'<meta name="twitter:card" content="summary_large_image" /><meta name="twitter:image" content="{escape(url)}" />'
            f'<meta name="twitter:image:alt" content="{escape(alt)}" />')


ROBOTS = "index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"


def _head_de(titulo: str, descripcion: str, url: str, jsonld: list[dict], imagen: tuple[str, str] | None = None,
             robots: str = ROBOTS) -> str:
    ld = "".join(f'<script type="application/ld+json">{_script_seguro(b)}</script>' for b in jsonld)
    return (
        f'<meta name="description" content="{escape(descripcion)}" />'
        f'<link rel="canonical" href="{escape(url)}" />'
        f'<meta name="robots" content="{escape(robots)}" />'
        '<meta property="og:type" content="website" /><meta property="og:site_name" content="QuantFut" />'
        '<meta property="og:locale" content="es_ES" />'
        f'<meta property="og:url" content="{escape(url)}" /><meta property="og:title" content="{escape(titulo)}" />'
        f'<meta property="og:description" content="{escape(descripcion)}" />'
        f'{_meta_imagen(imagen)}{ld}{_ESTILO}')


def _script_seguro(dato: dict) -> str:
    # Dentro de <script>, "<" podría cerrar la etiqueta: se escapa como en el filtro `tojson` de Jinja.
    return dumps(dato, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def _inicial(sec: Seccion) -> str:
    parrafos = "".join(f"<p>{escape(t)}</p>" for t in sec.texto)
    return marco_inicial(f"<h1>{escape(sec.h1)}</h1>{parrafos}")


def marco_inicial(principal: str) -> str:
    """HTML inicial de `#app`: cabecera con enlaces, el contenido propio de la página y el pie. Lo ve quien no
    ejecuta JavaScript y se pinta mientras carga el módulo; la SPA lo sustituye al arrancar."""
    from . import paginas
    secciones = "".join(f'<li><a href="{escape(s.path)}">{escape(s.migas)}</a></li>' for s in SECCIONES)
    # páginas de deporte (nba_paginas.py, futbol_paginas.py), servidas con el shell de la SPA
    secciones += '<li><a href="/futbol/">Pronósticos de fútbol</a></li><li><a href="/nba/">Pronósticos NBA</a></li><li><a href="/tenis/">Pronósticos de tenis</a></li><li><a href="/calibracion/">Calibración</a></li><li><a href="/calculadora-cuota-justa/">Cuota justa</a></li>'
    confianza = "".join(f'<li><a href="{escape(p.ruta)}">{escape(p.migas)}</a></li>' for p in paginas.PAGINAS)
    return (f'<div class="qf-inicial" data-seo-inicial><header><a href="/">QuantFut</a>'
            f'<nav aria-label="Secciones"><ul>{secciones}</ul></nav></header>'
            f'<main id="main-content" tabindex="-1">{principal}'
            f'<p class="aviso">{escape(AVISO)}</p></main>'
            f'<footer><ul>{confianza}<li><a href="/legal/terminos">Términos</a></li>'
            '<li><a href="/legal/privacidad">Privacidad</a></li></ul></footer></div>')


def _adaptar(html: str, *, titulo: str, ruta: str, head: str, inicial: str, atributos: str = "") -> str:
    """Sustituye en el index.html de la SPA título, descripción, `<html>` y `#app`. Si el archivo ya no tiene las
    marcas esperadas se devuelve sin cambios (la web sigue funcionando) y se deja constancia en el log."""
    marcas = (_TITULO.search(html), _DESCRIPCION.search(html), _HTML.search(html), _APP in html)
    if not all(marcas):
        log.error("rutas_web: index.html no tiene las marcas esperadas (title, description, <html>, #app); se sirve sin adaptar")
        return html
    html = _TITULO.sub(lambda _: f"<title>{escape(titulo)}</title>", html, count=1)
    html = _DESCRIPCION.sub(lambda _: head, html, count=1)
    html = _HTML.sub(lambda m: f'<html{m.group(1)} data-ruta="{escape(ruta)}"{atributos}>', html, count=1)
    html = _RELATIVOS.sub(lambda m: f'{m.group(1)}="/', html)
    return html.replace(_APP, f'<div id="app">{inicial}</div>', 1)


def render(sec: Seccion, base: str | None = None, index: str | None = None) -> str:
    """index.html de la SPA adaptado a una sección."""
    html = _index() if index is None else index
    base = seo.base_url() if base is None else base
    return _adaptar(html, titulo=f"{sec.titulo} | QuantFut", ruta=sec.ruta, head=_head(sec, base), inicial=_inicial(sec))


def render_pagina(*, titulo: str, descripcion: str, path: str, ruta: str, jsonld: list[dict], principal: str,
                  datos: dict[str, str] | None = None, base: str | None = None, index: str | None = None,
                  imagen: tuple[str, str] | None = None, robots: str = ROBOTS) -> str:
    """Página con URL propia que no es una sección fija (p. ej. un partido de NBA): mismo shell de la SPA, con su
    `<head>`, su JSON-LD y su contenido en el HTML inicial. `datos` son atributos `data-*` del `<html>` que la SPA
    lee al arrancar (sin que el servidor decida nada del diseño)."""
    html = _index() if index is None else index
    base = seo.base_url() if base is None else base
    atributos = "".join(f' data-{k}="{escape(str(v))}"' for k, v in (datos or {}).items())
    return _adaptar(html, titulo=f"{titulo} | QuantFut", ruta=ruta,
                    head=_head_de(f"{titulo} | QuantFut", descripcion, base + path, jsonld, imagen, robots),
                    inicial=marco_inicial(principal), atributos=atributos)


def responder(sec: Seccion) -> HTMLResponse:
    return HTMLResponse(render(sec), headers={"Cache-Control": "no-cache, must-revalidate"})


def _registrar(sec: Seccion) -> None:
    if sec.path == "/":
        return        # la portada la sirve web.py (`/`) con esta misma función
    @router.api_route(sec.path, methods=["GET", "HEAD"], name=f"seccion_{sec.ruta}")
    def _seccion():
        return responder(sec)

    @router.api_route(sec.path.rstrip("/"), methods=["GET", "HEAD"], name=f"seccion_{sec.ruta}_sin_barra")
    def _sin_barra(request: Request):
        destino = seo.base_url() + sec.path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(destino, status_code=301)


for _s in SECCIONES:
    _registrar(_s)
