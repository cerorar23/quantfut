"""F6.4d: tênis en portugués (`/pt/tenis/` y `/pt/tenis/{torneo}/{slug}/`). Eventos simulados como en test_tenis_paginas.py."""
import html
import re
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from qf.api import idiomas, main, ratelimit, tenis_datos, tenis_paginas, tenis_pt
from test_idiomas import estado  # noqa: F401  (fixture de estados de test_idiomas.py)
from test_tenis_paginas import (AHORA, BASE, EVENTOS, HOY, HTML, U_ACIERTO, U_CANCELADO, U_FALLO, U_PREVIA, U_TRAMPA, U_WALKOVER)

XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PALABRAS_ES = re.compile(r"\b(los|del|pero|cuando|también|nosotros|pronóstico|pronósticos|probabilidad|partido|ganó|perdió|acertó|falló|usted|aquí)\b")
PT_ACIERTO, PT_FALLO, PT_TRAMPA = "/pt" + U_ACIERTO, "/pt" + U_FALLO, "/pt" + U_TRAMPA
PT_PREVIA, PT_CANCELADO, PT_WALKOVER = "/pt" + U_PREVIA, "/pt" + U_CANCELADO, "/pt" + U_WALKOVER


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
    estado("pt=on")
    return client


# --- apagado y vista previa -------------------------------------------------------------------------

def test_apagado_tenis_em_portugues_da_404_y_no_esta_en_el_mapa(client, estado):  # noqa: F811
    estado(None)
    for ruta in ("/pt/tenis/", PT_ACIERTO, "/pt/tenis", PT_ACIERTO.rstrip("/")):
        assert client.get(ruta, headers=HTML).status_code == 404, ruta
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/pt/tenis" not in mapa
    assert client.get(U_ACIERTO, headers=HTML).status_code == 200


def test_vista_previa_no_se_indexa_ni_se_enumera(client, estado):  # noqa: F811
    estado("pt=preview")
    for ruta in ("/pt/tenis/", PT_ACIERTO):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 200 and r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
        assert 'content="noindex, follow"' in r.text
    assert "/pt/tenis" not in client.get("/sitemap-paginas.xml").text


# --- la partida -------------------------------------------------------------------------------------------

def test_partido_final_en_portugues_trae_todo_en_el_html(abierto):
    r = abierto.get(PT_ACIERTO, headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    t = r.text
    assert '<html lang="pt-BR">' in t and 'property="og:locale" content="pt_BR"' in t
    assert f'<link rel="canonical" href="{BASE}{PT_ACIERTO}">' in t
    assert "<title>Viktorija Golubic x Katie Boulter: previsão e resultado WTA Hong Kong, 8 de novembro de 2026 | QuantFut</title>" in t
    txt = visible(t)
    assert "O modelo dá a Katie Boulter 57% de probabilidade de vencer contra Viktorija Golubic, que tem 43%." in txt
    assert "Final: Katie Boulter venceu por 0-2 em sets (Viktorija Golubic 0, Katie Boulter 2)." in txt
    assert "O jogador com maior probabilidade (Katie Boulter) venceu." in txt
    assert "Erro da probabilidade (Brier) neste jogo: 0,184." in txt
    assert "Vencedor da partida" in txt and "Total de games" in txt and "Mais de 18.5" in txt and "Mais de 21.5" in txt
    assert "Acerto" in txt and "Erro" in txt and "quadra dura" in txt
    assert "Não há odds de casas de apostas publicadas para estes mercados" in txt
    assert '"inLanguage": "pt"' in t or '"inLanguage":"pt"' in t


def test_um_erro_do_favorito_se_diz_igual_em_portugues(abierto):
    txt = visible(abierto.get(PT_FALLO, headers=HTML).text)
    assert "A previsão errou: o jogador com maior probabilidade era Alexandra Eala e venceu Claire Liu." in txt


def test_a_trampa_do_mercado_no_se_anuncia_como_acierto(abierto):
    txt = visible(abierto.get(PT_TRAMPA, headers=HTML).text)
    assert "Resultado em revisão." in txt and "não mostramos acerto nem erro" in txt
    assert "A previsão errou" not in txt and "O jogador com maior probabilidade" not in txt


def test_previa_cancelada_y_walkover(abierto):
    assert "Antes da partida." in visible(abierto.get(PT_PREVIA, headers=HTML).text)
    assert "Cancelado." in visible(abierto.get(PT_CANCELADO, headers=HTML).text)
    assert "Terminado sem resultado completo." in visible(abierto.get(PT_WALKOVER, headers=HTML).text)


def test_sin_pronostico_inexistente_y_datos_caidos(abierto, monkeypatch):
    assert abierto.get("/pt/tenis/atp-stockholm/ninguem-vs-ninguem-2026-11-08/", headers=HTML).status_code == 404
    assert abierto.get("/pt/tenis/v2/algo/", headers=HTML).status_code == 404

    def roto(*a, **k):
        raise tenis_datos.TenisNoDisponible("caído")
    monkeypatch.setattr(tenis_datos, "eventos", roto)
    monkeypatch.setattr(tenis_datos, "ventana", roto)
    r = abierto.get("/pt/tenis/", headers=HTML)
    assert r.status_code == 503 and r.headers["retry-after"] == "60"


def test_pilar_em_portugues(abierto):
    r = abierto.get("/pt/tenis/", headers=HTML)
    assert r.status_code == 200
    t = r.text
    assert "<title>Previsões de tênis: probabilidade de vitória de cada jogador | QuantFut</title>" in t
    txt = visible(t)
    assert "Partidas de 8 de novembro de 2026" in txt
    assert f'href="{PT_ACIERTO}"' in t and f'href="{PT_FALLO}"' in t
    assert "Katie Boulter venceu por 0-2 em sets" in txt and "o favorito venceu" in txt and "o favorito perdeu" in txt
    assert "Claire Liu venceu por 2-0 em sets" in txt
    assert "resultado em revisão" in txt and "cancelada" in txt
    assert "terminada, sem resultado completo (desistência ou W.O.)" in txt
    assert "Jannik Sinner 54%" in txt
    assert "1 partida da lista tem o resultado em revisão" in txt


def test_sem_barra_redirige(abierto):
    r = abierto.get(PT_ACIERTO.rstrip("/") + "?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}{PT_ACIERTO}?x=1"
    assert abierto.get("/pt/tenis").headers["location"] == f"{BASE}/pt/tenis/"


# --- mismo dato que el español ------------------------------------------------------------------------

def test_las_dos_versiones_dicen_lo_mismo():
    es = tenis_paginas.construir_pilar(AHORA, eventos=list(EVENTOS))
    pt = tenis_pt.construir_pilar(AHORA, eventos=list(EVENTOS))
    assert (es.aciertos, es.juzgados, es.en_revision, es.total) == (pt.aciertos, pt.juzgados, pt.en_revision, pt.total)
    for ev in EVENTOS:
        if tenis_paginas.mercado_ganador(ev):
            c_es, c_pt = tenis_paginas.construir(ev, AHORA), tenis_pt.construir(ev, AHORA)
            assert (c_es.estado, c_es.hash, c_es.favorito) == (c_pt.estado, c_pt.hash, c_pt.favorito)
            assert c_es.p_fav.replace(" ", "") == c_pt.p_fav and c_es.resultado["coherente"] == c_pt.resultado["coherente"]


# --- hreflang y selector ---------------------------------------------------------------------------------

def test_hreflang_reciproco_del_pilar_y_de_partidas(abierto):
    raiz = ET.fromstring(abierto.get("/sitemap-paginas.xml").content)
    mapa = {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}
    for ruta in ("/tenis/", U_ACIERTO, U_FALLO, U_PREVIA):
        es, pt = BASE + ruta, BASE + "/pt" + ruta
        assert es in mapa and pt in mapa, ruta
        assert mapa[es] == {"es": es, "pt": pt, "x-default": es} and mapa[pt] == {"es": es, "pt": pt, "x-default": es}, ruta


def test_selector_de_idioma(abierto):
    assert f'<a href="{U_ACIERTO}" hreflang="es" lang="es">Español</a>' in abierto.get(PT_ACIERTO, headers=HTML).text
    assert '<a href="/tenis/" hreflang="es" lang="es">Español</a>' in abierto.get("/pt/tenis/", headers=HTML).text


@pytest.mark.parametrize("ruta", ["/pt/tenis/", PT_ACIERTO, PT_FALLO, PT_TRAMPA, PT_PREVIA])
def test_el_texto_no_trae_espanol(abierto, ruta):
    txt = visible(abierto.get(ruta, headers=HTML).text)
    assert PALABRAS_ES.findall(txt.lower()) == [], PALABRAS_ES.findall(txt.lower())[:8]
    assert not re.search(r"[ñ¿¡]", txt.lower())
