"""F3.2 del plan SEO: `/tenis/` y páginas de partido de tenis dentro de la app. Sin feed ni red: los eventos se simulan en
`tenis_datos.eventos`."""
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.routing import Match

from qf.api import main, ratelimit, seo, tenis_datos, tenis_paginas
from test_paginas import Doc

HTML = {"accept": "text/html,application/xhtml+xml"}
BASE = "https://pronosticosdeportivos.pro"
AHORA = datetime(2026, 11, 8, 21, 0, tzinfo=timezone.utc)
HOY = date(2026, 11, 8)
UTC = timezone.utc
SELLO = "2fccf2941770188fc551fbdb563328a8ec6b4a86f7d6ebd601d4d16cbca25181"


def mercado_ganador(fav, p, outcome):
    return {"id": "winner", "label": "Ganador del partido", "selection": fav, "probability": p, "price": None,
            "reference": "Probabilidad del motor", "push_probability": None, "outcome": outcome}


def ev(eid, home, away, start, league, status, score, fav, p, outcome, extra=True, sello=SELLO):
    markets = [mercado_ganador(fav, p, outcome)]
    if extra:
        markets += [{"id": "games_total-2", "label": "Juegos totales", "selection": "Más de 18.5", "probability": 0.635,
                     "price": None, "reference": "Probabilidad del motor; cuota no publicada", "push_probability": 0.0,
                     "outcome": outcome and "win"},
                    {"id": "games_total-4", "label": "Juegos totales", "selection": "Más de 21.5", "probability": 0.448,
                     "price": None, "reference": "Probabilidad del motor; cuota no publicada", "push_probability": 0.0,
                     "outcome": outcome and "loss"}]
    inicio = datetime.fromisoformat(start)
    return {"id": eid, "sport": "tenis", "home": home, "away": away, "start": start, "league": league, "surface": "Hard",
            "sealed_at": (inicio.replace(hour=max(inicio.hour - 2, 0))).isoformat(), "seal": sello, "status": status,
            "score": score, "actionable": False, "markets": markets, "_inicio": inicio.astimezone(UTC)}


# favorito = Boulter (visitante) 57 %; ganó Boulter 0-2: acierto y coherente
E_ACIERTO = ev("12176073", "Viktorija Golubic", "Katie Boulter", "2026-11-08T06:00:00+00:00", "WTA · Hong Kong", "finished", "0 - 2",
               "Katie Boulter", 0.5707, "win")
# favorita = Eala (visitante) 70 %, el mercado dice «loss» y los sets dicen 2-0 para Liu: ganó Liu, coherente, FALLO
E_FALLO = ev("12176074", "Claire Liu", "Alexandra Eala", "2026-11-08T03:00:00+00:00", "WTA · Hong Kong", "finished", "2 - 0",
             "Alexandra Eala", 0.70, "loss")
# LA TRAMPA: el mercado dice que el favorito (Basilashvili, local) ganó, pero el marcador por sets dice 0-2 para Gojo
E_TRAMPA = ev("12176075", "Nikoloz Basilashvili", "Borna Gojo", "2026-11-08T10:00:00+00:00", "ATP · Stockholm", "finished", "0 - 2",
              "Nikoloz Basilashvili", 0.62, "win")
E_PREVIA = ev("12176076", "Jannik Sinner", "Carlos Alcaraz", "2026-11-08T23:00:00+00:00", "ATP · Paris", "scheduled", None,
              "Jannik Sinner", 0.54, None)
E_CANCELADO = ev("12176077", "Elias Ymer", "Jaume Munar", "2026-11-08T11:00:00+00:00", "ATP · Stockholm", "cancelled", None,
                 "Elias Ymer", 0.51, "push")
E_WALKOVER = ev("12176078", "Jacob Fearnley", "Aleksandr Shevchenko", "2026-11-08T09:00:00+00:00", "ATP · Stockholm", "finished", None,
                "Jacob Fearnley", 0.66, "push", extra=False)
E_SIN_RESULTADO = ev("12176079", "Thiago Tirante", "Inaki Montes-De La Torre", "2026-11-07T08:00:00+00:00", "ATP · Stockholm", "no_result", None,
                     "Thiago Tirante", 0.58, None)
E_VIEJO = ev("12176080", "Ana Uno", "Bea Dos", "2026-11-01T08:00:00+00:00", "WTA · Chennai", "finished", "2 - 1", "Ana Uno", 0.6, "win")
EVENTOS = [E_ACIERTO, E_FALLO, E_TRAMPA, E_PREVIA, E_CANCELADO, E_WALKOVER, E_SIN_RESULTADO, E_VIEJO]

U_ACIERTO = "/tenis/wta-hong-kong/viktorija-golubic-vs-katie-boulter-2026-11-08/"
U_FALLO = "/tenis/wta-hong-kong/claire-liu-vs-alexandra-eala-2026-11-08/"
U_TRAMPA = "/tenis/atp-stockholm/nikoloz-basilashvili-vs-borna-gojo-2026-11-08/"
U_PREVIA = "/tenis/atp-paris/jannik-sinner-vs-carlos-alcaraz-2026-11-08/"
U_CANCELADO = "/tenis/atp-stockholm/elias-ymer-vs-jaume-munar-2026-11-08/"
U_WALKOVER = "/tenis/atp-stockholm/jacob-fearnley-vs-aleksandr-shevchenko-2026-11-08/"
U_SIN = "/tenis/atp-stockholm/thiago-tirante-vs-inaki-montes-de-la-torre-2026-11-07/"
U_VIEJO = "/tenis/wta-chennai/ana-uno-vs-bea-dos-2026-11-01/"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(tenis_paginas, "_ahora", lambda: AHORA)
    monkeypatch.setattr(tenis_datos, "hoy_utc", lambda ahora=None: HOY)
    monkeypatch.setattr(tenis_datos, "eventos", lambda: list(EVENTOS))
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


# --- partido --------------------------------------------------------------------------------------

def test_partido_final_trae_todo_en_el_html(client):
    r = client.get(U_ACIERTO, headers=HTML)
    assert r.status_code == 200 and "X-Robots-Tag" not in r.headers
    d = Doc(r.text)
    assert "Viktorija Golubic vs Katie Boulter" in d.title and "WTA Hong Kong" in d.title and "resultado" in d.title
    assert [l["href"] for l in d.links if l.get("rel") == "canonical"] == [BASE + U_ACIERTO]
    robots = [m["content"] for m in d.metas if m.get("name") == "robots"]
    assert len(robots) == 1 and robots[0].startswith("index, follow")
    assert "57 %" in r.text and "43 %" in r.text and SELLO in r.text
    assert "ganó Katie Boulter por 0-2 en sets" in r.text and "Acertó" in r.text
    assert len(d.h1) == 1 and d.h1[0].strip() == d.title.split(" | ")[0]


def test_el_fallo_se_muestra_igual_que_el_acierto(client):
    t = client.get(U_FALLO, headers=HTML).text
    assert "El pronóstico falló" in t and "ganó Claire Liu por 2-0" in t and "Brier" in t and "Falló" in t
    assert "El pronóstico falló" not in client.get(U_ACIERTO, headers=HTML).text


def test_la_trampa_ganador_contra_sets_no_muestra_ni_acierto_ni_fallo(client):
    """El mercado dice que el favorito ganó pero los sets dicen que ganó el rival: no se cuenta ni se afirma nada."""
    r = client.get(U_TRAMPA, headers=HTML)
    assert r.status_code == 200
    t = r.text
    assert "Resultado en revisión" in t
    for prohibido in ("Acertó", "Falló", "El pronóstico falló", "Brier", "ganó Nikoloz", "ganó Borna", "el favorito ganó"):
        assert prohibido not in t, prohibido
    assert "resultado" not in Doc(t).title.lower()                          # el título no promete un resultado
    assert "62 %" in t                                                      # el pronóstico sellado sí se ve
    assert resultado_de(E_TRAMPA)["en_revision"] and not resultado_de(E_TRAMPA)["coherente"]


def resultado_de(e):
    return tenis_paginas.resultado(e)


def test_resultado_solo_es_coherente_si_mercado_y_sets_coinciden():
    assert resultado_de(E_ACIERTO)["coherente"] and resultado_de(E_ACIERTO)["ganador"] == "Katie Boulter"
    assert resultado_de(E_FALLO)["coherente"] and resultado_de(E_FALLO)["ganador"] == "Claire Liu"
    assert resultado_de(E_WALKOVER)["devuelto"] and not resultado_de(E_WALKOVER)["coherente"]
    sin_marcador = {**E_ACIERTO, "score": None}
    assert resultado_de(sin_marcador)["en_revision"]
    empatado = {**E_ACIERTO, "score": "1 - 1"}
    assert resultado_de(empatado)["en_revision"]
    ilegible = {**E_ACIERTO, "score": "6-4 6-3"}
    assert resultado_de(ilegible)["en_revision"]
    assert not resultado_de(E_PREVIA)["coherente"] and not resultado_de(E_PREVIA)["en_revision"]
    assert tenis_paginas.veredicto(E_TRAMPA) is None and tenis_paginas.veredicto(E_PREVIA) is None


def test_veredicto_y_brier():
    v = tenis_paginas.veredicto(E_FALLO)
    assert not v["acerto"] and v["favorito"] == "Alexandra Eala" and v["ganador"] == "Claire Liu"
    assert abs(v["brier"] - 0.70 ** 2) < 1e-9
    assert abs(tenis_paginas.veredicto(E_ACIERTO)["brier"] - (1 - 0.5707) ** 2) < 1e-9


def test_previa_cancelado_walkover_y_sin_resultado_no_inventan_resultado(client):
    previa = client.get(U_PREVIA, headers=HTML).text
    assert "Antes del partido" in previa and "Final:" not in previa and "Brier" not in previa
    assert "Cancelado" in client.get(U_CANCELADO, headers=HTML).text
    wo = client.get(U_WALKOVER, headers=HTML).text
    assert "retirada o un walkover" in wo and "Acertó" not in wo and "Falló" not in wo
    sin = client.get(U_SIN, headers=HTML).text
    assert "Sin resultado oficial" in sin and "Brier" not in sin


def test_la_tabla_de_mercados_lleva_resultado_solo_si_es_coherente(client):
    con = client.get(U_ACIERTO, headers=HTML).text
    assert "Juegos totales" in con and "Más de 21.5" in con and '<th scope="col">Resultado</th>' in con
    sin = client.get(U_TRAMPA, headers=HTML).text
    assert "Juegos totales" in sin and '<th scope="col">Resultado</th>' not in sin


def test_inexistente_o_competicion_equivocada_es_404_html(client):
    for ruta in ("/tenis/atp-paris/nadie-vs-nada-2026-11-08/", "/tenis/atp-paris/viktorija-golubic-vs-katie-boulter-2026-11-08/",
                 "/tenis/wta-hong-kong/no-es-un-partido/", "/tenis/wta-hong-kong/a-vs-b-2026-13-45/"):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 404 and "text/html" in r.headers["content-type"], ruta
        assert 'content="noindex"' in r.text


def test_sin_barra_redirige_y_basura_no_redirige(client):
    r = client.get(U_ACIERTO.rstrip("/"))
    assert r.status_code == 301 and r.headers["location"] == BASE + U_ACIERTO
    assert client.get("/tenis/wta-hong-kong/cualquier-cosa", headers=HTML).status_code == 404
    assert client.get("/tenis").headers["location"] == BASE + "/tenis/"


def test_el_motor_de_tenis_gana_a_las_paginas():
    """`/tenis/v2/metodologia` también encaja en `/tenis/{torneo}/{slug}`: el motor tiene que ser la primera ruta que responde."""
    for ruta in ("/tenis/v2/cartelera", "/tenis/v2/metodologia", "/tenis/v2/partido/123"):
        scope = {"type": "http", "method": "GET", "path": ruta, "root_path": "", "query_string": b"", "headers": []}
        primera = next(r for r in main.app.router.routes if r.matches(scope)[0] == Match.FULL)
        assert primera.endpoint.__module__ == "qf.api.tenis_v2", (ruta, primera.endpoint.__module__)
    assert seo.noindex(type("R", (), {"url": type("U", (), {"path": "/tenis/v2/cartelera"})(), "headers": {}})())


def test_json_ld_valido_y_coherente(client):
    d = Doc(client.get(U_PREVIA, headers=HTML).text)
    tipos = {b["@type"]: b for b in d.ld}
    assert set(tipos) == {"BreadcrumbList", "WebPage"}
    web = tipos["WebPage"]
    assert web["about"]["@type"] == "SportsEvent" and web["about"]["sport"] == "Tennis"
    assert web["about"]["startDate"] == "2026-11-08T23:00:00Z" and web["datePublished"].endswith("Z")
    assert [c["name"] for c in web["about"]["competitor"]] == ["Jannik Sinner", "Carlos Alcaraz"]
    assert [i["item"] for i in tipos["BreadcrumbList"]["itemListElement"]] == [BASE + "/", BASE + "/tenis/", BASE + U_PREVIA]
    cancelado = Doc(client.get(U_CANCELADO, headers=HTML).text)
    assert [b for b in cancelado.ld if b["@type"] == "WebPage"][0]["about"]["eventStatus"].endswith("EventCancelled")


def test_el_partido_se_sirve_dentro_de_la_app_con_su_evento(client):
    t = client.get(U_PREVIA, headers=HTML).text
    assert 'data-ruta="partidos"' in t and 'data-deporte="tenis"' in t
    assert 'data-evento="12176076"' in t and 'data-inicio="2026-11-08T23:00:00+00:00"' in t
    assert re.search(r'<script[^>]+type="module"[^>]+src="/app\.js\?v=', t) and "data-seo-inicial" in t


def test_feed_caido_es_503_no_404(client, monkeypatch):
    def roto():
        raise tenis_datos.TenisNoDisponible("sin feed")
    monkeypatch.setattr(tenis_datos, "eventos", roto)
    for ruta in (U_ACIERTO, "/tenis/"):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 503 and r.headers["retry-after"] == "60" and r.headers["cache-control"] == "no-store", ruta
    assert client.get("/sitemap-paginas.xml").status_code == 200


def test_las_paginas_solo_usan_el_feed_publico():
    import ast
    usados = set()
    for modulo in (tenis_datos, tenis_paginas):
        for nodo in ast.walk(ast.parse(Path(modulo.__file__).read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Name):
                usados.add(nodo.id)
            elif isinstance(nodo, ast.Attribute):
                usados.add(nodo.attr)
            elif isinstance(nodo, ast.alias):
                usados.add(nodo.name.split(".")[-1])
    assert not usados & {"tenis_estadisticas", "tenis_v2", "public_event", "cuotas_web", "tennis_response", "applyTennisQuotes"}


# --- pilar y sitemap ------------------------------------------------------------------------------

def test_pilar_lista_por_torneo_con_enlaces_reales(client):
    r = client.get("/tenis/", headers=HTML)
    assert r.status_code == 200
    d = Doc(r.text)
    for u in (U_ACIERTO, U_FALLO, U_TRAMPA, U_PREVIA, U_CANCELADO, U_WALKOVER, U_SIN):
        assert u in d.hrefs, u
    assert U_VIEJO not in d.hrefs                                            # fuera de la ventana -3..+3
    assert "<h3>WTA Hong Kong</h3>" in r.text and "<h3>ATP Stockholm</h3>" in r.text and "<h3>ATP Paris</h3>" in r.text
    assert "1 de 2" in r.text                                                # solo cuentan los coherentes: Boulter sí, Eala no
    assert "1 partido(s) de la lista tienen el resultado en revisión" in r.text
    assert "resultado en revisión" in r.text
    assert [l["href"] for l in d.links if l.get("rel") == "canonical"] == [BASE + "/tenis/"]
    assert d.ld[1]["@type"] == "CollectionPage" and 'data-deporte="tenis"' in r.text


def _urls(client):
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    salida = {}
    for u in ET.fromstring(client.get("/sitemap-paginas.xml").text).findall("s:url", ns):
        mod = u.find("s:lastmod", ns)
        salida[u.find("s:loc", ns).text] = mod.text if mod is not None else None
    return salida


def test_sitemap_incluye_pilar_y_partidos_de_la_ventana(client):
    u = _urls(client)
    assert BASE + "/tenis/" in u and BASE + U_ACIERTO in u and BASE + U_PREVIA in u and BASE + U_TRAMPA in u
    assert BASE + U_VIEJO not in u
    assert u[BASE + U_PREVIA] == "2026-11-08"                                # sin resultado: día del sello
    assert u[BASE + U_ACIERTO] is None                                       # con resultado no hay hora de cierre verificable
    assert client.get(U_VIEJO, headers=HTML).status_code == 200              # pero la página sigue existiendo


def test_las_rutas_de_tenis_son_las_cuatro_de_las_paginas_mas_el_motor():
    rutas = {getattr(r, "path", "") for r in main.app.routes if getattr(r, "path", "").startswith("/tenis")}
    assert {"/tenis/", "/tenis", "/tenis/{torneo}/{slug}/", "/tenis/{torneo}/{slug}"} <= rutas
    assert {r for r in rutas if r.startswith("/tenis/v2")} >= {"/tenis/v2/cartelera", "/tenis/v2/metodologia"}


def test_slugs_de_torneo_y_nombres():
    assert tenis_datos.torneo_slug(E_ACIERTO) == "wta-hong-kong" and tenis_datos.torneo_nombre(E_ACIERTO) == "WTA Hong Kong"
    assert tenis_datos.slug_partido(E_SIN := E_SIN_RESULTADO).startswith("thiago-tirante-vs-inaki-montes-de-la-torre-")
    assert tenis_datos.buscar_partido("v2", "a-vs-b-2026-11-08") is None


def test_titulos_caben_en_un_resultado_de_busqueda(client):
    for u in (U_ACIERTO, U_FALLO, U_PREVIA, U_SIN):
        assert len(Doc(client.get(u, headers=HTML).text).title) <= 95, u
