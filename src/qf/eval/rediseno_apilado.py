"""
Apilado del rediseño de fútbol: árboles potenciados (LightGBM) sobre las salidas de los modelos base y rasgos
PREVIOS al partido, con SHAP para auditar qué mueve cada predicción.

Origen: Bunker, Yeung y Fujii 2024 (árboles potenciados sobre ratings, lo mejor con datos solo de goles; con
estadísticas de partido «no está claro») y la propuesta del titular del 1-nov (apilar Dixon-Coles/score-driven con
LightGBM y explicar con SHAP). Se mide contra el mejor modelo único y contra el mercado, sobre las mismas filas.

Todo rasgo es previo: medias exponenciales de partidos ANTERIORES de cada equipo (desplazadas una posición) y
probabilidades fuera de muestra de los modelos base. El modelo se reajusta cada `paso_dias` solo con partidos de
antes del corte. Requiere `lightgbm` y `shap` (entorno de investigación aparte, no el del worker).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .rediseno import Datos

DEFENSA = ["m_acciones_def"]


def rasgos_equipo(df: pd.DataFrame, datos: Datos, vida: float = 6.0) -> pd.DataFrame:
    """Rasgos previos por partido: medias exponenciales de cada equipo (local y visitante) y días de descanso."""
    eq = datos.equipo[datos.equipo["periodo"] == 0].copy()
    # DEFCON (Kim et al. 2025): contar acciones defensivas mide EXPOSICIÓN, no calidad; aquí se pone a prueba
    eq["acciones_def"] = eq[["entradas", "intercepciones", "despejes"]].sum(axis=1, min_count=1)
    est = eq.pivot_table(index="match_id", columns="side",
                         values=["grandes_ocasiones_creadas", "posesion", "tiros_dentro_area", "faltas",
                                 "acciones_def"])
    est.columns = [f"{s}_{c}" for c, s in est.columns]
    base = df.merge(est, left_on="match_id", right_index=True, how="left")
    filas = []
    for side, opp in (("home", "away"), ("away", "home")):
        filas.append(pd.DataFrame({
            "match_id": base["match_id"], "kickoff_utc": base["kickoff_utc"], "equipo": base[f"{side}_team"],
            "local": int(side == "home"),
            "goles": base[f"{side}_goals"], "goles_c": base[f"{opp}_goals"],
            "xg": base[f"{side}_xg"], "xg_c": base[f"{opp}_xg"],
            "npxg": base[f"{side}_npxg"], "npxg_c": base[f"{opp}_npxg"],
            "go": base.get(f"{side}_grandes_ocasiones_creadas"), "go_c": base.get(f"{opp}_grandes_ocasiones_creadas"),
            "posesion": base.get(f"{side}_posesion"), "tiros_area": base.get(f"{side}_tiros_dentro_area"),
            "tiros_area_c": base.get(f"{opp}_tiros_dentro_area"), "faltas": base.get(f"{side}_faltas"),
            "acciones_def": base.get(f"{side}_acciones_def")}))
    L = pd.concat(filas, ignore_index=True).sort_values(["kickoff_utc", "match_id"]).reset_index(drop=True)
    g = L.groupby("equipo")
    medias = [c for c in L.columns if c not in ("match_id", "kickoff_utc", "equipo", "local")]
    for c in medias:
        L[f"m_{c}"] = g[c].transform(lambda s: s.ewm(halflife=vida, ignore_na=True).mean().shift(1))
    L["descanso"] = g["kickoff_utc"].diff().dt.total_seconds() / 86400
    L["n_previos"] = g.cumcount()
    cols = [f"m_{c}" for c in medias] + ["descanso", "n_previos"]
    h = L[L["local"] == 1].set_index("match_id")[cols]
    a = L[L["local"] == 0].set_index("match_id")[cols]
    out = h.add_prefix("l_").join(a.add_prefix("v_"))
    for c in cols:
        out[f"d_{c}"] = out[f"l_{c}"] - out[f"v_{c}"]
    return out


def matriz(df: pd.DataFrame, rasgos: pd.DataFrame, base_pred: pd.DataFrame, modelos_base: list[str],
           con_mercado: bool, sin: list[str] = ()) -> pd.DataFrame:
    X = df[["match_id", "kickoff_utc", "semana", "league_id", "outcome", "mk_home", "mk_draw", "mk_away"]] \
        .merge(rasgos, left_on="match_id", right_index=True, how="left")
    for m in modelos_base:
        b = base_pred[base_pred["modelo"] == m].set_index("match_id")
        cols = [c for c in ("p_home", "p_draw", "p_away", "lam", "mu") if b[c].notna().any()]
        X = X.merge(b[cols].add_prefix(f"{m}_"), left_on="match_id", right_index=True, how="left")
    X["liga"] = X["league_id"].astype("category")
    if not con_mercado:
        X = X.drop(columns=["mk_home", "mk_draw", "mk_away"])
    quitar = [c for c in X.columns if any(c.endswith(s) or c.startswith(f"l_{s}") or c.startswith(f"v_{s}")
                                          or c.startswith(f"d_{s}") for s in sin)]
    return X.drop(columns=quitar)


def columnas(X: pd.DataFrame) -> list[str]:
    return [c for c in X.columns if c not in ("match_id", "kickoff_utc", "semana", "league_id", "outcome")]


def walk_forward(X: pd.DataFrame, desde, nombre: str, paso_dias: int = 28, inicio_entreno=None,
                 tipo: str = "lgbm") -> tuple[pd.DataFrame, object, list[str]]:
    """Predicciones fuera de muestra; devuelve también el último modelo (para SHAP) y sus columnas."""
    import lightgbm as lgb
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.impute import SimpleImputer

    cols = columnas(X)
    corte = pd.Timestamp(desde, tz="UTC"); fin = X["kickoff_utc"].max() + pd.Timedelta(seconds=1)
    ini = pd.Timestamp(inicio_entreno, tz="UTC") if inicio_entreno else X["kickoff_utc"].min()
    salida, modelo = [], None
    while corte < fin:
        sig = corte + pd.Timedelta(days=paso_dias)
        ent = X[(X["kickoff_utc"] < corte) & (X["kickoff_utc"] >= ini)]
        pru = X[(X["kickoff_utc"] >= corte) & (X["kickoff_utc"] < sig)]
        if len(pru):
            if tipo == "lgbm":
                modelo = lgb.LGBMClassifier(objective="multiclass", n_estimators=400, learning_rate=0.02,
                                            num_leaves=15, min_child_samples=80, subsample=0.8, subsample_freq=1,
                                            colsample_bytree=0.7, reg_lambda=5.0, verbose=-1)
                modelo.fit(ent[cols], ent["outcome"])
                p = modelo.predict_proba(pru[cols])
            else:
                num = [c for c in cols if c != "liga"]
                modelo = make_pipeline(SimpleImputer(), StandardScaler(), LogisticRegression(C=0.1, max_iter=2000))
                modelo.fit(ent[num], ent["outcome"])
                p = modelo.predict_proba(pru[num])
            salida.append(pd.DataFrame({"match_id": pru["match_id"].to_numpy(), "modelo": nombre,
                                        "p_home": p[:, 0], "p_draw": p[:, 1], "p_away": p[:, 2]}))
        corte = sig
    return pd.concat(salida, ignore_index=True), modelo, cols


def shap_resumen(modelo, X: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, np.ndarray]:
    """|SHAP| medio por rasgo y resultado (escala log-odds del árbol), sobre las filas `X`."""
    import shap
    sv = shap.TreeExplainer(modelo).shap_values(X[cols])
    sv = np.stack(sv, axis=-1) if isinstance(sv, list) else sv  # (n, rasgos, clases)
    res = pd.DataFrame({"rasgo": cols, "local": np.abs(sv[:, :, 0]).mean(0), "empate": np.abs(sv[:, :, 1]).mean(0),
                        "visita": np.abs(sv[:, :, 2]).mean(0)})
    res["total"] = res[["local", "empate", "visita"]].sum(1)
    return res.sort_values("total", ascending=False).reset_index(drop=True), sv
