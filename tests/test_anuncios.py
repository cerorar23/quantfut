"""Anuncios con recompensa de AdMob (src/qf/api/anuncios*.py, db/069)."""
import os
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from qf.api import anuncios, rewards

NOW = datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def pg(monkeypatch):
    """PostgreSQL real opcional; todo se revierte al terminar (incluidas las cuentas)."""
    if os.getenv('QF_TEST_POSTGRES') != '1':
        pytest.skip('requires PostgreSQL con db/069 aplicada')
    import psycopg
    from psycopg.rows import dict_row
    from qf.config import settings
    c = psycopg.connect(settings.pg_dsn, row_factory=dict_row)
    try:
        for aid in (-92001, -92002):
            c.execute("INSERT INTO accounts(account_id,email,password_hash,created_at,email_verified_at) "
                      "VALUES(%s,%s,'test-not-a-login',now()-interval '1 day',now())",
                      (aid, f'ads-test-{abs(aid)}@invalid.example'))
        for module in (rewards, anuncios):
            monkeypatch.setattr(module, 'conn', lambda: nullcontext(c))
            monkeypatch.setattr(module, 'query', lambda sql, params=(): c.execute(sql, params).fetchall())
            monkeypatch.setattr(module, 'query_one', lambda sql, params=(): c.execute(sql, params).fetchone())
        yield c
    finally:
        c.rollback()
        c.close()


def test_pg_migracion_defectos_y_restricciones(pg):
    cfg = pg.execute('SELECT * FROM reward_settings WHERE id=1').fetchone()
    assert (cfg['ads_enabled'], cfg['ad_coins'], cfg['ad_daily_cap'], cfg['ad_cooldown_seconds'],
            cfg['ad_test_mode']) == (False, 10, 5, 180, True)
    import psycopg
    for bad in ("ad_daily_cap=0", "ad_daily_cap=51", "ad_coins=0", "ad_cooldown_seconds=3601",
                "ad_unit_android='ca-app-pub-1/2'", "admob_publisher_id='pub-1'"):
        pg.execute('SAVEPOINT s')                    # una violación aborta la transacción: se deshace cada intento
        with pytest.raises(psycopg.errors.CheckViolation):
            pg.execute(f'UPDATE reward_settings SET {bad} WHERE id=1')
        pg.execute('ROLLBACK TO SAVEPOINT s')


def test_pg_eventos_son_inmutables(pg):
    import psycopg
    rewards.wallet(pg, -92001)
    pg.execute("INSERT INTO reward_ad_events(transaction_id,account_id,nonce,coins,outcome,day) "
               "VALUES('t1',-92001,'n1',10,'credited',current_date)")
    with pytest.raises(psycopg.errors.Error):
        pg.execute("UPDATE reward_ad_events SET coins=99 WHERE transaction_id='t1'")
