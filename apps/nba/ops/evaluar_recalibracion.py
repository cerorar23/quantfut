"""Recalibración del ganador con origen móvil: ajusta con las temporadas anteriores y mide en la de prueba.

    python apps/nba/ops/evaluar_recalibracion.py 2023-24=CARPETA 2024-25=CARPETA 2025-26=CARPETA

Cada CARPETA tiene `predicciones_s3b.json` (volcado de evaluar_s3b.py: predicciones hacia adelante de todos los partidos hasta la temporada de prueba).
Variantes: base (sin tocar), escala de la media k (coherente: cambia el margen esperado y por tanto todos los mercados) y logística (solo el
ganador; referencia de lo alcanzable). Se evalúan equipo solo y la mezcla equipo + jugadores.
"""
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nba.v2 import evaluacion as ev  # noqa: E402
from nba.v2 import recalibracion as rc  # noqa: E402


def conjunto(difs):
    pesos = [(d, 1 / (((hi - lo) / 3.92) ** 2)) for d, lo, hi in difs]
    total = sum(w for _, w in pesos)
    m = sum(d * w for d, w in pesos) / total
    ee = 1 / math.sqrt(total)
    return m, m - 1.96 * ee, m + 1.96 * ee


def margen_de(g, variante):
    eq = g["equipo_mu"][0] - g["equipo_mu"][1]
    return eq if variante == "equipo" else (eq + g["jugadores_margen"]) / 2


def evaluar(origen: str, carpeta: Path, variante: str):
    datos = json.loads((carpeta / "predicciones_s3b.json").read_text(encoding="utf8"))
    previos = [g for g in datos if g["temporada"] < origen]
    prueba = [g for g in datos if g["temporada"] == origen]
    mu_p = np.array([margen_de(g, variante) for g in previos])
    y_p = np.array([1.0 if g["pl"] > g["pv"] else 0.0 for g in previos])
    sigma = float(np.std([(g["pl"] - g["pv"]) - m for g, m in zip(previos, mu_p)]))
    k = rc.ajustar_escala(mu_p, sigma, y_p)
    a, b = rc.ajustar_logistica(rc.p_ganador(mu_p, sigma), y_p)
    mu_t = np.array([margen_de(g, variante) for g in prueba])
    y_t = np.array([1.0 if g["pl"] > g["pv"] else 0.0 for g in prueba])
    con_mercado = np.array([g["p_mercado"] is not None for g in prueba])
    grupos = np.array([g['fecha'] for g in prueba])
    p_mer = np.array([g["p_mercado"] if g["p_mercado"] is not None else 0.5 for g in prueba])
    base, escala = rc.p_ganador(mu_t, sigma), rc.p_ganador(mu_t, sigma, k)
    logis = rc.aplicar_logistica(base, a, b)
    fila = {"origen": origen, "variante": variante, "n_ajuste": len(previos), "n_prueba": len(prueba), "sigma": sigma, "k": k, "a": a, "b": b}
    for nombre, p in (("base", base), ("escala", escala), ("logistica", logis)):
        fila[nombre] = {"brier": ev.brier(p[con_mercado], y_t[con_mercado]), "logloss": ev.logloss(p[con_mercado], y_t[con_mercado]),
                        "pendiente": ev.pendiente_calibracion(p[con_mercado], y_t[con_mercado])[0],
                        "dif_vs_mercado": ev.ic_diferencia(p[con_mercado], p_mer[con_mercado], y_t[con_mercado], grupos=grupos[con_mercado]),
                        "dif_vs_base": ev.ic_diferencia(p[con_mercado], base[con_mercado], y_t[con_mercado], grupos=grupos[con_mercado])}
    # hándicap: la escala de la media también mueve las probabilidades de cubrir una línea, así que se comprueba que no empeoren
    h = [i for i, g in enumerate(prueba) if g["linea"] is not None and g["p_mercado_handicap"] is not None]
    if h:
        lin = np.array([prueba[i]["linea"] for i in h])
        y_h = np.array([1.0 if (prueba[i]["pl"] - prueba[i]["pv"] + prueba[i]["linea"]) > 0 else 0.0 for i in h])
        p_h_mer = np.array([prueba[i]["p_mercado_handicap"] for i in h])
        ph0 = np.clip(norm.cdf((mu_t[h] + lin) / sigma), 1e-6, 1 - 1e-6)
        ph1 = np.clip(norm.cdf((k * mu_t[h] + lin) / sigma), 1e-6, 1 - 1e-6)
        fila["handicap"] = {"n": len(h), "base": ev.brier(ph0, y_h), "escala": ev.brier(ph1, y_h), "mercado": ev.brier(p_h_mer, y_h),
                            "dif_escala_vs_base": ev.ic_diferencia(ph1, ph0, y_h, grupos=grupos[h])}
    fila["rmse_margen"] = {"base": ev.rmse(mu_t, [g["pl"] - g["pv"] for g in prueba]), "escala": ev.rmse(k * mu_t, [g["pl"] - g["pv"] for g in prueba])}
    return fila


def main(origenes: dict[str, Path]):
    sys.stdout.reconfigure(encoding="utf8")
    for variante in ("equipo", "mezcla"):
        filas = [evaluar(o, c, variante) for o, c in origenes.items()]
        print(f"\n### {variante}")
        print("| Origen | k (escala) | b (logística) | Brier base → escala → logística | Pendiente base → escala → logística | Δ Brier escala vs base (IC95) | Δ hándicap escala vs base (IC95) |")
        print("|---|---|---|---|---|---|---|")
        for f in filas:
            d = f["escala"]["dif_vs_base"]
            h = f.get("handicap", {}).get("dif_escala_vs_base")
            print(f"| {f['origen']} | {f['k']:.2f} | {f['b']:.2f} | {f['base']['brier']:.4f} → {f['escala']['brier']:.4f} → {f['logistica']['brier']:.4f} | "
                  f"{f['base']['pendiente']:.2f} → {f['escala']['pendiente']:.2f} → {f['logistica']['pendiente']:.2f} | {d[0]:+.5f} [{d[1]:+.5f}, {d[2]:+.5f}] | "
                  + (f"{h[0]:+.5f} [{h[1]:+.5f}, {h[2]:+.5f}]" if h else "—") + " |")
        for nombre, clave in (("escala", "escala"), ("logística", "logistica")):
            m, lo, hi = conjunto([f[clave]["dif_vs_base"] for f in filas])
            print(f"Conjunto Δ Brier {nombre} vs base: {m:+.5f} [{lo:+.5f}, {hi:+.5f}]")
        mm, lo, hi = conjunto([f["escala"]["dif_vs_mercado"] for f in filas])
        mb, lob, hib = conjunto([f["base"]["dif_vs_mercado"] for f in filas])
        print(f"Distancia al mercado (Brier ganador): base {mb:+.4f} [{lob:+.4f}, {hib:+.4f}] → con escala {mm:+.4f} [{lo:+.4f}, {hi:+.4f}]")
        hs = [f["handicap"]["dif_escala_vs_base"] for f in filas if "handicap" in f]
        if hs:
            m, lo, hi = conjunto(hs)
            print(f"Conjunto Δ Brier del hándicap con la escala: {m:+.5f} [{lo:+.5f}, {hi:+.5f}]")
        print("RMSE del margen base → escala:", ", ".join(f"{f['origen']} {f['rmse_margen']['base']:.2f} → {f['rmse_margen']['escala']:.2f}" for f in filas))


if __name__ == "__main__":
    main({a.split("=")[0]: Path(a.split("=", 1)[1]) for a in sys.argv[1:]})
