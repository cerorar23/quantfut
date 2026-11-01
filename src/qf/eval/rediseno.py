"""
Banco de pruebas del rediseño de los motores de fútbol (1-nov-2026).

Todos los modelos se miden sobre LAS MISMAS FILAS con el mismo walk-forward: en cada corte semanal cada modelo ve
solo partidos con saque anterior al corte y predice los de la semana siguiente. Lee la exportación de solo lectura
de `scripts/rediseno_futbol/exportar.sh` (tabla única `futbol.dato` + `matches` + `odds_snapshots`); no toca la
base. Plan y criterio en `docs/serie_a_sofascore_rediseno_20261031.md` §0.

Interfaz de un modelo: `ajustar(historia, corte)` y `predecir(partidos)`, que devuelve un DataFrame alineado con
`partidos` con `lam`, `mu`, `rho` (intensidades del marcador) o directamente `p_home`, `p_draw`, `p_away`.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..model.calibration import LambdaCalibrator, probs_1x2
from ..model.devig import devig
from .metrics import brier, diebold_mariano, log_loss, murphy, rps

log = logging.getLogger(__name__)

NUCLEO = ("it.serie_a", "de.bundesliga", "fr.ligue_1", "nl.eredivisie", "pt.primeira", "br.serie_a",
          "gb.premier_league", "es.laliga")
RESULTADOS = ("home", "draw", "away")


@dataclass
class Datos:
    partidos: pd.DataFrame
    tiros: pd.DataFrame
    incidencias: pd.DataFrame
    equipo: pd.DataFrame
    contexto: pd.DataFrame
    cuotas: pd.DataFrame


def cargar(carpeta: str | Path) -> Datos:
    d = Path(carpeta)
    leer = lambda n, **kw: pd.read_csv(d / f"{n}.csv.gz", low_memory=False, **kw)  # noqa: E731
    fechas = ["kickoff_utc", "xg_recorded_at", "result_recorded_at"]
    return Datos(leer("partidos", parse_dates=fechas), leer("tiros"), leer("incidencias"), leer("equipo"),
                 leer("contexto"), leer("cuotas", parse_dates=["captured_at"]))


def mercado_1x2(cuotas: pd.DataFrame, metodo: str = "shin") -> pd.DataFrame:
    """
    Cierre 1X2 sin margen: football-data (Pinnacle hasta el 14-ene-2026, bet365 después) y, donde no hay, el último
    precio de PropLine antes del saque (Pinnacle primero; desde el 23-oct-2026). `casa` dice cuál se usó.
    """
    c = cuotas[cuotas["source"].isin(["football_data", "propline"]) & (cuotas["market"] == "h2h")]
    w = c.pivot_table(index=["match_id", "source", "bookmaker"], columns="selection", values="price").dropna().reset_index()
    orden = {("football_data", "pinnacle"): 0, ("football_data", "bet365"): 1, ("propline", "pinnacle"): 2}
    w["prioridad"] = [orden.get((s, b), 3 if s == "propline" else 9) for s, b in zip(w["source"], w["bookmaker"])]
    w = w.sort_values("prioridad").drop_duplicates("match_id")
    p = np.array([devig([h, d, a], metodo) for h, d, a in w[["home", "draw", "away"]].to_numpy()])
    return pd.DataFrame({"match_id": w["match_id"].to_numpy(), "casa": w["bookmaker"].to_numpy(),
                         "mk_home": p[:, 0], "mk_draw": p[:, 1], "mk_away": p[:, 2],
                         "odd_home": w["home"].to_numpy(), "odd_draw": w["draw"].to_numpy(),
                         "odd_away": w["away"].to_numpy(),
                         "margen": (1 / w[["home", "draw", "away"]]).sum(axis=1).to_numpy() - 1})


def xg_por_estado(tiros: pd.DataFrame, incidencias: pd.DataFrame, peso: float = 0.5) -> pd.DataFrame:
    """
    A2: xG sin penaltis de cada lado con los tiros hechos en estado «roto» descontados (peso `peso`): con dos o
    más goles de diferencia o con distinto número de jugadores (rojas). El estado es el de JUSTO ANTES del tiro.
    """
    t = tiros[tiros["situacion"].ne("penalty") & tiros["xg"].notna()].copy()
    t["clave"] = t["minuto"].fillna(0) + t["anadido"].fillna(0) / 100
    inc = incidencias.copy()
    inc["clave"] = inc["minuto"].fillna(0) + inc["anadido"].fillna(0) / 100
    goles = inc[inc["subtipo"].eq("goal") & ~inc["anulada"].fillna(False).astype(bool)].sort_values("clave")
    rojas = inc[inc["subtipo"].eq("card") & inc["clase"].isin(["red", "yellowRed"])].copy()
    rojas["r_home"] = rojas["side"].eq("home").astype(int)
    rojas["r_away"] = rojas["side"].eq("away").astype(int)
    rojas = rojas.sort_values("clave")
    rojas[["r_home", "r_away"]] = rojas.groupby("match_id")[["r_home", "r_away"]].cumsum()
    t = t.sort_values("clave")
    t = pd.merge_asof(t, goles[["match_id", "clave", "marcador_local", "marcador_visita"]], on="clave",
                      by="match_id", allow_exact_matches=False)
    t = pd.merge_asof(t, rojas[["match_id", "clave", "r_home", "r_away"]], on="clave", by="match_id",
                      allow_exact_matches=False)
    dif = (t["marcador_local"].fillna(0) - t["marcador_visita"].fillna(0)).abs()
    roto = (dif >= 2) | (t["r_home"].fillna(0) != t["r_away"].fillna(0))
    t["npxg_estado"] = t["xg"] * np.where(roto, peso, 1.0)
    return t.groupby(["match_id", "side"])["npxg_estado"].sum().unstack("side").rename(
        columns={"home": "home_npxg_estado", "away": "away_npxg_estado"})


def tabla_partidos(datos: Datos, ligas=NUCLEO) -> pd.DataFrame:
    """Una fila por partido con lo que necesitan los modelos y el mercado de referencia."""
    p = datos.partidos[datos.partidos["league_id"].isin(ligas)].copy()
    p["home_team"] = p["home_team_id"].astype(str)
    p["away_team"] = p["away_team_id"].astype(str)
    p["outcome"] = np.select([p["home_goals"] > p["away_goals"], p["home_goals"] == p["away_goals"]], [0, 1], 2)
    t = datos.tiros
    pen = t["situacion"].eq("penalty")
    agg = (t.assign(npxg=t["xg"].where(~pen, 0.0), pen=pen.astype(int), sin_xg=t["xg"].isna().astype(int))
             .groupby(["match_id", "side"]).agg(npxg=("npxg", "sum"), pens=("pen", "sum"), tiros=("xg", "size"),
                                                tiros_sin_xg=("sin_xg", "sum"), xgot=("xgot", "sum")))
    for side in ("home", "away"):
        a = agg.xs(side, level="side").add_prefix(f"{side}_")
        p = p.merge(a, left_on="match_id", right_index=True, how="left")
    # xG por tiro solo cuando el partido tiene mapa de tiros y todos los tiros traen xG
    completo = (p["home_tiros_sin_xg"] == 0) & (p["away_tiros_sin_xg"] == 0)
    p = p.merge(xg_por_estado(datos.tiros, datos.incidencias), left_on="match_id", right_index=True, how="left")
    for side in ("home", "away"):
        p.loc[~completo, [f"{side}_npxg", f"{side}_npxg_estado"]] = np.nan
        p.loc[completo, f"{side}_npxg_estado"] = p.loc[completo, f"{side}_npxg_estado"].fillna(0.0)
    # A1/A2 con la misma historia que A0-xG: el xG por tiro donde hay mapa de tiros y el del partido antes de él,
    # para que los hiperparámetros se estimen sobre la misma escala y la comparación sea pareja.
    for side in ("home", "away"):
        for col in ("npxg", "npxg_estado"):
            p[f"{side}_{col}_o_xg"] = p[f"{side}_{col}"].fillna(p[f"{side}_xg"])
    p = p.merge(mercado_1x2(datos.cuotas), on="match_id", how="left")
    p["semana"] = p["kickoff_utc"].dt.tz_convert("UTC").dt.tz_localize(None).dt.to_period("W").astype(str)
    return p.sort_values("kickoff_utc").reset_index(drop=True)


def walk_forward(df: pd.DataFrame, modelos: dict, desde, hasta=None, paso_dias: int = 7) -> pd.DataFrame:
    """Predicciones fuera de muestra de cada modelo, en formato largo (una fila por partido y modelo)."""
    corte = pd.Timestamp(desde, tz="UTC")
    fin = pd.Timestamp(hasta, tz="UTC") if hasta else df["kickoff_utc"].max() + pd.Timedelta(seconds=1)
    salida, tiempos = [], {n: 0.0 for n in modelos}
    while corte < fin:
        sig = min(corte + pd.Timedelta(days=paso_dias), fin)
        prueba = df[(df["kickoff_utc"] >= corte) & (df["kickoff_utc"] < sig)]
        if not prueba.empty:
            historia = df[df["kickoff_utc"] < corte]
            for nombre, m in modelos.items():
                t0 = time.perf_counter()
                m.ajustar(historia, corte)
                out = m.predecir(prueba).reset_index(drop=True)
                tiempos[nombre] += time.perf_counter() - t0
                out.insert(0, "match_id", prueba["match_id"].to_numpy())
                out.insert(1, "modelo", nombre)
                salida.append(out)
        corte = sig
    log.info("Tiempo por modelo (s): %s", {k: round(v, 1) for k, v in tiempos.items()})
    pred = pd.concat(salida, ignore_index=True)
    return completar_1x2(pred)


def completar_1x2(pred: pd.DataFrame) -> pd.DataFrame:
    """Deriva el 1X2 de la matriz de marcadores en los modelos que dan intensidades."""
    pred = pred.copy()
    for c in ("p_home", "p_draw", "p_away", "lam", "mu", "rho"):
        if c not in pred:
            pred[c] = np.nan
    falta = pred["p_home"].isna() & pred["lam"].notna()
    for rho, idx in pred[falta].groupby(pred.loc[falta, "rho"].fillna(0.0)).groups.items():
        pred.loc[idx, ["p_home", "p_draw", "p_away"]] = probs_1x2(
            pred.loc[idx, "lam"].to_numpy(), pred.loc[idx, "mu"].to_numpy(), float(rho))
    return pred


def calibrar_secuencial(pred: pd.DataFrame, df: pd.DataFrame, modelo: str, nuevo: str,
                        ventana: int = 3000, minimo: int = 600) -> pd.DataFrame:
    """
    Añade el modelo `nuevo` = `modelo` con el calibrador afín en log-λ de producción, reajustado cada semana SOLO
    con predicciones fuera de muestra de semanas anteriores (las últimas `ventana`). Sin historia suficiente,
    no predice.
    """
    x = pred[pred["modelo"] == modelo].merge(df[["match_id", "kickoff_utc", "semana", "home_goals", "away_goals"]],
                                             on="match_id").sort_values("kickoff_utc")
    filas = []
    for semana, g in x.groupby("semana", sort=False):
        antes = x[x["kickoff_utc"] < g["kickoff_utc"].min()].tail(ventana)
        if len(antes) < minimo:
            continue
        rho = float(antes["rho"].iloc[-1]) if antes["rho"].notna().any() else 0.0
        cal = LambdaCalibrator().fit(antes["lam"].to_numpy(), antes["mu"].to_numpy(), antes["home_goals"].to_numpy(),
                                     antes["away_goals"].to_numpy(), rho=rho)
        lam, mu = cal.apply_vec(g["lam"].to_numpy(), g["mu"].to_numpy())
        filas.append(pd.DataFrame({"match_id": g["match_id"].to_numpy(), "modelo": nuevo, "lam": lam, "mu": mu,
                                   "rho": g["rho"].to_numpy()}))
    return pd.concat([pred, completar_1x2(pd.concat(filas, ignore_index=True))], ignore_index=True)


def inflar_secuencial(pred: pd.DataFrame, df: pd.DataFrame, modelo: str, nuevo: str,
                      ventana: int = 3000, minimo: int = 600) -> pd.DataFrame:
    """Como `calibrar_secuencial`, con la inflación diagonal de Karlis-Ntzoufras ajustada solo con el pasado."""
    from ..model.inflacion_diagonal import InflacionDiagonal
    x = pred[pred["modelo"] == modelo].merge(df[["match_id", "kickoff_utc", "semana", "home_goals", "away_goals"]],
                                             on="match_id").sort_values("kickoff_utc")
    filas = []
    for _, g in x.groupby("semana", sort=False):
        antes = x[x["kickoff_utc"] < g["kickoff_utc"].min()].tail(ventana)
        if len(antes) < minimo:
            continue
        rho = float(antes["rho"].iloc[-1]) if antes["rho"].notna().any() else 0.0
        inf = InflacionDiagonal().fit(antes["lam"].to_numpy(), antes["mu"].to_numpy(), rho,
                                      antes["home_goals"].to_numpy(), antes["away_goals"].to_numpy())
        pr = inf.probs_1x2(g["lam"].to_numpy(), g["mu"].to_numpy(), rho)
        filas.append(pd.DataFrame({"match_id": g["match_id"].to_numpy(), "modelo": nuevo, "p_home": pr[:, 0],
                                   "p_draw": pr[:, 1], "p_away": pr[:, 2], "p_inflacion": inf.p}))
    return pd.concat([pred, pd.concat(filas, ignore_index=True)], ignore_index=True)


def perdidas(probs: np.ndarray, outcome: np.ndarray) -> dict[str, np.ndarray]:
    """Pérdidas por partido (para comparar de forma pareada)."""
    n = len(outcome)
    onehot = np.zeros_like(probs); onehot[np.arange(n), outcome] = 1
    cp, co = np.cumsum(probs, 1), np.cumsum(onehot, 1)
    return {"log": -np.log(np.clip(probs[np.arange(n), outcome], 1e-15, 1)),
            "rps": ((cp[:, :2] - co[:, :2]) ** 2).sum(1) / 2,
            "brier": ((probs - onehot) ** 2).sum(1)}


def evaluar(pred: pd.DataFrame, df: pd.DataFrame, desde, hasta=None, referencia: str = "mercado",
            con_mercado: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Métricas por modelo sobre las filas que TODOS los modelos predijeron (y que tienen mercado, si `con_mercado`).
    Devuelve (resumen, comparaciones pareadas contra `referencia` con Diebold-Mariano por semana).
    """
    base = df[(df["kickoff_utc"] >= pd.Timestamp(desde, tz="UTC"))
              & (df["kickoff_utc"] < (pd.Timestamp(hasta, tz="UTC") if hasta else df["kickoff_utc"].max() + pd.Timedelta(1)))]
    if con_mercado:
        base = base[base["mk_home"].notna()]
    modelos = list(pred["modelo"].unique())
    ancho = {m: pred[pred["modelo"] == m].set_index("match_id")[["p_home", "p_draw", "p_away"]].dropna()
             for m in modelos}
    if con_mercado:
        ancho["mercado"] = base.set_index("match_id")[["mk_home", "mk_draw", "mk_away"]].set_axis(
            ["p_home", "p_draw", "p_away"], axis=1)
    comunes = base["match_id"]
    for a in ancho.values():
        comunes = comunes[comunes.isin(a.index)]
    base = base[base["match_id"].isin(comunes)]
    oc = base["outcome"].to_numpy(dtype=int)
    res, loss = [], {}
    for m, a in ancho.items():
        pr = a.loc[base["match_id"]].to_numpy(dtype=float)
        pr = pr / pr.sum(1, keepdims=True)
        loss[m] = perdidas(pr, oc)
        fila = {"modelo": m, "n": len(oc), "log": log_loss(pr, oc), "rps": rps(pr, oc), "brier": brier(pr, oc)}
        for k, r in enumerate(RESULTADOS):
            mu_ = murphy(pr[:, k], (oc == k).astype(float), score="log")
            fila[f"mcb_{r}"], fila[f"dsc_{r}"] = mu_["mcb"], mu_["dsc"]
        res.append(fila)
    resumen = pd.DataFrame(res).sort_values("log").reset_index(drop=True)
    comp = []
    if referencia in loss:
        for m in loss:
            if m == referencia:
                continue
            for metrica in ("log", "rps"):
                dm = diebold_mariano(loss[m][metrica], loss[referencia][metrica], base["semana"].to_numpy())
                comp.append({"modelo": m, "frente_a": referencia, "metrica": metrica, "delta": dm["delta"],
                             "ic95_bajo": dm["ic95"][0], "ic95_alto": dm["ic95"][1], "t": dm["t"]})
    return resumen, pd.DataFrame(comp)
