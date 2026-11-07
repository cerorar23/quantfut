"""Normalización de nombres para la identidad entre fuentes (puro, sin base)."""
import pytest

from tenis.identidad.normalizar import claves_apellido, nombre_clave, tokens


@pytest.mark.parametrize("nombre, esperado", [
    ("Carreño Busta", ["carreno", "busta"]),
    ("Auger-Aliassime", ["augeraliassime"]),
    ("O'Connell", ["oconnell"]),
    ("Alex De Minaur", ["alex", "deminaur"]),
    ("Alex de Minaur", ["alex", "deminaur"]),
    ("Seung-Hoon Lee", ["seunghoon", "lee"]),
])
def test_tokens_quitan_tildes_y_pegan_guiones_y_particulas(nombre, esperado):
    assert tokens(nombre) == esperado


def test_nombre_clave_no_depende_del_orden():
    assert nombre_clave("Alcaraz Carlos") == nombre_clave("Carlos Alcaraz")
    assert nombre_clave("Carreño Busta Roberto") == nombre_clave("Roberto Carreno Busta")


def test_apellido_inicial_y_nombre_apellido_son_comparables():
    assert claves_apellido("Alcaraz C.") & claves_apellido("Carlos Alcaraz")
    assert claves_apellido("Carreño Busta R.") & claves_apellido("Roberto Carreno Busta")


def test_apellido_compuesto_con_guion_y_particula():
    assert claves_apellido("Auger-Aliassime F.") & claves_apellido("Felix Auger Aliassime")
    assert claves_apellido("De Minaur A.") & claves_apellido("Alex De Minaur")
    assert claves_apellido("O'Connell C.") & claves_apellido("Christopher O'Connell")


def test_orden_apellido_nombre_se_resuelve_con_clave_exacta():
    assert nombre_clave("Alcaraz Carlos") == nombre_clave("Carlos Alcaraz")
    assert nombre_clave("Muller Alexandre") == nombre_clave("Alexandre Müller")


def test_nombres_con_mismo_apellido_y_distinto_nombre_no_comparten_clave_inversa():
    assert not (claves_apellido("Carlos Alcaraz") & claves_apellido("Alcaraz Juan"))


def test_nombre_de_una_palabra_no_tiene_claves():
    assert claves_apellido("Unknown") == frozenset()
    assert claves_apellido("") == frozenset()


def test_distinto_apellido_o_inicial_no_coincide():
    assert not (claves_apellido("Carlos Alcaraz") & claves_apellido("Carlos Alcantara"))
    assert not (claves_apellido("Carlos Alcaraz") & claves_apellido("Juan Alcaraz"))
