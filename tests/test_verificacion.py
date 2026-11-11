"""F8 / §2: página pública `/verificacion/` (+ `/en/verification/`, `/pt/verificacao/`)."""
from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from qf.api import idiomas, main, ratelimit, verificacion
from qf.publish import hashchain as hc
from test_idiomas import PALABRAS_ES as PALABRAS_ES_EN, visible
from test_idiomas_pt import PALABRAS_ES as PALABRAS_ES_PT

BASE = "https://pronosticosdeportivos.pro"
HTML = {"accept": "text/html,application/xhtml+xml"}
XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


@pytest.fixture
def estado(tmp_path, monkeypatch):
    archivo = tmp_path / "activos.txt"
    monkeypatch.setenv("IDIOMAS_ARCHIVO", str(archivo))

    def poner(texto: str | None):
        if texto is None:
            archivo.unlink(missing_ok=True)
        else:
            archivo.write_text(texto, encoding="utf-8")
        idiomas.olvidar()

    idiomas.olvidar()
    yield poner
    idiomas.olvidar()


@pytest.fixture
def client(monkeypatch, estado):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


def _lotes_desc(n: int = 3) -> list[dict]:
    prev = hc.GENESIS
    cron = []
    for dia in range(1, n + 1):
        fecha = f"2026-11-{dia:02d}"
        body = hc.canonical_json({"batch_date": fecha, "n": dia})
        ph = hc.sha256_hex(body)
        ch = hc.sha256_hex(prev + ph)
        cron.append({
            "batch_date": fecha,
            "batch_kind": "diario",
            "match_id": None,
            "n_predictions": dia * 10,
            "n_picks": dia,
            "payload_sha256": ph,
            "prev_sha256": prev,
            "chain_sha256": ch,
        })
        prev = ch
    return list(reversed(cron))


def _mapa(client) -> dict[str, dict[str, str]]:
    raiz = ET.fromstring(client.get("/sitemap-paginas.xml").content)
    return {
        u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")}
        for u in raiz.findall(f"{NS}url")
    }


def test_verificacion_espanol_csp_head_accesible_y_301(client):
    r = client.get("/verificacion/", headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    csp = r.headers["content-security-policy"]
    assert "default-src 'none'" in csp and "script-src 'self'" in csp and "connect-src 'self'" in csp
    script = next(d for d in csp.split("; ") if d.startswith("script-src"))
    assert "unsafe-inline" not in script and "unsafe-eval" not in script and "http" not in script

    t = r.text
    assert f'<link rel="canonical" href="{BASE}/verificacion/">' in t
    assert 'name="robots" content="index, follow' in t
    assert '"@type": "BreadcrumbList"' in t and '"@type": "WebPage"' in t
    etiquetas = re.findall(r"<script\b([^>]*)>", t)
    propios = [e for e in etiquetas if "application/ld+json" not in e]
    assert len(propios) == 1 and re.search(r'src="/static/verificar-cadena\.js\?v=[0-9a-f]{10}"', propios[0])
    assert "onclick" not in t and "onchange" not in t and "javascript:" not in t
    assert '<label for="vc-archivo"' in t and '<label for="vc-json"' in t
    assert "no está disponible" in t or "no hay lotes" in t.lower()

    redir = client.get("/verificacion?x=1")
    assert redir.status_code == 301 and redir.headers["location"] == f"{BASE}/verificacion/?x=1"
    assert client.head("/verificacion/").status_code == 200

    js = client.get("/static/verificar-cadena.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert "export async function verificarLotes" in js.text


def test_verificacion_ssr_real_con_lotes_y_deteccion_de_alteracion(client, monkeypatch):
    assert verificacion.GENESIS == hc.GENESIS
    assert verificacion.sha256_hex("a" + "b") == hc.sha256_hex("a" + "b")

    lotes = _lotes_desc(3)
    monkeypatch.setattr(verificacion, "carga_lotes", lambda limite=90: lotes)
    ok_html = client.get("/verificacion/", headers=HTML).text
    assert "Cadena consistente: 3 lote(s) revisados desde el génesis." in ok_html
    assert lotes[0]["chain_sha256"][:16] in ok_html

    alterados = _lotes_desc(3)
    alterados[1]["chain_sha256"] = "e" * 64
    monkeypatch.setattr(verificacion, "carga_lotes", lambda limite=90: alterados)
    fail_html = client.get("/verificacion/", headers=HTML).text
    assert "Incidencias detectadas en 3 lote(s)" in fail_html
    assert "FALLO" in fail_html


def test_puertas_en_y_pt_hreflang_y_metodologia_enlazada(client, estado):
    estado(None)
    assert client.get("/en/verification/", headers=HTML).status_code == 404
    assert client.get("/pt/verificacao/", headers=HTML).status_code == 404
    assert "/en/verification/" not in client.get("/sitemap-paginas.xml").text
    assert "/pt/verificacao/" not in client.get("/sitemap-paginas.xml").text

    estado("en=preview\npt=preview")
    r_en = client.get("/en/verification/", headers=HTML)
    r_pt = client.get("/pt/verificacao/", headers=HTML)
    assert r_en.status_code == 200 and r_en.headers["x-robots-tag"] == "noindex" and r_en.headers["cache-control"] == "no-store"
    assert r_pt.status_code == 200 and r_pt.headers["x-robots-tag"] == "noindex" and r_pt.headers["cache-control"] == "no-store"

    estado("en=on\npt=on")
    mapa = _mapa(client)
    esperado = {
        "es": f"{BASE}/verificacion/",
        "en": f"{BASE}/en/verification/",
        "pt": f"{BASE}/pt/verificacao/",
        "x-default": f"{BASE}/verificacion/",
    }
    for u in (esperado["es"], esperado["en"], esperado["pt"]):
        assert mapa[u] == esperado

    r301_en = client.get("/en/verification?a=1")
    r301_pt = client.get("/pt/verificacao?b=2")
    assert r301_en.status_code == 301 and r301_en.headers["location"] == f"{BASE}/en/verification/?a=1"
    assert r301_pt.status_code == 301 and r301_pt.headers["location"] == f"{BASE}/pt/verificacao/?b=2"

    # Enlaces desde metodología en los tres idiomas
    assert 'href="/verificacion/"' in client.get("/metodologia/", headers=HTML).text
    assert 'href="/en/verification/"' in client.get("/en/methodology/", headers=HTML).text
    assert 'href="/pt/verificacao/"' in client.get("/pt/metodologia/", headers=HTML).text


def test_textos_en_y_pt_sin_espanol_ni_promesas_falsas(client, estado):
    estado("en=on\npt=on")
    t_en = client.get("/en/verification/", headers=HTML).text
    assert '<html lang="en">' in t_en and 'property="og:locale" content="en_US"' in t_en
    vis_en = visible(t_en)
    assert PALABRAS_ES_EN.findall(vis_en.lower()) == []
    assert not re.search(r"[áéíóúñ¿¡]", vis_en.lower())
    assert "independent external third-party timestamp" in vis_en.lower()

    t_pt = client.get("/pt/verificacao/", headers=HTML).text
    assert '<html lang="pt-BR">' in t_pt and 'property="og:locale" content="pt_BR"' in t_pt
    vis_pt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t_pt.split('<main id="contenido">', 1)[1].split("</footer>", 1)[0])))
    assert PALABRAS_ES_PT.findall(vis_pt.lower()) == []
    assert not re.search(r"[ñ¿¡]", vis_pt.lower())
    assert "carimbo de tempo externo independente" in vis_pt.lower()
