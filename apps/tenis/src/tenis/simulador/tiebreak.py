"""Tiebreak a K puntos (K = 7 o 10) con alternancia ABBA (plan G.2; lit. C.i: A31 ecs. 11-16, T32 Prop. 3.2-3.5).

Saca el primer punto `primero`, luego dos puntos cada uno: el punto n (desde 0) lo saca `primero` si ⌊(n+1)/2⌋ es par.
Programación dinámica exacta hasta (K−1, K−1); desde ahí cada ronda de dos puntos tiene un saque de cada uno:
A gana las dos con w_A = p_A·q_B, B con w_B = q_A·p_B, y se vuelve a igualar con r = 1 − w_A − w_B.
Cola cerrada: P(A gana desde iguales) = w_A/(w_A + w_B); w_A + w_B > 0 para todo p ∈ (0, 1).
"""
from dataclasses import dataclass

import numpy as np

from ._comun import salida, validar_lado, validar_p

OBJETIVOS = (7, 10)


def _validar_objetivo(objetivo: int) -> int:
    if objetivo not in OBJETIVOS or isinstance(objetivo, bool):
        raise ValueError(f"tiebreak a {objetivo!r} puntos no soportado (solo 7 y 10)")
    return objetivo


def _saca_primero(n: int) -> bool:
    return ((n + 1) // 2) % 2 == 0


def _tabla(p_a: np.ndarray, p_b: np.ndarray, k: int, primero_a: bool):
    """Masa de cada final (K, j) y (j, K) con j ≤ K−2, y masa que llega a (K−1, K−1). Vectorizado."""
    vivos = {(0, 0): np.ones_like(p_a)}
    fin_a, fin_b = {}, {}
    for n in range(2 * k - 2):
        saca_a = _saca_primero(n) == primero_a
        wa = p_a if saca_a else 1.0 - p_b
        for i in range(max(0, n - (k - 1)), min(n, k - 1) + 1):
            m = vivos.pop((i, n - i), None)
            if m is None:
                continue
            j = n - i
            for (x, y), masa, fin, clave in (((i + 1, j), m * wa, fin_a, j), ((i, j + 1), m * (1.0 - wa), fin_b, i)):
                if max(x, y) == k:
                    fin[clave] = fin.get(clave, 0.0) + masa
                else:
                    vivos[(x, y)] = vivos.get((x, y), 0.0) + masa
    return fin_a, fin_b, vivos[(k - 1, k - 1)]


def _ganar_ambos(p_a: np.ndarray, p_b: np.ndarray, k: int, primero_a: bool) -> tuple[np.ndarray, np.ndarray]:
    """(P(A gana), P(B gana)) de una sola PD, cada una sumada por su lado (sin 1 − x: exacto también en extremos)."""
    fin_a, fin_b, iguales = _tabla(p_a, p_b, k, primero_a)
    wa, wb = p_a * (1.0 - p_b), (1.0 - p_a) * p_b
    return sum(fin_a.values()) + iguales * wa / (wa + wb), sum(fin_b.values()) + iguales * wb / (wa + wb)


def _ganar(p_a: np.ndarray, p_b: np.ndarray, k: int, primero_a: bool) -> np.ndarray:
    return _ganar_ambos(p_a, p_b, k, primero_a)[0]


def ganar_tiebreak(p_a, p_b, objetivo: int, saca_primero: str):
    """P(A gana el tiebreak). Por neutralidad (A31 §3.3) no depende de quién saca primero; se calcula igual."""
    k = _validar_objetivo(objetivo)
    primero_a = validar_lado(saca_primero)
    return salida(_ganar(validar_p(p_a, "p_a"), validar_p(p_b, "p_b"), k, primero_a))


@dataclass(frozen=True)
class DistTiebreak:
    """Marcador de puntos (A, B) → probabilidad, con las `rondas` primeras rondas tras (K−1, K−1) explícitas;
    la cola restante va en cola_a/cola_b (forma cerrada). puntos + colas suman 1."""
    puntos: dict
    cola_a: float
    cola_b: float

    @property
    def gana_a(self) -> float:
        return sum(v for (a, b), v in self.puntos.items() if a > b) + self.cola_a


def distribucion_tiebreak(p_a, p_b, objetivo: int, saca_primero: str, rondas: int = 60) -> DistTiebreak:
    k = _validar_objetivo(objetivo)
    pa, pb = float(validar_p(p_a, "p_a")), float(validar_p(p_b, "p_b"))
    fin_a, fin_b, iguales = _tabla(np.asarray(pa), np.asarray(pb), k, validar_lado(saca_primero))
    d = {(k, j): float(v) for j, v in fin_a.items()} | {(j, k): float(v) for j, v in fin_b.items()}
    wa, wb = pa * (1.0 - pb), (1.0 - pa) * pb
    r, iguales = 1.0 - wa - wb, float(iguales)
    for m in range(rondas):
        d[(k + 1 + m, k - 1 + m)] = iguales * r**m * wa
        d[(k - 1 + m, k + 1 + m)] = iguales * r**m * wb
    resto = iguales * r**rondas
    return DistTiebreak(d, resto * wa / (wa + wb), resto * wb / (wa + wb))


def puntos_media_var(p_a, p_b, objetivo: int, saca_primero: str) -> tuple[float, float]:
    """Media y varianza exactas del número de puntos del tiebreak (T32 Teor. 3.5)."""
    k = _validar_objetivo(objetivo)
    pa, pb = float(validar_p(p_a, "p_a")), float(validar_p(p_b, "p_b"))
    fin_a, fin_b, iguales = _tabla(np.asarray(pa), np.asarray(pb), k, validar_lado(saca_primero))
    e1 = sum(float(v) * (k + j) for j, v in fin_a.items()) + sum(float(v) * (k + j) for j, v in fin_b.items())
    e2 = sum(float(v) * (k + j) ** 2 for j, v in fin_a.items()) + sum(float(v) * (k + j) ** 2 for j, v in fin_b.items())
    s = pa * (1.0 - pb) + (1.0 - pa) * pb            # R ~ Geométrica(s) rondas, puntos = 2K − 2 + 2R
    er, vr = 1.0 / s, (1.0 - s) / (s * s)
    e_ig = 2 * k - 2 + 2 * er
    media = e1 + float(iguales) * e_ig
    return salida(media), salida(e2 + float(iguales) * (4 * vr + e_ig * e_ig) - media * media)
