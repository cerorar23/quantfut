"""F6.1: idiomas de la web pública (inglés), con su estado off / preview / on. Sin base ni red."""
import html
import re
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient

from qf.api import idiomas, main, paginas, ratelimit

BASE = "https://pronosticosdeportivos.pro"
HTML = {"accept": "text/html,application/xhtml+xml"}
EN = [p for p in paginas.PAGINAS_EN]
ES = list(paginas.PAGINAS)
XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


@pytest.fixture
def estado(tmp_path, monkeypatch):
    archivo = tmp_path / "activos.txt"
    monkeypatch.setenv("IDIOMAS_ARCHIVO", str(archivo))

    def poner(texto: str | None):
        if texto is None:
            archivo.unlink(missing_ok=True)
        else:
            archivo.write_text(texto, encoding="utf-8")
        idiomas.olvidar()
    idiomas.olvidar()
    yield poner
    idiomas.olvidar()


@pytest.fixture
def client(monkeypatch, estado):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


def sitemap(client) -> ET.Element:
    return ET.fromstring(client.get("/sitemap-paginas.xml").content)


def entradas(raiz) -> dict[str, dict[str, str]]:
    """{loc: {hreflang: href}}"""
    return {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}


def visible(texto: str) -> str:
    cuerpo = re.split(r'<main id="(?:main-content"|contenido">)', texto, maxsplit=1)[1].split("</footer>", 1)[0]    # shell de la app o página propia
    cuerpo = re.sub(r"<a [^>]*lang=\"es\"[^>]*>.*?</a>", " ", cuerpo, flags=re.S)     # los enlaces a páginas solo en español van marcados
    return html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))


# --- el archivo de estados ---------------------------------------------------------------------------

def test_por_defecto_el_ingles_esta_apagado(estado):
    estado(None)
    assert idiomas.estado("en") == "off" and idiomas.estado("es") == "on"


def test_lee_estados_ignora_basura_y_el_espanol_no_se_apaga(estado):
    estado("# comentario\nen = Preview  # revisión\nxx=on\npt=raro\nes=off\n\nbasura\n")
    assert idiomas.estado("en") == "preview"
    assert idiomas.estado("pt") == "off" and idiomas.estado("xx") == "off"
    assert idiomas.estado("es") == "on"


def test_el_cambio_se_nota_sin_reiniciar(client, estado):
    estado("en=on")
    assert client.get("/en/methodology/", headers=HTML).status_code == 200
    estado("en=off")
    assert client.get("/en/methodology/", headers=HTML).status_code == 404


# --- apagado: ni rastro ------------------------------------------------------------------------------

def test_apagado_las_paginas_en_ingles_dan_404_y_no_hay_rastro(client, estado):
    estado(None)
    for p in EN:
        assert client.get(p.ruta, headers=HTML).status_code == 404, p.ruta
        assert client.get(f"/{p.slug}", headers=HTML).status_code == 404
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/en/" not in mapa and "xhtml:link" not in mapa
    for p in ES:
        t = client.get(p.ruta, headers=HTML).text
        assert 'hreflang="en"' not in t and "English" not in t and "/en/" not in t


# --- vista previa: el titular puede revisar, nadie indexa --------------------------------------------

def test_preview_se_ve_pero_no_se_indexa_ni_se_enumera(client, estado):
    estado("en=preview")
    for p in EN:
        r = client.get(p.ruta, headers=HTML)
        assert r.status_code == 200
        assert r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
        assert 'name="robots" content="noindex, follow"' in r.text
        assert 'hreflang="es"' in r.text and "Español" in r.text           # enlace de vuelta a la versión en español
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/en/" not in mapa and "xhtml:link" not in mapa
    for p in ES:
        t = client.get(p.ruta, headers=HTML).text
        assert "English" not in t and 'href="/en/' not in t                 # el español no anuncia lo que aún no está abierto


# --- encendido ---------------------------------------------------------------------------------------

@pytest.fixture
def abierto(client, estado):
    estado("en=on")
    return client


@pytest.mark.parametrize("p", EN, ids=lambda p: p.slug)
def test_head_en_ingles_completo(abierto, p):
    r = abierto.get(p.ruta, headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    t = r.text
    assert t.startswith("<!doctype html>") and '<html lang="en" ' in t
    assert f'<link rel="canonical" href="{BASE}{p.ruta}" />' in t
    assert 'name="robots" content="index, follow' in t
    assert 'property="og:locale" content="en_US"' in t and f'property="og:url" content="{BASE}{p.ruta}"' in t
    assert f"<title>{html.escape(p.titulo)} | QuantFut</title>" in t
    assert 120 <= len(p.descripcion) <= 165, len(p.descripcion)
    assert "og:image" not in t                                          # la tarjeta de marca está en español
    assert t.count("<h1>") == 1
    assert '"inLanguage": "en"' in t or '"inLanguage":"en"' in t
    assert "Last reviewed" in t and "Última revisión" not in t


def test_titulos_y_descripciones_en_ingles_son_unicos_y_distintos_del_espanol():
    todos = ES + EN
    assert len({p.titulo for p in todos}) == len(todos)
    assert len({p.descripcion for p in todos}) == len(todos)


def test_fecha_en_ingles_es_la_del_mapa(abierto):
    mapa = entradas(sitemap(abierto))
    for p in EN:
        assert f"{BASE}{p.ruta}" in mapa
        t = abierto.get(p.ruta, headers=HTML).text
        assert f'<time datetime="{p.revision.isoformat()}">{paginas.fecha_larga(p.revision, "en")}</time>' in t
    assert paginas.fecha_larga(EN[0].revision, "en") == "November 9, 2026"


def test_hreflang_reciproco_absoluto_autorreferente_y_con_x_default(abierto):
    mapa = entradas(sitemap(abierto))
    for es, en in zip(ES, EN):
        u_es, u_en = BASE + es.ruta, BASE + en.ruta
        esperado = {"es": u_es, "en": u_en, "x-default": u_es}
        assert mapa[u_es] == esperado, es.ruta
        assert mapa[u_en] == esperado, en.ruta                          # recíproco: las dos listan lo mismo, cada una incluida a sí misma
    for loc, alt in mapa.items():
        if alt:
            assert all(h.startswith("https://") for h in alt.values())
            assert loc in alt.values()
    # una página sin versión en inglés no lleva hreflang
    assert mapa[BASE + "/historial/"] == {}


def test_selector_de_idioma_con_enlaces_normales_en_los_dos_sentidos(abierto):
    for es, en in zip(ES, EN):
        t_es = abierto.get(es.ruta, headers=HTML).text
        t_en = abierto.get(en.ruta, headers=HTML).text
        assert f'<a href="{en.ruta}" hreflang="en" lang="en">English</a>' in t_es
        assert f'<a href="{es.ruta}" hreflang="es" lang="es">Español</a>' in t_en


def test_sin_redireccion_por_idioma_del_navegador(abierto):
    r = abierto.get("/metodologia/", headers={**HTML, "accept-language": "en-US,en;q=0.9"})
    assert r.status_code == 200 and "location" not in r.headers
    r = abierto.get("/en/methodology/", headers={**HTML, "accept-language": "es-MX"})
    assert r.status_code == 200


def test_sin_barra_redirige_a_la_canonica(abierto):
    r = abierto.get("/en/about?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}/en/about/?x=1"


@pytest.mark.parametrize("p", EN, ids=lambda p: p.slug)
def test_enlaces_internos_existen_y_los_que_salen_del_ingles_van_a_ingles_o_estan_marcados(abierto, p):
    t = abierto.get(p.ruta, headers=HTML).text
    for etiqueta in re.findall(r"<a\b[^>]*>", t):
        m = re.search(r'href="([^"]+)"', etiqueta)
        href = m.group(1) if m else ""
        if not href.startswith("/") or href.startswith("//"):
            continue
        ruta = href.split("#")[0]
        neutro = ruta in ("/", "/chain")          # la portada y un JSON público: sin versión por idioma
        if ruta and not neutro:
            assert abierto.get(ruta, headers=HTML).status_code in (200, 301, 302), href
        assert ruta.startswith("/en/") or 'lang="es"' in etiqueta or neutro, f"enlace a una página en español sin marcar: {etiqueta}"


# --- el inglés está de verdad en inglés ---------------------------------------------------------------

PALABRAS_ES = re.compile(r"\b(el|la|los|las|de|del|que|para|con|una|un|por|se|su|es|más|pero|cuando|esta|este|y)\b")
NOMBRES_PROPIOS = ("Línea de la Vida",)


@pytest.mark.parametrize("p", EN, ids=lambda p: p.slug)
def test_el_texto_de_las_paginas_en_ingles_no_trae_espanol(abierto, p):
    texto = visible(abierto.get(p.ruta, headers=HTML).text)
    for n in NOMBRES_PROPIOS:
        texto = texto.replace(n, " ")
    # palabras vacías del español que no existen en inglés («no» sí, y se deja fuera)
    sueltas = PALABRAS_ES.findall(texto.lower())
    assert sueltas == [], sueltas[:10]
    assert not re.search(r"[áéíóúñ¿¡]", texto.lower().replace("línea", "")), re.findall(r".{20}[áéíóúñ¿¡].{20}", texto.lower())[:3]
    assert len(texto.split()) > 150


@pytest.mark.parametrize("p", EN, ids=lambda p: p.slug)
def test_el_ingles_conserva_las_garantias_del_espanol(abierto, p):
    t = visible(abierto.get(p.ruta, headers=HTML).text).lower()
    if p.grupo == "metodologia":
        for frase in ("do not claim to beat the market", "do not guarantee", "not yet publish them in an independent external register", "full record, including the misses"):
            assert frase in t or frase.replace("do not guarantee", "does not guarantee") in t, frase
    if p.grupo == "juego-responsable":
        assert "not a bookmaker" in t and "18 and over" in t
        for tel in ("1-800-697-3738", "900 200 225", "800 911 2000"):
            assert tel in t, tel
    if p.grupo == "sobre-nosotros":
        assert "saptain ltd" in t and "seychelles" in t and "e coast rd, victoria" in t
    for prohibido in ("guaranteed win", "sure bet", "easy money", "risk-free"):
        assert prohibido not in t


def test_cada_pagina_en_espanol_tiene_su_gemela_en_ingles():
    assert [p.grupo for p in ES] == [p.grupo for p in EN]
    assert all(p.grupo and p.idioma == "en" for p in EN)
    for es, en in zip(ES, EN):
        assert en.slug == "en/" + en.slug.split("/", 1)[1] and en.ruta.startswith("/en/")
        assert en.migas and en.titulo != es.titulo


def test_los_datos_de_contacto_son_los_mismos_que_en_espanol(abierto):
    """Teléfonos, correo y razón social no pueden diferir entre idiomas."""
    for es, en in zip(ES, EN):
        a = abierto.get(es.ruta, headers=HTML).text
        b = abierto.get(en.ruta, headers=HTML).text
        for patron in (r'href="(tel:[^"]+)"', r'href="(mailto:[^"]+)"', r'href="(https://[^"]+)" rel="noopener"'):
            assert sorted(set(re.findall(patron, a))) == sorted(set(re.findall(patron, b))), (es.slug, patron)
