"""Recalibración de la probabilidad de ganar con temporadas ANTERIORES (nunca con la de prueba).

Dos formas, ambas con un solo parámetro ajustable por máxima verosimilitud:
* escala de la media (`ajustar_escala`): P(gana el local) = Φ(k · μ / σ). Es coherente con el resto de mercados porque cambia el MARGEN esperado,
  no solo una probabilidad; si k > 1 el modelo reparte demasiado poco sus ratings.
* logística (`ajustar_logistica`): logit(p') = a + b · logit(p). Solo corrige la probabilidad del ganador y por eso no se puede sellar tal cual
  (rompería la coherencia con la distribución del margen); sirve de referencia de lo alcanzable.
"""
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import norm

from .evaluacion import pendiente_calibracion

EPS = 1e-6


def p_ganador(mu_margen, sigma: float, k: float = 1.0) -> np.ndarray:
    return np.clip(norm.cdf(k * np.asarray(mu_margen, float) / sigma), EPS, 1 - EPS)


def ajustar_escala(mu_margen, sigma: float, y, cotas: tuple[float, float] = (0.5, 3.0)) -> float:
    """k que maximiza la verosimilitud de y (1 = ganó el local) con P = Φ(k·μ/σ)."""
    mu, y = np.asarray(mu_margen, float), np.asarray(y, float)
    if len(y) < 100 or not np.isfinite(mu).all() or sigma <= 0:
        raise ValueError("hacen falta al menos 100 partidos con datos finitos y sigma positiva")

    def menos_loglik(k):
        p = p_ganador(mu, sigma, k)
        return -np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))

    return float(minimize_scalar(menos_loglik, bounds=cotas, method="bounded").x)


def ajustar_logistica(p, y) -> tuple[float, float]:
    """(a, b) de logit(p') = a + b·logit(p) por regresión logística de y sobre logit(p)."""
    pendiente, intercepto = pendiente_calibracion(p, y)
    return intercepto, pendiente


def aplicar_logistica(p, a: float, b: float) -> np.ndarray:
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return 1 / (1 + np.exp(-(a + b * np.log(p / (1 - p)))))
