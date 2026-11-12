import html as html_lib
import re
from html import escape
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from . import idiomas, rutas_web, web_config

router = APIRouter(include_in_schema=False)
PAGES = Path(__file__).with_name("legal_pages")
# Las páginas legales van dentro del shell de la app (encabezado, menú y pie de fútbol, NBA y tenis), que carga su módulo y sus hojas:
# la política cerrada de antes ya no sirve; se conserva la protección contra incrustarlas en otro sitio.
_CSP = "frame-ancestors 'none'"

_LEGAL_ROUTES = (
    ("legal:terminos", "es", "/legal/terminos"),
    ("legal:terminos", "en", "/en/legal/terms"),
    ("legal:terminos", "pt", "/pt/legal/termos"),
    ("legal:privacidad", "es", "/legal/privacidad"),
    ("legal:privacidad", "en", "/en/legal/privacy"),
    ("legal:privacidad", "pt", "/pt/legal/privacidade"),
    ("legal:eliminar-cuenta", "es", "/legal/eliminar-cuenta"),
    ("legal:eliminar-cuenta", "en", "/en/legal/delete-account"),
    ("legal:eliminar-cuenta", "pt", "/pt/legal/excluir-conta"),
)
_LEGAL_BY_KEY: dict[str, dict[str, str]] = {}
_LEGAL_BY_PATH: dict[str, str] = {}
for _key, _lang, _path in _LEGAL_ROUTES:
    _LEGAL_BY_KEY.setdefault(_key, {})[_lang] = _path
    _LEGAL_BY_PATH[_path] = _key


def _traductor_legal(ruta: str) -> dict[str, str] | None:
    key = _LEGAL_BY_PATH.get(ruta)
    if not key:
        return None
    paths = _LEGAL_BY_KEY[key]
    out = {"es": paths["es"]}
    for lang in ("en", "pt"):
        p = paths.get(lang)
        if p:
            row = web_config.get_page(key, lang)
            if row and (row.get("body_html") or "").strip():
                out[lang] = p
    return out if len(out) >= 2 else None


idiomas.registrar_traductor(_traductor_legal)

_LEGAL_LABELS = {
    "es": ("Documentos legales", "Términos", "Privacidad", "Eliminar cuenta", "/legal/terminos", "/legal/privacidad", "/legal/eliminar-cuenta"),
    "en": ("Legal documents", "Terms", "Privacy", "Delete account", "/en/legal/terms", "/en/legal/privacy", "/en/legal/delete-account"),
    "pt": ("Documentos legais", "Termos", "Privacidade", "Excluir conta", "/pt/legal/termos", "/pt/legal/privacidade", "/pt/legal/excluir-conta"),
}


_MARCA = re.compile(r"\s*[·|\-–]\s*QuantFut\s*$")


def _pagina_shell(titulo: str, descripcion: str, cuerpo: str, lang: str, route_path: str) -> HTMLResponse:
    """La página legal dentro del shell de la SPA, igual que las de NBA, fútbol y tenis: el texto viaja en `data-info-contenido`
    y la app lo conserva en su <main> (frontend/app.js, ruta `info`)."""
    cfg = web_config.get_settings()
    cab: dict[str, str] = {"Cache-Control": f"public, max-age={cfg['public_cache_seconds']}", "Content-Security-Policy": _CSP}
    if lang != "es":
        cab.update(idiomas.puerta(lang))
    nav_lbl, t_lbl, p_lbl, d_lbl, t_url, p_url, d_url = _LEGAL_LABELS[lang]
    docs = (f'<nav class="qf-info-docs" aria-label="{escape(nav_lbl)}"><a href="{t_url}">{escape(t_lbl)}</a> · '
            f'<a href="{p_url}">{escape(p_lbl)}</a> · <a href="{d_url}">{escape(d_lbl)}</a></nav>')
    alt = "".join(
        f' · <a href="{escape(a["ruta"])}" hreflang="{escape(a["codigo"])}" lang="{escape(a["codigo"])}">{escape(a["nombre"])}</a>'
        for a in idiomas.selector(route_path)
    )
    principal = (f'<div data-info-contenido>{cuerpo}{docs}</div>'
                 + (f'<nav aria-label="Idioma">{alt[3:]}</nav>' if alt else ""))
    titulo = _MARCA.sub("", titulo) or cfg["brand_name"]
    html = rutas_web.render_pagina(
        titulo=titulo, descripcion=descripcion, path=route_path, ruta="info", jsonld=[], principal=principal,
        datos={"pagina": "info"}, robots=idiomas.robots_de(lang) or rutas_web.ROBOTS, lang=lang)
    return HTMLResponse(html, headers=cab)


def _render_legal(page_key: str, lang: str, route_path: str) -> HTMLResponse:
    cfg = web_config.get_settings()
    if lang != "es" and (not (row := web_config.get_page(page_key, lang)) or not (row.get("body_html") or "").strip()):
        es_path = next((p for k, l, p in _LEGAL_ROUTES if k == page_key and l == "es"), "/legal/terminos")
        title = "Legal notice" if lang == "en" else "Aviso legal"
        heading = "Translation pending" if lang == "en" else "Tradução pendente"
        msg = (
            f'This legal document has not been translated into English yet. See the <a href="{es_path}" hreflang="es">Spanish version</a>.'
            if lang == "en"
            else f'Este documento legal ainda não foi traduzido para o português. Consulte a <a href="{es_path}" hreflang="es">versão em espanhol</a>.'
        )
        body, desc = f"<p>{msg}</p>", title
    else:
        row = web_config.get_page(page_key, lang)
        assert row is not None
        title = row.get("title") or cfg["brand_name"]
        heading = row.get("h1") or title
        desc = row.get("description") or title
        body = web_config.sanitize_html(row.get("body_html") or "")
    return _pagina_shell(title, desc, f"<h1>{escape(heading)}</h1>{body}", lang, route_path)


_TITULO = re.compile(r"<title>(.*?)</title>", re.S)
_DESCRIPCION = re.compile(r'<meta name="description" content="([^"]*)"')
_MAIN = re.compile(r"<main>(.*)</main>", re.S)


def _desde_archivo(slug: str) -> HTMLResponse:
    """Texto vigente del documento, tal como está en `legal_pages/` (sin fila personalizada en la base de datos)."""
    crudo = (PAGES / f"{slug}.html").read_text(encoding="utf-8")
    titulo, desc, main = _TITULO.search(crudo), _DESCRIPCION.search(crudo), _MAIN.search(crudo)
    if not (titulo and desc and main):
        raise HTTPException(500, detail="documento legal con formato inesperado")
    return _pagina_shell(html_lib.unescape(titulo.group(1)), html_lib.unescape(desc.group(1)), main.group(1), "es", f"/legal/{slug}")


def document(slug: str):
    page_key = f"legal:{slug}"
    if web_config.get_page(page_key, "es") is None:
        return _desde_archivo(slug)
    return _render_legal(page_key, "es", f"/legal/{slug}")


def entradas_sitemap() -> tuple[tuple[str, str | None], ...]:
    out: list[tuple[str, str | None]] = []
    for _key, lang, path in _LEGAL_ROUTES:
        if lang != "es" and idiomas.estado(lang) == "on":
            row = web_config.get_page(_key, lang)
            if row and (row.get("body_html") or "").strip():
                out.append((path, row.get("revision_date") or None))
    return tuple(out)


@router.get("/legal/terminos")
def terms():
    return document("terminos")


@router.get("/legal/privacidad")
def privacy():
    return document("privacidad")


@router.get("/legal/eliminar-cuenta")
def delete_account():
    return document("eliminar-cuenta")


@router.api_route("/en/legal/terms", methods=["GET", "HEAD"])
def terms_en():
    return _render_legal("legal:terminos", "en", "/en/legal/terms")


@router.api_route("/en/legal/privacy", methods=["GET", "HEAD"])
def privacy_en():
    return _render_legal("legal:privacidad", "en", "/en/legal/privacy")


@router.api_route("/en/legal/delete-account", methods=["GET", "HEAD"])
def delete_account_en():
    return _render_legal("legal:eliminar-cuenta", "en", "/en/legal/delete-account")


@router.api_route("/pt/legal/termos", methods=["GET", "HEAD"])
def terms_pt():
    return _render_legal("legal:terminos", "pt", "/pt/legal/termos")


@router.api_route("/pt/legal/privacidade", methods=["GET", "HEAD"])
def privacy_pt():
    return _render_legal("legal:privacidad", "pt", "/pt/legal/privacidade")


@router.api_route("/pt/legal/excluir-conta", methods=["GET", "HEAD"])
def delete_account_pt():
    return _render_legal("legal:eliminar-cuenta", "pt", "/pt/legal/excluir-conta")
