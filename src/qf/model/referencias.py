"""
Modelos de referencia del rediseño de fútbol (fase F2): lo que cualquier variante nueva tiene que batir.

- `Climatologia`: frecuencia de 1/X/2 de cada liga en las tres últimas temporadas.
- `DixonColesRef`: el motor A de producción (`dixon_coles.DixonColes`, vida media 270 días y mezcla 0,65 de xG
  como en el worker) reajustado en cada corte.
- `PiRatings`: Constantinou y Fenton (JQAS 2013), con goles o con xG sin penaltis; el rating se traduce a 1X2 con
  un logit ordenado ajustado con las diferencias PREVIAS de cada partido ya jugado.

Interfaz común con `eval/rediseno.py`: `ajustar(historia, corte)` y `predecir(partidos)`.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from .dixon_coles import DixonColes

EPS = 1e-12


class Climatologia:
    def __init__(self, dias: int = 3 * 365):
        self.dias = dias
        self.frec: dict[str, np.ndarray] = {}

    def ajustar(self, historia: pd.DataFrame, corte) -> None:
        h = historia[historia["kickoff_utc"] >= corte - pd.Timedelta(days=self.dias)]
        self.frec = {lg: np.bincount(g["outcome"], minlength=3) / len(g) for lg, g in h.groupby("league_id")}

    def predecir(self, partidos: pd.DataFrame) -> pd.DataFrame:
        p = np.array([self.frec.get(lg, np.array([0.45, 0.27, 0.28])) for lg in partidos["league_id"]])
        return pd.DataFrame(p, columns=["p_home", "p_draw", "p_away"])


class DixonColesRef:
    """Motor A de producción. Usa solo los últimos `anios` (con vida media de 270 días, lo anterior pesa < 0,5 %)."""

    def __init__(self, halflife: float = 270.0, xg_blend: float = 0.65, anios: float = 6.0):
        self.halflife, self.xg_blend, self.anios = halflife, xg_blend, anios
        self.m: DixonColes | None = None

    def ajustar(self, historia: pd.DataFrame, corte) -> None:
        h = historia[historia["kickoff_utc"] >= corte - pd.Timedelta(days=365 * self.anios)]
        self.m = DixonColes(halflife_days=self.halflife, xg_blend=self.xg_blend)
        self.m.fit(h, as_of=corte.to_pydatetime())

    def predecir(self, partidos: pd.DataFrame) -> pd.DataFrame:
        filas = [self.m.lambdas(r.home_team, r.away_team, r.league_id, r.home_league, r.away_league)
                 for r in partidos.itertuples()]
        out = pd.DataFrame(filas, columns=["lam", "mu"])
        out["rho"] = self.m.params.rho
        return out


def logit_ordenado(z: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Ajusta P(visita) = σ(c1 − βz), P(visita o empate) = σ(c2 − βz) con y = 0 local, 1 empate, 2 visita."""
    s = lambda x: 1 / (1 + np.exp(-x))  # noqa: E731

    def nll(t):
        b, c1, d = t
        c2 = c1 + math.exp(d)
        pa, pad = s(c1 - b * z), s(c2 - b * z)
        p = np.select([y == 2, y == 1], [pa, pad - pa], 1 - pad)
        return -np.sum(np.log(np.clip(p, EPS, 1)))

    r = minimize(nll, np.array([1.0, -0.6, math.log(1.0)]), method="L-BFGS-B")
    b, c1, d = r.x
    return float(b), float(c1), float(c1 + math.exp(d))


class PiRatings:
    """
    Ratings de local y de visitante por equipo (Constantinou-Fenton 2013): diferencia esperada
    ĝ = sign(R)·(10^(|R|/3) − 1); error e = |observada − esperada|; ψ(e) = 3·log10(1 + e); el rating del lado
    jugado se mueve λ·ψ y el del otro lado γ veces ese cambio. `objetivo` = "goles" o "npxg" (xG sin penaltis
    del mapa de tiros; sin él, el partido cuenta con goles).
    """

    def __init__(self, lam: float = 0.035, gam: float = 0.7, objetivo: str = "goles", dias_logit: int = 3 * 365):
        self.lam, self.gam, self.objetivo, self.dias_logit = lam, gam, objetivo, dias_logit
        self.rh: dict[str, float] = {}
        self.ra: dict[str, float] = {}
        self.visto = 0
        self.previas: list[tuple] = []  # (saque, diferencia esperada previa, resultado)
        self.coef = (1.0, -0.6, 0.6)

    @staticmethod
    def _g(r: float) -> float:
        return math.copysign(10 ** (abs(r) / 3) - 1, r)

    def diferencia(self, fila) -> float:
        # Clave = id del equipo: `teams.league_id` es la liga ACTUAL, y un descendido cambiaría de clave.
        return self._g(self.rh.get(fila.home_team, 0.0)) - self._g(self.ra.get(fila.away_team, 0.0))

    def ajustar(self, historia: pd.DataFrame, corte) -> None:
        nuevos = historia.iloc[self.visto:]
        for f in nuevos.itertuples():
            esperada = self.diferencia(f)
            self.previas.append((f.kickoff_utc, esperada, int(f.outcome)))
            if self.objetivo == "npxg" and f.home_npxg == f.home_npxg and f.away_npxg == f.away_npxg:
                obs = f.home_npxg - f.away_npxg
            else:
                obs = f.home_goals - f.away_goals
            e = abs(obs - esperada)
            psi = 3 * math.log10(1 + e)
            psi_h = psi if esperada < obs else -psi
            kh, ka = f.home_team, f.away_team
            dh = psi_h * self.lam
            da = -psi_h * self.lam
            self.rh[kh] = self.rh.get(kh, 0.0) + dh
            self.ra[kh] = self.ra.get(kh, 0.0) + dh * self.gam
            self.ra[ka] = self.ra.get(ka, 0.0) + da
            self.rh[ka] = self.rh.get(ka, 0.0) + da * self.gam
        self.visto = len(historia)
        desde = corte - pd.Timedelta(days=self.dias_logit)
        z = np.array([p[1] for p in self.previas if p[0] >= desde])
        y = np.array([p[2] for p in self.previas if p[0] >= desde])
        if len(z) > 500:
            self.coef = logit_ordenado(z, y)

    def predecir(self, partidos: pd.DataFrame) -> pd.DataFrame:
        b, c1, c2 = self.coef
        z = np.array([self.diferencia(f) for f in partidos.itertuples()])
        s = lambda x: 1 / (1 + np.exp(-x))  # noqa: E731
        pa, pad = s(c1 - b * z), s(c2 - b * z)
        return pd.DataFrame({"p_home": 1 - pad, "p_draw": pad - pa, "p_away": pa})
