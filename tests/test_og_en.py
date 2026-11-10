"""F6: tarjetas para redes en inglés (`/og/en/…`). Los datos son los de test_og.py (los de cada deporte); las pruebas que dibujan
necesitan Pillow, como las de test_og.py."""
import re

import pytest

import test_futbol_paginas as tf
import test_nba_paginas as tn
import test_tenis_paginas as tt
from qf.api import futbol_en, nba_datos, nba_en, og, tenis_en
from test_idiomas import estado  # noqa: F401  (fixture del archivo de estados)
from test_og import BASE, HTML, client, con_pillow  # noqa: F401  (cliente con los datos simulados de test_og)

SLUG_FINAL = tn.SLUG_FINAL


def _partido_nba(slug):
    return next(p for ps in tn.DIAS.values() for p in ps if nba_datos.slug_partido(p) == slug)


# --- textos: mismas claves en los dos idiomas --------------------------------------------------------

def test_los_textos_tienen_las_mismas_claves_en_los_dos_idiomas():
    assert set(og.TEXTOS["es"]) == set(og.TEXTOS["en"])


def test_los_textos_ingleses_no_traen_acentos_ni_palabras_espanolas():
    for clave, texto in og.TEXTOS["en"].items():
        assert not re.search(r"[áéíóúñ¿¡Á-Ú]", texto), (clave, texto)


# --- tarjetas en inglés (sin dibujar) -----------------------------------------------------------------

def test_tarjeta_nba_en_ingles(monkeypatch):
    monkeypatch.setattr(nba_datos, "estadisticas", lambda *a, **k: None)
    t = nba_en.tarjeta(nba_en.construir(_partido_nba(SLUG_FINAL), tn.AHORA))
    assert t.idioma == "en" and t.etiqueta == "NBA"
    assert t.contexto == "NBA · Nov 8, 2026"
    assert t.marcador == "121 – 127" and t.estado == "final" and t.veredicto == "acerto"
    assert [n for n, _ in t.barra] == ["Chicago Bulls", "Philadelphia 76ers"]


def test_tarjeta_futbol_en_ingles_usa_draw(monkeypatch):
    fila = dict(tf.F_FINAL, pron=tf.PRON[tf.F_FINAL["match_id"]])
    t = futbol_en.tarjeta(futbol_en.construir(fila, None, {"estadisticas": False, "h2h": False}))
    assert t.idioma == "en" and t.etiqueta == "FOOTBALL" and t.contexto == "LaLiga · Nov 8, 2026"
    assert [n for n, _ in t.barra] == ["Real Madrid", "Draw", "Sevilla"]
    assert t.marcador == "0 – 2" and t.veredicto == "fallo"


def test_tarjeta_tenis_en_ingles():
    t = tenis_en.tarjeta(tenis_en.construir(tt.E_ACIERTO, tt.AHORA))
    assert t.idioma == "en" and t.etiqueta == "TENNIS" and t.contexto == "WTA Hong Kong · Nov 8, 2026"
    assert t.marcador == "0 – 2 in sets" and t.veredicto == "acerto"


# --- rutas y dibujo (con Pillow) ----------------------------------------------------------------------

@con_pillow
def test_imagen_del_partido_en_ingles_solo_con_ingles_abierto(client, estado):  # noqa: F811
    estado("en=on")
    r = client.get(f"/og/en/nba/{SLUG_FINAL}-final.jpg")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert client.get(f"/og/en/nba/{SLUG_FINAL}-previa.jpg").status_code == 404          # un estado que el partido no tiene
    assert client.get("/og/en/nba/no-existe-2026-01-01-final.jpg").status_code == 404


@con_pillow
def test_con_el_ingles_apagado_no_hay_imagenes_en_ingles(client, estado):  # noqa: F811
    estado(None)
    assert client.get(f"/og/en/nba/{SLUG_FINAL}-final.jpg").status_code == 404
    assert client.get("/og/en/nba/pilar.jpg").status_code == 404


@con_pillow
def test_pilar_en_ingles(client, estado):  # noqa: F811
    estado("en=on")
    r = client.get("/og/en/nba/pilar.jpg")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"


@con_pillow
def test_la_pagina_inglesa_declara_su_imagen_en_ingles(client, estado):  # noqa: F811
    estado("en=on")
    t = client.get(f"/en/nba/{SLUG_FINAL}/", headers=HTML).text
    m = re.search(r'property="og:image" content="([^"]+)"', t)
    assert m and m.group(1) == f"{BASE}/og/en/nba/{SLUG_FINAL}-final.jpg"
    pilar = client.get("/en/nba/", headers=HTML).text
    assert f'property="og:image" content="{BASE}/og/en/nba/pilar.jpg"' in pilar


@con_pillow
def test_la_imagen_espanola_sigue_igual(client, estado):  # noqa: F811
    estado("en=on")
    assert client.get(f"/og/nba/{SLUG_FINAL}-final.jpg").status_code == 200
    t = client.get(f"/nba/{SLUG_FINAL}/", headers=HTML).text
    assert f"{BASE}/og/nba/{SLUG_FINAL}-final.jpg" in t
