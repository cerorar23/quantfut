"""Pruebas de paridad estricta de localización en 6 idiomas (es, en, pt, fr, it, de)."""
import pytest

from tenis.l10n import cargar_catalogo, texto

IDIOMAS_REQUERIDOS = ("es", "en", "pt", "fr", "it", "de")


def test_catalogo_contiene_los_seis_idiomas():
    cat = cargar_catalogo()
    for lang in IDIOMAS_REQUERIDOS:
        assert lang in cat, f"Falta idioma {lang} en el catálogo"


def test_paridad_estricta_de_claves_en_todos_los_idiomas():
    cat = cargar_catalogo()
    claves_es = set(cat["es"].keys())
    assert len(claves_es) > 15, "El catálogo en español tiene muy pocas claves"

    for lang in IDIOMAS_REQUERIDOS[1:]:
        claves_lang = set(cat[lang].keys())
        faltan = claves_es - claves_lang
        sobran = claves_lang - claves_es
        assert not faltan, f"En {lang} faltan las siguientes claves: {faltan}"
        assert not sobran, f"En {lang} sobran las siguientes claves: {sobran}"
        # Verificar que ningún texto esté vacío
        for k, v in cat[lang].items():
            assert v and v.strip(), f"En {lang}, la clave '{k}' tiene texto vacío"


def test_traduccion_fallback_y_idioma():
    assert texto("nav_cartelera", "es") == "Partidos"
    assert texto("nav_cartelera", "en") == "Matches"
    assert texto("nav_cartelera", "pt") == "Jogos"
    assert texto("nav_cartelera", "fr") == "Matchs"
    assert texto("nav_cartelera", "it") == "Partite"
    assert texto("nav_cartelera", "de") == "Spiele"

    # Idioma desconocido debe caer a español
    assert texto("nav_cartelera", "ru") == "Partidos"
