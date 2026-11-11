"""Pruebas del módulo de configuración web, APIMart y panel `/control/configuracion`."""
from __future__ import annotations

import copy
import json
import os
from contextlib import nullcontext
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf import db as qf_db
from qf.api import apimart, console, idiomas, indexnow, panel, ratelimit, rutas_web, web_config, web_config_panel
from qf.api.main import app as main_app
from qf.comercial import cifrado

DSN = os.getenv("QF_TEST_PG_DSN")
HTML = {"accept": "text/html,application/xhtml+xml"}
FAKE_API_KEY = "sk-test-fake-000000000000000000000000"


@pytest.fixture
def aislado(monkeypatch, tmp_path):
    """Aísla archivo de idiomas, clave maestra y cachés en memoria sin depender de Postgres."""
    archivo = tmp_path / "activos.txt"
    archivo.write_text("en = off\npt = off\n", encoding="utf-8")
    monkeypatch.setenv("IDIOMAS_ARCHIVO", str(archivo))
    monkeypatch.setenv("QF_SECRETS_KEY", cifrado.generar_clave())
    monkeypatch.delenv("APIMART_API_KEY", raising=False)
    monkeypatch.delenv("API_MARKET_KEY", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(web_config, "_db_reachable", lambda: False)
    idiomas.olvidar()
    web_config.invalidar_cache()
    rutas_web._leido = None
    yield archivo
    idiomas.olvidar()
    web_config.invalidar_cache()
    rutas_web._leido = None


@pytest.fixture
def panel_client(aislado):
    app = FastAPI()
    app.include_router(web_config_panel.router)
    app.include_router(web_config.router)
    app.dependency_overrides[console.require_console] = lambda: "tester"
    return TestClient(app), panel.csrf_token("tester")


# --- sanitización, redes sociales y JSON-LD ------------------------------------------------------

def test_sanitize_html_elimina_vectores_xss_y_conserva_semantica():
    dirty = (
        '<h2 onclick="alert(1)">Metodología</h2>'
        '<p class="aviso">Solo estadística <a href="javascript:alert(1)">malo</a> '
        '<a href="/legal/privacidad" style="color:red">privacidad</a>.</p>'
        '<script>fetch("https://evil.test")</script>'
        '<iframe src="https://evil.test"></iframe>'
        '<time datetime="2026-11-10">10 nov</time>'
    )
    clean = web_config.sanitize_html(dirty)
    assert "<script" not in clean and "<iframe" not in clean
    assert "onclick" not in clean and "javascript:" not in clean and "style=" not in clean
    assert "<h2>Metodología</h2>" in clean
    assert '<p class="aviso">' in clean
    assert '<a href="/legal/privacidad">privacidad</a>' in clean
    assert '<time datetime="2026-11-10">10 nov</time>' in clean


def test_normalize_social_handles_y_rechaza_dominios_ajenos():
    assert web_config.normalize_social("social_x", "@QuantFut") == "https://x.com/QuantFut"
    assert web_config.normalize_social("social_x", "https://twitter.com/QuantFut") == "https://twitter.com/QuantFut"
    assert web_config.normalize_social("social_youtube", "quantfut") == "https://www.youtube.com/@quantfut"
    assert web_config.normalize_social("social_tiktok", "@quantfut") == "https://www.tiktok.com/@quantfut"
    assert web_config.normalize_social("social_telegram", "https://t.me/quantfut") == "https://t.me/quantfut"
    assert web_config.normalize_social("social_x", "") == ""

    with pytest.raises(ValueError):
        web_config.normalize_social("social_x", "https://evil.example.com/phish")
    with pytest.raises(ValueError):
        web_config.normalize_social("social_instagram", "javascript:alert(1)")

    cfg = web_config.DEFAULT_SETTINGS | {"social_x": "https://x.com/QuantFut"}
    assert web_config.twitter_site_handle(cfg) == "@QuantFut"
    patched = web_config.apply_org_jsonld(
        [{"@type": "Organization", "name": "Old", "legalName": "Old", "email": "old@x.com"},
         {"@type": "WebSite", "name": "Old"}],
        cfg | {"brand_name": "QuantFut Pro", "legal_name": "Saptain Ltd.", "support_email": "hola@quantfut.test"},
    )
    assert patched[0]["name"] == "QuantFut Pro"
    assert patched[0]["legalName"] == "Saptain Ltd."
    assert patched[0]["email"] == "hola@quantfut.test"
    assert patched[0]["sameAs"] == ["https://x.com/QuantFut"]
    assert patched[1]["name"] == "QuantFut Pro"


def test_catalog_defaults_cubre_todas_las_secciones_y_plantillas(aislado):
    defaults = web_config.catalog_defaults()
    keys = {k for k, _ in defaults}
    assert "ui:frontend" in keys
    assert all(f"spa:{s.ruta}" in keys for s in rutas_web.SECCIONES)
    for pk in ("pagina:metodologia", "pagina:juego-responsable", "pagina:sobre-nosotros"):
        assert (pk, "es") in defaults and (pk, "en") in defaults and (pk, "pt") in defaults
    for pk in ("legal:terminos", "legal:privacidad", "legal:eliminar-cuenta"):
        assert (pk, "es") in defaults and defaults[(pk, "es")]["body_html"]
    for pk in ("tool:calibracion", "tool:cuota-justa", "tool:verificacion", "sport:futbol", "sport:nba", "sport:tenis"):
        assert (pk, "es") in defaults and (pk, "en") in defaults and (pk, "pt") in defaults


# --- cliente APIMart (OpenAI-compatible) ---------------------------------------------------------

def test_apimart_cifrado_y_resolucion_de_clave(aislado, monkeypatch):
    assert apimart.resolve_api_key("") == ("", "none")
    enc = apimart.encrypt_api_key(FAKE_API_KEY)
    assert FAKE_API_KEY not in enc
    assert apimart.resolve_api_key(enc) == (FAKE_API_KEY, "db")

    monkeypatch.setenv("APIMART_API_KEY", FAKE_API_KEY + "-env")
    assert apimart.resolve_api_key(enc) == (FAKE_API_KEY, "db")
    assert apimart.resolve_api_key("") == (FAKE_API_KEY + "-env", "env")

    with pytest.raises(apimart.ApimartError):
        apimart.normalize_base_url("http://remote-insecure.example.com/v1")
    assert apimart.normalize_base_url("https://api.apimart.ai/v1/") == "https://api.apimart.ai/v1"
    assert FAKE_API_KEY not in apimart.redact_secrets(f"Bearer {FAKE_API_KEY} error", FAKE_API_KEY)


def test_apimart_translate_page_y_fallback_response_format(monkeypatch):
    calls: list[dict] = []

    class FakeResp:
        def __init__(self, status_code: int, payload: dict, text: str = ""):
            self.status_code = status_code
            self._payload = payload
            self.text = text or json.dumps(payload)

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, timeout=45.0):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            calls.append({"url": url, "headers": headers, "json": copy.deepcopy(json)})
            if len(calls) == 1:
                return FakeResp(400, {"error": {"message": "response_format json_object unsupported"}})
            return FakeResp(200, {
                "model": "gpt-4o-mini",
                "usage": {"total_tokens": 120},
                "choices": [{
                    "message": {
                        "content": (
                            "```json\n"
                            + json_module_dumps({
                                "title": "Methodology | QuantFut",
                                "description": "How we compute statistical probabilities.",
                                "h1": "Methodology",
                                "migas": "Methodology",
                                "revision_date": "2026-11-10",
                                "body_html": "<p>Statistical baseline.</p>",
                            })
                            + "\n```"
                        )
                    }
                }],
            })

    json_module_dumps = json.dumps
    monkeypatch.setattr(httpx, "Client", FakeClient)

    res = apimart.translate_page(
        source={
            "page_key": "pagina:metodologia",
            "kind": "pagina",
            "title": "Metodología | QuantFut",
            "description": "Cómo calculamos probabilidades.",
            "h1": "Metodología",
            "migas": "Metodología",
            "revision_date": "2026-11-10",
            "body_html": "<p>Base estadística.</p>",
        },
        target_lang="en",
        brand_name="QuantFut",
        legal_name="Saptain LTD",
        support_email="admin@pronosticosdeportivos.pro",
        api_key=FAKE_API_KEY,
        base_url="https://api.apimart.ai/v1",
        model="gpt-4o-mini",
    )
    assert len(calls) == 2
    assert calls[0]["headers"]["Authorization"] == f"Bearer {FAKE_API_KEY}"
    assert "response_format" in calls[0]["json"]
    assert "response_format" not in calls[1]["json"]
    assert res["title"] == "Methodology | QuantFut"
    assert res["body_html"] == "<p>Statistical baseline.</p>"


def test_apimart_ui_dictionary_y_errores_sin_fuga(monkeypatch):
    class FakeResp:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.text = json.dumps(payload)

        def json(self):
            return self._payload

    class FakeClient:
        def __init__(self, timeout=45.0):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers=None, json=None):
            return FakeResp(200, {
                "model": "gpt-4o-mini",
                "choices": [{"message": {"content": globals_json({"title": "QuantFut UI", "ui": {"nav_inicio": "Home"}})}}],
            })

    globals_json = json.dumps
    monkeypatch.setattr(httpx, "Client", FakeClient)
    out = apimart.translate_page(
        source={
            "page_key": "ui:frontend",
            "kind": "ui",
            "title": "QuantFut UI",
            "description": "Desc",
            "h1": "UI",
            "migas": "UI",
            "body_html": json.dumps({"nav_inicio": "Inicio", "nav_planes": "Planes"}),
        },
        target_lang="en",
        brand_name="QuantFut",
        legal_name="Saptain LTD",
        support_email="admin@pronosticosdeportivos.pro",
        api_key=FAKE_API_KEY,
        base_url="https://api.apimart.ai/v1",
        model="gpt-4o-mini",
    )
    parsed_ui = json.loads(out["body_html"])
    assert parsed_ui["nav_inicio"] == "Home"
    assert parsed_ui["nav_planes"] == "Planes"

    class UnauthorizedClient(FakeClient):
        def post(self, url, headers=None, json=None):
            return FakeResp(401, {"error": {"message": f"invalid key {FAKE_API_KEY}"}})

    monkeypatch.setattr(httpx, "Client", UnauthorizedClient)
    with pytest.raises(apimart.ApimartError) as exc:
        apimart.test_connection(api_key=FAKE_API_KEY, base_url="https://api.apimart.ai/v1", model="gpt-4o-mini")
    assert FAKE_API_KEY not in str(exc.value)


# --- integración SSR / SEO / Legal / IndexNow / Panel (sin requerir PG externo) -----------------

def test_web_config_endpoint_no_expone_secretos_y_refleja_ajustes(aislado, monkeypatch):
    custom = web_config.DEFAULT_SETTINGS | {
        "brand_name": "QuantFut X",
        "maintenance_banner": "Ventana de mantenimiento",
        "social_x": "https://x.com/QuantFut",
        "public_cache_seconds": 120,
        "content_signal": "search=yes, ai-input=no, ai-train=no",
        "indexnow_enabled": False,
    }
    monkeypatch.setattr(web_config, "get_settings", lambda use_cache=True: custom)
    monkeypatch.setattr(web_config, "get_apimart_runtime_config", lambda: {"api_key": FAKE_API_KEY, "key_origin": "db", "base_url": apimart.DEFAULT_BASE_URL, "model": apimart.DEFAULT_MODEL})

    c = TestClient(main_app)
    r = c.get("/web/config")
    assert r.status_code == 200
    data = r.json()
    assert data["brand_name"] == "QuantFut X"
    assert data["maintenance_banner"] == "Ventana de mantenimiento"
    assert data["social"] == [{"key": "x", "label": "X", "url": "https://x.com/QuantFut"}]
    assert "apimart_key_enc" not in r.text and FAKE_API_KEY not in r.text
    assert r.headers["cache-control"] == "public, max-age=120"

    robots = c.get("/robots.txt")
    assert "Content-Signal: search=yes, ai-input=no, ai-train=no" in robots.text

    idx_res = indexnow.ejecutar(enviar=True, leer=lambda: b"", dominio="pronosticosdeportivos.pro")
    assert idx_res.get("desactivado") is True


def test_legal_y_spa_localizados_puertas_y_hreflang(aislado, monkeypatch):
    archivo = Path(aislado)
    translated_pages = {
        ("legal:terminos", "es"): {
            "page_key": "legal:terminos",
            "lang": "es",
            "kind": "legal",
            "title": "Términos Custom",
            "description": "Desc ES",
            "h1": "Términos de Uso Custom",
            "migas": "Términos",
            "body_html": "<p>Cláusula oficial de prueba.</p>",
            "revision_date": "",
        },
        ("legal:terminos", "en"): {
            "page_key": "legal:terminos",
            "lang": "en",
            "kind": "legal",
            "title": "Terms of Service | QuantFut",
            "description": "Terms EN",
            "h1": "Terms of Service",
            "migas": "Terms",
            "body_html": "<p>Statistical information terms in English.</p>",
            "revision_date": "",
        },
        ("spa:historial", "en"): {
            "page_key": "spa:historial",
            "lang": "en",
            "kind": "spa",
            "title": "Verified History | QuantFut",
            "description": "Published pick ledger in English.",
            "h1": "Verified Pick History",
            "migas": "History",
            "body_html": "<p>Every sealed pick since launch.</p>",
            "revision_date": "",
        },
    }
    monkeypatch.setattr(web_config, "get_page", lambda pk, lang="es", use_cache=True: translated_pages.get((pk, lang)))
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    c = TestClient(main_app, base_url="https://pronosticosdeportivos.pro")

    # Idiomas apagados -> /en/history/ y /en/legal/terms devuelven 404
    assert c.get("/en/legal/terms", headers=HTML).status_code == 404
    assert c.get("/en/history/", headers=HTML).status_code == 404
    assert c.get("/legal/terminos", headers=HTML).status_code == 200
    assert "Cláusula oficial de prueba." in c.get("/legal/terminos", headers=HTML).text

    # En preview -> 200 noindex
    archivo.write_text("en = preview\npt = off\n", encoding="utf-8")
    idiomas.olvidar()
    prev = c.get("/en/legal/terms", headers=HTML)
    assert prev.status_code == 200 and prev.headers["x-robots-tag"] == "noindex"

    # En on -> indexable, y aparecen tanto en rutas como en sitemap con hreflang recíproco
    archivo.write_text("en = on\npt = off\n", encoding="utf-8")
    idiomas.olvidar()
    live_legal = c.get("/en/legal/terms", headers=HTML)
    assert live_legal.status_code == 200 and "x-robots-tag" not in live_legal.headers
    assert "Statistical information terms in English." in live_legal.text

    live_spa = c.get("/en/history/", headers=HTML)
    assert live_spa.status_code == 200
    assert '<html lang="en" data-lang="en" data-ruta="historial">' in live_spa.text
    assert "Verified Pick History" in live_spa.text

    sitemap_xml = c.get("/sitemap-paginas.xml").text
    assert "https://pronosticosdeportivos.pro/en/legal/terms" in sitemap_xml
    assert "https://pronosticosdeportivos.pro/en/history/" in sitemap_xml
    # Documento legal sin traducir (eliminar-cuenta) no se publica aún en EN en el sitemap
    assert "https://pronosticosdeportivos.pro/en/legal/delete-account" not in sitemap_xml


def test_panel_configuracion_render_csrf_y_sin_clave_expuesta(panel_client, monkeypatch):
    client, csrf = panel_client
    monkeypatch.setattr(web_config, "_load_bundle_uncached", lambda seed_if_empty=False: {
        "settings": web_config.DEFAULT_SETTINGS | {"social_x": "https://x.com/QuantFut"},
        "pages": {},
        "apimart_key_enc": apimart.encrypt_api_key(FAKE_API_KEY),
        "db_ok": True,
    })

    r = client.get("/control/configuracion")
    assert r.status_code == 200
    assert "Configuración web" in r.text and "APIMart" in r.text
    assert "ui:frontend" in r.text and "legal:terminos" in r.text
    assert FAKE_API_KEY not in r.text

    # CSRF inválido -> 403
    bad = client.post("/control/configuracion/idiomas", data={"en_state": "on", "pt_state": "off", "csrf": "invalido"}, follow_redirects=False)
    assert bad.status_code == 403

    # POSTs con CSRF válido -> PRG 303
    called: list[tuple] = []
    monkeypatch.setattr(web_config, "save_language_states", lambda en, pt, actor: called.append(("lang", en, pt, actor)) or {"en": en, "pt": pt})
    ok = client.post("/control/configuracion/idiomas", data={"en_state": "preview", "pt_state": "on", "csrf": csrf}, follow_redirects=False)
    assert ok.status_code == 303 and "msg=web_idiomas_guardado" in ok.headers["location"]
    assert called == [("lang", "preview", "on", "panel:tester")]

    monkeypatch.setattr(web_config, "save_general_settings", lambda form, actor: called.append(("gen", form["brand_name"])) or web_config.DEFAULT_SETTINGS)
    ok_gen = client.post("/control/configuracion/general", data={
        "brand_name": "QuantFut", "legal_name": "Saptain LTD", "hero_badge": "SPORTS INTELLIGENCE",
        "support_email": "admin@pronosticosdeportivos.pro", "disclaimer_text": "Aviso +18.",
        "default_robots": "index,follow", "public_cache_seconds": "300", "csrf": csrf,
    }, follow_redirects=False)
    assert ok_gen.status_code == 303 and "msg=web_guardado" in ok_gen.headers["location"]

    # APIMart save + probar + lote
    monkeypatch.setattr(web_config, "save_apimart_settings", lambda **kw: {"base_url": kw["base_url"], "model": kw["model"], "api_key": FAKE_API_KEY})
    ok_api = client.post("/control/configuracion/apimart", data={
        "apimart_base_url": "https://api.apimart.ai/v1", "apimart_model": "gpt-4o-mini",
        "apimart_api_key": FAKE_API_KEY, "target_langs": ["en", "pt"], "csrf": csrf,
    }, follow_redirects=False)
    assert ok_api.status_code == 303 and "msg=web_apimart_guardado" in ok_api.headers["location"]

    monkeypatch.setattr(web_config, "get_apimart_runtime_config", lambda: {"api_key": FAKE_API_KEY, "key_origin": "db", "base_url": apimart.DEFAULT_BASE_URL, "model": apimart.DEFAULT_MODEL})
    monkeypatch.setattr(apimart, "test_connection", lambda **kw: {"ok": True, "model": kw["model"], "latency_ms": 12, "preview": "OK"})
    ok_probe = client.post("/control/configuracion/apimart/probar", data={"csrf": csrf}, follow_redirects=False)
    assert ok_probe.status_code == 303 and "msg=web_apimart_ok" in ok_probe.headers["location"]

    monkeypatch.setattr(web_config, "translate_pending_batch", lambda **kw: {"done": 2, "skipped": 4, "errors": []})
    ok_batch = client.post("/control/configuracion/traducir-lote", data={"target_lang": "en", "csrf": csrf}, follow_redirects=False)
    assert ok_batch.status_code == 303 and "msg=web_traduccion_lote" in ok_batch.headers["location"]

    # Editor individual de página: GET + guardar + traducir + restaurar
    pg_view = client.get("/control/configuracion/pagina/legal:terminos?lang=en")
    assert pg_view.status_code == 200 and "legal:terminos" in pg_view.text

    monkeypatch.setattr(web_config, "save_page", lambda **kw: {"page_key": kw["page_key"], "lang": kw["lang"]})
    pg_save = client.post("/control/configuracion/pagina/legal:terminos/guardar", data={
        "lang": "en", "title": "Terms", "description": "Desc", "h1": "Terms", "migas": "Terms",
        "body_html": "<p>Body</p>", "reviewed": "1", "csrf": csrf,
    }, follow_redirects=False)
    assert pg_save.status_code == 303 and "msg=web_pagina_guardada" in pg_save.headers["location"]

    monkeypatch.setattr(web_config, "translate_page_db", lambda pk, lang, actor: {"page_key": pk, "lang": lang})
    pg_tr = client.post("/control/configuracion/pagina/legal:terminos/traducir", data={"target_lang": "pt", "csrf": csrf}, follow_redirects=False)
    assert pg_tr.status_code == 303 and "msg=web_traduccion_ok" in pg_tr.headers["location"]

    monkeypatch.setattr(web_config, "restore_page_default", lambda pk, lang, actor: None)
    pg_rst = client.post("/control/configuracion/pagina/legal:terminos/restaurar", data={"lang": "en", "csrf": csrf}, follow_redirects=False)
    assert pg_rst.status_code == 303 and "msg=web_pagina_restaurada" in pg_rst.headers["location"]


def test_panel_ruta_en_aplicacion_principal():
    from starlette.routing import Match

    scope = {"type": "http", "method": "GET", "path": "/control/configuracion", "root_path": ""}
    matched = [r for r in main_app.routes if r.matches(scope)[0] == Match.FULL]
    assert matched, "/control/configuracion no está registrado en main.app"


# --- PostgreSQL real (migración db/110_web_config.sql + CRUD + auditoría + cifrado) -------------

@pytest.fixture
def pg_wc(monkeypatch, tmp_path):
    if not DSN:
        pytest.skip("sin QF_TEST_PG_DSN")
    import psycopg
    from psycopg.rows import dict_row

    archivo = tmp_path / "activos.txt"
    archivo.write_text("en = off\npt = off\n", encoding="utf-8")
    monkeypatch.setenv("IDIOMAS_ARCHIVO", str(archivo))
    monkeypatch.setenv("QF_SECRETS_KEY", cifrado.generar_clave())
    monkeypatch.delenv("APIMART_API_KEY", raising=False)
    idiomas.olvidar()
    web_config.invalidar_cache()

    c = psycopg.connect(DSN, row_factory=dict_row)
    try:
        monkeypatch.setattr(qf_db, "conn", lambda: nullcontext(c))
        monkeypatch.setattr(web_config, "_db_reachable", lambda: True)
        yield c
    finally:
        c.rollback()
        c.close()
        idiomas.olvidar()
        web_config.invalidar_cache()


def test_pg_migracion_y_constraints_db_110(pg_wc):
    import psycopg

    row = pg_wc.execute("SELECT id, brand_name, public_cache_seconds, lang_states FROM web_site_settings WHERE id = 1").fetchone()
    assert row and row["brand_name"] == "QuantFut" and row["public_cache_seconds"] == 300
    assert row["lang_states"] == {"en": "off", "pt": "off"}

    pg_wc.execute("SAVEPOINT s1")
    with pytest.raises(psycopg.errors.CheckViolation):
        pg_wc.execute("UPDATE web_site_settings SET public_cache_seconds = 999999 WHERE id = 1")
    pg_wc.execute("ROLLBACK TO SAVEPOINT s1")


def test_pg_crud_settings_cifrado_y_traduccion_auditada(pg_wc, monkeypatch):
    # 1. Seed idempotente + ajustes generales + social
    web_config.ensure_seeded(pg_wc)
    saved = web_config.save_general_settings({
        "brand_name": "QuantFut Live",
        "legal_name": "Saptain LTD",
        "hero_badge": "ESTADÍSTICA REAL",
        "support_email": "soporte@quantfut.test",
        "disclaimer_text": "Solo mayores de 18 años.",
        "maintenance_banner": "Ventana programada",
        "social_x": "@QuantFut",
        "social_telegram": "quantfut_canal",
        "default_robots": "index,follow",
        "content_signal": "search=yes, ai-input=yes, ai-train=no",
        "public_cache_seconds": "600",
        "indexnow_enabled": "1",
        "lang_selector_enabled": "1",
    }, actor="panel:test")
    assert saved["brand_name"] == "QuantFut Live"
    assert saved["social_x"] == "https://x.com/QuantFut"
    assert saved["social_telegram"] == "https://t.me/quantfut_canal"
    assert saved["public_cache_seconds"] == 600

    # 2. Clave APIMart cifrada AES-GCM (solo lectura runtime descifrada)
    rt = web_config.save_apimart_settings(
        base_url="https://api.apimart.ai/v1",
        model="gpt-4o-mini",
        new_api_key=FAKE_API_KEY,
        clear_api_key=False,
        target_langs=["en", "pt"],
        actor="panel:test",
    )
    assert rt["api_key"] == FAKE_API_KEY and rt["key_origin"] == "db"
    raw_db = pg_wc.execute("SELECT apimart_key_enc FROM web_site_settings WHERE id = 1").fetchone()["apimart_key_enc"]
    assert raw_db and FAKE_API_KEY not in raw_db

    # Guardar sin nueva clave conserva la existente
    rt2 = web_config.save_apimart_settings(
        base_url="https://api.apimart.ai/v1",
        model="gpt-4o",
        new_api_key="",
        clear_api_key=False,
        target_langs=["en"],
        actor="panel:test",
    )
    assert rt2["api_key"] == FAKE_API_KEY and rt2["model"] == "gpt-4o"

    # 3. Estado de idiomas en Postgres y archivo sincronizado
    states = web_config.save_language_states("preview", "on", actor="panel:test")
    assert states == {"en": "preview", "pt": "on"}
    assert "en = preview" in idiomas.archivo().read_text(encoding="utf-8")

    # 4. Traducción con APIMart mockeado + detección de desactualización (stale)
    monkeypatch.setattr(apimart, "translate_page", lambda **kw: {
        "title": "Terms of Service | QuantFut Live",
        "description": "Official legal terms.",
        "h1": "Terms of Service",
        "migas": "Terms",
        "revision_date": "",
        "body_html": "<p>Statistical forecast rules.</p><script>bad()</script>",
        "model": kw["model"],
        "usage": {},
    })
    tr = web_config.translate_page_db("legal:terminos", "en", actor="panel:test")
    assert tr["is_auto_translated"] is True and tr["reviewed"] is False
    assert "<script>" not in tr["body_html"]

    # Editar la versión ES vuelve la traducción EN desactualizada (`stale`)
    web_config.save_page(
        page_key="legal:terminos",
        lang="es",
        title="Términos editados",
        description="Desc",
        h1="Términos",
        migas="Términos",
        body_html="<p>Nueva cláusula en español.</p>",
        revision_date="",
        reviewed=True,
        actor="panel:test",
    )
    overview = web_config.build_catalog_overview(seed_if_needed=False)
    term_row = next(r for r in overview["rows"] if r["page_key"] == "legal:terminos")
    assert term_row["langs"]["en"]["stale"] is True

    # Restaurar valor por defecto
    web_config.restore_page_default("legal:terminos", "en", actor="panel:test")
    assert pg_wc.execute("SELECT 1 FROM web_page_contents WHERE page_key='legal:terminos' AND lang='en'").fetchone() is None

    # 5. Auditoría inmutable registrada
    audits = pg_wc.execute("SELECT action FROM admin_audit WHERE actor = 'panel:test' ORDER BY audit_id").fetchall()
    actions = [a["action"] for a in audits]
    assert "web_config_general_save" in actions
    assert "web_config_apimart_save" in actions
    assert "web_config_lang_states_save" in actions
    assert "web_config_translate" in actions
    assert "web_config_page_save" in actions
    assert "web_config_page_restore" in actions
