"""Interfaz del proveedor de calendario y resultados (decisión D3: el proveedor puede cambiar).

Solo hay contrato, interfaz (`Protocol`) y un proveedor falso en memoria para pruebas. No hay implementación real.
"""
from datetime import datetime
from typing import Literal, Protocol

from pydantic import Field, model_validator

from ..contratos.base import Contrato, Instante

Estado = Literal["programado", "en_juego", "terminado", "aplazado", "cancelado"]


class EventoCalendario(Contrato):
    evento_id: str = Field(min_length=1)
    circuito: Literal["atp", "wta"]
    torneo: str = Field(min_length=1)
    ronda: str = Field(pattern=r"^[A-Z]{1,2}[0-9]*$")
    jugador_1_id: int = Field(ge=1)
    jugador_2_id: int = Field(ge=1)
    inicio_utc: Instante
    estado: Estado

    @model_validator(mode="after")
    def _jugadores_distintos(self):
        if self.jugador_1_id == self.jugador_2_id:
            raise ValueError("los dos jugadores del evento son el mismo")
        return self


class ProveedorCalendario(Protocol):
    nombre: str

    def eventos(self, desde: datetime, hasta: datetime) -> list[EventoCalendario]:
        """Eventos con inicio en [desde, hasta)."""
        ...


class ProveedorFalso:
    """Proveedor en memoria para pruebas. No consulta ninguna red."""

    nombre = "falso"

    def __init__(self, eventos: list[EventoCalendario]) -> None:
        self._eventos = list(eventos)

    def eventos(self, desde: datetime, hasta: datetime) -> list[EventoCalendario]:
        return [e for e in self._eventos if desde <= e.inicio_utc < hasta]
