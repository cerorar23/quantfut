"""F6.2d: páginas de equipo de NBA en inglés (`/en/nba/equipos/{equipo}/`). Datos simulados como en test_nba_equipos.py."""
import html
import re
import xml.etree.ElementTree as ET

import pytest

from qf.api import nba_datos, nba_equipo_en, nba_equipos, nba_paginas
from test_idiomas import estado  # noqa: F401  (fixture del archivo de estados)
from test_nba_equipos import CEL, LAK, client  # noqa: F401  (datos y cliente simulados)
from test_nba_paginas import AHORA, BASE, HTML

XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
EN_CELTICS = "/en/nba/equipos/boston-celtics/"
EN_LAKERS = "/en/nba/equipos/los-angeles-lakers/"
PALABRAS_ES = re.compile(r"\b(el|la|los|las|de|del|que|para|con|una|un|por|se|su|es|más|pero|cuando|esta|este|y|ganó|perdió|acertó|falló)\b")


def visible(texto: str) -> str:
    cuerpo = texto.split('<main id="contenido">', 1)[1].split("</footer>", 1)[0]
    cuerpo = re.sub(r"<a [^>]*lang=\"es\"[^>]*>.*?</a>", " ", cuerpo, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))).strip()


@pytest.fixture
def abierto(client, estado):  # noqa: F811
    estado("en=on")
    return client


def robots(texto):
    m = re.search(r'name="robots" content="([^"]+)"', texto)
    return m.group(1) if m else None


# --- apagado, vista previa y umbral ---------------------------------------------------------------

def test_apagado_da_404_y_no_esta_en_el_mapa(client, estado):  # noqa: F811
    estado(None)
    assert client.get(EN_CELTICS, headers=HTML).status_code == 404
    assert client.get(EN_CELTICS.rstrip("/"), headers=HTML).status_code == 404
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/en/nba/equipos" not in mapa
    assert client.get("/nba/equipos/boston-celtics/", headers=HTML).status_code == 200      # el español, intacto


def test_vista_previa_nunca_se_indexa_aunque_supere_el_umbral(client, estado):  # noqa: F811
    estado("en=preview")
    r = client.get(EN_CELTICS, headers=HTML)
    assert r.status_code == 200 and r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
    assert robots(r.text) == nba_equipos.ROBOTS_BAJO_UMBRAL
    assert "/en/nba/equipos" not in client.get("/sitemap-paginas.xml").text


def test_sobre_el_umbral_es_indexable(abierto):
    r = abierto.get(EN_CELTICS, headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    assert robots(r.text) == nba_equipos.ROBOTS_INDEXABLE
    assert '<html lang="en">' in r.text and f'<link rel="canonical" href="{BASE}{EN_CELTICS}">' in r.text
    assert "<title>Boston Celtics: NBA predictions and how the model has done | QuantFut</title>" in r.text


def test_bajo_el_umbral_existe_pero_con_noindex_y_fuera_del_sitemap(abierto):
    r = abierto.get(EN_LAKERS, headers=HTML)
    assert r.status_code == 200 and robots(r.text) == nba_equipos.ROBOTS_BAJO_UMBRAL
    assert EN_LAKERS not in abierto.get("/sitemap-paginas.xml").text
    assert "too few games" in visible(r.text)


def test_equipo_inexistente_y_sin_barra(abierto):
    assert abierto.get("/en/nba/equipos/nadie/", headers=HTML).status_code == 404
    r = abierto.get("/en/nba/equipos/boston-celtics?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}{EN_CELTICS}?x=1"


def test_nba_caida_es_503(abierto, monkeypatch):
    def roto(*a, **k):
        raise nba_datos.NbaNoDisponible("caído")
    nba_datos.vaciar_cache()
    monkeypatch.setattr(nba_datos, "_pedir", roto)
    r = abierto.get(EN_CELTICS, headers=HTML)
    assert r.status_code == 503 and r.headers["retry-after"] == "60"


# --- las mismas cifras que el español ------------------------------------------------------------------

def test_las_cifras_coinciden_con_el_espanol():
    indice = nba_equipos.indice(nba_datos.hoy_et(AHORA))
    for slug in indice:
        es = nba_equipos.construir(slug, indice, AHORA)
        en = nba_equipo_en.construir(slug, indice, AHORA)
        assert (es.total, es.juzgados, es.aciertos, es.victorias, es.indexable) == (en.total, en.juzgados, en.aciertos, en.victorias, en.indexable)
        assert [f["acerto"] for f in es.filas] == [f["acerto"] for f in en.filas]
        assert [f["resultado"] for f in es.filas] == [f["resultado"] for f in en.filas]
        assert [f["p"].replace(" ", "").replace("%", "") for f in es.filas] == [f["p"].replace("%", "") for f in en.filas]


# --- sitemap, hreflang y selector ----------------------------------------------------------------------

def test_sitemap_solo_los_indexables_y_hreflang_reciproco(abierto):
    raiz = ET.fromstring(abierto.get("/sitemap-paginas.xml").content)
    mapa = {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}
    assert BASE + EN_CELTICS in mapa and BASE + "/nba/equipos/boston-celtics/" in mapa
    assert BASE + EN_LAKERS not in mapa and BASE + "/nba/equipos/los-angeles-lakers/" not in mapa
    es, en = BASE + "/nba/equipos/boston-celtics/", BASE + EN_CELTICS
    assert mapa[es] == {"es": es, "en": en, "x-default": es} and mapa[en] == {"es": es, "en": en, "x-default": es}


def test_selector_de_idioma(abierto):
    t = abierto.get(EN_CELTICS, headers=HTML).text
    assert '<a href="/nba/equipos/boston-celtics/" hreflang="es" lang="es">Español</a>' in t


# --- inglés de verdad ---------------------------------------------------------------------------------

def test_el_texto_no_trae_espanol_y_los_enlaces_son_ingleses_o_estan_marcados(abierto):
    t = abierto.get(EN_CELTICS, headers=HTML).text
    txt = visible(t)
    assert "hit" in txt and "miss" in txt and "Next game with a forecast" in txt and "Latest games" in txt
    assert "Situation at the last game" in txt and ("winning streak" in txt or "losing streak" in txt)
    sin_nombres = re.sub(r"los angeles lakers|boston celtics|miami heat", " ", txt.lower())
    assert PALABRAS_ES.findall(sin_nombres) == [], PALABRAS_ES.findall(sin_nombres)[:8]
    for etiqueta in re.findall(r"<a\b[^>]*>", t):
        m = re.search(r'href="([^"]+)"', etiqueta)
        href = (m.group(1) if m else "").split("#")[0]
        if not href.startswith("/") or href.startswith("//"):
            continue
        assert href.startswith("/en/") or href == "/" or 'lang="es"' in etiqueta, etiqueta
