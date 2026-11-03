"""
Corre una fase del rediseño de fútbol sobre la exportación local y guarda predicciones y métricas.

    PYTHONPATH=src python scripts/rediseno_futbol/correr.py f2 --salida .local/evaluacion_nueva [--datos ...]

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


def modelos_f2(disponibilidad='recepcion') -> dict:
    return {"clima": Climatologia(), "dc_goles": DixonColesRef(xg_blend=0.0,disponibilidad=disponibilidad), "dc_prod": DixonColesRef(xg_blend=0.65,disponibilidad=disponibilidad),
            "pi_goles": PiRatings(objetivo="goles"), "pi_npxg": PiRatings(objetivo="npxg")}


def modelos_f3(disponibilidad: str = 'recepcion') -> dict:
    # Hiperparámetros con la historia anterior a la evaluación (incluye 23/24, la primera con mapa de tiros).
    return {"dc_prod": DixonColesRef(xg_blend=0.65, disponibilidad=disponibilidad),
            "a0_goles": ScoreDriven(EVAL, disponibilidad=disponibilidad),
            "a0_xg": ScoreDriven(EVAL, w_xg=0.65, columna_xg="xg", disponibilidad=disponibilidad),
            "a1_npxg": ScoreDriven(EVAL, w_xg=0.65, columna_xg="npxg_o_xg", disponibilidad=disponibilidad),
            "a2_estado": ScoreDriven(EVAL, w_xg=0.65, columna_xg="npxg_estado_o_xg", disponibilidad=disponibilidad)}


FASES = {"f2": modelos_f2, "f3": modelos_f3, "f4": None}
CONTEOS = {"corners": ["c0_liga", "c1_equipos", "c2_yip"], "yellow": ["c0_liga", "t1_equipos", "t2_arbitro", "t3_dawson"]}
CALIBRAR = {"f2": ["dc_prod"], "f3": ["dc_prod", "a0_goles", "a0_xg", "a1_npxg", "a2_estado"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("fase", choices=sorted(FASES))
    ap.add_argument("--datos", default=".local/rediseno_20261101")
    ap.add_argument('--salida', required=True, help='Carpeta nueva; conserva los resultados anteriores')
    ap.add_argument('--disponibilidad', choices=('recepcion','reconstruida'), default='recepcion')
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    datos = Path(a.datos)
    salida_dir = Path(a.salida)
    salida_dir.mkdir(parents=True, exist_ok=False)
    (salida_dir/'protocolo.json').write_text(json.dumps({'disponibilidad':a.disponibilidad,
        'datos':str(datos.resolve()), 'reserva_2627_ya_observada':True, 'promocion':False},indent=2),encoding='utf-8')
    df = R.tabla_partidos(R.cargar(datos))
    for problema in check_leakage(df):
        print("check_leakage:", problema)
    if a.fase == "f4":
        return correr_conteos(df, datos, salida_dir, a.disponibilidad)
    modelos = FASES[a.fase](a.disponibilidad)
    pred = R.walk_forward(df, modelos, INICIO, disponibilidad=a.disponibilidad)
    (salida_dir/'fallos_ajuste.json').write_text(json.dumps(pred.attrs.get('fallos_ajuste',[]),indent=2),encoding='utf-8')
    for m in CALIBRAR[a.fase]:
        pred = R.calibrar_secuencial(pred, df, m, f"{m}_cal")
    print({m: getattr(o, "hip", None) for m, o in modelos.items() if getattr(o, "hip", None) is not None})
    pred.to_csv(salida_dir / f"pred_{a.fase}.csv.gz", index=False)
    salida = {}
    for tramo, (desde, hasta) in {"seleccion": (EVAL, RESERVA), "reserva_2627": (RESERVA, None)}.items():
        resumen, comp = R.evaluar(pred, df, desde, hasta)
        _, comp_dc = R.evaluar(pred, df, desde, hasta, referencia="dc_prod")
        salida[tramo] = {"resumen": resumen.to_dict("records"), "comparaciones": comp.to_dict("records"),
                         "frente_a_dc_prod": comp_dc.to_dict("records")}
        print(f"\n== {tramo}\n", resumen.round(5).to_string(), "\n", comp.round(5).to_string(),
              "\n", comp_dc.round(5).to_string())
    (salida_dir / f"metricas_{a.fase}.json").write_text(json.dumps(salida, indent=1, default=str), encoding="utf-8")


def correr_conteos(df: pd.DataFrame, datos: Path, salida_dir: Path, disponibilidad: str) -> None:
    d = R.cargar(datos)
    derbis = pd.read_csv(datos / "derbis.csv.gz")
    salida = {}
    for objetivo, variantes in CONTEOS.items():
        L = C.rasgos(df, d.contexto, derbis, d.equipo, objetivo, disponibilidad=disponibilidad)
        pred = C.walk_forward(L, objetivo, variantes, EVAL)
        pred.to_csv(salida_dir / f"pred_f4_{objetivo}.csv.gz", index=False)
        for tramo, (desde, hasta) in {"seleccion": (EVAL, RESERVA), "reserva_2627": (RESERVA, None)}.items():
            res, comp = C.evaluar(pred, L, objetivo, desde, hasta)
            salida[f"{objetivo}_{tramo}"] = {"resumen": res.to_dict("records"), "comparaciones": comp.to_dict("records")}
            print(f"\n== {objetivo} {tramo}\n", res.round(4).to_string(), "\n", comp.round(5).to_string())
    (salida_dir / "metricas_f4.json").write_text(json.dumps(salida, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
