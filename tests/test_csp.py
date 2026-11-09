"""F5: CSP en modo informe. Sin red ni base: se prueba la cabecera, el receptor de informes y su saneado."""
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from qf.api import csp, main, ratelimit

BASE = "https://pronosticosdeportivos.pro"
HTML = {"accept": "text/html,application/xhtml+xml"}
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.setenv("CSP_DIR", str(tmp_path / "csp"))
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(csp, "_ventana", {"inicio": 0.0, "n": 0})
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


def informe_antiguo(**extra):
    base = {"document-uri": f"{BASE}/nba/x-vs-y-2026-11-09/?token=SECRETO&a=1", "effective-directive": "script-src-elem",
            "violated-directive": "script-src-elem", "blocked-uri": "https://evil.example.com/p.js?k=SECRETO", "disposition": "report"}
    return {"csp-report": {**base, **extra}}


# --- la cabecera ----------------------------------------------------------------------------------

def test_las_paginas_html_publicas_llevan_la_politica_en_modo_informe(client):
    for ruta in ("/", "/historial/", "/planes/", "/nba/", "/futbol/", "/tenis/"):
        r = client.get(ruta, headers=HTML)
        assert r.headers.get("content-security-policy-report-only") == csp.POLITICA, ruta
        assert "content-security-policy" not in r.headers, ruta                # NO se aplica: solo informa
        assert r.headers["reporting-endpoints"] == 'csp="/csp-report"'


def test_no_la_llevan_ni_json_ni_panel_ni_imagenes_ni_el_motor_ni_las_paginas_con_su_propia_csp(client):
    for ruta in ("/robots.txt", "/sitemap.xml", "/web/imagenes/manifiesto.json", "/nba/v1/cartelera?fecha=2026-11-08", "/nba/v2/", "/csp-report"):
        r = client.get(ruta)
        assert "content-security-policy-report-only" not in r.headers, ruta
    paginas_con_csp = client.get("/metodologia/", headers=HTML)                 # ya trae una CSP estricta propia
    assert "content-security-policy" in paginas_con_csp.headers
    assert "content-security-policy-report-only" not in paginas_con_csp.headers


def test_la_politica_es_realista_y_no_afloja_lo_peligroso():
    d = {x.split(" ")[0]: x for x in csp.POLITICA.split("; ")}
    assert d["default-src"] == "default-src 'self'"
    assert "'unsafe-eval'" not in csp.POLITICA and "'unsafe-inline'" not in d["script-src"]
    assert "'unsafe-inline'" in d["style-src"]                                  # la app pinta style= en línea: se admite y se mide
    for host in ("https://connect.facebook.net", "https://static.cloudflareinsights.com", "https://www.gstatic.com", "https://cdn.whop.com"):
        assert host in d["script-src"], host
    assert d["object-src"] == "object-src 'none'" and d["base-uri"] == "base-uri 'self'" and d["frame-ancestors"] == "frame-ancestors 'none'"
    assert "report-uri /csp-report" in csp.POLITICA and csp.POLITICA.endswith("report-to csp")
    assert "*" not in d["script-src"].replace("*.", "")                         # sin comodín general en scripts


def test_el_html_de_la_app_no_tiene_scripts_ni_manejadores_en_linea():
    """Si esto falla, la política `script-src` sin 'unsafe-inline' dejaría de ser realista."""
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html)
    assert not re.search(r"\son[a-z]+\s*=", html)
    assert not re.search(r"javascript:", html)


# --- el receptor ----------------------------------------------------------------------------------

def test_recibe_el_formato_de_report_uri_y_guarda_solo_lo_necesario(client, tmp_path):
    r = client.post("/csp-report", content=json.dumps(informe_antiguo()), headers={"content-type": "application/csp-report"})
    assert r.status_code == 204 and r.content == b""
    lineas = (tmp_path / "csp" / "informes.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lineas) == 1
    fila = json.loads(lineas[0])
    assert set(fila) == {"t", "directiva", "bloqueado", "ruta", "disposicion"}
    assert fila["directiva"] == "script-src-elem" and fila["bloqueado"] == "evil.example.com" and fila["ruta"] == "/nba/x-vs-y-2026-11-09/"
    assert "SECRETO" not in lineas[0] and "token" not in lineas[0] and "?" not in lineas[0]      # ni la consulta ni las URL completas


def test_recibe_el_formato_de_report_to(client, tmp_path):
    cuerpo = [{"type": "csp-violation", "age": 5, "url": f"{BASE}/futbol/",
               "body": {"documentURL": f"{BASE}/futbol/?x=1", "effectiveDirective": "img-src", "blockedURL": "https://cdn.otro.net/i.png?s=1", "disposition": "report"}},
              {"type": "network-error", "body": {"x": 1}}, "basura", None]
    assert client.post("/csp-report", content=json.dumps(cuerpo), headers={"content-type": "application/reports+json"}).status_code == 204
    filas = [json.loads(x) for x in (tmp_path / "csp" / "informes.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(filas) == 1 and filas[0]["bloqueado"] == "cdn.otro.net" and filas[0]["ruta"] == "/futbol/" and filas[0]["directiva"] == "img-src"


def test_palabras_clave_de_bloqueo_no_se_confunden_con_hosts(client, tmp_path):
    for bloqueado in ("inline", "eval", "data", "blob:https://x.com/uuid", ""):
        client.post("/csp-report", content=json.dumps(informe_antiguo(**{"blocked-uri": bloqueado})))
    hosts = [json.loads(x)["bloqueado"] for x in (tmp_path / "csp" / "informes.jsonl").read_text(encoding="utf-8").splitlines()]
    assert hosts == ["inline", "eval", "data", "blob", "(vacío)"]


def test_basura_y_cuerpos_enormes_no_rompen_nada_ni_guardan(client, tmp_path):
    for cuerpo in (b"", b"no es json", b"\xff\xfe\x00", b"[]", b"{}", b'{"csp-report": 5}', b'{"csp-report": {}}'):
        assert client.post("/csp-report", content=cuerpo).status_code == 204
    assert client.post("/csp-report", content=b"x" * (csp.MAX_CUERPO + 1)).status_code == 413
    assert not (tmp_path / "csp" / "informes.jsonl").exists()
    assert client.get("/csp-report").status_code == 405


def test_hay_tope_por_hora_y_por_tamano_de_archivo(client, tmp_path, monkeypatch):
    monkeypatch.setattr(csp, "MAX_POR_HORA", 3)
    for _ in range(6):
        client.post("/csp-report", content=json.dumps(informe_antiguo()))
    assert len((tmp_path / "csp" / "informes.jsonl").read_text(encoding="utf-8").splitlines()) == 3
    monkeypatch.setattr(csp, "_ventana", {"inicio": 0.0, "n": 0})
    monkeypatch.setattr(csp, "MAX_POR_HORA", 400)
    monkeypatch.setattr(csp, "MAX_ARCHIVO", 10)
    client.post("/csp-report", content=json.dumps(informe_antiguo()))
    assert len((tmp_path / "csp" / "informes.jsonl").read_text(encoding="utf-8").splitlines()) == 3        # archivo lleno: no escribe más


def test_el_resumen_cuenta_por_directiva_y_host(client, tmp_path):
    for _ in range(3):
        client.post("/csp-report", content=json.dumps(informe_antiguo()))
    client.post("/csp-report", content=json.dumps(informe_antiguo(**{"effective-directive": "img-src", "blocked-uri": "https://img.otro.net/a.png"})))
    filas = csp.resumen(tmp_path / "csp" / "informes.jsonl")
    assert filas[0] == (3, "script-src-elem", "evil.example.com", "/nba/x-vs-y-2026-11-09/") and filas[1][:3] == (1, "img-src", "img.otro.net")
    assert csp.resumen(tmp_path / "no-existe.jsonl") == []


def test_la_ruta_de_informes_no_es_indexable_y_no_lleva_la_politica(client):
    from starlette.requests import Request
    from qf.api import seo
    peticion = Request({"type": "http", "method": "GET", "path": "/csp-report", "query_string": b"", "headers": [(b"host", b"pronosticosdeportivos.pro")]})
    assert seo.noindex(peticion)
    r = client.post("/csp-report", content=b"{}")
    assert r.headers["x-robots-tag"] == "noindex" and "content-security-policy-report-only" not in r.headers
