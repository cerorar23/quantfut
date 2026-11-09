"""F2.3 del plan SEO: tarjetas para redes (`og:image`). Los datos se simulan con los de las pruebas de cada deporte.
Las pruebas que dibujan necesitan Pillow (viene en requirements.txt); sin él se saltan y quedan las que no lo necesitan."""
import importlib.util
import io
import os
import re
import time
from datetime import timezone

import pytest
from fastapi.testclient import TestClient

import test_futbol_paginas as tf
import test_nba_paginas as tn
import test_tenis_paginas as tt
from qf.api import fichas, futbol_datos, futbol_paginas, main, nba_datos, nba_paginas, og, ratelimit, tenis_datos, tenis_paginas
from test_paginas import Doc

HTML = {"accept": "text/html,application/xhtml+xml"}
BASE = "https://pronosticosdeportivos.pro"
hay_pillow = importlib.util.find_spec("PIL") is not None
con_pillow = pytest.mark.skipif(not hay_pillow, reason="Pillow no instalado")


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("OG_DIR", str(tmp_path / "og"))
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(og, "_ultima_limpieza", 0.0)
    # NBA
    monkeypatch.setattr(nba_paginas, "_ahora", lambda: tn.AHORA)
    nba_datos.vaciar_cache()

    def falso(ruta, params=None):
        if ruta == "/nba/v1/cartelera":
            return {"fecha": params["fecha"], "partidos": tn.DIAS.get(params["fecha"], [])}
        raise nba_datos.NbaNoDisponible("sin estadísticas")
    monkeypatch.setattr(nba_datos, "_pedir", falso)
    # Fútbol
    monkeypatch.setattr(futbol_paginas, "_ahora", lambda: tf.AHORA)
    fichas._cache.clear()
    monkeypatch.setattr(futbol_datos, "agenda_dia", lambda d: tf.FILAS.get(d.isoformat(), []))
    monkeypatch.setattr(futbol_datos, "pronosticos", lambda ids: {i: tf.PRON[i] for i in ids if i in tf.PRON})
    monkeypatch.setattr(futbol_datos, "secciones_activas", lambda: {"estadisticas": True, "h2h": True})
    monkeypatch.setattr(futbol_datos, "ficha", lambda mid: None)
    # Tenis
    monkeypatch.setattr(tenis_paginas, "_ahora", lambda: tt.AHORA)
    monkeypatch.setattr(tenis_datos, "hoy_utc", lambda ahora=None: tt.HOY)
    monkeypatch.setattr(tenis_datos, "eventos", lambda: list(tt.EVENTOS))
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


def meta(texto, clave, atributo="property"):
    return [m["content"] for m in Doc(texto).metas if m.get(atributo) == clave]


# --- sin Pillow: nada se rompe ---------------------------------------------------------------------

def test_sin_pillow_las_paginas_no_declaran_imagen_y_la_ruta_da_404(client, monkeypatch):
    monkeypatch.setattr(og, "disponible", lambda: False)
    for ruta in (f"/nba/{tn.SLUG_FINAL}/", tf.URL_FINAL, tt.U_ACIERTO, "/nba/", "/futbol/", "/tenis/", "/", "/historial/", "/metodologia/"):
        t = client.get(ruta, headers=HTML).text
        assert "og:image" not in t and "twitter:image" not in t, ruta
        assert meta(t, "twitter:card", "name") == ["summary"], ruta
    for ruta in ("/og/marca.jpg", "/og/nba/pilar.jpg", f"/og/nba/{tn.SLUG_FINAL}-final.jpg"):
        assert client.get(ruta).status_code == 404, ruta


# --- qué dice cada tarjeta (sin dibujar) ------------------------------------------------------------

def test_la_tarjeta_de_nba_dice_lo_mismo_que_la_pagina():
    p = tn.DIAS["2026-11-08"][0]                                   # Bulls 121 - 127 Sixers; favorito visitante (63 %): acierto
    c = nba_paginas.construir(p, tn.AHORA)
    t = nba_paginas.tarjeta(c)
    assert (t.tipo, t.etiqueta, t.estado, t.marcador, t.veredicto) == ("partido", "NBA", "final", "121 – 127", "acerto")
    assert [n for n, _ in t.barra] == ["Chicago Bulls", "Philadelphia 76ers"] and abs(sum(p for _, p in t.barra) - 1) < 1e-9
    assert nba_paginas.estado_imagen(c) == "final"
    previa = nba_paginas.tarjeta(nba_paginas.construir(tn.DIAS["2026-11-08"][1], tn.AHORA))
    assert previa.estado == "previa" and previa.marcador == "" and previa.veredicto is None
    fallo = nba_paginas.tarjeta(nba_paginas.construir(tn.DIAS["2026-11-07"][0], tn.AHORA))
    assert fallo.estado == "final" and fallo.veredicto == "fallo"            # el fallo también se anuncia


def test_la_tarjeta_de_futbol_lleva_los_tres_resultados():
    fila = {**tf.F_FINAL, "pron": tf.PRON[tf.F_FINAL["match_id"]]}
    c = futbol_paginas.construir(fila, None, {"estadisticas": False, "h2h": False}, tf.AHORA)
    t = futbol_paginas.tarjeta(c)
    assert t.etiqueta == "FÚTBOL" and t.estado == "final" and t.marcador == "0 – 2" and t.veredicto == "fallo"
    assert [n for n, _ in t.barra] == ["Real Madrid", "Empate", "Sevilla"] and "LaLiga" in t.contexto


def test_la_tarjeta_de_tenis_solo_es_final_con_resultado_confirmado():
    ok = tenis_paginas.construir(tt.E_ACIERTO, tt.AHORA)
    assert tenis_paginas.estado_imagen(ok) == "final" and tenis_paginas.tarjeta(ok).marcador == "0 – 2 en sets"
    assert tenis_paginas.tarjeta(ok).veredicto == "acerto"
    revision = tenis_paginas.construir(tt.E_TRAMPA, tt.AHORA)               # ganador y sets no coinciden
    t = tenis_paginas.tarjeta(revision)
    assert tenis_paginas.estado_imagen(revision) == "previa" and t.estado == "previa" and t.marcador == "" and t.veredicto is None
    assert tenis_paginas.estado_imagen(tenis_paginas.construir(tt.E_CANCELADO, tt.AHORA)) == "previa"


def test_las_tarjetas_no_llevan_logotipos_ni_imagenes():
    campos = set(og.Tarjeta.__dataclass_fields__)
    assert not {c for c in campos if re.search(r"escudo|logo|imagen|foto|url", c)}, campos


# --- dibujo ---------------------------------------------------------------------------------------

@con_pillow
def test_renderizar_devuelve_un_jpeg_de_1200x630_ligero():
    from PIL import Image
    t = og.Tarjeta("partido", etiqueta="NBA", local="Chicago Bulls", visitante="Philadelphia 76ers", contexto="NBA · 8 de noviembre de 2026",
                   barra=[("Chicago Bulls", .37), ("Philadelphia 76ers", .63)], estado="final", marcador="121 – 127", veredicto="acerto")
    datos = og.renderizar(t)
    assert datos[:3] == b"\xff\xd8\xff" and len(datos) < 150_000
    img = Image.open(io.BytesIO(datos))
    assert img.size == (1200, 630) and img.format == "JPEG"
    r, g, b = img.getpixel((6, 300))
    assert g > 150 and r < 100                                              # la franja verde de la marca


@con_pillow
def test_nombres_larguisimos_y_caracteres_raros_no_rompen_ni_se_salen():
    from PIL import Image
    largo = "Club Deportivo Universidad Nacional Autónoma de México «Pumas» · Sección Femenil Sub-23 Ñandú Ünal"
    for tipo in ("partido", "pilar", "marca"):
        t = og.Tarjeta(tipo, etiqueta="FÚTBOL", titulo=largo, subtitulo=largo, local=largo, visitante=largo, contexto=largo * 2,
                       barra=[(largo, .2), ("Empate", .3), (largo, .5)], estado="final", marcador="10 – 12", veredicto="fallo")
        assert Image.open(io.BytesIO(og.renderizar(t))).size == (1200, 630)
    d = Image.new("RGB", (10, 10))
    from PIL import ImageDraw
    f, txt = og._ajustar(ImageDraw.Draw(d), largo, 300, 60, 20)
    assert txt.endswith("…") and ImageDraw.Draw(d).textlength(txt, font=f) <= 300 + 1


@con_pillow
def test_la_tarjeta_se_guarda_en_disco_y_la_segunda_vez_no_se_dibuja(client, monkeypatch, tmp_path):
    llamadas = []
    real = og.renderizar
    monkeypatch.setattr(og, "renderizar", lambda t: (llamadas.append(1), real(t))[1])
    ruta = f"/og/nba/{tn.SLUG_FINAL}-final.jpg"
    a = client.get(ruta)
    b = client.get(ruta)
    assert a.status_code == b.status_code == 200 and a.content == b.content and len(llamadas) == 1
    assert (tmp_path / "og").is_dir() and len(list((tmp_path / "og").glob("*.jpg"))) == 1
    assert not list((tmp_path / "og").glob(".*.tmp"))


@con_pillow
def test_se_borran_las_tarjetas_de_mas_de_30_dias(tmp_path, monkeypatch):
    monkeypatch.setattr(og, "_ultima_limpieza", 0.0)
    viejo, nuevo = tmp_path / "viejo.jpg", tmp_path / "nuevo.jpg"
    viejo.write_bytes(b"x"); nuevo.write_bytes(b"x")
    os.utime(viejo, (time.time() - 31 * 86400,) * 2)
    og._limpiar(tmp_path)
    assert not viejo.exists() and nuevo.exists()
    viejo.write_bytes(b"x"); os.utime(viejo, (time.time() - 31 * 86400,) * 2)
    og._limpiar(tmp_path)                                                    # a la hora no vuelve a limpiar
    assert viejo.exists()


# --- rutas ----------------------------------------------------------------------------------------

@con_pillow
def test_la_tarjeta_de_un_partido_responde_un_jpeg_inmutable_y_noindex(client):
    r = client.get(f"/og/nba/{tn.SLUG_FINAL}-final.jpg")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable" and r.headers["x-robots-tag"] == "noindex"
    assert r.content[:3] == b"\xff\xd8\xff"
    for ruta in (tf.URL_FINAL.replace("/futbol/", "/og/futbol/").rstrip("/") + "-final.jpg",
                 tt.U_ACIERTO.replace("/tenis/", "/og/tenis/").rstrip("/") + "-final.jpg",
                 tf.URL_PREVIA.replace("/futbol/", "/og/futbol/").rstrip("/") + "-previa.jpg"):
        assert client.get(ruta).status_code == 200, ruta


@con_pillow
def test_no_se_puede_fabricar_un_estado_que_el_partido_no_tiene(client):
    previa_pedida_como_final = f"/og/nba/{tn.SLUG_PREVIA}-final.jpg"           # el partido aún no terminó
    final_pedida_como_previa = f"/og/nba/{tn.SLUG_FINAL}-previa.jpg"           # ya terminó: esa tarjeta ya no es la suya
    assert client.get(previa_pedida_como_final).status_code == 404
    assert client.get(final_pedida_como_previa).status_code == 404
    en_revision = tt.U_TRAMPA.replace("/tenis/", "/og/tenis/").rstrip("/")     # tenis con ganador y sets que no coinciden
    assert client.get(en_revision + "-final.jpg").status_code == 404
    assert client.get(en_revision + "-previa.jpg").status_code == 200


@con_pillow
def test_sin_pagina_no_hay_tarjeta(client):
    for ruta in (f"/og/nba/{tn.SLUG_SIN_SELLO}-previa.jpg", "/og/nba/equipo-a-vs-equipo-b-2026-11-08-previa.jpg",
                 "/og/futbol/liga-mx/guadalajara-vs-pumas-unam-2026-11-08-previa.jpg", "/og/futbol/laliga/club-queretaro-vs-puebla-2026-11-08-previa.jpg",
                 "/og/tenis/atp-paris/nadie-vs-nada-2026-11-08-previa.jpg", "/og/golf/pilar.jpg", "/og/nba/otra-cosa.jpg",
                 "/og/nba/../../etc/passwd-previa.jpg", "/og/nba/%2e%2e/x-previa.jpg", "/og/nba/a/b/c-previa.jpg",
                 f"/og/nba/{tn.SLUG_FINAL}-final.png", f"/og/futbol/{tn.SLUG_FINAL}-final.jpg"):
        assert client.get(ruta).status_code == 404, ruta


@con_pillow
def test_datos_caidos_dan_503_y_no_una_imagen(client, monkeypatch):
    def roto(ruta, params=None):
        raise nba_datos.NbaNoDisponible("caído")
    nba_datos.vaciar_cache()
    monkeypatch.setattr(nba_datos, "_pedir", roto)
    r = client.get(f"/og/nba/{tn.SLUG_FINAL}-final.jpg")
    assert r.status_code == 503 and r.headers["retry-after"] == "60" and r.headers["cache-control"] == "no-store"


@con_pillow
def test_tarjetas_de_la_marca_y_de_los_pilares(client):
    for ruta in ("/og/marca.jpg", "/og/nba/pilar.jpg", "/og/futbol/pilar.jpg", "/og/tenis/pilar.jpg"):
        r = client.get(ruta)
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and r.headers["cache-control"] == "public, max-age=86400", ruta


# --- las páginas apuntan a su tarjeta -------------------------------------------------------------

@con_pillow
def test_cada_pagina_declara_la_tarjeta_de_su_estado(client):
    casos = [(f"/nba/{tn.SLUG_FINAL}/", f"{BASE}/og/nba/{tn.SLUG_FINAL}-final.jpg"),
             (f"/nba/{tn.SLUG_PREVIA}/", f"{BASE}/og/nba/{tn.SLUG_PREVIA}-previa.jpg"),
             (tf.URL_FINAL, BASE + tf.URL_FINAL.replace("/futbol/", "/og/futbol/").rstrip("/") + "-final.jpg"),
             (tf.URL_PREVIA, BASE + tf.URL_PREVIA.replace("/futbol/", "/og/futbol/").rstrip("/") + "-previa.jpg"),
             (tt.U_ACIERTO, BASE + tt.U_ACIERTO.replace("/tenis/", "/og/tenis/").rstrip("/") + "-final.jpg"),
             (tt.U_TRAMPA, BASE + tt.U_TRAMPA.replace("/tenis/", "/og/tenis/").rstrip("/") + "-previa.jpg"),   # en revisión: no anuncia resultado
             (tt.U_CANCELADO, BASE + tt.U_CANCELADO.replace("/tenis/", "/og/tenis/").rstrip("/") + "-previa.jpg")]
    for ruta, imagen in casos:
        t = client.get(ruta, headers=HTML).text
        assert meta(t, "og:image") == [imagen] and meta(t, "twitter:image", "name") == [imagen], ruta
        assert meta(t, "twitter:card", "name") == ["summary_large_image"], ruta
        assert meta(t, "og:image:width") == ["1200"] and meta(t, "og:image:height") == ["630"] and meta(t, "og:image:type") == ["image/jpeg"]
        assert meta(t, "og:image:alt")[0].startswith("Pronóstico ") and len(meta(t, "og:image")) == 1


@con_pillow
def test_pilares_secciones_portada_y_confianza_llevan_su_tarjeta(client):
    esperado = {"/nba/": "/og/nba/pilar.jpg", "/futbol/": "/og/futbol/pilar.jpg", "/tenis/": "/og/tenis/pilar.jpg",
                "/": "/og/marca.jpg", "/historial/": "/og/marca.jpg", "/planes/": "/og/marca.jpg", "/metodologia/": "/og/marca.jpg",
                "/juego-responsable/": "/og/marca.jpg", "/sobre-nosotros/": "/og/marca.jpg"}
    for ruta, imagen in esperado.items():
        t = client.get(ruta, headers=HTML).text
        assert meta(t, "og:image") == [BASE + imagen], ruta
        assert meta(t, "twitter:card", "name") == ["summary_large_image"], ruta


@con_pillow
def test_las_urls_de_imagen_de_las_paginas_se_pueden_pedir(client):
    """Lo que cada página declara tiene que existir: se piden todas las `og:image` de las páginas reales."""
    for ruta in (f"/nba/{tn.SLUG_FINAL}/", tf.URL_FINAL, tt.U_ACIERTO, "/nba/", "/", "/metodologia/"):
        url = meta(client.get(ruta, headers=HTML).text, "og:image")[0]
        r = client.get(url.replace(BASE, ""))
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg", (ruta, url)


def test_la_fuente_y_su_licencia_estan_en_el_repositorio():
    assert og.FUENTE.is_file() and og.FUENTE.stat().st_size > 100_000
    licencia = (og.FUENTE.parent / "LICENCIA-DejaVu.txt").read_text(encoding="utf-8")
    assert "Bitstream" in licencia and "Permission is hereby granted" in licencia
