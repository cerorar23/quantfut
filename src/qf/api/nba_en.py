"""Páginas públicas de NBA en INGLÉS (F6.2 de docs/plan_seo_redes_web_20261108.md, §9): `/en/nba/` y `/en/nba/{slug}/`.

Son páginas independientes, no la aplicación de una sola página: la app pinta todo en español al cargar su JavaScript, y una versión inglesa
que se volviera española incumpliría la regla del plan («100 % del contenido en ese idioma»). Salen de `paginas/base_en.html`.

Reutilizan los DATOS y las reglas de `nba_paginas.py` (estado del partido, veredicto, ventana de la cartelera) para que las dos versiones digan
exactamente lo mismo; aquí solo cambia la redacción, el formato (`50%`, `0.25`, `Nov 9, 2026`) y el idioma. El español no se toca.

Mismo slug tras el prefijo (`/nba/chicago-bulls-vs-philadelphia-76ers-2026-11-08/` ↔ `/en/nba/…/`), así el hreflang es mecánico.
Detrás del interruptor de idioma (`idiomas.py`): apagado = 404; vista previa = `noindex`; abierto = indexable y en el sitemap.
Sin tarjeta para redes todavía (la imagen está escrita en español).
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

from . import idiomas, nba_datos, nba_paginas, og, paginas, seo
from .nba_datos import NbaNoDisponible

log = logging.getLogger("qf.nba_en")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA_PILAR = "/en/nba/"
RUTA_PILAR_ES = nba_paginas.RUTA_PILAR
PREFIJO = "/en"


# --- formato inglés ---------------------------------------------------------------------------------

def pct(p: float) -> str:
    return f"{round(p * 100)}%"


def num(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}"


def entero(x: float) -> str:
    return str(int(round(x)))


def fecha_larga(d: date) -> str:
    return paginas.fecha_larga(d, "en")


def fecha_corta(d: date) -> str:
    return f"{paginas.MONTHS_EN[d.month - 1][:3]} {d.day}, {d.year}"


def fecha_hora_utc(dt: datetime) -> str:
    u = dt.astimezone(timezone.utc)
    return f"{paginas.MONTHS_EN[u.month - 1][:3]} {u.day}, {u.year} at {u:%H:%M} UTC"


# --- equivalencias español ↔ inglés (para hreflang y selector) ---------------------------------------

_RUTA_PARTIDO = re.compile(r"^(?P<en>/en)?/nba/(?P<slug>[^/]+)/$")


def equivalencias(ruta: str) -> dict[str, str] | None:
    if ruta in (RUTA_PILAR, RUTA_PILAR_ES):
        return {"es": RUTA_PILAR_ES, "en": RUTA_PILAR}
    m = _RUTA_PARTIDO.match(ruta)
    if m and nba_datos.SLUG_PARTIDO.match(m["slug"]):
        return {"es": f"/nba/{m['slug']}/", "en": f"{PREFIJO}/nba/{m['slug']}/"}
    return None


idiomas.registrar_traductor(equivalencias)


# --- interpretación de un partido (la redacción, en inglés) -------------------------------------------

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
            texto_racha = f"{abs(racha)}-game {'winning' if racha > 0 else 'losing'} streak"
        else:
            texto_racha = "—"
        dias = t.get("rest_days")
        filas.append({
            "nombre": nombre,
            "record": f"{t['season']['won']}-{t['season']['lost']}",
            "ultimos6": f"{t['last6']['won']}-{t['last6']['lost']}",
            "racha": texto_racha,
            "descanso": "second game in two nights" if t.get("back_to_back") else (
                f"{dias} {'day' if dias == 1 else 'days'} of rest" if isinstance(dias, int) else "—"),
        })
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
        texto_margen = "The median margin is 0: the model does not lean towards either side."
    else:
        favorecido = local if margen > 0 else visit
        texto_margen = f"The median margin is {entero(abs(margen))} points in favor of {favorecido}."
    a, b = pr["margen_p10_p90"], pr["total_p10_p90"]
    slug = nba_datos.slug_partido(p)
    url = f"{seo.base_url()}{PREFIJO}/nba/{slug}/"
    titulo = f"{local} vs {visit}: prediction for {fecha_corta(fecha)}"
    if st == "final":
        titulo = f"{local} vs {visit}: prediction and result for {fecha_corta(fecha)}"
    descripcion = (f"Win probability: {local} {pct(pl)} and {visit} {pct(1 - pl)}. Expected score, margin range and a "
                   f"forecast sealed with a hash before tip-off.")
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=f"{local} vs {visit}"),
        id=p["id"], slug=slug, url=url, local=local, visitante=visit, fecha=fecha, estado=st, veredicto=ver,
        inicio=inicio, sellado=sellado, resultado=p.get("resultado"),
        prob_local=pl, p_local=pct(pl), p_visit=pct(1 - pl), mu_local=num(pr["mu"][0]), mu_visit=num(pr["mu"][1]),
        texto_margen=texto_margen,
        margen_rango=f"{entero(a[0])} and {'+' if a[1] > 0 else ''}{entero(a[1])}",
        total_mediana=entero(pr["mediana"]["total"]), total_rango=f"{entero(b[0])} and {entero(b[1])}",
        hash=pr["hash"], version=str(pr.get("version_modelo", "")).split(";")[0],
        contexto=_contexto_equipos(p), brier=num(ver["brier"], 3) if ver else None,
        sellado_txt=fecha_hora_utc(sellado) if sellado else "—", inicio_txt=fecha_hora_utc(inicio) if inicio else None)


def _organizacion() -> dict:
    return {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}


def _jsonld_partido(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo,
           "inLanguage": "en", "description": c.p.descripcion,
           "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"}, "publisher": _organizacion(),
           "about": {"@type": "SportsEvent", "name": f"{c.local} vs {c.visitante}", "sport": "Basketball",
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


# --- pilar ----------------------------------------------------------------------------------------

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
            dias.append({"fecha": d, "iso": d.isoformat(), "largo": fecha_larga(d), "filas": filas, "proximo": d >= hoy})
    juzgados = [f["veredicto"] for dia in dias for f in dia["filas"] if f["veredicto"]]
    base = seo.base_url()
    url = base + RUTA_PILAR
    pagina = SimpleNamespace(
        titulo="NBA predictions: win probabilities for every game",
        descripcion=("Win probability, expected score and margin range for every NBA game, sealed with a hash before tip-off. "
                     "With the hits and the misses in plain view."),
        slug="nba", migas="NBA")
    return SimpleNamespace(p=pagina, url=url, dias=dias, aciertos=sum(1 for v in juzgados if v["acerto"]),
                           juzgados=len(juzgados), con_pronostico=sum(1 for dia in dias for f in dia["filas"] if f["url"]),
                           jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                               {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
                               {"@type": "ListItem", "position": 2, "name": "NBA", "item": url}]},
                               {"@context": "https://schema.org", "@type": "CollectionPage", "name": pagina.titulo, "url": url,
                                "inLanguage": "en", "description": pagina.descripcion,
                                "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"}, "publisher": _organizacion()}])


# --- sitemap --------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Solo con el inglés abierto (`on`): el pilar y los partidos con sello de la misma ventana que el español, con el mismo `lastmod`."""
    if idiomas.estado("en") != "on":
        return ()
    return tuple((equivalencias(ruta)["en"], lastmod) for ruta, lastmod in nba_paginas.entradas_sitemap())


# --- rutas ----------------------------------------------------------------------------------------

def _responder(plantilla: str, p: SimpleNamespace, url: str, jsonld: list[dict], ruta: str, og_imagen: str | None = None, **ctx) -> HTMLResponse:
    from . import web_config

    cab = idiomas.puerta("en")
    cab.setdefault("Cache-Control", "no-cache, must-revalidate")
    cab["Content-Security-Policy"] = paginas.CSP
    wctx = web_config.base_template_ctx(lang="en")
    cuerpo = _env.get_template(plantilla).render(
        p=p, url=url, base=seo.base_url(), jsonld=web_config.apply_org_jsonld(jsonld, wctx["cfg"]),
        paginas=paginas.PAGINAS_EN, og_imagen=og_imagen,
        idiomas_alt=idiomas.selector(ruta), robots=idiomas.robots_de("en"), **wctx, **ctx)
    return HTMLResponse(cuerpo, headers=cab)


def _no_disponible() -> HTTPException:
    # 503, no 404: un fallo pasajero del motor no debe retirar la página del índice.
    return HTTPException(503, detail="NBA data is not available right now.", headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route(RUTA_PILAR, methods=["GET", "HEAD"], name="en_nba_pilar")
def pilar():
    from . import web_config

    idiomas.puerta("en")
    try:
        c = construir_pilar()
    except NbaNoDisponible:
        raise _no_disponible()
    c.p, entradilla_override = web_config.apply_editorial_meta(c.p, "sport:nba", "en")
    return _responder("en_nba_cartelera.html", c.p, c.url, c.jsonld, RUTA_PILAR,
                      og_imagen=og.url_pilar_en("nba"), c=c, entradilla_override=entradilla_override)


@router.api_route(RUTA_PILAR.rstrip("/"), methods=["GET", "HEAD"], name="en_nba_pilar_sin_barra")
def pilar_sin_barra(request: Request):
    idiomas.puerta("en")
    return RedirectResponse(seo.base_url() + RUTA_PILAR + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


@router.api_route("/en/nba/{slug}/", methods=["GET", "HEAD"], name="en_nba_partido")
def partido(slug: str):
    idiomas.puerta("en")
    if not nba_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    try:
        p = nba_datos.buscar_partido(slug)
    except NbaNoDisponible:
        raise _no_disponible()
    if p is None:
        raise HTTPException(404)
    c = construir(p)
    imagen = og.url_partido(f"{PREFIJO}/nba/{c.slug}/", nba_paginas.estado_imagen(c))
    return _responder("en_nba_partido.html", c.p, c.url, _jsonld_partido(c, seo.base_url()), f"{PREFIJO}/nba/{c.slug}/",
                      og_imagen=imagen, c=c)


@router.api_route("/en/nba/{slug}", methods=["GET", "HEAD"], name="en_nba_partido_sin_barra")
def partido_sin_barra(slug: str, request: Request):
    idiomas.puerta("en")
    if not nba_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}/en/nba/{slug}/" + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


# --- tarjeta para redes (en inglés) -------------------------------------------------------------------

def tarjeta(c: SimpleNamespace) -> "og.Tarjeta":
    final = nba_paginas.estado_imagen(c) == "final"
    r = c.resultado
    return og.Tarjeta("partido", etiqueta="NBA", local=c.local, visitante=c.visitante, contexto=f"NBA · {fecha_corta(c.fecha)}",
                      barra=[(c.local, c.prob_local), (c.visitante, 1 - c.prob_local)], estado=nba_paginas.estado_imagen(c),
                      marcador=f"{int(r['local'])} – {int(r['visitante'])}" if final and r else "",
                      veredicto=(("acerto" if c.veredicto["acerto"] else "fallo") if final and c.veredicto else None), idioma="en")


def tarjeta_de_la_url(slug: str):
    p = nba_datos.buscar_partido(slug)
    return tarjeta(construir(p)) if p else None
