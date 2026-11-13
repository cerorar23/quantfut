"""Diccionario de textos de los bloques de contenido (src/qf/api/bloques_textos.py).

Regla del proyecto: todo texto que pueda verse en la app lleva sus 6 idiomas (es, en, pt, fr, it, de).
"""
import re

import pytest

from qf.api import bloques_textos as bt


def test_cada_clave_tiene_los_seis_idiomas_no_vacios():
    assert bt.IDIOMAS == ('es', 'en', 'pt', 'fr', 'it', 'de')
    assert bt.TEXTOS
    for clave, tr in bt.TEXTOS.items():
        assert len(tr) == len(bt.IDIOMAS), clave
        assert all(isinstance(t, str) and t.strip() for t in tr), clave
        assert not any('<' in t or '>' in t for t in tr), clave          # sin HTML
        if len(tr[0]) > 30:
            assert all(t != tr[0] for t in tr[1:]), f'sin traducir: {clave}'
        assert len(tr[0]) <= 600, clave


def test_claves_en_minuscula_y_sin_prefijo():
    for clave in bt.TEXTOS:
        assert re.fullmatch(r'[a-z0-9_]{1,40}', clave), clave


def test_resolver_traduce_claves_y_deja_nombres_propios():
    assert bt.resolver('@forma', 'en') == 'Recent form'
    assert bt.resolver('@forma', 'de') == 'Aktuelle Form'
    assert bt.resolver('Real Madrid', 'en') == 'Real Madrid'
    assert bt.resolver('42', 'fr') == '42'


def test_idioma_desconocido_cae_a_espanol():
    assert bt.texto('forma', 'zz') == 'Forma reciente'
    assert bt.texto('forma') == 'Forma reciente'


def test_idioma_vacio_cae_a_espanol(monkeypatch):
    monkeypatch.setitem(bt.TEXTOS, 'rota', ('Uno', ' ', 'Um', 'Un', 'Uno', 'Eins'))
    assert bt.texto('rota', 'en') == 'Uno' and bt.texto('rota', 'pt') == 'Um'


def test_clave_inexistente_falla():
    with pytest.raises(KeyError):
        bt.resolver('@no_existe', 'es')
