"""F1.2a del plan SEO: páginas públicas con HTML completo desde el servidor (metodología, juego
responsable, sobre nosotros). Sin Redis ni base."""
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from qf.api import main, paginas, ratelimit

HTML = {"accept": "text/html,application/xhtml+xml"}
BASE = "https://pronosticosdeportivos.pro"
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


class Doc(HTMLParser):
    def __init__(self, texto):
        super().__init__()
        self.metas, self.links, self.h1, self.ld, self.hrefs, self.times = [], [], [], [], [], []
        self.title, self._tag, self._buf, self.lang = "", None, "", None
        self.feed(texto)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        elif tag == "time":
            self.times.append(a.get("datetime"))
        self._tag = tag
        if tag == "script" and a.get("type") == "application/ld+json":
            self._buf = ""

    def handle_data(self, data):
        if self._tag == "title":
            self.title += data
        elif self._tag == "h1":
            self.h1.append(data)
        elif self._tag == "script":
            self._buf += data

    def handle_endtag(self, tag):
        if tag == "script" and self._buf.strip():
            self.ld.append(json.loads(self._buf))
            self._buf = ""
        self._tag = None

    def meta(self, clave, valor="name"):
        return next((m.get("content") for m in self.metas if m.get(valor) == clave), None)


def doc(client, pagina):
    r = client.get(pagina.ruta, headers=HTML)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html"), pagina.ruta
    return r, Doc(r.text)


TODAS = pytest.mark.parametrize("pagina", paginas.PAGINAS, ids=lambda p: p.slug)


@TODAS
def test_head_completo_y_correcto(client, pagina):
    r, d = doc(client, pagina)
    url = BASE + pagina.ruta
    assert d.lang == "es"
    assert d.title.endswith(" | QuantFut") and 40 <= len(d.title) <= 65, d.title
    descripcion = d.meta("description")
    assert 120 <= len(descripcion) <= 160, len(descripcion)
    assert '"' not in descripcion
    assert [l["href"] for l in d.links if l.get("rel") == "canonical"] == [url]
    robots = d.meta("robots")
    assert robots.startswith("index, follow") and "max-image-preview:large" in robots and "noindex" not in robots
    assert d.meta("og:url", "property") == url and d.meta("og:type", "property") == "website"
    assert d.meta("og:title", "property") == pagina.titulo and d.meta("og:locale", "property") == "es_ES"
    assert d.meta("twitter:card") == "summary"
    assert "x-robots-tag" not in r.headers


@TODAS
def test_un_solo_h1_y_estructura_navegable(client, pagina):
    r, d = doc(client, pagina)
    assert d.h1 == [pagina.titulo]
    assert len(re.findall(r"<h2", r.text)) >= 3
    assert 'id="contenido"' in r.text and 'href="#contenido"' in r.text      # saltar al contenido


@TODAS
def test_datos_estructurados_validos_con_migas_coherentes(client, pagina):
    _, d = doc(client, pagina)
    migas = next(b for b in d.ld if b["@type"] == "BreadcrumbList")
    items = migas["itemListElement"]
    assert [i["position"] for i in items] == [1, 2]
    assert items[0]["item"] == f"{BASE}/" and items[1]["item"] == BASE + pagina.ruta and items[1]["name"] == pagina.migas
    principal = next(b for b in d.ld if b["@type"] == pagina.tipo_schema)
    assert principal["url"] == BASE + pagina.ruta and principal["inLanguage"] == "es"
    assert principal["dateModified"] == pagina.revision.isoformat()
    assert principal["publisher"]["legalName"] == "Saptain LTD"


@TODAS
def test_la_fecha_del_mapa_es_la_que_ve_la_persona(client, pagina):
    _, d = doc(client, pagina)
    mapa = ET.fromstring(client.get("/sitemap-paginas.xml").text)
    lastmod = {e.find("s:loc", NS).text: getattr(e.find("s:lastmod", NS), "text", None) for e in mapa.findall("s:url", NS)}
    assert d.times == [pagina.revision.isoformat()] == [lastmod[BASE + pagina.ruta]]
    assert paginas.fecha_larga(pagina.revision) in client.get(pagina.ruta).text


@TODAS
def test_la_version_sin_barra_redirige_con_301_a_la_canonica(client, pagina):
    r = client.get(f"/{pagina.slug}?utm=x")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}{pagina.ruta}?utm=x"


@TODAS
def test_head_y_cabeceras_de_seguridad(client, pagina):
    assert client.head(pagina.ruta).status_code == 200
    r = client.get(pagina.ruta)
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["cache-control"] == "public, max-age=300"


@TODAS
def test_todos_los_enlaces_internos_existen(client, pagina):
    _, d = doc(client, pagina)
    internos = {h.split("#")[0] for h in d.hrefs if h.startswith("/")}
    assert {"/", "/legal/terminos", "/legal/privacidad", "/juego-responsable/"} <= internos
    # /chain consulta la base: se comprueba que está enlazada, no se llama.
    for ruta in sorted(internos - {"/chain"}):
        assert client.get(ruta, headers=HTML).status_code == 200, f"{pagina.slug} enlaza a {ruta}, que no responde 200"
    for h in d.hrefs:
        assert not h.startswith(("http://",)), f"enlace sin cifrar: {h}"
        assert not h.startswith("tel:") or re.fullmatch(r"tel:\+\d{8,15}", h), h
        assert not h.startswith("mailto:") or h == "mailto:admin@pronosticosdeportivos.pro", h


@TODAS
def test_pie_con_aviso_de_edad_y_sin_promesas(client, pagina):
    r, _ = doc(client, pagina)
    assert "+18" in r.text and "no una casa de apuestas" in r.text and "no garantiza un resultado" in r.text
    assert not re.search(r"dinero fácil|ganancias? garantizadas?|sin riesgo|apuesta segura|100 ?% de acierto", r.text, re.I)


def test_el_titulo_de_cada_pagina_es_unico(client):
    assert len({p.titulo for p in paginas.PAGINAS}) == len(paginas.PAGINAS)
    assert len({p.descripcion for p in paginas.PAGINAS}) == len(paginas.PAGINAS)


# --- contenido: lo que no puede cambiar sin que alguien lo decida -------------------------------------

def test_metodologia_dice_que_no_garantiza_y_que_no_supera_al_mercado(client):
    t = client.get("/metodologia/").text
    assert "no garantizan resultados" in t and "No afirmamos superar al mercado" in t


def test_metodologia_declara_que_aun_no_hay_registro_externo(client):
    # Verificado el 8-nov: published_ref es nulo en todos los lotes de /chain. Cuando exista el registro
    # público externo hay que actualizar esta página Y esta prueba: nunca afirmarlo antes de que sea cierto.
    t = client.get("/metodologia/").text
    assert "todavía no las publicamos en un registro externo independiente" in t
    assert not re.search(r"repositorio público|testigo externo|GitHub", t)


def test_juego_responsable_cita_recursos_verificados(client):
    t = client.get("/juego-responsable/").text
    for esperado in ("900 200 225", "800 911 2000", "1-800-MY-RESET", "gambleaware.org", "fejar.org"):
        assert esperado in t, esperado
    assert "1-800-GAMBLER" not in t, "ese número ya no es el de la línea nacional (cambió en enero de 2026)"
    assert "mayores de 18" in t


def test_sobre_nosotros_cita_a_la_sociedad_igual_que_los_textos_legales(client):
    t = client.get("/sobre-nosotros/").text
    legal = client.get("/legal/terminos").text
    for dato in ("Saptain LTD", "Seychelles", "admin@pronosticosdeportivos.pro"):
        assert dato in t and dato in legal, dato


def test_las_paginas_nuevas_no_heredan_noindex_de_las_rutas_json():
    from qf.api import seo
    for p in paginas.PAGINAS:
        assert seo.primer_segmento(p.ruta) not in seo.NOINDEX_SEGMENTS


def test_el_html_escapa_lo_que_incrusta(monkeypatch, client):
    malo = paginas.Pagina("x", "sobre_nosotros.html", 'T <script>alert(1)</script>', 'd "q" <b>', 'M', paginas.PAGINAS[0].revision)
    html = paginas.render(malo)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert 'content="d &#34;q&#34; &lt;b&gt;"' in html or 'content="d &quot;q&quot; &lt;b&gt;"' in html
    assert "\\u003cscript" in html     # el JSON-LD también va escapado
