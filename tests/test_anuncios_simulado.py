"""Crédito simulado de videos en modo prueba (src/qf/api/anuncios.py).

Los bloques de prueba de Google no disparan el callback SSV, así que sin esto el ciclo completo
no se puede ver en un teléfono. Solo funciona con el modo prueba encendido Y para los correos de
`QF_ADS_TEST_CREDIT_EMAILS`: sin esa lista nadie puede acreditarse sin ver un anuncio real.
"""
from datetime import timedelta

import pytest
from fastapi import HTTPException

from qf.api import anuncios, rewards
from test_anuncios import CFG, NOW, pg  # noqa: F401 - `pg` es una fixture compartida

PRUEBA = CFG | {'ad_test_mode': True}
CORREO = 'ads-test-92001@invalid.example'


def test_permitido_exige_modo_prueba_y_correo_en_la_lista(monkeypatch):
    monkeypatch.setenv('QF_ADS_TEST_CREDIT_EMAILS', 'Yo@Ejemplo.com, otro@ejemplo.com')
    assert anuncios.simulated_credit_allowed(PRUEBA, 'yo@ejemplo.com')
    assert anuncios.simulated_credit_allowed(PRUEBA, 'OTRO@ejemplo.com')
    assert not anuncios.simulated_credit_allowed(PRUEBA, 'ajeno@ejemplo.com')
    assert not anuncios.simulated_credit_allowed(CFG, 'yo@ejemplo.com')                  # modo prueba apagado
    assert not anuncios.simulated_credit_allowed(PRUEBA | {'ads_enabled': False}, 'yo@ejemplo.com')


@pytest.mark.parametrize('valor', ['', None, ' , '])
def test_sin_lista_nadie_puede(monkeypatch, valor):
    if valor is None:
        monkeypatch.delenv('QF_ADS_TEST_CREDIT_EMAILS', raising=False)
    else:
        monkeypatch.setenv('QF_ADS_TEST_CREDIT_EMAILS', valor)
    assert not anuncios.simulated_credit_allowed(PRUEBA, 'yo@ejemplo.com')
    assert not anuncios.simulated_credit_allowed(PRUEBA, '')


def test_pg_el_ticket_avisa_solo_a_las_cuentas_autorizadas(pg, monkeypatch):
    monkeypatch.setenv('QF_ADS_TEST_CREDIT_EMAILS', CORREO)
    assert anuncios.issue_ticket(pg, -92001, PRUEBA, 'android', NOW)['test_credit'] is True
    assert anuncios.issue_ticket(pg, -92002, PRUEBA, 'android', NOW)['test_credit'] is False
    pg.execute('DELETE FROM reward_ad_tickets')
    assert anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW)['test_credit'] is False


def test_pg_acredita_diez_monedas_y_es_idempotente(pg, monkeypatch):
    monkeypatch.setenv('QF_ADS_TEST_CREDIT_EMAILS', CORREO)
    t = anuncios.issue_ticket(pg, -92001, PRUEBA, 'android', NOW)
    ahora = NOW + timedelta(seconds=30)
    assert anuncios.simulated_credit(pg, -92001, t['nonce'], 'android', PRUEBA, ahora) == 'credited'
    assert anuncios.simulated_credit(pg, -92001, t['nonce'], 'android', PRUEBA, ahora) == 'credited'
    assert rewards.wallet(pg, -92001)['balance'] == 10
    fila = pg.execute("SELECT delta,kind FROM reward_ledger WHERE event_key=%s",
                      (f"ad:test:{t['nonce']}",)).fetchone()
    assert (fila['delta'], fila['kind']) == (10, 'ad')
    assert pg.execute('SELECT count(*) AS n FROM reward_ad_events').fetchone()['n'] == 1


def test_pg_cuenta_no_autorizada_o_sin_modo_prueba_recibe_403_y_nada_cambia(pg, monkeypatch):
    t = anuncios.issue_ticket(pg, -92001, PRUEBA, 'android', NOW)
    ahora = NOW + timedelta(seconds=30)
    monkeypatch.delenv('QF_ADS_TEST_CREDIT_EMAILS', raising=False)
    with pytest.raises(HTTPException) as e:
        anuncios.simulated_credit(pg, -92001, t['nonce'], 'android', PRUEBA, ahora)
    assert e.value.status_code == 403
    monkeypatch.setenv('QF_ADS_TEST_CREDIT_EMAILS', CORREO)
    with pytest.raises(HTTPException):
        anuncios.simulated_credit(pg, -92001, t['nonce'], 'android', CFG, ahora)           # modo prueba apagado
    assert rewards.wallet(pg, -92001)['balance'] == 0
    assert pg.execute('SELECT count(*) AS n FROM reward_ad_events').fetchone()['n'] == 0


def test_pg_respeta_ticket_y_tope_como_el_callback_real(pg, monkeypatch):
    monkeypatch.setenv('QF_ADS_TEST_CREDIT_EMAILS', CORREO)
    ahora = NOW + timedelta(seconds=30)
    assert anuncios.simulated_credit(pg, -92001, 'no-existe', 'android', PRUEBA, ahora) == 'rejected_ticket'
    t = anuncios.issue_ticket(pg, -92001, PRUEBA, 'android', NOW)
    pg.execute('UPDATE reward_ad_tickets SET cancelled_at=%s WHERE nonce=%s', (NOW, t['nonce']))
    assert anuncios.simulated_credit(pg, -92001, t['nonce'], 'android', PRUEBA, ahora) == 'rejected_ticket'
    assert rewards.wallet(pg, -92001)['balance'] == 0
