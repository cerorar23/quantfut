import pytest

from qf.comercial import cifrado


@pytest.fixture
def clave(monkeypatch):
    k = cifrado.generar_clave()
    monkeypatch.setenv(cifrado.ENV_KEY, k)
    monkeypatch.delenv(cifrado.ENV_OLD, raising=False)
    return k


def test_roundtrip_y_nonce_aleatorio(clave):
    a, b = cifrado.cifrar('s3cret', 'reward_provider:tapjoy'), cifrado.cifrar('s3cret', 'reward_provider:tapjoy')
    assert a != b and 's3cret' not in a
    assert cifrado.descifrar(a, 'reward_provider:tapjoy') == 's3cret'


def test_contexto_distinto_o_dato_alterado_falla(clave):
    t = cifrado.cifrar('s3cret', 'reward_provider:tapjoy')
    with pytest.raises(cifrado.CifradoError):
        cifrado.descifrar(t, 'reward_provider:bitlabs')
    ultimo = 'A' if t[-1] != 'A' else 'B'
    with pytest.raises(cifrado.CifradoError):
        cifrado.descifrar(t[:-1] + ultimo, 'reward_provider:tapjoy')


def test_sin_clave_falla_cerrado(monkeypatch):
    monkeypatch.delenv(cifrado.ENV_KEY, raising=False)
    assert not cifrado.disponible()
    with pytest.raises(cifrado.CifradoError):
        cifrado.cifrar('x', 'c')


def test_clave_de_longitud_incorrecta(monkeypatch):
    monkeypatch.setenv(cifrado.ENV_KEY, 'corta')
    assert not cifrado.disponible()


def test_rotacion_con_clave_anterior(monkeypatch, clave):
    t = cifrado.cifrar('s3cret', 'ctx')
    monkeypatch.setenv(cifrado.ENV_OLD, clave)
    monkeypatch.setenv(cifrado.ENV_KEY, cifrado.generar_clave())
    assert cifrado.descifrar(t, 'ctx') == 's3cret'
    assert cifrado.descifrar(cifrado.cifrar('s3cret', 'ctx'), 'ctx') == 's3cret'
