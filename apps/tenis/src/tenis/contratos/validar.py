"""Validación en las fronteras: lo que no cumple el contrato no se sella y no se sirve.

Aceptan modelos ya validados o diccionarios (tal como se leen de la base). Lanzan ContratoInvalido con un
motivo corto, apto para el registro y para la respuesta 502 de la API.
"""
from pydantic import ValidationError

from .entrada import PartidoPrevio
from .salida import DistribucionPartido, PronosticoSellado


class ContratoInvalido(ValueError):
    pass


def _como(modelo, valor, etiqueta: str):
    if isinstance(valor, modelo):
        return valor
    try:
        return modelo.model_validate(valor)
    except ValidationError as e:
        primeros = "; ".join(f"{'.'.join(str(p) for p in x['loc'])}: {x['msg']}" for x in e.errors()[:2])
        raise ContratoInvalido(f"{etiqueta} no cumple el contrato ({e.error_count()} errores): {primeros}"[:300]) from None


def validar_antes_de_sellar(partido, distribucion) -> None:
    p = _como(PartidoPrevio, partido, "partido previo")
    d = _como(DistribucionPartido, distribucion, "distribución")
    if (p.mejor_de, p.regla_decisivo) != (d.mejor_de, d.regla_decisivo):
        raise ContratoInvalido("el formato de la distribución no coincide con el del partido")


def validar_antes_de_servir(pronostico) -> None:
    _como(PronosticoSellado, pronostico, "pronóstico sellado")
