"""aplicar() contra un Postgres real con db/*.sql aplicados (ver test_escalera_pg)."""
import gzip
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.ingest.archivo_a_matches import aplicar

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")

STATS = {"yellow_cards": [2.0, 1.0], "red_cards": [0.0, 1.0], "corners": [7.0, 5.0],
         "total_shots": [22.0, 21.0], "ShotsOnTarget": [5.0, 6.0], "expected_goals_on_target": [1.05, 2.68]}
PAYLOAD = {"content": {"matchFacts": {
    "infoBox": {"Referee": {"text": "Árbitro Prueba"},
                "Stadium": {"name": "Estadio Prueba", "city": "Ciudad", "country": "País",
                            "lat": 10.0, "long": 20.0, "capacity": 1000, "surface": "grass"}},
    "events": {"events": [{"type": "Half", "halfStrShort": "HT", "homeScore": 1, "awayScore": 1}]}}}}


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


def _partido(hg=2, ag=3, **columnas):
    s = uuid.uuid4().hex[:8]
    liga = db.query_one("SELECT league_id FROM leagues ORDER BY league_id LIMIT 1")["league_id"]
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s,%s) RETURNING team_id",
                        (liga, f"{n}-{s}"))["team_id"] for n in ("Local", "Visita")]
    ko = datetime.now(timezone.utc) - timedelta(days=3)
    mid = f"{liga}:f0:{s}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  VALUES (%s,%s,'t',%s,%s,%s,'finished',%s,%s)""", (mid, liga, ko, *ids, hg, ag))
    for col, val in columnas.items():
        db.execute(f"UPDATE matches SET {col} = %s WHERE match_id = %s", (val, mid))
    db.execute("""INSERT INTO historical_football_matches
        (provider, source_match_id, league_id, season, kickoff_utc, captured_at, raw_sha256, raw_payload_gzip,
         raw_metadata, home_source_team_id, away_source_team_id, home_name, away_name, home_goals, away_goals,
         statistics, match_id, mapping_status)
        VALUES ('fotmob', %s, %s, 't', %s, now(), %s, %s, '{}', '1', '2', 'L', 'V', %s, %s, %s, %s, 'matched')""",
               (s, liga, ko, "0" * 64, gzip.compress(json.dumps(PAYLOAD).encode()), hg, ag,
                json.dumps(STATS), mid))
    return mid


def _fila(mid):
    return db.query_one("SELECT * FROM matches WHERE match_id = %s", (mid,))


def test_rellena_los_null_y_registra_procedencia():
    mid = _partido()
    with db.conn() as c:
        informe = aplicar(c, desde="2000-01-01")
    f = _fila(mid)
    assert (f["home_yellow"], f["away_yellow"]) == (2, 1)
    assert (f["home_goals_ht"], f["away_goals_ht"]) == (1, 1)
    assert f["referee_fotmob"] == "Árbitro Prueba" and f["referee"] is None
    assert f["stadium_id"] is not None and (f["home_xgot"], f["away_xgot"]) == (1.05, 2.68)
    assert f["home_psxg"] is None
    prov = db.query("SELECT campo FROM matches_enriquecimiento WHERE match_id = %s", (mid,))
    assert {"home_yellow", "home_goals_ht", "referee_fotmob", "stadium_id"} <= {p["campo"] for p in prov}
    assert informe["rellenados"]["home_yellow"] >= 1


def test_no_sobrescribe_un_valor_existente():
    mid = _partido(home_yellow=9, away_yellow=9)
    with db.conn() as c:
        aplicar(c, desde="2000-01-01")
    f = _fila(mid)
    assert (f["home_yellow"], f["away_yellow"]) == (9, 9)


def test_segunda_ejecucion_no_cambia_nada():
    _partido()
    with db.conn() as c:
        aplicar(c, desde="2000-01-01")
    with db.conn() as c:
        segunda = aplicar(c, desde="2000-01-01")
    assert sum(segunda["rellenados"].values()) == 0 and segunda["estadios_nuevos"] == 0


def test_marcador_distinto_no_se_toca():
    mid = _partido(hg=2, ag=3)
    db.execute("UPDATE historical_football_matches SET home_goals = 3, away_goals = 2 "
               "WHERE match_id = %s", (mid,))
    with db.conn() as c:
        informe = aplicar(c, desde="2000-01-01")
    assert _fila(mid)["home_yellow"] is None
    assert informe["omitidos"].get("marcador_distinto", 0) >= 1


def test_ensayo_revierte():
    mid = _partido()
    with db.conn() as c:
        aplicar(c, desde="2000-01-01", rollback=True)
    assert _fila(mid)["home_yellow"] is None
