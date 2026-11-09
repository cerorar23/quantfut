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
    yield
    nba_datos.vaciar_cache()
