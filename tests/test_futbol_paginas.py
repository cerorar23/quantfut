"""F3.1 del plan SEO: `/futbol/` y páginas de partido de fútbol dentro de la app. Sin base ni red: los datos se simulan
en `futbol_datos` (agenda, pronósticos, ficha y configuración)."""
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from qf.api import fichas, futbol_datos, futbol_paginas, main, ratelimit
from qf.api.futbol_datos import pronosticos as pronosticos_real   # la real: el conftest parchea el atributo del módulo
from test_paginas import Doc

HTML = {"accept": "text/html,application/xhtml+xml"}
BASE = "https://pronosticosdeportivos.pro"
AHORA = datetime(2026, 11, 8, 21, 0, tzinfo=timezone.utc)           # 15:00 del 8-nov en México
UTC = timezone.utc
GENERADA = datetime(2026, 11, 8, 9, 0, 3, tzinfo=UTC)               # corrida de las 03:00 de México


def fila(mid, ko, liga_id, liga, pais, local, visit, marcador=None, estado="scheduled"):
    return {"match_id": mid, "kickoff_utc": ko, "estado": estado, "marcador": marcador,
            "liga": {"id": liga_id, "nombre": liga, "pais": pais},
            "local": {"id": 1, "nombre": local, "escudo": None, "posicion": 3, "racha": "GGPEG"},
            "visitante": {"id": 2, "nombre": visit, "escudo": None, "posicion": 9, "racha": "PPEGP"}}


F_FINAL = fila("es.laliga:2627:real-madrid-sevilla:20261108", datetime(2026, 11, 8, 18, 0, tzinfo=UTC), "es.laliga", "LaLiga",
               "Spain", "Real Madrid", "Sevilla", marcador=[0, 2], estado="finished")
F_PREVIA = fila("mx.liga_mx:2627:queretaro-puebla:20261109", datetime(2026, 11, 9, 0, 0, tzinfo=UTC), "mx.liga_mx", "Liga MX",
                "Mexico", "Club Queretaro", "Puebla")
F_SIN = fila("mx.liga_mx:2627:chivas-pumas:20261109", datetime(2026, 11, 9, 2, 0, tzinfo=UTC), "mx.liga_mx", "Liga MX",
             "Mexico", "Guadalajara", "Pumas UNAM")
F_COPA = fila("eu.ucl:2627:inter-benfica:20261109", datetime(2026, 11, 8, 20, 0, tzinfo=UTC), "eu.ucl", "UEFA Champions League",
              "Europe", "Inter", "Benfica")
F_AZUL = fila("es.laliga:2627:valencia-betis:20261108", datetime(2026, 11, 8, 12, 0, tzinfo=UTC), "es.laliga", "LaLiga",
              "Spain", "Valencia", "Betis", marcador=[3, 0], estado="finished")

FILAS = {"2026-11-08": [F_FINAL, F_PREVIA, F_COPA, F_AZUL], "2026-11-09": [F_SIN]}
# La corrida diaria del 8-nov cubre los partidos de ese día de México (los de la noche UTC incluidos).
PRON = {
    F_FINAL["match_id"]: {"probs": {"home": 0.62, "draw": 0.22, "away": 0.16}, "modelo": True, "generada": GENERADA},
    F_PREVIA["match_id"]: {"probs": {"home": 0.5028, "draw": 0.2624, "away": 0.2348}, "modelo": True, "generada": GENERADA},
    F_COPA["match_id"]: {"probs": {"home": 0.48, "draw": 0.27, "away": 0.25}, "modelo": False, "generada": GENERADA},
    F_AZUL["match_id"]: {"probs": {"home": 0.55, "draw": 0.25, "away": 0.20}, "modelo": True, "generada": GENERADA},
}


def ficha(local, visit, liga="LaLiga"):
    lado = lambda nombre, pos, racha: {"nombre": nombre, "forma": {"resumen": {"n": 5, "racha": racha, "puntos": 7, "gf": 8, "gc": 5}},
                                       "clasificacion": {"posicion": pos, "puntos": 20, "liga": liga}}
    return {"local": lado(local, 2, "GGPEG"), "visitante": lado(visit, 9, "PPEGP"),
            "cara_a_cara": {"resumen": {"n": 6, "victorias_local": 3, "empates": 2, "victorias_visitante": 1, "goles_media": 2.67}}}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DOMAIN", "pronosticosdeportivos.pro")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    monkeypatch.setattr(ratelimit, "rate_limited", lambda *a, **k: False)
    monkeypatch.setattr(futbol_paginas, "_ahora", lambda: AHORA)
    # La agenda por defecto (la del sitemap) usa el día real: se fija al de AHORA para que los datos de prueba sigan en su ventana.
    monkeypatch.setattr(futbol_datos, "hoy_mx", lambda ahora=None: AHORA.astimezone(futbol_datos.MEXICO).date())
    fichas._cache.clear()
    monkeypatch.setattr(futbol_datos, "agenda_dia", lambda d: FILAS.get(d.isoformat(), []))
    monkeypatch.setattr(futbol_datos, "pronosticos", lambda ids: {i: PRON[i] for i in ids if i in PRON})
    monkeypatch.setattr(futbol_datos, "secciones_activas", lambda: {"estadisticas": True, "h2h": True})
    monkeypatch.setattr(futbol_datos, "ficha", lambda mid: {
        F_FINAL["match_id"]: ficha("Real Madrid", "Sevilla"),
        F_PREVIA["match_id"]: ficha("Club Queretaro", "Puebla", "Liga MX"),
        F_COPA["match_id"]: ficha("Inter", "Benfica", "Serie A"),
    }.get(mid))
    return TestClient(main.app, base_url=BASE, follow_redirects=False)


URL_FINAL = "/futbol/laliga/real-madrid-vs-sevilla-2026-11-08/"
URL_PREVIA = "/futbol/liga-mx/club-queretaro-vs-puebla-2026-11-08/"       # 00:00 UTC del 9 = 18:00 del 8 en México
URL_COPA = "/futbol/uefa-champions-league/inter-vs-benfica-2026-11-08/"


# --- partido --------------------------------------------------------------------------------------

def test_partido_final_trae_todo_en_el_html(client):
    r = client.get(URL_FINAL, headers=HTML)
    assert r.status_code == 200 and "X-Robots-Tag" not in r.headers
    d = Doc(r.text)
    assert "Real Madrid vs Sevilla" in d.title and "LaLiga" in d.title and "resultado" in d.title
    assert [l["href"] for l in d.links if l.get("rel") == "canonical"] == [BASE + URL_FINAL]
    robots = [m["content"] for m in d.metas if m.get("name") == "robots"]
    assert len(robots) == 1 and robots[0].startswith("index, follow")
    assert "62 %" in r.text and "22 %" in r.text and "16 %" in r.text          # 1X2 en el HTML, sin JS
    assert "Real Madrid 0, Sevilla 2" in r.text
    assert len(d.h1) == 1 and d.h1[0].strip() == d.title.split(" | ")[0]


def test_el_fallo_se_muestra_igual_que_el_acierto(client):
    fallo = client.get(URL_FINAL, headers=HTML).text                         # 62 % local y ganó el visitante
    assert "El pronóstico falló" in fallo and "Sevilla" in fallo and "Brier" in fallo
    acierto = client.get("/futbol/laliga/valencia-vs-betis-2026-11-08/", headers=HTML).text   # 55 % local y ganó
    assert "se cumplió" in acierto and "El pronóstico falló" not in acierto


def test_la_fecha_de_la_url_es_la_de_mexico_no_la_utc(client):
    assert F_PREVIA["match_id"].endswith(":20261109")                         # el match_id lleva la fecha UTC
    assert futbol_datos.ruta_partido(F_PREVIA) == URL_PREVIA                  # la URL, la de México
    assert client.get(URL_PREVIA, headers=HTML).status_code == 200
    assert client.get(URL_PREVIA.replace("11-08", "11-09"), headers=HTML).status_code == 404


def test_previa_no_inventa_resultado(client):
    t = client.get(URL_PREVIA, headers=HTML).text
    assert "Antes del partido" in t and "Final:" not in t and "Brier" not in t
    assert "50 %" in t and "26 %" in t and "23 %" in t


def test_sin_pronostico_competicion_equivocada_o_inexistente_es_404(client):
    for ruta in ("/futbol/liga-mx/guadalajara-vs-pumas-unam-2026-11-08/",        # sin pronóstico generado
                 "/futbol/laliga/club-queretaro-vs-puebla-2026-11-08/",           # competición que no es la suya
                 "/futbol/liga-mx/nadie-vs-nada-2026-11-08/", "/futbol/liga-mx/no-es-un-partido/",
                 "/futbol/liga-mx/a-vs-b-2026-13-45/"):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 404 and "text/html" in r.headers["content-type"], ruta
        assert 'content="noindex"' in r.text


def test_competicion_y_liga_no_son_lo_mismo_en_las_copas(client):
    t = client.get(URL_COPA, headers=HTML).text
    assert "UEFA Champions League" in t
    assert "en Serie A con 20 puntos" in t and "clasificación es la de la liga doméstica" in t   # puesto en su liga, no en la copa
    assert "el modelo propio todavía no conoce" in t and "consenso del mercado" in t          # 1X2 de mercado, no del modelo


def test_los_nombres_de_competicion_son_unicos_y_sin_acentos():
    nombres = ["Liga Profesional", "Brasileirão Série A", "Premier League", "UEFA Champions League", "UEFA Europa League",
               "Ligue 1", "Bundesliga", "Serie A", "Liga MX", "Eredivisie", "Eliteserien", "Primeira Liga", "LaLiga",
               "Süper Lig", "Major League Soccer", "Championship", "2. Bundesliga"]
    slugs = [futbol_datos.competicion_slug(n) for n in nombres]
    assert len(set(slugs)) == len(slugs)
    assert all(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", s) for s in slugs)
    assert "super-lig" in slugs and "brasileirao-serie-a" in slugs


def test_sin_barra_redirige_y_basura_no_redirige(client):
    r = client.get(URL_FINAL.rstrip("/"))
    assert r.status_code == 301 and r.headers["location"] == BASE + URL_FINAL
    assert client.get("/futbol/liga-mx/cualquier-cosa", headers=HTML).status_code == 404
    assert client.get("/futbol").headers["location"] == BASE + "/futbol/"


def test_json_ld_valido_y_coherente(client):
    d = Doc(client.get(URL_PREVIA, headers=HTML).text)
    tipos = {b["@type"]: b for b in d.ld}
    assert set(tipos) == {"BreadcrumbList", "WebPage"}
    web = tipos["WebPage"]
    assert web["about"]["@type"] == "SportsEvent" and web["about"]["sport"] == "Soccer"
    assert web["about"]["startDate"] == "2026-11-09T00:00:00Z" and web["datePublished"] == "2026-11-08T09:00:03Z"
    assert web["about"]["homeTeam"]["name"] == "Club Queretaro"
    assert [i["item"] for i in tipos["BreadcrumbList"]["itemListElement"]] == [BASE + "/", BASE + "/futbol/", BASE + URL_PREVIA]


def test_el_partido_se_sirve_dentro_de_la_app_con_su_evento(client):
    t = client.get(URL_PREVIA, headers=HTML).text
    assert 'data-ruta="partidos"' in t and 'data-deporte="futbol"' in t
    assert f'data-evento="{F_PREVIA["match_id"]}"' in t and 'data-inicio="2026-11-09T00:00:00+00:00"' in t
    assert re.search(r'<script[^>]+type="module"[^>]+src="/app\.js\?v=', t) and "data-seo-inicial" in t


def test_contexto_y_cara_a_cara_respetan_la_configuracion(client, monkeypatch):
    con = client.get(URL_FINAL, headers=HTML).text
    assert "Forma reciente y clasificación" in con and "Cara a cara" in con and "2.º en LaLiga con 20 puntos" in con
    monkeypatch.setattr(futbol_datos, "secciones_activas", lambda: {"estadisticas": True, "h2h": False})
    sin_h2h = client.get(URL_FINAL, headers=HTML).text
    assert "Forma reciente y clasificación" in sin_h2h and "Cara a cara" not in sin_h2h
    monkeypatch.setattr(futbol_datos, "secciones_activas", lambda: {"estadisticas": False, "h2h": True})
    assert client.get(URL_FINAL, headers=HTML).status_code == 404            # sin estadísticas no hay probabilidades públicas
    assert client.get("/futbol/", headers=HTML).status_code == 404


def test_la_ficha_ausente_no_tumba_la_pagina(client, monkeypatch):
    monkeypatch.setattr(futbol_datos, "ficha", lambda mid: None)
    r = client.get(URL_FINAL, headers=HTML)
    assert r.status_code == 200 and "Forma reciente" not in r.text and "62 %" in r.text


def test_base_caida_es_503_no_404(client, monkeypatch):
    def roto(*a, **k):
        raise futbol_datos.FutbolNoDisponible("caída")
    monkeypatch.setattr(futbol_datos, "agenda_dia", roto)
    for ruta in (URL_FINAL, "/futbol/"):
        r = client.get(ruta, headers=HTML)
        assert r.status_code == 503 and r.headers["retry-after"] == "60" and r.headers["cache-control"] == "no-store", ruta
    assert client.get("/sitemap-paginas.xml").status_code == 200


# --- sin VIP --------------------------------------------------------------------------------------

def test_las_paginas_no_consultan_picks_alta_probabilidad_ni_escalera(client, monkeypatch):
    """El contenido que puede ser VIP vive en `mobile.high_probability/ladder/detail`: si esas funciones explotan al
    llamarlas, las páginas siguen funcionando, y su código fuente no las nombra."""
    from qf.api import mobile

    def prohibido(*a, **k):
        raise AssertionError("una página pública de fútbol no puede consultar picks")
    for nombre in ("high_probability", "ladder", "detail", "high_rows", "mercados_partido", "market_card", "allocations"):
        monkeypatch.setattr(mobile, nombre, prohibido)
    for ruta in (URL_FINAL, URL_PREVIA, URL_COPA, "/futbol/"):
        assert client.get(ruta, headers=HTML).status_code == 200, ruta
    import ast
    usados = set()
    for modulo in (futbol_datos, futbol_paginas):
        for nodo in ast.walk(ast.parse(Path(modulo.__file__).read_text(encoding="utf-8"))):
            if isinstance(nodo, ast.Name):
                usados.add(nodo.id)
            elif isinstance(nodo, ast.Attribute):
                usados.add(nodo.attr)
            elif isinstance(nodo, ast.alias):
                usados.add(nodo.name.split(".")[-1])
    prohibidos = {"high_probability", "ladder", "detail", "high_rows", "mercados_partido", "market_card", "allocations",
                  "partido_mercados", "alta_prob_picks", "rewards", "member", "plus", "choose_free", "visible_agenda"}
    assert not usados & prohibidos, usados & prohibidos


def test_el_html_no_lleva_mercados_ni_cuotas(client):
    for ruta in (URL_FINAL, URL_PREVIA, URL_COPA, "/futbol/"):
        # El enlace de navegación a la calculadora de cuota justa (una herramienta educativa) no es un mercado ni una cuota del partido.
        t = client.get(ruta, headers=HTML).text.lower().replace("/calculadora-cuota-justa/", "").replace(">cuota justa<", "><")
        for palabra in ("cuota", "más de 2,5", "más de 2.5", "ambos marcan", "suscripción vip", "candado"):
            assert palabra not in t.split('id="app"', 1)[-1], (ruta, palabra)


# --- pronósticos: solo los anteriores al inicio ---------------------------------------------------

def test_solo_cuentan_los_pronosticos_generados_antes_del_inicio(monkeypatch):
    import qf.db
    visto = {}

    def consulta(sql, params=None):
        visto["sql"] = sql
        return [{"match_id": "a:1:x-y:20261108", "markets": {"1x2": {"home": .5, "draw": .3, "away": .2}},
                 "market_consensus": None, "conocido": "true", "generated_at": GENERADA},
                {"match_id": "b:1:z-w:20261108", "markets": {}, "market_consensus": {"home": 2.0, "draw": 3.0, "away": 4.0},
                 "conocido": "false", "generated_at": GENERADA},
                {"match_id": "c:1:p-q:20261108", "markets": {}, "market_consensus": None, "conocido": "true",
                 "generated_at": GENERADA}]
    monkeypatch.setattr(qf.db, "query", consulta)
    fichas._cache.clear()
    ids = ["a:1:x-y:20261108", "b:1:z-w:20261108", "c:1:p-q:20261108"]
    salida = pronosticos_real(ids)
    assert "p.generated_at < m.kickoff_utc" in visto["sql"]
    assert salida[ids[0]]["modelo"] is True and salida[ids[0]]["probs"]["home"] == .5
    assert salida[ids[1]]["modelo"] is False                                  # consenso del mercado sin margen
    assert abs(sum(salida[ids[1]]["probs"].values()) - 1) < 1e-9
    assert ids[2] not in salida                                               # sin 1X2 no hay página
    fichas._cache.clear()


# --- pilar y sitemap ------------------------------------------------------------------------------

def test_pilar_lista_por_competicion_con_enlaces_reales(client):
    r = client.get("/futbol/", headers=HTML)
    assert r.status_code == 200
    d = Doc(r.text)
    assert URL_FINAL in d.hrefs and URL_PREVIA in d.hrefs and URL_COPA in d.hrefs
    assert not any("guadalajara" in h for h in d.hrefs)                      # sin pronóstico: texto, no enlace
    assert "Guadalajara vs Pumas UNAM" in r.text and "pronóstico pendiente de generar" in r.text
    assert "1 de 2" in r.text                                                # Valencia-Betis cumplió, Real Madrid-Sevilla no
    assert "<h3>LaLiga</h3>" in r.text and "<h3>Liga MX</h3>" in r.text and "<h3>UEFA Champions League</h3>" in r.text
    assert [l["href"] for l in d.links if l.get("rel") == "canonical"] == [BASE + "/futbol/"]
    assert d.ld[1]["@type"] == "CollectionPage" and 'data-deporte="futbol"' in r.text


def _urls(client):
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    salida = {}
    for u in ET.fromstring(client.get("/sitemap-paginas.xml").text).findall("s:url", ns):
        mod = u.find("s:lastmod", ns)
        salida[u.find("s:loc", ns).text] = mod.text if mod is not None else None
    return salida


def test_sitemap_incluye_pilar_y_partidos_con_pronostico(client):
    u = _urls(client)
    assert BASE + "/futbol/" in u
    assert BASE + URL_FINAL in u and BASE + URL_PREVIA in u and BASE + URL_COPA in u
    assert not any("guadalajara" in k for k in u)
    assert u[BASE + URL_PREVIA] == "2026-11-08"                              # sin marcador: día de la generación
    assert u[BASE + URL_FINAL] is None                                       # con marcador no hay hora de cierre verificable


def test_las_rutas_de_futbol_son_solo_las_cuatro_de_las_paginas():
    rutas = {getattr(r, "path", "") for r in main.app.routes if getattr(r, "path", "").startswith("/futbol")}
    assert rutas == {"/futbol/", "/futbol", "/futbol/{comp}/{slug}/", "/futbol/{comp}/{slug}"}


def test_veredicto_y_brier_del_1x2():
    v = futbol_paginas.veredicto({**F_FINAL, "pron": PRON[F_FINAL["match_id"]]})
    assert not v["acerto"] and v["favorito"] == "Real Madrid" and v["resultado"] == "Sevilla"
    assert abs(v["brier"] - (0.62 ** 2 + 0.22 ** 2 + (1 - 0.16) ** 2)) < 1e-9
    empate = {**F_FINAL, "marcador": [1, 1], "pron": {"probs": {"home": .3, "draw": .4, "away": .3}, "modelo": True, "generada": GENERADA}}
    assert futbol_paginas.veredicto(empate)["acerto"]
    assert futbol_paginas.veredicto({**F_PREVIA, "pron": PRON[F_PREVIA["match_id"]]}) is None


def test_estados_segun_la_hora():
    ko = F_PREVIA["kickoff_utc"]
    assert futbol_paginas.estado(F_PREVIA, datetime(2026, 11, 8, 23, 0, tzinfo=UTC)) == "previa"
    assert futbol_paginas.estado(F_PREVIA, datetime(2026, 11, 9, 1, 0, tzinfo=UTC)) == "curso"
    assert futbol_paginas.estado(F_PREVIA, datetime(2026, 11, 9, 9, 0, tzinfo=UTC)) == "pendiente"
    assert futbol_paginas.estado({**F_PREVIA, "estado": "postponed"}, datetime(2026, 11, 8, 23, 0, tzinfo=UTC)) == "aplazado"
    assert futbol_paginas.estado(F_FINAL, ko) == "final"
