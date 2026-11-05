"""Salidas del simulador y del sellado (plan A.5): distribución conjunta y pronóstico sellado."""
from typing import Annotated

from pydantic import Field, model_validator

from .base import Contrato, Hash256, Instante
from .marcador import FormatoPartido, SetMarcador, validar_marcador
from .mercados import Mercados, validar_mercados

TOLERANCIA_SUMA = 1e-9


class EntradaMarcador(Contrato):
    """Un marcador completo del partido, set por set, con su probabilidad conjunta."""
    sets: list[SetMarcador] = Field(min_length=2, max_length=5)
    probabilidad: Annotated[float, Field(gt=0.0, le=1.0)]


class DistribucionPartido(FormatoPartido):
    entradas: list[EntradaMarcador] = Field(min_length=1)
    mercados: Mercados

    @model_validator(mode="after")
    def _valida(self):
        vistos: set[tuple] = set()
        for e in self.entradas:
            validar_marcador(e.sets, self.mejor_de, self.regla_decisivo)
            clave = tuple((s.juegos_a, s.juegos_b, s.tiebreak) for s in e.sets)
            if clave in vistos:
                raise ValueError("marcador duplicado en la distribución")
            vistos.add(clave)
        total = sum(e.probabilidad for e in self.entradas)
        if abs(total - 1.0) > TOLERANCIA_SUMA:
            raise ValueError(f"la masa de probabilidad suma {total:.12f}, no 1")
        validar_mercados(self.mercados, self.entradas)
        return self


class PronosticoSellado(Contrato):
    partido_id: int = Field(gt=0)
    version_modelo: str = Field(min_length=1)
    posicion: int = Field(ge=1)              # 1 = primer sello de la cadena
    corte: Instante
    sellado_en: Instante
    hash_previo: Hash256 | None
    hash: Hash256
    distribucion: DistribucionPartido

    @model_validator(mode="after")
    def _coherente(self):
        if not self.version_modelo.strip():
            raise ValueError("la versión de modelo no puede estar vacía")
        if (self.posicion == 1) != (self.hash_previo is None):
            raise ValueError("hash_previo solo puede faltar en el primer sello (posición 1)")
        if not self.corte < self.sellado_en:
            raise ValueError("el corte debe ser anterior al sellado")
        return self
