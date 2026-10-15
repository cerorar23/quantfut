"""Callback SSV de AdMob y acreditación de monedas (src/qf/api/anuncios.py)."""
import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI
from fastapi.testclient import TestClient

from qf.api import anuncios, rewards
from qf.api import anuncios_ssv as ssv
from test_anuncios import CFG, NOW, _evento, pg  # noqa: F401 - `pg` es una fixture compartida

CUENTA = {'status': 'active', 'email_verified_at': NOW}
TICKET = {'used_at': None, 'cancelled_at': None, 'expires_at': NOW + timedelta(minutes=3), 'day': NOW.date()}


def _decidir(**kw):
    base = dict(ticket=TICKET, account=CUENTA, cfg=CFG, ad_unit='1234567890', used_today=0, now=NOW)
    base.update(kw)
    return anuncios.decide_outcome(**base)


def test_decide_acredita_y_compara_la_unidad_normalizada():
    assert _decidir() == 'credited'
    assert _decidir(ad_unit='ca-app-pub-1234567890123456/1234567890') == 'credited'
    assert _decidir(ad_unit='999') == 'rejected_unit'
    assert _decidir(cfg=CFG | {'ad_test_mode': True}, ad_unit='5224354917') == 'credited'   # bloque de prueba


@pytest.mark.parametrize('ticket', [
    None,
    TICKET | {'used_at': NOW},
    TICKET | {'cancelled_at': NOW},
    TICKET | {'expires_at': NOW - timedelta(seconds=1)},
])
def test_decide_rechaza_tickets_invalidos(ticket):
    assert _decidir(ticket=ticket) == 'rejected_ticket'


def test_decide_cuenta_y_tope():
    assert _decidir(account={'status': 'suspended', 'email_verified_at': NOW}) == 'rejected_account'
    assert _decidir(account={'status': 'active', 'email_verified_at': None}) == 'rejected_account'
    assert _decidir(used_today=5) == 'rejected_cap'
    assert _decidir(used_today=4) == 'credited'


def _credito(pg, tx='tx1', aid=-92001, ad_unit='1234567890', cfg=CFG, now=NOW):
    t = anuncios.issue_ticket(pg, aid, cfg, 'android', now)
    return t, lambda **kw: anuncios.credit(pg, transaction_id=kw.get('tx', tx), uid=t['user_id'],
                                           nonce=kw.get('nonce', t['nonce']), ad_unit=ad_unit, cfg=cfg,
                                           now=now + timedelta(seconds=30))


def test_pg_acredita_diez_monedas_en_el_libro(pg):
    t, run = _credito(pg)
    assert run() == 'credited'
    assert rewards.wallet(pg, -92001)['balance'] == 10
    fila = pg.execute("SELECT delta,kind FROM reward_ledger WHERE event_key='ad:tx1'").fetchone()
    assert (fila['delta'], fila['kind']) == (10, 'ad')
    assert pg.execute('SELECT used_at FROM reward_ad_tickets WHERE nonce=%s', (t['nonce'],)).fetchone()['used_at']


def test_pg_reintento_del_mismo_transaction_id_acredita_una_vez(pg):
    t, run = _credito(pg)
    assert run() == 'credited'
    assert run() == 'credited'
    assert rewards.wallet(pg, -92001)['balance'] == 10
    assert pg.execute('SELECT count(*) AS n FROM reward_ad_events').fetchone()['n'] == 1


def test_pg_sin_ticket_o_ajeno_responde_sin_acreditar(pg):
    t, run = _credito(pg)
    assert run(nonce='no-existe', tx='tx-a') == 'rejected_ticket'
    otro = anuncios.issue_ticket(pg, -92002, CFG, 'android', NOW)
    assert run(nonce=otro['nonce'], tx='tx-b') == 'rejected_ticket'         # nonce de otra cuenta
    assert rewards.wallet(pg, -92001)['balance'] == 0


def test_pg_usuario_desconocido_no_escribe_nada(pg):
    assert anuncios.credit(pg, transaction_id='tx-u', uid='', nonce='', ad_unit='1', cfg=CFG,
                           now=NOW) == 'unknown_user'
    assert pg.execute('SELECT count(*) AS n FROM reward_ad_events').fetchone()['n'] == 0


def test_pg_ticket_de_las_23_59_cuenta_en_su_dia_aunque_llegue_a_las_00_01(pg):
    noche = datetime(2026, 10, 14, 23, 59, tzinfo=timezone.utc)
    t = anuncios.issue_ticket(pg, -92001, CFG, 'android', noche)
    anuncios.credit(pg, transaction_id='tx-n', uid=t['user_id'], nonce=t['nonce'], ad_unit='1234567890',
                    cfg=CFG, now=noche + timedelta(minutes=2))
    assert pg.execute("SELECT day FROM reward_ad_events WHERE transaction_id='tx-n'").fetchone()['day'] == noche.date()


def test_pg_tope_al_acreditar_deja_evento_con_cero_monedas(pg):
    t, run = _credito(pg)
    for i in range(5):
        _evento(pg, -92001, f'c{i}', NOW.date(), NOW - timedelta(hours=2))
    assert run() == 'rejected_cap'
    assert rewards.wallet(pg, -92001)['balance'] == 0
    assert pg.execute("SELECT coins,outcome FROM reward_ad_events WHERE transaction_id='tx1'").fetchone() == \
        {'coins': 0, 'outcome': 'rejected_cap'}


def test_pg_cuenta_suspendida_entre_ticket_y_callback_no_cobra(pg):
    t, run = _credito(pg)
    pg.execute("UPDATE accounts SET status='suspended' WHERE account_id=-92001")
    assert run() == 'rejected_account'
    assert rewards.wallet(pg, -92001)['balance'] == 0


def test_pg_apagar_los_anuncios_no_impide_acreditar_un_ticket_ya_emitido(pg):
    t = anuncios.issue_ticket(pg, -92001, CFG, 'android', NOW)
    pg.execute('UPDATE reward_settings SET ads_enabled=FALSE WHERE id=1')
    assert anuncios.credit(pg, transaction_id='tx-off', uid=t['user_id'], nonce=t['nonce'], ad_unit='1234567890',
                           cfg=CFG | {'ads_enabled': False}, now=NOW) == 'credited'


def test_pg_el_credito_de_anuncio_no_valida_referidos(pg):
    pg.execute('INSERT INTO reward_referrals(invitee_id,referrer_id) VALUES(-92002,-92001)')
    t = anuncios.issue_ticket(pg, -92002, CFG, 'android', NOW)
    anuncios.credit(pg, transaction_id='tx-r', uid=t['user_id'], nonce=t['nonce'], ad_unit='1234567890',
                    cfg=CFG, now=NOW)
    assert pg.execute('SELECT qualified_at FROM reward_referrals WHERE invitee_id=-92002').fetchone()['qualified_at'] is None
    assert rewards.wallet(pg, -92001)['balance'] == 0


# --- ruta HTTP -----------------------------------------------------------------

def _par():
    priv = ec.generate_private_key(ec.SECP256R1())
    der = priv.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return priv, der


def _firmada(priv, **q):
    base = {'ad_network': '1', 'ad_unit': '1234567890', 'reward_amount': '5000', 'reward_item': 'coins',
            'timestamp': '1', 'transaction_id': 'tx-http', 'user_id': 'u', 'custom_data': 'n'}
    base.update(q)
    contenido = '&'.join(f'{k}={v}' for k, v in sorted(base.items()) if v is not None)
    sig = base64.urlsafe_b64encode(priv.sign(contenido.encode(), ec.ECDSA(hashes.SHA256()))).decode().rstrip('=')
    return f'{contenido}&signature={sig}&key_id=7'


@pytest.fixture
def http(monkeypatch):
    priv, der = _par()
    monkeypatch.setattr(ssv, 'keys_for', lambda key_id, fetch=None: {'7': der})
    app = FastAPI()
    app.include_router(anuncios.router)
    return TestClient(app), priv


def test_http_firma_invalida_es_403_y_no_toca_la_base(http, monkeypatch):
    client, priv = http

    def sin_base():
        raise AssertionError('no debe tocar la BD')
    monkeypatch.setattr(anuncios, 'conn', sin_base)
    q = _firmada(priv).replace('reward_amount=5000', 'reward_amount=9999')
    assert client.get('/rewards/callback/admob?' + q).status_code == 403
    assert client.get('/rewards/callback/admob?transaction_id=x').status_code == 403


def test_http_claves_no_disponibles_es_503_para_que_google_reintente(http, monkeypatch):
    client, priv = http

    def sin_claves(key_id, fetch=None):
        raise ssv.KeysUnavailable('x')
    monkeypatch.setattr(ssv, 'keys_for', sin_claves)
    assert client.get('/rewards/callback/admob?' + _firmada(priv)).status_code == 503


def test_pg_http_sin_user_id_ni_custom_data_responde_200_sin_acreditar(http, pg):
    client, priv = http
    r = client.get('/rewards/callback/admob?' + _firmada(priv, user_id=None, custom_data=None))
    assert r.status_code == 200 and r.text == 'OK'
    assert pg.execute('SELECT count(*) AS n FROM reward_ad_events').fetchone()['n'] == 0


def test_pg_http_acredita_con_la_cantidad_del_servidor_y_no_la_de_google(http, pg):
    client, priv = http
    t = anuncios.issue_ticket(pg, -92001, CFG, 'android', datetime.now(timezone.utc))
    pg.execute("UPDATE reward_settings SET ads_enabled=TRUE, ad_test_mode=FALSE, "
               "ad_unit_android='ca-app-pub-1234567890123456/1234567890' WHERE id=1")
    r = client.get('/rewards/callback/admob?' + _firmada(priv, user_id=t['user_id'], custom_data=t['nonce']))
    assert r.status_code == 200
    assert rewards.wallet(pg, -92001)['balance'] == 10          # reward_amount=5000 de Google se ignora
