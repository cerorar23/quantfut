"""Páginas públicas de tenis en INGLÉS (F6.2c de docs/plan_seo_redes_web_20261108.md, §9): `/en/tenis/` y `/en/tenis/{torneo}/{slug}/`.

Igual que `nba_en.py` y `futbol_en.py`: páginas independientes sobre `base_en.html`. Reutilizan la lógica del español de
`tenis_paginas.py` (`resultado`, `veredicto`, `estado`, `mercado_ganador`): la salvaguarda de que el ganador del mercado y los SETS
coincidan se aplica igual en las dos versiones. Aquí cambian la redacción, el formato y el idioma.

Las etiquetas de mercado y las selecciones vienen del feed en español («Ganador del partido», «Más de 18.5»); se traducen con una tabla
pequeña de los tipos que hoy publica el motor. Un tipo de mercado sin traducción se muestra tal cual y la prueba lo detecta.
El español no se toca.
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

from . import idiomas, og, paginas, seo, tenis_datos, tenis_paginas
from .tenis_datos import TenisNoDisponible

log = logging.getLogger("qf.tenis_en")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA_PILAR = "/en/tenis/"
RUTA_PILAR_ES = tenis_paginas.RUTA_PILAR
PREFIJO = "/en"
ETIQUETAS = {"Ganador del partido": "Match winner", "Juegos totales": "Total games"}
RESULTADO = {"win": "Hit", "loss": "Miss", "push": "Refunded"}
SUPERFICIE = {"Hard": "hard court", "Clay": "clay court", "Grass": "grass court", "Carpet": "carpet court"}
_MAS = re.compile(r"^Más de (.+)$")
_MENOS = re.compile(r"^Menos de (.+)$")


# --- formato inglés ---------------------------------------------------------------------------------

def pct(p: float) -> str:
    return f"{round(p * 100)}%"


def num(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}"


def fecha_corta(d: date) -> str:
    return f"{paginas.MONTHS_EN[d.month - 1][:3]} {d.day}, {d.year}"


def fecha_hora_utc(dt: datetime) -> str:
    u = dt.astimezone(timezone.utc)
    return f"{paginas.MONTHS_EN[u.month - 1][:3]} {u.day}, {u.year} at {u:%H:%M} UTC"


def etiqueta(texto: str) -> str:
    return ETIQUETAS.get(texto, texto)


def seleccion(texto: str) -> str:
    if m := _MAS.match(texto):
        return f"Over {m[1]}"
    if m := _MENOS.match(texto):
        return f"Under {m[1]}"
    return texto


# --- equivalencias español ↔ inglés (hreflang y selector) ---------------------------------------------

_RUTA_PARTIDO = re.compile(r"^(?P<en>/en)?/tenis/(?P<torneo>[^/]+)/(?P<slug>[^/]+)/$")


def equivalencias(ruta: str) -> dict[str, str] | None:
    if ruta in (RUTA_PILAR, RUTA_PILAR_ES):
        return {"es": RUTA_PILAR_ES, "en": RUTA_PILAR}
    m = _RUTA_PARTIDO.match(ruta)
    if m and tenis_datos.SLUG_PARTIDO.match(m["slug"]) and m["torneo"] not in tenis_datos.RESERVADOS:
        base = f"/tenis/{m['torneo']}/{m['slug']}/"
        return {"es": base, "en": PREFIJO + base}
    return None


idiomas.registrar_traductor(equivalencias)


# --- interpretación (la lógica del español; el texto en inglés) ----------------------------------------

def construir(ev: dict, ahora: datetime | None = None) -> SimpleNamespace:
    ahora = ahora or tenis_paginas._ahora()
    ganador = tenis_paginas.mercado_ganador(ev)
    p = float(ganador["probability"])
    home, away = ev["home"], ev["away"]
    otro = away if ganador["selection"] == home else home
    res = tenis_paginas.resultado(ev)
    ver = tenis_paginas.veredicto(ev, res)
    torneo = tenis_datos.torneo_nombre(ev)
    dia = tenis_datos.fecha_utc(ev)
    st = tenis_paginas.estado(ev)
    slug, ruta = tenis_datos.slug_partido(ev), PREFIJO + tenis_datos.ruta_partido(ev)
    titulo = f"{home} vs {away}: prediction {torneo}, {fecha_corta(dia)}"
    if st == "final" and res["coherente"]:
        titulo = f"{home} vs {away}: prediction and result {torneo}, {fecha_corta(dia)}"
    descripcion = (f"Win probabilities in {torneo}: {ganador['selection']} {pct(p)} and {otro} {pct(1 - p)}. "
                   f"Forecast sealed before the match, with the result and the misses in plain view.")
    sellado = None
    try:
        sellado = datetime.fromisoformat(str(ev["sealed_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        pass
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=f"{home} vs {away}"),
        id=str(ev["id"]), slug=slug, ruta=ruta, url=seo.base_url() + ruta, home=home, away=away, torneo=torneo,
        superficie=SUPERFICIE.get(ev.get("surface"), str(ev.get("surface") or "").lower() or None),
        estado=st, resultado=res, veredicto=ver, inicio=ev["_inicio"], dia=dia, sellado=sellado,
        inicio_txt=fecha_hora_utc(ev["_inicio"]), sellado_txt=fecha_hora_utc(sellado) if sellado else None,
        hash=ev["seal"], favorito=ganador["selection"], otro=otro, prob_fav=p, p_fav=pct(p), p_otro=pct(1 - p),
        brier=num(ver["brier"], 3) if ver else None, mercados=_filas_mercados(ev, res))


def _filas_mercados(ev: dict, res: dict) -> list[dict]:
    mostrar = res["coherente"] or res["devuelto"]
    return [{"label": etiqueta(m.get("label", "")), "seleccion": seleccion(m.get("selection", "")), "prob": pct(float(m["probability"])),
             "resultado": RESULTADO.get(m.get("outcome")) if mostrar else None, "fallo": m.get("outcome") == "loss"}
            for m in ev.get("markets") or [] if isinstance(m.get("probability"), (int, float))]


def _organizacion() -> dict:
    return {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}


def jsonld_partido(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo, "inLanguage": "en",
           "description": c.p.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
           "publisher": _organizacion(),
           "about": {"@type": "SportsEvent", "name": f"{c.home} vs {c.away}", "sport": "Tennis",
                     "startDate": c.inicio.isoformat().replace("+00:00", "Z"),
                     "eventStatus": ("https://schema.org/EventCancelled" if c.estado == "cancelado" else "https://schema.org/EventScheduled"),
                     "competitor": [{"@type": "Person", "name": c.home}, {"@type": "Person", "name": c.away}]}}
    if c.sellado:
        web["datePublished"] = c.sellado.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "Tennis", "item": f"{base}{RUTA_PILAR}"},
        {"@type": "ListItem", "position": 3, "name": c.p.migas, "item": c.url}]}, web]


# --- pilar ----------------------------------------------------------------------------------------

def _fila(ev: dict) -> dict:
    res = tenis_paginas.resultado(ev)
    ver = tenis_paginas.veredicto(ev, res)
    g = tenis_paginas.mercado_ganador(ev)
    return {"home": ev["home"], "away": ev["away"], "inicio": ev["_inicio"], "estado": tenis_paginas.estado(ev),
            "url": PREFIJO + tenis_datos.ruta_partido(ev), "sets": res["sets"] if res["coherente"] else None,
            "ganador": res["ganador"], "veredicto": ver, "en_revision": res["en_revision"],
            "favorito": g["selection"] if g else None, "p_fav": pct(float(g["probability"])) if g else None}


def construir_pilar(ahora: datetime | None = None, eventos: list[dict] | None = None) -> SimpleNamespace:
    ahora = ahora or tenis_paginas._ahora()
    hoy = tenis_datos.hoy_utc(ahora)
    if eventos is None:
        eventos = tenis_datos.ventana(hoy)
    por_dia: dict[date, dict[str, list[dict]]] = {}
    for ev in sorted(eventos, key=lambda e: (tenis_datos.torneo_nombre(e), e["_inicio"])):
        por_dia.setdefault(tenis_datos.fecha_utc(ev), {}).setdefault(tenis_datos.torneo_nombre(ev), []).append(_fila(ev))
    dias = [{"iso": d.isoformat(), "largo": paginas.fecha_larga(d, "en"), "torneos": list(t.items()), "proximo": d >= hoy}
            for d, t in sorted(por_dia.items(), reverse=True)]
    juzgados = [f["veredicto"] for dia in dias for _, filas in dia["torneos"] for f in filas if f["veredicto"]]
    en_revision = sum(1 for dia in dias for _, filas in dia["torneos"] for f in filas if f["en_revision"])
    base = seo.base_url()
    url = base + RUTA_PILAR
    pagina = SimpleNamespace(
        titulo="Tennis predictions: win probabilities for every match",
        descripcion=("Win probability and set and game totals for ATP and WTA matches, sealed before the match "
                     "and with the hits and misses in plain view."), slug="tenis", migas="Tennis")
    return SimpleNamespace(
        p=pagina, url=url, dias=dias, juzgados=len(juzgados), aciertos=sum(1 for v in juzgados if v["acerto"]), en_revision=en_revision,
        total=sum(len(f) for dia in dias for _, f in dia["torneos"]),
        jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Tennis", "item": url}]},
            {"@context": "https://schema.org", "@type": "CollectionPage", "name": pagina.titulo, "url": url, "inLanguage": "en",
             "description": pagina.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
             "publisher": _organizacion()}])


# --- sitemap --------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Solo con el inglés abierto (`on`): las mismas entradas que el español, con el prefijo `/en`."""
    if idiomas.estado("en") != "on":
        return ()
    return tuple((PREFIJO + ruta, lastmod) for ruta, lastmod in tenis_paginas.entradas_sitemap())


# --- rutas ----------------------------------------------------------------------------------------

def _responder(plantilla: str, p: SimpleNamespace, url: str, jsonld: list[dict], ruta: str, og_imagen: str | None = None, **ctx) -> HTMLResponse:
    cab = idiomas.puerta("en")
    cab.setdefault("Cache-Control", "no-cache, must-revalidate")
    cab["Content-Security-Policy"] = paginas.CSP
    cuerpo = _env.get_template(plantilla).render(
        p=p, url=url, base=seo.base_url(), jsonld=jsonld, paginas=paginas.PAGINAS_EN, og_imagen=og_imagen,
        idiomas_alt=idiomas.selector(ruta), robots=idiomas.robots_de("en"), **ctx)
    return HTMLResponse(cuerpo, headers=cab)


def _no_disponible() -> HTTPException:
    return HTTPException(503, detail="Tennis data is not available right now.", headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route(RUTA_PILAR, methods=["GET", "HEAD"], name="en_tenis_pilar")
def pilar():
    idiomas.puerta("en")
    try:
        c = construir_pilar()
    except TenisNoDisponible:
        raise _no_disponible()
    return _responder("en_tenis_cartelera.html", c.p, c.url, c.jsonld, RUTA_PILAR, og_imagen=og.url_pilar_en("tenis"), c=c)


@router.api_route(RUTA_PILAR.rstrip("/"), methods=["GET", "HEAD"], name="en_tenis_pilar_sin_barra")
def pilar_sin_barra(request: Request):
    idiomas.puerta("en")
    return RedirectResponse(seo.base_url() + RUTA_PILAR + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


@router.api_route("/en/tenis/{torneo}/{slug}/", methods=["GET", "HEAD"], name="en_tenis_partido")
def partido(torneo: str, slug: str):
    idiomas.puerta("en")
    if torneo in tenis_datos.RESERVADOS or not tenis_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    try:
        ev = tenis_datos.buscar_partido(torneo, slug)
    except TenisNoDisponible:
        raise _no_disponible()
    if ev is None or not tenis_paginas.mercado_ganador(ev):
        raise HTTPException(404)
    c = construir(ev)
    imagen = og.url_partido(c.ruta, tenis_paginas.estado_imagen(c))
    return _responder("en_tenis_partido.html", c.p, c.url, jsonld_partido(c, seo.base_url()), c.ruta, og_imagen=imagen, c=c)


@router.api_route("/en/tenis/{torneo}/{slug}", methods=["GET", "HEAD"], name="en_tenis_partido_sin_barra")
def partido_sin_barra(torneo: str, slug: str, request: Request):
    idiomas.puerta("en")
    if torneo in tenis_datos.RESERVADOS or not tenis_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}/en/tenis/{torneo}/{slug}/" + (f"?{request.url.query}" if request.url.query else ""),
                            status_code=301)


# --- tarjeta para redes (en inglés) -------------------------------------------------------------------

def tarjeta(c: SimpleNamespace) -> "og.Tarjeta":
    final = tenis_paginas.estado_imagen(c) == "final"
    a, b = (c.prob_fav, 1 - c.prob_fav) if c.favorito == c.home else (1 - c.prob_fav, c.prob_fav)
    s = c.resultado["sets"]
    return og.Tarjeta("partido", etiqueta="TENNIS", local=c.home, visitante=c.away, contexto=f"{c.torneo} · {fecha_corta(c.dia)}",
                      barra=[(c.home, a), (c.away, b)], estado=tenis_paginas.estado_imagen(c),
                      marcador=f"{s[0]} – {s[1]} in sets" if final and s else "",
                      veredicto=(("acerto" if c.veredicto["acerto"] else "fallo") if final and c.veredicto else None), idioma="en")


def tarjeta_de_la_url(torneo: str, slug: str):
    ev = tenis_datos.buscar_partido(torneo, slug)
    return tarjeta(construir(ev)) if ev and tenis_paginas.mercado_ganador(ev) else None
