"""Páginas públicas de NBA con HTML completo desde el servidor (F2.1 de docs/plan_seo_redes_web_20261108.md).

- `/nba/`: cartelera de los últimos días y los próximos, con enlaces `<a href>` reales.
- `/nba/{local}-vs-{visitante}-{AAAA-MM-DD}/`: un partido con pronóstico sellado. Sin sello no existe (404).

Todo el texto sale de los datos que `nba-api` ya publica sin cuenta (`nba_datos.py`); aquí no se calcula ninguna
probabilidad. Los fallos se muestran igual que los aciertos. La fecha del URL es la fecha ET del partido
(`fecha_juego_et`), la misma que usa la cartelera.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import nba_datos, paginas, rutas_web, seo
from .nba_datos import NbaNoDisponible

log = logging.getLogger("qf.nba_paginas")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

DIAS_ATRAS = 3          # resultados recientes que muestra el pilar
DIAS_ADELANTE = 2       # el sello llega ~60 min antes del inicio: más allá casi no hay pronósticos
HORAS_SIN_RESULTADO = 8  # pasado este tiempo sin marcador se dice «pendiente de confirmar»
RUTA_PILAR = "/nba/"
RESERVADOS = {"v1", "v2"}   # los sirve nba-api; si llegaran aquí no son páginas


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


# --- formato --------------------------------------------------------------------------------------

def pct(p: float) -> str:
    return f"{round(p * 100)} %"


def num(x: float, dec: int = 1) -> str:
    return f"{x:.{dec}f}".replace(".", ",")


def entero(x: float) -> str:
    return str(int(round(x)))


def fecha_larga(d: date) -> str:
    return paginas.fecha_larga(d)


def fecha_corta(d: date) -> str:
    return f"{d.day} {paginas.MESES[d.month - 1][:3]} {d.year}"


def hora_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%H:%M") + " UTC"


def _dt(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        dt = datetime.fromisoformat(texto)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# --- interpretación de un partido ----------------------------------------------------------------

def estado(p: dict, ahora: datetime) -> str:
    """previa | curso | pendiente | final. Solo se sabe lo que dice la API: un marcador final o no."""
    if p.get("resultado"):
        return "final"
    inicio = _dt(p.get("inicio_utc"))
    if inicio is None or ahora < inicio:
        return "previa"
    return "pendiente" if ahora - inicio > timedelta(hours=HORAS_SIN_RESULTADO) else "curso"


def veredicto(p: dict) -> dict | None:
    """¿Acertó el ganador pronosticado y cuánto vale el Brier de esa probabilidad? Solo con resultado."""
    r, pr = p.get("resultado"), p.get("pronostico")
    if not r or not pr or r["local"] == r["visitante"]:
        return None
    local_gana = r["local"] > r["visitante"]
    p_local = pr["p_local"]
    favorito_local = p_local >= 0.5
    return {"acerto": favorito_local == local_gana,
            "favorito": p["local"]["nombre"] if favorito_local else p["visitante"]["nombre"],
            "ganador": p["local"]["nombre"] if local_gana else p["visitante"]["nombre"],
            "brier": (p_local - (1.0 if local_gana else 0.0)) ** 2}


def _contexto_equipos(p: dict) -> list[dict]:
    datos = nba_datos.estadisticas(p["id"], date.fromisoformat(p["fecha"]))
    equipos = {t.get("name"): t for t in (datos or {}).get("teams", []) if isinstance(t, dict)}
    filas = []
    for rol, clave in (("local", "local"), ("visitante", "visitante")):
        nombre = p[clave]["nombre"]
        t = equipos.get(nombre)
        if not t or not isinstance(t.get("season"), dict) or not isinstance(t.get("last6"), dict):
            return []   # sin los dos equipos completos no se muestra una tabla a medias
        racha = t.get("streak") or 0
        filas.append({
            "nombre": nombre, "rol": rol,
            "record": f"{t['season']['won']}-{t['season']['lost']}",
            "ultimos6": f"{t['last6']['won']}-{t['last6']['lost']}",
            "racha": (f"{abs(racha)} " + ("victorias" if racha > 0 else "derrotas") + " seguidas") if racha else "—",
            "descanso": "partido en dos noches seguidas" if t.get("back_to_back") else (
                f"{t['rest_days']} días de descanso" if isinstance(t.get("rest_days"), int) else "—"),
        })
    return filas


def construir(p: dict, ahora: datetime | None = None) -> SimpleNamespace:
    ahora = ahora or _ahora()
    pr = p["pronostico"]
    local, visit = p["local"]["nombre"], p["visitante"]["nombre"]
    fecha = date.fromisoformat(p["fecha"])
    inicio, sellado = _dt(p.get("inicio_utc")), _dt(pr.get("sellado_en"))
    st = estado(p, ahora)
    ver = veredicto(p)
    pl = pr["p_local"]
    margen = pr["mediana"]["margen"]
    if margen == 0:
        texto_margen = "La mediana del margen es 0: el modelo no inclina el partido hacia ningún lado."
    else:
        favorecido = local if margen > 0 else visit
        texto_margen = f"La mediana del margen es de {entero(abs(margen))} puntos a favor de {favorecido}."
    a, b = pr["margen_p10_p90"], pr["total_p10_p90"]
    slug = nba_datos.slug_partido(p)
    url = f"{seo.base_url()}/nba/{slug}/"
    titulo = f"{local} vs {visit}: pronóstico {fecha_corta(fecha)}"
    if st == "final":
        titulo = f"{local} vs {visit}: pronóstico y resultado {fecha_corta(fecha)}"
    descripcion = (f"Probabilidad de victoria: {local} {pct(pl)} y {visit} {pct(1 - pl)}. Marcador esperado, rango de "
                   f"márgenes y pronóstico sellado con hash antes del partido.")
    return SimpleNamespace(
        p=SimpleNamespace(titulo=titulo, descripcion=descripcion, slug=slug, migas=f"{local} vs {visit}"),
        id=p["id"], slug=slug, url=url, local=local, visitante=visit, fecha=fecha, estado=st, veredicto=ver,
        inicio=inicio, sellado=sellado, resultado=p.get("resultado"),
        p_local=pct(pl), p_visit=pct(1 - pl), mu_local=num(pr["mu"][0]), mu_visit=num(pr["mu"][1]),
        texto_margen=texto_margen,
        margen_rango=(f"{entero(a[0])} y {'+' if a[1] > 0 else ''}{entero(a[1])}"),
        total_mediana=entero(pr["mediana"]["total"]), total_rango=f"{entero(b[0])} y {entero(b[1])}",
        hash=pr["hash"], version=str(pr.get("version_modelo", "")).split(";")[0], objetivo=_dt(pr.get("objetivo_en")),
        contexto=_contexto_equipos(p), fecha_iso=p["fecha"],
        brier=num(ver["brier"], 3) if ver else None)


def _jsonld_partido(c: SimpleNamespace, base: str) -> list[dict]:
    web = {"@context": "https://schema.org", "@type": "WebPage", "@id": c.url, "url": c.url, "name": c.p.titulo,
           "inLanguage": "es", "description": c.p.descripcion,
           "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
           "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"},
           "about": {"@type": "SportsEvent", "name": f"{c.local} vs {c.visitante}", "sport": "Basketball",
                     "eventStatus": "https://schema.org/EventScheduled",
                     "homeTeam": {"@type": "SportsTeam", "name": c.local},
                     "awayTeam": {"@type": "SportsTeam", "name": c.visitante}}}
    if c.inicio:
        web["about"]["startDate"] = c.inicio.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if c.sellado:
        web["datePublished"] = c.sellado.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
        {"@type": "ListItem", "position": 2, "name": "NBA", "item": f"{base}{RUTA_PILAR}"},
        {"@type": "ListItem", "position": 3, "name": c.p.migas, "item": c.url}]}, web]


# --- pilar ----------------------------------------------------------------------------------------

def _ventana(hoy: date | None = None) -> dict[date, list[dict]]:
    hoy = hoy or nba_datos.hoy_et(_ahora())
    return nba_datos.cartelera_ventana(hoy - timedelta(days=DIAS_ATRAS), hoy + timedelta(days=DIAS_ADELANTE))


def _fila(p: dict, ahora: datetime) -> dict:
    pr = p.get("pronostico")
    f = {"local": p["local"]["nombre"], "visitante": p["visitante"]["nombre"],
         "inicio": _dt(p.get("inicio_utc")), "estado": estado(p, ahora), "resultado": p.get("resultado"),
         "url": f"/nba/{nba_datos.slug_partido(p)}/" if pr else None, "veredicto": veredicto(p)}
    if pr:
        f["p_local"], f["p_visit"] = pct(pr["p_local"]), pct(1 - pr["p_local"])
    return f


def construir_pilar(ahora: datetime | None = None, ventana: dict[date, list[dict]] | None = None) -> SimpleNamespace:
    ahora = ahora or _ahora()
    hoy = nba_datos.hoy_et(ahora)
    ventana = ventana if ventana is not None else _ventana(hoy)
    dias = []
    for d in sorted(ventana, reverse=True):
        filas = [_fila(p, ahora) for p in sorted(ventana[d], key=lambda x: x.get("inicio_utc") or "")]
        if filas:
            dias.append({"fecha": d, "iso": d.isoformat(), "largo": fecha_larga(d), "filas": filas,
                         "proximo": d >= hoy})
    juzgados = [f["veredicto"] for dia in dias for f in dia["filas"] if f["veredicto"]]
    base = seo.base_url()
    url = base + RUTA_PILAR
    pagina = SimpleNamespace(
        titulo="Pronósticos NBA: probabilidades de cada partido",
        descripcion=("Probabilidad de victoria, marcador esperado y rango de márgenes de cada partido de la NBA, "
                     "sellados con hash antes del inicio. Con los aciertos y los fallos a la vista."),
        slug="nba", migas="NBA")
    return SimpleNamespace(p=pagina, url=url, dias=dias, aciertos=sum(1 for v in juzgados if v["acerto"]),
                           juzgados=len(juzgados), con_pronostico=sum(1 for dia in dias for f in dia["filas"] if f["url"]),
                           jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                               {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
                               {"@type": "ListItem", "position": 2, "name": "NBA", "item": url}]},
                               {"@context": "https://schema.org", "@type": "CollectionPage", "name": pagina.titulo,
                                "url": url, "inLanguage": "es", "description": pagina.descripcion,
                                "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
                                "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"}}])


# --- sitemap --------------------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    """El pilar siempre; los partidos con sello de la ventana si el motor responde (si no, solo el pilar).
    `lastmod` = día del sello mientras no hay marcador; con marcador no hay una hora de cierre verificable y se omite."""
    filas: list[tuple[str, str | None]] = [(RUTA_PILAR, None)]
    try:
        ventana = _ventana()
    except NbaNoDisponible:
        return tuple(filas)
    for d in sorted(ventana, reverse=True):
        for p in ventana[d]:
            pr = p.get("pronostico")
            if not pr:
                continue
            sellado = _dt(pr.get("sellado_en"))
            lastmod = sellado.astimezone(timezone.utc).date().isoformat() if sellado and not p.get("resultado") else None
            filas.append((f"/nba/{nba_datos.slug_partido(p)}/", lastmod))
    return tuple(filas)


# --- rutas ----------------------------------------------------------------------------------------

def _pagina(plantilla: str, path: str, p: SimpleNamespace, jsonld: list[dict], datos: dict, **ctx) -> HTMLResponse:
    """La página dentro del shell de la SPA (mismo diseño que el resto de la web): el contenido en el HTML inicial es
    lo que leen Google y las redes; la persona ve la app, que arranca en este mismo partido (frontend/rutas.js)."""
    principal = _env.get_template(plantilla).render(p=p, **ctx)
    cuerpo = rutas_web.render_pagina(titulo=p.titulo, descripcion=p.descripcion, path=path, ruta="partidos",
                                     jsonld=jsonld, principal=principal, datos={"deporte": "nba", **datos})
    return HTMLResponse(cuerpo, headers={"Cache-Control": "no-cache, must-revalidate"})


def _no_disponible() -> HTTPException:
    # 503, no 404: un fallo pasajero del motor no debe retirar la página del índice.
    return HTTPException(503, detail="Los datos de NBA no están disponibles en este momento.",
                         headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route("/nba/", methods=["GET", "HEAD"], name="nba_pilar")
def pilar():
    try:
        c = construir_pilar()
    except NbaNoDisponible:
        raise _no_disponible()
    return _pagina("nba_cartelera.html", RUTA_PILAR, c.p, c.jsonld, {}, c=c)


@router.api_route("/nba", methods=["GET", "HEAD"], name="nba_pilar_sin_barra")
def pilar_sin_barra(request: Request):
    return RedirectResponse(seo.base_url() + RUTA_PILAR + (f"?{request.url.query}" if request.url.query else ""), status_code=301)


@router.api_route("/nba/{slug}/", methods=["GET", "HEAD"], name="nba_partido")
def partido(slug: str):
    if slug in RESERVADOS:
        raise HTTPException(404)
    try:
        p = nba_datos.buscar_partido(slug)
    except NbaNoDisponible:
        raise _no_disponible()
    if p is None:
        raise HTTPException(404)
    c = construir(p)
    datos = {"evento": c.id}
    if c.inicio:
        datos["inicio"] = c.inicio.astimezone(timezone.utc).isoformat()
    return _pagina("nba_partido.html", f"/nba/{c.slug}/", c.p, _jsonld_partido(c, seo.base_url()), datos, c=c)


@router.api_route("/nba/{slug}", methods=["GET", "HEAD"], name="nba_partido_sin_barra")
def partido_sin_barra(slug: str, request: Request):
    if slug in RESERVADOS or not nba_datos.SLUG_PARTIDO.match(slug):
        raise HTTPException(404)
    return RedirectResponse(f"{seo.base_url()}/nba/{slug}/" + (f"?{request.url.query}" if request.url.query else ""), status_code=301)
