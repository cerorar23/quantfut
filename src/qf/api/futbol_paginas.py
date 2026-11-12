"""Páginas públicas de fútbol dentro de la app (F3.1 de docs/plan_seo_redes_web_20261108.md).

- `/futbol/`: agenda de los días -1..+3 (los que muestra la app) con enlaces `<a href>` reales.
- `/futbol/<competición>/<local>-vs-<visitante>-<AAAA-MM-DD>/`: un partido con pronóstico generado antes de su inicio.

Igual que las de NBA se sirven dentro del shell de la SPA (`rutas_web.render_pagina`): el HTML inicial lleva el texto
para Google y las redes y la persona ve la app, que arranca en ese partido (`frontend/rutas.js`).

Qué NO hay aquí, a propósito: picks, alta probabilidad, escalera ni mercados. Es lo que puede ser VIP y esta página no
lo consulta, así que no puede filtrarlo (ver `futbol_datos.py`); la app muestra cada cosa con su acceso, como siempre.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..comercial import catalogo
from . import futbol_datos, og, paginas, rutas_web, seo
from .futbol_datos import FutbolNoDisponible

log = logging.getLogger("qf.futbol_paginas")
router = APIRouter(include_in_schema=False, dependencies=[Depends(catalogo.exigir_web('futbol'))])
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA_PILAR = "/futbol/"
HORAS_EN_JUEGO = 3        # pasado este tiempo sin marcador final se dice «pendiente de confirmar»
LADOS = ("home", "draw", "away")


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

def estado(fila: dict, ahora: datetime) -> str:
    """previa | curso | pendiente | final | aplazado."""
    if fila.get("marcador"):
        return "final"
    if fila.get("estado") == "postponed":
        return "aplazado"
    ko = fila["kickoff_utc"]
    if ko.tzinfo is None:
        ko = ko.replace(tzinfo=timezone.utc)
    if ahora < ko:
        return "previa"
    return "pendiente" if ahora - ko > timedelta(hours=HORAS_EN_JUEGO) else "curso"


def veredicto(fila: dict) -> dict | None:
    """¿Ganó el resultado más probable y cuánto vale el Brier del 1X2? Solo con marcador final."""
    pron, marcador = fila.get("pron"), fila.get("marcador")
    if not pron or not marcador:
        return None
    gl, gv = marcador
    real = "home" if gl > gv else "away" if gv > gl else "draw"
    probs = pron["probs"]
    total = sum(probs.values())
    p = {k: probs[k] / total for k in LADOS}
    favorito = max(LADOS, key=lambda k: (p[k], k == "home"))
    nombres = {"home": fila["local"]["nombre"], "away": fila["visitante"]["nombre"], "draw": "el empate"}
    return {"acerto": favorito == real, "favorito": nombres[favorito], "resultado": nombres[real],
            "brier": sum((p[k] - (1.0 if k == real else 0.0)) ** 2 for k in LADOS)}


def _lado(ficha: dict, clave: str) -> dict | None:
    lado = (ficha or {}).get(clave) or {}
    forma = (lado.get("forma") or {}).get("resumen") or {}
    clas = lado.get("clasificacion")
    if not lado.get("nombre") or not forma.get("n"):
        return None
    return {"nombre": lado["nombre"], "racha": forma.get("racha", ""), "puntos": forma.get("puntos"), "n": forma["n"],
            "gf": forma.get("gf"), "gc": forma.get("gc"),
            "puesto": (f"{clas['posicion']}.º en {clas['liga']} con {clas['puntos']} puntos" if clas else None)}


def contexto(ficha: dict | None, secciones: dict[str, bool]) -> dict:
    """Forma reciente, puesto y cara a cara. Si la configuración los apaga, no se enseñan (igual que la app)."""
    if not ficha or not secciones.get("estadisticas"):
        return {"lados": [], "h2h": None}
    lados = [x for x in (_lado(ficha, "local"), _lado(ficha, "visitante")) if x]
    h2h = None
    resumen = (ficha.get("cara_a_cara") or {}).get("resumen") or {}
    if secciones.get("h2h") and resumen.get("n"):
        h2h = {"n": resumen["n"], "local": resumen["victorias_local"], "empates": resumen["empates"],
               "visitante": resumen["victorias_visitante"], "goles": num(resumen["goles_media"])}
    return {"lados": lados if len(lados) == 2 else [], "h2h": h2h}


def construir(fila: dict, ficha: dict | None, secciones: dict[str, bool], ahora: datetime | None = None) -> SimpleNamespace:
    ahora = ahora or _ahora()
    pron = fila["pron"]
    total = sum(pron["probs"].values())
    p = {k: pron["probs"][k] / total for k in LADOS}
    local, visit = fila["local"]["nombre"], fila["visitante"]["nombre"]
    liga = fila["liga"]["nombre"]
    ko = fila["kickoff_utc"] if fila["kickoff_utc"].tzinfo else fila["kickoff_utc"].replace(tzinfo=timezone.utc)
    dia = futbol_datos.fecha_mx(ko)
    st = estado(fila, ahora)
    ver = veredicto(fila)
    slug = futbol_datos.slug_partido(fila)
    ruta = futbol_datos.ruta_partido(fila)
    titulo = f"{local} vs {visit}: pronóstico {liga} {fecha_corta(dia)}"
    if st == "final":
        titulo = f"{local} vs {visit}: pronóstico y resultado {liga} {fecha_corta(dia)}"
    descripcion = (f"Probabilidades del {liga}: {local} {pct(p['home'])}, empate {pct(p['draw'])} y {visit} {pct(p['away'])}. "
                   f"Pronóstico generado antes del partido, con el resultado y los fallos a la vista.")
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=f"{local} vs {visit}"),
        id=fila["match_id"], slug=slug, ruta=ruta, url=seo.base_url() + ruta, local=local, visitante=visit, liga=liga,
        pais=fila["liga"].get("pais"), estado=st, veredicto=ver, inicio=ko, dia=dia, marcador=fila.get("marcador"),
        generada=pron["generada"], modelo=pron["modelo"], probs=p,
        p_local=pct(p["home"]), p_empate=pct(p["draw"]), p_visit=pct(p["away"]),
        brier=num(ver["brier"], 3) if ver else None, ctx=contexto(ficha, secciones))


def jsonld_partido(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo,
           "inLanguage": "es", "description": c.p.descripcion,
           "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
           "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"},
           "about": {"@type": "SportsEvent", "name": f"{c.local} vs {c.visitante}", "sport": "Soccer",
                     "startDate": c.inicio.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                     "eventStatus": ("https://schema.org/EventPostponed" if c.estado == "aplazado"
                                     else "https://schema.org/EventScheduled"),
                     "homeTeam": {"@type": "SportsTeam", "name": c.local},
                     "awayTeam": {"@type": "SportsTeam", "name": c.visitante}}}
    if c.generada:
        web["datePublished"] = c.generada.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "Fútbol", "item": f"{base}{RUTA_PILAR}"},
        {"@type": "ListItem", "position": 3, "name": c.p.migas, "item": c.url}]}, web]


# --- tarjeta para redes ---------------------------------------------------------------------------

def estado_imagen(c: SimpleNamespace) -> str:
    return "final" if c.estado == "final" else "previa"


def tarjeta(c: SimpleNamespace) -> "og.Tarjeta":
    final = estado_imagen(c) == "final"
    return og.Tarjeta("partido", etiqueta="FÚTBOL", local=c.local, visitante=c.visitante, contexto=f"{c.liga} · {fecha_larga(c.dia)}",
                      barra=[(c.local, c.probs["home"]), ("Empate", c.probs["draw"]), (c.visitante, c.probs["away"])],
                      estado=estado_imagen(c), marcador=f"{c.marcador[0]} – {c.marcador[1]}" if final and c.marcador else "",
                      veredicto=(("acerto" if c.veredicto["acerto"] else "fallo") if final and c.veredicto else None))


def tarjeta_de_la_url(comp: str, slug: str):
    fila = futbol_datos.buscar_partido(comp, slug)
    return tarjeta(construir(fila, None, {"estadisticas": False, "h2h": False})) if fila else None


def _imagen_partido(c: SimpleNamespace):
    url = og.url_partido(c.ruta, estado_imagen(c))
    return (url, f"Pronóstico {c.local} vs {c.visitante}: probabilidades del modelo") if url else None


# --- pilar ----------------------------------------------------------------------------------------

def _fila(f: dict, ahora: datetime) -> dict:
    pron = f.get("pron")
    out = {"local": f["local"]["nombre"], "visitante": f["visitante"]["nombre"], "inicio": f["kickoff_utc"],
           "estado": estado(f, ahora), "marcador": f.get("marcador"), "veredicto": veredicto(f),
           "url": futbol_datos.ruta_partido(f) if pron else None}
    if pron:
        total = sum(pron["probs"].values())
        out.update(p_local=pct(pron["probs"]["home"] / total), p_empate=pct(pron["probs"]["draw"] / total),
                   p_visit=pct(pron["probs"]["away"] / total))
    return out


def construir_pilar(ahora: datetime | None = None, ventana: dict[date, list[dict]] | None = None) -> SimpleNamespace:
    ahora = ahora or _ahora()
    hoy = futbol_datos.hoy_mx(ahora)
    ventana = ventana if ventana is not None else futbol_datos.ventana(hoy)
    dias = []
    for d in sorted(ventana, reverse=True):
        por_liga: dict[str, list[dict]] = {}
        for f in sorted(ventana[d], key=lambda x: (x["liga"]["nombre"], x["kickoff_utc"])):
            por_liga.setdefault(f["liga"]["nombre"], []).append(_fila(f, ahora))
        if por_liga:
            dias.append({"iso": d.isoformat(), "largo": fecha_larga(d), "ligas": list(por_liga.items()), "proximo": d >= hoy})
    juzgados = [v for dia in dias for _, filas in dia["ligas"] for f in filas if (v := f["veredicto"])]
    base = seo.base_url()
    pagina = SimpleNamespace(
        titulo="Pronósticos de fútbol: probabilidades de cada partido",
        descripcion=("Probabilidad de victoria, empate y derrota de los partidos de las ligas que seguimos, generadas antes "
                     "del partido y con los aciertos y los fallos a la vista."),
        slug="futbol", migas="Fútbol")
    url = base + RUTA_PILAR
    return SimpleNamespace(
        p=pagina, url=url, dias=dias, juzgados=len(juzgados), aciertos=sum(1 for v in juzgados if v["acerto"]),
        con_pronostico=sum(1 for dia in dias for _, filas in dia["ligas"] for f in filas if f["url"]),
        jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Fútbol", "item": url}]},
            {"@context": "https://schema.org", "@type": "CollectionPage", "name": pagina.titulo, "url": url,
             "inLanguage": "es", "description": pagina.descripcion,
             "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
             "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}}])


# --- sitemap --------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """El pilar siempre; los partidos con pronóstico de la ventana si la base responde. `lastmod` = día de la generación
    del pronóstico mientras no hay marcador; con marcador no hay hora de cierre verificable y se omite."""
    filas: list[tuple[str, str | None]] = [(RUTA_PILAR, None)]
    try:
        ventana = futbol_datos.ventana()
    except FutbolNoDisponible:
        return tuple(filas)
    for d in sorted(ventana, reverse=True):
        for f in ventana[d]:
            if not f.get("pron"):
                continue
            gen = f["pron"]["generada"]
            lastmod = gen.astimezone(timezone.utc).date().isoformat() if gen and not f.get("marcador") else None
            filas.append((futbol_datos.ruta_partido(f), lastmod))
    return tuple(filas)


# --- rutas ----------------------------------------------------------------------------------------

def _pagina(plantilla: str, path: str, p: SimpleNamespace, jsonld: list[dict], datos: dict, imagen=None, **ctx) -> HTMLResponse:
    principal = _env.get_template(plantilla).render(p=p, **ctx)
    cuerpo = rutas_web.render_pagina(titulo=p.titulo, descripcion=p.descripcion, path=path, ruta="partidos",
                                     jsonld=jsonld, principal=principal, datos={"deporte": "futbol", **datos}, imagen=imagen)
    return HTMLResponse(cuerpo, headers={"Cache-Control": "no-cache, must-revalidate"})


def _no_disponible() -> HTTPException:
    return HTTPException(503, detail="Los datos de fútbol no están disponibles en este momento.",
                         headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route("/futbol/", methods=["GET", "HEAD"], name="futbol_pilar")
def pilar():
    from . import web_config

    try:
        if not futbol_datos.secciones_activas()["estadisticas"]:
            raise HTTPException(404)
        c = construir_pilar()
    except FutbolNoDisponible:
        raise _no_disponible()
    c.p, entradilla_override = web_config.apply_editorial_meta(c.p, "sport:futbol", "es")
    url = og.url_pilar("futbol")
    return _pagina("futbol_cartelera.html", RUTA_PILAR, c.p, c.jsonld, {},
                   (url, "Pronósticos de fútbol con probabilidades") if url else None,
                   c=c, entradilla_override=entradilla_override)


@router.api_route("/futbol", methods=["GET", "HEAD"], name="futbol_pilar_sin_barra")
def pilar_sin_barra(request: Request):
    return RedirectResponse(seo.base_url() + RUTA_PILAR + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


@router.api_route("/futbol/{comp}/{slug}/", methods=["GET", "HEAD"], name="futbol_partido")
def partido(comp: str, slug: str):
    try:
        secciones = futbol_datos.secciones_activas()
        if not secciones["estadisticas"]:
            raise HTTPException(404)
        fila = futbol_datos.buscar_partido(comp, slug)
        if fila is None:
            raise HTTPException(404)
        ficha = futbol_datos.ficha(fila["match_id"])
    except FutbolNoDisponible:
        raise _no_disponible()
    c = construir(fila, ficha, secciones)
    return _pagina("futbol_partido.html", c.ruta, c.p, jsonld_partido(c, seo.base_url()),
                   {"evento": c.id, "inicio": c.inicio.astimezone(timezone.utc).isoformat()}, _imagen_partido(c), c=c)


@router.api_route("/futbol/{comp}/{slug}", methods=["GET", "HEAD"], name="futbol_partido_sin_barra")
def partido_sin_barra(comp: str, slug: str, request: Request):
    if not futbol_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}/futbol/{comp}/{slug}/" + (f"?{request.url.query}" if request.url.query else ""),
                            status_code=301)
