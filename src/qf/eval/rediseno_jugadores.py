"""
Props de jugador del rediseño (listas del titular, 1-nov-2026): tiros a puerta, tiros, pases completados, faltas
recibidas, gol en cualquier momento, primer goleador y tarjeta.

Para cada TITULAR (el once es público a T-60) la media esperada es  tasa por 90 × minutos esperados / 90:
- tasa por 90: media exponencial de sus partidos ANTERIORES (estadística y minutos por separado), encogida hacia la
  media de su posición con `k` partidos de peso;
- minutos esperados: media exponencial de los minutos en sus titularidades anteriores.
Recuentos con Poisson; pases con binomial negativa (dispersión estimada con temporadas anteriores a la evaluación).
Gol: 65 % xG + 35 % goles por 90 cuando hay xG (como el motor A). Primer goleador: carrera exponencial,
P = (μ_jugador / Λ_partido)·(1 − e^{−Λ}).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson
from .temporal import medias_previas

STATS = ["tiros_puerta", "tiros_totales", "pases_acertados", "faltas_recibidas", "goles", "xg", "tarjeta"]


def tabla(jug: pd.DataFrame, partidos: pd.DataFrame, incid: pd.DataFrame) -> pd.DataFrame:
    j = jug.merge(partidos[["match_id", "kickoff_utc", "league_id"]], on="match_id")
    j["titular"] = j["titular"].astype(str).str.lower().isin(["t", "true", "1"])
    tot = j[["tiros_puerta", "tiros_fuera", "tiros_bloq"]].sum(axis=1, min_count=1)
    j["tiros_totales"] = j["tiros_totales"].fillna(tot)
    incoherente = j.tiros_puerta.gt(j.tiros_totales) | j.tiros_puerta.lt(0) | j.tiros_totales.lt(0)
    j.loc[incoherente, ['tiros_puerta','tiros_totales']] = np.nan
    tarj = incid[incid["subtipo"].eq("card") & incid["clase"].isin(["yellow", "yellowRed", "red"])]
    tarj = tarj.groupby(["match_id", "jugador_id"]).size().rename("tarjeta").reset_index()
    j = j.merge(tarj, on=["match_id", "jugador_id"], how="left")
    # solo partidos con incidencias cargadas cuentan como «sin tarjeta»
    con_inc = set(incid["match_id"])
    j["tarjeta"] = np.where(j["match_id"].isin(con_inc), j["tarjeta"].fillna(0), np.nan)
    j["dia"] = j["kickoff_utc"].dt.strftime("%Y-%m-%d")
    return j.sort_values(["kickoff_utc", "match_id"]).reset_index(drop=True)


def previos(j: pd.DataFrame, fin_entreno, vida: float = 8.0, k: float = 6.0) -> pd.DataFrame:
    """Medias esperadas por partido con solo información anterior (desplazada una posición)."""
    j = j.copy()
    g = j.groupby("jugador_id")
    ew = lambda s: s.ewm(halflife=vida, ignore_na=True).mean().shift(1)  # noqa: E731
    j["n_prev"] = g.cumcount()
    titulares = j["minutos"].where(j["titular"])
    j["min_esp"] = titulares.groupby(j["jugador_id"]).transform(ew)
    entrenamiento = j.kickoff_utc < pd.Timestamp(fin_entreno, tz='UTC')
    disponibles = j.kickoff_utc + pd.Timedelta(hours=3)
    for c in STATS:
        mins = j['minutos'].where(j[c].notna())
        tasa = j.groupby('jugador_id')[c].transform(ew) / mins.groupby(j.jugador_id).transform(ew) * 90
        # Incluso los pronósticos que entrenan el calibrador deben tener un prior anterior:
        # la media de toda la temporada de entrenamiento también filtra su futuro interno.
        val, minutos = j[c].where(entrenamiento), mins.where(entrenamiento)
        def prior_de(grupo):
            num,_=medias_previas(val,grupo,j.kickoff_utc,disponibles)
            den,_=medias_previas(minutos,grupo,j.kickoff_utc,disponibles)
            return num/den.replace(0,np.nan)*90
        prior=prior_de(j.posicion).fillna(prior_de(pd.Series('_global',index=j.index)))
        j[f"r_{c}"] = (tasa.fillna(prior) * j["n_prev"] + prior * k) / (j["n_prev"] + k)
    gol_xg = np.where(j["r_xg"].notna(), 0.65 * j["r_xg"].fillna(0) + 0.35 * j["r_goles"], j["r_goles"])
    j["r_gol"] = gol_xg
    for c in ["tiros_puerta", "tiros_totales", "pases_acertados", "faltas_recibidas", "tarjeta", "gol"]:
        j[f"m_{c}"] = j[f"r_{c}"] * j["min_esp"] / 90
    j.attrs['disponibilidad']='condicionado_al_once_reconstruido'
    return j


def kappa_nb(y: np.ndarray, m: np.ndarray) -> float:
    """Dispersión de la binomial negativa por momentos: Var = m + m²/κ."""
    ok = np.isfinite(y) & np.isfinite(m) & (m > 0)
    y, m = y[ok], m[ok]
    exceso = np.mean((y - m) ** 2 - m)
    return float(np.mean(m ** 2) / exceso) if exceso > 0 else 1e6


def p_mas(m: np.ndarray, linea: float, kappa: float | None = None) -> np.ndarray:
    """P(X > linea) con Poisson(m) o BN(m, κ)."""
    k = int(np.floor(linea))
    if kappa is None:
        return poisson.sf(k, m)
    return nbinom.sf(k, kappa, kappa / (kappa + m))


def platt(p: np.ndarray, y: np.ndarray):
    """Recalibración logística sobre logit(p), ajustada con temporadas anteriores; devuelve la función a aplicar."""
    from sklearn.linear_model import LogisticRegression
    ok = np.isfinite(p) & np.isfinite(y)
    lg = lambda q: np.log(np.clip(q, 1e-6, 1 - 1e-6) / (1 - np.clip(q, 1e-6, 1 - 1e-6)))  # noqa: E731
    m = LogisticRegression(C=1e6).fit(lg(p[ok])[:, None], y[ok].astype(int))
    return lambda q: m.predict_proba(lg(np.asarray(q, float))[:, None])[:, 1]
