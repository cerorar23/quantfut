"""Simulador analítico del partido de tenis (plan técnico §G, §D.3-D.4).

juego → tiebreak → set_ → partido (conjunta exacta) → mezcla (M̄_f por Gauss–Hermite) → inversion (δ*).
montecarlo solo verifica; sensibilidad mide ∂P/∂p; salida pasa la conjunta al contrato.
"""
from .formato import Formato
from .mezcla import SIN_INCERTIDUMBRE, Incertidumbre, distribucion_mezclada, prob_ganar
from .partido import distribucion_partido

__all__ = ["Formato", "Incertidumbre", "SIN_INCERTIDUMBRE", "distribucion_partido", "distribucion_mezclada",
           "prob_ganar"]
