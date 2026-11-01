"""
Pruebas del segundo lote de estudios (1-nov-2026) sobre las predicciones fuera de muestra ya guardadas:

- Inflación diagonal (Karlis-Ntzoufras) encima de Dixon-Coles y de A0 con xG.
- Mezcla con el mercado (Benter), peso estimado cada semana solo con el pasado.
- Kelly fraccional (0,25) contra el cierre real (Pinnacle hasta ene-2026, bet365 después), como diagnóstico.

    PYTHONPATH=src python scripts/rediseno_futbol/extras.py [--datos ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from qf.eval import rediseno as R
from qf.eval.rediseno_kelly import mezcla_benter, simular

EVAL, RESERVA = "2024-07-01", "2026-07-01"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datos", default=".local/rediseno_20261101")
    a = ap.parse_args()
    d = Path(a.datos)
    df = R.tabla_partidos(R.cargar(d))
    pred = pd.read_csv(d / "pred_f3.csv.gz")
    pred = pred[pred["modelo"].isin(["dc_prod", "a0_xg"])]
    for m in ("dc_prod", "a0_xg"):
        pred = R.inflar_secuencial(pred, df, m, f"{m}_infl")
        pred = pd.concat([pred, mezcla_benter(pred, df, m, f"{m}_benter")], ignore_index=True)
    ruta_ap = d / "pred_apilado.csv.gz"
    if ruta_ap.exists():
        ap_ = pd.read_csv(ruta_ap)
        pred = pd.concat([pred, ap_[ap_["modelo"].str.startswith(("gbm_", "logit_"))]], ignore_index=True)
    pred.to_csv(d / "pred_extras.csv.gz", index=False)
    salida = {}
    for tramo, (desde, hasta) in {"seleccion": (EVAL, RESERVA), "reserva_2627": (RESERVA, None)}.items():
        res, comp = R.evaluar(pred, df, desde, hasta)
        _, comp_a0 = R.evaluar(pred, df, desde, hasta, referencia="a0_xg")
        sub = df[(df["kickoff_utc"] >= pd.Timestamp(desde, tz="UTC"))
                 & (df["kickoff_utc"] < (pd.Timestamp(hasta, tz="UTC") if hasta else df["kickoff_utc"].max() + pd.Timedelta(1)))]
        kelly = {}
        for m in pred["modelo"].unique():
            kelly[m] = simular(sub, pred[pred["modelo"] == m][["match_id", "p_home", "p_draw", "p_away"]])
        mercado = sub[["match_id", "mk_home", "mk_draw", "mk_away"]].set_axis(["match_id", "p_home", "p_draw", "p_away"], axis=1)
        kelly["mercado_sin_margen"] = simular(sub, mercado)
        pinf = pred[pred["modelo"].str.endswith("_infl")].groupby("modelo")["p_inflacion"].mean().to_dict()
        wben = pred[pred["modelo"].str.endswith("_benter")].groupby("modelo")["w_modelo"].mean().to_dict()
        salida[tramo] = {"resumen": res.to_dict("records"), "frente_a_mercado": comp.to_dict("records"),
                         "frente_a_a0_xg": comp_a0.to_dict("records"), "kelly": kelly,
                         "p_inflacion_media": pinf, "w_benter_medio": wben}
        print(f"\n== {tramo}\n", res.round(5).to_string(), "\n", comp.round(5).to_string(), "\n",
              comp_a0.round(5).to_string(), "\n p_inflacion", pinf, "\n w_benter", wben)
        print(pd.DataFrame(kelly).T.round(4).to_string())
    (d / "metricas_extras.json").write_text(json.dumps(salida, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
