"""Reloj NBA: distinguir duración de partido de suma de minutos de cinco jugadores."""
import math


def minutos_partido(valor: float | None) -> float | None:
    if valor is None or not math.isfinite(valor) or valor <= 0:
        return None
    duracion = valor / 5 if valor >= 200 else valor
    ot = round((duracion - 48) / 5)
    if ot < 0 or ot > 20 or abs(duracion - (48 + 5 * ot)) > .15:
        return None
    return float(48 + 5 * ot)


def prorrogas(valor: float | None) -> int | None:
    duracion = minutos_partido(valor)
    return None if duracion is None else int(round((duracion - 48) / 5))
