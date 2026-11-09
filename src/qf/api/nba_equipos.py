"""Páginas de equipo de NBA (F2.2 de docs/plan_seo_redes_web_20261108.md): `/nba/equipos/<equipo>/`.

Cada página reúne los pronósticos SELLADOS en los que juega ese equipo (de `nba-api`, el mismo dato que las páginas de partido):
cuántos acertó el modelo, los últimos partidos con su resultado y el próximo, y la situación del equipo (récord, forma, racha)
a la fecha del último partido. Sin texto inventado: todo sale de esos datos.

Umbral contra páginas zombi (plan §3.3): una página es INDEXABLE solo si el equipo tiene al menos `UMBRAL` pronósticos sellados
en los últimos `DIAS_HISTORIA` días. Por debajo sigue existiendo (se puede abrir) pero lleva `noindex` y no entra en el sitemap
ni se enlaza desde las páginas de partido. El plan decía 12 meses; el motor NBA solo selló su primer pronóstico el 2-nov-2026, así
que la ventana es de 45 días y se medirá cuántos equipos la superan antes de ampliarla.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import nba_datos, nba_paginas, og, rutas_web, seo
from .nba_datos import NbaNoDisponible

log = logging.getLogger("qf.nba_equipos")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

UMBRAL = 5                                   # pronósticos sellados mínimos para indexar
DIAS_HISTORIA = 45
DESDE = date(2026, 11, 2)                    # primer día con pronósticos NBA sellados: antes no hay nada que pedir
ROBOTS_INDEXABLE = "index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1"
ROBOTS_BAJO_UMBRAL = "noindex, follow"
ULTIMOS = 10


def ruta_equipo(slug: str) -> str:
    return f"/nba/equipos/{slug}/"


def slug_equipo(nombre: str) -> str:
    return nba_datos.slug_texto(nombre)


def _dt(texto):
    return nba_paginas._dt(texto)


# --- datos ---------------------------------------------------------------------------------------

def indice(hoy: date | None = None) -> dict[str, dict]:
    """{slug: {nombre, partidos}} con los partidos SELLADOS de la ventana en los que juega cada equipo (más recientes primero)."""
    hoy = hoy or nba_datos.hoy_et(nba_paginas._ahora())
    desde = max(hoy - timedelta(days=DIAS_HISTORIA), DESDE)
    ventana = nba_datos.cartelera_ventana(desde, hoy + timedelta(days=1))
    equipos: dict[str, dict] = {}
    for d in sorted(ventana, reverse=True):
        for p in sorted(ventana[d], key=lambda x: x.get("inicio_utc") or "", reverse=True):
            if not p.get("pronostico"):
                continue
            for lado in ("local", "visitante"):
                nombre = p[lado]["nombre"]
                e = equipos.setdefault(slug_equipo(nombre), {"nombre": nombre, "partidos": []})
                e["partidos"].append(p)
    return equipos


def indexable(equipo: dict) -> bool:
    return len(equipo["partidos"]) >= UMBRAL


def enlace_si_indexable(nombre: str) -> str | None:
    """URL de la página del equipo solo si es indexable (no se enlaza lo que lleva `noindex`). Nunca rompe la página que lo pide."""
    try:
        e = indice().get(slug_equipo(nombre))
    except NbaNoDisponible:
        return None
    return ruta_equipo(slug_equipo(nombre)) if e and indexable(e) else None


# --- contenido -----------------------------------------------------------------------------------

def _prob_equipo(p: dict, nombre: str) -> float:
    pl = p["pronostico"]["p_local"]
    return pl if p["local"]["nombre"] == nombre else 1 - pl


def _fila(p: dict, nombre: str, ahora: datetime) -> dict:
    es_local = p["local"]["nombre"] == nombre
    rival = p["visitante"]["nombre"] if es_local else p["local"]["nombre"]
    res = p.get("resultado")
    pe = _prob_equipo(p, nombre)
    fila = {"fecha": date.fromisoformat(p["fecha"]), "rival": rival, "local": es_local, "p": nba_paginas.pct(pe),
            "estado": nba_paginas.estado(p, ahora), "url": f"/nba/{nba_datos.slug_partido(p)}/", "resultado": None, "gano": None, "acerto": None}
    if res:
        mios, suyos = (res["local"], res["visitante"]) if es_local else (res["visitante"], res["local"])
        if mios != suyos:
            fila.update(resultado=f"{int(mios)} – {int(suyos)}", gano=mios > suyos)
            fila["acerto"] = (pe >= 0.5) == (mios > suyos)       # ¿ganó el equipo con más probabilidad?
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
            racha = t.get("streak") or 0
            contexto = {"record": f"{t['season']['won']}-{t['season']['lost']}", "ultimos6": f"{t['last6']['won']}-{t['last6']['lost']}",
                        "racha": (f"{abs(racha)} " + ("victorias" if racha > 0 else "derrotas") + " seguidas") if racha else "—"}
    ruta = ruta_equipo(slug)
    base = seo.base_url()
    ind = indexable(e)
    titulo = f"{nombre}: pronósticos de NBA y cómo ha acertado el modelo"
    descripcion = (f"Pronósticos sellados de {nombre} en la NBA: probabilidad de victoria en cada partido, resultado y aciertos y fallos "
                   f"del modelo, con enlace a cada partido.")
    sellados = [_dt(p["pronostico"].get("sellado_en")) for p in partidos]
    sellados = [s for s in sellados if s]
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=nombre), nombre=nombre, slug=slug, ruta=ruta, url=base + ruta,
        total=len(partidos), indexable=ind, umbral=UMBRAL, dias=DIAS_HISTORIA, filas=filas[:ULTIMOS], hay_mas=len(filas) > ULTIMOS,
        juzgados=len(juzgadas), aciertos=sum(1 for f in juzgadas if f["acerto"]), victorias=sum(1 for f in juzgadas if f["gano"]),
        proximo=proximos[-1] if proximos else None, contexto=contexto,
        ultimo_sello=max(sellados) if sellados else None)


def _jsonld(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo, "inLanguage": "es",
           "description": c.p.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
           "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"},
           "about": {"@type": "SportsTeam", "name": c.nombre, "sport": "Basketball"}}
    if c.ultimo_sello:
        web["dateModified"] = c.ultimo_sello.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "NBA", "item": f"{base}/nba/"},
        {"@type": "ListItem", "position": 3, "name": c.nombre, "item": c.url}]}, web]


# --- sitemap -------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Solo los equipos que superan el umbral. `lastmod` = día del último sello del equipo (verificable)."""
    try:
        equipos = indice()
    except NbaNoDisponible:
        return ()
    filas = []
    for slug in sorted(equipos):
        e = equipos[slug]
        if not indexable(e):
            continue
        sellos = [s for s in (_dt(p["pronostico"].get("sellado_en")) for p in e["partidos"]) if s]
        filas.append((ruta_equipo(slug), max(sellos).astimezone(timezone.utc).date().isoformat() if sellos else None))
    return tuple(filas)


# --- rutas ---------------------------------------------------------------------------------------

def _no_disponible() -> HTTPException:
    return HTTPException(503, detail="Los datos de NBA no están disponibles en este momento.",
                         headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route("/nba/equipos/{equipo}/", methods=["GET", "HEAD"], name="nba_equipo")
def equipo(equipo: str):
    try:
        c = construir(equipo, indice())
    except NbaNoDisponible:
        raise _no_disponible()
    if c is None:
        raise HTTPException(404)
    principal = _env.get_template("nba_equipo.html").render(p=c.p, c=c)
    url = og.url_pilar("nba")
    cuerpo = rutas_web.render_pagina(
        titulo=c.p.titulo, descripcion=c.p.descripcion, path=c.ruta, ruta="partidos", jsonld=_jsonld(c, seo.base_url()), principal=principal,
        datos={"deporte": "nba"}, imagen=(url, f"Pronósticos de {c.nombre} en la NBA") if url else None,
        robots=ROBOTS_INDEXABLE if c.indexable else ROBOTS_BAJO_UMBRAL)
    return HTMLResponse(cuerpo, headers={"Cache-Control": "no-cache, must-revalidate"})


@router.api_route("/nba/equipos/{equipo}", methods=["GET", "HEAD"], name="nba_equipo_sin_barra")
def equipo_sin_barra(equipo: str, request: Request):
    if not nba_datos.slug_texto(equipo) == equipo:
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}{ruta_equipo(equipo)}" + (f"?{request.url.query}" if request.url.query else ""), status_code=301)
