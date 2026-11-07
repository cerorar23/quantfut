"""Juego al saque en forma cerrada (plan G.2; lit. C.i: A31 ec. 5, A26, T32 Teor. 2.3-2.5).

p = probabilidad de que el SACADOR gane un punto, q = 1 − p. El deuce se resuelve exactamente:
desde iguales cada ronda de dos puntos la gana el sacador con p², el restador con q² y vuelve a iguales
con 2pq, así que P(gana desde iguales) = p² / (p² + q²); el denominador vale ≥ 1/2 para todo p.
Todo acepta escalares o arrays de numpy (vectorizado sobre nodos de cuadratura).
"""
from dataclasses import dataclass

import numpy as np

from ._comun import salida, validar_p


def ganar_desde_iguales(p):
    p = validar_p(p)
    q = 1.0 - p
    return salida(p * p / (p * p + q * q))


def ganar_juego(p):
    """g(p) = p⁴(1 + 4q + 10q²) + 20p³q³ · p²/(p² + q²)   (1 − 2pq = p² + q²)."""
    p = validar_p(p)
    q = 1.0 - p
    return salida(p**4 * (1.0 + 4.0 * q + 10.0 * q * q) + 20.0 * p**3 * q**3 * p * p / (p * p + q * q))


def romper_saque(p):
    """1 − g(p) calculado como g(q) (el juego es simétrico entre sacador y restador): sin cancelación cerca de p = 1."""
    p = validar_p(p)
    return ganar_juego(1.0 - p)


def ganar_juego_sin_ventaja(p):
    """Juego con punto decisivo en 3-3 (A26 ec. 2): g* = p⁴(−20p³ + 70p² − 84p + 35)."""
    p = validar_p(p)
    return salida(p**4 * (-20.0 * p**3 + 70.0 * p * p - 84.0 * p + 35.0))


def puntos_media_var(p) -> tuple[float, float]:
    """Media y varianza exactas del número de puntos del juego (T32 Teor. 2.5)."""
    p = float(validar_p(p))
    q = 1.0 - p
    fin = {4: p**4 + q**4, 5: 4 * (p**4 * q + q**4 * p), 6: 10 * (p**4 * q * q + q**4 * p * p)}
    iguales = 20.0 * p**3 * q**3
    e1 = sum(n * m for n, m in fin.items())
    e2 = sum(n * n * m for n, m in fin.items())
    s = p * p + q * q                      # P(ronda decisiva); R ~ Geométrica(s), puntos = 6 + 2R
    er, vr = 1.0 / s, (1.0 - s) / (s * s)
    e_ig = 6.0 + 2.0 * er
    e2_ig = 4.0 * vr + e_ig * e_ig
    media = e1 + iguales * e_ig
    return salida(media), salida(e2 + iguales * e2_ig - media * media)


@dataclass(frozen=True)
class DistJuego:
    """Marcador final de puntos (sacador, restador) → probabilidad; la cola del deuce más allá de `rondas` rondas se
    declara aparte (cola_sacador + cola_restador) en forma cerrada: nada se trunca en silencio."""
    puntos: dict
    cola_sacador: float
    cola_restador: float


def distribucion_juego(p, rondas: int = 60) -> DistJuego:
    p = float(validar_p(p))
    q = 1.0 - p
    if rondas < 0:
        raise ValueError("rondas debe ser ≥ 0")
    d = {(4, 0): p**4, (4, 1): 4 * p**4 * q, (4, 2): 10 * p**4 * q * q,
         (0, 4): q**4, (1, 4): 4 * q**4 * p, (2, 4): 10 * q**4 * p * p}
    iguales, r = 20.0 * p**3 * q**3, 2.0 * p * q
    for m in range(rondas):
        d[(5 + m, 3 + m)] = iguales * r**m * p * p
        d[(3 + m, 5 + m)] = iguales * r**m * q * q
    resto = iguales * r**rondas
    return DistJuego(d, resto * p * p / (p * p + q * q), resto * q * q / (p * p + q * q))
