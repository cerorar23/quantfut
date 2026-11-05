"""Distribución discreta ponderada: la salida común de los modelos de minutos y (más adelante) de props."""
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Distribucion:
    valores: np.ndarray        # ordenados de menor a mayor
    pesos: np.ndarray          # suman 1

    @staticmethod
    def de_muestras(valores: Sequence[float], pesos: Sequence[float] | None = None) -> "Distribucion":
        v = np.asarray(valores, dtype=float)
        if v.ndim != 1 or v.size == 0 or not np.isfinite(v).all():
            raise ValueError("una distribución necesita al menos un valor")
        w = np.ones_like(v) if pesos is None else np.asarray(pesos, dtype=float)
        if w.shape != v.shape or not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
            raise ValueError("pesos inválidos")
        orden = np.argsort(v, kind="stable")
        return Distribucion(v[orden], w[orden] / w.sum())

    def media(self) -> float:
        return float(np.dot(self.valores, self.pesos))

    def cuantil(self, p: float) -> float:
        """Menor valor cuya probabilidad acumulada alcanza p (cuantil inferior de una distribución discreta)."""
        acumulada = np.cumsum(self.pesos)
        i = int(np.searchsorted(acumulada, min(max(p, 0.0), 1.0) - 1e-12))
        return float(self.valores[min(i, self.valores.size - 1)])

    def prob_menos_de(self, x: float) -> float:
        """P(X < x) estricta; la masa en x es una devolución separada."""
        return float(self.pesos[self.valores < x].sum())

    def prob_mas_de(self, x: float) -> float:
        return float(self.pesos[self.valores > x].sum())

    def cuantiles(self, niveles: Sequence[float]) -> np.ndarray:
        """Todos los cuantiles en una pasada; no se vuelve a ordenar ni acumular por nivel."""
        p = np.asarray(niveles, float)
        if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
            raise ValueError("niveles de cuantil inválidos")
        i = np.searchsorted(np.cumsum(self.pesos), np.maximum(p - 1e-12, 0))
        return self.valores[np.minimum(i, len(self.valores) - 1)]

    def pinball(self, y: float, p: float) -> float:
        """Pérdida de cuantil (pinball) del cuantil p frente al valor observado y."""
        q = self.cuantil(p)
        return float(max(p * (y - q), (p - 1) * (y - q)))

    @staticmethod
    def mezcla(partes: Sequence[tuple[float, "Distribucion"]]) -> "Distribucion":
        total = sum(peso for peso, _ in partes)
        if total <= 0:
            raise ValueError("la mezcla necesita peso positivo")
        return Distribucion.de_muestras(np.concatenate([d.valores for _, d in partes]),
                                        np.concatenate([d.pesos * (peso / total) for peso, d in partes]))
