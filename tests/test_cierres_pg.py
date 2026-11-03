"""insertar_cierre contra un Postgres real con db/*.sql aplicados (ver test_escalera_pg)."""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.ingest.cierres import insertar_cierre

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


def test_insertar_cierre_conserva_hora_fuente_y_actualizacion_de_la_casa():
    mid, liga, local, visita, ko = _partido()
    cap = ko - timedelta(minutes=5)
    upd = ko - timedelta(minutes=6)
    with db.conn() as c:
        n = insertar_cierre(c, mid, ko, {"home": 2.0, "draw": 3.4, "away": 3.9},
                            captured_at=cap, book_updated_at=upd, source="the_odds_api_hist")
        again = insertar_cierre(c, mid, ko, {"home": 9.0, "draw": 9.0, "away": 9.0}, source="the_odds_api_hist")
    f = db.query("""SELECT selection, price, captured_at, mins_to_kickoff, source, book_updated_at
                    FROM odds_snapshots WHERE match_id=%s AND window_tag='close' ORDER BY selection""", (mid,))
    assert n == 3 and again == 0 and len(f) == 3
    assert {x["source"] for x in f} == {"the_odds_api_hist"}
    assert all(x["captured_at"] == cap and x["mins_to_kickoff"] == 5 and x["book_updated_at"] == upd for x in f)
    assert [round(x["price"], 2) for x in f] == [3.9, 3.4, 2.0]
