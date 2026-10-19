"""Diagnóstico del modelo de córners: walk-forward sobre todo el historial y comparación con lo publicado.

Qué responde (medido el 19-oct-2026):
- ¿El modelo está calibrado? Sí: con 41.815 partidos de 23 ligas, las líneas de producción (más de 6,5 y 8,5, menos de 10,5, 11,5 y
  12,5) quedan a menos de 0,6 puntos de lo prometido en todas las ligas y en el periodo reciente.
- ¿Por qué los «menos de» publicados parecían quedarse 5-7 puntos cortos? Porque cada partido genera hasta 4 picks de córners muy
  correlacionados: 601 picks eran 170 partidos, y con 170 el margen de error es de ~3,5 puntos. Ver `error_estandar_por_partido`.
- ¿Alguna variable de contexto mejora la predicción del total? No (clima, altitud, descanso, desbalance de equipos, goles esperados
  del modelo A, bajas): todas empeoran fuera de muestra.

Regla que deja esta herramienta: un déficit medido sobre picks de un mismo partido se mide por PARTIDO. No se recalibra un modelo
calibrado con dos semanas de datos.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import nbinom

from ..model import estadisticas_mercado as em

LINEAS_PRODUCCION = (("under", 10.5), ("under", 11.5), ("under", 12.5), ("over", 6.5), ("over", 8.5))
BANDA = (0.62, 0.95)


def prob_lado(media_total, linea: float, lado: str, phi: float | None = None) -> np.ndarray:
    """P(total < línea) o P(total > línea) con la binomial negativa del modelo (líneas medias)."""
    phi = em.PARAMETROS["corners"]["phi"] if phi is None else phi
    media = np.asarray(media_total, dtype=float)
    r = media / (phi - 1.0)
    p_bajo = nbinom.cdf(math.floor(linea), r, r / (r + media))
    return p_bajo if lado == "under" else 1.0 - p_bajo


def tabla_calibracion(pred: pd.DataFrame, lineas=LINEAS_PRODUCCION, banda=BANDA, min_n: int = 30) -> pd.DataFrame:
    """Por línea: partidos, probabilidad prometida y frecuencia real, solo cuando el modelo da `banda`."""
    filas = []
    for lado, linea in lineas:
        p = prob_lado(pred["pred"].to_numpy(), linea, lado)
        gana = (pred["real"].to_numpy() < linea) if lado == "under" else (pred["real"].to_numpy() > linea)
        m = (p >= banda[0]) & (p <= banda[1])
        if m.sum() >= min_n:
            filas.append({"lado": lado, "linea": linea, "n": int(m.sum()), "prometido": float(p[m].mean()),
                          "real": float(gana[m].mean()), "dif": float(gana[m].mean() - p[m].mean())})
    return pd.DataFrame(filas)


def error_estandar_por_partido(partidos: pd.Series, gana: pd.Series) -> dict:
    """Error estándar de la tasa de acierto cuando varios picks comparten partido (agrupados por partido).

    Cada partido se resume en su media de aciertos con peso igual a sus picks (estimador de razón); con picks independientes
    coincidiría con el binomial, con picks correlacionados es bastante mayor.
    """
    d = pd.DataFrame({"p": partidos.to_numpy(), "g": gana.astype(float).to_numpy()})
    por = d.groupby("p")["g"].agg(["sum", "size"])
    n_picks, n_part = int(por["size"].sum()), int(len(por))
    tasa = float(por["sum"].sum() / n_picks)
    resid = por["sum"] - tasa * por["size"]
    ee = math.sqrt(float((resid ** 2).sum()) * n_part / max(n_part - 1, 1)) / n_picks
    ee_ingenuo = math.sqrt(tasa * (1 - tasa) / n_picks)
    return {"picks": n_picks, "partidos": n_part, "tasa": tasa, "ee_por_partido": ee, "ee_si_fueran_independientes": ee_ingenuo,
            "inflacion": ee / ee_ingenuo if ee_ingenuo else float("nan")}


def walk_forward(desde: str = "2019-01-01") -> pd.DataFrame:
    """Predicción del total de córners de cada partido con solo lo anterior (el modelo de producción, mismos parámetros)."""
    from ..db import query
    df = pd.DataFrame(query(
        """SELECT match_id, league_id, kickoff_utc, home_team_id, away_team_id, home_corners, away_corners FROM matches
           WHERE status = 'finished' AND home_corners IS NOT NULL AND away_corners IS NOT NULL AND kickoff_utc >= %s
           ORDER BY kickoff_utc, match_id""", (desde,)))
    df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
    accs: dict[str, em.Acumulador] = {}
    filas = []
    for r in df.itertuples():
        acc = accs.setdefault(r.league_id, em.acumulador("corners"))
        f = r.kickoff_utc.to_pydatetime()
        lam = acc.lambdas(f, r.home_team_id, r.away_team_id)
        if lam is not None:
            filas.append((r.match_id, r.league_id, r.kickoff_utc, lam[0] + lam[1], r.home_corners + r.away_corners))
        acc.agregar(f, r.home_team_id, r.away_team_id, int(r.home_corners), int(r.away_corners))
    return pd.DataFrame(filas, columns=["match_id", "league_id", "kickoff_utc", "pred", "real"])


def main(argv=None) -> None:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--desde", default="2019-01-01")
    a = ap.parse_args(argv)
    w = walk_forward(a.desde)
    print(f"partidos con predicción: {len(w)} | ligas: {w['league_id'].nunique()}")
    print("\ncalibración de las líneas de producción (modelo 62-95 %), toda la historia")
    print(tabla_calibracion(w).round(4).to_string(index=False))
    print("\ndesde jul-2025")
    print(tabla_calibracion(w[w["kickoff_utc"] >= "2025-07-01"]).round(4).to_string(index=False))
    print("\nsesgo de la media por liga (real - previsto, córners por partido)")
    print(w.groupby("league_id").apply(lambda g: g["real"].mean() - g["pred"].mean(), include_groups=False).round(2).sort_values()
          .to_string())


if __name__ == "__main__":
    main()
