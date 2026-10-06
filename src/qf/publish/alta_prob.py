"""
Línea de alta probabilidad: un pronóstico por partido con probabilidad real
entre el 80 % y el 95 %.

Es una línea de ACIERTO, no de valor (decisión del usuario, 2026-10-05; diseño
en docs/superpowers/specs/2026-10-05-linea-alta-probabilidad-design.md). Con
las casas de los suscriptores estos resultados no tienen valor esperado
positivo: football-data 2019-2025, favorito ≥ 80 %, ROI −2,4 % y EV al cierre
−2,6 %. Lo que sí se cumple es lo prometido: Pinnacle sin margen está
calibrado (84,6 % previsto, 84,8 % real; doble oportunidad 87,2 / 87,8).

POR QUÉ PINNACLE Y NO EL MODELO
-------------------------------
El modelo no bate al cierre sin margen (README, model-card). Aquí la promesa
es un porcentaje: tiene que salir de la referencia mejor calibrada.

LA REGLA
--------
Candidatos de 1X2, doble oportunidad (suma exacta del 1X2) y goles (desde
los goles esperados que reproducen el 1X2 y la línea de Pinnacle,
`market_anchor.market_lambdas`). Se publica el de MENOR probabilidad dentro
de [PROB_MIN, PROB_MAX]: el más informativo sin bajar del 80 %. El tope evita
obviedades ("menos de 5,5 goles" al 98 %).

Este módulo es la parte pura. La base de datos está en `alta_prob_datos.py`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from ..model.market_anchor import market_lambdas
from ..model.pricing import market_totals, score_matrix

PROB_MIN = 0.80
PROB_MAX = 0.95
MAX_EDAD_PRECIO = timedelta(hours=6)
HORIZONTE = timedelta(hours=36)
# Error absoluto máximo del ajuste de goles sobre las probabilidades de
# entrada. Por encima, el 1X2 y la línea de goles de Pinnacle no caben en la
# misma pareja de lambdas y los goles derivados no serían de fiar.
MAX_RESIDUO_AJUSTE = 0.01
# Las líneas que se calculan. Solo se publican las de
# MERCADOS_GOLES_HABILITADOS, que pasaron la prueba histórica
# (eval/alta_prob_calibracion.py). Cambiar esa lista exige repetir la prueba.
LINEAS_GOLES: tuple[tuple[str, float], ...] = (("over", 1.5), ("under", 3.5), ("under", 4.5))
MERCADOS_GOLES_HABILITADOS: tuple[tuple[str, float], ...] = ()
# Liquidados mínimos antes de que el control pueda pausar la línea.
MIN_N_CONTROL = 50
# Desempate exacto entre candidatos de la misma probabilidad.
_PRIORIDAD = {"h2h": 0, "totals": 1, "double_chance": 2}
_SEL = ("home", "draw", "away")


@dataclass(frozen=True)
class Candidato:
    market: str              # 'h2h' | 'double_chance' | 'totals' (los de clv._settle_outcome)
    selection: str           # home/draw/away · 1X/X2/12 · over/under
    line: float | None
    prob: float


def candidatos_1x2(p: dict[str, float]) -> list[Candidato]:
    return [Candidato("h2h", s, None, float(p[s])) for s in _SEL]


def candidatos_doble(p: dict[str, float]) -> list[Candidato]:
    return [Candidato("double_chance", "1X", None, float(p["home"] + p["draw"])),
            Candidato("double_chance", "X2", None, float(p["draw"] + p["away"])),
            Candidato("double_chance", "12", None, float(p["home"] + p["away"]))]


def ajuste_goles(p: dict[str, float], linea: float, p_over: float,
                 rho: float) -> dict | None:
    """Goles esperados de mercado, o None si el ajuste no reproduce la entrada."""
    try:
        fit = market_lambdas(p["home"], p["draw"], p["away"], rho=rho,
                             totals={linea: p_over})
    except ValueError:
        return None
    if not fit.converged or fit.residual > MAX_RESIDUO_AJUSTE:
        return None
    return {"lambda": fit.lam, "mu": fit.mu, "rho": rho,
            "linea": linea, "residuo": fit.residual}


def candidatos_goles(ajuste: dict | None,
                     habilitados: tuple[tuple[str, float], ...] | None = None
                     ) -> list[Candidato]:
    habilitados = MERCADOS_GOLES_HABILITADOS if habilitados is None else habilitados
    if ajuste is None or not habilitados:
        return []
    m = score_matrix(ajuste["lambda"], ajuste["mu"], ajuste["rho"])
    return [Candidato("totals", sel, linea, market_totals(m, linea)[sel])
            for sel, linea in habilitados]


def elegir(cands: list[Candidato], excluir: set[str] | frozenset = frozenset()
           ) -> Candidato | None:
    dentro = [c for c in cands
              if c.market not in excluir and PROB_MIN <= c.prob <= PROB_MAX]
    if not dentro:
        return None
    return min(dentro, key=lambda c: (c.prob, _PRIORIDAD[c.market]))


def _goles(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def texto(market: str, selection: str, line: float | None,
          local: str, visitante: str) -> str:
    """El pronóstico en palabras, como se enseña en la web."""
    if market == "h2h":
        return {"home": f"Gana {local}", "away": f"Gana {visitante}",
                "draw": "Empate"}[selection]
    if market == "double_chance":
        return {"1X": f"{local} o empate", "X2": f"{visitante} o empate",
                "12": f"{local} o {visitante} (sin empate)"}[selection]
    if market == "totals":
        return f"{'Más' if selection == 'over' else 'Menos'} de {_goles(line)} goles"
    raise ValueError(f"Mercado desconocido: {market}")
