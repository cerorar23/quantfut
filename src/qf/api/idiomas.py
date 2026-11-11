"""Idiomas de la web pública (F6 de docs/plan_seo_redes_web_20261108.md, §9).

Reglas del plan que este módulo hace cumplir:
- El español vive en la raíz, sin prefijo; los demás idiomas con prefijo (`/en/…`).
- **Un idioma solo se abre cuando todo su contenido está en ese idioma y una persona ha revisado una muestra.** Por eso cada idioma
  tiene un ESTADO que se cambia SIN reiniciar la API (un archivo de texto en el directorio de artefactos):
    · `off`      (por defecto) las páginas de ese idioma responden 404, no están en el sitemap ni en ningún selector;
    · `preview`  responden 200 con `noindex`, sin hreflang ni sitemap ni selector en el español: para que el titular las revise en producción;
    · `on`       indexables, con hreflang recíproco (en el sitemap, con `xhtml:link`), selector de idioma y `x-default` → español.
- hreflang con un único método (el sitemap), recíproco, absoluto, autorreferente y con `x-default`. Si una página no tiene versión en un idioma,
  esa versión no se enumera.
- **Sin redirección por IP ni por `Accept-Language`**: solo un selector de idioma con enlaces normales.

Archivo de estados (`IDIOMAS_ARCHIVO`, por defecto `/srv/quantfut/artifacts/idiomas/activos.txt`), una línea por idioma:

    en=preview
    # pt=off
"""
from __future__ import annotations

import os
import time
from pathlib import Path

ESPANOL = "es"
NOMBRES = {"es": "Español", "en": "English", "pt": "Português"}
LOCALES = {"es": "es_ES", "en": "en_US", "pt": "pt_BR"}
ESTADOS = ("off", "preview", "on")
TTL_ESTADOS = 20.0

_grupos: dict[str, dict[str, str]] = {}      # grupo → {idioma: ruta}
_por_ruta: dict[str, tuple[str, str]] = {}   # ruta → (grupo, idioma)
_cache = {"t": 0.0, "datos": {}}


def archivo() -> Path:
    explicito = os.environ.get("IDIOMAS_ARCHIVO")
    if explicito:
        return Path(explicito)
    return Path(os.environ.get("IDIOMAS_DIR", "/srv/quantfut/artifacts/idiomas")) / "activos.txt"


def _leer() -> dict[str, str]:
    datos: dict[str, str] = {}
    try:
        texto = archivo().read_text(encoding="utf-8")
    except OSError:
        return datos
    for linea in texto.splitlines():
        linea = linea.split("#", 1)[0].strip()
        if "=" not in linea:
            continue
        codigo, _, valor = linea.partition("=")
        codigo, valor = codigo.strip().lower(), valor.strip().lower()
        if codigo in NOMBRES and codigo != ESPANOL and valor in ESTADOS:
            datos[codigo] = valor
    return datos


def estados() -> dict[str, str]:
    ahora = time.monotonic()
    if not _cache["datos"] or ahora - _cache["t"] > TTL_ESTADOS:
        datos = _leer() if os.environ.get("IDIOMAS_ARCHIVO") else None
        if datos is None:
            from . import web_config

            db_states = web_config.get_lang_states()
            datos = db_states if db_states is not None else _leer()
        _cache.update(t=ahora, datos={"es": "on", **datos})
    return _cache["datos"]


def olvidar() -> None:
    """Para las pruebas: vuelve a leer el archivo en la siguiente consulta."""
    _cache.update(t=0.0, datos={})


def estado(codigo: str) -> str:
    return "on" if codigo == ESPANOL else estados().get(codigo, "off")


# --- registro de páginas con versión en varios idiomas -------------------------------------------------

_traductores: list = []     # funciones ruta → {idioma: ruta} para familias dinámicas (partidos, torneos…)


def registrar(grupo: str, codigo: str, ruta: str) -> None:
    _grupos.setdefault(grupo, {})[codigo] = ruta
    _por_ruta[ruta] = (grupo, codigo)


def registrar_traductor(fn) -> None:
    """Para páginas que no se enumeran de antemano (un partido, un torneo): `fn(ruta)` devuelve `{idioma: ruta}` con TODAS las versiones
    de esa página, incluida la propia, o `None` si `ruta` no pertenece a su familia o la página no existe en todos los idiomas."""
    _traductores.append(fn)


def _equivalencias(ruta: str) -> dict[str, str] | None:
    """Todas las versiones de `ruta` en todos los idiomas: la de su grupo y las que aportan los traductores (cada familia
    de páginas aporta las suyas; con tres idiomas, el español, el inglés y el portugués se combinan aquí)."""
    salida: dict[str, str] = {}
    g = _por_ruta.get(ruta)
    if g:
        salida.update(_grupos[g[0]])
    for fn in _traductores:
        eq = fn(ruta)
        for codigo, r in (eq or {}).items():
            salida.setdefault(codigo, r)
    return salida or None


def _codigo(ruta: str, eq: dict[str, str]) -> str | None:
    return next((c for c, r in eq.items() if r == ruta), None)


def grupo_de(ruta: str) -> tuple[str, str] | None:
    return _por_ruta.get(ruta)


def versiones(ruta: str) -> list[tuple[str, str]]:
    """Las versiones INDEXABLES de la página de `ruta` (idioma, ruta): el español siempre y los idiomas en estado `on`."""
    eq = _equivalencias(ruta)
    if not eq:
        return []
    return [(c, r) for c, r in eq.items() if estado(c) == "on"]


def hreflang(ruta: str) -> list[tuple[str, str]]:
    """[(hreflang, ruta)] para el sitemap, con `x-default` → español. Vacío si la página solo existe en un idioma."""
    v = versiones(ruta)
    if len(v) < 2:
        return []
    es = dict(v).get(ESPANOL)
    return v + ([("x-default", es)] if es else [])


def selector(ruta: str) -> list[dict]:
    """Enlaces del selector de idioma para la página `ruta`: los otros idiomas que existen para ella y están en `on`.
    Una página en `preview` solo enlaza de vuelta al español (nadie llega a ella desde fuera)."""
    from . import web_config

    if not web_config.get_settings().get("lang_selector_enabled", True):
        return []
    eq = _equivalencias(ruta)
    codigo = _codigo(ruta, eq) if eq else None
    if not eq or not codigo:
        return []
    propio = estado(codigo)
    salida = []
    for c, r in eq.items():
        if c == codigo:
            continue
        if estado(c) == "on" or (propio != "on" and c == ESPANOL):
            salida.append({"codigo": c, "nombre": NOMBRES[c], "ruta": r})
    return salida


def robots_de(codigo: str) -> str | None:
    """`noindex` mientras el idioma no esté abierto; `None` = el valor normal de la plantilla."""
    return None if estado(codigo) == "on" else "noindex, follow"


def puerta(codigo: str) -> dict[str, str]:
    """Cabeceras de una página de `codigo`: 404 si el idioma está apagado; sin caché y `noindex` en vista previa."""
    from fastapi import HTTPException
    e = estado(codigo)
    if e == "off":
        raise HTTPException(404)
    if e == "preview":
        return {"Cache-Control": "no-store", "X-Robots-Tag": "noindex"}
    return {}
