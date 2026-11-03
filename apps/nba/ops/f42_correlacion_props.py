"""F4.2 — ¿importa simular los props junto con el resultado del partido? Mide la dependencia entre el error de un prop y el del partido.

    python apps/nba/ops/f42_correlacion_props.py CARPETA   (necesita filas_props.json de evaluar_s4.py y predicciones_s3b.json de evaluar_s3b.py)

Para cada fila jugador-partido de la temporada de prueba: error del prop (real − pronóstico) frente al error del total y del margen del partido, y frente a lo
«reñido» que resultó (|margen real|). Si las dependencias fueran ≈ 0, simular por separado sería exacto también para combinaciones; si no, los marginales
siguen siendo correctos pero una probabilidad conjunta (prop Y partido) no se puede obtener multiplicando.
"""
import json
from pathlib import Path
import sys

import numpy as np


def main(carpeta: Path):
    sys.stdout.reconfigure(encoding="utf8")
    props = json.loads((carpeta / "filas_props.json").read_text(encoding="utf8"))
    partidos = {g["pid"]: g for g in json.loads((carpeta / "predicciones_s3b.json").read_text(encoding="utf8")) if g["temporada"] == "2025-26"}
    pid = np.array(props["pid"])
    ok = np.array([p in partidos for p in pid])
    g = [partidos[p] for p in pid[ok]]
    err_total = np.array([x["pl"] + x["pv"] - (x["equipo_mu"][0] + x["equipo_mu"][1]) for x in g])
    err_margen = np.array([x["pl"] - x["pv"] - ((x["equipo_mu"][0] - x["equipo_mu"][1]) + x["jugadores_margen"]) / 2 for x in g])
    abs_margen = np.abs(np.array([x["pl"] - x["pv"] for x in g]))
    minutos = np.array(props["minutos_esperados"])[ok]
    print(f"{ok.sum():,} filas jugador-partido, {len(set(pid[ok]))} partidos")
    print("| Prop | corr con el error del total | corr con |margen real| (partido desigual) | corr con |margen| solo titulares (≥ 28 min esperados) |")
    print("|---|---|---|---|")
    for nombre in ("puntos", "rebotes", "asistencias", "triples"):
        r = np.array(props[nombre]["y"])[ok] - np.array(props[nombre]["mu"])[ok]
        tit = minutos >= 28
        print(f"| {nombre} | {np.corrcoef(r, err_total)[0, 1]:+.3f} | {np.corrcoef(r, abs_margen)[0, 1]:+.3f} | {np.corrcoef(r[tit], abs_margen[tit])[0, 1]:+.3f} |")
    # magnitud práctica: «puntos del jugador por encima de lo esperado» y «total del partido por encima de lo esperado» (cada uno ≈ 50 %)
    r = np.array(props["puntos"]["y"])[ok] - np.array(props["puntos"]["mu"])[ok]
    a, b = r > 0, err_total > 0
    conjunta = np.mean(a & b)
    print(f"P(puntos del jugador > esperado) = {a.mean():.3f}; P(total del partido > esperado) = {b.mean():.3f}; producto {a.mean() * b.mean():.3f}; conjunta observada {conjunta:.3f}")
    c, d = r > 0, err_margen * np.where(np.array([x["pl"] > x["pv"] for x in g]), 1, -1) > 0
    print(f"corr(error del prop de puntos, error del margen del partido) = {np.corrcoef(r, err_margen)[0, 1]:+.3f} (el signo depende del equipo del jugador; ver arriba el efecto de partido desigual)")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
