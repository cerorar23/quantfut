"""Validación en las fronteras: lo que no cumple el contrato no se sella y no se sirve.

Funciones sin efectos: reciben el diccionario tal como se guarda en `nba.pronostico.distribucion` y lanzan `ContratoIncumplido` con un
mensaje corto (apto para el registro y las alertas) si no cumple.
"""
from pydantic import ValidationError

from .paso_c import DistribucionEquipo, DistribucionJugador


class ContratoIncumplido(ValueError):
    pass


def _validar(modelo, datos: dict, etiqueta: str) -> None:
    try:
        modelo.model_validate(datos)
    except ValidationError as e:
        primeros = "; ".join(f"{'.'.join(str(p) for p in x['loc'])}: {x['msg']}" for x in e.errors()[:2])
        raise ContratoIncumplido(f"{etiqueta} no cumple el contrato ({e.error_count()} errores): {primeros}"[:300]) from None


def validar_equipo(distribucion: dict) -> None:
    _validar(DistribucionEquipo, distribucion, "distribución de equipo")


def validar_jugador(distribucion: dict) -> None:
    _validar(DistribucionJugador, distribucion, "distribución de jugador")
