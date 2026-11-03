"""Base de todos los contratos: estrictos, inmutables, sin campos de más y sin NaN ni infinitos.

Un contrato es la frontera entre dos pasos del motor. Si algo cruza la frontera, ya está validado: lo que no cumple no se simula, no se sella
y no se sirve. Aquí solo hay tipos y reglas reutilizables; ningún contrato contiene lógica de modelo.
"""
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

Probabilidad = Annotated[float, Field(ge=0.0, le=1.0)]
Minutos = Annotated[float, Field(ge=0.0, le=60.0)]       # nadie juega más de 60 minutos (prórrogas largas incluidas)
Positivo = Annotated[float, Field(gt=0.0)]
NoNegativo = Annotated[float, Field(ge=0.0)]
Hash256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Tricode = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


def _con_zona(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        raise ValueError("el instante necesita zona horaria")
    return valor


Instante = Annotated[datetime, AfterValidator(_con_zona)]


def _no_decreciente(valores: list[float]) -> list[float]:
    if any(b < a for a, b in zip(valores, valores[1:])):
        raise ValueError("los valores deben ser no decrecientes")
    return valores


Cuantiles199 = Annotated[list[float], Field(min_length=199, max_length=199), AfterValidator(_no_decreciente)]


class Contrato(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True, allow_inf_nan=False)
