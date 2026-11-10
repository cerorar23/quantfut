"""Tarjetas para redes sociales (F2.3 de docs/plan_seo_redes_web_20261108.md): la imagen `og:image` de cada página.

Se generan BAJO DEMANDA la primera vez que un rastreador (Facebook, WhatsApp, X, Telegram, LinkedIn…) pide la imagen, y se
guardan en disco; Cloudflare las cachea por URL. La URL lleva el ESTADO (`…-previa.jpg`, `…-final.jpg`): cuando el partido
termina la página apunta a otra URL y las redes no sirven la tarjeta vieja (Facebook cachea las imágenes por URL).

Solo texto y formas: ningún escudo ni logotipo de equipos o ligas (las marcas se revisan aparte, CLAUDE.md). Una tarjeta
solo existe para un partido que ya tiene página (se resuelve con las mismas funciones que la página), y el estado pedido
tiene que ser el real: no se puede fabricar un «final» con la URL.

Pillow no viene en la imagen actual de producción. Sin él, `disponible()` es False: las páginas no declaran `og:image`
(siguen con la tarjeta `summary` de siempre) y esta ruta responde 404. Nunca se rompe una página por falta de la librería.
"""
from __future__ import annotations

import importlib.util
import io
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response

from . import seo

log = logging.getLogger("qf.og")
router = APIRouter(include_in_schema=False)

ANCHO, ALTO = 1200, 630
FUENTE = Path(__file__).with_name("fuentes") / "DejaVuSans-Bold.ttf"
FONDO, TEXTO, GRIS, VERDE, CIAN, AMBAR, LINEA = (10, 10, 15), (230, 237, 243), (154, 167, 180), (52, 211, 153), (34, 211, 238), (251, 191, 36), (42, 51, 64)
URL_MARCA = "/og/marca.jpg"
ESTADOS = ("previa", "final")
DEPORTES = {"nba": "NBA", "futbol": "FÚTBOL", "tenis": "TENIS"}
TITULOS_PILAR = {"nba": "Pronósticos de NBA", "futbol": "Pronósticos de fútbol", "tenis": "Pronósticos de tenis"}
# Inglés (F6): mismas tarjetas, textos en inglés. Las URLs van bajo /og/en/…; la página inglesa las declara como og:image.
DEPORTES_EN = {"nba": "NBA", "futbol": "FOOTBALL", "tenis": "TENNIS"}
TITULOS_PILAR_EN = {"nba": "NBA predictions", "futbol": "Football predictions", "tenis": "Tennis predictions"}
SUBTITULO_PILAR = {"es": "Probabilidad de cada partido, sellada antes de jugarse.",
                   "en": "Win probability for every match, sealed before it is played."}
TEXTOS = {
    "es": {"aviso": "+18 · Estimación estadística, no una garantía", "pronostico": "PRONÓSTICO ANTES DEL PARTIDO",
           "final": "FINAL", "sep": "  ", "acerto": "ACERTÓ", "fallo": "FALLÓ", "pct": "{n} %"},
    "en": {"aviso": "+18 · Statistical estimate, not a guarantee", "pronostico": "FORECAST BEFORE THE MATCH",
           "final": "FINAL", "sep": " ", "acerto": "HIT", "fallo": "MISS", "pct": "{n}%"},
}
VIDA_DISCO_S = 30 * 24 * 3600
_ultima_limpieza = 0.0


def disponible() -> bool:
    """¿Hay Pillow y la fuente? Se mira en cada petición: instalar o desinstalar Pillow enciende o apaga las tarjetas."""
    try:
        hay = importlib.util.find_spec("PIL") is not None
    except (ImportError, ValueError):
        hay = False
    return hay and FUENTE.is_file()


@dataclass
class Tarjeta:
    tipo: str                                   # partido | pilar | marca
    etiqueta: str = ""                          # NBA, FÚTBOL, TENIS
    titulo: str = ""                            # pilar y marca
    subtitulo: str = ""
    local: str = ""
    visitante: str = ""
    contexto: str = ""                          # competición · fecha
    barra: list[tuple[str, float]] = field(default_factory=list)   # (nombre, probabilidad) de izquierda a derecha
    estado: str = "previa"                      # previa | final
    marcador: str = ""                          # solo en final
    veredicto: str | None = None                # acerto | fallo | None
    idioma: str = "es"                         # es | en: textos de la imagen


# --- dibujo ---------------------------------------------------------------------------------------

def _fuente(tam: int):
    from PIL import ImageFont
    return ImageFont.truetype(str(FUENTE), tam)


def _ajustar(draw, texto: str, ancho: int, maximo: int, minimo: int):
    for tam in range(maximo, minimo - 1, -2):
        f = _fuente(tam)
        if draw.textlength(texto, font=f) <= ancho:
            return f, texto
    f = _fuente(minimo)
    while len(texto) > 1 and draw.textlength(texto + "…", font=f) > ancho:
        texto = texto[:-1]
    return f, texto + "…"


def _centrado(draw, xy, texto, fuente, color):
    x, y = xy
    ancho = draw.textlength(texto, font=fuente)
    draw.text((x - ancho / 2, y), texto, font=fuente, fill=color)


def renderizar(t: Tarjeta) -> bytes:
    from PIL import Image, ImageDraw
    T = TEXTOS[t.idioma]
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 14, ALTO), fill=VERDE)
    d.rectangle((14, ALTO - 6, ANCHO, ALTO), fill=LINEA)
    d.text((56, 38), "QuantFut", font=_fuente(40), fill=TEXTO)
    if t.etiqueta:
        f = _fuente(30)
        w = d.textlength(t.etiqueta, font=f)
        d.rounded_rectangle((ANCHO - 56 - w - 44, 34, ANCHO - 56, 90), radius=28, outline=VERDE, width=3)
        d.text((ANCHO - 56 - w - 22, 44), t.etiqueta, font=f, fill=VERDE)
    if t.tipo in ("pilar", "marca"):
        f, titulo = _ajustar(d, t.titulo, ANCHO - 160, 84, 48)
        d.text((56, 200), titulo, font=f, fill=TEXTO)
        f2, sub = _ajustar(d, t.subtitulo, ANCHO - 160, 40, 26)
        d.text((56, 330), sub, font=f2, fill=GRIS)
        d.rectangle((56, 410, 56 + 220, 418), fill=VERDE)
    else:
        if t.contexto:
            f, ctx = _ajustar(d, t.contexto, ANCHO - 112, 32, 22)
            d.text((56, 118), ctx, font=f, fill=GRIS)
        for nombre, y in ((t.local, 170), (t.visitante, 292)):
            f, nombre = _ajustar(d, nombre, ANCHO - 112, 84, 40)
            d.text((56, y), nombre, font=f, fill=TEXTO)
        d.text((56, 262), "vs", font=_fuente(34), fill=GRIS)
        _barra(d, t.barra, T)
        _pie_partido(d, t, T)
    d.text((56, 592), T["aviso"], font=_fuente(22), fill=GRIS)
    web = "pronosticosdeportivos.pro"
    d.text((ANCHO - 56 - d.textlength(web, font=_fuente(26)), 586), web, font=_fuente(26), fill=GRIS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=86, optimize=True)
    return buf.getvalue()


def _barra(d, barra: list[tuple[str, float]], T: dict) -> None:
    if not barra:
        return
    total = sum(p for _, p in barra) or 1.0
    x0, x1, y0, y1 = 56, ANCHO - 56, 430, 470
    colores = [VERDE, CIAN, (96, 165, 250)]
    x = x0
    for i, (_, p) in enumerate(barra):
        ancho = (x1 - x0) * p / total
        d.rectangle((round(x), y0, round(x + ancho) - (3 if i < len(barra) - 1 else 0), y1), fill=colores[i % 3])
        x += ancho
    tam = len(barra)
    for i, (nombre, p) in enumerate(barra):
        texto = f"{nombre} {T['pct'].format(n=round(p / total * 100))}"
        ff, texto = _ajustar(d, texto, (x1 - x0) // tam - 10, 30, 20)
        ancho = d.textlength(texto, font=ff)
        px = x0 if i == 0 else (x1 - ancho if i == tam - 1 else (x0 + x1) / 2 - ancho / 2)
        d.text((px, 482), texto, font=ff, fill=colores[i % 3])


def _pie_partido(d, t: Tarjeta, T: dict) -> None:
    if t.estado == "final" and t.marcador:
        texto, color = f"{T['final']}{T['sep']}{t.marcador}", TEXTO
    else:
        texto, color = T["pronostico"], VERDE
    f = _fuente(34)
    d.text((56, 532), texto, font=f, fill=color)
    if t.estado == "final" and t.veredicto:
        x = 56 + d.textlength(texto, font=f) + 34
        etiqueta, col = (T["acerto"], VERDE) if t.veredicto == "acerto" else (T["fallo"], AMBAR)
        w = d.textlength(etiqueta, font=f)
        d.rounded_rectangle((x - 16, 526, x + w + 16, 576), radius=10, outline=col, width=3)
        d.text((x, 532), etiqueta, font=f, fill=col)


# --- caché en disco -------------------------------------------------------------------------------

def _directorio() -> Path:
    for base in (os.environ.get("OG_DIR", "/srv/quantfut/artifacts/og"), str(Path(tempfile.gettempdir()) / "qf_og")):
        p = Path(base)
        try:
            p.mkdir(parents=True, exist_ok=True)
            if os.access(p, os.W_OK):
                return p
        except OSError:
            continue
    raise OSError("sin directorio de escritura para las tarjetas")


def _limpiar(d: Path) -> None:
    """Como mucho una vez por hora: borra tarjetas de más de 30 días (cada una pesa decenas de KB)."""
    global _ultima_limpieza
    ahora = time.time()
    if ahora - _ultima_limpieza < 3600:
        return
    _ultima_limpieza = ahora
    for f in d.glob("*.jpg"):
        try:
            if ahora - f.stat().st_mtime > VIDA_DISCO_S:
                f.unlink()
        except OSError:
            pass


def jpeg(clave: str, t: Tarjeta) -> bytes:
    """La tarjeta guardada de esa clave o, si no existe, la dibuja y la guarda (escritura atómica)."""
    nombre = re.sub(r"[^a-z0-9._-]+", "_", clave.lower()) + ".jpg"
    try:
        d = _directorio()
    except OSError:
        return renderizar(t)
    ruta = d / nombre
    try:
        return ruta.read_bytes()
    except OSError:
        pass
    datos = renderizar(t)
    try:
        tmp = d / f".{nombre}.{os.getpid()}.tmp"
        tmp.write_bytes(datos)
        os.replace(tmp, ruta)
        _limpiar(d)
    except OSError as e:
        log.warning("og: no se pudo guardar %s: %s", nombre, e)
    return datos


# --- URL de la imagen de cada página ---------------------------------------------------------------

def url_partido(ruta_pagina: str, estado: str) -> str | None:
    """`/nba/<slug>/` → `/og/nba/<slug>-<estado>.jpg`. None si no se pueden generar tarjetas en este servidor."""
    return f"{seo.base_url()}/og{ruta_pagina.rstrip('/')}-{estado}.jpg" if disponible() else None


def url_pilar(deporte: str) -> str | None:
    return f"{seo.base_url()}/og/{deporte}/pilar.jpg" if disponible() else None


def url_pilar_en(deporte: str) -> str | None:
    return f"{seo.base_url()}/og/en/{deporte}/pilar.jpg" if disponible() else None


def url_marca() -> str | None:
    return seo.base_url() + URL_MARCA if disponible() else None


# --- rutas ----------------------------------------------------------------------------------------

def _respuesta(datos: bytes, cache: str) -> Response:
    return Response(datos, media_type="image/jpeg", headers={"Cache-Control": cache, "Content-Length": str(len(datos))})


@router.get("/og/marca.jpg", name="og_marca")
def og_marca():
    if not disponible():
        raise HTTPException(404)
    t = Tarjeta("marca", titulo="Pronósticos de fútbol, NBA y tenis",
                subtitulo="Probabilidades selladas antes del partido, con los fallos a la vista.")
    return _respuesta(jpeg("marca-v1", t), "public, max-age=86400")


@router.get("/og/{deporte}/{resto:path}", name="og_tarjeta")
def og_tarjeta(deporte: str, resto: str):
    if deporte == "en":
        return _tarjeta_en(resto)
    if deporte not in DEPORTES or not disponible():
        raise HTTPException(404)
    if resto == "pilar.jpg":
        t = Tarjeta("pilar", etiqueta=DEPORTES[deporte], titulo=TITULOS_PILAR[deporte],
                    subtitulo="Probabilidad de cada partido, sellada antes de jugarse.")
        return _respuesta(jpeg(f"pilar-{deporte}-v1", t), "public, max-age=86400")
    m = re.fullmatch(r"(?P<ruta>[a-z0-9][a-z0-9/-]{3,160})-(?P<estado>previa|final)\.jpg", resto)
    if not m:
        raise HTTPException(404)
    partes = m["ruta"].split("/")
    from . import futbol_paginas, nba_paginas, tenis_paginas
    modulo = {"nba": nba_paginas, "futbol": futbol_paginas, "tenis": tenis_paginas}[deporte]
    if len(partes) != (1 if deporte == "nba" else 2):
        raise HTTPException(404)
    try:
        t = modulo.tarjeta_de_la_url(*partes)
    except HTTPException:
        raise
    except Exception as e:   # datos caídos: 503, nunca una imagen inventada
        log.warning("og: datos no disponibles para %s: %s", resto, e)
        raise HTTPException(503, headers={"Retry-After": "60", "Cache-Control": "no-store"})
    if t is None or t.estado != m["estado"]:
        raise HTTPException(404)          # sin página, o un estado que el partido todavía no tiene
    return _respuesta(jpeg(f"{deporte}-{'-'.join(partes)}-{t.estado}", t), "public, max-age=31536000, immutable")


def _tarjeta_en(resto: str):
    """/og/en/{deporte}/… : las mismas tarjetas con textos en inglés. Sin inglés abierto o en apagado, 404."""
    from . import idiomas
    if idiomas.estado("en") == "off" or not disponible():
        raise HTTPException(404)
    dep, _, rest = resto.partition("/")
    if dep not in DEPORTES_EN:
        raise HTTPException(404)
    if rest == "pilar.jpg":
        t = Tarjeta("pilar", etiqueta=DEPORTES_EN[dep], titulo=TITULOS_PILAR_EN[dep], subtitulo=SUBTITULO_PILAR["en"], idioma="en")
        return _respuesta(jpeg(f"en-pilar-{dep}-v1", t), "public, max-age=86400")
    m = re.fullmatch(r"(?P<ruta>[a-z0-9][a-z0-9/-]{3,160})-(?P<estado>previa|final)\.jpg", rest)
    if not m:
        raise HTTPException(404)
    partes = m["ruta"].split("/")
    if len(partes) != (1 if dep == "nba" else 2):
        raise HTTPException(404)
    from . import futbol_en, nba_en, tenis_en
    modulo = {"nba": nba_en, "futbol": futbol_en, "tenis": tenis_en}[dep]
    try:
        t = modulo.tarjeta_de_la_url(*partes)
    except HTTPException:
        raise
    except Exception as e:
        log.warning("og en: datos no disponibles para %s: %s", resto, e)
        raise HTTPException(503, headers={"Retry-After": "60", "Cache-Control": "no-store"})
    if t is None or t.estado != m["estado"]:
        raise HTTPException(404)
    return _respuesta(jpeg(f"en-{dep}-{'-'.join(partes)}-{t.estado}", t), "public, max-age=31536000, immutable")
