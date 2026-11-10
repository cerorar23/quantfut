"""Páginas públicas de NBA en PORTUGUÉS de Brasil (F6.4b de docs/plan_seo_redes_web_20261108.md, §9): `/pt/nba/` y `/pt/nba/{slug}/`.

Igual que `nba_en.py`: páginas independientes sobre `base_pt.html`, con los mismos datos y las mismas reglas que el español
(`nba_paginas.py`). Aquí cambian la redacción, el formato (cifras con coma decimal, `62%`, `8 de novembro de 2026`) y el idioma.
El español no se toca. Detrás del interruptor de idiomas (`idiomas.py`): `off` = 404; `preview` = `noindex`; `on` = indexable.

Glosario: previsão = forecast; mandante/visitante = home/away; campanha = record; sequência = streak; descanso = rest.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import idiomas, nba_datos, nba_paginas, paginas, seo
from .nba_datos import NbaNoDisponible

log = logging.getLogger("qf.nba_pt")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA_PILAR = "/pt/nba/"
RUTA_PILAR_ES = nba_paginas.RUTA_PILAR
PREFIJO = "/pt"


# --- formato português ------------------------------------------------------------------------------

def pct(p: float) -> str:
    return f"{round(p * 100)}%"


def num(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def entero(x: float) -> str:
    return str(int(round(x)))


def fecha_hora_utc(dt: datetime) -> str:
    u = dt.astimezone(timezone.utc)
    return f"{paginas.fecha_larga(u.date(), 'pt')} às {u:%H:%M} UTC"


# --- equivalencias español ↔ portugués (hreflang y selector) --------------------------------------------

_RUTA_PARTIDO = re.compile(r"^(?P<pt>/pt)?/nba/(?P<slug>[^/]+)/$")


def equivalencias(ruta: str) -> dict[str, str] | None:
    if ruta in (RUTA_PILAR, RUTA_PILAR_ES):
        return {"es": RUTA_PILAR_ES, "pt": RUTA_PILAR}
    m = _RUTA_PARTIDO.match(ruta)
    if m and nba_datos.SLUG_PARTIDO.match(m["slug"]):
        return {"es": f"/nba/{m['slug']}/", "pt": f"{PREFIJO}/nba/{m['slug']}/"}
    return None


idiomas.registrar_traductor(equivalencias)


# --- interpretación de un partido -----------------------------------------------------------------------

def _contexto_equipos(p: dict) -> list[dict]:
    datos = nba_datos.estadisticas(p["id"], date.fromisoformat(p["fecha"]))
    equipos = {t.get("name"): t for t in (datos or {}).get("teams", []) if isinstance(t, dict)}
    filas = []
    for clave in ("local", "visitante"):
        nombre = p[clave]["nombre"]
        t = equipos.get(nombre)
        if not t or not isinstance(t.get("season"), dict) or not isinstance(t.get("last6"), dict):
            return []   # sin los dos equipos completos no se muestra una tabla a medias
        racha = t.get("streak") or 0
        if racha:
            texto_racha = f"sequência de {abs(racha)} " + ("vitórias seguidas" if racha > 0 else "derrotas seguidas")
        else:
            texto_racha = "—"
        dias = t.get("rest_days")
        if t.get("back_to_back"):
            descanso = "segundo jogo em duas noites seguidas"
        elif isinstance(dias, int):
            descanso = f"{dias} {'dia' if dias == 1 else 'dias'} de descanso"
        else:
            descanso = "—"
        filas.append({"nombre": nombre, "record": f"{t['season']['won']}-{t['season']['lost']}",
                      "ultimos6": f"{t['last6']['won']}-{t['last6']['lost']}", "racha": texto_racha, "descanso": descanso})
    return filas


def construir(p: dict, ahora: datetime | None = None) -> SimpleNamespace:
    ahora = ahora or nba_paginas._ahora()
    pr = p["pronostico"]
    local, visit = p["local"]["nombre"], p["visitante"]["nombre"]
    fecha = date.fromisoformat(p["fecha"])
    inicio, sellado = nba_paginas._dt(p.get("inicio_utc")), nba_paginas._dt(pr.get("sellado_en"))
    st = nba_paginas.estado(p, ahora)
    ver = nba_paginas.veredicto(p)
    pl = pr["p_local"]
    margen = pr["mediana"]["margen"]
    if margen == 0:
        texto_margen = "A mediana da margem é 0: o modelo não inclina o jogo para nenhum dos lados."
    else:
        favorecido = local if margen > 0 else visit
        texto_margen = f"A mediana da margem é de {entero(abs(margen))} pontos a favor do {favorecido}."
    a, b = pr["margen_p10_p90"], pr["total_p10_p90"]
    slug = nba_datos.slug_partido(p)
    url = f"{seo.base_url()}{PREFIJO}/nba/{slug}/"
    titulo = f"{local} x {visit}: previsão {paginas.fecha_larga(fecha, 'pt')}"
    if st == "final":
        titulo = f"{local} x {visit}: previsão e resultado, {paginas.fecha_larga(fecha, 'pt')}"
    descripcion = (f"Probabilidade de vitória: {local} {pct(pl)} e {visit} {pct(1 - pl)}. Placar esperado, faixa de margens e "
                   f"previsão selada com impressão digital antes do jogo.")
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=f"{local} x {visit}"),
        id=p["id"], slug=slug, url=url, local=local, visitante=visit, fecha=fecha, estado=st, veredicto=ver,
        inicio=inicio, sellado=sellado, resultado=p.get("resultado"),
        p_local=pct(pl), p_visit=pct(1 - pl), mu_local=num(pr["mu"][0]), mu_visit=num(pr["mu"][1]),
        texto_margen=texto_margen,
        margen_rango=f"{entero(a[0])} e {'+' if a[1] > 0 else ''}{entero(a[1])}",
        total_mediana=entero(pr["mediana"]["total"]), total_rango=f"{entero(b[0])} e {entero(b[1])}",
        hash=pr["hash"], version=str(pr.get("version_modelo", "")).split(";")[0],
        contexto=_contexto_equipos(p), brier=num(ver["brier"], 3) if ver else None,
        sellado_txt=fecha_hora_utc(sellado) if sellado else "—", inicio_txt=fecha_hora_utc(inicio) if inicio else None)


def _organizacion() -> dict:
    return {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}


def _jsonld_partido(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo,
           "inLanguage": "pt", "description": c.p.descripcion,
           "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"}, "publisher": _organizacion(),
           "about": {"@type": "SportsEvent", "name": f"{c.local} x {c.visitante}", "sport": "Basketball",
                     "eventStatus": "https://schema.org/EventScheduled",
                     "homeTeam": {"@type": "SportsTeam", "name": c.local},
                     "awayTeam": {"@type": "SportsTeam", "name": c.visitante}}}
    if c.inicio:
        web["about"]["startDate"] = c.inicio.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if c.sellado:
        web["datePublished"] = c.sellado.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "NBA", "item": f"{base}{RUTA_PILAR}"},
        {"@type": "ListItem", "position": 3, "name": c.p.migas, "item": c.url}]}, web]


# --- pilar ----------------------------------------------------------------------------------------------

def _fila(p: dict, ahora: datetime) -> dict:
    pr = p.get("pronostico")
    f = {"local": p["local"]["nombre"], "visitante": p["visitante"]["nombre"],
         "inicio": nba_paginas._dt(p.get("inicio_utc")), "estado": nba_paginas.estado(p, ahora), "resultado": p.get("resultado"),
         "url": f"{PREFIJO}/nba/{nba_datos.slug_partido(p)}/" if pr else None, "veredicto": nba_paginas.veredicto(p)}
    if pr:
        f["p_local"], f["p_visit"] = pct(pr["p_local"]), pct(1 - pr["p_local"])
    return f


def construir_pilar(ahora: datetime | None = None, ventana: dict[date, list[dict]] | None = None) -> SimpleNamespace:
    ahora = ahora or nba_paginas._ahora()
    hoy = nba_datos.hoy_et(ahora)
    ventana = ventana if ventana is not None else nba_paginas._ventana(hoy)
    dias = []
    for d in sorted(ventana, reverse=True):
        filas = [_fila(p, ahora) for p in sorted(ventana[d], key=lambda x: x.get("inicio_utc") or "")]
        if filas:
            dias.append({"fecha": d, "iso": d.isoformat(), "largo": paginas.fecha_larga(d, "pt"), "filas": filas, "proximo": d >= hoy})
    juzgados = [f["veredicto"] for dia in dias for f in dia["filas"] if f["veredicto"]]
    base = seo.base_url()
    url = base + RUTA_PILAR
    pagina = SimpleNamespace(
        titulo="Previsões da NBA: probabilidade de vitória de cada jogo",
        descripcion=("Probabilidade de vitória, placar esperado e faixa de margens de cada jogo da NBA, selados com impressão "
                     "digital antes do início. Com os acertos e os erros à vista."),
        slug="nba", migas="NBA")
    return SimpleNamespace(p=pagina, url=url, dias=dias, aciertos=sum(1 for v in juzgados if v["acerto"]),
                           juzgados=len(juzgados), con_pronostico=sum(1 for dia in dias for f in dia["filas"] if f["url"]),
                           jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                               {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
                               {"@type": "ListItem", "position": 2, "name": "NBA", "item": url}]},
                               {"@context": "https://schema.org", "@type": "CollectionPage", "name": pagina.titulo, "url": url,
                                "inLanguage": "pt", "description": pagina.descripcion,
                                "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"}, "publisher": _organizacion()}])


# --- sitemap --------------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Solo con el portugués abierto (`on`): el pilar y los partidos con sello, con el mismo `lastmod` que el español."""
    if idiomas.estado("pt") != "on":
        return ()
    return tuple((equivalencias(ruta)["pt"], lastmod) for ruta, lastmod in nba_paginas.entradas_sitemap())


# --- rutas ----------------------------------------------------------------------------------------------

def _responder(plantilla: str, p: SimpleNamespace, url: str, jsonld: list[dict], ruta: str, **ctx) -> HTMLResponse:
    cab = idiomas.puerta("pt")
    cab.setdefault("Cache-Control", "no-cache, must-revalidate")
    cab["Content-Security-Policy"] = paginas.CSP
    cuerpo = _env.get_template(plantilla).render(
        p=p, url=url, base=seo.base_url(), jsonld=jsonld, paginas=paginas.PAGINAS_PT, og_imagen=None,
        idiomas_alt=idiomas.selector(ruta), robots=idiomas.robots_de("pt"), **ctx)
    return HTMLResponse(cuerpo, headers=cab)


def _no_disponible() -> HTTPException:
    return HTTPException(503, detail="Os dados da NBA não estão disponíveis no momento.",
                         headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route(RUTA_PILAR, methods=["GET", "HEAD"], name="pt_nba_pilar")
def pilar():
    idiomas.puerta("pt")
    try:
        c = construir_pilar()
    except NbaNoDisponible:
        raise _no_disponible()
    return _responder("pt_nba_cartelera.html", c.p, c.url, c.jsonld, RUTA_PILAR, c=c)


@router.api_route(RUTA_PILAR.rstrip("/"), methods=["GET", "HEAD"], name="pt_nba_pilar_sin_barra")
def pilar_sin_barra(request: Request):
    idiomas.puerta("pt")
    return RedirectResponse(seo.base_url() + RUTA_PILAR + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


@router.api_route("/pt/nba/{slug}/", methods=["GET", "HEAD"], name="pt_nba_partido")
def partido(slug: str):
    idiomas.puerta("pt")
    if not nba_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    try:
        p = nba_datos.buscar_partido(slug)
    except NbaNoDisponible:
        raise _no_disponible()
    if p is None:
        raise HTTPException(404)
    c = construir(p)
    return _responder("pt_nba_partido.html", c.p, c.url, _jsonld_partido(c, seo.base_url()), f"{PREFIJO}/nba/{c.slug}/", c=c)


@router.api_route("/pt/nba/{slug}", methods=["GET", "HEAD"], name="pt_nba_partido_sin_barra")
def partido_sin_barra(slug: str, request: Request):
    idiomas.puerta("pt")
    if not nba_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}/pt/nba/{slug}/" + (f"?{request.url.query}" if request.url.query else ""), status_code=301)
