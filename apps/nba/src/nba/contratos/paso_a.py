"""Paso A — estimadores: lo que sale de ratings, impacto por jugador, minutos y disponibilidad (hoy; mañana puede ser cualquier modelo).

La interfaz no presupone el tipo de modelo (regresión, boosting o red): solo exige estas salidas, ya en unidades del baloncesto.
"""
from typing import Literal

from pydantic import Field, model_validator

from .base import Contrato, Hash256, Instante, Minutos, NoNegativo, Probabilidad, Tricode

Estadistica = Literal["puntos", "rebotes", "asistencias", "triples"]


class MinutosSiJuega(Contrato):
    """Cuantiles de los minutos de un jugador condicionados a que juegue."""
    p10: Minutos
    p50: Minutos
    p90: Minutos

    @model_validator(mode="after")
    def _ordenados(self):
        if not self.p10 <= self.p50 <= self.p90:
            raise ValueError("p10 <= p50 <= p90")
        return self


class EstimacionJugador(Contrato):
    jugador_id: int = Field(gt=0)
    nombre: str = Field(min_length=1)
    equipo: Tricode
    estado: str | None = None                         # último parte oficial visible en el corte; None = sin parte
    p_juega: Probabilidad
    minutos: MinutosSiJuega
    tasa_por_minuto: dict[Estadistica, NoNegativo]
    partidos_en_historia: int = Field(ge=5)             # sin al menos 5 partidos no se estima

    @model_validator(mode="after")
    def _tasas_completas(self):
        if set(self.tasa_por_minuto) != {"puntos", "rebotes", "asistencias", "triples"}:
            raise ValueError("faltan tasas por minuto")
        return self


class DescansoDias(Contrato):
    """Días desde el último partido de cada equipo (1 = juega en la noche siguiente; 7 = sin partido reciente)."""
    local: int = Field(ge=1, le=400)
    visitante: int = Field(ge=1, le=400)


class SalidaPasoA(Contrato):
    partido_id: int = Field(gt=0)
    corte: Instante
    version_datos: Hash256
    local: Tricode
    visitante: Tricode
    margen_equipo: float = Field(ge=-60.0, le=60.0)      # puntos esperados, local menos visitante, del rating de equipo
    margen_jugadores: float | None = Field(default=None, ge=-60.0, le=60.0)   # None si no hubo plantilla suficiente
    total_equipo: float = Field(ge=100.0, le=350.0)
    descanso_dias: DescansoDias
    jugadores: list[EstimacionJugador]

    @model_validator(mode="after")
    def _equipos_distintos(self):
        if self.local == self.visitante:
            raise ValueError("local y visitante deben ser distintos")
        return self
