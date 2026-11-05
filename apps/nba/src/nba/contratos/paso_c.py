"""Paso C — Monte Carlo: entrada (parámetros + simulaciones + semilla) y salida (las distribuciones que se sellan y se sirven).

Las dos distribuciones de salida tienen EXACTAMENTE la forma del JSON que ya se guarda en `nba.pronostico.distribucion`, así que el mismo
contrato sirve para validar lo que se sella, lo que lee la API y lo que sale del motor.
"""
from typing import Literal

from pydantic import Field, model_validator

from .base import Contrato, Cuantiles199, Instante, Hash256, Probabilidad
from .paso_b import SalidaPasoB

TOLERANCIA_SUMA = 1e-4


class MasaDiscreta(Contrato):
    soporte: list[int] = Field(min_length=1, max_length=8193)
    pmf: list[float] = Field(min_length=1, max_length=8193)

    @model_validator(mode="after")
    def _masa(self):
        if len(self.soporte) != len(self.pmf) or any(b <= a for a, b in zip(self.soporte, self.soporte[1:])):
            raise ValueError("soporte discreto incompatible o no ordenado")
        if any(p < 0 for p in self.pmf) or abs(sum(self.pmf) - 1) > 1e-9:
            raise ValueError("la masa discreta no es una distribución")
        return self


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
    masas: dict[str, MasaDiscreta] | None = None
    objetivo: Literal["partido_completo_con_prorroga"] | None = None
    tratamiento_ot: Literal["final_historico_implicito", "regulacion_mas_prorroga"] | None = None

    @model_validator(mode="after")
    def _coherente(self):
        if not self.margen[0] <= self.margen[99] <= self.margen[-1]:
            raise ValueError("margen incoherente")
        if min(self.puntos_local[0], self.puntos_visitante[0], self.total[0]) < 0:
            raise ValueError("puntos negativos")
        if self.masas is not None:
            import numpy as np
            nombres = {"margen", "total", "puntos_local", "puntos_visitante"}
            if set(self.masas) != nombres:
                raise ValueError("faltan masas de mercados del marcador")
            for nombre, ley in self.masas.items():
                cdf = np.cumsum(ley.pmf)
                idx = np.searchsorted(cdf, .005 * np.arange(1, 200) - 1e-12)
                cuantiles = np.asarray(ley.soporte)[np.minimum(idx, len(ley.soporte) - 1)]
                if not np.allclose(cuantiles, getattr(self, nombre), atol=1e-9, rtol=0):
                    raise ValueError("cuantiles incompatibles con la masa del marcador")
            margen = self.masas["margen"]
            p_local = sum(p for x, p in zip(margen.soporte, margen.pmf) if x > 0)
            if abs(p_local - self.p_local) > 1e-6:
                raise ValueError("ganador incompatible con la masa del margen")
            medias = {n: sum(x*p for x,p in zip(ley.soporte, ley.pmf)) for n,ley in self.masas.items()}
            esperadas = {'puntos_local':self.mu[0], 'puntos_visitante':self.mu[1],
                         'total':sum(self.mu), 'margen':self.mu[0]-self.mu[1]}
            if any(abs(medias[n]-esperadas[n]) > 1e-3 for n in medias):
                raise ValueError('las medias contradicen las masas del marcador')
        return self


class DistribucionJugador(Contrato):
    pmf: list[float] = Field(min_length=6, max_length=4097)
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
        masa = sum(self.pmf)
        media = sum(k * p for k, p in enumerate(self.pmf)) / masa
        # Compatibilidad explícita con los sellos antiguos que redondeaban cada probabilidad a seis decimales.
        redondeada = all(abs(x-round(x,6)) <= 1e-12 for x in self.pmf)
        error_redondeo_antiguo = 5e-7 * len(self.pmf) * (len(self.pmf) - 1) / 2 if redondeada else 0.
        if abs(media - self.media) > max(1e-4, error_redondeo_antiguo):
            raise ValueError("la media contradice la PMF")
        for q, valor in ((.1, self.p10), (.5, self.p50), (.9, self.p90)):
            antes = sum(self.pmf[:valor]) / masa
            hasta = antes + self.pmf[valor] / masa
            if antes > q + TOLERANCIA_SUMA or hasta < q - TOLERANCIA_SUMA:
                raise ValueError("los cuantiles contradicen la PMF")
        return self


class SalidaMonteCarlo(Contrato):
    partido_id: int = Field(gt=0)
    corte: Instante
    version_datos: Hash256
    version_modelo: str = Field(min_length=3)
    n_simulaciones: int = Field(ge=1_000)
    equipo: DistribucionEquipo
    jugadores: dict[str, DistribucionJugador]            # clave «jugador_id:estadistica»
