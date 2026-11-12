"""Páginas públicas de tenis dentro de la app (F3.2 de docs/plan_seo_redes_web_20261108.md).

- `/tenis/`: partidos de los días -3..+3 con enlaces `<a href>` reales.
- `/tenis/<torneo>/<jugador-a>-vs-<jugador-b>-<AAAA-MM-DD>/`: un partido con pronóstico sellado (todos los del feed público).

Se sirven dentro del shell de la SPA (`rutas_web.render_pagina`), igual que NBA y fútbol. Todo sale del feed público de
`/web/deportes/tenis` (`tenis_datos.py`). Antes de decir quién ganó se cruza el ganador del mercado con los SETS del
marcador: si no coinciden, la página no muestra acierto ni fallo (la fuente de resultados ya calificó mal algún partido
a tres sets); la salvaguarda está en `resultado()` y la cubren las pruebas.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..comercial import catalogo
from . import og, paginas, rutas_web, seo, tenis_datos
from .tenis_datos import TenisNoDisponible

log = logging.getLogger("qf.tenis_paginas")
router = APIRouter(include_in_schema=False, dependencies=[Depends(catalogo.exigir_web('tenis'))])
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA_PILAR = "/tenis/"
SCORE = re.compile(r"^\s*(\d+)\s*-\s*(\d+)\s*$")
NOMBRE_OUTCOME = {"win": "Acertó", "loss": "Falló", "push": "Devolución"}


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def pct(p: float) -> str:
    return f"{round(p * 100)} %"


def num(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def fecha_corta(d: date) -> str:
    return f"{d.day} {paginas.MESES[d.month - 1][:3]} {d.year}"


def fecha_larga(d: date) -> str:
    return paginas.fecha_larga(d)


# --- interpretación de un partido ----------------------------------------------------------------

def mercado_ganador(ev: dict) -> dict | None:
    for m in ev.get("markets") or []:
        if m.get("id") == "winner":
            return m
    return None


def resultado(ev: dict) -> dict:
    """Qué se puede decir del resultado. `coherente` solo es True si el ganador que implica el mercado ganador coincide con
    el ganador por sets del marcador; si no, no se muestra acierto ni fallo."""
    out = {"sets": None, "ganador": None, "coherente": False, "en_revision": False, "devuelto": False}
    if ev.get("status") != "finished":
        return out
    m = SCORE.match(str(ev.get("score") or ""))
    if m:
        out["sets"] = (int(m[1]), int(m[2]))
    ganador = mercado_ganador(ev)
    if not ganador:
        out["en_revision"] = True
        return out
    if ganador.get("outcome") == "push":
        out["devuelto"] = True          # retirada o walkover sin sets completos: el mercado se devuelve
        return out
    favorito = ev["home"] if ganador.get("selection") == ev["home"] else ev["away"] if ganador.get("selection") == ev["away"] else None
    if favorito is None or ganador.get("outcome") not in ("win", "loss") or out["sets"] is None or out["sets"][0] == out["sets"][1]:
        out["en_revision"] = True
        return out
    por_mercado = favorito if ganador["outcome"] == "win" else (ev["away"] if favorito == ev["home"] else ev["home"])
    por_sets = ev["home"] if out["sets"][0] > out["sets"][1] else ev["away"]
    if por_mercado != por_sets:
        out["en_revision"] = True       # la salvaguarda: ganador y sets no coinciden
        return out
    out.update(ganador=por_sets, coherente=True)
    return out


def estado(ev: dict) -> str:
    return {"finished": "final", "cancelled": "cancelado", "scheduled": "previa", "awaiting_result": "pendiente",
            "no_result": "sin_resultado"}.get(ev.get("status"), "pendiente")


def veredicto(ev: dict, res: dict | None = None) -> dict | None:
    res = res or resultado(ev)
    ganador = mercado_ganador(ev)
    if not res["coherente"] or not ganador:
        return None
    p = float(ganador["probability"])
    acerto = ganador["outcome"] == "win"
    return {"acerto": acerto, "favorito": ganador["selection"], "ganador": res["ganador"], "brier": (p - (1.0 if acerto else 0.0)) ** 2}


def _filas_mercados(ev: dict, res: dict) -> list[dict]:
    mostrar = res["coherente"] or res["devuelto"]
    return [{"label": m.get("label", ""), "seleccion": m.get("selection", ""), "prob": pct(float(m["probability"])),
             "resultado": NOMBRE_OUTCOME.get(m.get("outcome")) if mostrar else None, "fallo": m.get("outcome") == "loss"}
            for m in ev.get("markets") or [] if isinstance(m.get("probability"), (int, float))]


def construir(ev: dict, ahora: datetime | None = None) -> SimpleNamespace:
    ahora = ahora or _ahora()
    ganador = mercado_ganador(ev)
    p = float(ganador["probability"])
    home, away = ev["home"], ev["away"]
    otro = away if ganador["selection"] == home else home
    res = resultado(ev)
    ver = veredicto(ev, res)
    torneo = tenis_datos.torneo_nombre(ev)
    dia = tenis_datos.fecha_utc(ev)
    st = estado(ev)
    slug, ruta = tenis_datos.slug_partido(ev), tenis_datos.ruta_partido(ev)
    titulo = f"{home} vs {away}: pronóstico {torneo} {fecha_corta(dia)}"
    if st == "final" and res["coherente"]:
        titulo = f"{home} vs {away}: pronóstico y resultado {torneo} {fecha_corta(dia)}"
    descripcion = (f"Probabilidad de victoria: {ganador['selection']} {pct(p)} y {otro} {pct(1 - p)} en {torneo}. "
                   f"Pronóstico sellado antes del partido, con el resultado y los fallos a la vista.")
    sellado = None
    try:
        sellado = datetime.fromisoformat(str(ev["sealed_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        pass
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=f"{home} vs {away}"),
        id=str(ev["id"]), slug=slug, ruta=ruta, url=seo.base_url() + ruta, home=home, away=away, torneo=torneo,
        superficie=ev.get("surface"), estado=st, resultado=res, veredicto=ver, inicio=ev["_inicio"], dia=dia, sellado=sellado,
        hash=ev["seal"], favorito=ganador["selection"], otro=otro, prob_fav=p, p_fav=pct(p), p_otro=pct(1 - p),
        brier=num(ver["brier"], 3) if ver else None, mercados=_filas_mercados(ev, res))


def jsonld_partido(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo, "inLanguage": "es",
           "description": c.p.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
           "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"},
           "about": {"@type": "SportsEvent", "name": f"{c.home} vs {c.away}", "sport": "Tennis",
                     "startDate": c.inicio.isoformat().replace("+00:00", "Z"),
                     "eventStatus": ("https://schema.org/EventCancelled" if c.estado == "cancelado" else "https://schema.org/EventScheduled"),
                     "competitor": [{"@type": "Person", "name": c.home}, {"@type": "Person", "name": c.away}]}}
    if c.sellado:
        web["datePublished"] = c.sellado.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "Tenis", "item": f"{base}{RUTA_PILAR}"},
        {"@type": "ListItem", "position": 3, "name": c.p.migas, "item": c.url}]}, web]


# --- tarjeta para redes ---------------------------------------------------------------------------

def estado_imagen(c: SimpleNamespace) -> str:
    # Solo hay tarjeta «final» con el resultado confirmado (ganador y sets coinciden): en revisión no se anuncia nada.
    return "final" if c.estado == "final" and c.resultado["coherente"] else "previa"


def tarjeta(c: SimpleNamespace) -> "og.Tarjeta":
    final = estado_imagen(c) == "final"
    a, b = (c.prob_fav, 1 - c.prob_fav) if c.favorito == c.home else (1 - c.prob_fav, c.prob_fav)
    s = c.resultado["sets"]
    return og.Tarjeta("partido", etiqueta="TENIS", local=c.home, visitante=c.away, contexto=f"{c.torneo} · {fecha_larga(c.dia)}",
                      barra=[(c.home, a), (c.away, b)], estado=estado_imagen(c),
                      marcador=f"{s[0]} – {s[1]} en sets" if final and s else "",
                      veredicto=(("acerto" if c.veredicto["acerto"] else "fallo") if final and c.veredicto else None))


def tarjeta_de_la_url(torneo: str, slug: str):
    ev = tenis_datos.buscar_partido(torneo, slug)
    return tarjeta(construir(ev)) if ev and mercado_ganador(ev) else None


def _imagen_partido(c: SimpleNamespace):
    url = og.url_partido(c.ruta, estado_imagen(c))
    return (url, f"Pronóstico {c.home} vs {c.away}: probabilidades del modelo") if url else None


# --- pilar ----------------------------------------------------------------------------------------

def _fila(ev: dict) -> dict:
    res = resultado(ev)
    ver = veredicto(ev, res)
    g = mercado_ganador(ev)
    return {"home": ev["home"], "away": ev["away"], "inicio": ev["_inicio"], "estado": estado(ev), "url": tenis_datos.ruta_partido(ev),
            "sets": res["sets"] if res["coherente"] else None, "ganador": res["ganador"], "veredicto": ver,
            "en_revision": res["en_revision"], "favorito": g["selection"] if g else None, "p_fav": pct(float(g["probability"])) if g else None}


def construir_pilar(ahora: datetime | None = None, eventos: list[dict] | None = None) -> SimpleNamespace:
    ahora = ahora or _ahora()
    hoy = tenis_datos.hoy_utc(ahora)
    if eventos is None:
        eventos = tenis_datos.ventana(hoy)
    por_dia: dict[date, dict[str, list[dict]]] = {}
    for ev in sorted(eventos, key=lambda e: (tenis_datos.torneo_nombre(e), e["_inicio"])):
        por_dia.setdefault(tenis_datos.fecha_utc(ev), {}).setdefault(tenis_datos.torneo_nombre(ev), []).append(_fila(ev))
    dias = [{"iso": d.isoformat(), "largo": fecha_larga(d), "torneos": list(t.items()), "proximo": d >= hoy}
            for d, t in sorted(por_dia.items(), reverse=True)]
    juzgados = [f["veredicto"] for dia in dias for _, filas in dia["torneos"] for f in filas if f["veredicto"]]
    en_revision = sum(1 for dia in dias for _, filas in dia["torneos"] for f in filas if f["en_revision"])
    base = seo.base_url()
    url = base + RUTA_PILAR
    pagina = SimpleNamespace(
        titulo="Pronósticos de tenis: probabilidades de cada partido",
        descripcion=("Probabilidad de victoria y de sets y juegos de los partidos ATP y WTA, sellada antes del partido y con los "
                     "aciertos y los fallos a la vista."), slug="tenis", migas="Tenis")
    return SimpleNamespace(
        p=pagina, url=url, dias=dias, juzgados=len(juzgados), aciertos=sum(1 for v in juzgados if v["acerto"]), en_revision=en_revision,
        total=sum(len(f) for dia in dias for _, f in dia["torneos"]),
        jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Tenis", "item": url}]},
            {"@context": "https://schema.org", "@type": "CollectionPage", "name": pagina.titulo, "url": url, "inLanguage": "es",
             "description": pagina.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
             "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}}])


# --- sitemap --------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """El pilar siempre; los partidos de la ventana si el feed responde. `lastmod` = día del sello mientras no hay resultado."""
    filas: list[tuple[str, str | None]] = [(RUTA_PILAR, None)]
    try:
        evs = tenis_datos.ventana()
    except TenisNoDisponible:
        return tuple(filas)
    for ev in sorted(evs, key=lambda e: (e["_inicio"], str(e["id"])), reverse=True):
        try:
            sellado = datetime.fromisoformat(str(ev["sealed_at"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            sellado = None
        lastmod = sellado.astimezone(timezone.utc).date().isoformat() if sellado and ev.get("status") != "finished" else None
        filas.append((tenis_datos.ruta_partido(ev), lastmod))
    return tuple(filas)


# --- rutas ----------------------------------------------------------------------------------------

def _pagina(plantilla: str, path: str, p: SimpleNamespace, jsonld: list[dict], datos: dict, imagen=None, **ctx) -> HTMLResponse:
    principal = _env.get_template(plantilla).render(p=p, **ctx)
    cuerpo = rutas_web.render_pagina(titulo=p.titulo, descripcion=p.descripcion, path=path, ruta="partidos",
                                     jsonld=jsonld, principal=principal, datos={"deporte": "tenis", **datos}, imagen=imagen)
    return HTMLResponse(cuerpo, headers={"Cache-Control": "no-cache, must-revalidate"})


def _no_disponible() -> HTTPException:
    return HTTPException(503, detail="Los datos de tenis no están disponibles en este momento.",
                         headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route("/tenis/", methods=["GET", "HEAD"], name="tenis_pilar")
def pilar():
    from . import web_config

    try:
        c = construir_pilar()
    except TenisNoDisponible:
        raise _no_disponible()
    c.p, entradilla_override = web_config.apply_editorial_meta(c.p, "sport:tenis", "es")
    url = og.url_pilar("tenis")
    return _pagina("tenis_cartelera.html", RUTA_PILAR, c.p, c.jsonld, {},
                   (url, "Pronósticos de tenis con probabilidades") if url else None,
                   c=c, entradilla_override=entradilla_override)


@router.api_route("/tenis", methods=["GET", "HEAD"], name="tenis_pilar_sin_barra")
def pilar_sin_barra(request: Request):
    return RedirectResponse(seo.base_url() + RUTA_PILAR + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


@router.api_route("/tenis/{torneo}/{slug}/", methods=["GET", "HEAD"], name="tenis_partido")
def partido(torneo: str, slug: str):
    if torneo in tenis_datos.RESERVADOS:
        raise HTTPException(404)
    try:
        ev = tenis_datos.buscar_partido(torneo, slug)
    except TenisNoDisponible:
        raise _no_disponible()
    if ev is None or not mercado_ganador(ev):
        raise HTTPException(404)
    c = construir(ev)
    return _pagina("tenis_partido.html", c.ruta, c.p, jsonld_partido(c, seo.base_url()),
                   {"evento": c.id, "inicio": c.inicio.isoformat()}, _imagen_partido(c), c=c)


@router.api_route("/tenis/{torneo}/{slug}", methods=["GET", "HEAD"], name="tenis_partido_sin_barra")
def partido_sin_barra(torneo: str, slug: str, request: Request):
    if torneo in tenis_datos.RESERVADOS or not tenis_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}/tenis/{torneo}/{slug}/" + (f"?{request.url.query}" if request.url.query else ""),
                            status_code=301)
