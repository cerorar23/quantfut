"""Página de invitación /i/CODIGO: código en 6 idiomas, sin base de datos y compatible con la CSP."""
import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import invitacion

app = FastAPI()
app.include_router(invitacion.router)
client = TestClient(app)


def _get(code, lang=None):
    return client.get(f"/i/{code}", headers={"Accept-Language": lang} if lang else {})


def test_muestra_el_codigo_en_mayusculas_y_como_usarlo():
    r = _get("f9b9cbe3633f")
    assert r.status_code == 200
    assert 'value="F9B9CBE3633F"' in r.text and 'lang="es"' in r.text
    assert "Código de quien te invitó" in r.text and "Registrar código" in r.text
    assert "primeros 7 días" in r.text


@pytest.mark.parametrize("lang,frase", [("en", "How to use it"), ("pt", "Como usar"), ("fr", "Comment l'utiliser"),
                                        ("it", "Come usarlo"), ("de", "So funktioniert es"), ("es", "Cómo usarlo")])
def test_se_ve_en_el_idioma_del_navegador(lang, frase):
    r = _get("ABC123DEF456", f"{lang}-XX,en;q=0.5")
    assert frase.replace("'", "&#39;") in r.text or frase in r.text
    assert f'lang="{lang}"' in r.text


def test_idioma_no_soportado_cae_en_espanol():
    assert 'lang="es"' in _get("ABC123DEF456", "ja-JP").text


@pytest.mark.parametrize("code", ["abc", "x" * 40, "ab%20cd1234", "<script>alert(1)</script>", "a-b-c-d-e-f"])
def test_un_codigo_mal_formado_da_404_y_no_se_repite_en_la_pagina(code):
    r = _get(code)
    assert r.status_code == 404
    assert "alert(1)" not in r.text and 'readonly' not in r.text


def test_cabeceras_sin_cache_sin_indexar_y_con_csp():
    h = _get("ABC123DEF456").headers
    assert h["cache-control"] == "no-store" and "noindex" in h["x-robots-tag"]
    assert "script-src 'self'" in h["content-security-policy"] and h["referrer-policy"] == "no-referrer"


def test_cumple_la_csp_sin_scripts_ni_estilos_en_linea():
    html = _get("ABC123DEF456").text
    assert re.findall(r"<script[^>]*>", html) == ['<script src="/static/invitacion.js" defer>']
    assert "<script>" not in html and " style=" not in html and "onclick" not in html
    assert (invitacion.__file__.rsplit("invitacion.py", 1)[0] + "static/invitacion.js")


def test_el_boton_de_descarga_solo_sale_si_hay_enlace(monkeypatch):
    from dataclasses import replace
    assert "Descargar la app" not in _get("ABC123DEF456").text
    monkeypatch.setattr(invitacion, "settings", replace(invitacion.settings, app_download_url="https://play.example/app"))
    assert 'href="https://play.example/app"' in _get("ABC123DEF456").text


def test_los_seis_idiomas_tienen_los_mismos_textos():
    claves = set(invitacion.TEXTOS["es"])
    for lang, t in invitacion.TEXTOS.items():
        assert set(t) == claves, lang
        assert all(v.strip() for v in t.values()), lang
    for lang in ("en", "pt", "fr", "it", "de"):
        # ninguna traducción es el texto en español sin traducir
        assert all(invitacion.TEXTOS[lang][k] != invitacion.TEXTOS["es"][k]
                   for k in ("titulo", "intro", "como", "paso1", "paso3", "invalido_texto")), lang


def test_el_script_de_copiar_existe_y_no_usa_cadenas_de_la_pagina():
    from pathlib import Path
    js = Path(invitacion.__file__).parent / "static" / "invitacion.js"
    assert "data-copy" in js.read_text(encoding="utf-8")
