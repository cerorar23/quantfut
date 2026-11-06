"""Mundo sintético con el esquema de la exportación PIT (solo para pruebas): partidos + eventos de resultado.

Cada semana se emparejan jugadores al azar; corte = lunes + 1 s, resultado visible 2 días después (como el calendario
retro). Fuerza verdadera fija por jugador; ranking = orden de la fuerza. Todo determinista con la semilla.
"""
from dataclasses import replace
from functools import lru_cache

import numpy as np
import pandas as pd

from .datos import COL_E, COL_P, COL_Y
from .parametros import Psi

INICIO = pd.Timestamp("2010-01-04", tz="UTC")
LBAR, SIGMA_EPS, RHO_EPS = 0.55, 0.22, -0.45


@lru_cache(maxsize=None)
def tablas_prueba() -> dict:
    """Tablas de M̄_f con ℓ̄ = 0,55 en las 4 superficies y la forma del día de A26 (H). Se construyen una vez."""
    from .tabla import construir_todas
    return construir_todas((LBAR,) * 4, SIGMA_EPS, RHO_EPS)


def psi_prueba(**cambios) -> Psi:
    base = Psi(tau_theta=0.1, tau_inact=0.1, sigma_theta0=0.15, b_rank=-0.05, kappa=(1.1, 0.9, 1.0, 1.05), sigma_d=0.05,
               tau_d=0.02, r_omega=0.3, phi=(0.02, 0.05), gamma=(0.1, 0.0, 0.0), lam=0.75, f90=200.0,
               sigma_eps=SIGMA_EPS, rho_eps=RHO_EPS, lbar=(LBAR,) * 4)
    return replace(base, **cambios)


def mundo(n_jugadores: int = 24, n_semanas: int = 30, semilla: int = 0, circuito: str = "atp",
          superficies=("Hard", "Clay", "Grass", "Indoor")) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(semilla)
    ids = rng.permutation(np.arange(1000, 1000 + 7 * n_jugadores, 7))      # ids arbitrarios (claves)
    fuerza = rng.normal(0, 0.15, n_jugadores)
    rango = np.empty(n_jugadores); rango[np.argsort(-fuerza)] = np.arange(1, n_jugadores + 1)
    filas, n_prev = [], np.zeros(n_jugadores, int)
    for w in range(n_semanas):
        lunes = INICIO + pd.Timedelta(weeks=w)
        orden = rng.permutation(n_jugadores)
        sup = superficies[w % len(superficies)]
        for k in range(0, n_jugadores - 1, 2):
            a, b = orden[k], orden[k + 1]
            pa = 1 / (1 + np.exp(-4 * (fuerza[a] - fuerza[b])))
            gan = 1 if rng.random() < pa else 2
            minutos = float(rng.integers(60, 200))
            filas.append({"partido_key": f"X{w:03d}_{k:03d}", "circuito": circuito, "temporada": lunes.year,
                          "categoria": "250", "ronda": "R32", "superficie": sup, "mejor_de": 3,
                          "formato_decisivo": "tiebreak_7", "por_equipos": False, "jjoo": False,
                          "semana_previa_gs": False, "jugador_1": int(ids[a]), "jugador_2": int(ids[b]),
                          "rank_1": float(rango[a]), "rank_2": float(rango[b]), "n_prev_1": int(n_prev[a]),
                          "n_prev_2": int(n_prev[b]), "corte_utc": lunes + pd.Timedelta(seconds=1), "excluir_motivo": None,
                          "y_estado": "completado", "y_ganador": gan, "y_sets_completos": 2,
                          "estado": "completado", "ganador": gan, "minutos_1": minutos, "minutos_2": minutos,
                          "actualiza_rating": True, "visible_resultado_utc": lunes + pd.Timedelta(days=2)})
            n_prev[a] += 1; n_prev[b] += 1
    df = pd.DataFrame(filas)
    return df[list(dict.fromkeys(COL_P + COL_Y))].copy(), df[COL_E].copy()
