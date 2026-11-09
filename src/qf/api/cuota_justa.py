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

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import og, paginas, seo

log = logging.getLogger("qf.cuota_justa")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA = "/calculadora-cuota-justa/"
REVISION = date(2026, 11, 9)
SCRIPT = "/static/cuota-justa.js"
ARCHIVO_SCRIPT = Path(__file__).with_name("static") / "cuota-justa.js"
# La política de las páginas de confianza ya admite el script PROPIO (`script-src 'self'`): sin 'unsafe-inline' en scripts, sin conexiones
# (la calculadora no envía nada a ningún sitio), sin Pixel de Meta.
CSP = paginas.CSP

# Ejemplo resuelto que se muestra sin JavaScript (cuotas típicas de un 1X2 con margen).
EJEMPLO = (("Local", 2.10), ("Empate", 3.40), ("Visitante", 3.60))


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

def n2(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def pct(x: float) -> str:
    return f"{x * 100:.2f} %".replace(".", ",")


def ejemplo(metodo: str = "shin") -> dict:
    cuotas = [c for _, c in EJEMPLO]
    imp = [1.0 / c for c in cuotas]
    sm = sin_margen(cuotas, metodo)
    filas = [{"nombre": n, "cuota": n2(c), "implicita": pct(i), "sin_margen": pct(p), "justa": n2(cuota_justa(p))}
             for (n, c), i, p in zip(EJEMPLO, imp, sm)]
    total = sum(imp)
    return {"filas": filas, "suma": pct(total), "margen": pct(total - 1.0), "suma_sin_margen": pct(sum(sm)),
            "metodo": metodo, "datos": {"cuotas": cuotas, "implicitas": imp, "sin_margen": sm, "total": total}}


# --- página --------------------------------------------------------------------------------------

def _pagina() -> paginas.Pagina:
    return paginas.Pagina(
        "calculadora-cuota-justa", "cuota_justa.html",
        "Calculadora de cuota justa: de cuota a probabilidad",
        "Convierte cuotas en probabilidades y al revés, y descubre cuánto margen lleva una cuota (1X2 o dos resultados). "
        "Herramienta educativa: no calcula importes de apuesta.",
        "Cuota justa", REVISION)


def _jsonld(p: paginas.Pagina, url: str, base: str) -> list[dict]:
    return [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": p.migas, "item": url}]},
        {"@context": "https://schema.org", "@type": "WebPage", "name": p.titulo, "url": url, "inLanguage": "es",
         "description": p.descripcion, "dateModified": REVISION.isoformat(),
         "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
         "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}},
    ]


def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    return ((RUTA, REVISION.isoformat()),)


def script_url() -> str:
    """La caché de Cloudflare guarda los .js por su URL completa: el hash del contenido fuerza a pedir el nuevo al cambiarlo."""
    try:
        return f"{SCRIPT}?v={hashlib.sha1(ARCHIVO_SCRIPT.read_bytes()).hexdigest()[:10]}"
    except OSError:
        return SCRIPT


def render() -> str:
    p = _pagina()
    base = seo.base_url()
    url = base + RUTA
    return _env.get_template("cuota_justa.html").render(
        p=p, url=url, base=base, jsonld=_jsonld(p, url, base), paginas=paginas.PAGINAS, og_imagen=og.url_marca(),
        revision_iso=REVISION.isoformat(), revision_larga=paginas.fecha_larga(REVISION),
        ej=ejemplo(), script=script_url(), ejemplo_nombres=[n for n, _ in EJEMPLO], ejemplo_cuotas=[n2(c) for _, c in EJEMPLO])


@router.api_route(RUTA, methods=["GET", "HEAD"], name="cuota_justa")
def cuota_justa_pagina():
    return HTMLResponse(render(), headers={"Cache-Control": "public, max-age=300", "Content-Security-Policy": CSP})


@router.api_route("/calculadora-cuota-justa", methods=["GET", "HEAD"], name="cuota_justa_sin_barra")
def cuota_justa_sin_barra(request: Request):
    return RedirectResponse(seo.base_url() + RUTA + (f"?{request.url.query}" if request.url.query else ""), status_code=301)
