"""F6.2c: tenis en inglés (`/en/tenis/` y `/en/tenis/{torneo}/{slug}/`). Eventos simulados como en test_tenis_paginas.py."""
import html
import re
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from qf.api import idiomas, main, ratelimit, seo, tenis_datos, tenis_en, tenis_paginas
from test_idiomas import estado  # noqa: F401  (fixture del archivo de estados)
from test_tenis_paginas import (AHORA, BASE, EVENTOS, HOY, HTML, U_ACIERTO, U_CANCELADO, U_FALLO, U_PREVIA, U_TRAMPA, U_WALKOVER)

XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PALABRAS_ES = re.compile(r"\b(el|la|los|las|de|del|que|para|con|una|un|por|se|su|es|más|pero|cuando|esta|este|y|empate|ganó|jugador)\b")
EN_ACIERTO, EN_FALLO, EN_TRAMPA = "/en" + U_ACIERTO, "/en" + U_FALLO, "/en" + U_TRAMPA
EN_PREVIA, EN_CANCELADO, EN_WALKOVER = "/en" + U_PREVIA, "/en" + U_CANCELADO, "/en" + U_WALKOVER


def visible(texto: str) -> str:
    cuerpo = texto.split('<main id="contenido">', 1)[1].split("</footer>", 1)[0]
    cuerpo = re.sub(r"<a [^>]*lang=\"es\"[^>]*>.*?</a>", " ", cuerpo, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))).strip()


@pytest.fixture
def client(monkeypatch, estado):  # noqa: F811
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(tenis_paginas, "_ahora", lambda: AHORA)
    monkeypatch.setattr(tenis_datos, "hoy_utc", lambda ahora=None: HOY)
    monkeypatch.setattr(tenis_datos, "eventos", lambda: list(EVENTOS))
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


@pytest.fixture
def abierto(client, estado):  # noqa: F811
    estado("en=on")
    return client


# --- apagado y vista previa -----------------------------------------------------------------------

def test_apagado_tenis_en_ingles_da_404_y_no_esta_en_el_mapa(client, estado):  # noqa: F811
    estado(None)
    for ruta in ("/en/tenis/", EN_ACIERTO, "/en/tenis", EN_ACIERTO.rstrip("/")):
        assert client.get(ruta, headers=HTML).status_code == 404, ruta
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/en/tenis" not in mapa and "xhtml:link" not in mapa
    assert client.get(U_ACIERTO, headers=HTML).status_code == 200          # el español, intacto


def test_preview_tenis_en_ingles_no_se_indexa_ni_se_enumera(client, estado):  # noqa: F811
    estado("en=preview")
    for ruta in ("/en/tenis/", EN_ACIERTO):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 200 and r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
        assert 'content="noindex, follow"' in r.text
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/en/tenis" not in mapa and "xhtml:link" not in mapa


# --- encendido: las páginas -------------------------------------------------------------------------

def test_partido_final_en_ingles_trae_todo_en_el_html(abierto):
    r = abierto.get(EN_ACIERTO, headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    t = r.text
    assert '<html lang="en">' in t and 'property="og:locale" content="en_US"' in t
    assert f'<link rel="canonical" href="{BASE}{EN_ACIERTO}">' in t
    assert 'name="robots" content="index, follow' in t
    assert "<title>Viktorija Golubic vs Katie Boulter: prediction and result WTA Hong Kong, Nov 8, 2026 | QuantFut</title>" in t
    assert t.count("<h1>") == 1
    txt = visible(t)
    assert "The model gives Katie Boulter a 57% chance of winning against Viktorija Golubic, who has 43%." in txt
    assert "Final: Katie Boulter won 0-2 in sets (Viktorija Golubic 0, Katie Boulter 2)." in txt
    assert "The player with the higher probability (Katie Boulter) won." in txt
    assert "Probability error (Brier) in this match: 0.184" in txt
    assert "Match winner" in txt and "Total games" in txt and "Over 18.5" in txt and "Over 21.5" in txt
    assert "Hit" in txt and "Miss" in txt and "hard court" in txt
    assert "No bookmaker odds are published for these markets" in txt
    assert '"inLanguage": "en"' in t or '"inLanguage":"en"' in t


def test_fallo_del_favorito_se_dice_igual_en_ingles(abierto):
    txt = visible(abierto.get(EN_FALLO, headers=HTML).text)
    assert "The forecast missed: the player with the higher probability was Alexandra Eala and Claire Liu won." in txt


def test_trampa_del_mercado_no_se_anuncia_como_acierto(abierto):
    txt = visible(abierto.get(EN_TRAMPA, headers=HTML).text)
    assert "Result under review." in txt and "neither a hit nor a miss" in txt
    assert "The forecast missed" not in txt and "The player with the higher probability" not in txt


def test_partido_previo_cancelado_y_walkover(abierto):
    assert "Before the match." in visible(abierto.get(EN_PREVIA, headers=HTML).text)
    assert "Cancelled." in visible(abierto.get(EN_CANCELADO, headers=HTML).text)
    assert "Finished without a complete result." in visible(abierto.get(EN_WALKOVER, headers=HTML).text)


def test_sin_pronostico_o_inexistente_da_404_y_motor_caido_da_503(abierto, monkeypatch):
    assert abierto.get("/en/tenis/atp-stockholm/nadie-vs-nadie-2026-11-08/", headers=HTML).status_code == 404
    assert abierto.get("/en/tenis/v2/algo/", headers=HTML).status_code == 404

    def roto(*a, **k):
        raise tenis_datos.TenisNoDisponible("caído")
    monkeypatch.setattr(tenis_datos, "eventos", roto)
    monkeypatch.setattr(tenis_datos, "ventana", roto)
    r = abierto.get("/en/tenis/", headers=HTML)
    assert r.status_code == 503 and r.headers["retry-after"] == "60"


def test_pilar_en_ingles(abierto):
    r = abierto.get("/en/tenis/", headers=HTML)
    assert r.status_code == 200
    t = r.text
    assert "<title>Tennis predictions: win probabilities for every match | QuantFut</title>" in t
    txt = visible(t)
    assert "Matches on November 8, 2026" in txt
    assert f'href="{EN_ACIERTO}"' in t and f'href="{EN_FALLO}"' in t
    assert "Katie Boulter won 0-2 in sets" in txt and "the favorite won" in txt and "the favorite lost" in txt
    assert "result under review" in txt and "cancelled" in txt
    assert "finished without a complete result (retirement or walkover)" in txt
    assert "1 match on this list has the result under review" in txt


def test_sin_barra_redirige_a_la_canonica(abierto):
    r = abierto.get(EN_ACIERTO.rstrip("/") + "?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}{EN_ACIERTO}?x=1"
    assert abierto.get("/en/tenis").headers["location"] == f"{BASE}/en/tenis/"


# --- mismo dato que el español ------------------------------------------------------------------------

def test_las_dos_versiones_dicen_lo_mismo():
    es, en = tenis_paginas.construir_pilar(AHORA, eventos=list(EVENTOS)), tenis_en.construir_pilar(AHORA, eventos=list(EVENTOS))
    assert (es.aciertos, es.juzgados, es.en_revision, es.total) == (en.aciertos, en.juzgados, en.en_revision, en.total)
    for dia_es, dia_en in zip(es.dias, en.dias):
        assert dia_es["iso"] == dia_en["iso"]
        for (torneo_es, filas_es), (torneo_en, filas_en) in zip(dia_es["torneos"], dia_en["torneos"]):
            assert torneo_es == torneo_en
            for a, b in zip(filas_es, filas_en):
                assert (a["estado"], a["sets"], a["ganador"]) == (b["estado"], b["sets"], b["ganador"])
                assert (a["veredicto"] or {}).get("acerto") == (b["veredicto"] or {}).get("acerto")
                assert b["url"] == "/en" + a["url"]
    for ev in EVENTOS:
        if tenis_paginas.mercado_ganador(ev):
            c_es, c_en = tenis_paginas.construir(ev, AHORA), tenis_en.construir(ev, AHORA)
            assert (c_es.estado, c_es.hash, c_es.favorito) == (c_en.estado, c_en.hash, c_en.favorito)
            assert c_es.p_fav.replace(" ", "") == c_en.p_fav and c_es.p_otro.replace(" ", "") == c_en.p_otro
            assert c_es.resultado["coherente"] == c_en.resultado["coherente"]


# --- hreflang y selector -----------------------------------------------------------------------------

def test_hreflang_reciproco_con_x_default(abierto):
    raiz = ET.fromstring(abierto.get("/sitemap-paginas.xml").content)
    mapa = {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}
    for ruta in ("/tenis/", U_ACIERTO, U_FALLO, U_PREVIA):
        es, en = BASE + ruta, BASE + "/en" + ruta
        assert es in mapa and en in mapa, ruta
        esperado = {"es": es, "en": en, "x-default": es}
        assert mapa[es] == esperado and mapa[en] == esperado, ruta
    for loc in mapa:
        if "/en/tenis" in loc:
            assert loc.replace("/en/tenis", "/tenis") in mapa


def test_selector_de_idioma_en_las_paginas_inglesas_de_tenis(abierto):
    assert f'<a href="{U_ACIERTO}" hreflang="es" lang="es">Español</a>' in abierto.get(EN_ACIERTO, headers=HTML).text
    assert '<a href="/tenis/" hreflang="es" lang="es">Español</a>' in abierto.get("/en/tenis/", headers=HTML).text


# --- está en inglés ------------------------------------------------------------------------------------

@pytest.mark.parametrize("ruta", ["/en/tenis/", EN_ACIERTO, EN_FALLO, EN_TRAMPA, EN_PREVIA])
def test_el_texto_no_trae_espanol_y_los_enlaces_son_ingleses_o_estan_marcados(abierto, ruta):
    t = abierto.get(ruta, headers=HTML).text
    txt = visible(t)
    sin_nombres = re.sub(r"montes-de la torre", " ", txt.lower())     # nombre propio de jugador
    assert PALABRAS_ES.findall(sin_nombres) == [], PALABRAS_ES.findall(sin_nombres)[:8]
    assert not re.search(r"[áéíóúñ¿¡]", txt.lower())
    for etiqueta in re.findall(r"<a\b[^>]*>", t):
        m = re.search(r'href="([^"]+)"', etiqueta)
        href = (m.group(1) if m else "").split("#")[0]
        if not href.startswith("/") or href.startswith("//"):
            continue
        assert href.startswith("/en/") or href.startswith("/nba/v1/") or href in ("/", "") or 'lang="es"' in etiqueta, etiqueta
    for prohibido in ("sure bet", "easy money", "risk-free"):
        assert prohibido not in txt.lower()
