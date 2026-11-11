from html import escape
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from . import idiomas, web_config

router = APIRouter(include_in_schema=False)
PAGES = Path(__file__).with_name("legal_pages")
_CSP = "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"

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

_LEGAL_CSS = (
    ":root{color-scheme:light;font-family:system-ui,sans-serif;color:#172329;background:#f5f7f8}"
    "body{margin:0;line-height:1.65}header,main,footer{max-width:850px;margin:auto;padding:24px}"
    "header{display:flex;gap:16px;flex-wrap:wrap;align-items:center}"
    "header>a:first-child{font-weight:800;color:#123c31;font-size:1.35rem;margin-right:auto}"
    "a{color:#086647;text-underline-offset:3px}main{background:white;border-radius:12px;overflow-wrap:anywhere}"
    "h1{font-size:clamp(1.7rem,4vw,2.3rem);line-height:1.2}h2{font-size:1.4rem;margin-top:2rem;line-height:1.3}"
    "table{border-collapse:collapse;width:100%;font-size:.95rem}th,td{border:1px solid #d9e0e3;padding:10px;text-align:left;vertical-align:top}"
    "th{background:#f1f6f3}footer{font-size:.9rem;color:#53656e}a:focus-visible{outline:3px solid #ddaa36;outline-offset:4px}"
    "@media(max-width:550px){header,main,footer{padding:18px}main{border-radius:0}th,td{padding:7px}}"
)

_LEGAL_LABELS = {
    "es": ("Documentos legales", "Términos", "Privacidad", "Eliminar cuenta", "/legal/terminos", "/legal/privacidad", "/legal/eliminar-cuenta"),
    "en": ("Legal documents", "Terms", "Privacy", "Delete account", "/en/legal/terms", "/en/legal/privacy", "/en/legal/delete-account"),
    "pt": ("Documentos legais", "Termos", "Privacidade", "Excluir conta", "/pt/legal/termos", "/pt/legal/privacidade", "/pt/legal/excluir-conta"),
}


def _render_legal(page_key: str, lang: str, route_path: str) -> HTMLResponse:
    cfg = web_config.get_settings()
    cab: dict[str, str] = {"Cache-Control": f"public, max-age={cfg['public_cache_seconds']}", "Content-Security-Policy": _CSP}
    if lang != "es":
        cab.update(idiomas.puerta(lang))
    row = web_config.get_page(page_key, lang)
    if lang != "es" and (not row or not (row.get("body_html") or "").strip()):
        es_path = next((p for k, l, p in _LEGAL_ROUTES if k == page_key and l == "es"), "/legal/terminos")
        brand = escape(cfg["brand_name"])
        email = escape(cfg["support_email"])
        title = "Legal notice" if lang == "en" else "Aviso legal"
        heading = "Translation pending" if lang == "en" else "Tradução pendente"
        msg = (
            f'This legal document has not been translated into English yet. See the <a href="{es_path}" hreflang="es">Spanish version</a>.'
            if lang == "en"
            else f'Este documento legal ainda não foi traduzido para o português. Consulte a <a href="{es_path}" hreflang="es">versão em espanhol</a>.'
        )
        body = f"<p>{msg}</p>"
        desc = title
    else:
        assert row is not None
        brand = escape(cfg["brand_name"])
        email = escape(cfg["support_email"])
        title = row.get("title") or brand
        heading = row.get("h1") or title
        desc = row.get("description") or title
        body = web_config.sanitize_html(row.get("body_html") or "")

    nav_lbl, t_lbl, p_lbl, d_lbl, t_url, p_url, d_url = _LEGAL_LABELS[lang]
    alt_links = idiomas.selector(route_path)
    alt_html = "".join(
        f' · <a href="{escape(a["ruta"])}" hreflang="{escape(a["codigo"])}" lang="{escape(a["codigo"])}">{escape(a["nombre"])}</a>'
        for a in alt_links
    )
    socials = web_config.social_links(cfg)
    social_html = "".join(
        f' · <a href="{escape(s["url"])}" rel="noopener noreferrer">{escape(s["label"])}</a>'
        for s in socials
    )
    lang_attr = "pt-BR" if lang == "pt" else lang
    banner_html = f'<p><strong>{escape(cfg["maintenance_banner"])}</strong></p>' if cfg["maintenance_banner"] else ""
    robots_meta = '<meta name="robots" content="noindex">' if (lang != "es" and idiomas.estado(lang) != "on") else ""
    home_url = "/" if lang == "es" else f"/{lang}/"
    doc = (
        f'<!doctype html><html lang="{lang_attr}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"{robots_meta}<title>{escape(title)}</title>"
        f'<meta name="description" content="{escape(desc)}">'
        f"<style>{_LEGAL_CSS}</style></head><body>"
        f'<header><a href="{home_url}">{brand}</a>'
        f'<nav aria-label="{escape(nav_lbl)}">'
        f'<a href="{t_url}">{escape(t_lbl)}</a> · <a href="{p_url}">{escape(p_lbl)}</a> · '
        f'<a href="{d_url}">{escape(d_lbl)}</a>{alt_html}</nav></header>'
        f"<main>{banner_html}<h1>{escape(heading)}</h1>{body}</main>"
        f'<footer>{escape(cfg["legal_name"])} · <a href="mailto:{email}">{email}</a>{social_html}</footer>'
        "</body></html>"
    )
    return HTMLResponse(doc, headers=cab)


def document(slug: str):
    page_key = f"legal:{slug}"
    row = web_config.get_page(page_key, "es")
    cfg = web_config.get_settings()
    if row is None and cfg == web_config.DEFAULT_SETTINGS:
        return FileResponse(
            PAGES / f"{slug}.html",
            media_type="text/html",
            headers={"Cache-Control": f"public, max-age={cfg['public_cache_seconds']}", "Content-Security-Policy": _CSP},
        )
    if row is None:
        parsed = web_config.catalog_defaults().get((page_key, "es"))
        if not parsed:
            raise HTTPException(404)
        # Fallback limpio al HTML en disco si no hay fila personalizada en BD
        return FileResponse(
            PAGES / f"{slug}.html",
            media_type="text/html",
            headers={"Cache-Control": f"public, max-age={cfg['public_cache_seconds']}", "Content-Security-Policy": _CSP},
        )
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
