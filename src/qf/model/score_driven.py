"""
A0 del rediseño: adaptación por residuos Poisson inspirada en Koopman y Lit (IJF 2019).

En vez de reajustar un Dixon-Coles ponderado en el tiempo, cada equipo lleva un ataque α y una defensa β que se
mueven tras cada partido con el residuo Poisson. La actualización no es una réplica del score
bivariante/Skellam/probit del artículo ni del gradiente de la corrección DC:

    λ_local  = exp(c_L + h_L + α_local − β_visita)      λ_visita = exp(c_L + α_visita − β_local)
    α_local ← (1 − b)·α_local + a_atq·(x − λ_local)      β_visita ← (1 − b)·β_visita − a_def·(x − λ_local)
    (y lo simétrico con el visitante); c_L y h_L de cada liga se mueven igual con paso a_liga.

`b` devuelve a cada equipo hacia la media de la liga. Equipo nuevo: entra con α = β = 0 (la media de su liga).
Los cinco hiperparámetros (a_atq, a_def, a_liga, b, ρ) se estiman UNA vez por máxima verosimilitud con la historia
anterior a `fin_estimacion` y quedan fijos; después el filtro solo avanza con los partidos nuevos. ρ es la
corrección τ de Dixon-Coles de los marcadores bajos. Con `w_xg` > 0 la observación que mueve las fuerzas es
(1 − w)·goles + w·xG; la verosimilitud se mide siempre con goles.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from .fit_checks import validar_ajuste
from .xg import xg_at_cutoff

C0, H0 = math.log(1.15), 0.25  # nivel inicial de una liga: ~1,15 goles del visitante y ventaja de local 0,25
LIMITES = [(0.0, 0.2), (0.0, 0.2), (0.0, 0.05), (0.0, 0.05), (-0.25, 0.15)]
INICIO = np.array([0.02, 0.02, 0.002, 0.005, -0.05])


def _tau(x: int, y: int, l1: float, l2: float, rho: float) -> float:
    if x == 0 and y == 0:
        return 1 - l1 * l2 * rho
    if x == 0 and y == 1:
        return 1 + l1 * rho
    if x == 1 and y == 0:
        return 1 + l2 * rho
    if x == 1 and y == 1:
        return 1 - rho
    return 1.0


class ScoreDriven:
    def __init__(self, fin_estimacion, w_xg: float = 0.0, columna_xg: str = "xg",
                 disponibilidad: str = 'recepcion'):
        fin = pd.Timestamp(fin_estimacion)
        self.fin_estimacion = fin.tz_localize("UTC") if fin.tzinfo is None else fin.tz_convert("UTC")
        self.w_xg, self.columna_xg = w_xg, columna_xg
        if disponibilidad not in ('recepcion', 'reconstruida'):
            raise ValueError('Política de xG desconocida')
        self.disponibilidad = disponibilidad
        self._as_of = self.fin_estimacion
        self.diagnostico: dict | None = None
        self.estimado_hasta = None
        self.hip: np.ndarray | None = None
        self._reiniciar()

    def _reiniciar(self) -> None:
        self.ataque: dict[str, float] = {}
        self.defensa: dict[str, float] = {}
        self.liga: dict[str, list[float]] = {}
        self.visto = 0

    def _observado(self, df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        hg, ag = df["home_goals"].to_numpy(float), df["away_goals"].to_numpy(float)
        if self.w_xg == 0:
            return hg, ag
        if self.disponibilidad == 'reconstruida':
            hx = df[f"home_{self.columna_xg}"].to_numpy(float)
            ax = df[f"away_{self.columna_xg}"].to_numpy(float)
        else:
            hx, ax = xg_at_cutoff(df, self._as_of)
            if self.columna_xg != 'xg':
                # El mapa de tiros tiene su propio reloj, distinto del xG de `matches`.
                recibido = pd.to_datetime(df.get('derivado_recibido_en', pd.Series(pd.NaT, index=df.index)), utc=True)
                disponible = recibido.notna() & (recibido <= self._as_of)
                dx, dy = (df[f'{s}_{self.columna_xg}'].to_numpy(float) for s in ('home','away'))
                usar = disponible.to_numpy() & np.isfinite(dx) & np.isfinite(dy)
                hx, ax = np.where(usar, dx, hx), np.where(usar, dy, ax)
        ok = ~(np.isnan(hx) | np.isnan(ax))
        w = self.w_xg
        return np.where(ok, (1 - w) * hg + w * hx, hg), np.where(ok, (1 - w) * ag + w * ax, ag)

    def _filtrar(self, df: pd.DataFrame, hip: np.ndarray, sumar: bool) -> float:
        """Avanza el estado con `df` (en orden); devuelve −log-verosimilitud si `sumar`."""
        a_atq, a_def, a_lg, b, rho = (float(v) for v in hip)
        keep = 1.0 - b
        ox, oy = self._observado(df)
        nll = 0.0
        at, de, lg = self.ataque, self.defensa, self.liga
        for h, a, L, x, y, gx, gy in zip(df["home_team"].to_numpy(), df["away_team"].to_numpy(),
                                         df["league_id"].to_numpy(), df["home_goals"].to_numpy(int),
                                         df["away_goals"].to_numpy(int), ox, oy):
            st = lg.get(L)
            if st is None:
                st = lg[L] = [C0, H0]
            ah, dh, aa, da = at.get(h, 0.0), de.get(h, 0.0), at.get(a, 0.0), de.get(a, 0.0)
            l1 = math.exp(st[0] + st[1] + ah - da)
            l2 = math.exp(st[0] + aa - dh)
            if sumar:
                t = _tau(x, y, l1, l2, rho)
                nll -= (x * math.log(l1) - l1 - math.lgamma(x + 1) + y * math.log(l2) - l2 - math.lgamma(y + 1)
                        + math.log(max(t, 1e-12)))
            e1, e2 = gx - l1, gy - l2
            at[h] = keep * ah + a_atq * e1
            de[a] = keep * da - a_def * e1
            at[a] = keep * aa + a_atq * e2
            de[h] = keep * dh - a_def * e2
            st[0] += a_lg * (e1 + e2)
            st[1] += a_lg * e1
        return nll

    def nll(self, hip: np.ndarray, df: pd.DataFrame) -> float:
        guardado = (self.ataque, self.defensa, self.liga, self.visto)
        self._reiniciar()
        try:
            return self._filtrar(df, np.asarray(hip, float), sumar=True)
        finally:
            self.ataque, self.defensa, self.liga, self.visto = guardado

    def ajustar(self, historia: pd.DataFrame, corte) -> None:
        corte = pd.Timestamp(corte)
        corte = corte.tz_localize('UTC') if corte.tzinfo is None else corte.tz_convert('UTC')
        if (historia['kickoff_utc'] >= corte).any():
            raise ValueError('La historia contiene partidos posteriores al corte')
        self._as_of = corte
        if self.estimado_hasta is None and corte >= self.fin_estimacion:
            est = historia[historia["kickoff_utc"] < self.fin_estimacion]
            if est.empty:
                raise ValueError('Sin historia para estimar los hiperparámetros')
            self._as_of = self.fin_estimacion
            # La diferencia hacia delante de paso fijo 1e-4 daba una dirección inexacta
            # cerca del óptimo y terminaba anormalmente en Linux. La derivada centrada
            # conserva la comprobación estricta de convergencia.
            r = minimize(self.nll, INICIO, args=(est,), jac='3-point', method="L-BFGS-B", bounds=LIMITES,
                         options={"maxiter": 500, "maxls": 50, 'ftol':1e-10, 'gtol':1e-5})
            self.diagnostico = validar_ajuste(r, 'ScoreDriven')
            self.hip = r.x
            self.estimado_hasta = self.fin_estimacion
        self._as_of = corte
        if self.hip is None:
            self.hip = INICIO.copy()  # calentamiento con prior; no se presenta como ajuste definitivo
        # Reproducir el filtro admite las observaciones que llegaron tarde sin dejar el estado
        # permanentemente calculado con el xG oculto del corte anterior.
        self._reiniciar()
        self._filtrar(historia, self.hip, sumar=False)
        self.visto = len(historia)

    def predecir(self, partidos: pd.DataFrame) -> pd.DataFrame:
        lam, mu = [], []
        for h, a, L in zip(partidos["home_team"], partidos["away_team"], partidos["league_id"]):
            c, hv = self.liga.get(L, [C0, H0])
            lam.append(math.exp(c + hv + self.ataque.get(h, 0.0) - self.defensa.get(a, 0.0)))
            mu.append(math.exp(c + self.ataque.get(a, 0.0) - self.defensa.get(h, 0.0)))
        return pd.DataFrame({"lam": lam, "mu": mu, "rho": float(self.hip[4])})
