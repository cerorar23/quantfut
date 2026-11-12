"""Fase 2 «Web y App», parte C: el estado web del catálogo gobierna las páginas SSR, el `sitemap` y los `hreflang`.

`off` → 404 y fuera del mapa; `preview` → 200 con `X-Robots-Tag: noindex` y fuera del mapa; `on` (la semilla) → como siempre.
Los datos de los motores se simulan como en test_nba_paginas.py, test_futbol_paginas.py y test_tenis_paginas.py.
"""
import copy

import pytest
from fastapi.testclient import TestClient

from qf.api import fichas, futbol_datos, futbol_paginas, main, nba_datos, nba_paginas, ratelimit, seo, tenis_datos, tenis_paginas
from qf.comercial import catalogo
from qf.comercial.catalogo_semilla import SEMILLA
import test_futbol_paginas as tf
import test_nba_paginas as tn
import test_tenis_paginas as tt
from test_idiomas import estado  # noqa: F401  (fixture del archivo de idiomas)

BASE = "https://pronosticosdeportivos.pro"
HTML = {"accept": "text/html,application/xhtml+xml"}
# pilar en es, en y pt; coinciden con el trozo de URL que identifica al deporte en el mapa
PILARES = {
    "futbol": ("/futbol/", "/en/futbol/", "/pt/futebol/"),
    "nba": ("/nba/", "/en/nba/", "/pt/nba/"),
    "tenis": ("/tenis/", "/en/tenis/", "/pt/tenis/"),
}


@pytest.fixture
def web(monkeypatch, estado):  # noqa: F811
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    estado("en=on\npt=on")
    # fútbol
    monkeypatch.setattr(futbol_paginas, "_ahora", lambda: tf.AHORA)
    monkeypatch.setattr(futbol_datos, "hoy_mx", lambda ahora=None: tf.AHORA.astimezone(futbol_datos.MEXICO).date())
    fichas._cache.clear()
    monkeypatch.setattr(futbol_datos, "agenda_dia", lambda d: tf.FILAS.get(d.isoformat(), []))
    monkeypatch.setattr(futbol_datos, "pronosticos", lambda ids: {i: tf.PRON[i] for i in ids if i in tf.PRON})
    monkeypatch.setattr(futbol_datos, "secciones_activas", lambda: {"estadisticas": True, "h2h": True})
    # NBA
    monkeypatch.setattr(nba_paginas, "_ahora", lambda: tn.AHORA)
    nba_datos.vaciar_cache()

    def falso(ruta, params=None):
        if ruta == "/nba/v1/cartelera":
            return {"fecha": params["fecha"], "partidos": tn.DIAS.get(params["fecha"], [])}
        raise nba_datos.NbaNoDisponible("sin estadísticas")
    monkeypatch.setattr(nba_datos, "_pedir", falso)
    # tenis
    monkeypatch.setattr(tenis_paginas, "_ahora", lambda: tt.AHORA)
    monkeypatch.setattr(tenis_datos, "hoy_utc", lambda ahora=None: tt.HOY)
    monkeypatch.setattr(tenis_datos, "eventos", lambda: list(tt.EVENTOS))
    yield TestClient(main.app, base_url=BASE, follow_redirects=False)
    nba_datos.vaciar_cache()


def _poner(monkeypatch, cat):
    monkeypatch.setattr(catalogo, "_cargar", lambda: catalogo._ordenar(copy.deepcopy(cat)))
    catalogo.invalidar_cache()


def fijar(monkeypatch, **estados):
    """Catálogo = la semilla con el estado web indicado por deporte (`fijar(mp, nba='off')`)."""
    cat = copy.deepcopy(list(SEMILLA))
    for d in cat:
        d["estado_web"] = estados.get(d["deporte_id"], d["estado_web"])
    _poner(monkeypatch, cat)


def mapa(client):
    return client.get("/sitemap-paginas.xml").text


def menciona(texto, trozo):
    """`<loc>` o `<xhtml:link>` del mapa que apuntan a una URL con `trozo`."""
    return [t for t in texto.split("<") if trozo in t and (t.startswith("loc>") or t.startswith("xhtml:link"))]


@pytest.mark.parametrize("deporte", list(PILARES))
def test_off_da_404_en_es_en_y_pt_y_sale_del_mapa_y_de_los_hreflang(web, monkeypatch, deporte):
    fijar(monkeypatch, **{deporte: "off"})
    for ruta in PILARES[deporte]:
        assert web.get(ruta, headers=HTML).status_code == 404, ruta
        assert web.get(ruta.rstrip("/"), headers=HTML).status_code == 404, ruta
    texto = mapa(web)
    for trozo in PILARES[deporte]:
        assert not menciona(texto, trozo), trozo
    for otro in (d for d in PILARES if d != deporte):      # los otros dos deportes siguen en el mapa
        assert menciona(texto, PILARES[otro][0])


@pytest.mark.parametrize("deporte", list(PILARES))
def test_preview_responde_con_noindex_y_no_entra_en_el_mapa(web, monkeypatch, deporte):
    fijar(monkeypatch, **{deporte: "preview"})
    for ruta in PILARES[deporte]:
        r = web.get(ruta, headers=HTML)
        assert r.status_code == 200, ruta
        assert r.headers["x-robots-tag"] == "noindex", ruta
    texto = mapa(web)
    for trozo in PILARES[deporte]:
        assert not menciona(texto, trozo), trozo


@pytest.mark.parametrize("deporte", list(PILARES))
def test_on_es_como_siempre(web, deporte):
    for ruta in PILARES[deporte]:
        r = web.get(ruta, headers=HTML)
        assert r.status_code == 200 and "x-robots-tag" not in r.headers, ruta
    texto = mapa(web)
    assert f"<loc>{BASE}{PILARES[deporte][0]}</loc>" in texto
    assert f'hreflang="en" href="{BASE}{PILARES[deporte][1]}"' in texto


def test_off_no_toca_la_api_de_los_motores(web, monkeypatch):
    fijar(monkeypatch, futbol="off", nba="off", tenis="off")
    assert web.get("/health").status_code == 200
    # solo las páginas públicas llevan la dependencia del catálogo; ninguna ruta de API ni de los motores
    con_dep = []
    for r in main.app.routes:
        dep = getattr(r, "dependant", None)
        if dep and any("exigir_web" in getattr(d.call, "__qualname__", "") for d in dep.dependencies):
            con_dep.append(r.path)
    assert con_dep
    prohibidos = seo.NOINDEX_PREFIJOS + ("/mobile/v1", "/web", "/cliente", "/app")
    for p in con_dep:
        assert not any(seo._bajo_prefijo(p, q) for q in prohibidos), p


def test_con_todo_on_el_mapa_es_el_de_siempre(web):
    from qf.api import (calibracion, cuota_justa, futbol_en, futbol_pt, legal, nba_en, nba_equipo_en, nba_equipo_pt,
                        nba_equipos, nba_pt, paginas, rutas_web, tenis_en, tenis_pt, verificacion)
    antes = (seo.PAGINAS + rutas_web.entradas_sitemap() + paginas.entradas_sitemap() + legal.entradas_sitemap()
             + nba_paginas.entradas_sitemap() + calibracion.entradas_sitemap() + cuota_justa.entradas_sitemap()
             + verificacion.entradas_sitemap() + nba_equipos.entradas_sitemap() + nba_en.entradas_sitemap()
             + futbol_en.entradas_sitemap() + tenis_en.entradas_sitemap() + nba_equipo_en.entradas_sitemap()
             + nba_pt.entradas_sitemap() + nba_equipo_pt.entradas_sitemap() + futbol_pt.entradas_sitemap()
             + tenis_pt.entradas_sitemap() + futbol_paginas.entradas_sitemap() + tenis_paginas.entradas_sitemap())
    assert seo.todas_las_paginas() == antes


# ── ruta genérica /{slug}/ ───────────────────────────────────────────────────

def con_hockey(monkeypatch, estado_web):
    cat = copy.deepcopy(list(SEMILLA))
    h = copy.deepcopy(cat[1])
    h.update(deporte_id="hockey", adaptador=None, orden=4, estado_web=estado_web, estado_app="off",
             nombre={k: "Hockey" for k in h["nombre"]}, slug={"es": "hockey", "en": "hockey", "pt": "hoquei"}, familias=[])
    _poner(monkeypatch, cat + [h])


def test_deporte_sin_ssr_se_sirve_como_spa_salvo_que_este_off(web, monkeypatch):
    con_hockey(monkeypatch, "on")
    r = web.get("/hockey/", headers=HTML)
    assert r.status_code == 200 and 'data-deporte="hockey"' in r.text and r.headers["x-robots-tag"] == "noindex"
    assert "/hockey/" not in mapa(web)
    con_hockey(monkeypatch, "preview")
    assert web.get("/hockey/", headers=HTML).status_code == 200
    con_hockey(monkeypatch, "off")
    assert web.get("/hockey/", headers=HTML).status_code == 404


def test_la_ruta_generica_no_pisa_nada(web, monkeypatch):
    con_hockey(monkeypatch, "on")
    # rutas desconocidas: 404 directo, sin la redirección de barra final que añadiría un `/{slug}/` ordinario
    assert web.get("/no-existe", headers=HTML).status_code == 404
    assert web.get("/no-existe/", headers=HTML).status_code == 404
    for ruta in ("/en/", "/pt/", "/health", "/legal/terminos", "/futbol/", "/nba/", "/tenis/"):
        r = web.get(ruta, headers=HTML)
        assert r.status_code == 200 and 'data-deporte="hockey"' not in r.text, ruta
