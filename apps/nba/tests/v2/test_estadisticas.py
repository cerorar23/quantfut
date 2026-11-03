"""Estadísticas de equipo que publica la API v2: solo temporada regular y solo marcadores anteriores a la fecha del partido."""
from datetime import date, datetime, UTC

import psycopg
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from nba.api import app as api
from nba.api.estadisticas import Marcador, estadisticas, es_regular, temporada_anterior, ventana_regular
from nba.v2 import identidad
from nba.v2.carga import DatoNuevo, guardar_datos

TEMPORADA = "2026-27"
PASADA = "2025-26"


def m(fecha, local, visitante, pl, pv, temporada=TEMPORADA):
    return Marcador(date.fromisoformat(fecha), temporada, local, visitante, pl, pv)


# ---- función pura ----

def test_ventana_regular_y_temporada_anterior():
    assert temporada_anterior("2026-27") == "2025-26" and temporada_anterior("2000-01") == "1999-00"
    assert ventana_regular("2026-27")[0] == date(2026, 10, 20)
    assert ventana_regular("2031-32") == (date(2031, 10, 15), date(2032, 4, 13))          # sin fila: calendario típico
    assert not es_regular(m("2026-10-16", "BOS", "NYK", 1, 2))                             # pretemporada
    assert not es_regular(m("2026-04-20", "BOS", "NYK", 1, 2, PASADA))                     # play-in y playoffs de 2025-26
    assert es_regular(m("2026-04-12", "BOS", "NYK", 1, 2, PASADA)) and es_regular(m("2021-10-19", "BOS", "NYK", 1, 2, "2021-22"))


def test_solo_cuentan_marcadores_anteriores_y_de_temporada_regular():
    previos = [m("2026-10-10", "BOS", "NYK", 130, 70),                    # pretemporada: fuera
               m("2026-10-21", "BOS", "LAL", 100, 90),
               m("2026-10-24", "BOS", "GSW", 90, 80),                      # mismo día del partido: fuera
               m("2026-10-30", "BOS", "NYK", 100, 50),                     # posterior: fuera
               m("2026-04-20", "BOS", "NYK", 99, 98, PASADA)]              # playoffs: fuera
    r = estadisticas(TEMPORADA, date(2026, 10, 24), "BOS", "NYK", previos)
    bos, nyk = r["teams"]
    assert r["games_used"] == 1 and bos["season"] == {"won": 1, "lost": 0, "rate": 1.0} and nyk["season"]["won"] + nyk["season"]["lost"] == 0
    assert bos["last_season"]["games"] == 0 and r["h2h"]["matches"] == []
    assert nyk["rest_days"] is None and nyk["back_to_back"] is None and nyk["standing"]["rank"] is None
    assert bos["rest_days"] == 2 and bos["back_to_back"] is False


def test_racha_forma_descanso_y_cara_a_cara():
    previos = [m("2026-10-21", "BOS", "LAL", 100, 90), m("2026-10-22", "NYK", "BOS", 95, 99), m("2026-10-23", "BOS", "MIA", 90, 91),
               m("2026-10-24", "ORL", "BOS", 80, 85),
               m("2025-12-01", "BOS", "NYK", 110, 100, PASADA), m("2025-12-20", "NYK", "BOS", 105, 99, PASADA)]
    bos, nyk = estadisticas(TEMPORADA, date(2026, 10, 25), "BOS", "NYK", previos)["teams"]
    assert bos["season"] == {"won": 3, "lost": 1, "rate": 0.75} and bos["home"]["won"] == 1 and bos["home"]["lost"] == 1 and bos["away"] == {"won": 2, "lost": 0, "rate": 1.0}
    assert bos["streak"] == 1 and bos["rest_days"] == 0 and bos["back_to_back"] is True
    assert [f["date"] for f in bos["form"]["all"]] == ["2026-10-24", "2026-10-23", "2026-10-22", "2026-10-21"]
    assert bos["form"]["all"][0] == {"date": "2026-10-24", "opponent": "Orlando Magic", "home": False, "points": 85, "opponent_points": 80, "won": True}
    assert [f["home"] for f in bos["form"]["home"]] == [True, True] and [f["home"] for f in bos["form"]["away"]] == [False, False]
    assert bos["scoring"] == {"games": 4, "points_for": 93.5, "points_against": 89.0}
    assert bos["last_season"] == {"won": 1, "lost": 1, "rate": 0.5, "games": 2, "points_for": 104.5, "points_against": 102.5}
    assert nyk["streak"] == -1 and nyk["rest_days"] == 2 and nyk["last_season"]["rate"] == 0.5
    assert nyk["scoring"]["games"] == 1 and nyk["conference"] == "este"


def test_racha_negativa_y_cara_a_cara_limitado_a_diez():
    previos = [m("2026-10-21", "BOS", "LAL", 90, 100), m("2026-10-22", "BOS", "MIA", 90, 100)]
    previos += [m(f"2022-11-{d:02d}", "BOS", "NYK", 100, 90, "2022-23") for d in range(1, 13)]
    r = estadisticas(TEMPORADA, date(2026, 10, 25), "BOS", "NYK", previos)
    assert r["teams"][0]["streak"] == -2 and len(r["h2h"]["matches"]) == 10 and r["h2h"]["matches"][0]["date"] == "2022-11-12"
    assert r["h2h"]["home_wins"] == 10 and r["h2h"]["away_wins"] == 0 and r["h2h"]["average_total"] == 190.0


def test_clasificacion_por_conferencia_diferencial_y_oeste():
    previos = [m("2026-10-21", "BOS", "ORL", 100, 90), m("2026-10-22", "NYK", "CHI", 120, 90), m("2026-10-23", "LAL", "BOS", 100, 99),
               m("2026-10-23", "GSW", "DEN", 100, 99), m("2026-10-24", "BOS", "DEN", 100, 99)]
    r = estadisticas(TEMPORADA, date(2026, 10, 30), "BOS", "GSW", previos)
    este, oeste = (t["standing"] for t in r["teams"])
    assert este == {"rank": 2, "of": 15, "conference": "este"}                    # BOS 2-1 (66,7 %); NYK 1-0 (100 %) va primero
    # GSW y LAL empatan 1-0 con +1: desempata el código, sin depender del orden de la base
    assert oeste["conference"] == "oeste" and oeste["of"] == 15 and oeste["rank"] == 1
    nyk = estadisticas(TEMPORADA, date(2026, 10, 30), "NYK", "BOS", previos)["teams"][0]["standing"]
    assert nyk["rank"] == 1


# ---- endpoint ----

@pytest.fixture
def cliente(base_migrada_dsn):
    ids, juegos = {}, {}
    with psycopg.connect(base_migrada_dsn) as db:
        for t in ("BOS", "NYK", "LAL", "GSW"):
            ids[t] = identidad.equipo(db, t)
        recibido = datetime(2026, 11, 2, tzinfo=UTC)

        def juego(clave, fecha, local, visitante, pl=None, pv=None, temporada=TEMPORADA):
            f = date.fromisoformat(fecha)
            pid = identidad.partido(db, "nba_oficial", f"{clave}", f, ids[local], ids[visitante], temporada)
            if pl is not None:
                guardar_datos(db, [DatoNuevo(partido_id=pid, entidad_id=ids[local], metrica="puntos", fase="final", fuente="nba_oficial", recibido_en=recibido, valor=pl),
                                   DatoNuevo(partido_id=pid, entidad_id=ids[visitante], metrica="puntos", fase="final", fuente="nba_oficial", recibido_en=recibido, valor=pv)])
            juegos[clave] = pid

        juego("antes1", "2025-12-01", "BOS", "NYK", 110, 100, PASADA)
        juego("antes2", "2025-12-20", "NYK", "BOS", 105, 99, PASADA)
        juego("antes3", "2026-01-05", "BOS", "LAL", 120, 100, PASADA)
        juego("playoffs", "2026-04-20", "BOS", "NYK", 90, 80, PASADA)
        juego("pretemporada", "2026-10-10", "BOS", "NYK", 130, 70)
        juego("g1", "2026-10-21", "BOS", "LAL", 100, 90)
        juego("g2", "2026-10-23", "NYK", "BOS", 95, 99)
        juego("g3", "2026-10-24", "BOS", "NYK", 101, 80)                     # el partido consultado ya tiene marcador: no debe usarse
        juego("mismo_dia", "2026-10-24", "GSW", "LAL", 100, 90)
        juego("g4", "2026-10-26", "NYK", "LAL", 90, 80)
        db.commit()
    return TestClient(api.crear_app(base_migrada_dsn)), juegos


def test_estadisticas_con_datos_de_temporada_pasada_y_sin_mirar_el_futuro(cliente):
    c, juegos = cliente
    r = c.get(f"/nba/v1/partido/{juegos['g3']}/estadisticas")
    assert r.status_code == 200
    d = r.json()
    assert d["temporada"] == TEMPORADA and d["fecha"] == "2026-10-24" and d["games_used"] == 2
    bos, nyk = d["teams"]
    assert bos["name"] == "Boston Celtics" and nyk["name"] == "New York Knicks"
    assert bos["season"] == {"won": 2, "lost": 0, "rate": 1.0} and bos["home"]["won"] == 1 and bos["away"]["won"] == 1
    assert bos["scoring"] == {"games": 2, "points_for": 99.5, "points_against": 92.5} and bos["streak"] == 2
    assert bos["rest_days"] == 0 and bos["back_to_back"] is True and bos["standing"]["rank"] == 1 and bos["standing"]["of"] == 15
    assert bos["last_season"] == {"won": 2, "lost": 1, "rate": 0.6667, "games": 3, "points_for": 109.7, "points_against": 101.7}   # sin los playoffs
    assert bos["form"]["all"][0] == {"date": "2026-10-23", "opponent": "New York Knicks", "home": False, "points": 99, "opponent_points": 95, "won": True}
    assert nyk["season"] == {"won": 0, "lost": 1, "rate": 0.0} and nyk["streak"] == -1 and nyk["last6"]["games"] == 1
    h = d["h2h"]                                                                  # sin pretemporada, playoffs ni el propio partido
    assert [x["date"] for x in h["matches"]] == ["2026-10-23", "2025-12-20", "2025-12-01"]
    assert h["home_wins"] == 2 and h["away_wins"] == 1 and h["average_total"] == 202.7
    assert h["matches"][0] == {"date": "2026-10-23", "home": "New York Knicks", "away": "Boston Celtics", "home_points": 95, "away_points": 99}


def test_cada_partido_solo_ve_lo_anterior_a_su_fecha(cliente):
    c, juegos = cliente
    primero = c.get(f"/nba/v1/partido/{juegos['g1']}/estadisticas").json()
    assert primero["games_used"] == 0 and primero["teams"][0]["season"]["rate"] is None and primero["teams"][0]["rest_days"] is None
    assert primero["teams"][0]["standing"]["rank"] is None and primero["teams"][0]["last_season"]["games"] == 3
    segundo = c.get(f"/nba/v1/partido/{juegos['g2']}/estadisticas").json()
    nyk, bos = segundo["teams"]
    assert segundo["games_used"] == 1 and bos["season"]["won"] == 1 and nyk["season"]["won"] + nyk["season"]["lost"] == 0
    assert bos["rest_days"] == 1 and bos["back_to_back"] is False
    ultimo = c.get(f"/nba/v1/partido/{juegos['g4']}/estadisticas").json()
    assert ultimo["games_used"] == 4 and ultimo["teams"][0]["season"] == {"won": 0, "lost": 2, "rate": 0.0}


def test_respuesta_cumple_el_contrato_que_valida_la_web(cliente):
    c, juegos = cliente
    d = c.get(f"/nba/v1/partido/{juegos['g3']}/estadisticas").json()
    claves = {"name", "conference", "season", "home", "away", "scoring", "last6", "streak", "rest_days", "back_to_back", "last_season", "form", "standing"}
    assert len(d["teams"]) == 2 and all(set(t) == claves and set(t["form"]) == {"all", "home", "away"} for t in d["teams"])
    assert set(d["h2h"]) == {"matches", "home_wins", "away_wins", "average_total"}


def test_pretemporada_playoffs_y_partidos_inexistentes(cliente):
    c, juegos = cliente
    pre = c.get(f"/nba/v1/partido/{juegos['pretemporada']}/estadisticas")
    assert pre.status_code == 404 and pre.json()["detail"]["codigo"] == "sin_estadisticas"
    assert c.get("/nba/v1/partido/999999/estadisticas").json()["detail"]["codigo"] == "partido_inexistente"
    assert c.get("/nba/v1/partido/abc/estadisticas").status_code == 422
    # un partido de playoffs recibe las estadísticas de su temporada regular completa
    po = c.get(f"/nba/v1/partido/{juegos['playoffs']}/estadisticas").json()
    assert po["teams"][0]["season"]["won"] + po["teams"][0]["season"]["lost"] == 3 and po["teams"][0]["last_season"]["games"] == 0


def test_la_api_solo_lee(cliente):
    c, juegos = cliente
    assert c.post(f"/nba/v1/partido/{juegos['g3']}/estadisticas").status_code == 405
