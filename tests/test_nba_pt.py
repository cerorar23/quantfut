"""F6.4b: NBA en portugués (`/pt/nba/`, `/pt/nba/{slug}/` y `/pt/nba/equipos/{equipo}/`). Dos conjuntos de datos simulados: los de
test_nba_paginas.py (partidos) y los de test_nba_equipos.py (equipos)."""
import html
import re
import xml.etree.ElementTree as ET
from datetime import date

import pytest

from qf.api import nba_datos, nba_equipo_pt, nba_equipos, nba_paginas, nba_pt
from test_idiomas import estado  # noqa: F401  (fixture de estados de test_idiomas.py)
from test_nba_equipos import client as client_equipos  # noqa: F401  (datos de equipos)
from test_nba_paginas import AHORA, BASE, DIAS, HTML, SLUG_FALLO, SLUG_FINAL, SLUG_PREVIA, SLUG_SIN_SELLO
from test_nba_paginas import client as client_partidos  # noqa: F401  (datos de partidos)

XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PT_FINAL = f"/pt/nba/{SLUG_FINAL}/"
PT_PREVIA = f"/pt/nba/{SLUG_PREVIA}/"
PT_FALLO = f"/pt/nba/{SLUG_FALLO}/"
PALABRAS_ES = re.compile(r"\b(los|del|pero|cuando|también|nosotros|pronóstico|pronósticos|probabilidad|partido|ganó|perdió|acertó|falló|usted|aquí)\b")


def visible(texto: str) -> str:
    cuerpo = texto.split('<main id="contenido">', 1)[1].split("</footer>", 1)[0]
    cuerpo = re.sub(r"<a [^>]*lang=\"es\"[^>]*>.*?</a>", " ", cuerpo, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))).strip()


@pytest.fixture
def abierto(client_partidos, estado):  # noqa: F811
    estado("pt=on")
    return client_partidos


# --- apagado y vista previa -----------------------------------------------------------------------

def test_apagado_nba_en_portugues_da_404_y_no_esta_en_el_mapa(client_partidos, estado):  # noqa: F811
    estado(None)
    for ruta in ("/pt/nba/", PT_FINAL, "/pt/nba", PT_FINAL.rstrip("/")):
        assert client_partidos.get(ruta, headers=HTML).status_code == 404, ruta
    mapa = client_partidos.get("/sitemap-paginas.xml").text
    assert "/pt/nba" not in mapa
    assert client_partidos.get(f"/nba/{SLUG_FINAL}/", headers=HTML).status_code == 200


def test_vista_previa_no_se_indexa_ni_se_enumera(client_partidos, estado):  # noqa: F811
    estado("pt=preview")
    for ruta in ("/pt/nba/", PT_FINAL):
        r = client_partidos.get(ruta, headers=HTML)
        assert r.status_code == 200 and r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
        assert 'content="noindex, follow"' in r.text
    assert "/pt/nba" not in client_partidos.get("/sitemap-paginas.xml").text


# --- las páginas de partido y el pilar --------------------------------------------------------------

def test_partido_final_en_portugues_trae_todo_en_el_html(abierto):
    r = abierto.get(PT_FINAL, headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    t = r.text
    assert '<html lang="pt-BR">' in t and 'property="og:locale" content="pt_BR"' in t
    assert f'<link rel="canonical" href="{BASE}{PT_FINAL}">' in t
    assert 'name="robots" content="index, follow' in t
    assert "<title>Chicago Bulls x Philadelphia 76ers: previsão e resultado, 8 de novembro de 2026 | QuantFut</title>" in t
    txt = visible(t)
    assert "O modelo dá ao Chicago Bulls 37% de probabilidade de vencer e ao Philadelphia 76ers 63%." in txt
    assert "Final: Chicago Bulls 121, Philadelphia 76ers 127." in txt
    assert "A equipe com maior probabilidade (Philadelphia 76ers) venceu." in txt
    assert "Erro da probabilidade (Brier) neste jogo: 0,137." in txt
    assert "sequência de 6 derrotas seguidas" in txt and "sequência de 2 vitórias seguidas" in txt
    assert "segundo jogo em duas noites seguidas" in txt and "3 dias de descanso" in txt
    assert "entre -23 e +13 pontos em 80 % dos casos" in txt
    assert "Versão do modelo: equipo-2.2." in txt
    assert '"inLanguage": "pt"' in t or '"inLanguage":"pt"' in t


def test_um_erro_se_diz_igual_em_portugues(abierto):
    txt = visible(abierto.get(PT_FALLO, headers=HTML).text)
    assert "A previsão errou:" in txt and "venceu o Utah Jazz" in txt


def test_partido_previo_em_portugues(abierto):
    txt = visible(abierto.get(PT_PREVIA, headers=HTML).text)
    assert "Antes do jogo." in txt and "não pode ser alterada" in txt and "62%" in txt and "38%" in txt


def test_sem_selo_inexistente_e_motor_caido(abierto, monkeypatch):
    assert abierto.get(f"/pt/nba/{SLUG_SIN_SELLO}/", headers=HTML).status_code == 404
    assert abierto.get("/pt/nba/no-e-um-jogo/", headers=HTML).status_code == 404

    def roto(ruta, params=None):
        raise nba_datos.NbaNoDisponible("caído")
    nba_datos.vaciar_cache()
    monkeypatch.setattr(nba_datos, "_pedir", roto)
    for ruta in ("/pt/nba/", PT_FINAL):
        r = abierto.get(ruta, headers=HTML)
        assert r.status_code == 503 and r.headers["retry-after"] == "60"


def test_pilar_em_portugues(abierto):
    r = abierto.get("/pt/nba/", headers=HTML)
    assert r.status_code == 200
    t = r.text
    assert "<title>Previsões da NBA: probabilidade de vitória de cada jogo | QuantFut</title>" in t
    txt = visible(t)
    assert "Jogos de 8 de novembro de 2026" in txt and "Resultados de 7 de novembro de 2026" in txt
    assert f'href="{PT_FINAL}"' in t and f'href="{PT_PREVIA}"' in t
    assert SLUG_SIN_SELLO not in t
    assert "Miami Heat x New York Knicks" in txt and "previsão pendente de selo" in txt
    assert "o favorito venceu" in txt and "o favorito perdeu" in txt
    assert "Boston Celtics 62%, Los Angeles Lakers 38%" in txt


def test_sem_barra_redirige(abierto):
    r = abierto.get(PT_PREVIA.rstrip("/") + "?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}{PT_PREVIA}?x=1"
    assert abierto.get("/pt/nba").headers["location"] == f"{BASE}/pt/nba/"


# --- mismo dato que el español --------------------------------------------------------------------

def test_las_dos_versiones_del_partido_dicen_lo_mismo():
    n = 0
    for p in [x for ps in DIAS.values() for x in ps]:
        if not p.get("pronostico"):
            continue
        n += 1
        es, pt = nba_paginas.construir(p, AHORA), nba_pt.construir(p, AHORA)
        assert (es.estado, es.veredicto, es.slug, es.hash, es.version) == (pt.estado, pt.veredicto, pt.slug, pt.hash, pt.version)
        assert es.p_local.replace(" %", "%").replace(" ", "") == pt.p_local
    assert n == 3


def test_pilar_mismos_partidos_y_aciertos_que_el_espanol():
    ventana = {date.fromisoformat(k): v for k, v in DIAS.items()}
    es = nba_paginas.construir_pilar(AHORA, ventana=ventana)
    pt = nba_pt.construir_pilar(AHORA, ventana=ventana)
    assert (es.aciertos, es.juzgados, es.con_pronostico) == (pt.aciertos, pt.juzgados, pt.con_pronostico)
    assert [[f["local"] for f in d["filas"]] for d in es.dias] == [[f["local"] for f in d["filas"]] for d in pt.dias]


# --- equipos ------------------------------------------------------------------------------------------

def test_cifras_de_equipos_como_el_espanol(client_equipos):  # noqa: F811
    indice = nba_equipos.indice(nba_datos.hoy_et(AHORA))
    assert indice, "el índice de equipos no debe estar vacío con los datos simulados"
    for slug in indice:
        es = nba_equipos.construir(slug, indice, AHORA)
        pt = nba_equipo_pt.construir(slug, indice, AHORA)
        assert (es.total, es.juzgados, es.aciertos, es.victorias, es.indexable) == (pt.total, pt.juzgados, pt.aciertos, pt.victorias, pt.indexable)
        assert [f["acerto"] for f in es.filas] == [f["acerto"] for f in pt.filas]


def test_equipo_bajo_umbral_con_noindex_y_fuera_del_mapa(client_equipos, estado):  # noqa: F811
    estado("pt=on")
    r = client_equipos.get("/pt/nba/equipos/los-angeles-lakers/", headers=HTML)
    assert r.status_code == 200 and 'content="noindex, follow"' in r.text
    assert "/pt/nba/equipos/los-angeles-lakers/" not in client_equipos.get("/sitemap-paginas.xml").text
    assert "São poucos jogos" in visible(r.text)


def test_hreflang_reciproco_del_pilar_y_de_un_partido(abierto):
    raiz = ET.fromstring(abierto.get("/sitemap-paginas.xml").content)
    mapa = {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}
    for ruta in ("/nba/", f"/nba/{SLUG_FINAL}/"):
        es, pt = BASE + ruta, BASE + "/pt" + ruta
        assert es in mapa and pt in mapa, ruta
        assert mapa[es] == {"es": es, "pt": pt, "x-default": es} and mapa[pt] == {"es": es, "pt": pt, "x-default": es}, ruta


@pytest.mark.parametrize("ruta", ["/pt/nba/", PT_FINAL, PT_PREVIA, PT_FALLO])
def test_el_texto_no_trae_espanol(abierto, ruta):
    txt = re.sub(r"los angeles", " ", visible(abierto.get(ruta, headers=HTML).text).lower())   # nombre propio de equipo
    assert PALABRAS_ES.findall(txt) == [], PALABRAS_ES.findall(txt)[:8]
    assert not re.search(r"[ñ¿¡]", txt)
