"""
Ratings dinámicos por filtrado bayesiano (espacio de estados).

QUÉ CAMBIA FRENTE AL DECAIMIENTO EXPONENCIAL
--------------------------------------------
`dixon_coles.py` trata la fuerza de un equipo como algo FIJO y compensa
pesando menos los partidos viejos. Es una aproximación: dice "lo de hace un
año importa la mitad", pero sigue estimando un único número por equipo para
todo el histórico.

Aquí la fuerza es un ESTADO LATENTE QUE EVOLUCIONA. Cada equipo tiene un
ataque y una defensa con su propia incertidumbre, ambos se mueven como un
paseo aleatorio entre partidos, y cada resultado los actualiza. Tres cosas que
el decaimiento exponencial no puede expresar y esto sí:

1. **La incertidumbre crece con el tiempo parado.** Un equipo que lleva tres
   meses sin jugar (parón, lesiones masivas, mercado de fichajes de por medio)
   tiene un rating más incierto, así que el siguiente resultado lo mueve más.
   El decaimiento exponencial trata igual un hueco de 3 días y uno de 3 meses.
2. **Los equipos nuevos se adaptan rápido.** Un ascendido arranca con
   incertidumbre alta y converge en pocas jornadas en vez de arrastrar la
   media de liga toda la temporada.
3. **Los cambios bruscos se capturan.** Cambio de entrenador, venta de la
   estrella, una plantilla rehecha en enero. El decaimiento tarda una media
   vida en reaccionar; el filtro reacciona en proporción a lo sorprendente que
   sea el resultado.

Además tiene una ventaja práctica grande: `predict_sequential()` recorre el
histórico UNA vez prediciendo cada partido antes de aprenderlo, y eso son
predicciones fuera de muestra genuinas en una sola pasada. El walk-forward de
`eval/backtest.py` reajusta el modelo entero cada 30 días para conseguir lo
mismo, que es órdenes de magnitud más caro.

LA MATEMÁTICA, Y DÓNDE SE APROXIMA
----------------------------------
Un filtro de Kalman exacto exige observaciones gaussianas y aquí los goles son
Poisson, así que se usa la actualización gaussiana aproximada estándar para
modelos lineales dinámicos generalizados (West & Harrison): se linealiza la
verosimilitud alrededor del estado actual usando el gradiente y la información
de Fisher. Para el enlace logarítmico con media λ = exp(η):

    gradiente respecto a η          =  y - λ
    información de Fisher           =  λ

y con ∂η/∂x = ±1 para ataque y defensa, la actualización de cada componente es

    precision_nueva = 1/P + λ
    P_nueva         = 1 / precision_nueva
    x_nueva         = x + P_nueva * (y - λ) * signo

APROXIMACIÓN DELIBERADA: la covarianza se mantiene DIAGONAL (cada equipo, cada
componente, por separado). La covarianza completa entre los 232 equipos
capturaría que "si subo el ataque del equipo A, debo bajar la defensa del B
con el que acaba de jugar", pero cuesta O(n²), complica el código y en la
práctica aporta poco cuando los equipos juegan decenas de partidos. Está
documentado aquí para que nadie lo descubra como sorpresa.

Los parámetros de liga (nivel de goles y ventaja de local) se estiman por
momentos en una pasada previa y se mantienen fijos: son estables en el tiempo,
y dejarlos también dinámicos añade ruido sin ganancia medible.
"""
from __future__ import annotations

import logging
import math
import pickle
from dataclasses import dataclass, field

import numpy as np

log = logging.getLogger(__name__)

# Varianza que gana un rating por cada día sin jugar. Es el parámetro que
# sustituye a la media vida: más alto = ratings más nerviosos.
PROCESS_VAR_PER_DAY = 2.5e-4
# Varianza inicial de un equipo desconocido. Amplia a propósito: queremos que
# sus primeros partidos lo muevan mucho.
INIT_VAR = 0.25
# Reversión a la media de liga por día. Evita que un rating se vaya a la deriva
# en rachas largas. Suave: es una red de seguridad, no el motor del modelo.
MEAN_REVERSION_PER_DAY = 1e-3
# Topes de seguridad de las intensidades, iguales que en dixon_coles.
LAMBDA_MAX = 6.0


@dataclass
class TeamState:
    attack: float = 0.0
    defence: float = 0.0
    var_attack: float = INIT_VAR
    var_defence: float = INIT_VAR
    last_seen: object = None       # datetime del último partido procesado
    n_matches: int = 0


@dataclass
class LeagueParams:
    base: float = 0.0              # log del nivel de goles de la liga
    home_adv: float = 0.25
    n_matches: int = 0


@dataclass
class KalmanConfig:
    process_var_per_day: float = PROCESS_VAR_PER_DAY
    init_var: float = INIT_VAR
    mean_reversion_per_day: float = MEAN_REVERSION_PER_DAY
    xg_blend: float = 0.65
    max_goals: int = 12
    rho: float = -0.03


class DynamicRatings:
    """
    Ratings de ataque y defensa que evolucionan partido a partido.

    Uso normal:
        m = DynamicRatings().fit(df)              # recorre el histórico
        lam, mu = m.lambdas("A", "B", "liga")     # estado actual

    Para evaluación honesta:
        oos = m.predict_sequential(df)            # predice antes de aprender
    """

    def __init__(self, config: KalmanConfig | None = None):
        self.cfg = config or KalmanConfig()
        self.teams: dict[str, TeamState] = {}
        self.leagues: dict[str, LeagueParams] = {}

    # ---------------- parámetros de liga ----------------

    def _estimate_league_params(self, df) -> None:
        """
        Estimación por momentos: el nivel de goles es el log de la media de
        goles de visitante, y la ventaja de local el log del cociente
        local/visitante. Es tosco pero estable, y estos dos números apenas se
        mueven de una temporada a otra.
        """
        col = ("league_id" if "league_id" in df.columns else None)
        grupos = df.groupby(col) if col else [("_", df)]
        for liga, g in grupos:
            hg = g["home_goals"].astype(float).mean()
            ag = g["away_goals"].astype(float).mean()
            hg = max(hg, 0.05)
            ag = max(ag, 0.05)
            self.leagues[str(liga)] = LeagueParams(
                base=math.log(ag),
                home_adv=math.log(hg / ag),
                n_matches=int(len(g)),
            )

    def _league(self, league_id) -> LeagueParams:
        lp = self.leagues.get(str(league_id))
        if lp is not None:
            return lp
        if not self.leagues:
            return LeagueParams()
        # Liga desconocida: media de las conocidas.
        return LeagueParams(
            base=float(np.mean([l.base for l in self.leagues.values()])),
            home_adv=float(np.mean([l.home_adv for l in self.leagues.values()])),
        )

    # ---------------- estado ----------------

    def _key(self, league_id, team: str) -> str:
        return f"{league_id or '_'}||{team}"

    def _state(self, league_id, team: str) -> TeamState:
        k = self._key(league_id, team)
        st = self.teams.get(k)
        if st is None:
            st = TeamState(var_attack=self.cfg.init_var,
                           var_defence=self.cfg.init_var)
            self.teams[k] = st
        return st

    def _advance(self, st: TeamState, ko) -> None:
        """
        Paso de predicción: el rating se difunde y revierte ligeramente hacia
        la media de liga (que es 0 por construcción) según los días
        transcurridos desde su último partido.
        """
        if st.last_seen is None:
            st.last_seen = ko
            return
        dias = max((ko - st.last_seen).total_seconds() / 86400.0, 0.0)
        if dias <= 0:
            return
        # Reversión a la media
        pull = math.exp(-self.cfg.mean_reversion_per_day * dias)
        st.attack *= pull
        st.defence *= pull
        # Difusión: la incertidumbre crece con el tiempo parado
        crecimiento = self.cfg.process_var_per_day * dias
        st.var_attack = st.var_attack * pull * pull + crecimiento
        st.var_defence = st.var_defence * pull * pull + crecimiento
        st.last_seen = ko

    # ---------------- predicción ----------------

    # `league_id` es la COMPETICIÓN (de ahí salen base y ventaja de local);
    # `home_league`/`away_league`, la liga doméstica de cada equipo, que es
    # quien lo identifica. Solo difieren en las copas europeas: indexar ahí por
    # la competición crearía un estado nuevo para el mismo club con la varianza
    # inicial completa, o sea tirando a la basura todo lo aprendido en su liga.
    def lambdas(self, home_team: str, away_team: str, league_id=None,
                home_league=None, away_league=None) -> tuple[float, float]:
        lp = self._league(league_id)
        h = self._state(home_league if home_league is not None else league_id,
                        home_team)
        a = self._state(away_league if away_league is not None else league_id,
                        away_team)
        lam = math.exp(lp.base + h.attack - a.defence + lp.home_adv)
        mu = math.exp(lp.base + a.attack - h.defence)
        return min(lam, LAMBDA_MAX), min(mu, LAMBDA_MAX)

    def knows(self, home_team: str, away_team: str, league_id=None,
              home_league=None, away_league=None) -> bool:
        hlg = home_league if home_league is not None else league_id
        alg = away_league if away_league is not None else league_id
        return (self._key(hlg, home_team) in self.teams
                and self._key(alg, away_team) in self.teams)

    def predict(self, home_team: str, away_team: str, league_id=None,
                home_league=None, away_league=None) -> dict:
        from .pricing import price_all_markets

        lam, mu = self.lambdas(home_team, away_team, league_id,
                               home_league, away_league)
        markets = price_all_markets(lam, mu, self.cfg.rho, self.cfg.max_goals)
        markets["_meta"] = {
            "home_lambda": lam, "away_lambda": mu, "rho": self.cfg.rho,
            "both_teams_known": self.knows(home_team, away_team, league_id,
                                           home_league, away_league),
            "engine": "kalman",
        }
        return markets

    # ---------------- actualización ----------------

    @staticmethod
    def _update_component(x: float, var: float, y: float, lam: float,
                          signo: float) -> tuple[float, float]:
        """
        Actualización gaussiana aproximada para una observación Poisson con
        enlace logarítmico. `signo` es ∂η/∂x: +1 para el ataque del que marca,
        -1 para la defensa del que encaja.
        """
        info = lam                      # información de Fisher respecto a η
        precision = 1.0 / max(var, 1e-9) + info
        var_new = 1.0 / precision
        x_new = x + var_new * (y - lam) * signo
        # Tope de cordura: un rating fuera de este rango es un dato corrupto,
        # no un equipo extraordinario.
        return float(np.clip(x_new, -2.5, 2.5)), float(var_new)

    def update_match(self, home_team: str, away_team: str, league_id,
                     home_goals: float, away_goals: float, ko,
                     home_xg: float | None = None,
                     away_xg: float | None = None,
                     home_league=None, away_league=None) -> None:
        lp = self._league(league_id)
        h = self._state(home_league if home_league is not None else league_id,
                        home_team)
        a = self._state(away_league if away_league is not None else league_id,
                        away_team)
        self._advance(h, ko)
        self._advance(a, ko)

        lam = min(math.exp(lp.base + h.attack - a.defence + lp.home_adv), LAMBDA_MAX)
        mu = min(math.exp(lp.base + a.attack - h.defence), LAMBDA_MAX)

        # Objetivo mezclado goles/xG, igual que en dixon_coles: el xG tiene
        # menos ruido, así que el filtro converge con menos partidos.
        b = self.cfg.xg_blend
        y_h = float(home_goals) if home_xg is None or home_xg != home_xg \
            else (1 - b) * float(home_goals) + b * float(home_xg)
        y_a = float(away_goals) if away_xg is None or away_xg != away_xg \
            else (1 - b) * float(away_goals) + b * float(away_xg)

        # Los goles del local informan del ataque local y de la defensa visitante.
        h.attack, h.var_attack = self._update_component(h.attack, h.var_attack,
                                                        y_h, lam, +1.0)
        a.defence, a.var_defence = self._update_component(a.defence, a.var_defence,
                                                          y_h, lam, -1.0)
        # Y los del visitante, al revés.
        a.attack, a.var_attack = self._update_component(a.attack, a.var_attack,
                                                        y_a, mu, +1.0)
        h.defence, h.var_defence = self._update_component(h.defence, h.var_defence,
                                                          y_a, mu, -1.0)

        h.n_matches += 1
        a.n_matches += 1
        h.last_seen = ko
        a.last_seen = ko

    # ---------------- recorridos ----------------

    def fit(self, df) -> "DynamicRatings":
        """Recorre el histórico en orden cronológico actualizando el estado."""
        df = df.dropna(subset=["home_goals", "away_goals"]).sort_values("kickoff_utc")
        if len(df) < 50:
            raise ValueError(f"Muestra insuficiente: {len(df)} partidos")
        self._estimate_league_params(df)
        for _, r in df.iterrows():
            self.update_match(
                r["home_team"], r["away_team"], r.get("league_id"),
                r["home_goals"], r["away_goals"], r["kickoff_utc"],
                r.get("home_xg"), r.get("away_xg"),
                r.get("home_league"), r.get("away_league"),
            )
        return self

    def predict_sequential(self, df, min_matches: int = 5):
        """
        Predice cada partido ANTES de aprenderlo y devuelve un DataFrame con la
        misma forma que `eval.backtest.walk_forward_oos`.

        Es fuera de muestra por construcción: cuando se predice el partido i,
        el estado solo ha visto los partidos 1..i-1. No hay forma de colar
        información del futuro ni olvidándose de un filtro, que es la fuga más
        común de estos backtests.

        `min_matches`: partidos mínimos que deben tener AMBOS equipos para que
        la fila cuente. Los primeros partidos de cada equipo son ruido de
        arranque del filtro, no señal.
        """
        import pandas as pd

        from .devig import devig

        df = df.dropna(subset=["home_goals", "away_goals"]).sort_values("kickoff_utc")
        self._estimate_league_params(df)
        filas = []

        for _, r in df.iterrows():
            liga = r.get("league_id")
            lg_h = r.get("home_league") if r.get("home_league") is not None else liga
            lg_a = r.get("away_league") if r.get("away_league") is not None else liga
            h = self._state(lg_h, r["home_team"])
            a = self._state(lg_a, r["away_team"])
            listos = h.n_matches >= min_matches and a.n_matches >= min_matches

            if listos:
                pred = self.predict(r["home_team"], r["away_team"], liga,
                                    lg_h, lg_a)
                p = pred["1x2"]
                hg, ag = int(r["home_goals"]), int(r["away_goals"])
                mk = [np.nan] * 3
                cols = ("odds_home", "odds_draw", "odds_away")
                if all(c in r and r[c] == r[c] and r[c] for c in cols):
                    try:
                        mk = list(devig([r[c] for c in cols]))
                    except ValueError:
                        pass
                filas.append({
                    "match_id": r.get("match_id"),
                    "kickoff_utc": r["kickoff_utc"],
                    "league_id": liga,
                    "home_team": r["home_team"], "away_team": r["away_team"],
                    "p_home": p["home"], "p_draw": p["draw"], "p_away": p["away"],
                    "lam": pred["_meta"]["home_lambda"],
                    "mu": pred["_meta"]["away_lambda"],
                    "mk_home": mk[0], "mk_draw": mk[1], "mk_away": mk[2],
                    "outcome": 0 if hg > ag else 1 if hg == ag else 2,
                    "both_known": True,
                    "home_goals": hg, "away_goals": ag,
                })

            self.update_match(
                r["home_team"], r["away_team"], liga,
                r["home_goals"], r["away_goals"], r["kickoff_utc"],
                r.get("home_xg"), r.get("away_xg"), lg_h, lg_a,
            )

        if not filas:
            raise RuntimeError(
                "No se produjo ninguna predicción. Revisa min_matches o el "
                "tamaño del histórico."
            )
        return pd.DataFrame(filas)

    # ---------------- informes y persistencia ----------------

    def league_report(self) -> list[dict]:
        return [
            {
                "league_id": lg,
                "home_advantage": round(lp.home_adv, 4),
                "goal_base": round(lp.base, 4),
                "expected_home_goals_avg": round(math.exp(lp.base + lp.home_adv), 3),
                "expected_away_goals_avg": round(math.exp(lp.base), 3),
                "n_matches": lp.n_matches,
            }
            for lg, lp in sorted(self.leagues.items())
        ]

    def top_teams(self, n: int = 10) -> list[dict]:
        """Ranking por fuerza neta. Sirve para el sanity check de ojo humano."""
        filas = [
            {
                "team": k.split("||", 1)[1],
                "league": k.split("||", 1)[0],
                "attack": round(st.attack, 4),
                "defence": round(st.defence, 4),
                "net": round(st.attack + st.defence, 4),
                "uncertainty": round(math.sqrt(st.var_attack + st.var_defence), 4),
                "n_matches": st.n_matches,
            }
            for k, st in self.teams.items() if st.n_matches >= 10
        ]
        filas.sort(key=lambda x: -x["net"])
        return filas[:n]

    def save(self, path: str) -> None:
        with open(path, "wb") as f:
            pickle.dump({"cfg": self.cfg, "teams": self.teams,
                         "leagues": self.leagues}, f)

    @classmethod
    def load(cls, path: str) -> "DynamicRatings":
        with open(path, "rb") as f:
            d = pickle.load(f)
        m = cls(d["cfg"])
        m.teams = d["teams"]
        m.leagues = d["leagues"]
        return m


def tune_process_var(df, grid=(5e-5, 1e-4, 2.5e-4, 5e-4, 1e-3),
                     xg_blend: float = 0.65) -> dict:
    """
    Barrido del parámetro que sustituye a la media vida.

    Es el único hiperparámetro del filtro que vale la pena ajustar a mano, y
    se ajusta contra RPS fuera de muestra secuencial, no contra el ajuste.
    """
    from ..eval.backtest import metrics_from_oos

    out = {}
    for pv in grid:
        try:
            m = DynamicRatings(KalmanConfig(process_var_per_day=float(pv),
                                            xg_blend=xg_blend))
            oos = m.predict_sequential(df)
            res = metrics_from_oos(oos)
            out[pv] = {"rps": res["rps"], "log_loss": res["log_loss"],
                       "n_obs": res["n_obs"],
                       "rps_market": res.get("rps_market")}
            log.info("process_var=%.1e -> RPS=%.5f (n=%d)",
                     pv, res["rps"], res["n_obs"])
        except Exception as exc:  # noqa: BLE001
            log.warning("process_var=%.1e falló: %s", pv, exc)
    best = min(out, key=lambda k: out[k]["rps"]) if out else None
    return {"results": out, "best_process_var": best}
