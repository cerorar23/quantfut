import base64

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from qf.api import anuncios_ssv as ssv

CONTENT = ('ad_network=1&ad_unit=1234567890&custom_data=abc&reward_amount=5&reward_item=coins'
           '&timestamp=1&transaction_id=tx1&user_id=u1')


def _par():
    priv = ec.generate_private_key(ec.SECP256R1())
    der = priv.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return priv, der


def _firmar(priv, content=CONTENT, key_id='111'):
    sig = priv.sign(content.encode(), ec.ECDSA(hashes.SHA256()))
    return f"{content}&signature={base64.urlsafe_b64encode(sig).decode().rstrip('=')}&key_id={key_id}"


@pytest.fixture(autouse=True)
def limpio():
    ssv.reset_cache()
    yield
    ssv.reset_cache()


def test_firma_valida():
    priv, der = _par()
    ssv.verify(_firmar(priv), {'111': der})


def test_contenido_alterado_clave_ajena_o_desconocida():
    priv, der = _par()
    _, otra = _par()
    bueno = _firmar(priv)
    with pytest.raises(ssv.SignatureError):
        ssv.verify(bueno.replace('reward_amount=5', 'reward_amount=500'), {'111': der})
    with pytest.raises(ssv.SignatureError):
        ssv.verify(bueno, {'111': otra})
    with pytest.raises(ssv.SignatureError):
        ssv.verify(bueno, {'999': der})


@pytest.mark.parametrize('raw', [
    CONTENT,                                                  # sin firma
    CONTENT + '&signature=abc',                               # sin key_id
    CONTENT + '&key_id=1&signature=abc',                      # orden invertido
    CONTENT + '&signature=abc&key_id=1&extra=1',              # algo después de key_id
    CONTENT + '&signature=a&signature=b&key_id=1',            # firma duplicada
    '&signature=abc&key_id=1',                                # sin contenido
])
def test_estructura_invalida(raw):
    with pytest.raises(ssv.SignatureError):
        ssv.split_signed(raw)


def test_parse_keys_acepta_key_id_numerico():
    _, der = _par()
    payload = {'keys': [{'keyId': 333, 'pem': 'x', 'base64': base64.b64encode(der).decode()}]}
    assert ssv.parse_keys(payload) == {'333': der}


def test_cache_24h_y_recarga_por_clave_desconocida_cada_60s(monkeypatch):
    _, der = _par()
    hora = [1000.0]
    monkeypatch.setattr(ssv, '_clock', lambda: hora[0])
    llamadas = []

    def fetch():
        llamadas.append(hora[0])
        return {'keys': [{'keyId': 1, 'base64': base64.b64encode(der).decode()}]}

    assert ssv.keys_for('1', fetch) == {'1': der}
    assert ssv.keys_for('1', fetch) == {'1': der}
    assert len(llamadas) == 1                       # caché
    ssv.keys_for('2', fetch)                        # desconocida, pero acaba de cargarse
    assert len(llamadas) == 1
    hora[0] += 61
    ssv.keys_for('2', fetch)                        # desconocida y pasó el minuto
    assert len(llamadas) == 2
    hora[0] += 24 * 3600 + 1
    ssv.keys_for('1', fetch)                        # caducada
    assert len(llamadas) == 3


def test_sin_red_y_sin_cache_es_error_recuperable():
    def fetch():
        raise OSError('sin red')
    with pytest.raises(ssv.KeysUnavailable):
        ssv.keys_for('1', fetch)


def test_con_cache_fresca_un_fallo_de_red_no_la_pierde(monkeypatch):
    _, der = _par()
    hora = [0.0]
    monkeypatch.setattr(ssv, '_clock', lambda: hora[0])
    ssv.keys_for('1', lambda: {'keys': [{'keyId': 1, 'base64': base64.b64encode(der).decode()}]})
    hora[0] += 61

    def roto():
        raise OSError('sin red')
    assert ssv.keys_for('2', roto) == {'1': der}
