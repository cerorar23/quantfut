"""Paso C — Monte Carlo: entrada (parámetros + simulaciones + semilla) y salida (las distribuciones que se sellan y se sirven).

Las dos distribuciones de salida tienen EXACTAMENTE la forma del JSON que ya se guarda en `nba.pronostico.distribucion`, así que el mismo
contrato sirve para validar lo que se sella, lo que lee la API y lo que sale del motor.
"""
from typing import Literal

from pydantic import Field, model_validator

from .base import Contrato, Cuantiles199, Instante, Hash256, Probabilidad
from .paso_b import SalidaPasoB

TOLERANCIA_SUMA = 1e-4


class EntradaMonteCarlo(Contrato):
    parametros: SalidaPasoB
    n_simulaciones: int = Field(ge=1_000, le=1_000_000, default=20_000)
    semilla: int = Field(ge=0)


class DistribucionEquipo(Contrato):
    p_local: Probabilidad
    mu: list[float] = Field(min_length=2, max_length=2)
    paso_cuantil: Literal[0.005]
    margen: Cuantiles199
    total: Cuantiles199
    puntos_local: Cuantiles199
    puntos_visitante: Cuantiles199

    @model_validator(mode="after")
    def _coherente(self):
        if not self.margen[0] <= self.margen[99] <= self.margen[-1]:
            raise ValueError("margen incoherente")
        if min(self.puntos_local[0], self.puntos_visitante[0], self.total[0]) < 0:
            raise ValueError("puntos negativos")
        return self


class DistribucionJugador(Contrato):
    pmf: list[float] = Field(min_length=6, max_length=201)
    media: float = Field(ge=0.0)
    p10: int = Field(ge=0)
    p50: int = Field(ge=0)
    p90: int = Field(ge=0)
    p_juega: Probabilidad
    minutos_esperados: float = Field(ge=0.0, le=60.0)

    @model_validator(mode="after")
    def _pmf_valida(self):
        if any(x < 0 for x in self.pmf) or abs(sum(self.pmf) - 1.0) > TOLERANCIA_SUMA:
            raise ValueError("la pmf debe ser no negativa y sumar 1")
        if not self.p10 <= self.p50 <= self.p90 < len(self.pmf):
            raise ValueError("p10 <= p50 <= p90 dentro del soporte")
        return self


class SalidaMonteCarlo(Contrato):
    partido_id: int = Field(gt=0)
    corte: Instante
    version_datos: Hash256
    version_modelo: str = Field(min_length=3)
    n_simulaciones: int = Field(ge=1_000)
    equipo: DistribucionEquipo
    jugadores: dict[str, DistribucionJugador]            # clave «jugador_id:estadistica»
