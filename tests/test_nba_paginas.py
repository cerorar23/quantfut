"""F2.1 del plan SEO: pilar `/nba/` y páginas de partido NBA con HTML completo. `nba-api` se simula: sin red, sin base."""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from qf.api import main, nba_datos, nba_paginas, ratelimit, seo
from test_paginas import Doc   # lector de HTML ya probado

HTML = {"accept": "text/html,application/xhtml+xml"}
BASE = "https://pronosticosdeportivos.pro"
AHORA = datetime(2026, 11, 8, 21, 0, tzinfo=timezone.utc)      # 16:00 ET del 8-nov
HASH = "4ffddfdb5b30ee4662554760a642b56733a568bdcf88ae6dead6c729c8329343"
SLUG_FINAL = "chicago-bulls-vs-philadelphia-76ers-2026-11-08"
SLUG_PREVIA = "boston-celtics-vs-los-angeles-lakers-2026-11-08"
SLUG_SIN_SELLO = "miami-heat-vs-new-york-knicks-2026-11-08"
SLUG_FALLO = "denver-nuggets-vs-utah-jazz-2026-11-07"


def partido(pid, local, visit, fecha, inicio, p_local=0.37, resultado=None, sello=True, hash_=HASH):
    pron = None
    if sello:
        pron = {"hash": hash_, "version_modelo": "equipo-2.2;posesiones;ratings-local",
                "objetivo_en": "2026-11-08T19:30:00+00:00", "sellado_en": "2026-11-08T19:31:11.849865+00:00",
                "p_local": p_local, "mu": [111.7822, 116.4725], "escenarios": {},
                "margen_p10_p90": [-23.0, 13.0], "total_p10_p90": [204.0, 253.0],
                "mediana": {"margen": -5.0, "total": 228.0}}
    return {"id": pid, "fecha": fecha, "local": {"codigo": local[:3].upper(), "nombre": local},
            "visitante": {"codigo": visit[:3].upper(), "nombre": visit}, "inicio_utc": inicio,
            "sello_previsto": None, "resultado": resultado, "pronostico": pron}


DIAS = {
    "2026-11-08": [
        partido(18220, "Chicago Bulls", "Philadelphia 76ers", "2026-11-08", "2026-11-08T20:30:00+00:00",
                resultado={"local": 121.0, "visitante": 127.0}),
        partido(18221, "Boston Celtics", "Los Angeles Lakers", "2026-11-08", "2026-11-08T23:30:00+00:00",
                p_local=0.62, hash_="a" * 64),
        partido(18222, "Miami Heat", "New York Knicks", "2026-11-08", "2026-11-09T00:30:00+00:00", sello=False),
    ],
    "2026-11-07": [
        partido(18200, "Denver Nuggets", "Utah Jazz", "2026-11-07", "2026-11-08T00:00:00+00:00", p_local=0.80,
                resultado={"local": 110.0, "visitante": 118.0}, hash_="b" * 64),
    ],
}
ESTADISTICAS = {"teams": [
    {"name": "Chicago Bulls", "season": {"won": 1, "lost": 7, "rate": .125}, "last6": {"won": 0, "lost": 6},
     "streak": -6, "rest_days": 3, "back_to_back": False},
    {"name": "Philadelphia 76ers", "season": {"won": 6, "lost": 2, "rate": .75}, "last6": {"won": 5, "lost": 1},
     "streak": 2, "rest_days": 1, "back_to_back": True},
]}


def _roto(ruta, params=None):
    raise nba_datos.NbaNoDisponible("caído")


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
            if ruta.split("/")[4] == "18220":
                return ESTADISTICAS
            raise nba_datos.NbaNoDisponible("sin estadísticas")
        raise AssertionError(ruta)

    monkeypatch.setattr(nba_datos, "_pedir", falso)
    yield TestClient(main.app, base_url=BASE, follow_redirects=False)
    nba_datos.vaciar_cache()


def _request(path):
    return Request({"type": "http", "method": "GET", "path": path, "query_string": b"",
                    "headers": [(b"host", b"pronosticosdeportivos.pro")]})


# --- partido --------------------------------------------------------------------------------------

def test_partido_final_trae_todo_en_el_html(client):
    r = client.get(f"/nba/{SLUG_FINAL}/", headers=HTML)
    assert r.status_code == 200 and "X-Robots-Tag" not in r.headers
    d = Doc(r.text)
    assert d.lang == "es" and "Chicago Bulls vs Philadelphia 76ers" in d.title and "resultado" in d.title
    assert [l["href"] for l in d.links if l.get("rel") == "canonical"] == [f"{BASE}/nba/{SLUG_FINAL}/"]
    robots = [m["content"] for m in d.metas if m.get("name") == "robots"]
    assert len(robots) == 1 and robots[0].startswith("index, follow")
    assert "37 %" in r.text and "63 %" in r.text                       # probabilidades en el HTML, sin JS
    assert HASH in r.text and f"/nba/v1/sello/{HASH}" in d.hrefs
    assert "121" in r.text and "127" in r.text
    assert len(d.h1) == 1 and d.h1[0].strip() == d.title.split(" | ")[0]


def test_el_fallo_se_muestra_igual_que_el_acierto(client):
    acierto = client.get(f"/nba/{SLUG_FINAL}/", headers=HTML).text     # favorito visitante (63 %) ganó
    assert "ganó" in acierto and "El pronóstico falló" not in acierto
    fallo = client.get(f"/nba/{SLUG_FALLO}/", headers=HTML).text        # 80 % local, ganó el visitante
    assert "El pronóstico falló" in fallo and "Utah Jazz" in fallo and "Brier" in fallo


def test_partido_previa_no_inventa_resultado(client):
    t = client.get(f"/nba/{SLUG_PREVIA}/", headers=HTML).text
    assert "Antes del partido" in t and "Final:" not in t and "Brier" not in t
    assert "62 %" in t and "38 %" in t


def test_sin_sello_o_inexistente_es_404_html(client):
    for slug in (SLUG_SIN_SELLO, "equipo-a-vs-equipo-b-2026-11-08", "no-es-un-partido", "a-vs-b-2026-13-45"):
        r = client.get(f"/nba/{slug}/", headers=HTML)
        assert r.status_code == 404 and "text/html" in r.headers["content-type"], slug
        assert 'content="noindex"' in r.text


def test_sin_barra_redirige_y_basura_no_redirige(client):
    r = client.get(f"/nba/{SLUG_FINAL}")
    assert r.status_code == 301 and r.headers["location"] == f"{BASE}/nba/{SLUG_FINAL}/"
    assert client.get("/nba/cualquier-cosa", headers=HTML).status_code == 404
    assert client.get("/nba").headers["location"] == f"{BASE}/nba/"


def test_rutas_del_motor_no_son_paginas(client):
    for ruta in ("/nba/v1/", "/nba/v2/", "/nba/v2"):
        assert client.get(ruta, headers=HTML).status_code == 404, ruta
    assert nba_paginas.RESERVADOS == {"v1", "v2"}


def test_noindex_solo_en_los_prefijos_del_motor():
    for privado in ("/nba/v1/cartelera", "/nba/v1", "/nba/v2", "/nba/v2/", "/nba/v2/app.js"):
        assert seo.noindex(_request(privado)), privado
    for publico in ("/nba/", f"/nba/{SLUG_FINAL}/", "/nba/v10-algo/"):
        assert not seo.noindex(_request(publico)), publico


def test_json_ld_valido_y_coherente(client):
    d = Doc(client.get(f"/nba/{SLUG_PREVIA}/", headers=HTML).text)
    tipos = {b["@type"]: b for b in d.ld}
    assert set(tipos) == {"BreadcrumbList", "WebPage"}
    web = tipos["WebPage"]
    assert web["url"] == f"{BASE}/nba/{SLUG_PREVIA}/" and web["about"]["@type"] == "SportsEvent"
    assert web["about"]["startDate"] == "2026-11-08T23:30:00Z" and web["datePublished"].endswith("Z")
    assert web["about"]["homeTeam"]["name"] == "Boston Celtics"
    assert [i["item"] for i in tipos["BreadcrumbList"]["itemListElement"]] == [
        f"{BASE}/", f"{BASE}/nba/", f"{BASE}/nba/{SLUG_PREVIA}/"]


def test_contexto_de_temporada_es_opcional(client):
    con = client.get(f"/nba/{SLUG_FINAL}/", headers=HTML).text
    assert "Contexto de la temporada" in con and "1-7" in con
    assert "partido en dos noches seguidas" in con and "6 derrotas seguidas" in con
    sin = client.get(f"/nba/{SLUG_PREVIA}/", headers=HTML)             # las estadísticas fallan: la página no cae
    assert sin.status_code == 200 and "Contexto de la temporada" not in sin.text


def test_descripcion_con_longitud_razonable(client):
    for slug in (SLUG_FINAL, SLUG_PREVIA):
        metas = Doc(client.get(f"/nba/{slug}/", headers=HTML).text).metas
        desc = [m["content"] for m in metas if m.get("name") == "description"][0]
        assert 100 <= len(desc) <= 200, desc


def test_estados_segun_la_hora():
    p = DIAS["2026-11-08"][1]
    assert nba_paginas.estado(p, datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc)) == "previa"
    assert nba_paginas.estado(p, datetime(2026, 11, 8, 23, 45, tzinfo=timezone.utc)) == "curso"
    assert nba_paginas.estado(p, datetime(2026, 11, 9, 9, 0, tzinfo=timezone.utc)) == "pendiente"
    assert nba_paginas.estado(DIAS["2026-11-08"][0], datetime(2026, 11, 8, 20, 0, tzinfo=timezone.utc)) == "final"


def test_veredicto_y_brier():
    v = nba_paginas.veredicto(DIAS["2026-11-08"][0])
    assert v["acerto"] and v["favorito"] == "Philadelphia 76ers" and abs(v["brier"] - 0.37 ** 2) < 1e-9
    assert nba_paginas.veredicto(DIAS["2026-11-08"][1]) is None


# --- pilar ----------------------------------------------------------------------------------------

def test_pilar_lista_con_enlaces_reales(client):
    r = client.get("/nba/", headers=HTML)
    assert r.status_code == 200
    d = Doc(r.text)
    assert f"/nba/{SLUG_FINAL}/" in d.hrefs and f"/nba/{SLUG_PREVIA}/" in d.hrefs
    assert not any(SLUG_SIN_SELLO in h for h in d.hrefs)                # sin sello: texto, no enlace
    assert "Miami Heat vs New York Knicks" in r.text and "pendiente de sellar" in r.text
    assert "1 de 2" in r.text                                          # Chicago-PHI acertó, Denver-Utah falló
    assert [l["href"] for l in d.links if l.get("rel") == "canonical"] == [f"{BASE}/nba/"]
    assert d.ld[1]["@type"] == "CollectionPage"


def test_pilar_sin_motor_es_503_no_404(client, monkeypatch):
    nba_datos.vaciar_cache()
    monkeypatch.setattr(nba_datos, "_pedir", _roto)
    r = client.get("/nba/", headers=HTML)
    assert r.status_code == 503 and r.headers["retry-after"] == "60" and r.headers["cache-control"] == "no-store"
    assert client.get(f"/nba/{SLUG_FINAL}/", headers=HTML).status_code == 503


def test_copia_guardada_cubre_una_caida(client, monkeypatch):
    assert client.get(f"/nba/{SLUG_FINAL}/", headers=HTML).status_code == 200
    monkeypatch.setattr(nba_datos, "_pedir", _roto)
    monkeypatch.setattr(nba_datos, "TTL_VIVO_S", 0)
    monkeypatch.setattr(nba_datos, "TTL_PASADO_S", 0)
    assert client.get(f"/nba/{SLUG_FINAL}/", headers=HTML).status_code == 200


# --- sitemap --------------------------------------------------------------------------------------

def _urls(client):
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    raiz = ET.fromstring(client.get("/sitemap-paginas.xml").text)
    salida = {}
    for u in raiz.findall("s:url", ns):
        mod = u.find("s:lastmod", ns)
        salida[u.find("s:loc", ns).text] = mod.text if mod is not None else None
    return salida


def test_sitemap_incluye_pilar_y_partidos_con_sello(client):
    u = _urls(client)
    assert f"{BASE}/nba/" in u
    assert f"{BASE}/nba/{SLUG_PREVIA}/" in u and f"{BASE}/nba/{SLUG_FINAL}/" in u
    assert not any(SLUG_SIN_SELLO in k for k in u)
    assert u[f"{BASE}/nba/{SLUG_PREVIA}/"] == "2026-11-08"             # sin marcador: día del sello
    assert u[f"{BASE}/nba/{SLUG_FINAL}/"] is None                      # con marcador no hay hora de cierre verificable


def test_sitemap_sobrevive_sin_motor(client, monkeypatch):
    nba_datos.vaciar_cache()
    monkeypatch.setattr(nba_datos, "_pedir", _roto)
    assert client.get("/sitemap-paginas.xml").status_code == 200
    u = _urls(client)
    assert f"{BASE}/nba/" in u and not any(re.search(r"-vs-", k) for k in u)


def test_slugs_sin_acentos_ni_simbolos():
    assert nba_datos.slug_texto("Portland Trail Blazers") == "portland-trail-blazers"
    assert nba_datos.slug_texto("Dallas  Mavericks!") == "dallas-mavericks"
    assert nba_datos.SLUG_PARTIDO.match("a-vs-b-2026-11-08") and not nba_datos.SLUG_PARTIDO.match("a-b-2026-11-08")


def test_titulos_caben_en_un_resultado_de_busqueda(client):
    for slug in (SLUG_FINAL, SLUG_PREVIA, SLUG_FALLO):
        titulo = Doc(client.get(f"/nba/{slug}/", headers=HTML).text).title
        assert len(titulo) <= 85, titulo


def test_la_portada_enlaza_al_pilar_de_nba(client):
    assert "/nba/" in Doc(client.get("/", headers=HTML).text).hrefs
    assert "/nba/" in Doc(client.get("/historial/", headers=HTML).text).hrefs
    assert "/nba/" in Doc(client.get("/metodologia/", headers=HTML).text).hrefs


# --- shell de la SPA -------------------------------------------------------------------------------

def test_el_partido_se_sirve_dentro_de_la_app_con_su_evento(client):
    t = client.get(f"/nba/{SLUG_PREVIA}/", headers=HTML).text
    assert '<html' in t and 'data-ruta="partidos"' in t and 'data-deporte="nba"' in t
    assert 'data-evento="18221"' in t and 'data-inicio="2026-11-08T23:30:00+00:00"' in t
    assert re.search(r'<script[^>]+type="module"[^>]+src="/app\.js\?v=', t)       # la app arranca, con ruta absoluta
    assert 'data-seo-inicial' in t and 'id="app"' in t


def test_el_pilar_arranca_en_nba_sin_evento(client):
    t = client.get("/nba/", headers=HTML).text
    assert 'data-ruta="partidos"' in t and 'data-deporte="nba"' in t and "data-evento" not in t
    assert re.search(r'<script[^>]+src="/app\.js\?v=', t)


def test_la_pagina_no_pierde_el_contenido_si_el_index_cambia(client, caplog):
    import logging
    from qf.api import rutas_web
    roto = "<html><body>sin marcas</body></html>"
    with caplog.at_level(logging.ERROR, logger="qf.api.rutas_web"):
        out = rutas_web.render_pagina(titulo="T", descripcion="d", path="/nba/", ruta="partidos", jsonld=[],
                                      principal="<h1>x</h1>", index=roto)
    assert out == roto and "no tiene las marcas esperadas" in caplog.text


# --- caché: servir lo caducado al instante y renovar en segundo plano ------------------------------

def test_lo_caducado_se_sirve_al_instante_y_se_renueva_aparte(monkeypatch):
    nba_datos.vaciar_cache()
    pendientes, llamadas = [], []
    versiones = iter(["v1", "v2", "v3"])

    def pedir(ruta, params=None):
        llamadas.append(params)
        return {"partidos": [next(versiones)]}
    monkeypatch.setattr(nba_datos, "_pedir", pedir)
    monkeypatch.setattr(nba_datos, "_lanzar", pendientes.append)
    monkeypatch.setattr(nba_datos, "TTL_VIVO_S", 0)                      # todo caduca al instante
    primera = nba_datos._con_cache("k", 0, "/x")
    assert primera == {"partidos": ["v1"]} and len(llamadas) == 1        # sin copia: espera y pide
    segunda = nba_datos._con_cache("k", 0, "/x")
    assert segunda == {"partidos": ["v1"]} and len(llamadas) == 1        # caducada: se sirve YA, sin esperar a nba-api
    assert len(pendientes) == 1
    nba_datos._con_cache("k", 0, "/x")
    assert len(pendientes) == 1                                          # una sola renovación a la vez por clave
    pendientes[0]()                                                      # termina la renovación
    assert nba_datos._cache["k"][1] == {"partidos": ["v2"]}              # la copia ya es la nueva
    assert nba_datos._con_cache("k", 0, "/x") == {"partidos": ["v2"]} and len(pendientes) == 2   # se sirve la nueva y se vuelve a renovar
    nba_datos.vaciar_cache()


def test_una_renovacion_fallida_conserva_la_copia_y_se_reintenta(monkeypatch):
    nba_datos.vaciar_cache()
    pendientes = []
    monkeypatch.setattr(nba_datos, "_lanzar", pendientes.append)
    monkeypatch.setattr(nba_datos, "_pedir", lambda ruta, params=None: {"partidos": ["buena"]})
    nba_datos._con_cache("k", 0, "/x")
    monkeypatch.setattr(nba_datos, "_pedir", lambda ruta, params=None: (_ for _ in ()).throw(nba_datos.NbaNoDisponible("caído")))
    assert nba_datos._con_cache("k", 0, "/x") == {"partidos": ["buena"]}
    pendientes.pop()()                                                   # la renovación falla sin romper nada
    assert nba_datos._cache["k"][1] == {"partidos": ["buena"]} and "k" not in nba_datos._renovando
    assert nba_datos._con_cache("k", 0, "/x") == {"partidos": ["buena"]} and len(pendientes) == 1   # se reintenta
    nba_datos.vaciar_cache()


def test_pasada_una_hora_ya_no_se_sirve_lo_viejo_sin_esperar(monkeypatch):
    nba_datos.vaciar_cache()
    monkeypatch.setattr(nba_datos, "_lanzar", lambda t: pytest.fail("no debe renovar en segundo plano: la copia es demasiado vieja"))
    versiones = iter(["viejo", "nuevo"])
    monkeypatch.setattr(nba_datos, "_pedir", lambda ruta, params=None: {"partidos": [next(versiones)]})
    nba_datos._con_cache("k", 0, "/x")
    clave, (t, v) = next(iter(nba_datos._cache.items()))
    nba_datos._cache[clave] = (t - nba_datos.STALE_MAX_S - 1, v)         # la copia tiene más de una hora
    assert nba_datos._con_cache("k", 0, "/x") == {"partidos": ["nuevo"]}  # espera y trae lo nuevo
    nba_datos.vaciar_cache()
