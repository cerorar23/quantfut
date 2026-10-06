"""
Anclar el modelo en el MERCADO en vez de en sí mismo.

POR QUÉ EXISTE ESTE MÓDULO
--------------------------
`model/meta.py` midió el peso óptimo del modelo frente al mercado sobre 28.128
predicciones fuera de muestra y le salió **w_model = 0.0001**. La lectura fácil
es "el modelo no sirve". La correcta es más útil:

    el modelo sirve para la FORMA, no para el NIVEL.

La forma es la matriz de marcadores: de dos intensidades salen ~150 mercados
que no se contradicen entre sí —el over 2.5, el hándicap y el resultado exacto
hablan del mismo partido—. Eso el mercado no te lo da: te da precios sueltos
de los mercados que cotiza, cada uno con su margen. El nivel sí lo tiene el
mercado, y mejor que el modelo.

Este módulo hace la inversión: de las probabilidades de mercado YA sin margen
saca el par (lambda, mu) que las reproduce bajo Dixon-Coles. A partir de ahí:

  - se puede precificar cualquier mercado derivado a partir del precio sharp,
    en vez de a partir de la fuerza estimada de los equipos;
  - un ajuste por información nueva (el XI, una lesión) se aplica ENCIMA del
    nivel de mercado, que es la única construcción en la que esa información
    es aditiva a lo ya preciado. Ver `model/lineup_challenger.py`.

EL LÍMITE, QUE HAY QUE MIRAR SIEMPRE
------------------------------------
La familia Dixon-Coles NO puede representar cualquier terna (local, empate,
visitante). Fijados los dos goles esperados, la probabilidad de empate queda
determinada; si el mercado cotiza un empate fuera de ese rango, no existe
ningún (lambda, mu) que lo reproduzca. Por eso `market_lambdas()` devuelve
SIEMPRE el residuo del ajuste junto a las lambdas, y quien lo llame tiene que
decidir con él. Devolver solo las lambdas convertiría un desacuerdo
estructural en un número de aspecto inocente.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from .pricing import market_1x2, score_matrix, totals_fair_over

# Por debajo de esto el ajuste reproduce el precio de mercado a efectos
# prácticos: 0,002 de error absoluto máximo es medio punto de cuota en una
# cuota de 3,00, muy por debajo del margen de cualquier casa.
RESIDUAL_OK = 0.002


@dataclass(frozen=True)
class MarketFit:
    lam: float
    mu: float
    residual: float          # error absoluto MÁXIMO sobre las probabilidades
    converged: bool

    @property
    def usable(self) -> bool:
        return self.converged and self.residual <= RESIDUAL_OK

    def as_dict(self) -> dict:
        return {"lambda": self.lam, "mu": self.mu,
                "residual": self.residual, "usable": self.usable}


def _targets(p_home: float, p_draw: float, p_away: float,
             totals: dict[float, float] | None):
    """[(callable(matriz) -> prob, objetivo, peso)]."""
    out = [
        (lambda m: market_1x2(m)["home"], p_home, 1.0),
        (lambda m: market_1x2(m)["draw"], p_draw, 1.0),
        (lambda m: market_1x2(m)["away"], p_away, 1.0),
    ]
    # Los totales sobre-identifican el sistema: con 1X2 solo hay exactamente
    # dos ecuaciones libres para dos incógnitas, así que el over/under no
    # cambia la solución cuando el mercado es coherente, pero cuando NO lo es
    # el residuo lo delata en vez de esconderlo. `p_over` es la del mercado
    # de dos vías sin margen: en gol entero y cuarto de gol lleva el push
    # descontado, por eso se compara con `totals_fair_over` y no con P(over).
    for line, p_over in (totals or {}).items():
        out.append((lambda m, ln=float(line): totals_fair_over(m, ln),
                    float(p_over), 0.5))
    return out


def market_lambdas(p_home: float, p_draw: float, p_away: float,
                   rho: float = 0.0, max_goals: int = 12,
                   totals: dict[float, float] | None = None) -> MarketFit:
    """
    (lambda, mu) que reproducen el precio de mercado SIN MARGEN bajo Dixon-Coles.

    `p_*` tienen que venir ya des-margenadas (`model/devig.py`). Pasar cuotas
    implícitas crudas mete el margen de la casa dentro de las intensidades y
    todo lo que se derive después estará inflado.

    `rho` es el del modelo: la corrección de marcadores bajos es estructura del
    fútbol, no una opinión sobre este partido, así que se hereda en vez de
    estimarse aquí (con tres probabilidades no habría grados de libertad para
    una tercera incógnita).
    """
    p = np.array([p_home, p_draw, p_away], dtype=float)
    if np.any(p <= 0) or np.any(p >= 1):
        raise ValueError(f"Probabilidades fuera de (0,1): {p}")
    s = p.sum()
    if not math.isclose(s, 1.0, abs_tol=1e-6):
        raise ValueError(f"Las probabilidades 1X2 tienen que sumar 1, suman {s:.6f}. "
                         "¿Se olvidó el de-vig?")

    objetivos = _targets(p_home, p_draw, p_away, totals)

    def coste(x: np.ndarray) -> float:
        lam, mu = math.exp(x[0]), math.exp(x[1])
        m = score_matrix(lam, mu, rho, max_goals)
        return float(sum(w * (fn(m) - obj) ** 2 for fn, obj, w in objetivos))

    # Arranque: la ventaja local sale del cociente local/visitante y el total de
    # goles de lo lejos que esté el empate. No hace falta afinar, solo caer en
    # la cuenca correcta.
    sup = 0.5 * math.log(max(p_home, 1e-6) / max(p_away, 1e-6))
    tot = math.log(max(2.7 * (1.0 - p_draw) / 0.75, 0.4))
    x0 = np.array([tot / 2 + sup, tot / 2 - sup])

    res = minimize(coste, x0, method="Nelder-Mead",
                   options={"xatol": 1e-8, "fatol": 1e-12, "maxiter": 2000})

    lam, mu = float(math.exp(res.x[0])), float(math.exp(res.x[1]))
    m = score_matrix(lam, mu, rho, max_goals)
    residual = max(abs(fn(m) - obj) for fn, obj, _ in objetivos)
    return MarketFit(lam=lam, mu=mu, residual=float(residual),
                     converged=bool(res.success))


def anchor_from_consensus(consensus: dict[str, float], rho: float = 0.0,
                          max_goals: int = 12,
                          totals: dict[float, float] | None = None
                          ) -> MarketFit | None:
    """
    Atajo desde la salida de `devig.consensus_devig`. Devuelve None si el
    consenso no trae el 1X2 completo, que es lo normal cuando solo hay una
    casa con dos de los tres precios.
    """
    if not consensus or not {"home", "draw", "away"} <= set(consensus):
        return None
    return market_lambdas(consensus["home"], consensus["draw"],
                          consensus["away"], rho, max_goals, totals)
