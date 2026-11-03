"""
Apilado LightGBM + SHAP del rediseño de fútbol (propuesta del titular, 1-nov-2026).

    PYTHONPATH=src .local/venv_rediseno/Scripts/python scripts/rediseno_futbol/apilado.py [--datos ...]

1. Modelos base fuera de muestra desde jul-2019 (walk-forward semanal): Dixon-Coles de producción, pi-ratings con
   xG sin penaltis y A0 score-driven con xG (hiperparámetros estimados solo con la historia anterior a jul-2019).
2. Rasgos previos de equipo (medias exponenciales desplazadas) y descanso.
3. Variantes (registradas: 5): gbm_rasgos, gbm_apilado, gbm_apilado_sin_def (ablación DEFCON), logit_apilado,
   gbm_apilado_mercado. Reajuste cada 28 días; entrenamiento desde ene-2020.
4. Evaluación en las mismas filas que el mercado; selección 24/25–25/26 y reserva 26/27 aparte.
5. SHAP del último modelo: importancia global y explicación de los 5 partidos con peor log-loss.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from qf.eval import rediseno as R
from qf.eval import rediseno_apilado as A
from qf.model.referencias import DixonColesRef, PiRatings
from qf.model.score_driven import ScoreDriven

BASE_DESDE = "2019-07-01"
ENTRENO_DESDE = "2020-01-01"
EVAL, RESERVA = "2024-07-01", "2026-07-01"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=".local/rediseno_20261101")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    datos_dir = Path(a.datos)
    datos = R.cargar(datos_dir)
    df = R.tabla_partidos(datos)

    ruta_base = datos_dir / "pred_base_2019.csv.gz"
    if ruta_base.exists():
        base = pd.read_csv(ruta_base)
    else:
        base = R.walk_forward(df, {"dc_prod": DixonColesRef(xg_blend=0.65), "pi_npxg": PiRatings(objetivo="npxg"),
                                   "a0_xg": ScoreDriven(BASE_DESDE, w_xg=0.65, columna_xg="xg")}, BASE_DESDE)
        base.to_csv(ruta_base, index=False)
    modelos_base = ["dc_prod", "pi_npxg", "a0_xg"]

    rasgos = A.rasgos_equipo(df, datos)
    variantes = {
        "gbm_rasgos": dict(modelos=[], mercado=False, sin=()),
        "gbm_apilado": dict(modelos=modelos_base, mercado=False, sin=()),
        "gbm_apilado_sin_def": dict(modelos=modelos_base, mercado=False, sin=A.DEFENSA),
        "logit_apilado": dict(modelos=modelos_base, mercado=False, sin=(), tipo="logit"),
        "gbm_apilado_mercado": dict(modelos=modelos_base, mercado=True, sin=()),
    }
    preds, ultimos = [base], {}
    for nombre, v in variantes.items():
        X = A.matriz(df, rasgos, base, v["modelos"], v["mercado"], v["sin"])
        p, modelo, cols = A.walk_forward(X, EVAL, nombre, inicio_entreno=ENTRENO_DESDE, tipo=v.get("tipo", "lgbm"))
        preds.append(p)
        ultimos[nombre] = (modelo, cols, X)
        logging.info("%s: %d predicciones, %d rasgos", nombre, len(p), len(cols))
    pred = pd.concat(preds, ignore_index=True)
    pred.to_csv(datos_dir / "pred_apilado.csv.gz", index=False)

    salida = {}
    for tramo, (desde, hasta) in {"seleccion": (EVAL, RESERVA), "reserva_2627": (RESERVA, None)}.items():
        res, comp = R.evaluar(pred, df, desde, hasta)
        _, comp_a0 = R.evaluar(pred, df, desde, hasta, referencia="a0_xg")
        salida[tramo] = {"resumen": res.to_dict("records"), "frente_a_mercado": comp.to_dict("records"),
                         "frente_a_a0_xg": comp_a0.to_dict("records")}
        print(f"\n== {tramo}\n", res.round(5).to_string(), "\n", comp.round(5).to_string(), "\n",
              comp_a0.round(5).to_string())

    # SHAP del último modelo sobre las filas evaluadas (explicación, no evaluación)
    for nombre in ("gbm_apilado", "gbm_apilado_mercado"):
        modelo, cols, X = ultimos[nombre]
        ev = X[X["kickoff_utc"] >= pd.Timestamp(EVAL, tz="UTC")]
        imp, sv = A.shap_resumen(modelo, ev, cols)
        imp.to_csv(datos_dir / f"shap_{nombre}.csv", index=False)
        salida[f"shap_{nombre}"] = imp.head(25).to_dict("records")
        print(f"\n== SHAP {nombre}\n", imp.head(25).round(4).to_string())
        if nombre == "gbm_apilado":
            p = pred[pred["modelo"] == nombre].set_index("match_id").loc[ev["match_id"]]
            ll = -np.log(np.clip(p[["p_home", "p_draw", "p_away"]].to_numpy()[np.arange(len(ev)),
                                                                             ev["outcome"].to_numpy()], 1e-15, 1))
            peores = np.argsort(-ll)[:5]
            auditoria = []
            for i in peores:
                k = int(ev["outcome"].iloc[i])
                top = sorted(zip(cols, sv[i, :, k]), key=lambda t: -abs(t[1]))[:6]
                auditoria.append({"match_id": ev["match_id"].iloc[i], "resultado": k, "log_loss": float(ll[i]),
                                  "p_resultado": float(np.exp(-ll[i])),
                                  "rasgos": [(c, round(float(v), 3)) for c, v in top]})
            salida["auditoria_peores"] = auditoria
            print("\n== Auditoría de los 5 peores\n", json.dumps(auditoria, indent=1, ensure_ascii=False))
    (datos_dir / "metricas_apilado.json").write_text(json.dumps(salida, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
