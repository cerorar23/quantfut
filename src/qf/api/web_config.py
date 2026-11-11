"""Configuración web editable, páginas principales multiidioma y puente con APIMart.

Almacena ajustes globales de marca, redes sociales, banners, SEO/caché, estado
de idiomas y contenidos por página/idioma en PostgreSQL (`db/110_web_config.sql`),
usando las plantillas y definiciones actuales como semilla inicial.

Nunca expone claves secretas en HTML, logs ni endpoints públicos. En entornos
sin base de datos disponible hace respaldo inmediato a los valores base sin
bloquear las pruebas ni las rutas públicas.
"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import re
import socket
import time
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from psycopg.errors import UndefinedTable
from psycopg.types.json import Jsonb

from . import apimart
from .. import db as qf_db
from ..comercial.auditoria import audit
from ..config import settings as app_settings

log = logging.getLogger("qf.web_config")
router = APIRouter(tags=["web-config"])

IDIOMAS_VALIDOS = ("es", "en", "pt")
IDIOMAS_SECUNDARIOS = ("en", "pt")
IDIOMAS_BLOQUEADOS_F7 = (
    ("fr", "Francés (F7)", "Pendiente de evaluación jurídica y de mercado."),
    ("it", "Italiano (F7)", "Pendiente de evaluación jurídica y de mercado."),
    ("de", "Alemán (F7)", "Pendiente de evaluación jurídica y de mercado."),
)
ESTADOS_IDIOMA = ("off", "preview", "on")
ROBOTS_OPTIONS = ("index,follow", "index,nofollow", "noindex,follow", "noindex,nofollow")

_TTL_SECS = 5.0
_PROBE_FAIL_TTL = 10.0
_probe_fail_until = 0.0
_cache_at = 0.0
_cache_data: dict[str, Any] | None = None

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_TAG_MAIN_RE = re.compile(r"<main\b[^>]*>(.*?)</main>", re.DOTALL | re.IGNORECASE)
_H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.DOTALL | re.IGNORECASE)
_TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)
_META_DESC_RE = re.compile(
    r'<meta\b[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_BLOCK_CONTENIDO_RE = re.compile(r"\{%\s*block\s+contenido\s*%\}(.*?)\{%\s*endblock\s*%\}", re.DOTALL)
_ENTRADILLA_RE = re.compile(r'<p\s+class=["\']entradilla["\']\s*>(.*?)</p>', re.DOTALL | re.IGNORECASE)

DEFAULT_SETTINGS: dict[str, Any] = {
    "brand_name": "QuantFut",
    "legal_name": "Saptain LTD",
    "hero_badge": "SPORTS INTELLIGENCE",
    "support_email": "admin@pronosticosdeportivos.pro",
    "disclaimer_text": (
        "QuantFut es un servicio de información estadística, no una casa de apuestas. "
        "Los pronósticos tienen fines exclusivamente informativos y de entretenimiento: "
        "una probabilidad estimada no garantiza un resultado."
    ),
    "maintenance_banner": "",
    "social_x": "",
    "social_instagram": "",
    "social_telegram": "",
    "social_facebook": "",
    "social_youtube": "",
    "social_tiktok": "",
    "default_robots": "index,follow",
    "content_signal": "search=yes, ai-input=yes, ai-train=no",
    "public_cache_seconds": 300,
    "indexnow_enabled": True,
    "lang_selector_enabled": True,
    "lang_states": {"en": "off", "pt": "off"},
    "apimart_base_url": apimart.DEFAULT_BASE_URL,
    "apimart_model": apimart.DEFAULT_MODEL,
    "translation_target_langs": ["en", "pt"],
    "updated_by": "",
    "updated_at": None,
}

SOCIAL_SPECS: tuple[dict[str, Any], ...] = (
    {"field": "social_x", "key": "x", "label": "X", "base": "https://x.com/", "hosts": ("x.com", "twitter.com"), "prefix_at": False, "placeholder": "@QuantFut o https://x.com/QuantFut"},
    {"field": "social_instagram", "key": "instagram", "label": "Instagram", "base": "https://www.instagram.com/", "hosts": ("instagram.com", "www.instagram.com"), "prefix_at": False, "placeholder": "@quantfut o https://instagram.com/quantfut"},
    {"field": "social_telegram", "key": "telegram", "label": "Telegram", "base": "https://t.me/", "hosts": ("t.me", "telegram.me"), "prefix_at": False, "placeholder": "@quantfut o https://t.me/quantfut"},
    {"field": "social_facebook", "key": "facebook", "label": "Facebook", "base": "https://www.facebook.com/", "hosts": ("facebook.com", "www.facebook.com", "fb.com"), "prefix_at": False, "placeholder": "quantfut o https://facebook.com/quantfut"},
    {"field": "social_youtube", "key": "youtube", "label": "YouTube", "base": "https://www.youtube.com/", "hosts": ("youtube.com", "www.youtube.com", "youtu.be"), "prefix_at": True, "placeholder": "@quantfut o https://youtube.com/@quantfut"},
    {"field": "social_tiktok", "key": "tiktok", "label": "TikTok", "base": "https://www.tiktok.com/", "hosts": ("tiktok.com", "www.tiktok.com"), "prefix_at": True, "placeholder": "@quantfut o https://tiktok.com/@quantfut"},
)
_SOCIAL_BY_FIELD = {s["field"]: s for s in SOCIAL_SPECS}

UI_FRONTEND_DEFAULTS: dict[str, dict[str, str]] = {
    "es": {
        "brand_tagline": "Pronósticos deportivos con cálculo estadístico y trazabilidad verificable.",
        "nav_inicio": "Inicio",
        "nav_partidos": "Partidos",
        "nav_picks": "Pronósticos",
        "nav_alta": "Alta probabilidad",
        "nav_parley": "Parley del día",
        "nav_escalera": "Reto Escalera",
        "nav_paquetes": "Paquetes",
        "nav_historial": "Historial",
        "nav_planes": "Planes",
        "footer_sports": "Pronósticos por deporte",
        "footer_info": "Información",
        "footer_metodologia": "Metodología",
        "footer_juego": "Juego responsable",
        "footer_sobre": "Sobre nosotros",
        "footer_terminos": "Términos",
        "footer_privacidad": "Privacidad",
        "footer_prefs": "Preferencias de medición",
        "footer_social": "Canales oficiales",
        "cta_partidos": "Ver partidos de hoy",
        "cta_planes": "Ver planes",
        "aviso_banner_label": "Aviso del servicio",
        "lang_es": "Español",
        "lang_en": "English",
        "lang_pt": "Português",
    },
    "en": {
        "brand_tagline": "Sports forecasts built on statistical modelling and verifiable tracking.",
        "nav_inicio": "Home",
        "nav_partidos": "Matches",
        "nav_picks": "Predictions",
        "nav_alta": "High probability",
        "nav_parley": "Parlay of the day",
        "nav_escalera": "Ladder challenge",
        "nav_paquetes": "Packages",
        "nav_historial": "History",
        "nav_planes": "Plans",
        "footer_sports": "Predictions by sport",
        "footer_info": "Information",
        "footer_metodologia": "Methodology",
        "footer_juego": "Responsible gambling",
        "footer_sobre": "About us",
        "footer_terminos": "Terms",
        "footer_privacidad": "Privacy",
        "footer_prefs": "Measurement preferences",
        "footer_social": "Official channels",
        "cta_partidos": "View today's matches",
        "cta_planes": "View plans",
        "aviso_banner_label": "Service notice",
        "lang_es": "Español",
        "lang_en": "English",
        "lang_pt": "Português",
    },
    "pt": {
        "brand_tagline": "Previsões esportivas com cálculo estatístico e rastreabilidade verificável.",
        "nav_inicio": "Início",
        "nav_partidos": "Jogos",
        "nav_picks": "Previsões",
        "nav_alta": "Alta probabilidade",
        "nav_parley": "Múltipla do dia",
        "nav_escalera": "Desafio Escada",
        "nav_paquetes": "Pacotes",
        "nav_historial": "Histórico",
        "nav_planes": "Planos",
        "footer_sports": "Previsões por esporte",
        "footer_info": "Informações",
        "footer_metodologia": "Metodologia",
        "footer_juego": "Jogo responsável",
        "footer_sobre": "Sobre nós",
        "footer_terminos": "Termos",
        "footer_privacidad": "Privacidade",
        "footer_prefs": "Preferências de medição",
        "footer_social": "Canais oficiais",
        "cta_partidos": "Ver jogos de hoje",
        "cta_planes": "Ver planos",
        "aviso_banner_label": "Aviso do serviço",
        "lang_es": "Español",
        "lang_en": "English",
        "lang_pt": "Português",
    },
}

SPA_LOCALIZED_PATHS: dict[str, dict[str, str]] = {
    "inicio": {"es": "/", "en": "/en/", "pt": "/pt/"},
    "partidos": {"es": "/partidos/", "en": "/en/matches/", "pt": "/pt/partidos/"},
    "picks": {"es": "/pronosticos/", "en": "/en/predictions/", "pt": "/pt/previsoes/"},
    "historial": {"es": "/historial/", "en": "/en/history/", "pt": "/pt/historico/"},
    "alta": {"es": "/pronosticos-alta-probabilidad/", "en": "/en/high-probability-picks/", "pt": "/pt/alta-probabilidade/"},
    "parley": {"es": "/parley-del-dia/", "en": "/en/parlay-of-the-day/", "pt": "/pt/multipla-do-dia/"},
    "escalera": {"es": "/reto-escalera/", "en": "/en/ladder-challenge/", "pt": "/pt/desafio-escada/"},
    "paquetes": {"es": "/paquetes/", "en": "/en/packages/", "pt": "/pt/pacotes/"},
    "planes": {"es": "/planes/", "en": "/en/plans/", "pt": "/pt/planos/"},
}

LEGAL_SLUGS: dict[str, dict[str, str]] = {
    "legal:terminos": {"es": "/legal/terminos", "en": "/en/legal/terms", "pt": "/pt/legal/termos"},
    "legal:privacidad": {"es": "/legal/privacidad", "en": "/en/legal/privacy", "pt": "/pt/legal/privacidade"},
    "legal:eliminar-cuenta": {"es": "/legal/eliminar-cuenta", "en": "/en/legal/delete-account", "pt": "/pt/legal/excluir-conta"},
}

KIND_LABELS: dict[str, str] = {
    "ui": "Interfaz SPA (diccionario)",
    "spa": "App principal (SPA)",
    "pagina": "Páginas de confianza",
    "legal": "Documentos legales",
    "tool": "Herramientas públicas",
    "sport": "Hubs por deporte",
}


# --- sanitización HTML ----------------------------------------------------------------------------

_DROP_TAGS = frozenset({
    "script", "style", "iframe", "object", "embed", "svg", "math",
    "form", "input", "button", "textarea", "select", "option",
    "link", "meta", "base", "noscript",
})
_ALLOWED_TAGS = frozenset({
    "p", "br", "hr", "h1", "h2", "h3", "h4", "strong", "b", "em", "i",
    "u", "s", "small", "code", "pre", "blockquote", "ul", "ol", "li",
    "a", "span", "div", "table", "thead", "tbody", "tfoot", "tr", "th",
    "td", "caption", "dl", "dt", "dd", "time", "article", "section",
})
_VOID_TAGS = frozenset({"br", "hr"})
_UNIVERSAL_ATTRS = frozenset({"class", "id", "lang", "hreflang", "aria-label", "aria-labelledby", "aria-describedby"})
_TAG_ATTRS: dict[str, frozenset[str]] = {
    "a": frozenset({"href", "rel", "target"}),
    "th": frozenset({"scope", "colspan", "rowspan"}),
    "td": frozenset({"colspan", "rowspan"}),
    "time": frozenset({"datetime"}),
}


def _safe_href(raw: str | None) -> str | None:
    href = (raw or "").strip()
    if not href:
        return None
    if href.startswith("#"):
        return href
    if href.startswith("/") and not href.startswith("//"):
        return href
    parsed = urlsplit(href)
    if parsed.scheme.lower() in ("http", "https", "mailto", "tel") and (parsed.netloc or parsed.path):
        return href
    return None


class _SafeHTMLSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._out: list[str] = []
        self._drop_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in _DROP_TAGS:
            self._drop_depth += 1
            return
        if self._drop_depth > 0 or t not in _ALLOWED_TAGS:
            return
        allowed = _UNIVERSAL_ATTRS | _TAG_ATTRS.get(t, frozenset())
        parts: list[str] = [f"<{t}"]
        has_blank = False
        has_rel = False
        for k, v in attrs:
            name = (k or "").lower().strip()
            if not name or name.startswith("on") or name not in allowed:
                continue
            val = "" if v is None else str(v)
            if t == "a" and name == "href":
                safe = _safe_href(val)
                if not safe:
                    continue
                val = safe
            elif t == "a" and name == "target":
                if val not in ("_blank", "_self"):
                    continue
                has_blank = val == "_blank"
            elif t == "a" and name == "rel":
                has_rel = True
            parts.append(f' {name}="{escape(val, quote=True)}"')
        if t == "a" and has_blank and not has_rel:
            parts.append(' rel="noopener noreferrer"')
        parts.append(">")
        self._out.append("".join(parts))

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in _DROP_TAGS:
            if self._drop_depth > 0:
                self._drop_depth -= 1
            return
        if self._drop_depth > 0 or t not in _ALLOWED_TAGS or t in _VOID_TAGS:
            return
        self._out.append(f"</{t}>")

    def handle_data(self, data: str) -> None:
        if self._drop_depth == 0:
            self._out.append(escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if self._drop_depth == 0:
            self._out.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._drop_depth == 0:
            self._out.append(f"&#{name};")

    def html(self) -> str:
        return "".join(self._out).strip()


def sanitize_html(raw: str | None) -> str:
    if not raw:
        return ""
    parser = _SafeHTMLSanitizer()
    parser.feed(str(raw))
    parser.close()
    return parser.html()


# --- redes sociales y normalización --------------------------------------------------------------

def normalize_social(field: str, raw: str | None) -> str:
    spec = _SOCIAL_BY_FIELD.get(field)
    if spec is None:
        raise ValueError(f"Red social desconocida: {field}")
    value = (raw or "").strip()
    if not value:
        return ""
    if any(ch.isspace() for ch in value):
        raise ValueError(f"{spec['label']}: no debe contener espacios.")
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"{spec['label']}: URL inválida (usa https://...).")
        host = (parsed.hostname or "").lower()
        allowed_hosts = {h.lower() for h in spec["hosts"]}
        allowed_hosts |= {f"m.{h}" for h in allowed_hosts} | {f"mobile.{h}" for h in allowed_hosts}
        if host not in allowed_hosts:
            raise ValueError(f"{spec['label']}: dominio no permitido ({host}).")
        scheme = "https" if parsed.scheme.lower() == "http" else parsed.scheme.lower()
        path = parsed.path or "/"
        query = f"?{parsed.query}" if parsed.query else ""
        return f"{scheme}://{parsed.netloc}{path}{query}"
    if ":" in value:
        raise ValueError(f"{spec['label']}: esquema o formato inválido.")
    lower = value.lower()
    for host in spec["hosts"]:
        if lower.startswith(host + "/"):
            return f"https://{value}"
    handle = value.lstrip("/")
    if not spec["prefix_at"]:
        handle = handle.lstrip("@")
    else:
        handle = handle if handle.startswith("@") else f"@{handle.lstrip('@')}"
    if not handle or handle == "@":
        return ""
    return f"{spec['base']}{handle}"


def social_links(cfg: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for spec in SOCIAL_SPECS:
        url = (cfg.get(spec["field"]) or "").strip()
        if url:
            out.append({"field": spec["field"], "key": spec["key"], "label": spec["label"], "url": url})
    return out


def social_same_as(cfg: dict[str, Any]) -> list[str]:
    return [item["url"] for item in social_links(cfg)]


def twitter_site_handle(cfg: dict[str, Any]) -> str:
    url = (cfg.get("social_x") or "").strip()
    if not url:
        return ""
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if host not in ("x.com", "www.x.com", "twitter.com", "www.twitter.com"):
        return ""
    seg = parsed.path.strip("/").split("/")[0]
    if not seg or seg in ("home", "explore", "search", "i", "intent", "share"):
        return ""
    return seg if seg.startswith("@") else f"@{seg}"


def base_template_ctx(*, lang: str = "es") -> dict[str, Any]:
    """Contexto compartido para `paginas/base*.html` y plantillas derivadas."""
    cfg = get_settings()
    return {
        "cfg": cfg,
        "brand": cfg["brand_name"],
        "legal_name": cfg["legal_name"],
        "support_email": cfg["support_email"],
        "redes": social_links(cfg),
        "twitter_site": twitter_site_handle(cfg),
        "banner": cfg["maintenance_banner"],
        "disclaimer_override": cfg["disclaimer_text"] if (
            lang == "es" and cfg["disclaimer_text"] != DEFAULT_SETTINGS["disclaimer_text"]
        ) else "",
    }


def apply_editorial_meta(page_obj: Any, page_key: str, lang: str) -> tuple[Any, str | None]:
    """Aplica título, descripción, h1, migas y entradilla editados en BD si existen."""
    from types import SimpleNamespace

    ov = get_page(page_key, lang)
    if not ov:
        return page_obj, None
    data = vars(page_obj).copy()
    if ov.get("title"):
        data["titulo"] = ov["title"]
    if ov.get("description"):
        data["descripcion"] = ov["description"]
    if ov.get("migas"):
        data["migas"] = ov["migas"]
    if ov.get("h1"):
        data["h1"] = ov["h1"]
    entradilla = ov.get("body_html") or None
    return SimpleNamespace(**data), entradilla


def apply_org_jsonld(blocks: list[dict[str, Any]], cfg: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Inyecta brand_name, legal_name, email y `sameAs` en bloques JSON-LD."""
    site = cfg or get_settings()
    same_as = social_same_as(site)

    def _patch(obj: Any) -> Any:
        if isinstance(obj, list):
            return [_patch(x) for x in obj]
        if not isinstance(obj, dict):
            return obj
        out = {k: _patch(v) for k, v in obj.items()}
        typ = out.get("@type")
        if typ == "Organization":
            out["name"] = site["brand_name"]
            out["legalName"] = site["legal_name"]
            if "email" in out:
                out["email"] = site["support_email"]
            if isinstance(out.get("contactPoint"), dict) and "email" in out["contactPoint"]:
                out["contactPoint"]["email"] = site["support_email"]
            if same_as:
                out["sameAs"] = same_as
        elif typ == "WebSite":
            out["name"] = site["brand_name"]
        return out

    return _patch(blocks)


# --- sonda de base de datos y caché --------------------------------------------------------------

def _dsn_host_port(dsn: str) -> tuple[str, int]:
    raw = (dsn or "").strip()
    if raw.startswith(("postgres://", "postgresql://")):
        parsed = urlsplit(raw)
        return parsed.hostname or "127.0.0.1", int(parsed.port or 5432)
    host_m = re.search(r"(?:^|\s)host=([^\s]+)", raw)
    port_m = re.search(r"(?:^|\s)port=(\d+)", raw)
    return (host_m.group(1) if host_m else "127.0.0.1"), (int(port_m.group(1)) if port_m else 5432)


def _db_reachable() -> bool:
    global _probe_fail_until
    if os.getenv("QF_WEB_CONFIG_DB", "1") in ("0", "false", "False"):
        return False
    if qf_db._pool is not None:
        return True
    now = time.monotonic()
    if now < _probe_fail_until:
        return False
    host, port = _dsn_host_port(app_settings.pg_dsn)
    try:
        with socket.create_connection((host, port), timeout=0.12):
            return True
    except OSError:
        _probe_fail_until = now + _PROBE_FAIL_TTL
        return False


def _cache_ttl() -> float:
    return 0.0 if os.getenv("PYTEST_CURRENT_TEST") else _TTL_SECS


def invalidar_cache() -> None:
    global _cache_at, _cache_data, _probe_fail_until
    _cache_at = 0.0
    _cache_data = None
    _probe_fail_until = 0.0


# --- catálogo inicial basado en plantillas y módulos actuales ------------------------------------

def _strip_tags_text(raw: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", raw or ""))).strip()


def _extract_block_contenido(template_file: Path) -> str:
    if not template_file.exists():
        return ""
    text = template_file.read_text(encoding="utf-8")
    match = _BLOCK_CONTENIDO_RE.search(text)
    if not match:
        return ""
    return sanitize_html(match.group(1).strip())


def _extract_entradilla(template_file: Path) -> str:
    if not template_file.exists():
        return ""
    text = template_file.read_text(encoding="utf-8")
    match = _ENTRADILLA_RE.search(text)
    if not match:
        return ""
    return sanitize_html(f'<p class="entradilla">{match.group(1).strip()}</p>')


def _extract_legal_file(html_file: Path) -> dict[str, str]:
    if not html_file.exists():
        return {"title": "", "description": "", "h1": "", "body_html": ""}
    raw = html_file.read_text(encoding="utf-8")
    title_m = _TITLE_RE.search(raw)
    desc_m = _META_DESC_RE.search(raw)
    main_m = _TAG_MAIN_RE.search(raw)
    main_inner = main_m.group(1).strip() if main_m else ""
    h1_m = _H1_RE.search(main_inner)
    h1_text = _strip_tags_text(h1_m.group(1)) if h1_m else ""
    body_without_h1 = _H1_RE.sub("", main_inner, count=1).strip()
    return {
        "title": _strip_tags_text(title_m.group(1)) if title_m else "",
        "description": unescape(desc_m.group(1)).strip() if desc_m else "",
        "h1": h1_text,
        "body_html": sanitize_html(body_without_h1),
    }


def _paragraphs_to_html(parrafos: tuple[str, ...]) -> str:
    return "\n".join(f"<p>{escape(p)}</p>" for p in parrafos if p)


def _html_to_paragraphs(body_html: str) -> list[str]:
    clean = sanitize_html(body_html)
    items = [
        _strip_tags_text(m.group(1))
        for m in re.finditer(r"<(?:p|li|h2|h3)\b[^>]*>(.*?)</(?:p|li|h2|h3)>", clean, re.DOTALL | re.IGNORECASE)
    ]
    items = [x for x in items if x]
    if not items and clean:
        txt = _strip_tags_text(clean)
        if txt:
            items = [txt]
    return items


def content_sha256(row: dict[str, Any]) -> str:
    payload = "\n".join(
        str(row.get(k) or "").strip()
        for k in ("title", "description", "h1", "migas", "body_html", "revision_date")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def catalog_order() -> list[dict[str, str]]:
    """Orden estable del catálogo editable para el panel `/control/configuracion`."""
    from . import rutas_web as _rw

    items: list[dict[str, str]] = [
        {"page_key": "ui:frontend", "kind": "ui", "label": "Textos globales y navegación (SPA)"},
    ]
    for sec in _rw.SECCIONES:
        items.append({"page_key": f"spa:{sec.ruta}", "kind": "spa", "label": f"SPA · {sec.migas} ({sec.path})"})
    items.extend([
        {"page_key": "pagina:metodologia", "kind": "pagina", "label": "Metodología (/metodologia/)"},
        {"page_key": "pagina:juego-responsable", "kind": "pagina", "label": "Juego responsable (/juego-responsable/)"},
        {"page_key": "pagina:sobre-nosotros", "kind": "pagina", "label": "Sobre nosotros (/sobre-nosotros/)"},
        {"page_key": "legal:terminos", "kind": "legal", "label": "Términos de uso (/legal/terminos)"},
        {"page_key": "legal:privacidad", "kind": "legal", "label": "Política de privacidad (/legal/privacidad)"},
        {"page_key": "legal:eliminar-cuenta", "kind": "legal", "label": "Eliminar cuenta (/legal/eliminar-cuenta)"},
        {"page_key": "tool:calibracion", "kind": "tool", "label": "Calibración (/calibracion/)"},
        {"page_key": "tool:cuota-justa", "kind": "tool", "label": "Calculadora de cuota justa (/calculadora-cuota-justa/)"},
        {"page_key": "tool:verificacion", "kind": "tool", "label": "Verificador de cadena (/verificacion/)"},
        {"page_key": "sport:futbol", "kind": "sport", "label": "Hub Fútbol (/futbol/)"},
        {"page_key": "sport:nba", "kind": "sport", "label": "Hub NBA (/nba/)"},
        {"page_key": "sport:tenis", "kind": "sport", "label": "Hub Tenis (/tenis/)"},
    ])
    return items


def catalog_route_paths() -> dict[str, dict[str, str]]:
    from . import calibracion, cuota_justa, paginas, rutas_web, verificacion

    routes: dict[str, dict[str, str]] = {
        "ui:frontend": {"es": "/", "en": "/en/", "pt": "/pt/"},
        "tool:calibracion": dict(calibracion.RUTAS),
        "tool:cuota-justa": {k: p.ruta for k, p in cuota_justa._PAGINAS.items()},
        "tool:verificacion": {k: p.ruta for k, p in verificacion._PAGINAS.items()},
        "sport:futbol": {"es": "/futbol/", "en": "/en/futbol/", "pt": "/pt/futebol/"},
        "sport:nba": {"es": "/nba/", "en": "/en/nba/", "pt": "/pt/nba/"},
        "sport:tenis": {"es": "/tenis/", "en": "/en/tenis/", "pt": "/pt/tenis/"},
    }
    routes.update({k: dict(v) for k, v in LEGAL_SLUGS.items()})
    for sec in rutas_web.SECCIONES:
        routes[f"spa:{sec.ruta}"] = dict(SPA_LOCALIZED_PATHS.get(sec.ruta, {"es": sec.path, "en": f"/en{sec.path}", "pt": f"/pt{sec.path}"}))
    slug_to_key = {
        "metodologia": "pagina:metodologia",
        "en/methodology": "pagina:metodologia",
        "pt/metodologia": "pagina:metodologia",
        "juego-responsable": "pagina:juego-responsable",
        "en/responsible-gambling": "pagina:juego-responsable",
        "pt/jogo-responsavel": "pagina:juego-responsable",
        "sobre-nosotros": "pagina:sobre-nosotros",
        "en/about": "pagina:sobre-nosotros",
        "pt/sobre-nos": "pagina:sobre-nosotros",
    }
    for p in paginas.TODAS_LAS_PAGINAS:
        pk = slug_to_key[p.slug]
        routes.setdefault(pk, {})[p.idioma] = p.ruta
    return routes


def catalog_defaults() -> dict[tuple[str, str], dict[str, Any]]:
    """Extrae la semilla inicial exacta desde las plantillas y código actuales."""
    from . import calibracion, cuota_justa, paginas, rutas_web, verificacion

    api_dir = Path(__file__).resolve().parent
    paginas_dir = api_dir / "paginas"
    legal_dir = api_dir / "legal_pages"
    routes = catalog_route_paths()
    out: dict[tuple[str, str], dict[str, Any]] = {}

    # 1. UI global de la SPA (ES, EN, PT)
    for lang in IDIOMAS_VALIDOS:
        out[("ui:frontend", lang)] = {
            "page_key": "ui:frontend",
            "lang": lang,
            "kind": "ui",
            "route_path": routes["ui:frontend"][lang],
            "title": "QuantFut UI",
            "description": "Textos globales de navegación, cabecera, pie y botones de la SPA.",
            "h1": "UI SPA",
            "migas": "UI",
            "body_html": json.dumps(UI_FRONTEND_DEFAULTS[lang], ensure_ascii=False, indent=2),
            "revision_date": "",
            "is_auto_translated": False,
            "reviewed": True,
            "source_sha256": "",
        }

    # 2. Secciones SPA (ES base desde rutas_web.SECCIONES)
    for sec in rutas_web.SECCIONES:
        pk = f"spa:{sec.ruta}"
        out[(pk, "es")] = {
            "page_key": pk,
            "lang": "es",
            "kind": "spa",
            "route_path": sec.path,
            "title": sec.titulo,
            "description": sec.descripcion,
            "h1": sec.h1,
            "migas": sec.migas,
            "body_html": _paragraphs_to_html(sec.texto),
            "revision_date": "",
            "is_auto_translated": False,
            "reviewed": True,
            "source_sha256": "",
        }

    # 3. Páginas de confianza (ES, EN, PT desde paginas.py + paginas/*.html)
    slug_to_key = {
        "metodologia": "pagina:metodologia",
        "en/methodology": "pagina:metodologia",
        "pt/metodologia": "pagina:metodologia",
        "juego-responsable": "pagina:juego-responsable",
        "en/responsible-gambling": "pagina:juego-responsable",
        "pt/jogo-responsavel": "pagina:juego-responsable",
        "sobre-nosotros": "pagina:sobre-nosotros",
        "en/about": "pagina:sobre-nosotros",
        "pt/sobre-nos": "pagina:sobre-nosotros",
    }
    for p in paginas.TODAS_LAS_PAGINAS:
        pk = slug_to_key[p.slug]
        out[(pk, p.idioma)] = {
            "page_key": pk,
            "lang": p.idioma,
            "kind": "pagina",
            "route_path": p.ruta,
            "title": p.titulo,
            "description": p.descripcion,
            "h1": p.titulo,
            "migas": p.migas,
            "body_html": _extract_block_contenido(paginas_dir / p.plantilla),
            "revision_date": p.revision.isoformat(),
            "is_auto_translated": False,
            "reviewed": True,
            "source_sha256": "",
        }

    # 4. Documentos legales (ES desde legal_pages/*.html; EN/PT pendientes de traducir con APIMart)
    legal_files = {
        "legal:terminos": "terminos.html",
        "legal:privacidad": "privacidad.html",
        "legal:eliminar-cuenta": "eliminar-cuenta.html",
    }
    for pk, fname in legal_files.items():
        parsed = _extract_legal_file(legal_dir / fname)
        out[(pk, "es")] = {
            "page_key": pk,
            "lang": "es",
            "kind": "legal",
            "route_path": routes[pk]["es"],
            "title": parsed["title"],
            "description": parsed["description"],
            "h1": parsed["h1"],
            "migas": parsed["h1"] or parsed["title"],
            "body_html": parsed["body_html"],
            "revision_date": "2026-10-16",
            "is_auto_translated": False,
            "reviewed": True,
            "source_sha256": "",
        }

    # 5. Herramientas (ES, EN, PT: metadatos y entradilla editable)
    for lang, tx in calibracion._TEXTOS.items():
        out[("tool:calibracion", lang)] = {
            "page_key": "tool:calibracion",
            "lang": lang,
            "kind": "tool",
            "route_path": calibracion.RUTAS[lang],
            "title": tx["titulo"],
            "description": tx["descripcion"],
            "h1": tx["titulo"],
            "migas": tx["migas"],
            "body_html": _extract_entradilla(paginas_dir / tx["plantilla"]),
            "revision_date": "",
            "is_auto_translated": False,
            "reviewed": True,
            "source_sha256": "",
        }

    cuota_templates = {"es": "cuota_justa.html", "en": "en_cuota_justa.html", "pt": "pt_cuota_justa.html"}
    cuota_meta = {
        "es": ("Calculadora de cuota justa: quita el margen de la casa",
               "Convierte cuotas en probabilidades sin margen (Shin, proporcional y potencia) y probabilidades en cuotas justas.",
               "Calculadora de cuota justa", "Cuota justa"),
        "en": ("Fair odds calculator: remove the bookmaker margin",
               "Convert bookmaker odds into margin-free fair probabilities (Shin, proportional, power) and fair probabilities into odds.",
               "Fair odds calculator", "Fair odds"),
        "pt": ("Calculadora de odd justa: remova a margem da casa",
               "Converta odds em probabilidades sem margem (Shin, proporcional e potência) e probabilidades em odds justas.",
               "Calculadora de odd justa", "Odd justa"),
    }
    for lang in IDIOMAS_VALIDOS:
        t, d, h1, m = cuota_meta[lang]
        out[("tool:cuota-justa", lang)] = {
            "page_key": "tool:cuota-justa",
            "lang": lang,
            "kind": "tool",
            "route_path": cuota_justa._PAGINAS[lang].ruta,
            "title": t,
            "description": d,
            "h1": h1,
            "migas": m,
            "body_html": _extract_entradilla(paginas_dir / cuota_templates[lang]),
            "revision_date": "",
            "is_auto_translated": False,
            "reviewed": True,
            "source_sha256": "",
        }

    verif_templates = {"es": "verificacion.html", "en": "en_verificacion.html", "pt": "pt_verificacao.html"}
    verif_meta = {
        "es": ("Verificador de cadena SHA-256: comprueba los lotes públicos",
               "Verifica en tu navegador o por CLI que los lotes diarios y por partido publicados en /chain están encadenados sin saltos.",
               "Verificador de cadena", "Verificación"),
        "en": ("SHA-256 chain verifier: check the public prediction ledger",
               "Verify in your browser or via CLI that every daily and match batch published at /chain chains cleanly without gaps.",
               "Chain verifier", "Verification"),
        "pt": ("Verificador de cadeia SHA-256: confira os lotes públicos",
               "Verifique no navegador ou via CLI se os lotes diários e por jogo publicados em /chain estão encadeados sem falhas.",
               "Verificador de cadeia", "Verificação"),
    }
    for lang in IDIOMAS_VALIDOS:
        t, d, h1, m = verif_meta[lang]
        out[("tool:verificacion", lang)] = {
            "page_key": "tool:verificacion",
            "lang": lang,
            "kind": "tool",
            "route_path": verificacion._PAGINAS[lang].ruta,
            "title": t,
            "description": d,
            "h1": h1,
            "migas": m,
            "body_html": _extract_entradilla(paginas_dir / verif_templates[lang]),
            "revision_date": "",
            "is_auto_translated": False,
            "reviewed": True,
            "source_sha256": "",
        }

    # 6. Hubs por deporte (ES, EN, PT)
    sport_defs = {
        "sport:futbol": {
            "es": ("Pronósticos de fútbol: probabilidades de cada partido",
                   "Probabilidad de victoria, empate y derrota de los partidos de las ligas que seguimos, generadas antes del partido y con los aciertos y los fallos a la vista.",
                   "Fútbol", "futbol_cartelera.html"),
            "en": ("Football predictions: win probabilities for every match",
                   "Home win, draw and away win probabilities for the leagues we follow, generated before each match and with the hits and misses in plain view.",
                   "Football", "en_futbol_cartelera.html"),
            "pt": ("Previsões de futebol: probabilidades de cada jogo",
                   "Probabilidades de vitória do mandante, empate e visitante nas ligas que acompanhamos, geradas antes da partida e com acertos e erros à vista.",
                   "Futebol", "pt_futbol_cartelera.html"),
        },
        "sport:nba": {
            "es": ("Pronósticos NBA: probabilidades de cada partido",
                   "Probabilidad de victoria, marcador esperado y rango de márgenes de cada partido de la NBA, sellados con hash antes del inicio. Con los aciertos y los fallos a la vista.",
                   "NBA", "nba_cartelera.html"),
            "en": ("NBA predictions: win probabilities for every game",
                   "Win probability, expected score and margin range for every NBA game, sealed with a hash before tip-off. With the hits and the misses in plain view.",
                   "NBA", "en_nba_cartelera.html"),
            "pt": ("Previsões NBA: probabilidades de cada jogo",
                   "Probabilidade de vitória, placar esperado e faixa de diferença de cada jogo da NBA, selados com hash antes do início. Com acertos e erros à vista.",
                   "NBA", "pt_nba_cartelera.html"),
        },
        "sport:tenis": {
            "es": ("Pronósticos de tenis: probabilidades de cada partido",
                   "Probabilidad de victoria y de sets y juegos de los partidos ATP y WTA, sellada antes del partido y con los aciertos y los fallos a la vista.",
                   "Tenis", "tenis_cartelera.html"),
            "en": ("Tennis predictions: win probabilities for every match",
                   "Win, set and game probabilities for ATP and WTA matches, sealed before the match and with the hits and misses in plain view.",
                   "Tennis", "en_tenis_cartelera.html"),
            "pt": ("Previsões de tênis: probabilidades de cada partida",
                   "Probabilidades de vitória, sets e games nas partidas ATP e WTA, seladas antes do início e com os acertos e erros à vista.",
                   "Tênis", "pt_tenis_cartelera.html"),
        },
    }
    for pk, langs_map in sport_defs.items():
        for lang, (t, d, m, tpl) in langs_map.items():
            out[(pk, lang)] = {
                "page_key": pk,
                "lang": lang,
                "kind": "sport",
                "route_path": routes[pk][lang],
                "title": t,
                "description": d,
                "h1": t,
                "migas": m,
                "body_html": _extract_entradilla(paginas_dir / tpl),
                "revision_date": "",
                "is_auto_translated": False,
                "reviewed": True,
                "source_sha256": "",
            }

    return out


# --- lectura / semilla en PostgreSQL ---------------------------------------------------------------

def _normalize_lang_states(raw: Any) -> dict[str, str]:
    data = dict(raw) if isinstance(raw, dict) else {}
    return {
        lang: data.get(lang) if data.get(lang) in ESTADOS_IDIOMA else "off"
        for lang in IDIOMAS_SECUNDARIOS
    }


def _clean_settings_row(row: dict[str, Any] | None) -> dict[str, Any]:
    out = copy.deepcopy(DEFAULT_SETTINGS)
    if not row:
        return out
    for k in DEFAULT_SETTINGS:
        if k not in row or row[k] is None:
            continue
        if k == "lang_states":
            out[k] = _normalize_lang_states(row[k])
        elif k == "translation_target_langs":
            vals = [x for x in (row[k] or []) if x in IDIOMAS_SECUNDARIOS]
            out[k] = vals or ["en", "pt"]
        elif k == "public_cache_seconds":
            out[k] = max(0, min(86400, int(row[k])))
        else:
            out[k] = row[k]
    return out


def ensure_seeded(c) -> None:
    """Inserta fila base de configuración y todas las páginas iniciales si aún no existen."""
    c.execute("INSERT INTO web_site_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
    for item in catalog_defaults().values():
        c.execute(
            """
            INSERT INTO web_page_contents (
                page_key, lang, kind, route_path, title, description, h1, migas,
                body_html, revision_date, is_auto_translated, reviewed, source_sha256
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (page_key, lang) DO NOTHING
            """,
            (
                item["page_key"], item["lang"], item["kind"], item["route_path"],
                item["title"], item["description"], item["h1"], item["migas"],
                item["body_html"], item["revision_date"], item["is_auto_translated"],
                item["reviewed"], item["source_sha256"],
            ),
        )


def _load_bundle_uncached(*, seed_if_empty: bool = False) -> dict[str, Any]:
    if not _db_reachable():
        return {"settings": copy.deepcopy(DEFAULT_SETTINGS), "pages": {}, "apimart_key_enc": "", "db_ok": False}
    try:
        row = qf_db.query_one(
            """
            SELECT brand_name, legal_name, hero_badge, support_email,
                   disclaimer_text, maintenance_banner,
                   social_x, social_instagram, social_telegram,
                   social_facebook, social_youtube, social_tiktok,
                   default_robots, content_signal, public_cache_seconds,
                   indexnow_enabled, lang_selector_enabled, lang_states,
                   apimart_base_url, apimart_model, apimart_key_enc,
                   translation_target_langs, updated_by, updated_at
            FROM web_site_settings WHERE id = 1
            """
        )
        page_rows = qf_db.query(
            """
            SELECT page_key, lang, kind, route_path, title, description, h1, migas,
                   body_html, revision_date, is_auto_translated, reviewed,
                   source_sha256, translation_model, updated_by, updated_at
            FROM web_page_contents
            """
        )
        if seed_if_empty and (row is None or not page_rows):
            with qf_db.conn() as c:
                ensure_seeded(c)
            return _load_bundle_uncached(seed_if_empty=False)
    except UndefinedTable:
        return {"settings": copy.deepcopy(DEFAULT_SETTINGS), "pages": {}, "apimart_key_enc": "", "db_ok": False}
    except Exception as exc:
        log.debug("Respaldo en memoria para web_config: %s", exc)
        return {"settings": copy.deepcopy(DEFAULT_SETTINGS), "pages": {}, "apimart_key_enc": "", "db_ok": False}

    enc_key = (row or {}).get("apimart_key_enc") or ""
    pages_map: dict[tuple[str, str], dict[str, Any]] = {}
    for pr in page_rows:
        item = dict(pr)
        if item.get("kind") != "ui":
            item["body_html"] = sanitize_html(item.get("body_html"))
        pages_map[(item["page_key"], item["lang"])] = item
    return {
        "settings": _clean_settings_row(row),
        "pages": pages_map,
        "apimart_key_enc": enc_key,
        "db_ok": True,
    }


def _bundle(*, use_cache: bool = True, seed_if_empty: bool = False) -> dict[str, Any]:
    global _cache_at, _cache_data
    ttl = _cache_ttl()
    now = time.monotonic()
    if use_cache and ttl > 0 and _cache_data is not None and (now - _cache_at) < ttl:
        return _cache_data
    data = _load_bundle_uncached(seed_if_empty=seed_if_empty)
    if use_cache and ttl > 0:
        _cache_data = data
        _cache_at = now
    return data


def get_settings(*, use_cache: bool = True) -> dict[str, Any]:
    return copy.deepcopy(_bundle(use_cache=use_cache)["settings"])


def get_lang_states(*, use_cache: bool = True) -> dict[str, str] | None:
    """Devuelve `{"en": ..., "pt": ...}` desde PostgreSQL si el esquema está instalado, o `None`."""
    b = _bundle(use_cache=use_cache)
    if not b["db_ok"]:
        return None
    return dict(b["settings"]["lang_states"])


def get_apimart_runtime_config() -> dict[str, Any]:
    b = _bundle(use_cache=False)
    s = b["settings"]
    enc = b.get("apimart_key_enc") or ""
    key, origin = apimart.resolve_api_key(enc)
    return {
        "base_url": s["apimart_base_url"],
        "model": s["apimart_model"],
        "target_langs": list(s["translation_target_langs"]),
        "api_key": key,
        "key_origin": origin,
    }


def get_page(page_key: str, lang: str = "es", *, use_cache: bool = True) -> dict[str, Any] | None:
    b = _bundle(use_cache=use_cache)
    item = b["pages"].get((page_key, lang))
    return dict(item) if item else None


def get_page_or_default(page_key: str, lang: str = "es", *, use_cache: bool = True) -> dict[str, Any] | None:
    item = get_page(page_key, lang, use_cache=use_cache)
    if item:
        return item
    return catalog_defaults().get((page_key, lang))


def get_ui_dict(lang: str = "es", *, use_cache: bool = True) -> dict[str, str]:
    base = dict(UI_FRONTEND_DEFAULTS.get(lang) or UI_FRONTEND_DEFAULTS["es"])
    row = get_page("ui:frontend", lang, use_cache=use_cache)
    if row and row.get("body_html"):
        try:
            loaded = json.loads(row["body_html"])
            if isinstance(loaded, dict):
                for k, v in loaded.items():
                    if isinstance(k, str) and isinstance(v, str) and v.strip():
                        base[k] = v.strip()
        except json.JSONDecodeError:
            pass
    return base


def get_spa_section_override(ruta: str, lang: str = "es") -> dict[str, Any] | None:
    row = get_page(f"spa:{ruta}", lang)
    if not row:
        return None
    return {
        **row,
        "parrafos": tuple(_html_to_paragraphs(row.get("body_html") or "")),
    }


def build_catalog_overview(*, seed_if_needed: bool = True) -> dict[str, Any]:
    b = _bundle(use_cache=False, seed_if_empty=seed_if_needed)
    defaults = catalog_defaults()
    routes = catalog_route_paths()
    pages_db = b["pages"]
    rows: list[dict[str, Any]] = []
    for entry in catalog_order():
        pk = entry["page_key"]
        es_row = pages_db.get((pk, "es")) or defaults.get((pk, "es")) or {}
        es_sha = content_sha256(es_row) if es_row else ""
        lang_cards: dict[str, dict[str, Any]] = {}
        for lang in IDIOMAS_VALIDOS:
            cur = pages_db.get((pk, lang)) or defaults.get((pk, lang))
            has_content = bool(cur and ((cur.get("title") or "").strip() or (cur.get("body_html") or "").strip()))
            stale = bool(
                lang != "es"
                and cur
                and cur.get("is_auto_translated")
                and cur.get("source_sha256")
                and es_sha
                and cur.get("source_sha256") != es_sha
            )
            lang_cards[lang] = {
                "exists": has_content,
                "stale": stale,
                "is_auto_translated": bool(cur.get("is_auto_translated")) if cur else False,
                "reviewed": bool(cur.get("reviewed", True)) if cur else False,
                "route_path": (cur or {}).get("route_path") or routes.get(pk, {}).get(lang, ""),
                "updated_at": (cur or {}).get("updated_at"),
            }
        rows.append({**entry, "kind_label": KIND_LABELS.get(entry["kind"], entry["kind"]), "langs": lang_cards})
    return {
        "db_ok": b["db_ok"],
        "settings": b["settings"],
        "key_origin": get_apimart_runtime_config()["key_origin"],
        "rows": rows,
        "social_specs": SOCIAL_SPECS,
    }


# --- mutaciones desde /control/configuracion -----------------------------------------------------

def _sync_idiomas_file(lang_states: dict[str, str]) -> None:
    from . import idiomas

    path = idiomas.archivo()
    lines = [f"{k} = {lang_states.get(k, 'off')}" for k in IDIOMAS_SECUNDARIOS]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        log.warning("No se pudo actualizar %s: %s", path, exc)
    idiomas.olvidar()


def save_general_settings(form: dict[str, Any], actor: str) -> dict[str, Any]:
    brand_name = str(form.get("brand_name") or "").strip()
    legal_name = str(form.get("legal_name") or "").strip()
    hero_badge = str(form.get("hero_badge") or "").strip()
    support_email = str(form.get("support_email") or "").strip()
    disclaimer_text = str(form.get("disclaimer_text") or "").strip()
    maintenance_banner = str(form.get("maintenance_banner") or "").strip()
    default_robots = str(form.get("default_robots") or "index,follow").strip()
    content_signal = str(form.get("content_signal") or "").strip()

    if not brand_name or not legal_name:
        raise ValueError("Marca y razón social son obligatorios.")
    if not _EMAIL_RE.match(support_email):
        raise ValueError("Correo de soporte inválido.")
    if default_robots not in ROBOTS_OPTIONS:
        raise ValueError("Directiva robots inválida.")
    try:
        cache_secs = int(str(form.get("public_cache_seconds") or "300").strip())
    except ValueError:
        raise ValueError("Segundos de caché debe ser un número entero.") from None
    if not (0 <= cache_secs <= 86400):
        raise ValueError("Segundos de caché debe estar entre 0 y 86400.")

    socials = {
        spec["field"]: normalize_social(spec["field"], form.get(spec["field"]))
        for spec in SOCIAL_SPECS
    }
    indexnow_enabled = bool(form.get("indexnow_enabled"))
    lang_selector_enabled = bool(form.get("lang_selector_enabled"))

    with qf_db.conn() as c:
        ensure_seeded(c)
        c.execute(
            """
            UPDATE web_site_settings SET
                brand_name = %s,
                legal_name = %s,
                hero_badge = %s,
                support_email = %s,
                disclaimer_text = %s,
                maintenance_banner = %s,
                social_x = %s,
                social_instagram = %s,
                social_telegram = %s,
                social_facebook = %s,
                social_youtube = %s,
                social_tiktok = %s,
                default_robots = %s,
                content_signal = %s,
                public_cache_seconds = %s,
                indexnow_enabled = %s,
                lang_selector_enabled = %s,
                updated_by = %s,
                updated_at = now()
            WHERE id = 1
            """,
            (
                brand_name, legal_name, hero_badge, support_email,
                disclaimer_text, maintenance_banner,
                socials["social_x"], socials["social_instagram"], socials["social_telegram"],
                socials["social_facebook"], socials["social_youtube"], socials["social_tiktok"],
                default_robots, content_signal or DEFAULT_SETTINGS["content_signal"],
                cache_secs, indexnow_enabled, lang_selector_enabled, actor,
            ),
        )
        audit(
            c, actor, "web_config_general_save",
            detail={"brand_name": brand_name, "public_cache_seconds": cache_secs, "default_robots": default_robots},
        )
    invalidar_cache()
    return get_settings(use_cache=False)


def save_language_states(en_state: str, pt_state: str, actor: str) -> dict[str, str]:
    states = _normalize_lang_states({"en": en_state, "pt": pt_state})
    with qf_db.conn() as c:
        ensure_seeded(c)
        c.execute(
            "UPDATE web_site_settings SET lang_states = %s, updated_by = %s, updated_at = now() WHERE id = 1",
            (Jsonb(states), actor),
        )
        audit(c, actor, "web_config_lang_states_save", detail=states)
    _sync_idiomas_file(states)
    invalidar_cache()
    return states


def save_apimart_settings(
    *,
    base_url: str,
    model: str,
    new_api_key: str,
    clear_api_key: bool,
    target_langs: list[str],
    actor: str,
) -> dict[str, Any]:
    clean_url = apimart.normalize_base_url(base_url)
    clean_model = (model or apimart.DEFAULT_MODEL).strip() or apimart.DEFAULT_MODEL
    targets = [x for x in target_langs if x in IDIOMAS_SECUNDARIOS] or ["en", "pt"]
    key_input = (new_api_key or "").strip()

    with qf_db.conn() as c:
        ensure_seeded(c)
        if clear_api_key:
            c.execute(
                """
                UPDATE web_site_settings SET
                    apimart_base_url = %s,
                    apimart_model = %s,
                    apimart_key_enc = '',
                    translation_target_langs = %s,
                    updated_by = %s,
                    updated_at = now()
                WHERE id = 1
                """,
                (clean_url, clean_model, Jsonb(targets), actor),
            )
        elif key_input:
            enc = apimart.encrypt_api_key(key_input)
            c.execute(
                """
                UPDATE web_site_settings SET
                    apimart_base_url = %s,
                    apimart_model = %s,
                    apimart_key_enc = %s,
                    translation_target_langs = %s,
                    updated_by = %s,
                    updated_at = now()
                WHERE id = 1
                """,
                (clean_url, clean_model, enc, Jsonb(targets), actor),
            )
        else:
            c.execute(
                """
                UPDATE web_site_settings SET
                    apimart_base_url = %s,
                    apimart_model = %s,
                    translation_target_langs = %s,
                    updated_by = %s,
                    updated_at = now()
                WHERE id = 1
                """,
                (clean_url, clean_model, Jsonb(targets), actor),
            )
        audit(
            c, actor, "web_config_apimart_save",
            detail={
                "base_url": clean_url,
                "model": clean_model,
                "target_langs": targets,
                "key_updated": bool(key_input),
                "key_cleared": bool(clear_api_key),
            },
        )
    invalidar_cache()
    return get_apimart_runtime_config()


def save_page(
    *,
    page_key: str,
    lang: str,
    title: str,
    description: str,
    h1: str,
    migas: str,
    body_html: str,
    revision_date: str,
    reviewed: bool,
    actor: str,
) -> dict[str, Any]:
    if lang not in IDIOMAS_VALIDOS:
        raise ValueError(f"Idioma inválido: {lang}")
    order_map = {item["page_key"]: item for item in catalog_order()}
    meta = order_map.get(page_key)
    if meta is None:
        raise ValueError(f"Página desconocida: {page_key}")
    kind = meta["kind"]
    route_path = catalog_route_paths().get(page_key, {}).get(lang, "/")

    clean_title = (title or "").strip()
    clean_desc = (description or "").strip()
    clean_h1 = (h1 or "").strip() or clean_title
    clean_migas = (migas or "").strip() or clean_h1
    clean_rev = (revision_date or "").strip()
    if kind == "ui":
        try:
            parsed = json.loads(body_html or "{}")
            if not isinstance(parsed, dict):
                raise ValueError("El diccionario UI debe ser un objeto JSON clave → texto.")
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON inválido en diccionario UI: {exc}") from None
        clean_body = json.dumps({str(k): str(v) for k, v in parsed.items()}, ensure_ascii=False, indent=2)
    else:
        clean_body = sanitize_html(body_html)

    with qf_db.conn() as c:
        ensure_seeded(c)
        c.execute(
            """
            INSERT INTO web_page_contents (
                page_key, lang, kind, route_path, title, description, h1, migas,
                body_html, revision_date, is_auto_translated, reviewed, updated_by, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s, now())
            ON CONFLICT (page_key, lang) DO UPDATE SET
                kind = EXCLUDED.kind,
                route_path = EXCLUDED.route_path,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                h1 = EXCLUDED.h1,
                migas = EXCLUDED.migas,
                body_html = EXCLUDED.body_html,
                revision_date = EXCLUDED.revision_date,
                reviewed = EXCLUDED.reviewed,
                updated_by = EXCLUDED.updated_by,
                updated_at = now()
            """,
            (
                page_key, lang, kind, route_path,
                clean_title, clean_desc, clean_h1, clean_migas,
                clean_body, clean_rev, reviewed, actor,
            ),
        )
        audit(c, actor, "web_config_page_save", detail={"page_key": page_key, "lang": lang})
    invalidar_cache()
    return get_page_or_default(page_key, lang, use_cache=False) or {}


def restore_page_default(page_key: str, lang: str, actor: str) -> dict[str, Any] | None:
    default = catalog_defaults().get((page_key, lang))
    with qf_db.conn() as c:
        ensure_seeded(c)
        if default is None:
            c.execute("DELETE FROM web_page_contents WHERE page_key = %s AND lang = %s", (page_key, lang))
        else:
            c.execute(
                """
                INSERT INTO web_page_contents (
                    page_key, lang, kind, route_path, title, description, h1, migas,
                    body_html, revision_date, is_auto_translated, reviewed, source_sha256,
                    translation_model, updated_by, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE, TRUE, '', '', %s, now())
                ON CONFLICT (page_key, lang) DO UPDATE SET
                    kind = EXCLUDED.kind,
                    route_path = EXCLUDED.route_path,
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    h1 = EXCLUDED.h1,
                    migas = EXCLUDED.migas,
                    body_html = EXCLUDED.body_html,
                    revision_date = EXCLUDED.revision_date,
                    is_auto_translated = FALSE,
                    reviewed = TRUE,
                    source_sha256 = '',
                    translation_model = '',
                    updated_by = EXCLUDED.updated_by,
                    updated_at = now()
                """,
                (
                    default["page_key"], default["lang"], default["kind"], default["route_path"],
                    default["title"], default["description"], default["h1"], default["migas"],
                    default["body_html"], default["revision_date"], actor,
                ),
            )
        audit(c, actor, "web_config_page_restore", detail={"page_key": page_key, "lang": lang})
    invalidar_cache()
    return get_page_or_default(page_key, lang, use_cache=False)


def translate_page_db(page_key: str, target_lang: str, actor: str) -> dict[str, Any]:
    if target_lang not in IDIOMAS_SECUNDARIOS:
        raise ValueError(f"Idioma destino inválido: {target_lang}")
    order_map = {item["page_key"]: item for item in catalog_order()}
    meta = order_map.get(page_key)
    if meta is None:
        raise ValueError(f"Página desconocida: {page_key}")

    with qf_db.conn() as c:
        ensure_seeded(c)
    source = get_page_or_default(page_key, "es", use_cache=False)
    if not source:
        raise ValueError(f"No hay contenido base en español para {page_key}")

    site = get_settings(use_cache=False)
    runtime = get_apimart_runtime_config()
    translated = apimart.translate_page(
        source=source,
        target_lang=target_lang,
        brand_name=site["brand_name"],
        legal_name=site["legal_name"],
        support_email=site["support_email"],
        api_key=runtime["api_key"],
        base_url=runtime["base_url"],
        model=runtime["model"],
    )

    body = translated["body_html"]
    if meta["kind"] != "ui":
        body = sanitize_html(body)
    route_path = catalog_route_paths().get(page_key, {}).get(target_lang, "/")
    src_hash = content_sha256(source)

    with qf_db.conn() as c:
        c.execute(
            """
            INSERT INTO web_page_contents (
                page_key, lang, kind, route_path, title, description, h1, migas,
                body_html, revision_date, is_auto_translated, reviewed, source_sha256,
                translation_model, updated_by, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, FALSE, %s, %s, %s, now())
            ON CONFLICT (page_key, lang) DO UPDATE SET
                kind = EXCLUDED.kind,
                route_path = EXCLUDED.route_path,
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                h1 = EXCLUDED.h1,
                migas = EXCLUDED.migas,
                body_html = EXCLUDED.body_html,
                revision_date = EXCLUDED.revision_date,
                is_auto_translated = TRUE,
                reviewed = FALSE,
                source_sha256 = EXCLUDED.source_sha256,
                translation_model = EXCLUDED.translation_model,
                updated_by = EXCLUDED.updated_by,
                updated_at = now()
            """,
            (
                page_key, target_lang, meta["kind"], route_path,
                translated["title"], translated["description"], translated["h1"], translated["migas"],
                body, translated["revision_date"], src_hash, translated["model"], actor,
            ),
        )
        audit(
            c, actor, "web_config_translate",
            detail={"page_key": page_key, "target_lang": target_lang, "model": translated["model"]},
        )
    invalidar_cache()
    return get_page_or_default(page_key, target_lang, use_cache=False) or {}


def translate_pending_batch(
    *,
    target_lang: str | None = None,
    force_all: bool = False,
    actor: str,
) -> dict[str, Any]:
    overview = build_catalog_overview(seed_if_needed=True)
    site = overview["settings"]
    targets = [target_lang] if target_lang in IDIOMAS_SECUNDARIOS else list(site["translation_target_langs"])
    done = 0
    skipped = 0
    errors: list[str] = []
    for row in overview["rows"]:
        pk = row["page_key"]
        for lang in targets:
            card = row["langs"][lang]
            needs = force_all or (not card["exists"]) or card["stale"]
            if not needs:
                skipped += 1
                continue
            try:
                translate_page_db(pk, lang, actor)
                done += 1
            except Exception as exc:
                errors.append(f"{pk} ({lang}): {exc}")
                if len(errors) == 1 and "clave api" in str(exc).lower():
                    return {"done": done, "skipped": skipped, "errors": errors}
    return {"done": done, "skipped": skipped, "errors": errors}


# --- endpoint público ligero para la SPA ----------------------------------------------------------

@router.get("/web/config")
def public_web_config():
    from . import idiomas

    cfg = get_settings()
    active_langs = {
        "es": "on",
        "en": idiomas.estado("en"),
        "pt": idiomas.estado("pt"),
    }
    exposed_langs = [lang for lang in IDIOMAS_VALIDOS if active_langs[lang] != "off"]
    ui_map: dict[str, dict[str, str]] = {}
    sections_map: dict[str, dict[str, Any]] = {}
    for lang in exposed_langs:
        ui_map[lang] = get_ui_dict(lang)
        sec_lang: dict[str, Any] = {}
        for slug, paths in SPA_LOCALIZED_PATHS.items():
            ov = get_spa_section_override(slug, lang)
            if not ov and lang == "es":
                default_sec = catalog_defaults().get((f"spa:{slug}", "es"))
                if default_sec:
                    ov = {**default_sec, "parrafos": tuple(_html_to_paragraphs(default_sec.get("body_html") or ""))}
            if ov:
                sec_lang[slug] = {
                    "path": paths[lang],
                    "title": ov["title"],
                    "description": ov["description"],
                    "h1": ov["h1"],
                    "migas": ov["migas"],
                    "paragraphs": list(ov["parrafos"]),
                }
        sections_map[lang] = sec_lang

    payload = {
        "brand_name": cfg["brand_name"],
        "legal_name": cfg["legal_name"],
        "hero_badge": cfg["hero_badge"],
        "support_email": cfg["support_email"],
        "disclaimer_text": cfg["disclaimer_text"],
        "maintenance_banner": cfg["maintenance_banner"],
        "social": [{"key": s["key"], "label": s["label"], "url": s["url"]} for s in social_links(cfg)],
        "lang_selector_enabled": bool(cfg["lang_selector_enabled"]),
        "languages": active_langs,
        "ui": ui_map,
        "sections": sections_map,
    }
    max_age = cfg["public_cache_seconds"]
    return JSONResponse(payload, headers={"Cache-Control": f"public, max-age={max_age}"})
