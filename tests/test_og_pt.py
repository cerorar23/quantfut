"""F6.4e: tarjetas para redes en portugués (`/og/pt/…`). Datos simulados como en test_og.py. Las pruebas que dibujan necesitan Pillow."""
import re

import pytest

import test_futbol_paginas as tf
import test_nba_paginas as tn
import test_tenis_paginas as tt
from qf.api import futbol_datos, futbol_paginas, futbol_pt, nba_datos, nba_pt, og, tenis_pt
from test_idiomas import estado  # noqa: F401  (fixture de estados de test_idiomas.py)
from test_og import BASE, HTML, client, con_pillow  # noqa: F401  (cliente con los datos simulados de test_og)

SLUG_FINAL = tn.SLUG_FINAL
FUT_SLUG = "laliga/real-madrid-vs-sevilla-2026-11-08"
TEN_SLUG = "wta-hong-kong/viktorija-golubic-vs-katie-boulter-2026-11-08"


def _partido_nba(slug):
    return next(p for ps in tn.DIAS.values() for p in ps if nba_datos.slug_partido(p) == slug)


# --- textos -------------------------------------------------------------------------------------------

def test_los_textos_tienen_las_mismas_claves_en_los_tres_idiomas():
    assert set(og.TEXTOS["es"]) == set(og.TEXTOS["en"]) == set(og.TEXTOS["pt"])


def test_los_textos_portugueses_son_portugueses():
    assert og.TEXTOS["pt"]["pronostico"] == "PREVISÃO ANTES DO JOGO"
    assert og.TEXTOS["pt"]["acerto"] == "ACERTO" and og.TEXTOS["pt"]["fallo"] == "ERRO"
    assert "Estimativa estatística" in og.TEXTOS["pt"]["aviso"]


# --- tarjetas en portugués (sin dibujar) -----------------------------------------------------------------

def test_tarjeta_nba_en_portugues(monkeypatch):
    monkeypatch.setattr(nba_datos, "estadisticas", lambda *a, **k: None)
    from qf.api import nba_paginas  # noqa: F401
    t = nba_pt.tarjeta(nba_pt.construir(_partido_nba(SLUG_FINAL), tn.AHORA))
    assert t.idioma == "pt" and t.etiqueta == "NBA"
    assert t.contexto == "NBA · 8 de novembro de 2026"
    assert t.marcador == "121 – 127" and t.estado == "final" and t.veredicto == "acerto"
    assert [n for n, _ in t.barra] == ["Chicago Bulls", "Philadelphia 76ers"]


def test_tarjeta_futebol_en_portugues_usa_empate():
    fila = dict(tf.F_FINAL, pron=tf.PRON[tf.F_FINAL["match_id"]])
    t = futbol_pt.tarjeta(futbol_pt.construir(fila, None, {"estadisticas": False, "h2h": False}))
    assert t.idioma == "pt" and t.etiqueta == "FUTEBOL" and t.contexto == "LaLiga · 8 de novembro de 2026"
    assert [n for n, _ in t.barra] == ["Real Madrid", "Empate", "Sevilla"]
    assert t.marcador == "0 – 2" and t.veredicto == "fallo"


def test_tarjeta_tenis_en_portugues():
    t = tenis_pt.tarjeta(tenis_pt.construir(tt.E_ACIERTO, tt.AHORA))
    assert t.idioma == "pt" and t.etiqueta == "TÊNIS" and t.contexto == "WTA Hong Kong · 8 de novembro de 2026"
    assert t.marcador == "0 – 2 em sets" and t.veredicto == "acerto"


# --- rutas y dibujo (con Pillow) ----------------------------------------------------------------------------

@con_pillow
def test_imagen_del_partido_en_portugues_solo_con_el_portugues_abierto(client, estado):  # noqa: F811
    estado("pt=on")
    r = client.get(f"/og/pt/nba/{SLUG_FINAL}-final.jpg")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert client.get(f"/og/pt/nba/{SLUG_FINAL}-previa.jpg").status_code == 404
    assert client.get("/og/pt/nba/no-existe-2026-01-01-final.jpg").status_code == 404


@con_pillow
def test_con_el_portugues_apagado_no_hay_imagenes(client, estado):  # noqa: F811
    estado(None)
    assert client.get(f"/og/pt/nba/{SLUG_FINAL}-final.jpg").status_code == 404
    assert client.get("/og/pt/nba/pilar.jpg").status_code == 404


@con_pillow
def test_imagen_de_futebol_usa_el_segmento_portugues(client, estado):  # noqa: F811
    estado("pt=on")
    r = client.get(f"/og/pt/futebol/{FUT_SLUG}-final.jpg")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert client.get(f"/og/pt/futbol/{FUT_SLUG}-final.jpg").status_code == 404      # el segmento de la URL es «futebol»


@con_pillow
def test_imagen_de_tenis_y_pilares_en_portugues(client, estado):  # noqa: F811
    estado("pt=on")
    assert client.get(f"/og/pt/tenis/{TEN_SLUG}-final.jpg").status_code == 200
    assert client.get("/og/pt/nba/pilar.jpg").status_code == 200
    assert client.get("/og/pt/futebol/pilar.jpg").status_code == 200


@con_pillow
def test_la_pagina_portuguesa_declara_su_imagen_en_portugues(client, estado):  # noqa: F811
    estado("pt=on")
    t = client.get(f"/pt/nba/{SLUG_FINAL}/", headers=HTML).text
    m = re.search(r'property="og:image" content="([^"]+)"', t)
    assert m and m.group(1) == f"{BASE}/og/pt/nba/{SLUG_FINAL}-final.jpg"
    assert f'property="og:image" content="{BASE}/og/pt/nba/pilar.jpg"' in client.get("/pt/nba/", headers=HTML).text
    t = client.get(f"/pt/futebol/{FUT_SLUG}/", headers=HTML).text
    assert f'property="og:image" content="{BASE}/og/pt/futebol/{FUT_SLUG}-final.jpg"' in t


@con_pillow
def test_la_imagen_en_ingles_y_espanol_siguen_igual(client, estado):  # noqa: F811
    estado("pt=on\nen=on")
    assert client.get(f"/og/en/nba/{SLUG_FINAL}-final.jpg").status_code == 200
    assert client.get(f"/og/nba/{SLUG_FINAL}-final.jpg").status_code == 200
