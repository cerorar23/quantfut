"""`/calculadora-cuota-justa/` (F4.2 de docs/plan_seo_redes_web_20261108.md): cuota ↔ probabilidad y «quitar el margen de la casa».

Es una herramienta de EDUCACIÓN, no de apuestas: convierte cuotas en probabilidades y viceversa y muestra cuánto margen lleva una cuota.
No calcula importes ni «apuestas de valor» (plan §2, fila 14: decirle a alguien cuánto apostar es lo más arriesgado que puede publicar la web).

Tres piezas que deben decir lo MISMO:
- este módulo (Python puro, sin numpy/scipy): referencia y ejemplo resuelto que se pinta en el HTML aunque el navegador no ejecute JavaScript;
- `static/cuota-justa.js`: la calculadora interactiva;
- `src/qf/model/devig.py`: el de-vig que usa el motor. Las pruebas comprueban que las tres coinciden (vectores en `tests/datos_cuota_justa.json`).
"""
from __future__ import annotations

import hashlib
import logging
import math
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import idiomas, og, paginas, seo

log = logging.getLogger("qf.cuota_justa")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA = "/calculadora-cuota-justa/"
REVISION = date(2026, 11, 9)
REVISION_NUEVOS = date(2026, 11, 10)
SCRIPT = "/static/cuota-justa.js"
ARCHIVO_SCRIPT = Path(__file__).with_name("static") / "cuota-justa.js"
# La política de las páginas de confianza ya admite el script PROPIO (`script-src 'self'`): sin 'unsafe-inline' en scripts, sin conexiones
# (la calculadora no envía nada a ningún sitio), sin Pixel de Meta.
CSP = paginas.CSP

# Ejemplo resuelto que se muestra sin JavaScript (cuotas típicas de un 1X2 con margen).
EJEMPLO = (("Local", 2.10), ("Empate", 3.40), ("Visitante", 3.60))
_NOMBRES_EJEMPLO = {
    "es": ("Local", "Empate", "Visitante"),
    "en": ("Home", "Draw", "Away"),
    "pt": ("Casa", "Empate", "Visitante"),
}
_PAGINAS: dict[str, paginas.Pagina] = {
    "es": paginas.Pagina(
        "calculadora-cuota-justa", "cuota_justa.html",
        "Calculadora de cuota justa: de cuota a probabilidad",
        "Convierte cuotas en probabilidades y al revés, y descubre cuánto margen lleva una cuota (1X2 o dos resultados). "
        "Herramienta educativa: no calcula importes de apuesta.",
        "Cuota justa", REVISION, idioma="es", grupo="cuota-justa",
    ),
    "en": paginas.Pagina(
        "en/fair-odds-calculator", "en_cuota_justa.html",
        "Fair odds calculator: from odds to probability",
        "Convert betting odds into implied probabilities and back, and remove the bookmaker's margin (1X2 or two-way). "
        "Educational tool: does not suggest bet sizes.",
        "Fair odds", REVISION_NUEVOS, idioma="en", grupo="cuota-justa",
    ),
    "pt": paginas.Pagina(
        "pt/calculadora-odd-justa", "pt_cuota_justa.html",
        "Calculadora de odd justa: de odd a probabilidade",
        "Converta odds em probabilidades implícitas e vice-versa, e remova a margem da casa (1X2 ou dois resultados). "
        "Ferramenta educativa: não indica quanto apostar.",
        "Odd justa", REVISION_NUEVOS, idioma="pt", grupo="cuota-justa",
    ),
}
for _cod, _pag in _PAGINAS.items():
    idiomas.registrar("cuota-justa", _cod, _pag.ruta)


# --- cálculo (mismo algoritmo que qf.model.devig; ver `devig.py` para la teoría) -------------------------

def _biseccion(f, a: float, b: float, tol: float = 1e-12):
    """Raíz de f en [a, b] por bisección, o None si f no cambia de signo (lo mismo que `brentq` al lanzar ValueError)."""
    fa, fb = f(a), f(b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0:
        return None
    for _ in range(200):
        m = 0.5 * (a + b)
        fm = f(m)
        if fm == 0.0 or (b - a) < tol:
            return m
        if fa * fm < 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


def _validar(cuotas) -> list[float]:
    xs = [float(c) for c in cuotas]
    if len(xs) < 2 or any((not math.isfinite(x)) or x <= 1.0 for x in xs):
        raise ValueError(f"Cuotas decimales inválidas: {cuotas}")
    return xs


def sobreredondeo(cuotas) -> float:
    """Suma de 1/cuota. Es 1 + el margen de la casa (1,05 = un 5 % de margen)."""
    return sum(1.0 / c for c in _validar(cuotas))


def proporcional(cuotas) -> list[float]:
    raw = [1.0 / c for c in _validar(cuotas)]
    s = sum(raw)
    return [r / s for r in raw]


def potencia(cuotas) -> list[float]:
    raw = [1.0 / c for c in _validar(cuotas)]
    k = _biseccion(lambda k: sum(r ** k for r in raw) - 1.0, 0.35, 3.0)
    if k is None:
        return proporcional(cuotas)
    p = [r ** k for r in raw]
    s = sum(p)
    return [x / s for x in p]


def shin(cuotas) -> list[float]:
    """Método de Shin (1993), el que usa el motor por defecto. Reparte el margen según un modelo de apostadores informados."""
    raw = [1.0 / c for c in _validar(cuotas)]
    s = sum(raw)
    if s <= 1.0 + 1e-12:
        return [r / s for r in raw]

    def pi_de_z(z: float) -> list[float]:
        return [(math.sqrt(max(z * z + 4.0 * (1.0 - z) * (r * r) / s, 0.0)) - z) / (2.0 * (1.0 - z)) for r in raw]

    z = _biseccion(lambda z: sum(pi_de_z(z)) - 1.0, 1e-9, 0.35)
    if z is None:
        return potencia(cuotas)
    p = [min(max(x, 1e-9), 1.0) for x in pi_de_z(z)]
    t = sum(p)
    return [x / t for x in p]


METODOS = {"proporcional": proporcional, "shin": shin, "potencia": potencia}


def sin_margen(cuotas, metodo: str = "shin") -> list[float]:
    return METODOS[metodo](cuotas)


def cuota_justa(prob: float) -> float:
    return math.inf if prob <= 0 else 1.0 / prob


# --- formato (lo que se pinta en el ejemplo resuelto; el JS usa las mismas reglas) ------------------------

def n2(x: float, idioma: str = "es") -> str:
    s = f"{x:.2f}"
    return s if idioma == "en" else s.replace(".", ",")


def pct(x: float, idioma: str = "es") -> str:
    s = f"{x * 100:.2f}"
    if idioma == "en":
        return f"{s}%"
    if idioma == "pt":
        return f"{s.replace('.', ',')}%"
    return f"{s.replace('.', ',')} %"


def ejemplo(metodo: str = "shin", idioma: str = "es") -> dict:
    cuotas = [c for _, c in EJEMPLO]
    nombres = _NOMBRES_EJEMPLO[idioma]
    imp = [1.0 / c for c in cuotas]
    sm = sin_margen(cuotas, metodo)
    filas = [{"nombre": n, "cuota": n2(c, idioma), "implicita": pct(i, idioma), "sin_margen": pct(p, idioma), "justa": n2(cuota_justa(p), idioma)}
             for n, c, i, p in zip(nombres, cuotas, imp, sm)]
    total = sum(imp)
    return {"filas": filas, "suma": pct(total, idioma), "margen": pct(total - 1.0, idioma), "suma_sin_margen": pct(sum(sm), idioma),
            "metodo": metodo, "datos": {"cuotas": cuotas, "implicitas": imp, "sin_margen": sm, "total": total}}


# --- página --------------------------------------------------------------------------------------

def _pagina(idioma: str = "es") -> paginas.Pagina:
    return _PAGINAS[idioma]


def _jsonld(p: paginas.Pagina, url: str, base: str) -> list[dict]:
    return [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio" if p.idioma == "es" else "QuantFut", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": p.migas, "item": url}]},
        {"@context": "https://schema.org", "@type": "WebPage", "name": p.titulo, "url": url, "inLanguage": p.idioma,
         "description": p.descripcion, "dateModified": p.revision.isoformat(),
         "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
         "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}},
    ]


def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    return tuple((p.ruta, p.revision.isoformat()) for p in _PAGINAS.values() if idiomas.estado(p.idioma) == "on")


def script_url() -> str:
    """La caché de Cloudflare guarda los .js por su URL completa: el hash del contenido fuerza a pedir el nuevo al cambiarlo."""
    try:
        return f"{SCRIPT}?v={hashlib.sha1(ARCHIVO_SCRIPT.read_bytes()).hexdigest()[:10]}"
    except OSError:
        return SCRIPT


def render(idioma: str = "es") -> str:
    p = _pagina(idioma)
    base = seo.base_url()
    url = base + p.ruta
    ej = ejemplo(idioma=idioma)
    cuotas = [c for _, c in EJEMPLO]
    return _env.get_template(p.plantilla).render(
        p=p, url=url, base=base, jsonld=_jsonld(p, url, base), paginas=paginas.EN_POR_IDIOMA[idioma],
        og_imagen=og.url_marca() if idioma == "es" else None,
        idiomas_alt=idiomas.selector(p.ruta), robots=idiomas.robots_de(idioma),
        revision_iso=p.revision.isoformat(), revision_larga=paginas.fecha_larga(p.revision, idioma),
        ej=ej, script=script_url(), ejemplo_nombres=list(_NOMBRES_EJEMPLO[idioma]), ejemplo_cuotas=[n2(c, idioma) for c in cuotas])


def _servir(idioma: str) -> HTMLResponse:
    cab = {"Cache-Control": "public, max-age=300", "Content-Security-Policy": CSP, **idiomas.puerta(idioma)}
    return HTMLResponse(render(idioma), headers=cab)


def _sin_barra(request: Request, idioma: str) -> RedirectResponse:
    if idiomas.estado(idioma) == "off":
        raise HTTPException(404)
    destino = seo.base_url() + _PAGINAS[idioma].ruta + (f"?{request.url.query}" if request.url.query else "")
    return RedirectResponse(destino, status_code=301)


@router.api_route(RUTA, methods=["GET", "HEAD"], name="cuota_justa")
def cuota_justa_pagina():
    return _servir("es")


@router.api_route("/calculadora-cuota-justa", methods=["GET", "HEAD"], name="cuota_justa_sin_barra")
def cuota_justa_sin_barra(request: Request):
    return _sin_barra(request, "es")


@router.api_route(_PAGINAS["en"].ruta, methods=["GET", "HEAD"], name="cuota_justa_en")
def cuota_justa_en_pagina():
    return _servir("en")


@router.api_route(f"/{_PAGINAS['en'].slug}", methods=["GET", "HEAD"], name="cuota_justa_en_sin_barra")
def cuota_justa_en_sin_barra(request: Request):
    return _sin_barra(request, "en")


@router.api_route(_PAGINAS["pt"].ruta, methods=["GET", "HEAD"], name="cuota_justa_pt")
def cuota_justa_pt_pagina():
    return _servir("pt")


@router.api_route(f"/{_PAGINAS['pt'].slug}", methods=["GET", "HEAD"], name="cuota_justa_pt_sin_barra")
def cuota_justa_pt_sin_barra(request: Request):
    return _sin_barra(request, "pt")
