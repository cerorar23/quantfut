"""Paso B — fórmulas analíticas: de las estimaciones a PARÁMETROS de distribuciones (todavía nada simulado).

Entrada: `SalidaPasoA`. Salida: los parámetros que el Monte Carlo necesita para simular el partido y a cada jugador de rotación.
"""
from pydantic import Field, model_validator

from .base import Contrato, Hash256, Minutos, NoNegativo, Positivo, Instante
from .paso_a import Estadistica, SalidaPasoA

__all__ = ["ParametrosMarcador", "ParametrosConteo", "SalidaPasoB", "SalidaPasoA"]


class ParametrosMarcador(Contrato):
    """Marcador conjunto: margen y total normales independientes (v2.x); puntos de cada equipo = (total ± margen) / 2."""
    mu_local: float = Field(ge=40.0, le=200.0)
    mu_visitante: float = Field(ge=40.0, le=200.0)
    sigma_margen: float = Field(gt=3.0, le=40.0)
    sigma_total: float = Field(gt=3.0, le=40.0)
    margen_equipo: float = Field(ge=-60.0, le=60.0)
    margen_jugadores: float | None = Field(default=None, ge=-60.0, le=60.0)


class ParametrosConteo(Contrato):
    """Conteo de un jugador: binomial negativa de media tasa × minutos, mezclada sobre las muestras de minutos si juega."""
    jugador_id: int = Field(gt=0)
    estadistica: Estadistica
    tasa_por_minuto: NoNegativo
    alfa: Positivo = Field(lt=5.0)                       # sobredispersión: var = mu + alfa * mu^2
    minutos_muestras: list[Minutos] = Field(min_length=5, max_length=200)
    techo: int = Field(ge=5, le=200)
    p_juega: float = Field(ge=0.0, le=1.0)


class SalidaPasoB(Contrato):
    partido_id: int = Field(gt=0)
    corte: Instante
    version_datos: Hash256
    version_modelo: str = Field(min_length=3)
    marcador: ParametrosMarcador
    jugadores: list[ParametrosConteo]

    @model_validator(mode="after")
    def _sin_duplicados(self):
        claves = [(j.jugador_id, j.estadistica) for j in self.jugadores]
        if len(claves) != len(set(claves)):
            raise ValueError("un jugador y una estadística aparecen una sola vez")
        return self
