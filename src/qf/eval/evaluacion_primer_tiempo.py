"""
Mercados de primera mitad hacia ModelEvaluator (sin cuotas).

Las probabilidades salen de `model.primer_tiempo.probs` con las intensidades del partido que
da el modelo ANTES de jugarse (las `lam` y `mu` de un walk-forward fuera de muestra). Mercados:
gol en 1T, ambos anotan en 1T, más de 1,5 goles en 1T (binarios) y ganador del 1T (excluyente),
más filas de RMSE con los goles esperados y reales de la mitad.

La proporción de goles de la 1ª mitad se ajustó con datos de 2019-2022: mide desde sep-2022.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.model.primer_tiempo import PROPORCION_1T, probs

MERCADOS_EXCLUYENTES_1T = frozenset({"ganador_1t"})


def filas_primer_tiempo(evento, lam: float, mu: float, goles_local: int,
                        goles_visitante: int) -> list[dict]:
    p = probs(lam, mu)
    gl, gv = int(goles_local), int(goles_visitante)
    filas: list[dict] = []

    def add(mercado, seleccion, prob, ocurrio):
        filas.append({"evento": evento, "mercado": mercado, "seleccion": seleccion,
                      "prob": prob, "resultado": float(ocurrio),
                      "esperado": np.nan, "real": np.nan})

    add("gol_1t_si", "si", p["gol_1t_si"], gl + gv > 0)
    add("ambos_1t_si", "si", p["ambos_1t_si"], gl > 0 and gv > 0)
    add("mas_1_5_1t", "si", p["mas_1_5_1t"], gl + gv > 1)
    real = "local" if gl > gv else "visita" if gv > gl else "empate"
    for sel, clave in (("local", "ganador_1t_local"), ("empate", "ganador_1t_empate"),
                       ("visita", "ganador_1t_visita")):
        add("ganador_1t", sel, p[clave], sel == real)

    el, ev = PROPORCION_1T[0] * lam, PROPORCION_1T[1] * mu
    for nombre, esperado, valor in (("goles_1t_total", el + ev, gl + gv),
                                    ("goles_1t_local", el, gl),
                                    ("goles_1t_visitante", ev, gv)):
        filas.append({"evento": evento, "mercado": nombre, "seleccion": None,
                      "prob": np.nan, "resultado": np.nan,
                      "esperado": esperado, "real": float(valor)})
    return filas


def tabla_primer_tiempo(partidos: pd.DataFrame) -> pd.DataFrame:
    """partidos: evento, lam, mu, goles_1t_local, goles_1t_visitante (NaN = sin marcador de 1T)."""
    filas: list[dict] = []
    sin_dato = 0
    for r in partidos.itertuples(index=False):
        if pd.isna(r.goles_1t_local) or pd.isna(r.goles_1t_visitante):
            sin_dato += 1
            continue
        filas.extend(filas_primer_tiempo(r.evento, r.lam, r.mu,
                                         r.goles_1t_local, r.goles_1t_visitante))
    out = pd.DataFrame(filas, columns=["evento", "mercado", "seleccion", "prob",
                                       "resultado", "esperado", "real"])
    out.attrs["cobertura"] = {"partidos": len(partidos), "sin_dato": sin_dato}
    return out
