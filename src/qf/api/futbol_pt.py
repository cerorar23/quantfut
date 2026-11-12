"""Páginas públicas de fútbol en PORTUGUÉS de Brasil (F6.4c de docs/plan_seo_redes_web_20261108.md, §9): `/pt/futebol/` y `/pt/futebol/{competição}/{slug}/`.

Igual que `futbol_en.py`: páginas independientes sobre `base_pt.html`. Reutilizan los datos y las reglas del español (`futbol_paginas.estado`,
el veredicto, la forma, la posición y el cara a cara). Aquí cambian la redacción, las cifras (coma decimal), el formato de fecha
(`8 de novembro de 2026`), la forma (G/E/P → V/E/D: vitória, empate, derrota) y el idioma. El español no se toca.

Glosario: mandante/visitante = home/away; confronto direto = head to head; classificação = standings; previsão = forecast.
Las competiciones y los nombres de equipo se dejan tal cual.
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
from . import futbol_datos, futbol_paginas, idiomas, og, paginas, seo
from .futbol_datos import FutbolNoDisponible

log = logging.getLogger("qf.futbol_pt")
router = APIRouter(include_in_schema=False, dependencies=[Depends(catalogo.exigir_web('futbol'))])
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA_PILAR = "/pt/futebol/"
RUTA_PILAR_ES = futbol_paginas.RUTA_PILAR
PREFIJO = "/pt"
LADOS = ("home", "draw", "away")
FORMA_ES_PT = str.maketrans({"G": "V", "E": "E", "P": "D"})     # la racha guarda G/E/P; en portugués V/E/D


# --- formato portugués -----------------------------------------------------------------------------

def pct(p: float) -> str:
    return f"{round(p * 100)}%"


def num(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def ruta_pt(ruta_es: str) -> str:
    """`/futbol/{comp}/{slug}/` → `/pt/futebol/{comp}/{slug}/` (la URL portuguesa usa la palabra portuguesa)."""
    return "/pt/futebol/" + ruta_es[len("/futbol/"):]


def ordinal(n: int) -> str:
    return f"{n}º"


def fecha_hora_utc(dt: datetime) -> str:
    u = dt.astimezone(timezone.utc)
    return f"{paginas.fecha_larga(u.date(), 'pt')} às {u:%H:%M} UTC"


# --- equivalencias español ↔ portugués --------------------------------------------------------------

_RUTA_PARTIDO = re.compile(r"^(?:/pt/futebol|/futbol)/(?P<comp>[^/]+)/(?P<slug>[^/]+)/$")


def equivalencias(ruta: str) -> dict[str, str] | None:
    if ruta in (RUTA_PILAR, RUTA_PILAR_ES):
        return {"es": RUTA_PILAR_ES, "pt": RUTA_PILAR}
    m = _RUTA_PARTIDO.match(ruta)
    if m and futbol_datos.SLUG_PARTIDO.match(m["slug"]):
        es = f"/futbol/{m['comp']}/{m['slug']}/"
        return {"es": es, "pt": ruta_pt(es)}
    return None


idiomas.registrar_traductor(equivalencias)


# --- interpretación (la misma regla que el español, con el texto en portugués) ------------------------

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
    nombres = {"home": fila["local"]["nombre"], "away": fila["visitante"]["nombre"], "draw": "o empate"}
    return {"acerto": favorito == real, "favorito": nombres[favorito], "resultado": nombres[real],
            "brier": sum((p[k] - (1.0 if k == real else 0.0)) ** 2 for k in LADOS)}


def _lado(ficha: dict, clave: str) -> dict | None:
    lado = (ficha or {}).get(clave) or {}
    forma = (lado.get("forma") or {}).get("resumen") or {}
    clas = lado.get("clasificacion")
    if not lado.get("nombre") or not forma.get("n"):
        return None
    return {"nombre": lado["nombre"], "racha": str(forma.get("racha", "")).translate(FORMA_ES_PT), "puntos": forma.get("puntos"),
            "n": forma["n"], "gf": forma.get("gf"), "gc": forma.get("gc"),
            "puesto": (f"{ordinal(clas['posicion'])} na {clas['liga']} com {clas['puntos']} pontos" if clas else None)}


def contexto(ficha: dict | None, secciones: dict[str, bool]) -> dict:
    """Forma reciente, clasificación y cara a cara. Si la configuración los apaga, no se muestran (igual que el español)."""
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
    ruta = ruta_pt(futbol_datos.ruta_partido(fila))
    titulo = f"{local} x {visit}: previsão {liga}, {paginas.fecha_larga(dia, 'pt')}"
    if st == "final":
        titulo = f"{local} x {visit}: previsão e resultado {liga}, {paginas.fecha_larga(dia, 'pt')}"
    descripcion = (f"Probabilidades da {liga}: {local} {pct(p['home'])}, empate {pct(p['draw'])} e {visit} {pct(p['away'])}. "
                   f"Previsão gerada antes do jogo, com o resultado e os erros à vista.")
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=f"{local} x {visit}"),
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
           "inLanguage": "pt", "description": c.p.descripcion,
           "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"}, "publisher": _organizacion(),
           "about": {"@type": "SportsEvent", "name": f"{c.local} x {c.visitante}", "sport": "Soccer",
                     "startDate": c.inicio.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                     "eventStatus": ("https://schema.org/EventPostponed" if c.estado == "aplazado"
                                     else "https://schema.org/EventScheduled"),
                     "homeTeam": {"@type": "SportsTeam", "name": c.local},
                     "awayTeam": {"@type": "SportsTeam", "name": c.visitante}}}
    if c.generada:
        web["datePublished"] = c.generada.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "Futebol", "item": f"{base}{RUTA_PILAR}"},
        {"@type": "ListItem", "position": 3, "name": c.p.migas, "item": c.url}]}, web]


# --- pilar ----------------------------------------------------------------------------------------------

def _fila(f: dict, ahora: datetime) -> dict:
    pron = f.get("pron")
    out = {"local": f["local"]["nombre"], "visitante": f["visitante"]["nombre"], "inicio": f["kickoff_utc"],
           "estado": futbol_paginas.estado(f, ahora), "marcador": f.get("marcador"), "veredicto": veredicto(f),
           "url": ruta_pt(futbol_datos.ruta_partido(f)) if pron else None}
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
            dias.append({"iso": d.isoformat(), "largo": paginas.fecha_larga(d, "pt"), "ligas": list(por_liga.items()), "proximo": d >= hoy})
    juzgados = [v for dia in dias for _, filas in dia["ligas"] for f in filas if (v := f["veredicto"])]
    base = seo.base_url()
    url = base + RUTA_PILAR
    pagina = SimpleNamespace(
        titulo="Previsões de futebol: probabilidades de cada jogo",
        descripcion=("Probabilidade de vitória do mandante, empate e vitória do visitante nas ligas que acompanhamos, geradas "
                     "antes do jogo e com os acertos e erros à vista."),
        slug="futebol", migas="Futebol")
    return SimpleNamespace(
        p=pagina, url=url, dias=dias, juzgados=len(juzgados), aciertos=sum(1 for v in juzgados if v["acerto"]),
        con_pronostico=sum(1 for dia in dias for _, filas in dia["ligas"] for f in filas if f["url"]),
        jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "QuantFut", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Futebol", "item": url}]},
            {"@context": "https://schema.org", "@type": "CollectionPage", "name": pagina.titulo, "url": url, "inLanguage": "pt",
             "description": pagina.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
             "publisher": _organizacion()}])


# --- sitemap --------------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """Solo con el portugués abierto (`on`): las mismas entradas que el español, con la URL portuguesa."""
    if idiomas.estado("pt") != "on":
        return ()
    return tuple((ruta if ruta == RUTA_PILAR else ruta_pt(ruta), lastmod) for ruta, lastmod in futbol_paginas.entradas_sitemap())


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
    return HTTPException(503, detail="Os dados de futebol não estão disponíveis no momento.",
                         headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route(RUTA_PILAR, methods=["GET", "HEAD"], name="pt_futbol_pilar")
def pilar():
    from . import web_config

    idiomas.puerta("pt")
    try:
        if not futbol_datos.secciones_activas()["estadisticas"]:
            raise HTTPException(404)
        c = construir_pilar()
    except FutbolNoDisponible:
        raise _no_disponible()
    c.p, entradilla_override = web_config.apply_editorial_meta(c.p, "sport:futbol", "pt")
    return _responder("pt_futbol_cartelera.html", c.p, c.url, c.jsonld, RUTA_PILAR,
                      og_imagen=og.url_pilar_pt("futbol"), c=c, entradilla_override=entradilla_override)


@router.api_route(RUTA_PILAR.rstrip("/"), methods=["GET", "HEAD"], name="pt_futbol_pilar_sin_barra")
def pilar_sin_barra(request: Request):
    idiomas.puerta("pt")
    return RedirectResponse(seo.base_url() + RUTA_PILAR + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


@router.api_route("/pt/futebol/{comp}/{slug}/", methods=["GET", "HEAD"], name="pt_futbol_partido")
def partido(comp: str, slug: str):
    idiomas.puerta("pt")
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
    return _responder("pt_futbol_partido.html", c.p, c.url, jsonld_partido(c, seo.base_url()), c.ruta, og_imagen=imagen, c=c)


@router.api_route("/pt/futebol/{comp}/{slug}", methods=["GET", "HEAD"], name="pt_futbol_partido_sin_barra")
def partido_sin_barra(comp: str, slug: str, request: Request):
    idiomas.puerta("pt")
    if not futbol_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}/pt/futebol/{comp}/{slug}/" + (f"?{request.url.query}" if request.url.query else ""),
                            status_code=301)


# --- tarjeta para redes (en portugués) -----------------------------------------------------------

def tarjeta(c: SimpleNamespace) -> "og.Tarjeta":
    final = futbol_paginas.estado_imagen(c) == "final"
    return og.Tarjeta("partido", etiqueta="FUTEBOL", local=c.local, visitante=c.visitante,
                      contexto=f"{c.liga} · {paginas.fecha_larga(c.dia, 'pt')}",
                      barra=[(c.local, c.probs["home"]), ("Empate", c.probs["draw"]), (c.visitante, c.probs["away"])],
                      estado=futbol_paginas.estado_imagen(c),
                      marcador=f"{c.marcador[0]} – {c.marcador[1]}" if final and c.marcador else "",
                      veredicto=(("acerto" if c.veredicto["acerto"] else "fallo") if final and c.veredicto else None), idioma="pt")


def tarjeta_de_la_url(comp: str, slug: str):
    fila = futbol_datos.buscar_partido(comp, slug)
    return tarjeta(construir(fila, None, {"estadisticas": False, "h2h": False})) if fila else None

