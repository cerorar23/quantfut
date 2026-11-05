"""Sprint 5, método de quitado de margen por mercado: log-pérdida de cada método contra el resultado real.

    python apps/nba/ops/evaluar_s5.py CARPETA

Usa los cierres de bet365 (ganador, hándicap, total; s3_cierres.csv) y de Pinnacle (ganador; s3_pinnacle.csv) con los resultados de
s3_juegos.csv. En dos resultados los métodos casi coinciden; la diferencia aparece con favoritos fuertes (sesgo favorito-improbable).
"""
import csv
from collections import defaultdict
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nba.v2 import evaluacion, referencia  # noqa: E402


def cargar(carpeta: Path):
    resultado = {}
    for r in csv.DictReader(open(carpeta / "s3_juegos.csv", encoding="utf8")):
        resultado[int(r["partido_id"])] = (float(r["pts_local"]), float(r["pts_visitante"]))
    mercados = defaultdict(dict)
    for r in csv.DictReader(open(carpeta / "s3_cierres.csv", encoding="utf8")):
        clave = ("bet365 " + r["mercado"], int(r["partido_id"]))
        mercados[clave].setdefault("linea", float(r["linea"]) if r["linea"] else None)
        mercados[clave][r["lado"]] = float(r["cuota"])
    for r in csv.DictReader(open(carpeta / "s3_pinnacle.csv", encoding="utf8")):
        clave = ("pinnacle h2h", int(r["partido_id"]))
        mercados[clave].setdefault("linea", None)
        mercados[clave][r["lado"]] = float(r["cuota"])
    return resultado, mercados


def main(carpeta: Path):
    resultado, mercados = cargar(carpeta)
    fechas = {int(r['partido_id']): r['fecha'] for r in csv.DictReader(open(carpeta / 's3_juegos.csv', encoding='utf8'))}
    filas = defaultdict(lambda: defaultdict(list))
    for (nombre, pid), v in mercados.items():
        if pid not in resultado:
            continue
        pl, pv = resultado[pid]
        if nombre.endswith("h2h") and "local" in v and "visit" in v:
            a, b, y = v["local"], v["visit"], float(pl > pv)
        elif nombre.endswith("spreads") and "local" in v and "visit" in v and v["linea"] is not None and v["linea"] % 1 != 0:
            a, b, y = v["local"], v["visit"], float(pl - pv + v["linea"] > 0)
        elif nombre.endswith("totals") and "over" in v and "under" in v and v["linea"] is not None and v["linea"] % 1 != 0:
            a, b, y = v["over"], v["under"], float(pl + pv > v["linea"])
        else:
            continue
        if a <= 1 or b <= 1:
            continue
        filas[nombre]["y"].append(y)
        filas[nombre]["grupos"].append(fechas[pid])
        filas[nombre]["max"].append(max(1 / a, 1 / b) / (1 / a + 1 / b))
        for metodo in referencia.METODOS:
            filas[nombre][metodo].append(referencia.quitar_margen([a, b], metodo)[0])
    informe = {}
    for nombre, d in sorted(filas.items()):
        y = np.array(d["y"])
        informe[nombre] = {"n": len(y), "favorito_medio": float(np.mean(d["max"]))}
        for metodo in referencia.METODOS:
            p = np.array(d[metodo])
            informe[nombre][metodo] = {"logloss": evaluacion.logloss(p, y), "brier": evaluacion.brier(p, y),
                                       "pendiente": evaluacion.pendiente_calibracion(p, y)[0]}
        mejor = min(referencia.METODOS, key=lambda m: informe[nombre][m]["logloss"])
        base = np.array(d["proporcional"])
        informe[nombre]["mejor"] = mejor
        informe[nombre]["dif_brier_mejor_vs_proporcional"] = evaluacion.ic_diferencia(np.array(d[mejor]), base, y, grupos=d['grupos'])
        print(f"{nombre:16s} n={len(y):5d} " + " ".join(f"{m}={informe[nombre][m]['logloss']:.5f}" for m in referencia.METODOS) + f" -> {mejor}")
    (carpeta / "informe_s5_referencia.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
