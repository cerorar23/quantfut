"""Entradas del modelo: lo que cruza de la lectura PIT al motor (plan A.5)."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import Contrato, Instante
from .marcador import FormatoPartido
from .matriz import validar_covarianza

Superficie = Literal["Clay", "Grass", "Hard", "Indoor"]
Prob2a98 = Annotated[float, Field(ge=0.02, le=0.98)]


class PartidoPrevio(FormatoPartido):
    partido_id: int = Field(gt=0)
    jugador_1: int = Field(gt=0)
    jugador_2: int = Field(gt=0)
    superficie: Superficie
    indoor: bool | None
    corte: Instante
    inicio_programado_mas_temprano: Instante

    @model_validator(mode="after")
    def _coherente(self):
        if self.jugador_1 == self.jugador_2:
            raise ValueError("los dos jugadores deben ser distintos")
        if self.superficie == "Indoor" and self.indoor is not True:
            raise ValueError("superficie Indoor exige indoor=True")
        if not self.corte < self.inicio_programado_mas_temprano:
            raise ValueError("el corte debe ser anterior al inicio programado más temprano")
        return self


class EstadoJugador(Contrato):
    jugador_id: int = Field(gt=0)
    media: float
    varianza: float = Field(gt=0.0)
    n_partidos_previos: int = Field(ge=0)
    minutos_96h: float | None = Field(default=None, ge=0.0, le=1000.0)
    fatiga_desconocida: bool = False

    @model_validator(mode="after")
    def _fatiga(self):
        if self.minutos_96h is None and not self.fatiga_desconocida:
            raise ValueError("minutos_96h solo puede ser None si fatiga_desconocida=True")
        return self


class ParametrosPunto(Contrato):
    p1: Prob2a98
    p2: Prob2a98
    covarianza: list[list[float]]

    @model_validator(mode="after")
    def _covarianza(self):
        validar_covarianza(self.covarianza)
        return self
