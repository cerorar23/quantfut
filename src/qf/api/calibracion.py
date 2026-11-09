"""`/calibracion/` (F4 de docs/plan_seo_redes_web_20261108.md): ¿las probabilidades se cumplen? Una página de transparencia generada
AUTOMÁTICAMENTE con las mediciones que la web ya publica (`/calibration` de fútbol y `/nba/v1/calibracion` de NBA), con un gráfico de
fiabilidad en SVG (sin JavaScript) y los números también en tabla. Ninguna cifra se escribe a mano: salen de los datos y la
prueba automática comprueba que todas las cifras del texto están en ellos (criterio de terminado de F4).

Honestidad por construcción: la frase sobre si el modelo supera o no al mercado se DERIVA de los datos (`rps` frente a `rps_market`,
`brier` frente al del mercado); si algún día el modelo gana, la página lo dirá, y si pierde, también. Lo que no está certificado se
llama «descriptivo».
"""
from __future__ import annotations

import html
import logging
import math
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import fichas, nba_datos, og, paginas, seo
from .nba_datos import NbaNoDisponible

log = logging.getLogger("qf.calibracion")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA = "/calibracion/"
HISTORIAL = 4          # ejecuciones de fútbol que se muestran


# --- formato (todo número visible sale de estas funciones) -----------------------------------------

def n3(x: float) -> str:
    return f"{x:.3f}".replace(".", ",")


def n4(x: float) -> str:
    return f"{x:.4f}".replace(".", ",")


def pct(x: float, dec: int = 1) -> str:
    return f"{x * 100:.{dec}f} %".replace(".", ",")


def entero(x: int) -> str:
    return f"{int(x):,}".replace(",", ".")


def _f(x) -> float | None:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def _fecha(x) -> date | None:
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    try:
        return date.fromisoformat(str(x)[:10])
    except ValueError:
        return None


# --- datos ---------------------------------------------------------------------------------------

def carga_futbol() -> list[dict]:
    """Las últimas ejecuciones de `calibration_runs` (las mismas que sirve `/calibration`)."""
    from ..db import query

    def consulta():
        return query("SELECT model_version, window_start, window_end, n_obs, rps, rps_market, log_loss, brier, bins, created_at "
                     "FROM calibration_runs ORDER BY created_at DESC LIMIT 12")
    return fichas._cacheado(("calibracion_futbol",), 300, consulta)


def carga_nba() -> dict | None:
    try:
        datos = nba_datos.calibracion()
    except NbaNoDisponible:
        return None
    return datos if isinstance(datos, dict) else None


# --- construcción --------------------------------------------------------------------------------

def _puntos_futbol(bins: list[dict]) -> list[dict]:
    filas = []
    for b in bins or []:
        pred, obs, n = _f(b.get("predicted")), _f(b.get("observed")), b.get("n")
        if pred is None or obs is None or not isinstance(n, int) or n <= 0:
            continue
        filas.append({"rango": str(b.get("bin", "")).replace(".", ","), "pred": pred, "obs": obs, "n": n, "se": _f(b.get("se")), "dentro": bool(b.get("within_2se"))})
    return filas


def _puntos_nba(bins: list[dict]) -> list[dict]:
    filas = []
    for b in bins or []:
        pred, obs, n = _f(b.get("prob_media")), _f(b.get("tasa_observada")), b.get("n")
        if pred is None or obs is None or not isinstance(n, int) or n <= 0:
            continue
        filas.append({"rango": f"{str(b.get('desde')).replace('.', ',')}-{str(b.get('hasta')).replace('.', ',')}", "pred": pred, "obs": obs, "n": n, "se": None, "dentro": None})
    return filas


def _comparar(propio: float, mercado: float) -> dict:
    """Menor es mejor en RPS y Brier. La frase sale de aquí: si el modelo mejora al mercado se dice, y si no, también."""
    d = propio - mercado
    return {"propio": propio, "mercado": mercado, "diferencia": abs(d), "mejor": "modelo" if d < 0 else "mercado" if d > 0 else "empate"}


def svg_fiabilidad(puntos: list[dict], titulo: str, descripcion: str) -> str:
    """Gráfico de fiabilidad: probabilidad predicha (eje x) frente a frecuencia observada (eje y). La diagonal es la calibración perfecta.
    Con `se`, una barra de ±2 errores estándar; en ámbar los grupos que quedan fuera de ella. Tamaño del punto = número de partidos."""
    ancho = alto = 380
    m = 46
    lado = ancho - 2 * m
    x = lambda v: m + max(0.0, min(1.0, v)) * lado    # noqa: E731
    y = lambda v: alto - m - max(0.0, min(1.0, v)) * lado   # noqa: E731
    mayor = max((p["n"] for p in puntos), default=1)
    partes = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" width="100%" role="img" aria-labelledby="t d" '
              f'preserveAspectRatio="xMidYMid meet" style="max-width:420px;color:#e6edf3"><title id="t">{html.escape(titulo)}</title>'
              f'<desc id="d">{html.escape(descripcion)}</desc>']
    for v in (0, .25, .5, .75, 1):
        partes.append(f'<line x1="{x(v):.1f}" y1="{y(0):.1f}" x2="{x(v):.1f}" y2="{y(1):.1f}" stroke="currentColor" stroke-opacity=".12"/>'
                      f'<line x1="{x(0):.1f}" y1="{y(v):.1f}" x2="{x(1):.1f}" y2="{y(v):.1f}" stroke="currentColor" stroke-opacity=".12"/>'
                      f'<text x="{x(v):.1f}" y="{alto - m + 18}" font-size="11" text-anchor="middle" fill="currentColor" fill-opacity=".7">{str(v).replace(".", ",")}</text>'
                      f'<text x="{m - 8}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end" fill="currentColor" fill-opacity=".7">{str(v).replace(".", ",")}</text>')
    partes.append(f'<line x1="{x(0):.1f}" y1="{y(0):.1f}" x2="{x(1):.1f}" y2="{y(1):.1f}" stroke="currentColor" stroke-opacity=".55" stroke-dasharray="5 4"/>')
    for p in puntos:
        color = "#34d399" if p["dentro"] in (True, None) else "#fbbf24"
        if p["se"]:
            partes.append(f'<line x1="{x(p["pred"]):.1f}" y1="{y(p["obs"] - 2 * p["se"]):.1f}" x2="{x(p["pred"]):.1f}" y2="{y(p["obs"] + 2 * p["se"]):.1f}" stroke="{color}" stroke-width="2"/>')
        r = 3 + 8 * math.sqrt(p["n"] / mayor)
        partes.append(f'<circle cx="{x(p["pred"]):.1f}" cy="{y(p["obs"]):.1f}" r="{r:.1f}" fill="{color}" fill-opacity=".85"/>')
    partes.append(f'<text x="{ancho / 2:.0f}" y="{alto - 6}" font-size="12" text-anchor="middle" fill="currentColor">Probabilidad predicha</text>'
                  f'<text x="14" y="{alto / 2:.0f}" font-size="12" text-anchor="middle" fill="currentColor" transform="rotate(-90 14 {alto / 2:.0f})">Frecuencia observada</text></svg>')
    return "".join(partes)


def construir(futbol: list[dict] | None, nba: dict | None) -> SimpleNamespace:
    secciones = []
    fechas = []
    # Fútbol
    runs = [r for r in (futbol or []) if _f(r.get("rps")) is not None and _f(r.get("rps_market")) is not None]
    if runs:
        r = runs[0]
        puntos = _puntos_futbol(r.get("bins"))
        fin = _fecha(r.get("window_end"))
        creada = _fecha(r.get("created_at"))
        if creada:
            fechas.append(creada)
        cmp_rps = _comparar(r["rps"], r["rps_market"])
        dentro = sum(1 for p in puntos if p["dentro"])
        secciones.append(SimpleNamespace(
            id="futbol", titulo="Fútbol", n=entero(r["n_obs"]), desde=_fecha(r.get("window_start")), hasta=fin, cmp=cmp_rps,
            rps=n4(r["rps"]), rps_mercado=n4(r["rps_market"]), diferencia=n4(cmp_rps["diferencia"]), logloss=n3(_f(r.get("log_loss")) or 0.0) if _f(r.get("log_loss")) is not None else None,
            brier=n3(_f(r.get("brier")) or 0.0) if _f(r.get("brier")) is not None else None,
            puntos=[SimpleNamespace(rango=p["rango"], pred=pct(p["pred"]), obs=pct(p["obs"]), n=entero(p["n"]), dentro=p["dentro"]) for p in puntos],
            n_bins=len(puntos), dentro=dentro, fuera=len(puntos) - dentro,
            svg=svg_fiabilidad(puntos, "Fiabilidad del 1X2 de fútbol", "Probabilidad predicha frente a frecuencia observada por tramos; la diagonal es la calibración perfecta.") if puntos else None,
            historial=[SimpleNamespace(hasta=_fecha(x.get("window_end")), n=entero(x["n_obs"]), rps=n4(x["rps"]), rps_mercado=n4(x["rps_market"]))
                       for x in runs[:HISTORIAL] if isinstance(x.get("n_obs"), int)]))
    # NBA
    if nba:
        h = (nba.get("historico") or {}).get("equipo") or {}
        n_h = h.get("n") or {}
        hist = None
        if _f((h.get("modelo") or {}).get("brier_ganador")) is not None and _f((h.get("mercado") or {}).get("brier_ganador")) is not None:
            c = _comparar(h["modelo"]["brier_ganador"], h["mercado"]["brier_ganador"])
            hist = SimpleNamespace(temporada=str((nba.get("historico") or {}).get("temporada", "")), n=entero(n_h.get("ganador") or 0) if n_h.get("ganador") else None,
                                   brier=n4(c["propio"]), brier_mercado=n4(c["mercado"]), diferencia=n4(c["diferencia"]), cmp=c,
                                   pendiente=n3(_f(h["modelo"].get("pendiente_ganador"))) if _f(h["modelo"].get("pendiente_ganador")) is not None else None)
        pro = nba.get("prospectivo") or {}
        puntos = _puntos_nba(pro.get("fiabilidad"))
        prospectivo = None
        if isinstance(pro.get("con_resultado"), int) and _f(pro.get("brier_ganador")) is not None:
            prospectivo = SimpleNamespace(n=entero(pro["con_resultado"]), sellados=entero(pro.get("sellados") or pro["con_resultado"]), brier=n4(pro["brier_ganador"]),
                                          logloss=n3(pro["logloss_ganador"]) if _f(pro.get("logloss_ganador")) is not None else None,
                                          evidencia=str(pro.get("estado_evidencia") or "descriptiva"), certificada=bool(pro.get("calibracion_certificada")),
                                          puntos=[SimpleNamespace(rango=p["rango"], pred=pct(p["pred"]), obs=pct(p["obs"]), n=entero(p["n"])) for p in puntos],
                                          svg=svg_fiabilidad(puntos, "Fiabilidad del ganador de NBA desde el sellado", "Probabilidad predicha frente a frecuencia observada por tramos; la diagonal es la calibración perfecta.") if puntos else None)
        if hist or prospectivo:
            secciones.append(SimpleNamespace(id="nba", titulo="NBA", hist=hist, pro=prospectivo))
    base = seo.base_url()
    actualizada = max(fechas) if fechas else None
    p = SimpleNamespace(titulo="Calibración: ¿se cumplen nuestras probabilidades?", slug="calibracion", migas="Calibración",
                        descripcion=("Mediciones públicas de si las probabilidades de QuantFut se cumplen: gráficos de fiabilidad de fútbol y NBA, "
                                     "comparación con el mercado y el estado de la evidencia, sin maquillaje."))
    return SimpleNamespace(p=p, secciones=secciones, actualizada=actualizada, url=base + RUTA,
                           jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                               {"@type": "ListItem", "position": 1, "name": "Inicio", "item": f"{base}/"},
                               {"@type": "ListItem", "position": 2, "name": "Calibración", "item": base + RUTA}]},
                               {"@context": "https://schema.org", "@type": "WebPage", "name": p.titulo, "url": base + RUTA, "inLanguage": "es",
                                "description": p.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
                                "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"},
                                **({"dateModified": actualizada.isoformat()} if actualizada else {})}])


# --- sitemap y rutas -----------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    try:
        c = construir(carga_futbol(), None)
    except Exception:   # base caída: la página sigue en el mapa, sin fecha
        return ((RUTA, None),)
    return ((RUTA, c.actualizada.isoformat() if c.actualizada else None),)


def _no_disponible() -> HTTPException:
    return HTTPException(503, detail="Las mediciones de calibración no están disponibles en este momento.",
                         headers={"Retry-After": "60", "Cache-Control": "no-store"})


@router.api_route(RUTA, methods=["GET", "HEAD"], name="calibracion")
def calibracion_pagina():
    futbol = None
    try:
        futbol = carga_futbol()
    except Exception as e:    # la base de fútbol caída no tumba la parte de NBA
        log.warning("calibración de fútbol no disponible: %s", e)
    c = construir(futbol, carga_nba())
    if not c.secciones:
        raise _no_disponible()
    cuerpo = _env.get_template("calibracion.html").render(
        p=c.p, c=c, url=c.url, base=seo.base_url(), jsonld=c.jsonld, paginas=paginas.PAGINAS, og_imagen=og.url_marca(),
        revision_iso=c.actualizada.isoformat() if c.actualizada else None,
        revision_larga=paginas.fecha_larga(c.actualizada) if c.actualizada else None)
    return HTMLResponse(cuerpo, headers={"Cache-Control": "public, max-age=300",
                                         "Content-Security-Policy": paginas.CSP})


@router.api_route("/calibracion", methods=["GET", "HEAD"], name="calibracion_sin_barra")
def calibracion_sin_barra(request: Request):
    return RedirectResponse(seo.base_url() + RUTA + (f"?{request.url.query}" if request.url.query else ""), status_code=301)
