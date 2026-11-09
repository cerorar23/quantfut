"""
Aplanado y liquidación de los mercados que dependen solo del marcador final.

Convierte `pricing.price_all_markets` + el marcador real en el DataFrame largo que
espera `ModelEvaluator` (sin cuotas: solo probabilidad predicha y resultado). Cada línea es
su propio mercado ("over_2.5", "ah_-0.25") para ver la calibración línea por línea.

Convenciones:
- Binarios: se emite una sola cara (over, sí, local) porque la otra es el complemento y
  duplicaría el peso del mercado.
- Excluyentes (`MERCADOS_EXCLUYENTES`): 1x2, marcador_exacto (top 12 + «otro» para que sume 1)
  y margen_victoria.
- Hándicap asiático: prob = la efectiva del motor (`home`, ya condicionada a no devolución);
  resultado = parte ganada / parte no devuelta, que en líneas de cuarto sigue siendo 0 o 1.
  Si todo el stake se devuelve (push completo) resultado = NaN y la fila no puntúa.
- Goles totales/local/visitante: fila sin probabilidad con `esperado` y `real` para el RMSE.
Córners, tarjetas y primera mitad no están aquí: necesitan datos reales distintos al marcador.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from qf.model.pricing import AH_LINES, price_all_markets

MERCADOS_EXCLUYENTES = frozenset({"1x2", "marcador_exacto", "margen_victoria"})
_EPS = 1e-9


def _ah_resultado(diff: int, line: float) -> float:
    """Resultado efectivo del local: ganado / (1 - devuelto). NaN si se devuelve todo."""
    cuarto = abs(line * 2 - round(line * 2)) > _EPS
    patas = [line - 0.25, line + 0.25] if cuarto else [line]
    ganado = sum(1.0 for p in patas if diff + p > _EPS) / len(patas)
    devuelto = sum(1.0 for p in patas if abs(diff + p) < _EPS) / len(patas)
    if 1.0 - devuelto < _EPS:
        return float("nan")
    return ganado / (1.0 - devuelto)


def _clave_margen(d: int) -> str:
    if d == 0:
        return "draw"
    lado, k = ("home", d) if d > 0 else ("away", -d)
    return f"{lado}_by_4plus" if k >= 4 else f"{lado}_by_{k}"


def filas_goles(evento, lam: float, mu: float, rho: float,
                goles_local: int, goles_visitante: int) -> list[dict]:
    mk = price_all_markets(lam, mu, rho)
    gh, ga = int(goles_local), int(goles_visitante)
    if gh < 0 or ga < 0:
        raise ValueError(f"Goles negativos: {gh}-{ga}")
    diff, total = gh - ga, gh + ga
    filas: list[dict] = []

    def add(mercado, seleccion, prob, ocurrio):
        filas.append({"evento": evento, "mercado": mercado, "seleccion": seleccion,
                      "prob": prob, "resultado": float(ocurrio)})

    real_1x2 = "home" if diff > 0 else "away" if diff < 0 else "draw"
    for sel, p in mk["1x2"].items():
        add("1x2", sel, p, sel == real_1x2)

    ocurre_dc = {"1X": diff >= 0, "12": diff != 0, "X2": diff <= 0}
    for sel, p in mk["double_chance"].items():
        add("doble_oportunidad", sel, p, ocurre_dc[sel])

    add("btts", "yes", mk["btts"]["yes"], gh > 0 and ga > 0)

    for ln, d in mk["totals"].items():
        add(f"over_{ln}", "over", d["over"], total > float(ln))
    for lado, goles in (("home", gh), ("away", ga)):
        nombre = "local" if lado == "home" else "visitante"
        for ln, d in mk["team_totals"][lado].items():
            add(f"{nombre}_over_{ln}", "over", d["over"], goles > float(ln))

    for ln in AH_LINES:
        p = mk["asian_handicap"][f"{ln:+.2f}"]["home"]
        r = _ah_resultado(diff, ln)
        filas.append({"evento": evento, "mercado": f"ah_{ln}", "seleccion": "home",
                      "prob": p, "resultado": r})

    marcador = f"{gh}-{ga}"
    top = mk["correct_score"]
    for s in top:
        add("marcador_exacto", s["score"], s["prob"], s["score"] == marcador)
    en_top = any(s["score"] == marcador for s in top)
    add("marcador_exacto", "otro", 1.0 - sum(s["prob"] for s in top), not en_top)

    real_margen = _clave_margen(diff)
    for sel, p in mk["winning_margin"].items():
        add("margen_victoria", sel, p, sel == real_margen)

    lam_tot = mk["expected_goals"]
    for mercado, esperado, real in (("goles_total", lam_tot["total"], total),
                                    ("goles_local", lam_tot["home"], gh),
                                    ("goles_visitante", lam_tot["away"], ga)):
        filas.append({"evento": evento, "mercado": mercado, "seleccion": None,
                      "prob": np.nan, "resultado": np.nan,
                      "esperado": esperado, "real": float(real)})
    return filas


def tabla_goles(partidos: pd.DataFrame) -> pd.DataFrame:
    """
    partidos: evento, lam, mu, rho, goles_local, goles_visitante (una fila por partido).
    Devuelve el DataFrame largo listo para ModelEvaluator(mercados_excluyentes=MERCADOS_EXCLUYENTES).
    """
    filas: list[dict] = []
    sin_dato = 0
    for r in partidos.itertuples(index=False):
        if pd.isna(r.goles_local) or pd.isna(r.goles_visitante):
            sin_dato += 1
            continue
        filas.extend(filas_goles(r.evento, r.lam, r.mu, r.rho,
                                 r.goles_local, r.goles_visitante))
    out = pd.DataFrame(filas, columns=["evento", "mercado", "seleccion", "prob",
                                       "resultado", "esperado", "real"])
    out.attrs["cobertura"] = {"partidos": len(partidos), "sin_dato": sin_dato}
    return out
