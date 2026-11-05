"""Sensibilidad (plan G.7): derivadas centrales (h = 1e-4) de P(ganar), del 1.er set y de la media de juegos
respecto de p_A y p_B, con o sin la mezcla. «Por 1 pp» = derivada × 0,01: cuánto mueve el mercado un error de
un punto porcentual en la probabilidad de punto al saque."""
from dataclasses import dataclass

from .formato import Formato, validar_formato
from .mezcla import Q_POR_DEFECTO, Incertidumbre, distribucion_mezclada

H = 1e-4


@dataclass(frozen=True)
class Sensibilidad:
    gana_a: float
    d_gana_pa: float
    d_gana_pb: float
    d_primer_set_pa: float
    d_primer_set_pb: float
    media_juegos: float
    d_juegos_pa: float
    d_juegos_pb: float

    def por_punto_porcentual(self) -> dict:
        return {k: 0.01 * getattr(self, k) for k in ("d_gana_pa", "d_gana_pb", "d_primer_set_pa",
                                                     "d_primer_set_pb", "d_juegos_pa", "d_juegos_pb")}


def sensibilidad(p_a: float, p_b: float, formato: Formato, inc: Incertidumbre, q: int = Q_POR_DEFECTO,
                 h: float = H) -> Sensibilidad:
    formato = validar_formato(formato)

    def d(pa, pb):
        return distribucion_mezclada(pa, pb, formato, inc, q)

    c, a1, a0, b1, b0 = d(p_a, p_b), d(p_a + h, p_b), d(p_a - h, p_b), d(p_a, p_b + h), d(p_a, p_b - h)

    def der(f, mas, menos):
        return (f(mas) - f(menos)) / (2 * h)

    gana, ps, jm = (lambda x: x.gana_a), (lambda x: x.primer_set_a_prob), (lambda x: x.media_juegos)
    return Sensibilidad(c.gana_a, der(gana, a1, a0), der(gana, b1, b0), der(ps, a1, a0), der(ps, b1, b0),
                        c.media_juegos, der(jm, a1, a0), der(jm, b1, b0))
