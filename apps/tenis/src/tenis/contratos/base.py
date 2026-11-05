"""Base de los contratos del motor de tenis: estrictos, inmutables, sin campos de más y sin NaN ni infinitos.

Un contrato es la frontera entre dos pasos. Lo que no cumple no se simula, no se sella y no se sirve.
Aquí solo hay tipos y reglas reutilizables; ningún contrato contiene lógica de modelo.
"""
import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _con_zona(valor: datetime) -> datetime:
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise ValueError("el instante necesita zona horaria")
    return valor


def _hash256(valor: str) -> str:
    if re.fullmatch(r"[0-9a-f]{64}", valor) is None:
        raise ValueError("hash SHA-256 de 64 caracteres hexadecimales en minúsculas")
    return valor


Instante = Annotated[datetime, AfterValidator(_con_zona)]
Prob = Annotated[float, Field(ge=0.0, le=1.0)]
ProbPunto = Annotated[float, Field(gt=0.0, lt=1.0)]   # probabilidad de ganar un punto: intervalo abierto
Hash256 = Annotated[str, AfterValidator(_hash256)]
DuracionMin = Annotated[int, Field(gt=0, le=1440)]    # minutos de partido: nunca 0 (0 significa «no medido»)


class Contrato(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, allow_inf_nan=False)
