"""Un cierre reconstruido a 60 minutos del inicio no es un cierre: no alimenta el mercado de referencia."""
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qf.eval.cierre import MAX_MIN_RECONSTRUIDO, es_cierre_real

RAIZ = Path(__file__).resolve().parents[1]
CONSUMIDORES = {"src/qf/model/train.py": 2, "src/qf/eval/clv.py": 2,
                "src/qf/model/shadow.py": 1, "src/qf/publish/shadow_sharp.py": 2}


def test_el_fragmento_acepta_el_cierre_real_y_el_reconstruido_al_inicio():
    sql = es_cierre_real()
    assert "oddspapi_reconstructed" in sql and f"mins_to_kickoff > {MAX_MIN_RECONSTRUIDO}" in sql
    assert es_cierre_real("s").count("s.source") == 1 and "s.mins_to_kickoff" in es_cierre_real("s")


@pytest.mark.parametrize("ruta, usos", CONSUMIDORES.items())
def test_todo_consumidor_del_cierre_aplica_el_filtro(ruta, usos):
    """Guarda: cada lectura de window_tag='close' lleva su es_cierre_real(...)."""
    texto = (RAIZ / ruta).read_text(encoding="utf-8")
    # Solo lecturas SQL (AND/WHERE ... window_tag = 'close'); una mención en un comentario no cuenta.
    lecturas = len(re.findall(r"(?:AND|WHERE)[^\n]*window_tag\s*=\s*'close'", texto))
    assert lecturas == usos, f"{ruta}: {lecturas} lecturas del cierre, se esperaban {usos}"
    assert texto.count("es_cierre_real(") == usos, f"{ruta}: falta el filtro en alguna lectura del cierre"


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


def _partido(db, liga, ko, goles=(2, 1)):
    s = uuid.uuid4().hex[:6]
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s,%s) RETURNING team_id",
                        (liga, f"{n}-{s}"))["team_id"] for n in ("L", "V")]
    mid = f"{liga}:c:{s}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  VALUES (%s,%s,'t',%s,%s,%s,'finished',%s,%s)""", (mid, liga, ko, *ids, *goles))
    return mid


def _cierre(db, mid, ko, fuente, mins, precios=(2.0, 3.4, 3.9)):
    for sel, p in zip(("home", "draw", "away"), precios):
        db.execute("""INSERT INTO odds_snapshots (match_id,bookmaker,market,selection,price,captured_at,mins_to_kickoff,
                                                  window_tag,source) VALUES (%s,'pinnacle','h2h',%s,%s,%s,%s,'close',%s)""",
                   (mid, sel, p, ko - timedelta(minutes=mins), mins, fuente))


def _liga(db):
    s = uuid.uuid4().hex[:6]
    lid = f"t{s}.liga"
    db.execute("""INSERT INTO leagues (league_id, country, name, tier, odds_api_key, model_enabled)
                  VALUES (%s,'XX','Prueba',1,%s,true)""", (lid, f"soccer_{s}"))
    return lid


@pg
def test_el_entrenamiento_ignora_el_cierre_de_60_min_y_conserva_el_real_y_el_reconstruido_al_inicio(base):
    from qf.model.train import load_training_data
    db = base
    liga = _liga(db)
    ko = datetime.now(timezone.utc) - timedelta(days=5)
    t60, al_inicio, real = (_partido(db, liga, ko + timedelta(hours=i)) for i in range(3))
    _cierre(db, t60, ko, "oddspapi_reconstructed", 60)
    _cierre(db, al_inicio, ko + timedelta(hours=1), "oddspapi_reconstructed", 0)
    _cierre(db, real, ko + timedelta(hours=2), "the_odds_api", 6)
    df = load_training_data(league_id=liga).set_index("match_id")
    assert df.loc[t60, "odds_home"] != df.loc[t60, "odds_home"]          # NaN: no hay cierre
    assert df.loc[al_inicio, "odds_home"] == pytest.approx(2.0)
    assert df.loc[real, "odds_home"] == pytest.approx(2.0)


@pg
def test_el_clv_y_la_liquidacion_en_sombra_ignoran_el_cierre_de_60_min(base):
    from qf.eval.clv import _sharp_close_quotes
    from qf.model.shadow import _closing
    db = base
    liga = _liga(db)
    ko = datetime.now(timezone.utc) - timedelta(days=2)
    solo_t60 = _partido(db, liga, ko)
    _cierre(db, solo_t60, ko, "oddspapi_reconstructed", 60)
    mixto = _partido(db, liga, ko + timedelta(hours=1))
    _cierre(db, mixto, ko + timedelta(hours=1), "oddspapi_reconstructed", 60, (1.5, 4.0, 6.0))
    _cierre(db, mixto, ko + timedelta(hours=1), "the_odds_api", 5, (2.0, 3.4, 3.9))
    assert _sharp_close_quotes(solo_t60, "h2h") == {} and _closing(solo_t60) == {}
    assert _closing(mixto)["home"] == pytest.approx(2.0)
    assert _sharp_close_quotes(mixto, "h2h")[("home", None)] == pytest.approx(2.0)
