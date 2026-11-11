"""Cliente OpenAI-compatible para APIMart (https://docs.apimart.ai/es).

Se usa desde /control/configuracion para traducir el contenido de la web a
inglés y portugués bajo demanda del administrador. Nunca expone la clave en
logs, errores ni HTML.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any
from urllib.parse import urlsplit

import httpx

from ..comercial import cifrado

DEFAULT_BASE_URL = "https://api.apimart.ai/v1"
DEFAULT_MODEL = "gpt-4o-mini"
CIPHER_CONTEXT = "web_config:apimart"
MODELOS_SUGERIDOS: tuple[str, ...] = (
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-5",
    "claude-sonnet-4.5",
    "claude-haiku-4.5",
    "gemini-2.0-flash",
)
LANG_NAMES: dict[str, str] = {
    "es": "Spanish (neutral/LatAm-Spain readable)",
    "en": "English (natural US/international)",
    "pt": "Portuguese (Brazilian Portuguese, natural)",
}

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)
_BEARER_RE = re.compile(r"sk-[A-Za-z0-9_-]{6,}")


class ApimartError(RuntimeError):
    """Error controlado al invocar la API de APIMart."""


def normalize_base_url(raw: str | None) -> str:
    url = (raw or "").strip().rstrip("/")
    if not url:
        return DEFAULT_BASE_URL
    parsed = urlsplit(url)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise ApimartError("URL base de APIMart inválida; usa https://api.apimart.ai/v1")
    if parsed.scheme == "http" and not (parsed.hostname in ("127.0.0.1", "localhost")):
        raise ApimartError("La URL de APIMart debe usar HTTPS")
    if parsed.username or parsed.password:
        raise ApimartError("La URL de APIMart no debe incluir credenciales embebidas")
    return url


def redact_secrets(text: str, key: str = "") -> str:
    cleaned = _BEARER_RE.sub("sk-***", text or "")
    if key and len(key) >= 6:
        cleaned = cleaned.replace(key, "***")
    return cleaned


def resolve_api_key(encrypted_key: str | None = "") -> tuple[str, str]:
    """Devuelve `(clave, origen)` donde `origen` es 'db', 'env' o 'none'."""
    token = (encrypted_key or "").strip()
    if token and cifrado.disponible():
        try:
            plain = cifrado.descifrar(token, CIPHER_CONTEXT).strip()
            if plain:
                return plain, "db"
        except Exception:
            pass
    for env_name in ("APIMART_API_KEY", "API_MARKET_KEY"):
        val = (os.getenv(env_name) or "").strip()
        if val:
            return val, "env"
    return "", "none"


def encrypt_api_key(plain: str) -> str:
    value = (plain or "").strip()
    if not value:
        return ""
    if not cifrado.disponible():
        raise ApimartError(
            "QF_SECRETS_KEY no está configurada en el servidor; define APIMART_API_KEY en el entorno o configura QF_SECRETS_KEY."
        )
    return cifrado.cifrar(value, CIPHER_CONTEXT)


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = (raw_text or "").strip()
    match = _FENCE_RE.match(text)
    if match:
        text = match.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise ApimartError("APIMart no devolvió un JSON válido.") from None
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ApimartError(f"JSON inválido en respuesta de APIMart: {exc}") from None
    if not isinstance(data, dict):
        raise ApimartError("La respuesta JSON de APIMart no es un objeto.")
    return data


def _chat_completion(
    *,
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    expect_json: bool = False,
    max_tokens: int | None = None,
    timeout: float = 45.0,
) -> dict[str, Any]:
    if not api_key:
        raise ApimartError("Falta la clave API de APIMart. Guárdala en Configuración o en APIMART_API_KEY.")
    endpoint = f"{normalize_base_url(base_url)}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": (model or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if expect_json:
        payload["response_format"] = {"type": "json_object"}

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(endpoint, headers=headers, json=payload)
            if resp.status_code == 400 and expect_json and "response_format" in (resp.text or "").lower():
                payload.pop("response_format", None)
                resp = client.post(endpoint, headers=headers, json=payload)
    except httpx.TimeoutException:
        raise ApimartError("Tiempo de espera agotado al conectar con APIMart.") from None
    except httpx.HTTPError as exc:
        raise ApimartError(f"Error de red al conectar con APIMart: {redact_secrets(str(exc), api_key)}") from None

    if resp.status_code in (401, 403):
        raise ApimartError("Clave API de APIMart rechazada (HTTP 401/403).")
    if resp.status_code >= 400:
        detail = ""
        try:
            err_json = resp.json()
            detail = str((err_json.get("error") or {}).get("message") or err_json.get("message") or "")
        except Exception:
            detail = (resp.text or "")[:200]
        detail = redact_secrets(detail, api_key)
        raise ApimartError(f"APIMart devolvió HTTP {resp.status_code}: {detail or 'error sin detalle'}")

    try:
        data = resp.json()
    except Exception:
        raise ApimartError("APIMart devolvió una respuesta que no es JSON.") from None

    choices = data.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise ApimartError("APIMart no devolvió choices en la respuesta.")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ApimartError("APIMart devolvió contenido vacío.")
    return {
        "content": content,
        "model": str(data.get("model") or payload["model"]),
        "usage": data.get("usage") or {},
    }


def test_connection(*, api_key: str, base_url: str, model: str) -> dict[str, Any]:
    started = time.monotonic()
    res = _chat_completion(
        api_key=api_key,
        base_url=base_url,
        model=model,
        messages=[
            {"role": "system", "content": "You are a connectivity probe. Reply only with OK."},
            {"role": "user", "content": "Reply with OK"},
        ],
        expect_json=False,
        max_tokens=16,
        timeout=20.0,
    )
    elapsed_ms = round((time.monotonic() - started) * 1000)
    return {
        "ok": True,
        "model": res["model"],
        "latency_ms": elapsed_ms,
        "preview": res["content"].strip()[:40],
    }


def translate_page(
    *,
    source: dict[str, Any],
    target_lang: str,
    brand_name: str,
    legal_name: str,
    support_email: str,
    api_key: str,
    base_url: str,
    model: str,
) -> dict[str, Any]:
    if target_lang not in ("en", "pt"):
        raise ApimartError(f"Idioma destino no soportado: {target_lang}")
    lang_label = LANG_NAMES[target_lang]
    kind = str(source.get("kind") or "pagina")

    if kind == "ui":
        try:
            ui_source = json.loads(source.get("body_html") or "{}")
            if not isinstance(ui_source, dict):
                ui_source = {}
        except json.JSONDecodeError:
            ui_source = {}
        system_msg = (
            f"You are a professional web product localizer translating QuantFut UI copy from Spanish into {lang_label}. "
            "Preserve exact JSON keys, placeholder tokens like {year}, {league}, {count}, URLs, brand name, "
            "legal name, support email, and '+18' marker. Keep concise, idiomatic betting-analytics terminology "
            "without gambling hype or profit guarantees. Return strictly a single JSON object."
        )
        user_payload = {
            "brand_name": brand_name,
            "legal_name": legal_name,
            "support_email": support_email,
            "target_lang": target_lang,
            "fields": {
                "title": source.get("title") or "",
                "description": source.get("description") or "",
                "h1": source.get("h1") or "",
                "migas": source.get("migas") or "",
                "ui": ui_source,
            },
        }
        res = _chat_completion(
            api_key=api_key,
            base_url=base_url,
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {
                    "role": "user",
                    "content": (
                        "Translate every string inside `fields` (preserving keys inside `ui` verbatim) "
                        "and return a JSON object with keys `title`, `description`, `h1`, `migas`, `ui`:\n"
                        + json.dumps(user_payload, ensure_ascii=False)
                    ),
                },
            ],
            expect_json=True,
        )
        parsed = _extract_json_object(res["content"])
        raw_ui = parsed.get("ui") if isinstance(parsed.get("ui"), dict) else {}
        merged_ui = {k: str(raw_ui.get(k) or v) for k, v in ui_source.items()}
        return {
            "title": str(parsed.get("title") or source.get("title") or "").strip(),
            "description": str(parsed.get("description") or source.get("description") or "").strip(),
            "h1": str(parsed.get("h1") or source.get("h1") or "").strip(),
            "migas": str(parsed.get("migas") or source.get("migas") or "").strip(),
            "body_html": json.dumps(merged_ui, ensure_ascii=False, indent=2),
            "revision_date": str(source.get("revision_date") or "").strip(),
            "model": res["model"],
            "usage": res["usage"],
        }

    system_msg = (
        f"You are an expert YMYL statistical-sports web translator translating from Spanish into {lang_label}. "
        f"Preserve the brand '{brand_name}', legal entity '{legal_name}', email '{support_email}', numeric figures, "
        "'+18', URLs, and existing HTML tags/classes/attributes inside `body_html` verbatim. Do not add <script>, "
        "<iframe>, inline event handlers, or unrequested claims or profit promises. Translate only human-readable "
        "text in `title`, `description`, `h1`, `migas`, `revision_date`, and inside `body_html`. "
        "Return strictly a JSON object with keys `title`, `description`, `h1`, `migas`, `revision_date`, `body_html`."
    )
    user_payload = {
        "page_key": source.get("page_key") or "",
        "kind": kind,
        "target_lang": target_lang,
        "title": source.get("title") or "",
        "description": source.get("description") or "",
        "h1": source.get("h1") or "",
        "migas": source.get("migas") or "",
        "revision_date": source.get("revision_date") or "",
        "body_html": source.get("body_html") or "",
    }
    res = _chat_completion(
        api_key=api_key,
        base_url=base_url,
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        expect_json=True,
    )
    parsed = _extract_json_object(res["content"])
    title = str(parsed.get("title") or source.get("title") or "").strip()
    description = str(parsed.get("description") or source.get("description") or "").strip()
    h1 = str(parsed.get("h1") or source.get("h1") or "").strip()
    migas = str(parsed.get("migas") or source.get("migas") or "").strip()
    revision_date = str(parsed.get("revision_date") or source.get("revision_date") or "").strip()
    body_html = str(parsed.get("body_html") or "").strip()
    if source.get("body_html") and not body_html:
        raise ApimartError("La traducción devolvió `body_html` vacío.")
    return {
        "title": title,
        "description": description,
        "h1": h1,
        "migas": migas,
        "body_html": body_html,
        "revision_date": revision_date,
        "model": res["model"],
        "usage": res["usage"],
    }
