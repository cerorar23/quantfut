"""pendientes y cargar contra un Postgres real (ver test_cierres_pg)."""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.ingest import cierres_odds_api as co
from qf.ingest import odds_history as oh

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


def _liga(modelada=True):
    s = uuid.uuid4().hex[:6]
    lid = f"t{s}.liga"
    db.execute("""INSERT INTO leagues (league_id, country, name, tier, odds_api_key, model_enabled)
                  VALUES (%s,'XX','Liga prueba',1,%s,%s)""", (lid, f"soccer_{s}", modelada))
    return lid, f"soccer_{s}"


def _partido(liga, ko):
    s = uuid.uuid4().hex[:6]
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s,%s) RETURNING team_id",
                        (liga, f"{n}-{s}"))["team_id"] for n in ("Local", "Visita")]
    mid = f"{liga}:p:{s}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  VALUES (%s,%s,'t',%s,%s,%s,'finished',1,0)""", (mid, liga, ko, *ids))
    return mid, ids, f"Local-{s}", f"Visita-{s}"


def test_pendientes_excluye_lo_que_ya_tiene_cierre_y_las_ligas_no_modeladas():
    liga, _ = _liga()
    otra, _ = _liga(modelada=False)
    ko = datetime.now(timezone.utc) - timedelta(days=3)
    sin, *_ = _partido(liga, ko)
    con, *_ = _partido(liga, ko + timedelta(hours=1))
    fuera, *_ = _partido(otra, ko)
    db.execute("""INSERT INTO odds_snapshots (match_id,bookmaker,market,selection,price,captured_at,mins_to_kickoff,
                                              window_tag,source) VALUES (%s,'pinnacle','h2h','home',2.0,%s,0,'close','x')""",
               (con, ko))
    with db.conn() as c:
        ids = {p["match_id"] for p in co.pendientes(c, [liga, otra], "2000-01-01", solo_modeladas=True)}
        todos = {p["match_id"] for p in co.pendientes(c, [liga, otra], "2000-01-01", solo_modeladas=False)}
    assert ids == {sin} and todos == {sin, fuera}


def _snapshot(cache, sport, t, ev):
    ruta = cache / sport / f"odds_{t.strftime('%Y%m%dT%H%M')}_markets-h2h_regions-eu.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"timestamp": (t + timedelta(seconds=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "data": [ev]}), encoding="utf-8")


def _evento(ko, h, a, upd_min_antes=6):
    upd = (ko - timedelta(minutes=upd_min_antes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": "e", "home_team": h, "away_team": a, "commence_time": ko.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "bookmakers": [{"key": "pinnacle", "last_update": upd, "markets": [{
                "key": "h2h", "last_update": upd, "outcomes": [
                    {"name": h, "price": 1.8}, {"name": "Draw", "price": 3.6}, {"name": a, "price": 4.4}]}]}]}


def test_cargar_inserta_el_cierre_desde_lo_descargado_y_es_idempotente(tmp_path):
    liga, sport = _liga()
    ko = (datetime.now(timezone.utc) - timedelta(days=3)).replace(second=0, microsecond=0)
    mid, ids, h, a = _partido(liga, ko)
    with db.conn() as c:
        slots = co.planificar(co.pendientes(c, [liga], "2000-01-01"))
    assert len(slots) == 1
    _snapshot(tmp_path, sport, slots[0]["t"], _evento(ko, h, a))
    por_nombre = {h: ids[0], a: ids[1]}
    with db.conn() as c:
        ensayo = co.cargar(c, slots, tmp_path, por_nombre.get, aplicar=False)
    assert ensayo["a_insertar"] == 1 and ensayo["insertadas"] == 0
    with db.conn() as c:
        real = co.cargar(c, slots, tmp_path, por_nombre.get, aplicar=True)
    f = db.query("SELECT * FROM odds_snapshots WHERE match_id=%s AND window_tag='close' ORDER BY selection", (mid,))
    assert real["insertadas"] == 3 and len(f) == 3
    assert {x["source"] for x in f} == {co.FUENTE} and {x["mins_to_kickoff"] for x in f} == {4}
    assert all(x["book_updated_at"] is not None and x["book_updated_at"] < x["captured_at"] for x in f)
    with db.conn() as c:
        otra_vez = co.cargar(c, [{**slots[0], "matches": slots[0]["matches"]}], tmp_path, por_nombre.get, aplicar=True)
    assert otra_vez["insertadas"] == 0 and len(db.query(
        "SELECT 1 FROM odds_snapshots WHERE match_id=%s AND window_tag='close'", (mid,))) == 3


def test_cargar_cuenta_lo_que_no_se_descargo_o_no_trae_pinnacle_valido(tmp_path):
    liga, sport = _liga()
    ko = (datetime.now(timezone.utc) - timedelta(days=3)).replace(second=0, microsecond=0)
    mid, ids, h, a = _partido(liga, ko)
    with db.conn() as c:
        slots = co.planificar(co.pendientes(c, [liga], "2000-01-01"))
        r = co.cargar(c, slots, tmp_path, {h: ids[0], a: ids[1]}.get, aplicar=True)
    assert r["sin_snapshot"] == 1 and r["insertadas"] == 0
    _snapshot(tmp_path, sport, slots[0]["t"], _evento(ko, h, a, upd_min_antes=50))   # precio de hace 50 min
    with db.conn() as c:
        r = co.cargar(c, slots, tmp_path, {h: ids[0], a: ids[1]}.get, aplicar=True)
    assert r["sin_cierre_valido"] == 1 and r["insertadas"] == 0
