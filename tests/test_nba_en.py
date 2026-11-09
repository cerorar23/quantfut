"""F6.2a: NBA en inglés (`/en/nba/` y `/en/nba/{slug}/`). `nba-api` se simula como en test_nba_paginas.py."""
import html
import re
import xml.etree.ElementTree as ET
from datetime import date

import pytest

from qf.api import nba_datos, nba_en, nba_paginas
from test_idiomas import estado  # noqa: F401  (fixture del archivo de estados)
from test_nba_paginas import AHORA, BASE, DIAS, HTML, SLUG_FALLO, SLUG_FINAL, SLUG_PREVIA, SLUG_SIN_SELLO, client  # noqa: F401

XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PALABRAS_ES = re.compile(r"\b(el|la|los|las|de|del|que|para|con|una|un|por|se|su|es|más|pero|cuando|esta|este|y)\b")


def todos():
    return [p for ps in DIAS.values() for p in ps]


def ventana():
    return {date.fromisoformat(k): v for k, v in DIAS.items()}


def visible(texto: str) -> str:
    cuerpo = texto.split('<main id="contenido">', 1)[1].split("</footer>", 1)[0]
    cuerpo = re.sub(r"<a [^>]*lang=\"es\"[^>]*>.*?</a>", " ", cuerpo, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))


@pytest.fixture
def abierto(client, estado):  # noqa: F811
    estado("en=on")
    return client


# --- apagado y vista previa -----------------------------------------------------------------------

def test_apagado_nba_en_ingles_da_404_y_no_esta_en_el_mapa(client, estado):  # noqa: F811
    estado(None)
    for ruta in ("/en/nba/", f"/en/nba/{SLUG_FINAL}/", "/en/nba", f"/en/nba/{SLUG_FINAL}"):
        assert client.get(ruta, headers=HTML).status_code == 404, ruta
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/en/nba" not in mapa and "xhtml:link" not in mapa
    assert client.get(f"/nba/{SLUG_FINAL}/", headers=HTML).status_code == 200      # el español, intacto


def test_preview_nba_en_ingles_no_se_indexa_ni_se_enumera(client, estado):  # noqa: F811
    estado("en=preview")
    for ruta in ("/en/nba/", f"/en/nba/{SLUG_FINAL}/"):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 200 and r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
        assert 'content="noindex, follow"' in r.text
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/en/nba" not in mapa and "xhtml:link" not in mapa


# --- encendido: las páginas -------------------------------------------------------------------------

def test_partido_final_en_ingles_trae_todo_en_el_html(abierto):
    r = abierto.get(f"/en/nba/{SLUG_FINAL}/", headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    t = r.text
    assert '<html lang="en">' in t and 'property="og:locale" content="en_US"' in t
    assert f'<link rel="canonical" href="{BASE}/en/nba/{SLUG_FINAL}/">' in t
    assert 'name="robots" content="index, follow' in t and "og:image" not in t
    assert "<title>Chicago Bulls vs Philadelphia 76ers: prediction and result for Nov 8, 2026 | QuantFut</title>" in t
    assert t.count("<h1>") == 1
    txt = visible(t)
    assert "Chicago Bulls 121, Philadelphia 76ers 127" in txt
    assert "chance of winning" in txt and "37%" in txt and "63%" in txt
    assert "The team with the higher probability (Philadelphia 76ers) won." in txt
    assert "Probability error (Brier) in this game: 0.137" in txt
    assert "6-game losing streak" in txt and "2-game winning streak" in txt and "second game in two nights" in txt and "3 days of rest" in txt
    assert "(home)" in txt and "(away)" in txt and "between -23 and +13 points in 80% of cases" in txt
    assert "/nba/v1/sello/" in t and "Model version: equipo-2.2." in txt
    assert '"inLanguage": "en"' in t or '"inLanguage":"en"' in t


def test_un_fallo_se_dice_igual_en_ingles(abierto):
    txt = visible(abierto.get(f"/en/nba/{SLUG_FALLO}/", headers=HTML).text)
    assert "The forecast missed:" in txt and "the team with the higher probability was Denver Nuggets and Utah Jazz won." in txt


def test_partido_previa_en_ingles(abierto):
    txt = visible(abierto.get(f"/en/nba/{SLUG_PREVIA}/", headers=HTML).text)
    assert "Before the game." in txt and "cannot be changed" in txt and "62%" in txt and "38%" in txt


def test_sin_sello_o_inexistente_da_404_y_motor_caido_da_503(abierto, monkeypatch):
    assert abierto.get(f"/en/nba/{SLUG_SIN_SELLO}/", headers=HTML).status_code == 404
    assert abierto.get("/en/nba/no-es-un-partido/", headers=HTML).status_code == 404

    def roto(ruta, params=None):
        raise nba_datos.NbaNoDisponible("caído")
    nba_datos.vaciar_cache()
    monkeypatch.setattr(nba_datos, "_pedir", roto)
    for ruta in ("/en/nba/", f"/en/nba/{SLUG_FINAL}/"):
        r = abierto.get(ruta, headers=HTML)
        assert r.status_code == 503 and r.headers["retry-after"] == "60"


def test_pilar_en_ingles(abierto):
    r = abierto.get("/en/nba/", headers=HTML)
    assert r.status_code == 200
    t = r.text
    assert "<title>NBA predictions: win probabilities for every game | QuantFut</title>" in t
    txt = visible(t)
    assert "Games on" in txt and "Results for" in txt and "November 8, 2026" in txt and "November 7, 2026" in txt
    assert f'href="/en/nba/{SLUG_FINAL}/"' in t and f'href="/en/nba/{SLUG_PREVIA}/"' in t
    assert SLUG_SIN_SELLO not in t                                               # sin sello no hay enlace
    assert "Miami Heat vs New York Knicks" in txt and "forecast pending seal" in txt
    assert "the favorite won" in txt and "the favorite lost" in txt
    assert "tip-off 23:30 UTC" in txt and "Boston Celtics 62%, Los Angeles Lakers 38%" in txt


def test_sin_barra_redirige_a_la_canonica(abierto):
    r = abierto.get(f"/en/nba/{SLUG_PREVIA}?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}/en/nba/{SLUG_PREVIA}/?x=1"
    assert abierto.get("/en/nba").headers["location"] == f"{BASE}/en/nba/"


# --- mismo dato que el español ------------------------------------------------------------------------

def test_las_dos_versiones_dicen_lo_mismo():
    n = 0
    for p in todos():
        if not p.get("pronostico"):
            continue
        n += 1
        es, en = nba_paginas.construir(p, AHORA), nba_en.construir(p, AHORA)
        assert es.estado == en.estado and es.veredicto == en.veredicto and es.slug == en.slug
        assert es.p_local.replace(" %", "") == en.p_local.rstrip("%") and es.p_visit.replace(" %", "") == en.p_visit.rstrip("%")
        assert es.mu_local.replace(",", ".") == en.mu_local and es.total_mediana == en.total_mediana
        assert es.hash == en.hash and es.version == en.version and len(es.contexto) == len(en.contexto)
        for a, b in zip(es.contexto, en.contexto):
            assert (a["record"], a["ultimos6"], a["nombre"]) == (b["record"], b["ultimos6"], b["nombre"])
    assert n == 3


def test_pilar_mismos_partidos_y_aciertos_que_el_espanol():
    es, en = nba_paginas.construir_pilar(AHORA, ventana=ventana()), nba_en.construir_pilar(AHORA, ventana=ventana())
    assert (es.aciertos, es.juzgados, es.con_pronostico) == (en.aciertos, en.juzgados, en.con_pronostico)
    assert [[f["local"] for f in d["filas"]] for d in es.dias] == [[f["local"] for f in d["filas"]] for d in en.dias]
    assert [[f["url"] for f in d["filas"]] for d in en.dias] == [[("/en" + f["url"] if f["url"] else None) for f in d["filas"]] for d in es.dias]


# --- hreflang y selector -----------------------------------------------------------------------------

def test_hreflang_reciproco_con_x_default_para_el_pilar_y_cada_partido(abierto):
    raiz = ET.fromstring(abierto.get("/sitemap-paginas.xml").content)
    mapa = {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}
    for ruta in ("/nba/", f"/nba/{SLUG_FINAL}/", f"/nba/{SLUG_PREVIA}/", f"/nba/{SLUG_FALLO}/"):
        es, en = BASE + ruta, BASE + "/en" + ruta
        assert es in mapa and en in mapa, ruta
        esperado = {"es": es, "en": en, "x-default": es}
        assert mapa[es] == esperado and mapa[en] == esperado, ruta
    assert BASE + "/en" + f"/nba/{SLUG_SIN_SELLO}/" not in mapa                  # lo que no existe en español no se enumera en inglés
    assert all(not alt for loc, alt in mapa.items() if "/nba/equipos/" in loc)   # sin versión inglesa, sin hreflang
    for loc in mapa:
        if "/en/nba/" in loc:
            assert loc.replace("/en/nba/", "/nba/") in mapa


def test_selector_de_idioma_en_las_paginas_inglesas_de_nba(abierto):
    t = abierto.get(f"/en/nba/{SLUG_FINAL}/", headers=HTML).text
    assert f'<a href="/nba/{SLUG_FINAL}/" hreflang="es" lang="es">Español</a>' in t
    assert '<a href="/nba/" hreflang="es" lang="es">Español</a>' in abierto.get("/en/nba/", headers=HTML).text


# --- está en inglés ------------------------------------------------------------------------------------

@pytest.mark.parametrize("ruta", ["/en/nba/", f"/en/nba/{SLUG_FINAL}/", f"/en/nba/{SLUG_PREVIA}/", f"/en/nba/{SLUG_FALLO}/"])
def test_el_texto_no_trae_espanol_y_los_enlaces_son_ingleses_o_estan_marcados(abierto, ruta):
    t = abierto.get(ruta, headers=HTML).text
    txt = visible(t).replace("Los Angeles", " ")        # nombre propio de equipo
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
