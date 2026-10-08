"""Reto escalera contra un Postgres real con db/*.sql aplicados (ver test_cuentas_pg)."""
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.publish import escalera_datos as ed
from qf.publish import hashchain

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


@pytest.fixture(autouse=True)
def _lote(monkeypatch):
    monkeypatch.setattr(hashchain, "LOTE_ESCALERA_DESDE", date(2000, 1, 1))


def _dia() -> datetime:
    """Una fecha distinta en cada ejecución: los lotes no se pueden borrar."""
    return datetime(2001, 1, 1, 9, tzinfo=timezone.utc) + timedelta(days=uuid.uuid4().int % 8000)


def _partido(status="finished", hg=2, ag=0, kickoff=None) -> tuple[str, str, str]:
    sufijo = uuid.uuid4().hex[:8]
    liga = db.query_one("SELECT league_id FROM leagues ORDER BY league_id LIMIT 1")["league_id"]
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s, %s) RETURNING team_id",
                        (liga, f"{n}-{sufijo}"))["team_id"] for n in ("Local", "Visita")]
    mid = f"{liga}:test:{sufijo}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id,
                                       status, home_goals, away_goals)
                  VALUES (%s,%s,'test',%s,%s,%s,%s,%s,%s)""",
               (mid, liga, kickoff or datetime.now(timezone.utc) - timedelta(days=1), *ids, status,
                hg if status == "finished" else None, ag if status == "finished" else None))
    return mid, f"Local-{sufijo}", f"Visita-{sufijo}"


def _reto(objetivo=2) -> int:
    return db.query_one("""INSERT INTO escalera_retos (stake_inicial, pasos_objetivo, cuota_min, cuota_max, ev_min)
                           VALUES (10, %s, 1.25, 1.40, 0) RETURNING reto_id""", (objetivo,))["reto_id"]


def _paso(reto_id, paso, mid, decided, price=1.30) -> None:
    db.execute("""INSERT INTO escalera_pasos (reto_id, paso, match_id, market, selection, prob, fair_price,
                                              price, book, odds_source, odds_as_of, decided_at)
                  VALUES (%s,%s,%s,'h2h','home',0.77,1.2987,%s,'betano','the_odds_api',%s,%s)""",
               (reto_id, paso, mid, price, decided - timedelta(hours=1), decided))


def _sellar(dia: datetime) -> None:
    h = uuid.uuid4().hex
    db.execute("""INSERT INTO prediction_batches (batch_date, n_predictions, n_picks, payload_sha256,
                                                  prev_sha256, chain_sha256, created_at)
                  VALUES (%s, 1, 0, %s, %s, %s, %s)""",
               (dia.date(), h, h, h + "c", dia + timedelta(hours=1)))


def _reto_publico(reto_id):
    return next(r for r in [ed.informe_publico()["actual"], *ed.informe_publico()["historial"]]
                if r and r["reto_id"] == reto_id)


def test_escalon_sellado_se_liquida_y_mueve_el_saldo():
    dia = _dia()
    reto = _reto(objetivo=2)
    mid, local, _ = _partido(hg=2, ag=0)
    _paso(reto, 1, mid, dia)
    _sellar(dia)
    assert ed.settle_pending()["settled"] >= 1
    r = _reto_publico(reto)
    assert r["estado"] == "en_curso" and r["ganados"] == 1 and r["saldo"] == "13.00"
    (p,) = r["pasos"]
    assert p["texto"] == f"Gana {local}" and p["marcador"] == "2-0" and p["outcome"] == "win"
    assert p["chain_sha256"]


def test_escalon_sin_sellar_no_se_ensena():
    dia = _dia()
    reto = _reto(objetivo=3)
    mid, *_ = _partido()
    _paso(reto, 1, mid, dia)              # sin lote: no existe para el público
    r = _reto_publico(reto)
    assert r["pasos"] == [] and r["estado"] == "en_curso"


def test_aplazado_pasado_el_margen_queda_nulo():
    dia = _dia()
    reto = _reto(objetivo=2)
    mid, *_ = _partido(status="postponed", kickoff=datetime.now(timezone.utc) - timedelta(days=3))
    _paso(reto, 1, mid, dia)
    _sellar(dia)
    ed.settle_pending()
    r = _reto_publico(reto)
    assert r["pasos"][0]["outcome"] == "void" and r["ganados"] == 0 and r["saldo"] == "10.00"


def test_perder_cierra_el_reto_y_las_filas_no_se_pueden_tocar():
    dia = _dia()
    reto = _reto(objetivo=2)
    mid, *_ = _partido(hg=0, ag=1)
    _paso(reto, 1, mid, dia)
    _sellar(dia)
    ed.settle_pending()
    r = _reto_publico(reto)
    assert r["estado"] == "fallido" and r["ganancia"] == "-10.00"
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("UPDATE escalera_pasos SET price = 9 WHERE reto_id = %s", (reto,))
    with pytest.raises(psycopg.errors.RaiseException):
        db.execute("DELETE FROM escalera_retos WHERE reto_id = %s", (reto,))
