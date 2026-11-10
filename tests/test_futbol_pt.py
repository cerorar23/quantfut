"""F6.4c: fútbol en portugués (`/pt/futebol/` y `/pt/futebol/{competição}/{slug}/`). Datos simulados como en test_futbol_paginas.py."""
import html
import re
import xml.etree.ElementTree as ET

import pytest

from qf.api import futbol_datos, futbol_pt
from test_futbol_paginas import AHORA, BASE, HTML, URL_COPA, URL_FINAL, URL_PREVIA, client  # noqa: F401  (datos y cliente de test_futbol_paginas)
from test_idiomas import estado  # noqa: F401  (fixture de estados de test_idiomas.py)

XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PT_FINAL = "/pt/futebol/" + URL_FINAL.split("/futbol/", 1)[1]
PT_PREVIA = "/pt/futebol/" + URL_PREVIA.split("/futbol/", 1)[1]
PT_COPA = "/pt/futebol/" + URL_COPA.split("/futbol/", 1)[1]
PALABRAS_ES = re.compile(r"\b(los|del|pero|cuando|también|nosotros|pronóstico|pronósticos|probabilidad|partido|ganó|perdió|acertó|falló|usted|aquí)\b")


def visible(texto: str) -> str:
    cuerpo = texto.split('<main id="contenido">', 1)[1].split("</footer>", 1)[0]
    cuerpo = re.sub(r"<a [^>]*lang=\"es\"[^>]*>.*?</a>", " ", cuerpo, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))).strip()


@pytest.fixture
def abierto(client, estado):  # noqa: F811
    estado("pt=on")
    return client


# --- apagado y vista previa -------------------------------------------------------------------------

def test_apagado_futebol_em_portugues_da_404_y_no_esta_en_el_mapa(client, estado):  # noqa: F811
    estado(None)
    for ruta in ("/pt/futebol/", PT_FINAL, "/pt/futebol", PT_FINAL.rstrip("/")):
        assert client.get(ruta, headers=HTML).status_code == 404, ruta
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/pt/futebol" not in mapa
    assert client.get(URL_FINAL, headers=HTML).status_code == 200


def test_vista_previa_no_se_indexa_ni_se_enumera(client, estado):  # noqa: F811
    estado("pt=preview")
    for ruta in ("/pt/futebol/", PT_FINAL):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 200 and r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
        assert 'content="noindex, follow"' in r.text
    assert "/pt/futebol" not in client.get("/sitemap-paginas.xml").text


# --- el partido ------------------------------------------------------------------------------------------

def test_partido_final_en_portugues_trae_todo_en_el_html(abierto):
    r = abierto.get(PT_FINAL, headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    t = r.text
    assert '<html lang="pt-BR">' in t and 'property="og:locale" content="pt_BR"' in t
    assert f'<link rel="canonical" href="{BASE}{PT_FINAL}">' in t
    assert 'name="robots" content="index, follow' in t
    assert "<title>Real Madrid x Sevilla: previsão e resultado LaLiga, 8 de novembro de 2026 | QuantFut</title>" in t
    txt = visible(t)
    assert "O modelo dá ao Real Madrid 62% de probabilidade de vencer, 22% de empate e 16% de vitória de Sevilla." in txt
    assert "Final: Real Madrid 0, Sevilla 2." in txt
    assert "A previsão errou: o resultado mais provável era Real Madrid e o resultado foi Sevilla." in txt
    assert "Brier dos três resultados) neste jogo: 1,138." in txt
    assert "Vitória de Real Madrid (mandante)" in txt and "Vitória de Sevilla (visitante)" in txt
    assert "VVDEV" in txt and "DDEVD" in txt
    assert "2º na LaLiga com 20 pontos" in txt and "9º na LaLiga com 20 pontos" in txt
    assert "Nos últimos 6 confrontos: Real Madrid venceu 3 vezes, houve 2 empates e Sevilla venceu 1 vez, com 2,67 gols por jogo em média." in txt
    assert '"inLanguage": "pt"' in t or '"inLanguage":"pt"' in t


def test_partido_previo_con_modelo_propio(abierto):
    txt = visible(abierto.get(PT_PREVIA, headers=HTML).text)
    assert "O modelo dá ao Club Queretaro 50% de probabilidade de vencer, 26% de empate e 23% de vitória de Puebla." in txt
    assert "Antes do jogo." in txt and "não pode ser alterada" in txt


def test_partido_previo_con_probabilidades_de_mercado(abierto):
    txt = visible(abierto.get(PT_COPA, headers=HTML).text)
    assert "consenso do mercado sem a margem" in txt
    assert "Inter 48%, empate 27%, Benfica 25%" in txt


def test_sin_pronostico_inexistente_y_motor_caido(abierto, monkeypatch):
    assert abierto.get("/pt/futebol/liga-mx/guadalajara-vs-pumas-unam-2026-11-09/", headers=HTML).status_code == 404
    assert abierto.get("/pt/futebol/laliga/nao-e-um-jogo/", headers=HTML).status_code == 404

    def roto(*a, **k):
        raise futbol_datos.FutbolNoDisponible("caído")
    monkeypatch.setattr(futbol_datos, "agenda_dia", roto)
    monkeypatch.setattr(futbol_datos, "ventana", roto)
    r = abierto.get("/pt/futebol/", headers=HTML)
    assert r.status_code == 503 and r.headers["retry-after"] == "60"


def test_pilar_em_portugues(abierto):
    r = abierto.get("/pt/futebol/", headers=HTML)
    assert r.status_code == 200
    t = r.text
    assert "<title>Previsões de futebol: probabilidades de cada jogo | QuantFut</title>" in t
    txt = visible(t)
    assert "Jogos de 8 de novembro de 2026" in txt
    assert f'href="{PT_FINAL}"' in t and f'href="{PT_PREVIA}"' in t and f'href="{PT_COPA}"' in t
    assert "Club Queretaro 50%, empate 26%, Puebla 23%" in txt
    assert "final Real Madrid 0, Sevilla 2" in txt and "o resultado mais provável não se confirmou" in txt
    assert "previsão pendente de geração" in txt


def test_sin_barra_redirige(abierto):
    r = abierto.get(PT_FINAL.rstrip("/") + "?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}{PT_FINAL}?x=1"
    assert abierto.get("/pt/futebol").headers["location"] == f"{BASE}/pt/futebol/"


# --- mismo dato que el español ----------------------------------------------------------------------------

def test_las_dos_versiones_dicen_lo_mismo():
    from qf.api import futbol_paginas
    es, pt = futbol_paginas.construir_pilar(AHORA), futbol_pt.construir_pilar(AHORA)
    assert (es.aciertos, es.juzgados, es.con_pronostico) == (pt.aciertos, pt.juzgados, pt.con_pronostico)
    assert [[f["local"] for f in filas] for d in es.dias for _, filas in d["ligas"]] == \
           [[f["local"] for f in filas] for d in pt.dias for _, filas in d["ligas"]]


# --- hreflang y selector -----------------------------------------------------------------------------------

def test_hreflang_reciproco_del_pilar_y_de_los_partidos(abierto):
    raiz = ET.fromstring(abierto.get("/sitemap-paginas.xml").content)
    mapa = {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}
    for es_ruta, pt_ruta in (("/futbol/", "/pt/futebol/"), (URL_FINAL, PT_FINAL), (URL_PREVIA, PT_PREVIA)):
        es, pt = BASE + es_ruta, BASE + pt_ruta
        assert es in mapa and pt in mapa, es_ruta
        assert mapa[es] == {"es": es, "pt": pt, "x-default": es} and mapa[pt] == {"es": es, "pt": pt, "x-default": es}, es_ruta


def test_selector_de_idioma_en_las_paginas_portuguesas(abierto):
    assert f'<a href="{URL_FINAL}" hreflang="es" lang="es">Español</a>' in abierto.get(PT_FINAL, headers=HTML).text
    assert '<a href="/futbol/" hreflang="es" lang="es">Español</a>' in abierto.get("/pt/futebol/", headers=HTML).text


@pytest.mark.parametrize("ruta", ["/pt/futebol/", PT_FINAL, PT_PREVIA, PT_COPA])
def test_el_texto_no_trae_espanol(abierto, ruta):
    txt = visible(abierto.get(ruta, headers=HTML).text)
    assert PALABRAS_ES.findall(txt.lower()) == [], PALABRAS_ES.findall(txt.lower())[:8]
    assert not re.search(r"[ñ¿¡]", txt.lower())
