"""
Ajuste por competición de la primera mitad (9-nov-2026, decisión del titular tras docs/hipotesis_mercados_20261109.md).

Calcula, con las predicciones FUERA de muestra del walk-forward (λ y μ del Dixon-Coles) y los goles al descanso reales, una recalibración logística
de «gol en 1T» y de «ambos anotan en 1T»:   logit(p') = pendiente · logit(p) + intercepto(competición),   con p = `model/primer_tiempo.probs` de proporción fija.
La pendiente es común y el intercepto es propio de cada competición (regularizado: pocas filas ⇒ se acerca a la media). El resultado se escribe como constantes
en `src/qf/model/ajuste_1t_datos.py`, que `model/primer_tiempo.probs(liga=...)` aplica. Cambia la salida, no la matriz de marcadores ni el modelo de goles.

    ejecutar.sh .local/entreno_AAAAMMDD qf.eval.ajuste_primer_tiempo --oos .local/backtest_oos_2024/pit_oos.csv --escribir src/qf/model/ajuste_1t_datos.py

Reajuste: repetir tras cada reentreno mensual con el walk-forward actualizado. Es un ajuste pequeño (en el walk-forward mejoró el Brier −0,00041).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

MIN_FILAS_LIGA = 150     # una competición con menos filas no recibe ajuste (se queda con la proporción fija)
C_REG = 1.0              # misma regularización que se midió en el walk-forward


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def preparar(oos: pd.DataFrame, ht: pd.DataFrame) -> pd.DataFrame:
    """Filas con ambos equipos conocidos, goles al descanso y las probabilidades de proporción fija (sin ajuste)."""
    from ..model import primer_tiempo as m1t
    o = oos[oos["both_known"].astype(bool)] if "both_known" in oos else oos
    o = o.merge(ht, on="match_id", how="inner").dropna(subset=["home_goals_ht", "away_goals_ht"]).reset_index(drop=True)
    p = [m1t.probs(a, b) for a, b in zip(o["lam"], o["mu"])]
    o["p_gol"] = [x["gol_1t_si"] for x in p]
    o["p_ambos"] = [x["ambos_1t_si"] for x in p]
    o["y_gol"] = ((o["home_goals_ht"] + o["away_goals_ht"]) > 0).astype(float)
    o["y_ambos"] = ((o["home_goals_ht"] > 0) & (o["away_goals_ht"] > 0)).astype(float)
    return o


def ajustar(filas: pd.DataFrame, min_filas: int = MIN_FILAS_LIGA, c: float = C_REG) -> dict:
    """Pendiente común e intercepto por competición para cada mercado. Devuelve el diccionario que se escribe en `ajuste_1t_datos.py`."""
    from sklearn.linear_model import LogisticRegression
    cuenta = filas["league_id"].value_counts()
    ligas = sorted(l for l, n in cuenta.items() if n >= min_filas)
    if not ligas:   # ninguna competición con filas suficientes: nada que ajustar, todas quedan con la proporción fija
        return {"pendiente": {}, "intercepto": {}, "meta": {"filas": 0, "ligas": 0, "desde": None, "hasta": None, "min_filas_liga": min_filas,
                                                              "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}}
    f = filas[filas["league_id"].isin(ligas)]
    dummies = np.stack([(f["league_id"].to_numpy() == l).astype(float) for l in ligas], axis=1)
    out = {"pendiente": {}, "intercepto": {l: {} for l in ligas}}
    for clave, p, y in (("gol", "p_gol", "y_gol"), ("ambos", "p_ambos", "y_ambos")):
        X = np.hstack([_logit(f[p])[:, None], dummies])
        m = LogisticRegression(C=c, max_iter=1000).fit(X, f[y])
        out["pendiente"][clave] = float(m.coef_[0][0])
        for i, l in enumerate(ligas):
            out["intercepto"][l][clave] = float(m.intercept_[0] + m.coef_[0][1 + i])
    out["meta"] = {"filas": int(len(f)), "ligas": len(ligas), "desde": str(pd.to_datetime(f["kickoff_utc"]).min().date()),
                   "hasta": str(pd.to_datetime(f["kickoff_utc"]).max().date()), "min_filas_liga": min_filas,
                   "generado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    return out


def resumen_en_muestra(filas: pd.DataFrame, ajuste: dict) -> dict:
    """Comprobación EN MUESTRA (no es evidencia: la medición honesta es el walk-forward de hipotesis_mercados)."""
    from ..model import primer_tiempo as m1t
    ajustado = [m1t.ajustar_probs({"gol_1t_si": a, "ambos_1t_si": b}, l, ajuste) for a, b, l in zip(filas["p_gol"], filas["p_ambos"], filas["league_id"])]
    g = np.array([x["gol_1t_si"] for x in ajustado])
    a = np.array([x["ambos_1t_si"] for x in ajustado])
    return {"brier_gol": {"fijo": float(((filas["p_gol"] - filas["y_gol"]) ** 2).mean()), "ajustado": float(((g - filas["y_gol"]) ** 2).mean())},
            "brier_ambos": {"fijo": float(((filas["p_ambos"] - filas["y_ambos"]) ** 2).mean()), "ajustado": float(((a - filas["y_ambos"]) ** 2).mean())}}


def escribir_modulo(ajuste: dict, ruta: Path) -> None:
    m = ajuste["meta"]
    cuerpo = json.dumps({"pendiente": ajuste["pendiente"], "intercepto": ajuste["intercepto"]}, ensure_ascii=False, indent=4, sort_keys=True)
    ruta.write_text(
        '"""Ajuste por competición de la primera mitad. GENERADO por `qf.eval.ajuste_primer_tiempo`: no editar a mano.\n\n'
        f"Ajustado con {m['filas']} partidos fuera de muestra de {m['ligas']} competiciones ({m['desde']} a {m['hasta']}); generado {m['generado']}.\n"
        "logit(p') = pendiente · logit(p) + intercepto[competición]. Una competición que no figura aquí se queda con la proporción fija.\n"
        'Ver docs/hipotesis_mercados_20261109.md.\n"""\n'
        f"META = {json.dumps(m, ensure_ascii=False)}\n"
        f"AJUSTE = {cuerpo}\n", encoding="utf-8")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--oos", default=".local/backtest_oos_2024/pit_oos.csv")
    ap.add_argument("--escribir", help="ruta de src/qf/model/ajuste_1t_datos.py")
    a = ap.parse_args(argv)
    from ..db import query
    oos = pd.read_csv(a.oos, parse_dates=["kickoff_utc"])
    ht = pd.DataFrame(query("SELECT match_id, home_goals_ht, away_goals_ht FROM matches "
                            "WHERE status = 'finished' AND home_goals_ht IS NOT NULL AND away_goals_ht IS NOT NULL"))
    filas = preparar(oos, ht)
    aj = ajustar(filas)
    print(json.dumps({"meta": aj["meta"], "pendiente": aj["pendiente"],
                      "intercepto_liga_mx": aj["intercepto"].get("mx.liga_mx"), "intercepto_champions": aj["intercepto"].get("eu.ucl"),
                      "en_muestra": resumen_en_muestra(filas, aj)}, ensure_ascii=False, indent=1))
    if a.escribir:
        escribir_modulo(aj, Path(a.escribir))
        print("escrito", a.escribir)


if __name__ == "__main__":
    main(sys.argv[1:])
