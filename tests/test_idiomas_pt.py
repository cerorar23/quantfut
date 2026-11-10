"""F6.4: portugués (pt-BR) de las páginas de confianza, con su estado off / preview / on y el hreflang de tres idiomas."""
import html
import re
import xml.etree.ElementTree as ET

import pytest

from qf.api import paginas
from test_idiomas import client, estado  # noqa: F401  (cliente y estados de test_idiomas.py)

BASE = "https://pronosticosdeportivos.pro"
HTML = {"accept": "text/html,application/xhtml+xml"}
PT = list(paginas.PAGINAS_PT)
ES = list(paginas.PAGINAS)
EN = list(paginas.PAGINAS_EN)
XHTML = "{http://www.w3.org/1999/xhtml}"
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
# Palabras que existen en español y no en portugués. Las compartidas («de», «para», «com», «que», «las» en «incluí-las», «está», «sus» o
# «SUS» como sigla) no sirven para detectar español.
PALABRAS_ES = re.compile(r"\b(los|del|pero|cuando|también|nosotros|pronóstico|pronósticos|probabilidad|partido|ganó|perdió|acertó|falló|usted|aquí)\b")


def visible(texto: str) -> str:
    cuerpo = texto.split('<main id="contenido">', 1)[1].split("</footer>", 1)[0]
    cuerpo = re.sub(r"<a [^>]*lang=\"es\"[^>]*>.*?</a>", " ", cuerpo, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))).strip()


@pytest.fixture
def abierto(client, estado):  # noqa: F811
    estado("pt=on")
    return client


# --- apagado y vista previa ----------------------------------------------------------------------

def test_apagado_el_portugues_da_404_y_no_aparece_en_el_mapa(client, estado):  # noqa: F811
    estado(None)
    for p in PT:
        assert client.get(p.ruta, headers=HTML).status_code == 404, p.ruta
        assert client.get(f"/{p.slug}", headers=HTML).status_code == 404
    mapa = client.get("/sitemap-paginas.xml").text
    assert "/pt/" not in mapa
    for p in ES:
        t = client.get(p.ruta, headers=HTML).text
        assert 'hreflang="pt"' not in t and "Português" not in t


def test_vista_previa_no_se_indexa_ni_se_enumera(client, estado):  # noqa: F811
    estado("pt=preview")
    for p in PT:
        r = client.get(p.ruta, headers=HTML)
        assert r.status_code == 200 and r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
        assert 'name="robots" content="noindex, follow"' in r.text
    assert "/pt/" not in client.get("/sitemap-paginas.xml").text


# --- encendido: la cabeza y las fechas ------------------------------------------------------------

@pytest.mark.parametrize("p", PT, ids=lambda p: p.slug)
def test_cabeza_en_portugues(abierto, p):
    r = abierto.get(p.ruta, headers=HTML)
    assert r.status_code == 200 and "x-robots-tag" not in r.headers
    t = r.text
    assert '<html lang="pt-BR">' in t and 'property="og:locale" content="pt_BR"' in t
    assert f'<link rel="canonical" href="{BASE}{p.ruta}">' in t
    assert 'name="robots" content="index, follow' in t and "og:image" not in t
    assert f"<title>{html.escape(p.titulo)} | QuantFut</title>" in t
    assert 120 <= len(p.descripcion) <= 165, len(p.descripcion)
    assert t.count("<h1>") == 1
    assert '"inLanguage": "pt"' in t or '"inLanguage":"pt"' in t
    assert "Pular para o conteúdo" in t and "Última revisão" in t


def test_fecha_en_portugues_es_la_del_mapa(abierto):
    for p in PT:
        t = abierto.get(p.ruta, headers=HTML).text
        assert f'<time datetime="{p.revision.isoformat()}">{paginas.fecha_larga(p.revision, "pt")}</time>' in t
    assert paginas.fecha_larga(PT[0].revision, "pt") == "10 de novembro de 2026"


def test_titulos_y_descripciones_son_unicos_entre_idiomas():
    todos = ES + EN + PT
    assert len({p.titulo for p in todos}) == len(todos)
    assert len({p.descripcion for p in todos}) == len(todos)


# --- hreflang de tres idiomas y selector -----------------------------------------------------------

def _mapa(client):
    raiz = ET.fromstring(client.get("/sitemap-paginas.xml").content)
    return {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}


def test_hreflang_con_portugues_y_espanol_sin_ingles(abierto, estado):  # noqa: F811
    estado("pt=on\nen=off")
    mapa = _mapa(abierto)
    for es, pt in zip(ES, PT):
        u_es, u_pt = BASE + es.ruta, BASE + pt.ruta
        esperado = {"es": u_es, "pt": u_pt, "x-default": u_es}
        assert mapa[u_es] == esperado and mapa[u_pt] == esperado, es.slug


def test_hreflang_con_los_tres_idiomas_abiertos(abierto, estado):  # noqa: F811
    estado("pt=on\nen=on")
    mapa = _mapa(abierto)
    for es, en, pt in zip(ES, EN, PT):
        esperado = {"es": BASE + es.ruta, "en": BASE + en.ruta, "pt": BASE + pt.ruta, "x-default": BASE + es.ruta}
        assert mapa[BASE + es.ruta] == esperado and mapa[BASE + en.ruta] == esperado and mapa[BASE + pt.ruta] == esperado, es.slug


def test_selector_enlaza_al_espanol_y_al_ingles_solo_si_estan_abiertos(abierto, estado):  # noqa: F811
    estado("pt=on\nen=off")
    t = abierto.get(PT[0].ruta, headers=HTML).text
    assert f'<a href="{ES[0].ruta}" hreflang="es" lang="es">Español</a>' in t
    assert "English" not in t
    estado("pt=on\nen=on")
    t = abierto.get(PT[0].ruta, headers=HTML).text
    assert f'<a href="{EN[0].ruta}" hreflang="en" lang="en">English</a>' in t


def test_sin_redireccion_por_idioma(abierto):
    r = abierto.get("/metodologia/", headers={**HTML, "accept-language": "pt-BR,pt;q=0.9"})
    assert r.status_code == 200 and "location" not in r.headers
    assert abierto.get("/pt/metodologia/", headers={**HTML, "accept-language": "es-MX"}).status_code == 200


def test_sin_barra_redirige_a_la_canonica(abierto):
    r = abierto.get("/pt/sobre-nos?x=1")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}/pt/sobre-nos/?x=1"


# --- el texto está en portugués, con las mismas garantías ----------------------------------------------

@pytest.mark.parametrize("p", PT, ids=lambda p: p.slug)
def test_el_texto_no_trae_espanol(abierto, p):
    txt = visible(abierto.get(p.ruta, headers=HTML).text)
    assert PALABRAS_ES.findall(txt.lower()) == [], PALABRAS_ES.findall(txt.lower())[:8]
    assert not re.search(r"[ñ¿¡]", txt.lower())
    assert len(txt.split()) > 150


def test_garantias_de_contenido(abierto):
    metodo = visible(abierto.get("/pt/metodologia/", headers=HTML).text).lower()
    for frase in ("não garantem resultados", "não afirmamos superar o mercado", "ainda não as publicamos em um registro externo independente"):
        assert frase in metodo, frase
    jogo = visible(abierto.get("/pt/jogo-responsavel/", headers=HTML).text).lower()
    assert "não é uma casa de apostas" in jogo and "18 anos" in jogo and "192" in jogo
    sobre = visible(abierto.get("/pt/sobre-nos/", headers=HTML).text).lower()
    assert "saptain ltd" in sobre and "seicheles" in sobre and "e coast rd, victoria" in sobre
    for prohibido in ("aposta segura", "dinheiro fácil", "lucro garantido"):
        assert prohibido not in (metodo + jogo + sobre)


def test_telefonos_y_correo_son_los_del_espanol(abierto):
    for es, pt in zip(ES, PT):
        a = abierto.get(es.ruta, headers=HTML).text
        b = abierto.get(pt.ruta, headers=HTML).text
        for patron in (r'href="(tel:[^"]+)"', r'href="(mailto:[^"]+)"'):
            assert sorted(set(re.findall(patron, a))) == sorted(set(re.findall(patron, b))), (es.slug, patron)
