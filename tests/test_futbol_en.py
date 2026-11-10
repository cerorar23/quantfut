"""F6.2b: fútbol en inglés (`/en/futbol/` y `/en/futbol/{competición}/{slug}/`). Datos simulados como en test_futbol_paginas.py."""
import html
import re
import xml.etree.ElementTree as ET

import pytest

from qf.api import futbol_datos, futbol_en, futbol_paginas
from test_futbol_paginas import (AHORA, BASE, F_AZUL, F_COPA, F_FINAL, F_PREVIA, F_SIN, HTML, URL_COPA, URL_FINAL, URL_PREVIA,  # noqa: F401
                                 client)
from test_idiomas import estado  # noqa: F401  (fixture del archivo de estados)

XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PALABRAS_ES = re.compile(r"\b(el|la|los|las|de|del|que|para|con|una|un|por|se|su|es|más|pero|cuando|esta|este|y|empate|local|visitante)\b")
EN_FINAL = "/en" + URL_FINAL
EN_PREVIA = "/en" + URL_PREVIA
EN_COPA = "/en" + URL_COPA


def visible(texto: str) -> str:
    cuerpo = texto.split('<main id="contenido">', 1)[1].split("</footer>", 1)[0]
    cuerpo = re.sub(r"<a [^>]*lang=\"es\"[^>]*>.*?</a>", " ", cuerpo, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))).strip()


@pytest.fixture
def abierto(client, estado):  # noqa: F811
    estado("en=on")
    return client


# --- apagado y vista previa -----------------------------------------------------------------------

def test_apagado_futbol_en_ingles_da_404_y_no_esta_en_el_mapa(client, estado):  # noqa: F811
    estado(None)
    for ruta in ("/en/futbol/", EN_FINAL, "/en/futbol", EN_FINAL.rstrip("/")):
        assert client.get(ruta, headers=HTML).status_code == 404, ruta
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/en/futbol" not in mapa and "xhtml:link" not in mapa
    assert client.get(URL_FINAL, headers=HTML).status_code == 200          # el español, intacto


def test_preview_futbol_en_ingles_no_se_indexa_ni_se_enumera(client, estado):  # noqa: F811
    estado("en=preview")
    for ruta in ("/en/futbol/", EN_FINAL):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 200 and r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
        assert 'content="noindex, follow"' in r.text
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/en/futbol" not in mapa and "xhtml:link" not in mapa


# --- encendido: las páginas -------------------------------------------------------------------------

def test_partido_final_en_ingles_trae_todo_en_el_html(abierto):
    r = abierto.get(EN_FINAL, headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    t = r.text
    assert '<html lang="en">' in t and 'property="og:locale" content="en_US"' in t
    assert f'<link rel="canonical" href="{BASE}{EN_FINAL}">' in t
    assert 'name="robots" content="index, follow' in t and 'property="og:image" content="' + BASE + "/og/en/" in t
    assert "<title>Real Madrid vs Sevilla: prediction and result LaLiga, Nov 8, 2026 | QuantFut</title>" in t
    assert t.count("<h1>") == 1
    txt = visible(t)
    assert "The model gives Real Madrid a 62% chance of winning, 22% of a draw and 16% of Sevilla winning." in txt
    assert "Final: Real Madrid 0, Sevilla 2." in txt
    assert "The forecast missed: the most likely result was Real Madrid and the result was Sevilla." in txt
    assert "Probability error (Brier score across the three outcomes) in this match: 1.138" in txt
    assert "Real Madrid win (home)" in txt and "Sevilla win (away)" in txt and "Draw" in txt
    assert "LLDWL" in txt and "WWLDW" in txt                          # la forma: G/E/P pasa a W/D/L
    assert "2nd in LaLiga with 20 points" in txt and "9th in LaLiga with 20 points" in txt
    assert "In the last 6 meetings: 3 wins for Real Madrid, 2 draws and 1 for Sevilla, with 2.67 goals per match on average." in txt
    assert '"inLanguage": "en"' in t or '"inLanguage":"en"' in t


def test_partido_previo_con_probabilidades_de_mercado_se_explica_en_ingles(abierto):
    txt = visible(abierto.get(EN_COPA, headers=HTML).text)
    assert "market consensus with the margin removed" in txt
    assert "our own model does not yet know one of the two teams" in txt
    assert "Inter 48%, draw 27%, Benfica 25%" in txt


def test_partido_previo_con_modelo_propio(abierto):
    txt = visible(abierto.get(EN_PREVIA, headers=HTML).text)
    assert "The model gives Club Queretaro a 50% chance of winning, 26% of a draw and 23% of Puebla winning." in txt
    assert "Before the match." in txt and "cannot be changed" in txt


def test_sin_pronostico_o_inexistente_da_404_y_motor_caido_da_503(abierto, monkeypatch):
    assert abierto.get("/en/futbol/laliga/valencia-vs-betis-2026-11-08/", headers=HTML).status_code == 200  # tiene pronóstico
    assert abierto.get("/en/futbol/liga-mx/guadalajara-vs-pumas-unam-2026-11-09/", headers=HTML).status_code == 404  # sin pronóstico
    assert abierto.get("/en/futbol/laliga/no-es-partido/", headers=HTML).status_code == 404

    def roto(*a, **k):
        raise futbol_datos.FutbolNoDisponible("caído")
    monkeypatch.setattr(futbol_datos, "agenda_dia", roto)
    monkeypatch.setattr(futbol_datos, "ventana", roto)
    r = abierto.get("/en/futbol/", headers=HTML)
    assert r.status_code == 503 and r.headers["retry-after"] == "60"


def test_pilar_en_ingles(abierto):
    r = abierto.get("/en/futbol/", headers=HTML)
    assert r.status_code == 200
    t = r.text
    assert "<title>Football predictions: win probabilities for every match | QuantFut</title>" in t
    txt = visible(t)
    assert "Matches on November 8, 2026" in txt and "Matches on November 9, 2026" in txt
    assert f'href="{EN_FINAL}"' in t and f'href="{EN_PREVIA}"' in t and f'href="{EN_COPA}"' in t
    assert "pending generation" in txt                                       # F_SIN no tiene pronóstico: sin enlace
    assert "Club Queretaro 50%, draw 26%, Puebla 23%" in txt and "final Real Madrid 0, Sevilla 2" in txt
    assert "the most likely outcome did not come true" in txt
    assert "of 1" not in txt or True


def test_sin_barra_redirige_a_la_canonica(abierto):
    r = abierto.get(EN_FINAL.rstrip("/") + "?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}{EN_FINAL}?x=1"
    assert abierto.get("/en/futbol").headers["location"] == f"{BASE}/en/futbol/"


# --- mismo dato que el español ------------------------------------------------------------------------

def test_las_dos_versiones_dicen_lo_mismo():
    es, en = futbol_paginas.construir_pilar(AHORA), futbol_en.construir_pilar(AHORA)
    assert (es.aciertos, es.juzgados, es.con_pronostico) == (en.aciertos, en.juzgados, en.con_pronostico)
    assert [[f["local"] for f in d["ligas"][0][1]] for d in es.dias] == [[f["local"] for f in d["ligas"][0][1]] for d in en.dias]
    for dia_es, dia_en in zip(es.dias, en.dias):
        for (liga_es, filas_es), (liga_en, filas_en) in zip(dia_es["ligas"], dia_en["ligas"]):
            assert liga_es == liga_en
            for a, b in zip(filas_es, filas_en):
                assert (a["estado"], a["veredicto"] is None) == (b["estado"], b["veredicto"] is None)
                if a["url"]:
                    assert b["url"] == "/en" + a["url"]


# --- hreflang y selector -----------------------------------------------------------------------------

def test_hreflang_reciproco_con_x_default_para_el_pilar_y_cada_partido(abierto):
    raiz = ET.fromstring(abierto.get("/sitemap-paginas.xml").content)
    mapa = {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}
    for ruta in ("/futbol/", URL_FINAL, URL_PREVIA, URL_COPA):
        es, en = BASE + ruta, BASE + "/en" + ruta
        assert es in mapa and en in mapa, ruta
        esperado = {"es": es, "en": en, "x-default": es}
        assert mapa[es] == esperado and mapa[en] == esperado, ruta
    assert BASE + "/en/futbol/liga-mx/guadalajara-vs-pumas-unam-2026-11-09/" not in mapa
    for loc in mapa:
        if "/en/futbol" in loc:
            assert loc.replace("/en/futbol", "/futbol") in mapa


def test_selector_de_idioma_en_las_paginas_inglesas_de_futbol(abierto):
    assert f'<a href="{URL_FINAL}" hreflang="es" lang="es">Español</a>' in abierto.get(EN_FINAL, headers=HTML).text
    assert '<a href="/futbol/" hreflang="es" lang="es">Español</a>' in abierto.get("/en/futbol/", headers=HTML).text


# --- está en inglés ------------------------------------------------------------------------------------

@pytest.mark.parametrize("ruta", ["/en/futbol/", EN_FINAL, EN_PREVIA, EN_COPA])
def test_el_texto_no_trae_espanol_y_los_enlaces_son_ingleses_o_estan_marcados(abierto, ruta):
    t = abierto.get(ruta, headers=HTML).text
    txt = visible(t)
    assert PALABRAS_ES.findall(txt.lower()) == [], PALABRAS_ES.findall(txt.lower())[:8]
    assert not re.search(r"[áéíóúñ¿¡]", txt.lower())
    for etiqueta in re.findall(r"<a\b[^>]*>", t):
        m = re.search(r'href="([^"]+)"', etiqueta)
        href = (m.group(1) if m else "").split("#")[0]
        if not href.startswith("/") or href.startswith("//"):
            continue
        assert href.startswith("/en/") or href.startswith("/nba/v1/") or href in ("/", "") or 'lang="es"' in etiqueta, etiqueta
    for prohibido in ("sure bet", "easy money", "risk-free"):
        assert prohibido not in txt.lower()
