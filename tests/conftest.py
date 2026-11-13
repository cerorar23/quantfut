"""Ajustes comunes de las pruebas."""
import os

# El seguimiento de tarjetas viene ENCENDIDO por defecto en producción (no publica nada y
# activarlo por entorno obligaría a recrear el worker). Las pruebas del job diario no
# simulan su consulta, así que arrancan con él apagado; las suyas lo encienden a mano.
os.environ.setdefault("TARJETAS_SEG_ENABLED", "0")


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _sin_red_hacia_nba_api(monkeypatch):
    """Las páginas públicas de NBA leen `nba-api` por HTTP. Ninguna prueba debe salir a la red (ni esperar el
    tiempo de espera de un contenedor que no existe): por defecto la cartelera está vacía. Las pruebas que
    necesitan datos reemplazan `_pedir` (tests/test_nba_paginas.py)."""
    try:
        from qf.api import nba_datos
    except Exception:   # pruebas de otros paquetes sin la API en el camino
        yield
        return

    def vacio(ruta, params=None):
        if ruta == "/nba/v1/cartelera":
            return {"fecha": (params or {}).get("fecha"), "partidos": []}
        raise nba_datos.NbaNoDisponible("sin red en pruebas")

    nba_datos.vaciar_cache()
    monkeypatch.setattr(nba_datos, "_pedir", vacio)
    # Igual con la base en las páginas de fútbol: sin datos (agenda vacía) y sin tocar Postgres.
    from qf.api import futbol_datos
    monkeypatch.setattr(futbol_datos, "secciones_activas", lambda: {"estadisticas": True, "h2h": True})
    monkeypatch.setattr(futbol_datos, "agenda_dia", lambda d: [])
    monkeypatch.setattr(futbol_datos, "pronosticos", lambda ids: {})
    from qf.api import tenis_datos
    monkeypatch.setattr(tenis_datos, "eventos", lambda: [])   # sin feed de tenis: no hay volumen en las pruebas
    # Calibración: datos de ejemplo (sin base ni red) para que /calibracion/ responda 200 en las pruebas que recorren enlaces.
    import datos_calibracion
    from qf.api import calibracion
    monkeypatch.setattr(calibracion, "carga_futbol", lambda: datos_calibracion.FUTBOL)
    monkeypatch.setattr(calibracion, "carga_nba", lambda: datos_calibracion.NBA)
    from qf.api import verificacion
    monkeypatch.setattr(verificacion, "carga_lotes", lambda limite=90: None)
    yield
    nba_datos.vaciar_cache()


@pytest.fixture(autouse=True)
def _reglas_de_acceso_de_codigo(monkeypatch):
    """Sin Postgres: las reglas de acceso (db/111) valen los valores de hoy y `dias_agenda` 7.
    Las pruebas de tests/test_acceso_reglas.py sustituyen `_cargar` con las suyas."""
    try:
        from qf.comercial import acceso_reglas
    except Exception:
        yield
        return
    monkeypatch.setattr(acceso_reglas, "_cargar", lambda: [acceso_reglas.HOY])
    monkeypatch.setattr(acceso_reglas, "_cargar_dias", lambda: acceso_reglas.DIAS_AGENDA_DEFECTO)
    acceso_reglas.invalidar_cache()
    yield
    acceso_reglas.invalidar_cache()


@pytest.fixture(autouse=True)
def _catalogo_de_codigo(monkeypatch):
    """Sin Postgres: el catálogo de deportes (db/112) vale la semilla del código.
    Las pruebas de tests/test_catalogo.py sustituyen `_cargar` con las suyas."""
    try:
        from qf.comercial import catalogo
    except Exception:
        yield
        return
    monkeypatch.setattr(catalogo, "_cargar", catalogo._de_semilla)
    catalogo.invalidar_cache()
    yield
    catalogo.invalidar_cache()


@pytest.fixture(autouse=True)
def _pantallas_de_codigo(monkeypatch):
    """Sin Postgres: sin pantallas publicadas (db/113), cada cliente usa su orden de hoy.
    Las pruebas de tests/test_pantallas.py sustituyen `_cargar` con las suyas."""
    try:
        from qf.comercial import pantallas
    except Exception:
        yield
        return
    monkeypatch.setattr(pantallas, "_cargar", lambda: {})
    pantallas.invalidar_cache()
    yield
    pantallas.invalidar_cache()
