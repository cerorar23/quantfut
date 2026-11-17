"""Capa de edad (17-nov-2026): segunda etapa sobre π del filtro congelado.

    logit π' = b · logit π + β · z,    z = (edad_1 − edad_2) / escala

- Sin intercepto: los lados están en orden pseudoaleatorio, así que π'(A, B) + π'(B, A) = 1 por construcción.
- Edad desconocida (cualquiera de los dos jugadores, o fuera de [14, 50] años) ⇒ z = 0: solo actúa la pendiente b.
  Medido en el walk-forward 2019-24: sin edad conocida la capa cambia el log-loss en 0,0000.
- `b` absorbe la recalibración de pendiente que ya existía (`recalibracion.py`); esta capa la REEMPLAZA, no se apila.
- Se ajusta SOLO con temporadas anteriores a la evaluada (`por_temporada`) y se congela para producción con
  `ajustar` sobre todo el histórico liquidado. No toca el filtro, el simulador ni los triggers de la base de datos.
- `β` no tiene signo impuesto: lo estima la verosimilitud (en los datos sale negativo: el jugador más joven rinde
  por encima de lo que su rating anticipa).
"""
import math
from dataclasses import asdict, dataclass

import numpy as np

from .recalibracion import logit

EDAD_MIN, EDAD_MAX = 14.0, 50.0     # fuera de este rango la fecha de nacimiento se trata como desconocida
DIF_MAX = 20.0                      # |edad_1 − edad_2| se recorta aquí (casos raros; el ajuste ya lo incluye)
MIN_FILAS = 2000                    # menos partidos liquidados que esto no sostienen el ajuste
ITERACIONES = 50


@dataclass(frozen=True)
class CapaEdad:
    pendiente: float      # b: pendiente sobre logit π
    beta: float           # β: efecto por desviación estándar de la diferencia de edad (en logit)
    escala: float         # desviación estándar de la diferencia de edad en la muestra de ajuste (años)
    n: int                # partidos liquidados del ajuste
    desde: int            # primera y última temporada del ajuste
    hasta: int

    def __post_init__(self):
        if not all(math.isfinite(x) for x in (self.pendiente, self.beta, self.escala)):
            raise ValueError("la capa de edad exige coeficientes finitos")
        if not (0.0 < self.pendiente <= 3.0):
            raise ValueError("pendiente b fuera de (0, 3]")
        if abs(self.beta) > 2.0:
            raise ValueError("|β| > 2: el ajuste no es creíble")
        if not self.escala > 0.0:
            raise ValueError("escala de la edad debe ser > 0")

    def como_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def desde_dict(cls, d: dict) -> "CapaEdad":
        return cls(**{k: d[k] for k in ("pendiente", "beta", "escala", "n", "desde", "hasta")})


def diferencia_edad(edad_1, edad_2):
    """edad_1 − edad_2 recortada a ±DIF_MAX; NaN si falta alguna o está fuera de [EDAD_MIN, EDAD_MAX]."""
    a, b = np.asarray(edad_1, dtype=float), np.asarray(edad_2, dtype=float)
    ok = (np.isfinite(a) & np.isfinite(b) & (a >= EDAD_MIN) & (a <= EDAD_MAX) & (b >= EDAD_MIN) & (b <= EDAD_MAX))
    return np.where(ok, np.clip(a - b, -DIF_MAX, DIF_MAX), np.nan)


def _z(dedad, escala: float) -> np.ndarray:
    return np.nan_to_num(np.asarray(dedad, dtype=float), nan=0.0) / escala


def _newton(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Máxima verosimilitud de y ~ Bernoulli(expit(X·c)); c arranca en (1, 0)."""
    c = np.array([1.0, 0.0])
    for _ in range(ITERACIONES):
        q = 1 / (1 + np.exp(-(x @ c)))
        w = q * (1 - q)
        g = x.T @ (y - q)
        h = (x * w[:, None]).T @ x + 1e-9 * np.eye(2)
        paso = np.linalg.solve(h, g)
        c = c + paso
        if np.max(np.abs(paso)) < 1e-10:
            break
    return c


def ajustar(pi, dedad, y, desde: int = 0, hasta: int = 0) -> CapaEdad:
    """Ajusta (b, β) con los partidos dados. `y` ∈ {0, 1}; `dedad` con NaN donde no se conoce."""
    pi, dedad, y = (np.asarray(v, dtype=float) for v in (pi, dedad, y))
    ok = np.isfinite(pi) & ((y == 0) | (y == 1)) & (pi > 0) & (pi < 1)
    if int(ok.sum()) < MIN_FILAS:
        raise ValueError(f"capa de edad: {int(ok.sum())} partidos liquidados (mínimo {MIN_FILAS})")
    conocida = ok & np.isfinite(dedad)
    escala = float(np.std(dedad[conocida])) if conocida.sum() > 1 else 0.0
    if not escala > 0.0:
        raise ValueError("capa de edad: sin diferencias de edad conocidas en la muestra de ajuste")
    x = np.column_stack([logit(pi[ok]), _z(dedad[ok], escala)])
    c = _newton(x, y[ok])
    return CapaEdad(pendiente=float(c[0]), beta=float(c[1]), escala=escala, n=int(ok.sum()), desde=int(desde),
                    hasta=int(hasta))


def aplicar(pi, dedad, capa: CapaEdad):
    """π' con la capa. Conserva NaN de π; edad desconocida ⇒ z = 0."""
    pi = np.asarray(pi, dtype=float)
    z = capa.pendiente * logit(np.where(np.isfinite(pi), pi, 0.5)) + capa.beta * _z(dedad, capa.escala)
    return np.where(np.isfinite(pi), 1 / (1 + np.exp(-z)), np.nan)


def por_temporada(temporada, pi, dedad, y, liquida, evaluar, desde: int):
    """Para cada temporada T evaluada: capa ajustada con las temporadas desde..T−1 (liquidadas) y aplicada a T.

    Devuelve (π', {T: CapaEdad | None}). Con menos de MIN_FILAS antes de T no se ajusta: π' = NaN para esa temporada.
    """
    temporada, pi, dedad, y, liquida = (np.asarray(v) for v in (temporada, pi, dedad, y, liquida))
    out, capas = np.full(len(pi), np.nan), {}
    for t in evaluar:
        tr = liquida.astype(bool) & (temporada >= desde) & (temporada < t) & np.isfinite(pi.astype(float))
        try:
            capa = ajustar(pi[tr], dedad[tr], y[tr], desde, int(t) - 1)
        except ValueError:
            capas[int(t)] = None
            continue
        sel = temporada == t
        out[sel] = aplicar(pi[sel], dedad[sel], capa)
        capas[int(t)] = capa
    return out, capas
