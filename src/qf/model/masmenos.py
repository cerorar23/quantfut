"""
Más-menos regularizado por jugador (idea 2 de la literatura, 2026-10-03).

Kharrat, McHale y Peña (2020) y Hvattum valoran a un jugador por cómo le va
al equipo con él en el campo, descontando compañeros y rivales, y encuentran
que predice mejor que construir el valor desde sus estadísticas, que es lo
que hizo "XI con valor" (`player_ratings.py`) y no funcionó.

Versión APROXIMADA (decisión del usuario): sin el minuto de cada cambio, cada
jugador cuenta en el partido entero en proporción a sus minutos. La exacta
necesita `/fixtures/events` y queda para después si esta apunta algo.

    y_partido = diferencia de goles local−visitante, mezclada con la de xG
    fila      = +minutos/90 por jugador local, −minutos/90 por visitante
    ridge ponderado por decaimiento, λ = LAMBDA

Punto en el tiempo por construcción: se reajusta cada REAJUSTE_DIAS solo con
partidos anteriores al reajuste, y los partidos hasta el siguiente usan esos
ratings. Diseño fijado antes de ver resultados en harness/tareas.md.
"""
from __future__ import annotations

from collections import defaultdict, deque

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import lsqr

from .player_ratings import LADOS, _habitual, _xi

LAMBDA = 10.0           # un jugador pesa como 10 partidos completos a rating 0
REAJUSTE_DIAS = 7
MASMENOS_FEATURES = [f"{lado}_d_pm" for lado in LADOS]


def objetivo(partidos: pd.DataFrame, xg_blend: float) -> np.ndarray:
    """Diferencia de goles mezclada con la de xG donde la hay, igual que el modelo."""
    gd = (partidos["home_goals"].astype(float) - partidos["away_goals"].astype(float)).to_numpy()
    if not {"home_xg", "away_xg"} <= set(partidos.columns):
        return gd
    xgd = (pd.to_numeric(partidos["home_xg"], errors="coerce")
           - pd.to_numeric(partidos["away_xg"], errors="coerce")).to_numpy(float)
    return np.where(np.isfinite(xgd), (1 - xg_blend) * gd + xg_blend * xgd, gd)


class _Disenio:
    """Matriz dispersa partido × jugador construida una sola vez."""

    def __init__(self, partidos: pd.DataFrame, stats: pd.DataFrame, xg_blend: float):
        stats = stats[stats["minutos"] > 0]
        con_stats = partidos[partidos["match_id"].isin(set(stats["match_id"]))]
        con_stats = con_stats.sort_values("kickoff_utc").reset_index(drop=True)
        self.ko = pd.to_datetime(con_stats["kickoff_utc"], utc=True).dt.tz_convert(None).to_numpy()
        self.y = objetivo(con_stats, xg_blend)
        fila = {mid: i for i, mid in enumerate(con_stats["match_id"])}
        s = stats[stats["match_id"].isin(fila)]
        self.jugadores = np.array(sorted(s["player_id"].astype(int).unique()))
        col = {pid: j for j, pid in enumerate(self.jugadores)}
        signo = np.where(s["side"].to_numpy() == "home", 1.0, -1.0)
        self.X = csr_matrix(
            (signo * s["minutos"].to_numpy(float) / 90.0,
             (s["match_id"].map(fila).to_numpy(), s["player_id"].astype(int).map(col).to_numpy())),
            shape=(len(con_stats), len(self.jugadores)))

    def ajustar(self, hasta: pd.Timestamp, vida_media_dias: float,
                lam: float = LAMBDA) -> dict[int, float]:
        """Ratings con los partidos estrictamente anteriores a `hasta`."""
        t = pd.Timestamp(hasta).tz_convert(None).to_datetime64()
        n = int(np.searchsorted(self.ko, t, side="left"))
        if n == 0:
            return {}
        X = self.X[:n]
        dias = (t - self.ko[:n]) / np.timedelta64(1, "D")
        w = 0.5 ** (dias / vida_media_dias)
        y = self.y[:n] - np.average(self.y[:n], weights=w)   # la localía
        raiz = np.sqrt(w)
        A = X.multiply(raiz[:, None]).tocsr()
        beta = lsqr(A, y * raiz, damp=np.sqrt(lam), atol=1e-8, btol=1e-8)[0]
        jugaron = np.asarray(abs(X).sum(axis=0)).ravel() > 0
        return {int(p): float(b) for p, b, ok in zip(self.jugadores, beta, jugaron) if ok}


def build_pm_features(matches: pd.DataFrame, lineups: pd.DataFrame, stats: pd.DataFrame,
                      vida_media_dias: float = 180.0, xg_blend: float = 0.65,
                      lam: float = LAMBDA, lookback: int = 5,
                      max_desconocidos: int = 3) -> pd.DataFrame:
    """
    Por partido y lado: suma de ratings del XI de hoy menos la del XI
    habitual. Mismas reglas de historia y descarte que
    `player_ratings.build_value_features`, para comparar sobre las mismas filas.
    """
    cols = ["match_id", *MASMENOS_FEATURES]
    if matches.empty or lineups.empty or stats.empty:
        return pd.DataFrame(columns=cols)
    ms = matches.copy()
    ms["kickoff_utc"] = pd.to_datetime(ms["kickoff_utc"], utc=True)
    ms = ms.dropna(subset=["home_goals", "away_goals"])
    disenio = _Disenio(ms, stats, xg_blend)
    xi_de = {(r["match_id"], r["side"]): _xi(r["starters"]) for _, r in lineups.iterrows()}
    historias: dict[object, deque] = defaultdict(lambda: deque(maxlen=lookback))
    ratings: dict[int, float] = {}
    siguiente: pd.Timestamp | None = None
    filas = []
    for ko, grupo in ms.sort_values(["kickoff_utc", "match_id"]).groupby("kickoff_utc", sort=True):
        if siguiente is None or ko >= siguiente:
            ratings = disenio.ajustar(ko, vida_media_dias, lam)
            siguiente = ko + pd.Timedelta(days=REAJUSTE_DIAS)
        pendientes = []
        for _, m in grupo.iterrows():
            valores, completo = {"match_id": m["match_id"]}, True
            for lado in LADOS:
                hoy = xi_de.get((m["match_id"], lado))
                equipo = m[f"{lado}_team_id"]
                if not hoy:
                    completo = False
                    continue
                pendientes.append((equipo, hoy))
                historia = historias[equipo]
                if len(historia) < 3 or sum(p not in ratings for p in hoy) > max_desconocidos:
                    completo = False
                    continue
                suma = lambda xi: sum(ratings.get(p, 0.0) for p in xi)  # noqa: E731
                valores[f"{lado}_d_pm"] = suma(hoy) - suma(_habitual(historia))
            if completo:
                filas.append(valores)
        for equipo, hoy in pendientes:
            historias[equipo].append(hoy)
    return pd.DataFrame(filas, columns=cols)
