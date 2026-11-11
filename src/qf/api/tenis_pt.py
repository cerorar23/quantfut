"""Páginas públicas de tênis en PORTUGUÉS de Brasil (F6.4d de docs/plan_seo_redes_web_20261108.md, §9): `/pt/tenis/` y `/pt/tenis/{torneo}/{slug}/`.

Igual que `tenis_en.py`: páginas independientes sobre `base_pt.html`. Reutilizan la lógica del español de `tenis_paginas.py`
(`resultado`, `veredicto`, `estado`, `mercado_ganador`): la salvaguarda de que el ganador del mercado y los SETS coincidan se aplica igual.
Las etiquetas de mercado vienen del feed en español; se traducen con una tabla pequeña de los tipos que publica el motor.
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

log = logging.getLogger("qf.tenis_pt")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA_PILAR = "/pt/tenis/"
RUTA_PILAR_ES = tenis_paginas.RUTA_PILAR
PREFIJO = "/pt"
ETIQUETAS = {"Ganador del partido": "Vencedor da partida", "Juegos totales": "Total de games"}
RESULTADO = {"win": "Acerto", "loss": "Erro", "push": "Reembolsado"}
SUPERFICIE = {"Hard": "quadra dura", "Clay": "saibro", "Grass": "grama", "Carpet": "carpete"}
_MAS = re.compile(r"^Más de (.+)$")
_MENOS = re.compile(r"^Menos de (.+)$")


# --- formato portugués -----------------------------------------------------------------------------

def pct(p: float) -> str:
    return f"{round(p * 100)}%"


def num(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def fecha_hora_utc(dt: datetime) -> str:
    u = dt.astimezone(timezone.utc)
    return f"{paginas.fecha_larga(u.date(), 'pt')} às {u:%H:%M} UTC"


def etiqueta(texto: str) -> str:
    return ETIQUETAS.get(texto, texto)


def seleccion(texto: str) -> str:
    if m := _MAS.match(texto):
        return f"Mais de {m[1]}"
    if m := _MENOS.match(texto):
        return f"Menos de {m[1]}"
    return texto


# --- equivalencias español ↔ portugués ------------------------------------------------------------

_RUTA_PARTIDO = re.compile(r"^(?P<pt>/pt)?/tenis/(?P<torneo>[^/]+)/(?P<slug>[^/]+)/$")


def equivalencias(ruta: str) -> dict[str, str] | None:
    if ruta in (RUTA_PILAR, RUTA_PILAR_ES):
        return {"es": RUTA_PILAR_ES, "pt": RUTA_PILAR}
    m = _RUTA_PARTIDO.match(ruta)
    if m and tenis_datos.SLUG_PARTIDO.match(m["slug"]) and m["torneo"] not in tenis_datos.RESERVADOS:
        base = f"/tenis/{m['torneo']}/{m['slug']}/"
        return {"es": base, "pt": PREFIJO + base}
    return None


idiomas.registrar_traductor(equivalencias)


# --- interpretación (la lógica del español; el texto en portugués) --------------------------------------

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
    titulo = f"{home} x {away}: previsão {torneo}, {paginas.fecha_larga(dia, 'pt')}"
    if st == "final" and res["coherente"]:
        titulo = f"{home} x {away}: previsão e resultado {torneo}, {paginas.fecha_larga(dia, 'pt')}"
    descripcion = (f"Probabilidades de vitória em {torneo}: {ganador['selection']} {pct(p)} e {otro} {pct(1 - p)}. "
                   f"Previsão selada antes da partida, com o resultado e os erros à vista.")
    sellado = None
    try:
        sellado = datetime.fromisoformat(str(ev["sealed_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        pass
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=f"{home} x {away}"),
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
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo, "inLanguage": "pt",
           "description": c.p.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
           "publisher": _organizacion(),
           "about": {"@type": "SportsEvent", "name": f"{c.home} x {c.away}", "sport": "Tennis",
                     "startDate": c.inicio.isoformat().replace("+00:00", "Z"),
                     "eventStatus": ("https://schema.org/EventCancelled" if c.estado == "cancelado" else "https://schema.org/EventScheduled"),
                     "competitor": [{"@type": "Person", "name": c.home}, {"@type": "Person", "name": c.away}]}}
    if c.sellado:
        web["datePublished"] = c.sellado.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "Tênis", "item": f"{base}{RUTA_PILAR}"},
        {"@type": "ListItem", "position": 3, "name": c.p.migas, "item": c.url}]}, web]


# --- pilar ----------------------------------------------------------------------------------------------

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
    dias = [{"iso": d.isoformat(), "largo": paginas.fecha_larga(d, "pt"), "torneos": list(t.items()), "proximo": d >= hoy}
            for d, t in sorted(por_dia.items(), reverse=True)]
    juzgados = [f["veredicto"] for dia in dias for _, filas in dia["torneos"] for f in filas if f["veredicto"]]
    en_revision = sum(1 for dia in dias for _, filas in dia["torneos"] for f in filas if f["en_revision"])
    base = seo.base_url()
    url = base + RUTA_PILAR
    pagina = SimpleNamespace(
        titulo="Previsões de tênis: probabilidade de vitória de cada jogador",
        descripcion=("Probabilidade de vitória e de totais de sets e games das partidas ATP e WTA, selada antes da partida "
                     "e com os acertos e erros à vista."), slug="tenis", migas="Tênis")
    return SimpleNamespace(
        p=pagina, url=url, dias=dias, juzgados=len(juzgados), aciertos=sum(1 for v in juzgados if v["acerto"]), en_revision=en_revision,
        total=sum(len(f) for dia in dias for _, f in dia["torneos"]),
        jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Tênis", "item": url}]},
            {"@context": "https://schema.org", "@type": "CollectionPage", "name": pagina.titulo, "url": url, "inLanguage": "pt",
             "description": pagina.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
             "publisher": _organizacion()}])


# --- sitemap --------------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Solo con el portugués abierto (`on`): las mismas entradas que el español, con el prefijo `/pt`."""
    if idiomas.estado("pt") != "on":
        return ()
    return tuple((PREFIJO + ruta, lastmod) for ruta, lastmod in tenis_paginas.entradas_sitemap())


# --- rutas ----------------------------------------------------------------------------------------------

def _responder(plantilla: str, p: SimpleNamespace, url: str, jsonld: list[dict], ruta: str, og_imagen: str | None = None, **ctx) -> HTMLResponse:
    from . import web_config

    cab = idiomas.puerta("pt")
    cab.setdefault("Cache-Control", "no-cache, must-revalidate")
    cab["Content-Security-Policy"] = paginas.CSP
    wctx = web_config.base_template_ctx(lang="pt")
    cuerpo = _env.get_template(plantilla).render(
        p=p, url=url, base=seo.base_url(), jsonld=web_config.apply_org_jsonld(jsonld, wctx["cfg"]),
        paginas=paginas.PAGINAS_PT, og_imagen=og_imagen,
        idiomas_alt=idiomas.selector(ruta), robots=idiomas.robots_de("pt"), **wctx, **ctx)
    return HTMLResponse(cuerpo, headers=cab)


def _no_disponible() -> HTTPException:
    return HTTPException(503, detail="Os dados de tênis não estão disponíveis no momento.",
                         headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route(RUTA_PILAR, methods=["GET", "HEAD"], name="pt_tenis_pilar")
def pilar():
    from . import web_config

    idiomas.puerta("pt")
    try:
        c = construir_pilar()
    except TenisNoDisponible:
        raise _no_disponible()
    c.p, entradilla_override = web_config.apply_editorial_meta(c.p, "sport:tenis", "pt")
    return _responder("pt_tenis_cartelera.html", c.p, c.url, c.jsonld, RUTA_PILAR,
                      og_imagen=og.url_pilar_pt("tenis"), c=c, entradilla_override=entradilla_override)


@router.api_route(RUTA_PILAR.rstrip("/"), methods=["GET", "HEAD"], name="pt_tenis_pilar_sin_barra")
def pilar_sin_barra(request: Request):
    idiomas.puerta("pt")
    return RedirectResponse(seo.base_url() + RUTA_PILAR + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


@router.api_route("/pt/tenis/{torneo}/{slug}/", methods=["GET", "HEAD"], name="pt_tenis_partido")
def partido(torneo: str, slug: str):
    idiomas.puerta("pt")
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
    return _responder("pt_tenis_partido.html", c.p, c.url, jsonld_partido(c, seo.base_url()), c.ruta, og_imagen=imagen, c=c)


@router.api_route("/pt/tenis/{torneo}/{slug}", methods=["GET", "HEAD"], name="pt_tenis_partido_sin_barra")
def partido_sin_barra(torneo: str, slug: str, request: Request):
    idiomas.puerta("pt")
    if torneo in tenis_datos.RESERVADOS or not tenis_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}/pt/tenis/{torneo}/{slug}/" + (f"?{request.url.query}" if request.url.query else ""),
                            status_code=301)


# --- tarjeta para redes (en portugués) -----------------------------------------------------------

def tarjeta(c: SimpleNamespace) -> "og.Tarjeta":
    final = tenis_paginas.estado_imagen(c) == "final"
    a, b = (c.prob_fav, 1 - c.prob_fav) if c.favorito == c.home else (1 - c.prob_fav, c.prob_fav)
    s = c.resultado["sets"]
    return og.Tarjeta("partido", etiqueta="TÊNIS", local=c.home, visitante=c.away,
                      contexto=f"{c.torneo} · {paginas.fecha_larga(c.dia, 'pt')}",
                      barra=[(c.home, a), (c.away, b)], estado=tenis_paginas.estado_imagen(c),
                      marcador=f"{s[0]} – {s[1]} em sets" if final and s else "",
                      veredicto=(("acerto" if c.veredicto["acerto"] else "fallo") if final and c.veredicto else None), idioma="pt")


def tarjeta_de_la_url(torneo: str, slug: str):
    ev = tenis_datos.buscar_partido(torneo, slug)
    return tarjeta(construir(ev)) if ev and tenis_paginas.mercado_ganador(ev) else None

