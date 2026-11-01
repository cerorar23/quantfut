"""La sombra del XI con las cuotas horarias de PropLine (25-oct-2026).

Desde el 23-oct no hay capturas `post_xi`: PropLine guarda una foto por hora (`hourly:*`). La sombra
tiene que admitir esa foto si es posterior al XI, anterior a T-15 y no más vieja de 75 min.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest

DSN = os.getenv("QF_TEST_PG_DSN")
pg = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture
def base():
    from psycopg_pool import ConnectionPool

    from qf import db
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield db
    db._pool = old
    pool.close()


def _partido(db, ko):
    s = uuid.uuid4().hex[:6]
    lid = f"t{s}.liga"
    db.execute("""INSERT INTO leagues (league_id, country, name, tier, odds_api_key, model_enabled)
                  VALUES (%s,'XX','Prueba',1,%s,true)""", (lid, f"soccer_{s}"))
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s,%s) RETURNING team_id",
                        (lid, f"{n}-{s}"))["team_id"] for n in ("L", "V")]
    mid = f"{lid}:s:{s}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id)
                  VALUES (%s,%s,'t',%s,%s,%s)""", (mid, lid, ko, *ids))
    return mid


def _foto(db, mid, ko, hace_min, tag, precio=2.0):
    cap = datetime.now(timezone.utc) - timedelta(minutes=hace_min)
    for sel, p in zip(("home", "draw", "away"), (precio, 3.4, 3.9)):
        db.execute("""INSERT INTO odds_snapshots (match_id,bookmaker,market,selection,price,captured_at,
                                                  mins_to_kickoff,window_tag,source)
                      VALUES (%s,'pinnacle','h2h',%s,%s,%s,%s,%s,'propline')""",
                   (mid, sel, p, cap, int((ko - cap).total_seconds() // 60), tag))


@pg
def test_admite_la_foto_horaria_posterior_al_xi(base):
    from qf.model.shadow import _quotes
    db = base
    ko = datetime.now(timezone.utc) + timedelta(minutes=30)
    mid = _partido(db, ko)
    xi = datetime.now(timezone.utc) - timedelta(minutes=50)
    _foto(db, mid, ko, 70, "hourly:1", precio=1.9)       # anterior al XI: no vale
    assert _quotes(mid, xi) == []
    _foto(db, mid, ko, 40, "hourly:2", precio=2.1)       # posterior al XI, a T-70
    q = {r["selection"]: float(r["price"]) for r in _quotes(mid, xi)}
    assert q == {"home": 2.1, "draw": 3.4, "away": 3.9}


@pg
def test_no_admite_una_foto_horaria_de_mas_de_75_min_ni_dentro_de_t15(base):
    from qf.model.shadow import _quotes
    db = base
    ko = datetime.now(timezone.utc) + timedelta(minutes=10)
    mid = _partido(db, ko)
    xi = datetime.now(timezone.utc) - timedelta(minutes=120)
    _foto(db, mid, ko, 90, "hourly:1")                   # demasiado vieja
    _foto(db, mid, ko, 2, "hourly:2")                    # a T-12: dentro de los 15 min finales
    assert _quotes(mid, xi) == []
