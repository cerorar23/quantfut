"""Distribución exacta del marcador de un set (plan G.2; lit. C.i: A31 ecs. 6-10, T32 Teor. 3.6).

Reglas de set: 'tiebreak_7' (normal), 'tiebreak_10' (decisivo de Grand Slam), 'ventaja' (sin tiebreak: desde 6-6
gana quien saque dos juegos de diferencia) y 'super_tiebreak_10' (el set ES un tiebreak a 10; marcador 1-0).
El primer sacador σ saca los juegos impares (1.º, 3.º, …) y el primer punto del tiebreak (juego 13).
Sacador del set siguiente (plan G.2): σ si el set tuvo un número par de juegos (tiebreak = 1 juego), ¬σ si impar.

Set de ventaja: desde 6-6 cada ronda de dos juegos (uno al saque de cada uno) la gana A con h_A·b_A, B con
(1−h_A)(1−b_A) y vuelve a igualar con r. Se enumeran los marcadores hasta `max_juegos` juegos del ganador
(50 = límite de `contratos.marcador.SetMarcador`); la masa restante NO se descarta: va a dos pseudo-marcadores de
cola (gana A / gana B, forma cerrada) con su número esperado de juegos. Error de truncar = 0 en P(gana); la cola
solo indica qué parte de la masa no tiene marcador exacto representable.
"""
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from ._comun import salida, validar_lado, validar_p
from .juego import ganar_juego
from .tiebreak import _ganar_ambos

REGLAS_SET = ("tiebreak_7", "tiebreak_10", "ventaja", "super_tiebreak_10")
MAX_JUEGOS_CONTRATO = 50


@dataclass(frozen=True)
class Catalogo:
    """Resultados posibles de un set, en orden fijo. juegos es float porque la cola lleva su media."""
    ga: np.ndarray
    gb: np.ndarray
    tb: np.ndarray        # bool: hubo tiebreak
    gana_a: np.ndarray    # bool
    juegos: np.ndarray    # float: ga + gb (tiebreak = 1 juego más en ga+gb, ya incluido en 7-6)
    paridad: np.ndarray   # int: 1 si cambia el sacador del set siguiente
    cola: np.ndarray      # bool: pseudo-marcador de cola del set de ventaja

    def __len__(self) -> int:
        return len(self.ga)


@lru_cache(maxsize=None)
def catalogo(regla: str, max_juegos: int = MAX_JUEGOS_CONTRATO) -> Catalogo:
    validar_regla_set(regla)
    if regla == "super_tiebreak_10":
        filas = [(1, 0, True), (0, 1, True)]
    else:
        base = [(6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (7, 5)]
        if regla == "ventaja":
            if max_juegos < 8:
                raise ValueError("max_juegos del set de ventaja debe ser ≥ 8")
            base += [(8 + j, 6 + j) for j in range(max_juegos - 7)]
            filas = [(a, b, False) for a, b in base] + [(b, a, False) for a, b in base]
        else:
            filas = [(a, b, False) for a, b in base] + [(7, 6, True)]
            filas += [(b, a, t) for a, b, t in filas]
    ga = np.array([f[0] for f in filas] + ([-1, -1] if regla == "ventaja" else []))
    gb = np.array([f[1] for f in filas] + ([-1, -1] if regla == "ventaja" else []))
    cola = np.array([False] * len(filas) + ([True, True] if regla == "ventaja" else []))
    tb = np.array([f[2] for f in filas] + ([False, False] if regla == "ventaja" else []))
    gana_a = np.where(cola, np.arange(len(ga)) == len(ga) - 2, ga > gb)
    juegos = np.where(cola, np.nan, (ga + gb).astype(float))
    paridad = np.where(cola, 0, (ga + gb) % 2)
    return Catalogo(ga, gb, tb, gana_a, juegos, paridad.astype(int), cola)


def validar_regla_set(regla: str) -> str:
    if regla not in REGLAS_SET:
        raise ValueError(f"regla de set «{regla}» desconocida: {REGLAS_SET}")
    return regla


def probs_set(p_a: np.ndarray, p_b: np.ndarray, regla: str, max_juegos: int = MAX_JUEGOS_CONTRATO,
              sigmas: tuple = (0, 1)):
    """Tabla T[n, σ, o] (σ = 0 si saca A primero) y medias de juegos de la cola. Vectorizado sobre n nodos.

    Los juegos al saque se calculan UNA vez por nodo y se reutilizan para ambos σ; `sigmas=(0,)` deja σ = B en
    cero (lo usa P(ganar), que por neutralidad solo necesita uno)."""
    cat = catalogo(regla, max_juegos)
    p_a, p_b = np.atleast_1d(p_a), np.atleast_1d(p_b)
    n = len(p_a)
    t = np.zeros((n, 2, len(cat)))
    juegos_cola = np.zeros((n, 2))
    if regla == "super_tiebreak_10":
        for s in sigmas:
            t[:, s, 0], t[:, s, 1] = _ganar_ambos(p_a, p_b, 10, s == 0)
        return cat, t, juegos_cola
    # A mantiene / A rompe, y sus complementos calculados SIN restar (1 − g(p) = g(1 − p)): sin cancelación con
    # p cerca de 0 o 1, que rompería en el 1e-11 la simetría exacta del set de ventaja.
    h_a, no_h_a = np.atleast_1d(ganar_juego(p_a)), np.atleast_1d(ganar_juego(1.0 - p_a))
    b_a, no_b_a = np.atleast_1d(ganar_juego(1.0 - p_b)), np.atleast_1d(ganar_juego(p_b))
    idx = {(int(a), int(b)): i for i, (a, b, c) in enumerate(zip(cat.ga, cat.gb, cat.cola)) if not c}
    for s in sigmas:
        vivos = {(0, 0): np.ones(n)}
        for juego in range(12):
            saca_a = (juego % 2 == 0) == (s == 0)
            wa, wb = (h_a, no_h_a) if saca_a else (b_a, no_b_a)
            for x in range(max(0, juego - 6), min(juego, 6) + 1):
                m = vivos.pop((x, juego - x), None)
                if m is None:
                    continue
                for (nx, ny), masa in (((x + 1, juego - x), m * wa), ((x, juego - x + 1), m * wb)):
                    hi, lo = max(nx, ny), min(nx, ny)
                    if (hi == 6 and lo <= 4) or hi == 7:
                        t[:, s, idx[(nx, ny)]] += masa
                    else:
                        vivos[(nx, ny)] = vivos.get((nx, ny), 0.0) + masa
        m66 = vivos.pop((6, 6))
        if regla == "ventaja":
            ambos_a, ambos_b = h_a * b_a, no_h_a * no_b_a
            fin = ambos_a + ambos_b
            if np.any(fin <= 0.0):
                raise ValueError("set de ventaja sin fin numérico (p demasiado cerca de 0 o 1)")
            r = h_a * no_b_a + no_h_a * b_a                                  # vuelve a igualar
            ronda = m66.copy()
            for j in range(max_juegos - 7):
                t[:, s, idx[(8 + j, 6 + j)]] = ronda * ambos_a
                t[:, s, idx[(6 + j, 8 + j)]] = ronda * ambos_b
                ronda = ronda * r
            t[:, s, -2], t[:, s, -1] = ronda * ambos_a / fin, ronda * ambos_b / fin
            juegos_cola[:, s] = 12 + 2 * (max_juegos - 7) + 2.0 / fin
        else:
            k = 7 if regla == "tiebreak_7" else 10
            wa_tb, wb_tb = _ganar_ambos(p_a, p_b, k, s == 0)
            t[:, s, idx[(7, 6)]], t[:, s, idx[(6, 7)]] = m66 * wa_tb, m66 * wb_tb
    return cat, t, juegos_cola


@dataclass(frozen=True)
class TablaSet:
    marcadores: tuple          # (juegos_a, juegos_b, tiebreak); la cola de ventaja no tiene marcador
    prob: tuple
    siguiente_saca: tuple      # 'A' / 'B' para cada marcador
    cola_a: float
    cola_b: float

    @property
    def gana_a(self) -> float:
        return sum(p for (a, b, _), p in zip(self.marcadores, self.prob) if a > b) + self.cola_a


def tabla_set(p_a, p_b, saca_primero: str, regla: str, max_juegos: int = MAX_JUEGOS_CONTRATO) -> TablaSet:
    s = 0 if validar_lado(saca_primero) else 1
    validar_regla_set(regla)
    cat, t, _ = probs_set(validar_p(p_a, "p_a"), validar_p(p_b, "p_b"), regla, max_juegos)
    fila = salida(t[0, s])
    marc, prob, sig = [], [], []
    for i in range(len(cat)):
        if cat.cola[i]:
            continue
        marc.append((int(cat.ga[i]), int(cat.gb[i]), bool(cat.tb[i])))
        prob.append(float(fila[i]))
        sig.append("AB"[s ^ int(cat.paridad[i])])
    cola_a, cola_b = (float(fila[-2]), float(fila[-1])) if cat.cola.any() else (0.0, 0.0)
    return TablaSet(tuple(marc), tuple(prob), tuple(sig), cola_a, cola_b)
