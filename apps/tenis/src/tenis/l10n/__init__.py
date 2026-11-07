"""Localización y glosario en 6 idiomas para tenis v2 (es, en, pt, fr, it, de)."""
from __future__ import annotations

import json
from pathlib import Path

RUTA_I18N = Path(__file__).resolve().parent / "i18n.json"

_DATOS: dict[str, dict[str, str]] | None = None


def cargar_catalogo() -> dict[str, dict[str, str]]:
    global _DATOS
    if _DATOS is None:
        _DATOS = json.loads(RUTA_I18N.read_text(encoding="utf-8"))
    return _DATOS


def texto(clave: str, idioma: str = "es") -> str:
    cat = cargar_catalogo()
    lang = idioma.lower()[:2]
    if lang not in cat:
        lang = "es"
    return cat[lang].get(clave, cat["es"].get(clave, clave))
