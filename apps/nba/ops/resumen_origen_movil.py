"""Resumen de la evaluación de origen móvil: la misma metodología con varias temporadas de prueba, cada una entrenada solo con lo anterior.

    python apps/nba/ops/resumen_origen_movil.py 2023-24=CARPETA 2024-25=CARPETA 2025-26=CARPETA

Lee informe_s3.json (equipo), informe_s3b.json (mezcla con jugadores) y informe_s4.json (props) de cada carpeta y escribe una tabla por métrica y
origen, con la diferencia de Brier frente al mercado (negativa = el modelo mejor) y su estimación conjunta: media ponderada por la inversa de la
varianza (error típico = anchura del IC95 / 3,92; los partidos de cada origen son distintos, así que se tratan como independientes).
"""
import json
import math
from pathlib import Path
import sys


def leer(carpeta: Path, nombre: str):
    ruta = carpeta / nombre
    return json.loads(ruta.read_text(encoding="utf8")) if ruta.exists() else None


def conjunto(difs):
    """[(dif, lo, hi)] → (media ponderada, lo, hi) con pesos 1/EE²."""
    pesos = [(d, 1 / (((hi - lo) / 3.92) ** 2)) for d, lo, hi in difs]
    total = sum(w for _, w in pesos)
    media = sum(d * w for d, w in pesos) / total
    ee = 1 / math.sqrt(total)
    return media, media - 1.96 * ee, media + 1.96 * ee


def fila_brier(nombre, datos):
    d = [(x["dif"], *x["ic95"]) for x in datos]
    m, lo, hi = conjunto(d)
    celdas = " | ".join(f"{x['brier']:.4f} ({x['dif']:+.4f})" for x in datos)
    return f"| {nombre} | {celdas} | {m:+.4f} [{lo:+.4f}, {hi:+.4f}] |"


def main(origenes: dict[str, Path]):
    sys.stdout.reconfigure(encoding="utf8")
    nombres = list(origenes)
    out = ["| Métrica | " + " | ".join(nombres) + " | Conjunto (IC95) |", "|---|" + "---|" * (len(nombres) + 1)]
    s3 = {o: leer(c, "informe_s3.json") for o, c in origenes.items()}
    s3b = {o: leer(c, "informe_s3b.json") for o, c in origenes.items()}
    s4 = {o: leer(c, "informe_s4.json") for o, c in origenes.items()}
    out.append("| **Equipo (núcleo v2.0)** | | | | |")
    out.append("| RMSE margen: modelo / mercado | " + " | ".join(f"{s3[o]['rmse_con_cierre']['margen_modelo']:.2f} / {s3[o]['rmse_con_cierre']['margen_mercado']:.2f}" for o in nombres) + " | |")
    out.append("| RMSE total: modelo / mercado | " + " | ".join(f"{s3[o]['rmse_con_cierre']['total_modelo']:.2f} / {s3[o]['rmse_con_cierre']['total_mercado']:.2f}" for o in nombres) + " | |")
    for k, etiqueta in (("ganador", "Brier ganador"), ("handicap", "Brier hándicap"), ("total", "Brier total")):
        out.append(fila_brier(etiqueta + " (dif. vs mercado)", [{"brier": s3[o][k]["brier_modelo"], "dif": s3[o][k]["dif_brier"], "ic95": s3[o][k]["dif_ic95"]} for o in nombres]))
    out.append("| Pendiente de calibración del ganador | " + " | ".join(f"{s3[o]['ganador']['pendiente']:.2f}" for o in nombres) + " | |")
    out.append("| Parámetros elegidos (eta / arrastre / liga) | " + " | ".join(f"{s3[o]['parametros']['eta']} / {s3[o]['parametros']['arrastre']} / {s3[o]['parametros']['eta_liga']}" for o in nombres) + " | |")
    out.append("| **Equipo + jugadores (media)** | | | | |")
    var = {o: {v["nombre"]: v for v in s3b[o]["variantes"]} for o in nombres}
    for k, etiqueta in (("ganador", "Brier ganador"), ("handicap", "Brier hándicap"), ("total", "Brier total")):
        out.append(fila_brier(etiqueta + " (dif. vs mercado)", [var[o]["mitad_equipo_mitad_jugadores"][k] for o in nombres]))
    out.append("| RMSE margen: equipo → mezcla | " + " | ".join(f"{var[o]['equipo']['rmse_margen']:.2f} → {var[o]['mitad_equipo_mitad_jugadores']['rmse_margen']:.2f}" for o in nombres) + " | |")
    props_o = [o for o in nombres if s4[o]]
    if props_o:
        out += ["", "| Props (" + ", ".join(props_o) + ") | MASE | Cobertura 80 % | Brier vs mercado (IC95) |", "|---|---|---|---|"]
        for stat in ("puntos", "rebotes", "asistencias", "triples"):
            celdas = [s4[o]["stats"][stat] for o in props_o]
            mase = " / ".join(f"{c['MASE']:.3f}" for c in celdas)
            cob = " / ".join(f"{c['cobertura80']:.3f}" for c in celdas)
            dif = " / ".join(f"{c['linea']['dif_brier_vs_mercado']:+.4f} [{c['linea']['ic95'][0]:+.4f}, {c['linea']['ic95'][1]:+.4f}]" for c in celdas)
            out.append(f"| {stat} | {mase} | {cob} | {dif} |")
    print("\n".join(out))


if __name__ == "__main__":
    main({a.split("=")[0]: Path(a.split("=", 1)[1]) for a in sys.argv[1:]})
