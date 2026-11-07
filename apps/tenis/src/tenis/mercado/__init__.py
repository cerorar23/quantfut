"""Mdulo de mercado y cuotas de referencia (Sprint 5, B.4, I.0, I.3).

Precios de referencia de mercado cargados con su recepcin real, enlazados y sin entrar en el modelo.
Evaluacin retrospectiva (ganador, clase b) y prospectiva (todos los mercados).
"""
from .devig import (
    cuota_americana_a_decimal,
    cuota_decimal_a_americana,
    calcular_margen,
    devig_proporcional,
    devig_dos_vias,
)
from .liquidacion import (
    liquidar_ganador,
    liquidar_primer_set,
    liquidar_handicap_sets,
    liquidar_totales_juegos,
    liquidar_handicap_juegos,
    liquidar_tiebreak,
    validar_resultado_propio,
)

__all__ = [
    "cuota_americana_a_decimal",
    "cuota_decimal_a_americana",
    "calcular_margen",
    "devig_proporcional",
    "devig_dos_vias",
    "liquidar_ganador",
    "liquidar_primer_set",
    "liquidar_handicap_sets",
    "liquidar_totales_juegos",
    "liquidar_handicap_juegos",
    "liquidar_tiebreak",
    "validar_resultado_propio",
]
