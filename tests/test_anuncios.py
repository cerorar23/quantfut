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


CFG = {'enabled': True, 'ads_enabled': True, 'ad_coins': 10, 'ad_daily_cap': 5, 'ad_cooldown_seconds': 180,
       'ad_unit_android': 'ca-app-pub-1234567890123456/1234567890', 'ad_unit_ios': '',
       'ad_test_mode': False, 'admob_publisher_id': ''}


def _permitido(**kw):
    base = dict(used_today=0, last_credit_at=None, open_ticket=False, now=NOW)
    base.update(kw)
    anuncios.check_ticket_allowed(CFG | base.pop('cfg', {}), base.pop('platform', 'android'), **base)


def _codigo(exc):
    d = exc.value.detail
    return d['code'] if isinstance(d, dict) else d


def test_ticket_permitido_en_el_caso_normal():
    _permitido()


@pytest.mark.parametrize('cfg', [{'ads_enabled': False}, {'enabled': False}])
def test_ticket_apagado(cfg):
    with pytest.raises(HTTPException) as e:
        _permitido(cfg=cfg)
    assert e.value.status_code == 503 and _codigo(e) == 'Los anuncios con recompensa no están disponibles'


def test_ticket_sin_id_para_esa_plataforma_pero_con_modo_prueba_si():
    with pytest.raises(HTTPException) as e:
        _permitido(platform='ios')
    assert e.value.status_code == 409 and _codigo(e) == 'Anuncios no disponibles en este dispositivo'
    _permitido(platform='ios', cfg={'ad_test_mode': True})


def test_ticket_abierto_tope_y_pausa():
    with pytest.raises(HTTPException) as e:
        _permitido(open_ticket=True)
    assert _codigo(e) == 'anuncio_en_curso'
    with pytest.raises(HTTPException) as e:
        _permitido(used_today=5)
    assert e.value.status_code == 409 and _codigo(e) == 'limite_diario'
    with pytest.raises(HTTPException) as e:
        _permitido(last_credit_at=NOW - timedelta(seconds=100))
    assert _codigo(e) == 'anuncio_en_espera' and e.value.headers['Retry-After'] == '80'
    _permitido(last_credit_at=NOW - timedelta(seconds=180))      # justo cumplida la pausa
    _permitido(used_today=4)


def test_modo_prueba_entrega_los_bloques_oficiales_de_google():
    assert anuncios.unit_for(CFG | {'ad_test_mode': True}, 'android') == anuncios.TEST_UNITS['android']
    assert anuncios.unit_for(CFG | {'ad_test_mode': True}, 'ios') == anuncios.TEST_UNITS['ios']
    assert anuncios.unit_for(CFG, 'android') == CFG['ad_unit_android']


def test_ads_state_cuentas_y_apagado():
    assert anuncios.ads_state(CFG | {'ads_enabled': False}, 0, None, NOW) == {'enabled': False}
    st = anuncios.ads_state(CFG, 2, NOW - timedelta(seconds=60), NOW)
    assert st == {'enabled': True, 'coins': 10, 'daily_cap': 5, 'cooldown_seconds': 180,
                  'used_today': 2, 'remaining_today': 3,
                  'next_at': (NOW + timedelta(seconds=120)).isoformat()}
    assert anuncios.ads_state(CFG, 5, None, NOW)['remaining_today'] == 0
    assert anuncios.ads_state(CFG, 1, NOW - timedelta(seconds=999), NOW)['next_at'] is None


def _evento(pg, aid, tx, day, creado, outcome='credited'):
    pg.execute("INSERT INTO reward_ad_events(transaction_id,account_id,nonce,coins,outcome,day,created_at) "
               "VALUES(%s,%s,%s,10,%s,%s,%s)", (tx, aid, 'n-' + tx, outcome, day, creado))


def test_pg_ticket_unico_abierto_y_cancelacion(pg):
    t = anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW)
    assert t['unit_id'] == CFG['ad_unit_android'] and len(t['nonce']) == 32
    assert t['user_id'] == rewards.wallet(pg, -92001)['uid']
    with pytest.raises(HTTPException) as e:
        anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW + timedelta(seconds=1))
    assert _codigo(e) == 'anuncio_en_curso'
    assert anuncios.cancel_ticket(pg, -92001, t['nonce'], NOW) == {'cancelled': True}
    assert anuncios.cancel_ticket(pg, -92001, t['nonce'], NOW) == {'cancelled': False}
    anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW + timedelta(seconds=2))


def test_pg_no_se_cancela_un_ticket_ajeno(pg):
    t = anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW)
    assert anuncios.cancel_ticket(pg, -92002, t['nonce'], NOW) == {'cancelled': False}


def test_pg_ticket_caducado_deja_pedir_otro(pg):
    anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW)
    anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW + anuncios.TICKET_TTL + timedelta(seconds=1))


def test_pg_tope_diario_pausa_y_reinicio_utc(pg):
    ayer = (NOW - timedelta(days=1)).date()
    for i in range(5):
        _evento(pg, -92001, f'a{i}', ayer, NOW - timedelta(hours=20))       # ayer: no cuenta hoy
    anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW)
    pg.execute("DELETE FROM reward_ad_tickets WHERE account_id=-92001")
    for i in range(5):
        _evento(pg, -92001, f'h{i}', NOW.date(), NOW - timedelta(hours=2))  # hoy: 5 → tope
    with pytest.raises(HTTPException) as e:
        anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW)
    assert _codigo(e) == 'limite_diario'
    siguiente = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    anuncios.issue_ticket(pg, -92001, CFG, 'android', siguiente)            # 00:00 UTC: contador a 0


def test_pg_pausa_cuenta_desde_el_ultimo_credito_aunque_sea_de_ayer(pg):
    ahora = datetime(2026, 10, 15, 0, 1, tzinfo=timezone.utc)
    _evento(pg, -92001, 'x1', ahora.date() - timedelta(days=1), ahora - timedelta(seconds=60))
    with pytest.raises(HTTPException) as e:
        anuncios.issue_ticket(pg, -92001, CFG, 'android', ahora)
    assert _codigo(e) == 'anuncio_en_espera'


def test_pg_el_resumen_incluye_el_bloque_ads(pg):
    from fastapi import Response
    from starlette.requests import Request
    cuenta = pg.execute('SELECT * FROM accounts WHERE account_id=-92001').fetchone()
    pg.execute('UPDATE reward_settings SET ads_enabled=TRUE WHERE id=1')
    out = rewards.overview(Request({'type': 'http', 'headers': []}), Response(), cuenta)
    assert out['ads']['enabled'] is True and out['ads']['remaining_today'] == 5
    assert rewards.overview(Request({'type': 'http', 'headers': []}), Response(), None)['ads'] == {'enabled': False}
