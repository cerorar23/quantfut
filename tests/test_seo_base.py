"""F1.1 del plan SEO: robots.txt, mapas del sitio, noindex, un solo host y 404 en HTML.
Se prueba la `app` real (middleware y manejador de excepciones incluidos), sin Redis ni base."""
import re
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from qf.api import main, ratelimit, seo

HTML = {"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    return TestClient(main.app, base_url="https://pronosticosdeportivos.pro", follow_redirects=False)


# --- robots.txt ---------------------------------------------------------------------------------

def test_robots_permite_todo_declara_senales_de_ia_y_apunta_al_sitemap(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/plain")
    lineas = r.text.splitlines()
    assert "User-agent: *" in lineas and "Allow: /" in lineas
    assert "Content-Signal: search=yes, ai-input=yes, ai-train=no" in lineas
    assert "Sitemap: https://pronosticosdeportivos.pro/sitemap.xml" in lineas


def test_robots_no_bloquea_lo_que_lleva_noindex(client):
    # Si se bloqueara, Google no rastrearía la URL y nunca vería el noindex.
    assert not any(l.lower().startswith("disallow") and l.split(":", 1)[1].strip() for l in client.get("/robots.txt").text.splitlines())


def test_robots_del_host_api_no_anuncia_sitemap(client):
    r = client.get("/robots.txt", headers={"host": "api.pronosticosdeportivos.pro"})
    assert "Sitemap:" not in r.text and "Allow: /" in r.text


def test_head_funciona_en_robots_y_mapas(client):
    for ruta in ("/robots.txt", "/sitemap.xml", "/sitemap-paginas.xml"):
        assert client.head(ruta).status_code == 200


# --- mapas del sitio ----------------------------------------------------------------------------

def test_indice_de_sitemaps_lista_el_mapa_de_paginas_con_url_absoluta(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200 and "xml" in r.headers["content-type"]
    locs = [e.text for e in ET.fromstring(r.text).findall("s:sitemap/s:loc", NS)]
    assert locs == ["https://pronosticosdeportivos.pro/sitemap-paginas.xml"]


def test_mapa_de_paginas_solo_tiene_urls_reales_absolutas_y_sin_fragmentos(client):
    r = client.get("/sitemap-paginas.xml")
    locs = [e.text for e in ET.fromstring(r.text).findall("s:url/s:loc", NS)]
    assert locs == ["https://pronosticosdeportivos.pro/", "https://pronosticosdeportivos.pro/legal/terminos",
                    "https://pronosticosdeportivos.pro/legal/privacidad"]
    assert all("#" not in u and u.startswith("https://") for u in locs)
    assert "<lastmod>" not in r.text, "sin fecha de cambio verificable no se declara lastmod"


def test_cada_url_del_mapa_responde_200_y_se_puede_indexar(client):
    for ruta, _ in seo.PAGINAS:
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 200, ruta
        assert "x-robots-tag" not in r.headers, f"{ruta} está en el mapa pero lleva noindex"


def test_el_mapa_cabe_en_los_limites_de_google():
    assert len(seo.PAGINAS) <= 50_000


def test_lastmod_solo_si_hay_fecha(monkeypatch, client):
    monkeypatch.setattr(seo, "PAGINAS", (("/", "2026-11-08T10:00:00+00:00"),))
    assert "<lastmod>2026-11-08T10:00:00+00:00</lastmod>" in client.get("/sitemap-paginas.xml").text


def test_public_base_url_fuerza_el_origen(monkeypatch, client):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://ejemplo.test/")
    assert "https://ejemplo.test/sitemap.xml" in client.get("/robots.txt").text


# --- noindex ------------------------------------------------------------------------------------

@pytest.mark.parametrize("base", sorted("/" + x for x in seo.NOINDEX_SEGMENTS))
def test_rutas_privadas_y_de_api_llevan_noindex(client, base):
    # Subruta inexistente: la cabecera la pone el middleware por el primer segmento, sin llegar a ningún
    # handler (varios consultan la base) y sin importar qué responda la ruta real.
    assert client.get(base + "/zz-no-existe").headers.get("x-robots-tag") == "noindex"


@pytest.mark.parametrize("ruta", ["/", "/legal/terminos", "/legal/privacidad", "/robots.txt", "/sitemap.xml"])
def test_paginas_publicas_no_llevan_noindex(client, ruta):
    assert "x-robots-tag" not in client.get(ruta, headers=HTML).headers


def test_el_segmento_se_compara_entero_no_por_prefijo():
    # /picks-del-dia (futura página pública) no puede heredar el noindex de /picks.
    assert seo.primer_segmento("/picks-del-dia/x") == "picks-del-dia"
    assert seo.primer_segmento("/Control/") == "control"
    assert "picks-del-dia" not in seo.NOINDEX_SEGMENTS and "nba-hoy" not in seo.NOINDEX_SEGMENTS


def test_host_api_va_entero_con_noindex_incluida_la_portada(client):
    r = client.get("/", headers={**HTML, "host": "api.pronosticosdeportivos.pro"})
    assert r.headers.get("x-robots-tag") == "noindex"
    r = client.get("/legal/terminos", headers={**HTML, "x-forwarded-host": "api.pronosticosdeportivos.pro"})
    assert r.headers.get("x-robots-tag") == "noindex"


# --- un solo host -------------------------------------------------------------------------------

def test_www_redirige_a_la_raiz_con_301_conservando_ruta_y_consulta(client):
    r = client.get("/legal/terminos?x=1", headers={"host": "www.pronosticosdeportivos.pro"})
    assert r.status_code == 301
    assert r.headers["location"] == "https://pronosticosdeportivos.pro/legal/terminos?x=1"


def test_www_con_post_usa_308_para_no_cambiar_el_metodo(client):
    r = client.post("/app/v1/auth/login", headers={"host": "www.pronosticosdeportivos.pro"})
    assert r.status_code == 308 and r.headers["location"] == "https://pronosticosdeportivos.pro/app/v1/auth/login"


def test_el_dominio_sin_www_no_redirige(client):
    assert client.get("/legal/terminos").status_code == 200


def test_www_se_detecta_tambien_por_x_forwarded_host(client):
    r = client.get("/", headers={"host": "quantfut-api:8000", "x-forwarded-host": "www.pronosticosdeportivos.pro"})
    assert r.status_code == 301


# --- 404 ----------------------------------------------------------------------------------------

def test_404_para_quien_navega_es_una_pagina_html_con_estado_404(client):
    r = client.get("/esta-pagina-no-existe", headers=HTML)
    assert r.status_code == 404 and r.headers["content-type"].startswith("text/html")
    assert 'content="noindex"' in r.text and "Página no encontrada" in r.text
    assert 'href="https://pronosticosdeportivos.pro/"' in r.text
    assert "x-robots-tag" not in r.headers


def test_404_para_clientes_de_la_api_sigue_siendo_json(client):
    for cabeceras in ({}, {"accept": "application/json"}, {"accept": "*/*"}):
        r = client.get("/ruta-que-no-existe", headers=cabeceras)
        assert r.status_code == 404 and r.json() == {"detail": "Not Found"}


@pytest.mark.parametrize("ruta", ["/v1/nada", "/admin/nada", "/control/nada", "/app/v1/nada", "/nba/v1/nada",
                                  "/web/nada", "/picks/nada", "/tenis/v2/nada"])
def test_las_rutas_privadas_no_revelan_nada_ni_con_accept_html(client, ruta):
    r = client.get(ruta, headers=HTML)
    assert r.headers["content-type"].startswith("application/json")
    assert "Página no encontrada" not in r.text


def test_otros_errores_no_cambian(client):
    r = client.post("/legal/terminos", headers=HTML)
    assert r.status_code == 405 and r.headers["content-type"].startswith("application/json")


def test_el_404_html_no_incrusta_nada_de_la_peticion(client):
    r = client.get('/<script>alert(1)</script>', headers=HTML)
    assert r.status_code == 404 and "<script>alert" not in r.text and not re.search(r"alert\(1\)", r.text)
