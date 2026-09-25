"""
Del "creo que tengo un 6% de ventaja" al "6% ± 4%", que es lo que decide.

DOS PROBLEMAS, UNA SOLA MEDIDA
------------------------------
El sistema arrastraba dos constantes puestas a ojo que resuelven lo mismo mal:

1. `EDGE_SHRINKAGE = 0.55`. El edge estimado está sesgado al alza por selección
   adversa —solo se apuesta donde el modelo discrepa, que es donde suele
   equivocarse— y se corrige multiplicando por 0,55. Es la dirección correcta y
   la magnitud inventada, y sobre todo es la MISMA para todos: encoge igual una
   discrepancia sobre el Liverpool, del que hay 20 partidos recientes, que una
   sobre un recién ascendido del que hay tres.

2. No había zona de abstención. Un edge nominalmente positivo pero dentro del
   ruido del propio modelo producía un pick igual.

Las dos se resuelven con la misma cantidad: **cuánto varía el edge cuando los
parámetros del modelo varían dentro de su propia incertidumbre**. Si el edge
medio es 6% y su desviación 8%, no es una ventaja del 6%: es ruido. Si es 6%
con desviación 1,5%, es una ventaja pequeña y sólida.

CÓMO
----
`DixonColes.fit()` deja el error estándar de `attack` y `defence` de cada
equipo (estimador sándwich, ver allí). Aquí se propagan por Monte Carlo hasta
el edge:

    atk_h, dfn_h, atk_a, dfn_a  ~  N(estimado, se)
        -> lambda, mu  ->  matriz de marcadores  ->  p(selección)
        -> edge = p * cuota - 1

Y de la distribución del edge salen las dos decisiones:

    edge_floor = media - Z * desviación

    edge_floor <= 0  ->  ABSTENERSE. La ventaja no sobrevive al ruido.
    edge_floor >  0  ->  encogimiento = edge_floor / media,
                         que es `EDGE_SHRINKAGE` pero MEDIDO y por apuesta.

Un equipo bien medido apenas se encoge; uno con muestra corta se encoge mucho
o directamente no se apuesta. Eso es lo que la constante no podía hacer.

LO QUE ESTO NO ES
-----------------
No crea ventaja. Elimina apuestas de valor esperado negativo que el sistema
publicaba como si fueran buenas, así que sube el ROI realizado y NO mejora el
RPS: son cosas distintas y conviene no confundirlas al medir si funciona.

Tampoco cubre todas las fuentes de error. Mide la incertidumbre de los
parámetros DADO el modelo; no mide que el modelo sea el equivocado, que es la
parte que `w_model = 0.0001` dice que domina. Es un suelo de prudencia, no un
intervalo de confianza honesto sobre el resultado del partido.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..config import settings
from .dixon_coles import DixonColes, team_key
from .pricing import market_1x2, market_totals, score_matrix


@dataclass(frozen=True)
class EdgeUncertainty:
    edge_mean: float          # %, media de la distribución
    edge_sd: float            # %
    edge_floor: float         # %, media - Z*sd
    shrinkage: float          # en [0, 1]; 0 = abstenerse
    n_draws: int

    @property
    def abstain(self) -> bool:
        return self.shrinkage <= 0.0

    def as_dict(self) -> dict:
        return {"edge_mean_pct": round(self.edge_mean, 4),
                "edge_sd_pct": round(self.edge_sd, 4),
                "edge_floor_pct": round(self.edge_floor, 4),
                "shrinkage": round(self.shrinkage, 4),
                "abstain": self.abstain, "n_draws": self.n_draws}


def _se(model: DixonColes, team: str, league: str | None) -> tuple[float, float]:
    """
    (se_ataque, se_defensa).

    Un equipo que el modelo no tiene es INCIERTO del todo, no certero: devuelve
    infinito, y quien llame se abstendrá. Devolver cero diría lo contrario de
    la verdad.
    """
    p = model.params
    if p is None:
        raise RuntimeError("Modelo no entrenado")
    if not p.se_attack or not p.se_defence:
        return 0.0, 0.0          # artefacto anterior: sin dato, sin veredicto
    i = model._idx.get(team_key(league, team))
    if i is None:
        return float("inf"), float("inf")
    return float(p.se_attack[i]), float(p.se_defence[i])


def lambda_draws(model: DixonColes, home_team: str, away_team: str,
                 league_id: str | None = None,
                 home_league: str | None = None,
                 away_league: str | None = None,
                 n_draws: int = 256, seed: int | None = 0,
                 base: tuple[float, float] | None = None
                 ) -> tuple[np.ndarray, np.ndarray]:
    """
    Muestras de (lambda, mu) perturbando los parámetros de los dos equipos.

    `base` permite anclar en el MERCADO (ver `model/market_anchor.py`): la
    incertidumbre sigue siendo la del modelo, pero se aplica alrededor del
    nivel de mercado en vez del suyo propio. Es lo coherente con w_model ~ 0.
    """
    hlg = home_league if home_league is not None else league_id
    alg = away_league if away_league is not None else league_id
    se_atk_h, se_dfn_h = _se(model, home_team, hlg)
    se_atk_a, se_dfn_a = _se(model, away_team, alg)

    lam0, mu0 = (base if base is not None
                 else model.lambdas(home_team, away_team, league_id, hlg, alg))

    if not np.isfinite([se_atk_h, se_dfn_h, se_atk_a, se_dfn_a]).all():
        nan = np.full(n_draws, np.nan)
        return nan, nan

    rng = np.random.default_rng(seed)
    # log(lambda) lleva +atk_h -dfn_a ; log(mu) lleva +atk_a -dfn_h.
    d_lam = rng.normal(0, se_atk_h, n_draws) - rng.normal(0, se_dfn_a, n_draws)
    d_mu = rng.normal(0, se_atk_a, n_draws) - rng.normal(0, se_dfn_h, n_draws)
    return (np.clip(lam0 * np.exp(d_lam), 1e-6, 25.0),
            np.clip(mu0 * np.exp(d_mu), 1e-6, 25.0))


def _prob(lam: float, mu: float, rho: float, market: str, selection: str,
          line: float | None, max_goals: int) -> float:
    m = score_matrix(lam, mu, rho, max_goals)
    if market == "h2h":
        return market_1x2(m)[selection]
    if market == "totals":
        return market_totals(m, float(line))[selection]
    raise ValueError(f"Mercado sin soporte de incertidumbre: {market}")


SUPPORTED_MARKETS = ("h2h", "totals")


def edge_uncertainty(model: DixonColes, home_team: str, away_team: str,
                     market: str, selection: str, line: float | None,
                     price: float, league_id: str | None = None,
                     home_league: str | None = None,
                     away_league: str | None = None,
                     n_draws: int | None = None, z: float | None = None,
                     seed: int | None = 0,
                     base: tuple[float, float] | None = None
                     ) -> EdgeUncertainty:
    """Distribución del edge de UNA selección y el encogimiento que le toca."""
    z = settings.uncertainty_z if z is None else z
    n_draws = settings.uncertainty_draws if n_draws is None else n_draws
    lams, mus = lambda_draws(model, home_team, away_team, league_id,
                             home_league, away_league, n_draws, seed, base)
    if np.isnan(lams).any():
        # Sin errores estándar no se puede afirmar nada: abstenerse.
        return EdgeUncertainty(0.0, float("inf"), float("-inf"), 0.0, n_draws)

    rho = model.params.rho
    probs = np.array([_prob(float(l), float(m), rho, market, selection, line,
                            model.max_goals) for l, m in zip(lams, mus)])
    edges = (probs * price - 1.0) * 100.0
    mean, sd = float(edges.mean()), float(edges.std(ddof=1))
    floor = mean - z * sd
    shrink = 0.0 if (mean <= 0 or floor <= 0) else min(floor / mean, 1.0)
    return EdgeUncertainty(mean, sd, floor, shrink, n_draws)
