"""F6.3: calibración y calculadora de cuota justa en inglés (`/en/calibration/`, `/en/fair-odds-calculator/`)
y portugués (`/pt/calibracao/`, `/pt/calculadora-odd-justa/`).
"""
import copy
import html
import re
import xml.etree.ElementTree as ET

import pytest

import datos_calibracion as dc
from qf.api import calibracion, cuota_justa, paginas
from test_calibracion import CONSTANTES_DE_REDACCION, derivadas, texto_visible
from test_idiomas import PALABRAS_ES as PALABRAS_ES_EN, client, estado  # noqa: F401
from test_idiomas_pt import PALABRAS_ES as PALABRAS_ES_PT
from test_paginas import Doc

BASE = "https://pronosticosdeportivos.pro"
HTML = {"accept": "text/html,application/xhtml+xml"}
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
XHTML = "{http://www.w3.org/1999/xhtml}"

GRUPOS = (
    ("calibracion", "/calibracion/", "/en/calibration/", "/pt/calibracao/", "/en/calibration", "/pt/calibracao"),
    ("cuota-justa", "/calculadora-cuota-justa/", "/en/fair-odds-calculator/", "/pt/calculadora-odd-justa/", "/en/fair-odds-calculator", "/pt/calculadora-odd-justa"),
)


@pytest.fixture
def todos(client, estado):  # noqa: F811
    estado("en=on\npt=on")
    return client


def _numeros(texto: str, idioma: str):
    pat = r"\d{1,3}(,\d{3})+" if idioma == "en" else r"\d{1,3}(\.\d{3})+"
    for t in re.findall(r"\d+(?:[.,]\d+)*", texto):
        if re.fullmatch(pat, t):
            yield float(t.replace(",", "") if idioma == "en" else t.replace(".", ""))
        elif len(re.findall(r"[.,]", t)) > 1:
            yield from (float(x) for x in re.split(r"[.,]", t))
        else:
            yield float(t.replace(",", "."))


def _permitidos(idioma: str) -> set[float]:
    ok = set(CONSTANTES_DE_REDACCION)

    def anadir(v: float):
        for dec in range(0, 6):
            ok.add(round(v, dec))
            ok.add(round(v * 100, dec))

    def recorrer(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            anadir(float(x))
        elif hasattr(x, "year") and hasattr(x, "month") and hasattr(x, "day"):
            ok.update({float(x.year), float(x.month), float(x.day)})
        elif isinstance(x, str):
            ok.update(_numeros(x, idioma))
        elif isinstance(x, dict):
            for v in x.values():
                recorrer(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                recorrer(v)

    for src in (dc.FUTBOL, dc.NBA, derivadas(dc.FUTBOL, dc.NBA)):
        recorrer(src)
    return ok


def _cifras_sin_origen(texto: str, idioma: str) -> list[str]:
    ok = _permitidos(idioma)
    malas = []
    for t in re.findall(r"\d+(?:[.,]\d+)*", texto):
        for v in _numeros(t, idioma):
            if all(round(v, dec) not in ok for dec in (0, 1, 2, 3, 4, 5)) and v not in ok:
                malas.append(t)
                break
    return malas


def _visible_contenido(html_doc: str) -> str:
    cuerpo = html_doc.split('<main id="contenido">', 1)[1].split("</footer>", 1)[0]
    cuerpo = re.sub(r"<svg.*?</svg>", " ", cuerpo, flags=re.S)
    cuerpo = re.sub(r"<a [^>]*lang=\"es\"[^>]*>.*?</a>", " ", cuerpo, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))).strip()


# --- puerta off / preview / on, redirecciones y hreflang ---

def test_apagado_responde_404_sin_rastro_en_sitemap_ni_selector(client, estado):  # noqa: F811
    estado(None)
    for _, r_es, r_en, r_pt, sb_en, sb_pt in GRUPOS:
        for u in (r_en, r_pt, sb_en, sb_pt):
            assert client.get(u, headers=HTML).status_code == 404, u
        t_es = client.get(r_es, headers=HTML).text
        assert "/en/" not in t_es and "/pt/" not in t_es
        assert 'hreflang="en"' not in t_es and 'hreflang="pt"' not in t_es
    mapa = client.get("/sitemap-paginas.xml").text
    for _, _, r_en, r_pt, _, _ in GRUPOS:
        assert r_en not in mapa and r_pt not in mapa


def test_vista_previa_noindex_sin_cache_y_no_en_sitemap(client, estado):  # noqa: F811
    estado("en=preview\npt=preview")
    for _, r_es, r_en, r_pt, sb_en, sb_pt in GRUPOS:
        for ruta, sb in ((r_en, sb_en), (r_pt, sb_pt)):
            r = client.get(ruta, headers=HTML)
            assert r.status_code == 200
            assert r.headers["x-robots-tag"] == "noindex" and r.headers["cache-control"] == "no-store"
            assert 'name="robots" content="noindex, follow"' in r.text
            assert f'href="{r_es}" hreflang="es" lang="es">Español</a>' in r.text
            red = client.get(f"{sb}?x=1")
            assert red.status_code == 301 and red.headers["location"] == f"{BASE}{ruta}?x=1"
        t_es = client.get(r_es, headers=HTML).text
        assert r_en not in t_es and r_pt not in t_es
    mapa = client.get("/sitemap-paginas.xml").text
    for _, _, r_en, r_pt, _, _ in GRUPOS:
        assert r_en not in mapa and r_pt not in mapa


def test_abierto_hreflang_reciproco_selector_y_cabeceras(todos):
    raiz = ET.fromstring(todos.get("/sitemap-paginas.xml").content)
    mapa = {u.findtext(f"{NS}loc"): {a.get("hreflang"): a.get("href") for a in u.findall(f"{XHTML}link")} for u in raiz.findall(f"{NS}url")}
    for _, r_es, r_en, r_pt, _, _ in GRUPOS:
        esperado = {"es": BASE + r_es, "en": BASE + r_en, "pt": BASE + r_pt, "x-default": BASE + r_es}
        assert mapa[BASE + r_es] == esperado
        assert mapa[BASE + r_en] == esperado
        assert mapa[BASE + r_pt] == esperado

        for ruta, lang, locale in ((r_en, "en", "en_US"), (r_pt, "pt-BR", "pt_BR")):
            resp = todos.get(ruta, headers=HTML)
            assert resp.status_code == 200 and "x-robots-tag" not in resp.headers
            t = resp.text
            assert f'<html lang="{lang}">' in t
            assert f'property="og:locale" content="{locale}"' in t
            assert f'<link rel="canonical" href="{BASE}{ruta}">' in t
            assert 'name="robots" content="index, follow' in t
            assert "og:image" not in t
            assert todos.head(ruta).status_code == 200

        t_en = todos.get(r_en, headers=HTML).text
        t_pt = todos.get(r_pt, headers=HTML).text
        assert f'href="{r_pt}" hreflang="pt" lang="pt">Português</a>' in t_en
        assert f'href="{r_en}" hreflang="en" lang="en">English</a>' in t_pt


# --- calibración EN y PT ---

@pytest.mark.parametrize("ruta,idioma", [("/en/calibration/", "en"), ("/pt/calibracao/", "pt")])
def test_calibracion_sin_cifras_inventadas_ni_espanol(todos, ruta, idioma):
    html_doc = todos.get(ruta, headers=HTML).text
    vis = texto_visible(html_doc)
    assert _cifras_sin_origen(vis, idioma) == []
    extra = " plus 87.3% accuracy" if idioma == "en" else " e 87,3% de acerto"
    assert _cifras_sin_origen(vis + extra, idioma) == ["87.3" if idioma == "en" else "87,3"]

    cuerpo = _visible_contenido(html_doc)
    if idioma == "en":
        assert PALABRAS_ES_EN.findall(cuerpo.lower()) == []
        assert not re.search(r"[áéíóúñ¿¡]", cuerpo.lower())
        assert "3,222 matches" in vis and "model 0.2091" in vis and "market 0.2009" in vis
        assert "Nov 9, 2026" in vis and "descriptive" in vis and "descriptiva" not in vis.lower()
        assert "the model does not beat the market" in vis
        assert "Predicted probability" in html_doc and "Observed frequency" in html_doc
        assert "<th scope=\"row\">0.3-0.4</th>" in html_doc
    else:
        assert PALABRAS_ES_PT.findall(cuerpo.lower()) == []
        assert not re.search(r"[ñ¿¡]", cuerpo.lower())
        assert "3.222 partidas" in vis and "modelo 0,2091" in vis and "mercado 0,2009" in vis
        assert "09/11/2026" in vis and "descritiva" in vis and "descriptiva" not in vis.lower()
        assert "o modelo não supera o mercado" in vis
        assert "Probabilidade prevista" in html_doc and "Frequência observada" in html_doc
        assert "<th scope=\"row\">0,3-0,4</th>" in html_doc


@pytest.mark.parametrize("ruta,esperado", [
    ("/en/calibration/", "The model was more accurate"),
    ("/pt/calibracao/", "O modelo foi mais preciso"),
])
def test_calibracion_cambia_veredicto_cuando_mejoran_los_datos(todos, monkeypatch, ruta, esperado):
    mejor = copy.deepcopy(dc.FUTBOL)
    mejor[0]["rps"], mejor[0]["rps_market"] = 0.19, 0.2
    nba = copy.deepcopy(dc.NBA)
    nba["historico"]["equipo"]["modelo"]["brier_ganador"] = 0.19
    monkeypatch.setattr(calibracion, "carga_futbol", lambda: mejor)
    monkeypatch.setattr(calibracion, "carga_nba", lambda: nba)
    t = texto_visible(todos.get(ruta, headers=HTML).text)
    assert t.count(esperado) == 2
    assert "does not beat the market" not in t and "não supera o mercado" not in t


@pytest.mark.parametrize("ruta", ["/en/calibration/", "/pt/calibracao/"])
def test_calibracion_accesible_y_503_sin_datos(todos, monkeypatch, ruta):
    t = todos.get(ruta, headers=HTML).text
    svgs = re.findall(r"<svg.*?</svg>", t, re.S)
    assert len(svgs) == 2 and all('role="img"' in s and "<title" in s and "<desc" in s and "stroke-dasharray" in s for s in svgs)
    assert svgs[0].count("<circle") == 5 and "#fbbf24" in svgs[0]
    monkeypatch.setattr(calibracion, "carga_futbol", lambda: [])
    monkeypatch.setattr(calibracion, "carga_nba", lambda: None)
    r = todos.get(ruta, headers=HTML)
    assert r.status_code == 503 and r.headers["retry-after"] == "60" and r.headers["cache-control"] == "no-store"


# --- calculadora EN y PT ---

@pytest.mark.parametrize("ruta,idioma", [("/en/fair-odds-calculator/", "en"), ("/pt/calculadora-odd-justa/", "pt")])
def test_calculadora_csp_estricta_ejemplo_y_sin_promesas(todos, ruta, idioma):
    r = todos.get(ruta, headers=HTML)
    csp = r.headers["content-security-policy"]
    assert csp == paginas.CSP
    assert "default-src 'none'" in csp and "script-src 'self'" in csp and "connect-src" not in csp
    t = r.text
    etiquetas = re.findall(r"<script\b([^>]*)>", t)
    propios = [e for e in etiquetas if "application/ld+json" not in e]
    assert len(propios) == 1 and 'type="module"' in propios[0]
    assert re.search(r'src="/static/cuota-justa\.js\?v=[0-9a-f]{10}"', propios[0])
    assert "onclick" not in t and "onchange" not in t and "oninput" not in t and "fbevents" not in t

    ej = cuota_justa.ejemplo(idioma=idioma)
    for f in ej["filas"]:
        assert f"<tr><th scope=\"row\">{f['nombre']}</th><td>{f['cuota']}</td><td>{f['implicita']}</td><td>{f['sin_margen']}</td><td>{f['justa']}</td></tr>" in t
    assert ej["suma"] in t and ej["margen"] in t and "<noscript>" in t

    for ident in ("cj-formato", "cj-cuota", "cj-prob", "cj-n", "cj-metodo", "cj-o0", "cj-o1", "cj-o2"):
        assert re.search(rf'<label for="{ident}"', t), ident
    assert t.count('aria-live="polite"') >= 3

    cuerpo = _visible_contenido(t)
    if idioma == "en":
        assert PALABRAS_ES_EN.findall(cuerpo.lower()) == []
        assert not re.search(r"[áéíóúñ¿¡]", cuerpo.lower())
        assert 'value="2.10"' in t
    else:
        assert PALABRAS_ES_PT.findall(cuerpo.lower()) == []
        assert not re.search(r"[ñ¿¡]", cuerpo.lower())
        assert 'value="2,10"' in t

    minus = t.lower()
    for prohibido in ("kelly", "bankroll", "stake", "sure bet", "easy money", "risk-free", "guaranteed win",
                      "aposta segura", "dinheiro fácil", "lucro garantido"):
        assert prohibido not in minus, prohibido


def test_metodologia_y_nav_enlazan_calibracion_y_calculadora_en_cada_idioma(todos):
    en_m = todos.get("/en/methodology/", headers=HTML).text
    assert "/en/fair-odds-calculator/" in en_m and "/en/calibration/" in en_m
    assert "/calculadora-cuota-justa/" not in en_m and "only in Spanish) calculator" not in en_m

    pt_m = todos.get("/pt/metodologia/", headers=HTML).text
    assert "/pt/calculadora-odd-justa/" in pt_m and "/pt/calibracao/" in pt_m
    assert "/calculadora-cuota-justa/" not in pt_m


def test_titulos_y_descripciones_f63_unicos_y_en_rango(todos):
    titulos, descripciones = [], []
    for _, _, r_en, r_pt, _, _ in GRUPOS:
        for ruta in (r_en, r_pt):
            d = Doc(todos.get(ruta, headers=HTML).text)
            desc = next(m["content"] for m in d.metas if m.get("name") == "description")
            assert 120 <= len(desc) <= 165, (ruta, len(desc))
            assert len(d.h1) == 1
            titulos.append(d.title)
            descripciones.append(desc)
    assert len(set(titulos)) == len(titulos)
    assert len(set(descripciones)) == len(descripciones)
