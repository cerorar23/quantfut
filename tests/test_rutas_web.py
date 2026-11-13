"""F1.2b del plan SEO: secciones con URL propia sobre el index.html de la SPA. Sin Redis ni base."""
import json
import logging
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from qf.api import main, og, paginas, ratelimit, rutas_web, seo

BASE = "https://pronosticosdeportivos.pro"
HTML = {"accept": "text/html,application/xhtml+xml"}
FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
SECCIONES = pytest.mark.parametrize("sec", rutas_web.SECCIONES, ids=lambda s: s.ruta)


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


class Doc(HTMLParser):
    def __init__(self, texto):
        super().__init__()
        self.metas, self.links, self.hrefs, self.srcs, self.ld, self.titles = [], [], [], [], [], []
        self.h1, self.html_attrs, self._tag, self._buf, self._en_app = [], {}, None, "", 0
        self.app_html_tags = []
        self.feed(texto)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.html_attrs = a
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
            if a.get("href"):
                self.hrefs.append(a["href"])
        elif tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        if a.get("src"):
            self.srcs.append(a["src"])
        if tag == "div" and a.get("id") == "app":
            self._en_app = 1
        elif self._en_app:
            self.app_html_tags.append(tag)
        self._tag = tag
        if tag == "script" and a.get("type") == "application/ld+json":
            self._buf = ""

    def handle_data(self, data):
        if self._tag == "title":
            self.titles.append(data)
        elif self._tag == "h1":
            self.h1.append(data)
        elif self._tag == "script":
            self._buf += data

    def handle_endtag(self, tag):
        if tag == "script" and self._buf.strip():
            self.ld.append(json.loads(self._buf))
            self._buf = ""
        self._tag = None

    def meta(self, clave, atributo="name"):
        return [m.get("content") for m in self.metas if m.get(atributo) == clave]


def pagina(client, sec):
    r = client.get(sec.path, headers=HTML)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html"), sec.path
    return r, Doc(r.text)


# --- cada sección ----------------------------------------------------------------------------------

@SECCIONES
def test_head_propio_completo_y_sin_duplicados(client, sec):
    r, d = pagina(client, sec)
    url = BASE + sec.path
    assert d.titles == [f"{sec.titulo} | QuantFut"]
    assert d.meta("description") == [sec.descripcion] and 110 <= len(sec.descripcion) <= 160
    assert [l["href"] for l in d.links if l.get("rel") == "canonical"] == [url]
    robots = d.meta("robots")
    assert len(robots) == 1 and robots[0].startswith("index, follow") and "max-image-preview:large" in robots[0]
    assert d.meta("og:url", "property") == [url] and d.meta("og:title", "property") == [f"{sec.titulo} | QuantFut"]
    assert d.meta("og:locale", "property") == ["es_ES"] and d.meta("twitter:card") == (["summary_large_image"] if og.disponible() else ["summary"])
    assert d.html_attrs["lang"] == "es" and d.html_attrs["data-ruta"] == sec.ruta
    assert "x-robots-tag" not in r.headers


@SECCIONES
def test_datos_estructurados_validos(client, sec):
    _, d = pagina(client, sec)
    tipos = [b["@type"] for b in d.ld]
    if sec.ruta == "inicio":
        assert tipos == ["WebSite", "Organization"]
        org = next(b for b in d.ld if b["@type"] == "Organization")
        assert org["legalName"] == "Saptain LTD"
        assert org["contactPoint"] == {
            "@type": "ContactPoint",
            "contactType": "customer support",
            "email": "admin@pronosticosdeportivos.pro",
        }
    else:
        migas = d.ld[0]["itemListElement"]
        assert tipos == ["BreadcrumbList"] and [i["position"] for i in migas] == [1, 2]
        assert migas[1]["item"] == BASE + sec.path and migas[1]["name"] == sec.migas


@SECCIONES
def test_html_inicial_dentro_de_app_con_titulo_texto_y_enlaces(client, sec):
    r, d = pagina(client, sec)
    assert d.h1 == [sec.h1]
    assert 'id="app"><div class="qf-inicial" data-seo-inicial>' in r.text
    for parrafo in sec.texto:
        assert parrafo.split(".")[0][:40] in r.text
    assert "no una casa de apuestas" in r.text and "mayores de 18" in r.text
    for s in rutas_web.SECCIONES:
        assert f'href="{s.path}"' in r.text, f"{sec.path} no enlaza a {s.path}"
    for p in paginas.PAGINAS:
        assert f'href="{p.ruta}"' in r.text


@SECCIONES
def test_recursos_con_ruta_absoluta_para_que_carguen_desde_una_ruta_anidada(client, sec):
    r, d = pagina(client, sec)
    assert 'href="./' not in r.text and 'src="./' not in r.text
    css = [l["href"] for l in d.links if l.get("rel") == "stylesheet"]
    assert css and all(h.startswith("/") and not h.startswith("//") for h in css), css
    preloads = [l["href"] for l in d.links if l.get("rel") == "modulepreload"]
    assert preloads and all(h.startswith("/") and not h.startswith("//") for h in preloads), preloads
    modulos = [s for s in d.srcs if s.startswith("/app.js")]
    assert len(modulos) == 1
    original = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert len(css) == len(re.findall(r'<link rel="stylesheet"', original)), "se perdió alguna hoja de estilo"
    assert len(preloads) == len(re.findall(r'<link rel="modulepreload"', original)), "se perdió algún modulepreload"


@SECCIONES
def test_la_spa_no_pierde_nada_de_su_index(client, sec):
    r, _ = pagina(client, sec)
    original = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<script type="module" src="/app\.js\?v=[^"]+"></script>', r.text)
    assert 'class="skip-link" href="#main-content"' in r.text       # el enlace «saltar al contenido» sigue ahí
    assert '<meta name="theme-color"' in r.text and '<meta name="viewport"' in r.text
    for marca in ("cybercore.min.css", "styles.css", "conversion.css", "membership.css"):
        assert marca in original and marca in r.text


@SECCIONES
def test_sin_barra_final_redirige_con_301_y_head_funciona(client, sec):
    if sec.path == "/":
        assert client.head("/").status_code == 200
        return
    r = client.get(sec.path.rstrip("/") + "?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}{sec.path}?x=1"
    assert client.head(sec.path).status_code == 200


@SECCIONES
def test_el_snapshot_solo_enlaza_a_paginas_que_existen(client, sec):
    _, d = pagina(client, sec)
    internos = {h for h in d.hrefs if h.startswith("/") and not h.startswith("//")}
    for ruta in sorted(internos):
        assert client.get(ruta, headers=HTML).status_code == 200, f"{sec.path} enlaza a {ruta}"


# --- coherencia entre servidor, cliente y sitemap ---------------------------------------------------

def _bloque(js: str, nombre: str) -> dict:
    cuerpo = re.search(rf"{nombre}\s*=\s*\{{(.*?)\}};", js, re.S).group(1)
    return dict(re.findall(r"(\w+):\s*'([^']*)'", cuerpo))


def test_rutas_js_y_secciones_coinciden():
    js = (FRONTEND / "rutas.js").read_text(encoding="utf-8")
    assert _bloque(js, "export const ROUTE_PATH") == {s.ruta: s.path for s in rutas_web.SECCIONES}


def test_las_rutas_de_las_secciones_existen_en_la_spa():
    app = (FRONTEND / "app.js").read_text(encoding="utf-8")
    titulos = set(re.findall(r"(\w+):\s*'", re.search(r"const routeTitle = \{(.*?)\};", app, re.S).group(1)))
    for s in rutas_web.SECCIONES:
        assert s.ruta in titulos, f"{s.ruta} no es una ruta de app.js"
    assert "import { routeFromLocation, cleanUrl, historyEntry, deporteBoot } from './rutas.js" in app


def test_titulos_y_descripciones_unicos_en_todo_el_sitio():
    titulos = [s.titulo for s in rutas_web.SECCIONES] + [p.titulo for p in paginas.PAGINAS]
    descripciones = [s.descripcion for s in rutas_web.SECCIONES] + [p.descripcion for p in paginas.PAGINAS]
    assert len(set(titulos)) == len(titulos) and len(set(descripciones)) == len(descripciones)
    for s in rutas_web.SECCIONES:
        assert 30 <= len(f"{s.titulo} | QuantFut") <= 66, s.titulo


def test_las_secciones_estan_en_el_mapa_sin_lastmod(client):
    filas = {e.find("s:loc", NS).text: e.find("s:lastmod", NS) for e in
             ET.fromstring(client.get("/sitemap-paginas.xml").text).findall("s:url", NS)}
    for s in rutas_web.SECCIONES:
        assert BASE + s.path in filas, s.path
        assert filas[BASE + s.path] is None, "el HTML inicial no cambia a diario: no se declara lastmod"


def test_ninguna_seccion_hereda_noindex():
    for s in rutas_web.SECCIONES:
        assert seo.primer_segmento(s.path) not in seo.NOINDEX_SEGMENTS, s.path


def test_rutas_js_se_publica_como_javascript(client):
    r = client.get("/rutas.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert r.text == (FRONTEND / "rutas.js").read_text(encoding="utf-8")


def test_las_rutas_con_hash_y_las_privadas_no_cambian(client):
    # cuenta/acceso/pago no tienen URL propia; la API y lo privado no se vuelven páginas.
    for ruta in ("/cuenta/", "/acceso/", "/checkout/"):
        assert client.get(ruta, headers=HTML).status_code in (404,), ruta


# --- robustez ---------------------------------------------------------------------------------------

def test_si_index_html_cambia_se_sirve_sin_adaptar_y_se_avisa(caplog):
    roto = "<html><body><div id='app'></div></body></html>"
    with caplog.at_level(logging.ERROR, logger="qf.api.rutas_web"):
        assert rutas_web.render(rutas_web.SECCIONES[3], BASE, roto) == roto
    assert "no tiene las marcas esperadas" in caplog.text


def test_el_index_real_tiene_las_marcas_que_necesita_rutas_web():
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert re.search(r"<title>.*?</title>", html, re.S) and re.search(r'<meta\s+name="description"[^>]*>', html)
    assert re.search(r"<html\b[^>]*>", html) and '<div id="app"></div>' in html


def test_el_html_escapa_titulos_y_descripciones(monkeypatch):
    mala = rutas_web.Seccion("historial", "/historial/", 'T <script>alert(1)</script>', 'd "q" <b>', 'H "1"',
                             ('p <i>x</i>',), "M")
    html = rutas_web.render(mala, BASE)
    assert "<script>alert(1)</script>" not in html and "<i>x</i>" not in html
    assert "&lt;script&gt;" in html and '"q"' not in html.split('name="description"')[1].split(">")[0]
    ld = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html)
    assert ld and all("<" not in b for b in ld)


DEPORTES = {"nba", "tenis", "futbol"}


def test_toda_ruta_de_la_app_o_es_una_pagina_publica_o_lleva_noindex():
    """Recorre las rutas REALES de la app: una ruta nueva (p. ej. un JSON público) que nadie marque con noindex
    haría fallar esta prueba, en vez de quedar indexable sin que nadie lo note."""
    publicas = {"", "legal", "calibracion", "calculadora-cuota-justa", "verificacion", "en", "pt"} | {p.slug for p in paginas.PAGINAS} | {s.path.strip("/") for s in rutas_web.SECCIONES}
    sueltas = []
    for r in main.app.routes:
        ruta = getattr(r, "path", "")
        primero = ruta.lstrip("/").split("/", 1)[0]
        if "." in primero or "{" in primero:        # archivos (app.js, robots.txt…) y rutas con parámetro en raíz
            continue
        if primero in DEPORTES:
            # Páginas de deporte y API del motor comparten primer segmento: manda el prefijo (`/nba/v1`, `/tenis/v2`…).
            cubierta = any(seo._bajo_prefijo(ruta, q) for q in seo.NOINDEX_PREFIJOS)
            pagina = getattr(r, "name", "").startswith(tuple(f"{d}_" for d in DEPORTES))
            if not (cubierta or pagina):
                sueltas.append(ruta)
        elif primero not in publicas and primero not in seo.NOINDEX_SEGMENTS:
            sueltas.append(ruta)
    assert not sueltas, f"rutas sin noindex ni página pública: {sorted(set(sueltas))}"


def test_ninguna_pagina_publica_comparte_primer_segmento_con_una_ruta_de_api():
    # /alta-probabilidad (JSON) y /alta-probabilidad/ (página) no se pueden distinguir por prefijo.
    publicas = {p.slug for p in paginas.PAGINAS} | {s.path.strip("/") for s in rutas_web.SECCIONES} - {""}
    assert not publicas & seo.NOINDEX_SEGMENTS, publicas & seo.NOINDEX_SEGMENTS


# --- pie global de la SPA (app.js · siteFooter) -----------------------------------------------------

def _pie_de_la_spa() -> str:
    app = (FRONTEND / "app.js").read_text(encoding="utf-8")
    cuerpo = re.search(r"function siteFooter\(\) \{(.*?)\n\}\n", app, re.S)
    assert cuerpo, "app.js ya no define siteFooter()"
    assert "${siteFooter()}</div>" in app, "el shell no pinta el pie"
    return cuerpo.group(1)


def test_el_pie_de_la_spa_enlaza_a_todas_las_paginas_de_confianza_y_lo_legal():
    hrefs = re.findall(r'<a href="([^"]+)"', _pie_de_la_spa())
    esperados = [p.ruta for p in paginas.PAGINAS] + ["/legal/terminos", "/legal/privacidad", "/futbol/", "/nba/", "/tenis/"]
    assert sorted(hrefs) == sorted(esperados), hrefs


def test_los_enlaces_del_pie_existen_en_el_servidor(client):
    for href in re.findall(r'<a href="([^"]+)"', _pie_de_la_spa()):
        assert client.get(href, headers=HTML).status_code == 200, href


def test_el_pie_usa_enlaces_reales_y_lleva_el_aviso_de_edad():
    pie = _pie_de_la_spa()
    # Navegar es siempre un <a href> real (Google puede seguirlo); lo único que no navega es el botón de preferencias.
    assert 'data-route' not in pie
    botones = re.findall(r"<button\b[^>]*>", pie)
    assert len(botones) == 1 and 'data-membership-action="ads-preferences"' in botones[0], botones
    assert "+18" in pie and "no una casa de apuestas" in pie and "no garantiza un resultado" in pie


def test_el_boton_de_preferencias_esta_cableado_hasta_el_aviso_de_medicion():
    membership = (FRONTEND / "membership.js").read_text(encoding="utf-8")
    pixel = (FRONTEND / "meta-pixel.js").read_text(encoding="utf-8")
    assert "export const openPreferences" in pixel
    assert "openPreferences as openAdsPreferences" in membership
    assert re.search(r"case 'ads-preferences':\s*openAdsPreferences\(\)", membership), "membership.js no atiende la acción del botón"
    assert 'data-membership-action="ads-preferences"' in _pie_de_la_spa()


def test_app_y_membership_cargan_el_pixel_con_versiones_nuevas_para_saltar_la_cache():
    # El archivo cambió de contenido: si la versión no cambia, Cloudflare y los navegadores sirven la copia vieja.
    app = (FRONTEND / "app.js").read_text(encoding="utf-8")
    membership = (FRONTEND / "membership.js").read_text(encoding="utf-8")
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert re.search(r"meta-pixel\.js\?v=preferencias-20261108", membership)
    assert "membership.js?v=preferencias-20261108" in app
    assert "app.js?v=generica-20261113" in index and "conversion.css?v=info-20261111" in index
    assert "sports-window.js?v=generica-20261113" in app    # la ventana ya no pisa el partido pedido por la URL mientras carga
    assert "rutas.js?v=generica-20261113" in app    # rutas.js cambió (catálogo de deportes): otra versión para saltar la caché


def test_el_boton_del_pie_tiene_estilo_de_enlace_y_area_tactil():
    css = (FRONTEND / "conversion.css").read_text(encoding="utf-8")
    bloque = css.split(".qf-pie-prefs {", 1)[1].split("}", 1)[0]
    assert "text-decoration: underline" in bloque and "padding: 8px 0" in bloque


def test_la_spa_no_intercepta_los_enlaces_del_pie():
    # El manejador global de clics solo recoge botones y a[data-sport]: un <a href> normal navega de verdad.
    app = (FRONTEND / "app.js").read_text(encoding="utf-8")
    assert "event.target.closest('button, a[data-sport]')" in app


def test_el_pie_tiene_estilo_y_deja_hueco_a_la_barra_movil():
    css = (FRONTEND / "conversion.css").read_text(encoding="utf-8")
    assert ".qf-pie {" in css and "env(safe-area-inset-bottom)" in css.split(".qf-pie {", 1)[1]


def test_el_motor_de_cada_deporte_es_noindex_y_sus_paginas_no():
    from starlette.requests import Request

    def req(path):
        return Request({"type": "http", "method": "GET", "path": path, "query_string": b"",
                        "headers": [(b"host", b"pronosticosdeportivos.pro")]})
    for privado in ("/tenis/v2/cartelera", "/tenis/v2/partido/1", "/tenis/v2", "/nba/v1/cartelera", "/nba/v2/"):
        assert seo.noindex(req(privado)), privado
    for publico in ("/tenis/", "/tenis/atp-finals/sinner-vs-alcaraz-2026-11-12/", "/futbol/",
                    "/futbol/liga-mx/club-queretaro-vs-puebla-2026-11-09/", "/nba/"):
        assert not seo.noindex(req(publico)), publico
