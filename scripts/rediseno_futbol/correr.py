"""
Corre una fase del rediseño de fútbol sobre la exportación local y guarda predicciones y métricas.

    PYTHONPATH=src python scripts/rediseno_futbol/correr.py f2 [--datos .local/rediseno_20261101]

Walk-forward semanal desde el 1-jul-2023 (24/25 en adelante se evalúa; lo anterior calienta calibradores y
logits). Selección con 24/25–25/26; 26/27 se reserva y se informa aparte. `check_leakage()` se imprime antes.
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import pandas as pd

from qf.eval import rediseno as R
from qf.eval import rediseno_conteos as C
from qf.eval.backtest import check_leakage
from qf.model.referencias import Climatologia, DixonColesRef, PiRatings
from qf.model.score_driven import ScoreDriven

INICIO = "2023-07-01"
EVAL = "2024-07-01"
RESERVA = "2026-07-01"  # 26/27: solo al final


def modelos_f2() -> dict:
    return {"clima": Climatologia(), "dc_goles": DixonColesRef(xg_blend=0.0), "dc_prod": DixonColesRef(xg_blend=0.65),
            "pi_goles": PiRatings(objetivo="goles"), "pi_npxg": PiRatings(objetivo="npxg")}


def modelos_f3() -> dict:
    # Hiperparámetros con la historia anterior a la evaluación (incluye 23/24, la primera con mapa de tiros).
    return {"dc_prod": DixonColesRef(xg_blend=0.65),
            "a0_goles": ScoreDriven(EVAL),
            "a0_xg": ScoreDriven(EVAL, w_xg=0.65, columna_xg="xg"),
            "a1_npxg": ScoreDriven(EVAL, w_xg=0.65, columna_xg="npxg_o_xg"),
            "a2_estado": ScoreDriven(EVAL, w_xg=0.65, columna_xg="npxg_estado_o_xg")}


FASES = {"f2": modelos_f2, "f3": modelos_f3, "f4": None}
CONTEOS = {"corners": ["c0_liga", "c1_equipos", "c2_yip"], "yellow": ["c0_liga", "t1_equipos", "t2_arbitro", "t3_dawson"]}
CALIBRAR = {"f2": ["dc_prod"], "f3": ["dc_prod", "a0_goles", "a0_xg", "a1_npxg", "a2_estado"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("fase", choices=sorted(FASES))
    ap.add_argument("--datos", default=".local/rediseno_20261101")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    datos = Path(a.datos)
    df = R.tabla_partidos(R.cargar(datos))
    for problema in check_leakage(df):
        print("check_leakage:", problema)
    if a.fase == "f4":
        return correr_conteos(df, datos)
    modelos = FASES[a.fase]()
    pred = R.walk_forward(df, modelos, INICIO)
    for m in CALIBRAR[a.fase]:
        pred = R.calibrar_secuencial(pred, df, m, f"{m}_cal")
    print({m: getattr(o, "hip", None) for m, o in modelos.items() if getattr(o, "hip", None) is not None})
    pred.to_csv(datos / f"pred_{a.fase}.csv.gz", index=False)
    salida = {}
    for tramo, (desde, hasta) in {"seleccion": (EVAL, RESERVA), "reserva_2627": (RESERVA, None)}.items():
        resumen, comp = R.evaluar(pred, df, desde, hasta)
        _, comp_dc = R.evaluar(pred, df, desde, hasta, referencia="dc_prod")
        salida[tramo] = {"resumen": resumen.to_dict("records"), "comparaciones": comp.to_dict("records"),
                         "frente_a_dc_prod": comp_dc.to_dict("records")}
        print(f"\n== {tramo}\n", resumen.round(5).to_string(), "\n", comp.round(5).to_string(),
              "\n", comp_dc.round(5).to_string())
    (datos / f"metricas_{a.fase}.json").write_text(json.dumps(salida, indent=1, default=str), encoding="utf-8")


def correr_conteos(df: pd.DataFrame, datos: Path) -> None:
    d = R.cargar(datos)
    derbis = pd.read_csv(datos / "derbis.csv.gz")
    salida = {}
    for objetivo, variantes in CONTEOS.items():
        L = C.rasgos(df, d.contexto, derbis, d.equipo, objetivo)
        pred = C.walk_forward(L, objetivo, variantes, EVAL)
        pred.to_csv(datos / f"pred_f4_{objetivo}.csv.gz", index=False)
        for tramo, (desde, hasta) in {"seleccion": (EVAL, RESERVA), "reserva_2627": (RESERVA, None)}.items():
            res, comp = C.evaluar(pred, L, objetivo, desde, hasta)
            salida[f"{objetivo}_{tramo}"] = {"resumen": res.to_dict("records"), "comparaciones": comp.to_dict("records")}
            print(f"\n== {objetivo} {tramo}\n", res.round(4).to_string(), "\n", comp.round(5).to_string())
    (datos / "metricas_f4.json").write_text(json.dumps(salida, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
