"""F2.2 del plan SEO: páginas de equipo de NBA con umbral. `nba-api` simulado: sin red ni base."""
import xml.etree.ElementTree as ET
from datetime import date

import pytest
from fastapi.testclient import TestClient

from qf.api import main, nba_datos, nba_equipos, nba_paginas, ratelimit
from test_nba_paginas import AHORA, BASE, HTML, partido
from test_paginas import Doc

CEL, LAK, OTR = "Boston Celtics", "Los Angeles Lakers", "Miami Heat"


def _dia(d):
    return f"2026-11-{d:02d}"


def hacer_dias():
    """Celtics: 6 pronósticos sellados (>= umbral). Lakers: 2 (bajo el umbral). Heat: 3. Un partido sin sello no cuenta."""
    dias = {}
    pid = 100
    for d, (loc, vis, p_local, res) in {
        2: (CEL, LAK, .60, {"local": 110.0, "visitante": 100.0}),      # favorito local ganó
        3: (OTR, CEL, .30, {"local": 90.0, "visitante": 101.0}),        # Celtics visitante favoritos (70 %) ganaron
        4: (CEL, OTR, .75, {"local": 99.0, "visitante": 104.0}),        # favorito local PERDIÓ: fallo
        5: (LAK, CEL, .45, {"local": 95.0, "visitante": 97.0}),         # Celtics (55 %) ganaron
        6: (CEL, OTR, .55, {"local": 108.0, "visitante": 100.0}),
        8: (CEL, LAK, .62, None),                                       # sin resultado: por jugar
    }.items():
        pid += 1
        dias.setdefault(_dia(d), []).append(partido(pid, loc, vis, _dia(d), f"2026-11-{d:02d}T23:30:00+00:00", p_local=p_local, resultado=res,
                                                   hash_=f"{pid:064x}"))
    dias[_dia(7)] = [partido(300, CEL, OTR, _dia(7), "2026-11-07T23:30:00+00:00", sello=False)]
    return dias


DIAS = hacer_dias()
ESTADISTICAS = {"teams": [{"name": CEL, "season": {"won": 5, "lost": 1, "rate": .83}, "last6": {"won": 5, "lost": 1}, "streak": 2,
                           "rest_days": 1, "back_to_back": False}]}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(nba_paginas, "_ahora", lambda: AHORA)
    nba_datos.vaciar_cache()

    def falso(ruta, params=None):
        if ruta == "/nba/v1/cartelera":
            return {"fecha": params["fecha"], "partidos": DIAS.get(params["fecha"], [])}
        if ruta.endswith("/estadisticas"):
            return ESTADISTICAS
        raise AssertionError(ruta)
    monkeypatch.setattr(nba_datos, "_pedir", falso)
    yield TestClient(main.app, base_url=BASE, follow_redirects=False)
    nba_datos.vaciar_cache()


def robots(texto):
    return [m["content"] for m in Doc(texto).metas if m.get("name") == "robots"]


def test_equipo_sobre_el_umbral_es_indexable_y_trae_su_historial(client):
    r = client.get("/nba/equipos/boston-celtics/", headers=HTML)
    assert r.status_code == 200
    d = Doc(r.text)
    assert robots(r.text) == [nba_equipos.ROBOTS_INDEXABLE]
    assert [x["href"] for x in d.links if x.get("rel") == "canonical"] == [f"{BASE}/nba/equipos/boston-celtics/"]
    assert "Boston Celtics" in d.title and "pronósticos" in d.title.lower() and len(d.h1) == 1
    assert "6 pronósticos de partidos de Boston Celtics" in r.text
    # 5 con resultado: ganó el favorito en 4 (el del día 4 falló); los Celtics ganaron 4 (días 2, 3, 5 y 6) y perdieron el del día 4
    assert "<strong>4</strong>" in r.text and "Boston Celtics ganó 4" in r.text
    assert "acertó" in r.text and "falló" in r.text and "por jugar" in r.text
    assert "/nba/boston-celtics-vs-los-angeles-lakers-2026-11-08/" in d.hrefs
    assert "5-1" in r.text and "2 victorias seguidas" in r.text                        # situación a la fecha del último partido


def test_equipo_bajo_el_umbral_existe_pero_con_noindex_y_fuera_del_sitemap(client):
    r = client.get("/nba/equipos/los-angeles-lakers/", headers=HTML)
    assert r.status_code == 200 and robots(r.text) == ["noindex, follow"]
    assert "3 pronósticos de partidos de Los Angeles Lakers" in r.text
    assert "las cifras todavía no dicen nada" in r.text
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = {}
    for u in ET.fromstring(client.get("/sitemap-paginas.xml").text).findall("s:url", ns):
        mod = u.find("s:lastmod", ns)
        urls[u.find("s:loc", ns).text] = mod.text if mod is not None else None
    assert f"{BASE}/nba/equipos/boston-celtics/" in urls and f"{BASE}/nba/equipos/los-angeles-lakers/" not in urls
    assert f"{BASE}/nba/equipos/miami-heat/" not in urls                               # 3 pronósticos: bajo el umbral
    assert urls[f"{BASE}/nba/equipos/boston-celtics/"] == "2026-11-08"                 # día del último sello verificable


def test_equipo_inexistente_sin_barra_y_basura(client):
    assert client.get("/nba/equipos/no-existe-fc/", headers=HTML).status_code == 404
    assert client.get("/nba/equipos/", headers=HTML).status_code == 404
    r = client.get("/nba/equipos/boston-celtics")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}/nba/equipos/boston-celtics/"
    assert client.get("/nba/equipos/Boston%20Celtics").status_code == 404           # solo se redirige a slugs bien formados


def test_json_ld_y_dentro_de_la_app(client):
    r = client.get("/nba/equipos/boston-celtics/", headers=HTML)
    d = Doc(r.text)
    tipos = {b["@type"]: b for b in d.ld}
    assert set(tipos) == {"BreadcrumbList", "WebPage"} and tipos["WebPage"]["about"] == {"@type": "SportsTeam", "name": CEL, "sport": "Basketball"}
    assert [i["item"] for i in tipos["BreadcrumbList"]["itemListElement"]] == [f"{BASE}/", f"{BASE}/nba/", f"{BASE}/nba/equipos/boston-celtics/"]
    assert 'data-ruta="partidos"' in r.text and 'data-deporte="nba"' in r.text and "data-evento" not in r.text


def test_la_pagina_del_partido_enlaza_solo_a_los_equipos_indexables(client):
    t = client.get("/nba/boston-celtics-vs-los-angeles-lakers-2026-11-08/", headers=HTML).text
    hrefs = Doc(t).hrefs
    assert "/nba/equipos/boston-celtics/" in hrefs and "/nba/equipos/los-angeles-lakers/" not in hrefs


def test_nba_caida_es_503_y_el_sitemap_sobrevive(client, monkeypatch):
    def roto(ruta, params=None):
        raise nba_datos.NbaNoDisponible("caído")
    nba_datos.vaciar_cache()
    monkeypatch.setattr(nba_datos, "_pedir", roto)
    r = client.get("/nba/equipos/boston-celtics/", headers=HTML)
    assert r.status_code == 503 and r.headers["retry-after"] == "60" and r.headers["cache-control"] == "no-store"
    assert client.get("/sitemap-paginas.xml").status_code == 200
    assert nba_equipos.enlace_si_indexable(CEL) is None


def test_la_ventana_parte_del_primer_dia_con_sellos_y_tiene_tope(monkeypatch):
    pedidas = []
    monkeypatch.setattr(nba_datos, "cartelera_ventana", lambda desde, hasta: pedidas.append((desde, hasta)) or {desde: []})
    nba_equipos.indice(date(2026, 11, 8))
    nba_equipos.indice(date(2027, 3, 1))
    assert pedidas[0][0] == date(2026, 11, 2)                                           # nunca antes del primer sello
    assert (pedidas[1][1] - pedidas[1][0]).days <= nba_equipos.DIAS_HISTORIA + 1       # y con tope de días en temporada larga


def test_las_cifras_del_equipo(client):
    c = nba_equipos.construir("boston-celtics", nba_equipos.indice(date(2026, 11, 8)), AHORA)
    assert (c.total, c.juzgados, c.aciertos, c.victorias) == (6, 5, 4, 4) and c.indexable and c.proximo and c.proximo["rival"] == LAK
    assert [f["rival"] for f in c.filas][:2] == [LAK, OTR]                              # más recientes primero
    fallo = next(f for f in c.filas if f["fecha"] == date(2026, 11, 4))
    assert fallo["acerto"] is False and fallo["gano"] is False and fallo["resultado"] == "99 – 104"
