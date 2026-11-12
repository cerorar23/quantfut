"""Páginas de equipo de NBA en PORTUGUÉS (F6.4b de docs/plan_seo_redes_web_20261108.md): `/pt/nba/equipos/{equipo}/`.

Igual que `nba_equipo_en.py`: página independiente sobre `base_pt.html`. Reutiliza el índice, el UMBRAL y las reglas de
`nba_equipos.py`, así que las dos versiones de un equipo dicen lo mismo. Indexable solo si supera el umbral y el portugués está en
`on`. El español no se toca.
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

log = logging.getLogger("qf.nba_equipo_pt")
router = APIRouter(include_in_schema=False, dependencies=[Depends(catalogo.exigir_web('nba'))])
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

PREFIJO = "/pt"


def ruta_equipo(slug: str) -> str:
    return f"{PREFIJO}/nba/equipos/{slug}/"


# --- equivalencias español ↔ portugués --------------------------------------------------------------

def equivalencias(ruta: str) -> dict[str, str] | None:
    partes = ruta.strip("/").split("/")
    if len(partes) == 3 and partes[:2] == ["nba", "equipos"]:          # /nba/equipos/{slug}/
        slug = partes[2]
        return {"es": f"/nba/equipos/{slug}/", "pt": f"{PREFIJO}/nba/equipos/{slug}/"}
    if len(partes) == 4 and partes[:3] == ["pt", "nba", "equipos"]:    # /pt/nba/equipos/{slug}/
        slug = partes[3]
        return {"es": f"/nba/equipos/{slug}/", "pt": f"{PREFIJO}/nba/equipos/{slug}/"}
    return None


idiomas.registrar_traductor(equivalencias)


# --- contenido en portugués (mismas reglas que nba_equipos) -------------------------------------------

def _fecha(d: date) -> str:
    return paginas.fecha_larga(d, "pt")


def _racha(n: int) -> str:
    if not n:
        return "—"
    return f"sequência de {abs(n)} " + ("vitórias seguidas" if n > 0 else "derrotas seguidas")


def _fila(p: dict, nombre: str, ahora: datetime) -> dict:
    es_local = p["local"]["nombre"] == nombre
    rival = p["visitante"]["nombre"] if es_local else p["local"]["nombre"]
    res = p.get("resultado")
    pe = nba_equipos._prob_equipo(p, nombre)
    fila = {"fecha": date.fromisoformat(p["fecha"]), "fecha_txt": _fecha(date.fromisoformat(p["fecha"])), "rival": rival,
            "local": es_local, "p": f"{round(pe * 100)}%", "estado": nba_paginas.estado(p, ahora),
            "url": f"{PREFIJO}/nba/{nba_datos.slug_partido(p)}/", "resultado": None, "gano": None, "acerto": None}
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
    titulo = f"{nombre}: previsões da NBA e como o modelo tem se saído"
    descripcion = (f"Previsões seladas do {nombre} na NBA: probabilidade de vitória em cada jogo, resultado e acertos e erros "
                   f"do modelo, com link para cada jogo.")
    sellados = [s for s in (nba_paginas._dt(p["pronostico"].get("sellado_en")) for p in partidos) if s]
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=nombre), nombre=nombre, slug=slug, ruta=ruta,
        url=base + ruta, total=len(partidos), indexable=ind, umbral=nba_equipos.UMBRAL, dias=nba_equipos.DIAS_HISTORIA,
        filas=filas[:nba_equipos.ULTIMOS], hay_mas=len(filas) > nba_equipos.ULTIMOS, juzgados=len(juzgadas),
        aciertos=sum(1 for f in juzgadas if f["acerto"]), victorias=sum(1 for f in juzgadas if f["gano"]),
        proximo=proximos[-1] if proximos else None, contexto=contexto,
        ultimo_sello=max(sellados) if sellados else None)


def _jsonld(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo, "inLanguage": "pt",
           "description": c.p.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
           "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"},
           "about": {"@type": "SportsTeam", "name": c.nombre, "sport": "Basketball"}}
    if c.ultimo_sello:
        web["dateModified"] = c.ultimo_sello.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "NBA", "item": f"{base}{PREFIJO}/nba/"},
        {"@type": "ListItem", "position": 3, "name": c.nombre, "item": c.url}]}, web]


# --- sitemap y rutas -----------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Solo con el portugués abierto (`on`) y solo los equipos que superan el umbral."""
    if idiomas.estado("pt") != "on":
        return ()
    return tuple((PREFIJO + ruta, lastmod) for ruta, lastmod in nba_equipos.entradas_sitemap())


def _no_disponible() -> HTTPException:
    return HTTPException(503, detail="Os dados da NBA não estão disponíveis no momento.",
                         headers={"Retry-After": "60", "Cache-Control": "no-store"})


def _pagina_completa(c: SimpleNamespace, principal: str, robots: str) -> str:
    plantilla = _env.from_string(
        '{% extends "base_pt.html" %}{% block revision_p %}{% endblock %}{% block contenido %}{{ principal|safe }}{% endblock %}')
    return plantilla.render(p=c.p, url=c.url, base=seo.base_url(), jsonld=_jsonld(c, seo.base_url()), paginas=paginas.PAGINAS_PT,
                            og_imagen=None, idiomas_alt=idiomas.selector(c.ruta), robots=robots, principal=principal)


@router.api_route("/pt/nba/equipos/{equipo}/", methods=["GET", "HEAD"], name="pt_nba_equipo")
def equipo(equipo: str):
    cab = idiomas.puerta("pt")
    try:
        c = construir(equipo, nba_equipos.indice())
    except NbaNoDisponible:
        raise _no_disponible()
    if c is None:
        raise HTTPException(404)
    principal = _env.get_template("pt_nba_equipo.html").render(p=c.p, c=c)
    indexable = c.indexable and idiomas.estado("pt") == "on"
    cuerpo = _pagina_completa(c, principal, nba_equipos.ROBOTS_INDEXABLE if indexable else nba_equipos.ROBOTS_BAJO_UMBRAL)
    cab.setdefault("Cache-Control", "no-cache, must-revalidate")
    cab["Content-Security-Policy"] = paginas.CSP
    return HTMLResponse(cuerpo, headers=cab)


@router.api_route("/pt/nba/equipos/{equipo}", methods=["GET", "HEAD"], name="pt_nba_equipo_sin_barra")
def equipo_sin_barra(equipo: str, request: Request):
    idiomas.puerta("pt")
    if not nba_datos.slug_texto(equipo) == equipo:
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}{ruta_equipo(equipo)}" + (f"?{request.url.query}" if request.url.query else ""), status_code=301)
