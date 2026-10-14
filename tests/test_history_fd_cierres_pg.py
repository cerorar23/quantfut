"""cargar_ternas contra un Postgres real con db/*.sql aplicados (ver test_escalera_pg)."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.ingest.history_fd import cargar_ternas

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


def _partido(ko=None, local="Local", visita="Visita"):
    s = uuid.uuid4().hex[:8]
    liga = db.query_one("SELECT league_id FROM leagues ORDER BY league_id LIMIT 1")["league_id"]
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s,%s) RETURNING team_id",
                        (liga, f"{n}-{s}"))["team_id"] for n in (local, visita)]
    ko = ko or datetime.now(timezone.utc) - timedelta(days=5)
    mid = f"{liga}:cier:{s}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  VALUES (%s,%s,'t',%s,%s,%s,'finished',1,0)""", (mid, liga, ko, *ids))
    return mid, liga, f"{local}-{s}", f"{visita}-{s}", ko


def _terna(local, visita, ko, p=(2.1, 3.3, 3.6)):
    return {"home": local, "away": visita, "ko": ko, "price": dict(zip(("home", "draw", "away"), p))}


def _resolver(nombre, league_id):
    return nombre


def _cierres(mid):
    return db.query("""SELECT selection, price, bookmaker, window_tag, source, mins_to_kickoff, captured_at
                       FROM odds_snapshots WHERE match_id=%s AND market='h2h' AND window_tag='close'
                       ORDER BY selection""", (mid,))


def test_inserta_la_terna_de_pinnacle_en_el_partido_existente():
    mid, liga, local, visita, ko = _partido()
    with db.conn() as c:
        r = cargar_ternas(c, liga, [_terna(local, visita, ko + timedelta(hours=1))], _resolver, aplicar=True)
    f = _cierres(mid)
    assert r["insertadas"] == 3 and r["a_insertar"] == 1 and len(f) == 3
    assert {x["bookmaker"] for x in f} == {"pinnacle"} and {x["source"] for x in f} == {"football_data"}
    assert all(x["mins_to_kickoff"] == 0 and x["captured_at"] == ko for x in f)
    assert [round(x["price"], 2) for x in f] == [3.6, 3.3, 2.1]      # away, draw, home (orden alfabético)


def test_segunda_ejecucion_no_inserta_nada():
    mid, liga, local, visita, ko = _partido()
    t = [_terna(local, visita, ko)]
    with db.conn() as c:
        cargar_ternas(c, liga, t, _resolver, aplicar=True)
    with db.conn() as c:
        r = cargar_ternas(c, liga, t, _resolver, aplicar=True)
    assert r["insertadas"] == 0 and r["ya_tenia_cierre"] == 1 and len(_cierres(mid)) == 3


def test_si_la_api_en_vivo_ya_trajo_el_cierre_no_se_duplica():
    mid, liga, local, visita, ko = _partido()
    for sel, p in (("home", 2.0), ("draw", 3.2), ("away", 3.5)):
        db.execute("""INSERT INTO odds_snapshots (match_id,bookmaker,market,selection,line,price,captured_at,
                                                  mins_to_kickoff,window_tag,source)
                      VALUES (%s,'pinnacle','h2h',%s,NULL,%s,%s,3,'close','the_odds_api')""",
                   (mid, sel, p, ko - timedelta(minutes=3)))
    with db.conn() as c:
        r = cargar_ternas(c, liga, [_terna(local, visita, ko)], _resolver, aplicar=True)
    assert r["insertadas"] == 0 and r["ya_tenia_cierre"] == 1 and len(_cierres(mid)) == 3


def test_el_ensayo_cuenta_y_no_escribe():
    mid, liga, local, visita, ko = _partido()
    with db.conn() as c:
        r = cargar_ternas(c, liga, [_terna(local, visita, ko)], _resolver, aplicar=False)
    assert r["a_insertar"] == 1 and r["insertadas"] == 0 and _cierres(mid) == []


def test_sin_partido_y_sin_resolver_se_cuentan_y_se_omiten():
    mid, liga, local, visita, ko = _partido()
    sin_pareja = _terna(local, visita, ko + timedelta(days=10))
    desconocido = _terna("Nadie", visita, ko)
    with db.conn() as c:
        r = cargar_ternas(c, liga, [sin_pareja, desconocido], lambda n, l: None if n == "Nadie" else n,
                          aplicar=True)
    assert r["sin_partido"] == 1 and r["sin_resolver"] == 1 and r["insertadas"] == 0


def test_con_dos_partidos_cercanos_elige_el_mas_proximo():
    mid1, liga, local, visita, ko = _partido(ko=datetime.now(timezone.utc) - timedelta(days=9))
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  SELECT %s, league_id, season, %s, home_team_id, away_team_id, 'finished', 2, 2
                  FROM matches WHERE match_id = %s""", (mid1 + "-b", ko + timedelta(hours=30), mid1))
    with db.conn() as c:
        cargar_ternas(c, liga, [_terna(local, visita, ko + timedelta(hours=28))], _resolver, aplicar=True)
    assert len(_cierres(mid1)) == 0 and len(_cierres(mid1 + "-b")) == 3
