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

from . import fichas, idiomas, nba_datos, paginas, seo
from .nba_datos import NbaNoDisponible

log = logging.getLogger("qf.calibracion")
router = APIRouter(include_in_schema=False)
_env = Environment(loader=FileSystemLoader(str(Path(__file__).with_name("paginas"))),
                   autoescape=select_autoescape(["html"]), trim_blocks=True, lstrip_blocks=True)

RUTA = "/calibracion/"
RUTAS = {"es": RUTA, "en": "/en/calibration/", "pt": "/pt/calibracao/"}
HISTORIAL = 4          # ejecuciones de fútbol que se muestran

for _cod, _ruta in RUTAS.items():
    idiomas.registrar("calibracion", _cod, _ruta)


# --- formato (todo número visible sale de estas funciones) -----------------------------------------

def _num(x: float, dec: int, idioma: str = "es") -> str:
    s = f"{x:.{dec}f}"
    return s if idioma == "en" else s.replace(".", ",")


def n3(x: float, idioma: str = "es") -> str:
    return _num(x, 3, idioma)


def n4(x: float, idioma: str = "es") -> str:
    return _num(x, 4, idioma)


def pct(x: float, dec: int = 1, idioma: str = "es") -> str:
    s = f"{x * 100:.{dec}f}"
    if idioma == "en":
        return f"{s}%"
    if idioma == "pt":
        return f"{s.replace('.', ',')}%"
    return f"{s.replace('.', ',')} %"


def entero(x: int, idioma: str = "es") -> str:
    s = f"{int(x):,}"
    return s if idioma == "en" else s.replace(",", ".")


def _fecha_tabla(d: date | None, idioma: str = "es") -> str:
    if not d:
        return "—"
    if idioma == "en":
        return f"{paginas.MONTHS_EN[d.month - 1][:3]} {d.day}, {d.year}"
    return d.strftime("%d/%m/%Y")


def _rango(texto: str, idioma: str = "es") -> str:
    return texto if idioma == "en" else texto.replace(".", ",")


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


_TEXTOS = {
    "es": {
        "slug": "calibracion",
        "plantilla": "calibracion.html",
        "titulo": "Calibración: ¿se cumplen nuestras probabilidades?",
        "migas": "Calibración",
        "inicio": "Inicio",
        "descripcion": ("Mediciones públicas de si las probabilidades de QuantFut se cumplen: gráficos de fiabilidad de fútbol y NBA, "
                        "comparación con el mercado y el estado de la evidencia, sin maquillaje."),
        "futbol": "Fútbol",
        "nba": "NBA",
        "svg_futbol": ("Fiabilidad del 1X2 de fútbol",
                       "Probabilidad predicha frente a frecuencia observada por tramos; la diagonal es la calibración perfecta."),
        "svg_nba": ("Fiabilidad del ganador de NBA desde el sellado",
                    "Probabilidad predicha frente a frecuencia observada por tramos; la diagonal es la calibración perfecta."),
        "eje_x": "Probabilidad predicha",
        "eje_y": "Frecuencia observada",
        "no_disp": "Las mediciones de calibración no están disponibles en este momento.",
        "evidencia": {},
        "paginas": paginas.PAGINAS,
    },
    "en": {
        "slug": "en/calibration",
        "plantilla": "en_calibracion.html",
        "titulo": "Calibration: do our probabilities hold up?",
        "migas": "Calibration",
        "inicio": "QuantFut",
        "descripcion": ("Public checks on whether QuantFut's probabilities come true: football and NBA reliability charts, "
                        "market comparison and evidence status."),
        "futbol": "Football",
        "nba": "NBA",
        "svg_futbol": ("Football 1X2 reliability",
                       "Predicted probability against observed frequency by bin; the dashed diagonal is perfect calibration."),
        "svg_nba": ("NBA winner reliability since sealing",
                    "Predicted probability against observed frequency by bin; the dashed diagonal is perfect calibration."),
        "eje_x": "Predicted probability",
        "eje_y": "Observed frequency",
        "no_disp": "Calibration measurements are not available right now.",
        "evidencia": {"descriptiva": "descriptive", "preliminar": "preliminary", "certificada": "certified", "insuficiente": "insufficient"},
        "paginas": paginas.PAGINAS_EN,
    },
    "pt": {
        "slug": "pt/calibracao",
        "plantilla": "pt_calibracao.html",
        "titulo": "Calibração: nossas probabilidades se cumprem?",
        "migas": "Calibração",
        "inicio": "QuantFut",
        "descripcion": ("Medições públicas de se as probabilidades da QuantFut se cumprem: gráficos de confiabilidade de futebol e NBA, "
                        "comparação com o mercado e evidência."),
        "futbol": "Futebol",
        "nba": "NBA",
        "svg_futbol": ("Confiabilidade do 1X2 de futebol",
                       "Probabilidade prevista frente à frequência observada por faixa; a diagonal tracejada é a calibração perfeita."),
        "svg_nba": ("Confiabilidade do vencedor da NBA desde o selo",
                    "Probabilidade prevista frente à frequência observada por faixa; a diagonal tracejada é a calibração perfeita."),
        "eje_x": "Probabilidade prevista",
        "eje_y": "Frequência observada",
        "no_disp": "As medições de calibração não estão disponíveis no momento.",
        "evidencia": {"descriptiva": "descritiva", "preliminar": "preliminar", "certificada": "certificada", "insuficiente": "insuficiente"},
        "paginas": paginas.PAGINAS_PT,
    },
}


# --- construcción --------------------------------------------------------------------------------

def _puntos_futbol(bins: list[dict], idioma: str = "es") -> list[dict]:
    filas = []
    for b in bins or []:
        pred, obs, n = _f(b.get("predicted")), _f(b.get("observed")), b.get("n")
        if pred is None or obs is None or not isinstance(n, int) or n <= 0:
            continue
        filas.append({"rango": _rango(str(b.get("bin", "")), idioma), "pred": pred, "obs": obs, "n": n, "se": _f(b.get("se")), "dentro": bool(b.get("within_2se"))})
    return filas


def _puntos_nba(bins: list[dict], idioma: str = "es") -> list[dict]:
    filas = []
    for b in bins or []:
        pred, obs, n = _f(b.get("prob_media")), _f(b.get("tasa_observada")), b.get("n")
        if pred is None or obs is None or not isinstance(n, int) or n <= 0:
            continue
        r = f"{b.get('desde')}-{b.get('hasta')}"
        filas.append({"rango": _rango(r, idioma), "pred": pred, "obs": obs, "n": n, "se": None, "dentro": None})
    return filas


def _comparar(propio: float, mercado: float) -> dict:
    """Menor es mejor en RPS y Brier. La frase sale de aquí: si el modelo mejora al mercado se dice, y si no, también."""
    d = propio - mercado
    return {"propio": propio, "mercado": mercado, "diferencia": abs(d), "mejor": "modelo" if d < 0 else "mercado" if d > 0 else "empate"}


def svg_fiabilidad(puntos: list[dict], titulo: str, descripcion: str, *, idioma: str = "es") -> str:
    """Gráfico de fiabilidad: probabilidad predicha (eje x) frente a frecuencia observada (eje y). La diagonal es la calibración perfecta.
    Con `se`, una barra de ±2 errores estándar; en ámbar los grupos que quedan fuera de ella. Tamaño del punto = número de partidos."""
    tx = _TEXTOS[idioma]
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
        tv = _rango(str(v), idioma)
        partes.append(f'<line x1="{x(v):.1f}" y1="{y(0):.1f}" x2="{x(v):.1f}" y2="{y(1):.1f}" stroke="currentColor" stroke-opacity=".12"/>'
                      f'<line x1="{x(0):.1f}" y1="{y(v):.1f}" x2="{x(1):.1f}" y2="{y(v):.1f}" stroke="currentColor" stroke-opacity=".12"/>'
                      f'<text x="{x(v):.1f}" y="{alto - m + 18}" font-size="11" text-anchor="middle" fill="currentColor" fill-opacity=".7">{tv}</text>'
                      f'<text x="{m - 8}" y="{y(v) + 4:.1f}" font-size="11" text-anchor="end" fill="currentColor" fill-opacity=".7">{tv}</text>')
    partes.append(f'<line x1="{x(0):.1f}" y1="{y(0):.1f}" x2="{x(1):.1f}" y2="{y(1):.1f}" stroke="currentColor" stroke-opacity=".55" stroke-dasharray="5 4"/>')
    for p in puntos:
        color = "#34d399" if p["dentro"] in (True, None) else "#fbbf24"
        if p["se"]:
            partes.append(f'<line x1="{x(p["pred"]):.1f}" y1="{y(p["obs"] - 2 * p["se"]):.1f}" x2="{x(p["pred"]):.1f}" y2="{y(p["obs"] + 2 * p["se"]):.1f}" stroke="{color}" stroke-width="2"/>')
        r = 3 + 8 * math.sqrt(p["n"] / mayor)
        partes.append(f'<circle cx="{x(p["pred"]):.1f}" cy="{y(p["obs"]):.1f}" r="{r:.1f}" fill="{color}" fill-opacity=".85"/>')
    partes.append(f'<text x="{ancho / 2:.0f}" y="{alto - 6}" font-size="12" text-anchor="middle" fill="currentColor">{html.escape(tx["eje_x"])}</text>'
                  f'<text x="14" y="{alto / 2:.0f}" font-size="12" text-anchor="middle" fill="currentColor" transform="rotate(-90 14 {alto / 2:.0f})">{html.escape(tx["eje_y"])}</text></svg>')
    return "".join(partes)


def construir(futbol: list[dict] | None, nba: dict | None, idioma: str = "es") -> SimpleNamespace:
    tx = _TEXTOS[idioma]
    ruta = RUTAS[idioma]
    secciones = []
    fechas = []
    # Fútbol
    runs = [r for r in (futbol or []) if _f(r.get("rps")) is not None and _f(r.get("rps_market")) is not None]
    if runs:
        r = runs[0]
        puntos = _puntos_futbol(r.get("bins"), idioma)
        desde = _fecha(r.get("window_start"))
        fin = _fecha(r.get("window_end"))
        creada = _fecha(r.get("created_at"))
        if creada:
            fechas.append(creada)
        cmp_rps = _comparar(r["rps"], r["rps_market"])
        dentro = sum(1 for p in puntos if p["dentro"])
        secciones.append(SimpleNamespace(
            id="futbol", titulo=tx["futbol"], n=entero(r["n_obs"], idioma),
            desde=desde, hasta=fin, desde_txt=_fecha_tabla(desde, idioma), hasta_txt=_fecha_tabla(fin, idioma), cmp=cmp_rps,
            rps=n4(r["rps"], idioma), rps_mercado=n4(r["rps_market"], idioma), diferencia=n4(cmp_rps["diferencia"], idioma),
            logloss=n3(_f(r.get("log_loss")) or 0.0, idioma) if _f(r.get("log_loss")) is not None else None,
            brier=n3(_f(r.get("brier")) or 0.0, idioma) if _f(r.get("brier")) is not None else None,
            puntos=[SimpleNamespace(rango=p["rango"], pred=pct(p["pred"], 1, idioma), obs=pct(p["obs"], 1, idioma),
                                    n=entero(p["n"], idioma), dentro=p["dentro"]) for p in puntos],
            n_bins=len(puntos), dentro=dentro, fuera=len(puntos) - dentro,
            svg=svg_fiabilidad(puntos, *tx["svg_futbol"], idioma=idioma) if puntos else None,
            historial=[SimpleNamespace(hasta=(h := _fecha(x.get("window_end"))), hasta_txt=_fecha_tabla(h, idioma),
                                       n=entero(x["n_obs"], idioma), rps=n4(x["rps"], idioma), rps_mercado=n4(x["rps_market"], idioma))
                       for x in runs[:HISTORIAL] if isinstance(x.get("n_obs"), int)]))
    # NBA
    if nba:
        h = (nba.get("historico") or {}).get("equipo") or {}
        n_h = h.get("n") or {}
        hist = None
        if _f((h.get("modelo") or {}).get("brier_ganador")) is not None and _f((h.get("mercado") or {}).get("brier_ganador")) is not None:
            c = _comparar(h["modelo"]["brier_ganador"], h["mercado"]["brier_ganador"])
            hist = SimpleNamespace(temporada=str((nba.get("historico") or {}).get("temporada", "")),
                                   n=entero(n_h.get("ganador") or 0, idioma) if n_h.get("ganador") else None,
                                   brier=n4(c["propio"], idioma), brier_mercado=n4(c["mercado"], idioma),
                                   diferencia=n4(c["diferencia"], idioma), cmp=c,
                                   pendiente=n3(_f(h["modelo"].get("pendiente_ganador")), idioma) if _f(h["modelo"].get("pendiente_ganador")) is not None else None)
        pro = nba.get("prospectivo") or {}
        puntos = _puntos_nba(pro.get("fiabilidad"), idioma)
        prospectivo = None
        if isinstance(pro.get("con_resultado"), int) and _f(pro.get("brier_ganador")) is not None:
            ev_raw = str(pro.get("estado_evidencia") or "descriptiva")
            ev = tx["evidencia"].get(ev_raw.lower(), ev_raw)
            prospectivo = SimpleNamespace(n=entero(pro["con_resultado"], idioma),
                                          sellados=entero(pro.get("sellados") or pro["con_resultado"], idioma),
                                          brier=n4(pro["brier_ganador"], idioma),
                                          logloss=n3(pro["logloss_ganador"], idioma) if _f(pro.get("logloss_ganador")) is not None else None,
                                          evidencia=ev, certificada=bool(pro.get("calibracion_certificada")),
                                          puntos=[SimpleNamespace(rango=p["rango"], pred=pct(p["pred"], 1, idioma),
                                                                  obs=pct(p["obs"], 1, idioma), n=entero(p["n"], idioma)) for p in puntos],
                                          svg=svg_fiabilidad(puntos, *tx["svg_nba"], idioma=idioma) if puntos else None)
        if hist or prospectivo:
            secciones.append(SimpleNamespace(id="nba", titulo=tx["nba"], hist=hist, pro=prospectivo))
    base = seo.base_url()
    actualizada = max(fechas) if fechas else None
    url = base + ruta
    p = SimpleNamespace(titulo=tx["titulo"], slug=tx["slug"], migas=tx["migas"], descripcion=tx["descripcion"])
    return SimpleNamespace(p=p, secciones=secciones, actualizada=actualizada, ruta=ruta, url=url,
                           jsonld=[{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                               {"@type": "ListItem", "position": 1, "name": tx["inicio"], "item": f"{base}/"},
                               {"@type": "ListItem", "position": 2, "name": tx["migas"], "item": url}]},
                               {"@context": "https://schema.org", "@type": "WebPage", "name": p.titulo, "url": url, "inLanguage": idioma,
                                "description": p.descripcion, "isPartOf": {"@type": "WebSite", "name": "QuantFut", "url": f"{base}/"},
                                "publisher": {"@type": "Organization", "name": "QuantFut", "legalName": "Saptain LTD"},
                                **({"dateModified": actualizada.isoformat()} if actualizada else {})}])


# --- sitemap y rutas -----------------------------------------------------------------------------

def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    mod: str | None = None
    try:
        c = construir(carga_futbol(), None)
        mod = c.actualizada.isoformat() if c.actualizada else None
    except Exception:   # base caída: la página sigue en el mapa, sin fecha
        mod = None
    return tuple((r, mod) for cod, r in RUTAS.items() if idiomas.estado(cod) == "on")


def _no_disponible(idioma: str = "es") -> HTTPException:
    return HTTPException(503, detail=_TEXTOS[idioma]["no_disp"], headers={"Retry-After": "60", "Cache-Control": "no-store"})


def _servir(idioma: str) -> HTMLResponse:
    from . import web_config

    cab_idioma = idiomas.puerta(idioma)
    futbol = None
    try:
        futbol = carga_futbol()
    except Exception as e:    # la base de fútbol caída no tumba la parte de NBA
        log.warning("calibración de fútbol no disponible (%s): %s", idioma, e)
    c = construir(futbol, carga_nba(), idioma=idioma)
    if not c.secciones:
        raise _no_disponible(idioma)
    tx = _TEXTOS[idioma]
    p_eff, entradilla_override = web_config.apply_editorial_meta(c.p, "tool:calibracion", idioma)
    ctx = web_config.base_template_ctx(lang=idioma)
    cuerpo = paginas.envolver(
        _env.get_template(tx["plantilla"]), p_eff, c.ruta, idioma, c=c, url=c.url, base=seo.base_url(),
        jsonld=web_config.apply_org_jsonld(c.jsonld, ctx["cfg"]), robots=idiomas.robots_de(idioma),
        revision_iso=c.actualizada.isoformat() if c.actualizada else None,
        revision_larga=paginas.fecha_larga(c.actualizada, idioma) if c.actualizada else None,
        entradilla_override=entradilla_override, **ctx)
    secs = ctx["cfg"].get("public_cache_seconds", 300)
    cab = {"Cache-Control": f"public, max-age={secs}", "Content-Security-Policy": paginas.CSP_SHELL, **cab_idioma}
    return HTMLResponse(cuerpo, headers=cab)


def _sin_barra(request: Request, idioma: str) -> RedirectResponse:
    if idiomas.estado(idioma) == "off":
        raise HTTPException(404)
    destino = seo.base_url() + RUTAS[idioma] + (f"?{request.url.query}" if request.url.query else "")
    return RedirectResponse(destino, status_code=301)


@router.api_route(RUTA, methods=["GET", "HEAD"], name="calibracion")
def calibracion_pagina():
    return _servir("es")


@router.api_route("/calibracion", methods=["GET", "HEAD"], name="calibracion_sin_barra")
def calibracion_sin_barra(request: Request):
    return _sin_barra(request, "es")


@router.api_route(RUTAS["en"], methods=["GET", "HEAD"], name="calibracion_en")
def calibracion_en_pagina():
    return _servir("en")


@router.api_route("/en/calibration", methods=["GET", "HEAD"], name="calibracion_en_sin_barra")
def calibracion_en_sin_barra(request: Request):
    return _sin_barra(request, "en")


@router.api_route(RUTAS["pt"], methods=["GET", "HEAD"], name="calibracion_pt")
def calibracion_pt_pagina():
    return _servir("pt")


@router.api_route("/pt/calibracao", methods=["GET", "HEAD"], name="calibracion_pt_sin_barra")
def calibracion_pt_sin_barra(request: Request):
    return _sin_barra(request, "pt")
