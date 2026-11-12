"""Páginas de equipo de NBA en INGLÉS (F6.2d de docs/plan_seo_redes_web_20261108.md, §9): `/en/nba/equipos/{equipo}/`.

Igual que `nba_en.py`: página independiente sobre `base_en.html`. Reutiliza el índice, el UMBRAL y las reglas de `nba_equipos.py`
(qué partidos cuentan, qué es un acierto, cuándo una página es indexable), así que las dos versiones de un equipo siempre dicen lo mismo.
Por debajo del umbral lleva `noindex` igual que el español y no entra en el sitemap. El español no se toca.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..comercial import catalogo
from . import idiomas, nba_datos, nba_equipos, nba_paginas, paginas, seo
from .nba_datos import NbaNoDisponible

log = logging.getLogger("qf.nba_equipo_en")
router = APIRouter(include_in_schema=False, dependencies=[Depends(catalogo.exigir_web('nba'))])
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

PREFIJO = "/en"


def ruta_equipo(slug: str) -> str:
    return f"{PREFIJO}/nba/equipos/{slug}/"


# --- equivalencias español ↔ inglés (hreflang y selector) ---------------------------------------------

def equivalencias(ruta: str) -> dict[str, str] | None:
    partes = ruta.strip("/").split("/")
    if len(partes) == 3 and partes[:2] == ["nba", "equipos"]:          # /nba/equipos/{slug}/
        slug = partes[2]
        return {"es": f"/nba/equipos/{slug}/", "en": f"{PREFIJO}/nba/equipos/{slug}/"}
    if len(partes) == 4 and partes[:3] == ["en", "nba", "equipos"]:    # /en/nba/equipos/{slug}/
        slug = partes[3]
        return {"es": f"/nba/equipos/{slug}/", "en": f"{PREFIJO}/nba/equipos/{slug}/"}
    return None


idiomas.registrar_traductor(equivalencias)


# --- formato y contenido en inglés (las mismas reglas que nba_equipos) --------------------------------

def _fecha(d: date) -> str:
    return f"{paginas.MONTHS_EN[d.month - 1][:3]} {d.day}, {d.year}"


def _racha(n: int) -> str:
    if not n:
        return "—"
    return f"{abs(n)}-game {'winning' if n > 0 else 'losing'} streak"


def _fila(p: dict, nombre: str, ahora: datetime) -> dict:
    es_local = p["local"]["nombre"] == nombre
    rival = p["visitante"]["nombre"] if es_local else p["local"]["nombre"]
    res = p.get("resultado")
    pe = nba_equipos._prob_equipo(p, nombre)
    fila = {"fecha": date.fromisoformat(p["fecha"]), "fecha_txt": _fecha(date.fromisoformat(p["fecha"])), "rival": rival, "local": es_local, "p": f"{round(pe * 100)}%",
            "estado": nba_paginas.estado(p, ahora), "url": f"{PREFIJO}/nba/{nba_datos.slug_partido(p)}/",
            "resultado": None, "gano": None, "acerto": None}
    if res:
        mios, suyos = (res["local"], res["visitante"]) if es_local else (res["visitante"], res["local"])
        if mios != suyos:
            fila.update(resultado=f"{int(mios)} – {int(suyos)}", gano=mios > suyos)
            fila["acerto"] = (pe >= 0.5) == (mios > suyos)
    return fila


def construir(slug: str, equipos: dict[str, dict], ahora: datetime | None = None) -> SimpleNamespace | None:
    ahora = ahora or nba_paginas._ahora()
    e = equipos.get(slug)
    if not e:
        return None
    nombre, partidos = e["nombre"], e["partidos"]
    filas = [_fila(p, nombre, ahora) for p in partidos]
    juzgadas = [f for f in filas if f["acerto"] is not None]
    proximos = [f for f in filas if f["estado"] in ("previa", "curso", "pendiente")]
    ultimo = partidos[0]
    contexto = None
    stats = nba_datos.estadisticas(ultimo["id"], date.fromisoformat(ultimo["fecha"]))
    for t in (stats or {}).get("teams", []):
        if isinstance(t, dict) and t.get("name") == nombre and isinstance(t.get("season"), dict) and isinstance(t.get("last6"), dict):
            contexto = {"record": f"{t['season']['won']}-{t['season']['lost']}", "ultimos6": f"{t['last6']['won']}-{t['last6']['lost']}",
                        "racha": _racha(t.get("streak") or 0)}
    ind = nba_equipos.indexable(e)
    base = seo.base_url()
    ruta = ruta_equipo(slug)
    titulo = f"{nombre}: NBA predictions and how the model has done"
    descripcion = (f"Sealed NBA forecasts for {nombre}: win probability in each game, the result, and the model's hits and misses, "
                   f"with a link to every game.")
    sellados = [s for s in (nba_paginas._dt(p["pronostico"].get("sellado_en")) for p in partidos) if s]
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=nombre), nombre=nombre, slug=slug, ruta=ruta,
        url=base + ruta, total=len(partidos), indexable=ind, umbral=nba_equipos.UMBRAL, dias=nba_equipos.DIAS_HISTORIA,
        filas=filas[:nba_equipos.ULTIMOS], hay_mas=len(filas) > nba_equipos.ULTIMOS, juzgados=len(juzgadas),
        aciertos=sum(1 for f in juzgadas if f["acerto"]), victorias=sum(1 for f in juzgadas if f["gano"]),
        proximo=proximos[-1] if proximos else None, contexto=contexto,
        ultimo_sello=max(sellados) if sellados else None)


def _jsonld(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo, "inLanguage": "en",
           "description": c.p.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
           "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"},
           "about": {"@type": "SportsTeam", "name": c.nombre, "sport": "Basketball"}}
    if c.ultimo_sello:
        web["dateModified"] = c.ultimo_sello.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "NBA", "item": f"{base}{PREFIJO}/nba/"},
        {"@type": "ListItem", "position": 3, "name": c.nombre, "item": c.url}]}, web]


# --- sitemap --------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Solo con el inglés abierto (`on`) y solo los equipos que superan el umbral, con el mismo `lastmod` que el español."""
    if idiomas.estado("en") != "on":
        return ()
    return tuple((PREFIJO + ruta, lastmod) for ruta, lastmod in nba_equipos.entradas_sitemap())


# --- rutas ---------------------------------------------------------------------------------------

def _no_disponible() -> HTTPException:
    return HTTPException(503, detail="NBA data is not available right now.", headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route("/en/nba/equipos/{equipo}/", methods=["GET", "HEAD"], name="en_nba_equipo")
def equipo(equipo: str):
    cab = idiomas.puerta("en")
    try:
        c = construir(equipo, nba_equipos.indice())
    except NbaNoDisponible:
        raise _no_disponible()
    if c is None:
        raise HTTPException(404)
    principal = _env.get_template("en_nba_equipo.html").render(p=c.p, c=c)
    # `noindex` salvo que el equipo supere el umbral Y el inglés esté abierto (`on`); en vista previa nada se indexa.
    indexable = c.indexable and idiomas.estado("en") == "on"
    cuerpo = _pagina_completa(c, principal, nba_equipos.ROBOTS_INDEXABLE if indexable else nba_equipos.ROBOTS_BAJO_UMBRAL)
    cab.setdefault("Cache-Control", "no-cache, must-revalidate")
    cab["Content-Security-Policy"] = paginas.CSP
    return HTMLResponse(cuerpo, headers=cab)


def _pagina_completa(c: SimpleNamespace, principal: str, robots: str) -> str:
    """La plantilla inglesa con el contenido ya renderizado en el bloque `contenido`."""
    plantilla = _env.from_string(
        '{% extends "base_en.html" %}{% block revision_p %}{% endblock %}{% block contenido %}{{ principal|safe }}{% endblock %}')
    return plantilla.render(p=c.p, url=c.url, base=seo.base_url(), jsonld=_jsonld(c, seo.base_url()), paginas=paginas.PAGINAS_EN,
                            og_imagen=None, idiomas_alt=idiomas.selector(c.ruta), robots=robots, principal=principal)


@router.api_route("/en/nba/equipos/{equipo}", methods=["GET", "HEAD"], name="en_nba_equipo_sin_barra")
def equipo_sin_barra(equipo: str, request: Request):
    idiomas.puerta("en")
    if not nba_datos.slug_texto(equipo) == equipo:
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}{ruta_equipo(equipo)}" + (f"?{request.url.query}" if request.url.query else ""), status_code=301)
