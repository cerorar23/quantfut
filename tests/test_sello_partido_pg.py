"""Sello por partido contra un Postgres real con db/*.sql aplicados: idempotencia y que no duplique lo del lote diario."""
import dataclasses
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import psycopg
import pytest
from psycopg_pool import ConnectionPool

from qf import db
from qf.publish import hashchain, parley_datos

DSN = os.getenv("QF_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="sin QF_TEST_PG_DSN")


@pytest.fixture(scope="module", autouse=True)
def _pool():
    pool = ConnectionPool(DSN, min_size=1, max_size=2, open=True)
    old, db._pool = db._pool, pool
    yield
    db._pool = old
    pool.close()


def _partido(kickoff):
    sufijo = uuid.uuid4().hex[:8]
    liga = db.query_one("SELECT league_id FROM leagues ORDER BY league_id LIMIT 1")["league_id"]
    ids = [db.query_one("INSERT INTO teams (league_id, canonical_name) VALUES (%s, %s) RETURNING team_id",
                        (liga, f"{n}-{sufijo}"))["team_id"] for n in ("Local", "Visita")]
    mid = f"{liga}:test:{sufijo}"
    db.execute("""INSERT INTO matches (match_id, league_id, season, kickoff_utc, home_team_id, away_team_id, status)
                  VALUES (%s,%s,'test',%s,%s,%s,'scheduled')""", (mid, liga, kickoff, *ids))
    return mid


def _prediccion(mid, etapa):
    return db.query_one(
        """INSERT INTO predictions (match_id, model_version, fs_version, home_lambda, away_lambda, markets, etapa)
           VALUES (%s, 'test', 'test', 1.4, 1.1, '{"1x2": {}, "totals": {}}'::jsonb, %s) RETURNING prediction_id""",
        (mid, etapa))["prediction_id"]


@pytest.fixture
def carpeta(tmp_path, monkeypatch):
    monkeypatch.setattr(hashchain, "settings",
                        dataclasses.replace(hashchain.settings, chain_dir=str(tmp_path), chain_git_remote=""))
    return tmp_path


def test_el_lote_de_partido_es_idempotente_y_enlaza_con_la_cadena(carpeta):
    ko = datetime(2001, 1, 1, 20, tzinfo=timezone.utc) + timedelta(days=uuid.uuid4().int % 8000)
    mid = _partido(ko)
    _prediccion(mid, "final")
    r1 = hashchain.seal_partido(mid)
    ruta = hashchain._ruta_partido(mid, ko.date())
    assert r1["chain_sha256"] and (carpeta / f"{ruta}.receipt.json").exists()
    r2 = hashchain.seal_partido(mid)                         # segundo disparo: no vuelve a sellar
    assert r2["chain_sha256"] == r1["chain_sha256"]
    assert db.query_one("SELECT count(*) AS n FROM prediction_batches WHERE match_id = %s", (mid,))["n"] == 1


def test_sin_prediccion_final_no_se_sella(carpeta):
    mid = _partido(datetime.now(timezone.utc) + timedelta(days=400))
    _prediccion(mid, "diaria")
    assert hashchain.seal_partido(mid) == {}


def test_solo_una_prediccion_final_por_partido():
    mid = _partido(datetime.now(timezone.utc) + timedelta(days=401))
    _prediccion(mid, "final")
    with pytest.raises(psycopg.errors.UniqueViolation):
        _prediccion(mid, "final")


def test_el_lote_diario_no_recoge_predicciones_finales():
    mid = _partido(datetime.now(timezone.utc) + timedelta(days=402))
    p_diaria, p_final = _prediccion(mid, "diaria"), _prediccion(mid, "final")     # las dos se generan hoy
    ids = {p["prediction_id"] for p in hashchain._collect(datetime.now(timezone.utc).date())["predictions"]}
    assert p_diaria in ids and p_final not in ids


def _lote(dia, kind, match_id=None):
    h = uuid.uuid4().hex
    db.execute("""INSERT INTO prediction_batches (batch_date, batch_kind, match_id, n_predictions, n_picks,
                      payload_sha256, prev_sha256, chain_sha256, created_at)
                  VALUES (%s, %s, %s, 1, 0, %s, %s, %s, %s)""",
               (dia.date(), kind, match_id, h, h, h + "c", dia + timedelta(hours=1)))


def test_un_lote_de_partido_no_cuenta_ni_duplica_lo_sellado(monkeypatch):
    """Un ticket se considera sellado por el lote DIARIO posterior: los de partido no cuentan y no multiplican filas."""
    monkeypatch.setattr(hashchain, "LOTE_PARLEY_DESDE", date(2000, 1, 1))
    dia = datetime(2001, 1, 1, 9, tzinfo=timezone.utc) + timedelta(days=uuid.uuid4().int % 8000)
    consulta = f"SELECT count(*) AS n FROM (SELECT %s::timestamptz AS decided_at) t {parley_datos._sql_sellado()}"
    for _ in range(3):                                       # tres lotes de partido el mismo día
        _lote(dia, "partido", _partido(dia + timedelta(hours=11)))
    assert db.query_one(consulta, (dia,))["n"] == 0          # solo lotes de partido: nada queda sellado
    _lote(dia, "diario")
    assert db.query_one(consulta, (dia,))["n"] == 1          # el diario sella, una sola vez pese a los de partido
