"""F4: `/calibracion/`. Datos de ejemplo con la forma de los reales; sin base ni red."""
import copy
import html
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

import datos_calibracion as dc
from qf.api import calibracion, main, nba_datos, ratelimit
from test_paginas import Doc

BASE = "https://pronosticosdeportivos.pro"
HTML = {"accept": "text/html,application/xhtml+xml"}
# Números que aparecen en la redacción fija de la plantilla («2 errores estándar», «el 70 %», «1 sería perfecta»): nada más.
CONSTANTES_DE_REDACCION = {1.0, 2.0, 70.0}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(calibracion, "carga_futbol", lambda: copy.deepcopy(dc.FUTBOL))
    monkeypatch.setattr(calibracion, "carga_nba", lambda: copy.deepcopy(dc.NBA))
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


def principal(texto: str) -> str:
    return texto.split('<main id="contenido">', 1)[1].split("</main>", 1)[0]


def texto_visible(texto: str) -> str:
    cuerpo = re.sub(r"<svg.*?</svg>", " ", principal(texto), flags=re.S)       # los ejes del gráfico no son redacción
    return html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))


# --- número por número: ninguna cifra de la redacción sale de fuera de los datos -----------------------

def _numeros_de_texto(s: str):
    for t in re.findall(r"\d+(?:[.,]\d+)*", s):
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
            yield float(t.replace(".", ""))
        elif len(re.findall(r"[.,]", t)) > 1:          # versiones y fechas con varios puntos: cada parte es un número
            yield from (float(x) for x in re.split(r"[.,]", t))
        else:
            yield float(t.replace(",", "."))


def valores_permitidos(*fuentes) -> set[float]:
    ok = set(CONSTANTES_DE_REDACCION)

    def anadir(v):
        for dec in range(0, 6):
            ok.add(round(v, dec))
            ok.add(round(v * 100, dec))                 # porcentajes

    def recorrer(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            anadir(float(x))
        elif isinstance(x, (datetime, date)):
            ok.update({float(x.year), float(x.month), float(x.day)})
        elif isinstance(x, str):
            ok.update(_numeros_de_texto(x))
        elif isinstance(x, dict):
            for v in x.values():
                recorrer(v)
        elif isinstance(x, (list, tuple)):
            for v in x:
                recorrer(v)
    for f in fuentes:
        recorrer(f)
    return ok


def cifras_sin_origen(texto: str, permitidos: set[float]) -> list[str]:
    malas = []
    for t in re.findall(r"\d+(?:[.,]\d+)*", texto):
        for v in _numeros_de_texto(t):
            if all(round(v, dec) not in permitidos for dec in (0, 1, 2, 3, 4, 5)) and v not in permitidos:
                malas.append(t)
                break
    return malas


def derivadas(futbol, nba) -> list:
    """Cifras que la página CALCULA a partir de los datos (diferencias y recuentos): se admiten porque son derivadas, no inventadas."""
    r = futbol[0]
    salida = [abs(r["rps"] - r["rps_market"]), len(r["bins"]), sum(1 for b in r["bins"] if b["within_2se"]),
              sum(1 for b in r["bins"] if not b["within_2se"])]
    h = nba["historico"]["equipo"]
    salida.append(abs(h["modelo"]["brier_ganador"] - h["mercado"]["brier_ganador"]))
    return salida


def test_todas_las_cifras_del_texto_salen_de_los_datos(client):
    t = texto_visible(client.get("/calibracion/", headers=HTML).text)
    permitidos = valores_permitidos(dc.FUTBOL, dc.NBA, derivadas(dc.FUTBOL, dc.NBA))
    assert cifras_sin_origen(t, permitidos) == []


def test_la_comprobacion_de_cifras_detecta_una_inventada(client):
    t = texto_visible(client.get("/calibracion/", headers=HTML).text) + " y además un 87,3 % de acierto"
    permitidos = valores_permitidos(dc.FUTBOL, dc.NBA, derivadas(dc.FUTBOL, dc.NBA))
    assert cifras_sin_origen(t, permitidos) == ["87,3"]


# --- la página ------------------------------------------------------------------------------------

def test_pagina_con_cifras_graficos_y_aviso_de_automatizacion(client):
    r = client.get("/calibracion/", headers=HTML)
    assert r.status_code == 200
    d = Doc(r.text)
    assert d.title.startswith("Calibración") and len(d.h1) == 1
    assert [x["href"] for x in d.links if x.get("rel") == "canonical"] == [f"{BASE}/calibracion/"]
    assert [m["content"] for m in d.metas if m.get("name") == "robots"][0].startswith("index, follow")
    assert "Página generada automáticamente" in r.text and "ninguna se escribe a mano" in r.text       # aviso visible (plan §8)
    t = texto_visible(r.text)
    assert "3.222 partidos" in t and "modelo 0,2091" in t and "mercado 0,2009" in t
    assert "Tramos dentro de 2 errores estándar de la calibración perfecta: 4 de 5 (1 fuera)" in t
    assert "Temporada 2025-26" in t and "modelo 0,2063" in t and "mercado 0,1981" in t and "(1 sería perfecta)" in t
    assert "17 partidos con pronóstico sellado" in t and "no certificada" in t and "Todavía son pocos partidos" in t


def test_el_modelo_no_supera_al_mercado_solo_si_los_datos_lo_dicen(client, monkeypatch):
    t = texto_visible(client.get("/calibracion/", headers=HTML).text)
    assert t.count("el modelo no supera al mercado") == 2                      # fútbol y NBA histórico, con los datos de ejemplo
    mejor = copy.deepcopy(dc.FUTBOL)
    mejor[0]["rps"], mejor[0]["rps_market"] = 0.19, 0.2
    nba = copy.deepcopy(dc.NBA)
    nba["historico"]["equipo"]["modelo"]["brier_ganador"] = 0.19
    monkeypatch.setattr(calibracion, "carga_futbol", lambda: mejor)
    monkeypatch.setattr(calibracion, "carga_nba", lambda: nba)
    t2 = texto_visible(client.get("/calibracion/", headers=HTML).text)
    assert "el modelo no supera al mercado" not in t2
    assert t2.count("El modelo fue más preciso") == 2 and "por 0,0100" in t2


def test_el_grafico_es_accesible_y_marca_lo_que_cae_fuera(client):
    t = client.get("/calibracion/", headers=HTML).text
    svgs = re.findall(r"<svg.*?</svg>", t, re.S)
    assert len(svgs) == 2
    for s in svgs:
        assert 'role="img"' in s and "<title" in s and "<desc" in s and "stroke-dasharray" in s       # diagonal de calibración perfecta
    assert svgs[0].count("<circle") == 5 and "#fbbf24" in svgs[0]                                         # el tramo fuera del margen, en ámbar
    assert svgs[1].count("<circle") == 5 and "#fbbf24" not in svgs[1]                                     # NBA no trae error estándar: sin barras
    assert "<th scope=\"row\">0,3-0,4</th>" in t and 'class="fallo">no<' in t                             # la misma información en tabla


def test_el_svg_escapa_y_aguanta_vacios_y_valores_fuera_de_rango():
    s = calibracion.svg_fiabilidad([], 'Título <script>"x"', "d & d")
    assert "<script>" not in s and "&lt;script&gt;" in s and "<circle" not in s
    fuera = calibracion.svg_fiabilidad([{"pred": 1.4, "obs": -0.2, "n": 3, "se": 0.5, "dentro": False}], "t", "d")
    assert fuera.count("<circle") == 1 and "nan" not in fuera.lower()


def test_secciones_parciales_y_sin_datos(client, monkeypatch):
    monkeypatch.setattr(calibracion, "carga_futbol", lambda: [])
    r = client.get("/calibracion/", headers=HTML)
    assert r.status_code == 200 and 'id="nba"' in r.text and 'id="futbol"' not in r.text
    monkeypatch.setattr(calibracion, "carga_nba", lambda: None)
    r = client.get("/calibracion/", headers=HTML)
    assert r.status_code == 503 and r.headers["retry-after"] == "60" and r.headers["cache-control"] == "no-store"
    assert client.get("/sitemap-paginas.xml").status_code == 200


def test_la_base_de_futbol_caida_no_tumba_la_pagina(client, monkeypatch):
    def roto():
        raise RuntimeError("sin base")
    monkeypatch.setattr(calibracion, "carga_futbol", roto)
    r = client.get("/calibracion/", headers=HTML)
    assert r.status_code == 200 and 'id="nba"' in r.text


def test_en_el_mapa_con_la_fecha_de_la_ultima_medicion_y_enlazada(client):
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {}
    for u in ET.fromstring(client.get("/sitemap-paginas.xml").text).findall("s:url", ns):
        mod = u.find("s:lastmod", ns)
        urls[u.find("s:loc", ns).text] = mod.text if mod is not None else None
    assert urls[f"{BASE}/calibracion/"] == "2026-11-09"
    assert "/calibracion/" in Doc(client.get("/metodologia/", headers=HTML).text).hrefs
    assert "/calibracion/" in Doc(client.get("/", headers=HTML).text).hrefs
    r = client.get("/calibracion")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}/calibracion/"


def test_json_ld_y_cabeceras(client):
    r = client.get("/calibracion/", headers=HTML)
    d = Doc(r.text)
    tipos = {b["@type"]: b for b in d.ld}
    assert set(tipos) == {"BreadcrumbList", "WebPage"} and tipos["WebPage"]["dateModified"] == "2026-11-09"
    assert r.headers["content-security-policy"].startswith("default-src 'none'") and "x-robots-tag" not in r.headers


def test_la_fecha_de_los_datos_manda_sobre_el_reloj(client, monkeypatch):
    viejo = copy.deepcopy(dc.FUTBOL)
    viejo[0]["created_at"] = datetime(2026, 1, 5, 3, 0)
    monkeypatch.setattr(calibracion, "carga_futbol", lambda: viejo)
    t = client.get("/calibracion/", headers=HTML).text
    assert "Última revisión: <time datetime=\"2026-01-05\">5 de enero de 2026</time>" in t


def test_nba_calibracion_pide_solo_el_endpoint_publico(monkeypatch):
    pedidos = []
    monkeypatch.setattr(nba_datos, "_pedir", lambda ruta, params=None: pedidos.append(ruta) or {"ok": True})
    nba_datos.vaciar_cache()
    assert nba_datos.calibracion() == {"ok": True} and pedidos == ["/nba/v1/calibracion"]
    nba_datos.vaciar_cache()
