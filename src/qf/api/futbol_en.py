"""Páginas públicas de fútbol en INGLÉS (F6.2b de docs/plan_seo_redes_web_20261108.md, §9): `/en/futbol/` y `/en/futbol/{competición}/{slug}/`.

Igual que `nba_en.py`: páginas independientes sobre `base_en.html`, no la aplicación de una sola página. Reutilizan los datos y las
reglas del español (`futbol_paginas.estado`, el veredicto, la forma y el cara a cara) para que las dos versiones digan lo mismo; aquí
cambian la redacción, el formato (`62%`, `2.10`, `Nov 8, 2026`) y el idioma. El español no se toca.

Glosario: pronóstico → forecast; empate → draw; local/visitante → home/away; forma → form; clasificación → league position; las
competiciones y los nombres de equipo se dejan tal cual (son nombres propios). Detrás del interruptor de idioma (`idiomas.py`).
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

from . import futbol_datos, futbol_paginas, idiomas, og, paginas, seo
from .futbol_datos import FutbolNoDisponible

log = logging.getLogger("qf.futbol_en")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA_PILAR = "/en/futbol/"
RUTA_PILAR_ES = futbol_paginas.RUTA_PILAR
PREFIJO = "/en"
LADOS = ("home", "draw", "away")
FORMA_ES_EN = str.maketrans({"G": "W", "E": "D", "P": "L"})      # la racha guarda G/E/P; en inglés W/D/L


# --- formato inglés ---------------------------------------------------------------------------------

def pct(p: float) -> str:
    return f"{round(p * 100)}%"


def num(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}"


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def fecha_corta(d: date) -> str:
    return f"{paginas.MONTHS_EN[d.month - 1][:3]} {d.day}, {d.year}"


def fecha_hora_utc(dt: datetime) -> str:
    u = dt.astimezone(timezone.utc)
    return f"{paginas.MONTHS_EN[u.month - 1][:3]} {u.day}, {u.year} at {u:%H:%M} UTC"


# --- equivalencias español ↔ inglés (hreflang y selector) ---------------------------------------------

_RUTA_PARTIDO = re.compile(r"^(?P<en>/en)?/futbol/(?P<comp>[^/]+)/(?P<slug>[^/]+)/$")


def equivalencias(ruta: str) -> dict[str, str] | None:
    if ruta in (RUTA_PILAR, RUTA_PILAR_ES):
        return {"es": RUTA_PILAR_ES, "en": RUTA_PILAR}
    m = _RUTA_PARTIDO.match(ruta)
    if m and futbol_datos.SLUG_PARTIDO.match(m["slug"]):
        base = f"/futbol/{m['comp']}/{m['slug']}/"
        return {"es": base, "en": PREFIJO + base}
    return None


idiomas.registrar_traductor(equivalencias)


# --- interpretación (la misma regla que el español, con el texto en inglés) ----------------------------

def veredicto(fila: dict) -> dict | None:
    """¿Se cumplió el resultado más probable y cuánto vale el Brier del 1X2? Solo con marcador final."""
    pron, marcador = fila.get("pron"), fila.get("marcador")
    if not pron or not marcador:
        return None
    gl, gv = marcador
    real = "home" if gl > gv else "away" if gv > gl else "draw"
    probs = pron["probs"]
    total = sum(probs.values())
    p = {k: probs[k] / total for k in LADOS}
    favorito = max(LADOS, key=lambda k: (p[k], k == "home"))
    nombres = {"home": fila["local"]["nombre"], "away": fila["visitante"]["nombre"], "draw": "a draw"}
    return {"acerto": favorito == real, "favorito": nombres[favorito], "resultado": nombres[real],
            "brier": sum((p[k] - (1.0 if k == real else 0.0)) ** 2 for k in LADOS)}


def _lado(ficha: dict, clave: str) -> dict | None:
    lado = (ficha or {}).get(clave) or {}
    forma = (lado.get("forma") or {}).get("resumen") or {}
    clas = lado.get("clasificacion")
    if not lado.get("nombre") or not forma.get("n"):
        return None
    return {"nombre": lado["nombre"], "racha": str(forma.get("racha", "")).translate(FORMA_ES_EN), "puntos": forma.get("puntos"),
            "n": forma["n"], "gf": forma.get("gf"), "gc": forma.get("gc"),
            "puesto": (f"{ordinal(clas['posicion'])} in {clas['liga']} with {clas['puntos']} points" if clas else None)}


def contexto(ficha: dict | None, secciones: dict[str, bool]) -> dict:
    """Forma reciente, posición y cara a cara. Si la configuración los apaga, no se enseñan (igual que el español)."""
    if not ficha or not secciones.get("estadisticas"):
        return {"lados": [], "h2h": None}
    lados = [x for x in (_lado(ficha, "local"), _lado(ficha, "visitante")) if x]
    h2h = None
    resumen = (ficha.get("cara_a_cara") or {}).get("resumen") or {}
    if secciones.get("h2h") and resumen.get("n"):
        h2h = {"n": resumen["n"], "local": resumen["victorias_local"], "empates": resumen["empates"],
               "visitante": resumen["victorias_visitante"], "goles": num(resumen["goles_media"], 2)}
    return {"lados": lados if len(lados) == 2 else [], "h2h": h2h}


def construir(fila: dict, ficha: dict | None, secciones: dict[str, bool], ahora: datetime | None = None) -> SimpleNamespace:
    ahora = ahora or futbol_paginas._ahora()
    pron = fila["pron"]
    total = sum(pron["probs"].values())
    p = {k: pron["probs"][k] / total for k in LADOS}
    local, visit = fila["local"]["nombre"], fila["visitante"]["nombre"]
    liga = fila["liga"]["nombre"]
    ko = fila["kickoff_utc"] if fila["kickoff_utc"].tzinfo else fila["kickoff_utc"].replace(tzinfo=timezone.utc)
    dia = futbol_datos.fecha_mx(ko)
    st = futbol_paginas.estado(fila, ahora)
    ver = veredicto(fila)
    slug = futbol_datos.slug_partido(fila)
    ruta = PREFIJO + futbol_datos.ruta_partido(fila)
    titulo = f"{local} vs {visit}: prediction {liga}, {fecha_corta(dia)}"
    if st == "final":
        titulo = f"{local} vs {visit}: prediction and result {liga}, {fecha_corta(dia)}"
    descripcion = (f"{liga} win probabilities: {local} {pct(p['home'])}, draw {pct(p['draw'])} and {visit} {pct(p['away'])}. "
                   f"Forecast generated before kick-off, with the result and the misses in plain view.")
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=f"{local} vs {visit}"),
        id=fila["match_id"], slug=slug, ruta=ruta, url=seo.base_url() + ruta, local=local, visitante=visit, liga=liga,
        pais=fila["liga"].get("pais"), estado=st, veredicto=ver, inicio=ko, dia=dia, marcador=fila.get("marcador"),
        generada=pron["generada"], modelo=pron["modelo"], probs=p,
        p_local=pct(p["home"]), p_empate=pct(p["draw"]), p_visit=pct(p["away"]),
        brier=num(ver["brier"], 3) if ver else None, ctx=contexto(ficha, secciones),
        inicio_txt=fecha_hora_utc(ko), generada_txt=fecha_hora_utc(pron["generada"]) if pron.get("generada") else None)


def _organizacion() -> dict:
    return {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}


def jsonld_partido(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo,
           "inLanguage": "en", "description": c.p.descripcion,
           "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"}, "publisher": _organizacion(),
           "about": {"@type": "SportsEvent", "name": f"{c.local} vs {c.visitante}", "sport": "Soccer",
                     "startDate": c.inicio.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                     "eventStatus": ("https://schema.org/EventPostponed" if c.estado == "aplazado"
                                     else "https://schema.org/EventScheduled"),
                     "homeTeam": {"@type": "SportsTeam", "name": c.local},
                     "awayTeam": {"@type": "SportsTeam", "name": c.visitante}}}
    if c.generada:
        web["datePublished"] = c.generada.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "Football", "item": f"{base}{RUTA_PILAR}"},
        {"@type": "ListItem", "position": 3, "name": c.p.migas, "item": c.url}]}, web]


# --- pilar ----------------------------------------------------------------------------------------

def _fila(f: dict, ahora: datetime) -> dict:
    pron = f.get("pron")
    out = {"local": f["local"]["nombre"], "visitante": f["visitante"]["nombre"], "inicio": f["kickoff_utc"],
           "estado": futbol_paginas.estado(f, ahora), "marcador": f.get("marcador"), "veredicto": veredicto(f),
           "url": PREFIJO + futbol_datos.ruta_partido(f) if pron else None}
    if pron:
        total = sum(pron["probs"].values())
        out.update(p_local=pct(pron["probs"]["home"] / total), p_empate=pct(pron["probs"]["draw"] / total),
                   p_visit=pct(pron["probs"]["away"] / total))
    return out


def construir_pilar(ahora: datetime | None = None, ventana: dict[date, list[dict]] | None = None) -> SimpleNamespace:
    ahora = ahora or futbol_paginas._ahora()
    hoy = futbol_datos.hoy_mx(ahora)
    ventana = ventana if ventana is not None else futbol_datos.ventana(hoy)
    dias = []
    for d in sorted(ventana, reverse=True):
        por_liga: dict[str, list[dict]] = {}
        for f in sorted(ventana[d], key=lambda x: (x["liga"]["nombre"], x["kickoff_utc"])):
            por_liga.setdefault(f["liga"]["nombre"], []).append(_fila(f, ahora))
        if por_liga:
            dias.append({"iso": d.isoformat(), "largo": paginas.fecha_larga(d, "en"), "ligas": list(por_liga.items()), "proximo": d >= hoy})
    juzgados = [v for dia in dias for _, filas in dia["ligas"] for f in filas if (v := f["veredicto"])]
    base = seo.base_url()
    url = base + RUTA_PILAR
    pagina = SimpleNamespace(
        titulo="Football predictions: win probabilities for every match",
        descripcion=("Home win, draw and away win probabilities for the leagues we follow, generated before each match "
                     "and with the hits and misses in plain view."),
        slug="futbol", migas="Football")
    return SimpleNamespace(
        p=pagina, url=url, dias=dias, juzgados=len(juzgados), aciertos=sum(1 for v in juzgados if v["acerto"]),
        con_pronostico=sum(1 for dia in dias for _, filas in dia["ligas"] for f in filas if f["url"]),
        jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Football", "item": url}]},
            {"@context": "https://schema.org", "@type": "CollectionPage", "name": pagina.titulo, "url": url, "inLanguage": "en",
             "description": pagina.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
             "publisher": _organizacion()}])


# --- sitemap --------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Solo con el inglés abierto (`on`): las mismas entradas que el español, con el prefijo `/en`."""
    if idiomas.estado("en") != "on":
        return ()
    return tuple((PREFIJO + ruta, lastmod) for ruta, lastmod in futbol_paginas.entradas_sitemap())


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
    return HTTPException(503, detail="Football data is not available right now.", headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route(RUTA_PILAR, methods=["GET", "HEAD"], name="en_futbol_pilar")
def pilar():
    idiomas.puerta("en")
    try:
        if not futbol_datos.secciones_activas()["estadisticas"]:
            raise HTTPException(404)
        c = construir_pilar()
    except FutbolNoDisponible:
        raise _no_disponible()
    return _responder("en_futbol_cartelera.html", c.p, c.url, c.jsonld, RUTA_PILAR, og_imagen=og.url_pilar_en("futbol"), c=c)


@router.api_route(RUTA_PILAR.rstrip("/"), methods=["GET", "HEAD"], name="en_futbol_pilar_sin_barra")
def pilar_sin_barra(request: Request):
    idiomas.puerta("en")
    return RedirectResponse(seo.base_url() + RUTA_PILAR + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


@router.api_route("/en/futbol/{comp}/{slug}/", methods=["GET", "HEAD"], name="en_futbol_partido")
def partido(comp: str, slug: str):
    idiomas.puerta("en")
    try:
        secciones = futbol_datos.secciones_activas()
        if not secciones["estadisticas"]:
            raise HTTPException(404)
        if not futbol_datos.SLUG_PARTIDO.match(slug):
            raise HTTPException(404)
        fila = futbol_datos.buscar_partido(comp, slug)
        if fila is None:
            raise HTTPException(404)
        ficha = futbol_datos.ficha(fila["match_id"])
    except FutbolNoDisponible:
        raise _no_disponible()
    c = construir(fila, ficha, secciones)
    imagen = og.url_partido(c.ruta, futbol_paginas.estado_imagen(c))
    return _responder("en_futbol_partido.html", c.p, c.url, jsonld_partido(c, seo.base_url()), c.ruta, og_imagen=imagen, c=c)


@router.api_route("/en/futbol/{comp}/{slug}", methods=["GET", "HEAD"], name="en_futbol_partido_sin_barra")
def partido_sin_barra(comp: str, slug: str, request: Request):
    idiomas.puerta("en")
    if not futbol_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}/en/futbol/{comp}/{slug}/" + (f"?{request.url.query}" if request.url.query else ""),
                            status_code=301)


# --- tarjeta para redes (en inglés) -------------------------------------------------------------------

def tarjeta(c: SimpleNamespace) -> "og.Tarjeta":
    final = futbol_paginas.estado_imagen(c) == "final"
    return og.Tarjeta("partido", etiqueta="FOOTBALL", local=c.local, visitante=c.visitante, contexto=f"{c.liga} · {fecha_corta(c.dia)}",
                      barra=[(c.local, c.probs["home"]), ("Draw", c.probs["draw"]), (c.visitante, c.probs["away"])],
                      estado=futbol_paginas.estado_imagen(c),
                      marcador=f"{c.marcador[0]} – {c.marcador[1]}" if final and c.marcador else "",
                      veredicto=(("acerto" if c.veredicto["acerto"] else "fallo") if final and c.veredicto else None), idioma="en")


def tarjeta_de_la_url(comp: str, slug: str):
    fila = futbol_datos.buscar_partido(comp, slug)
    return tarjeta(construir(fila, None, {"estadisticas": False, "h2h": False})) if fila else None
