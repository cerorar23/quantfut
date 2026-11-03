"""Evaluación del Sprint 3 con datos exportados de `nba_datos` (CSV): núcleo del marcador y mercados de equipo.

    python apps/nba/ops/evaluar_s3.py CARPETA_CON_CSV [temporada_prueba=2025-26]

Entradas: s3_juegos.csv (fecha, temporada, partido_id, local, visitante, pts_local, pts_visitante) y s3_cierres.csv
(cierre de bet365: h2h, spreads y totals del partido completo). Validación hacia adelante: cada partido se predice con
los ratings anteriores a él. Los parámetros y las desviaciones se ajustan SOLO con temporadas anteriores a la de prueba.
Las líneas enteras (con posible push) se excluyen de las métricas de cobertura.
"""
import csv
from datetime import date
import itertools
import json
from collections import defaultdict
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nba.v2 import mercados, nucleo  # noqa: E402
from nba.v2.evaluacion import brier, ic_diferencia, logloss, pendiente_calibracion, rmse  # noqa: E402,F401
from nba.v2.referencia import quitar_margen  # noqa: E402


def desvig(o1, o2):
    return quitar_margen([o1, o2])[0]
from nba.v2.nucleo import Parametros, Ratings  # noqa: E402

N_SIM = 20000


def leer(carpeta: Path):
    juegos = []
    with open(carpeta / "s3_juegos.csv", encoding="utf8") as f:
        for r in csv.DictReader(f):
            juegos.append(dict(fecha=r["fecha"], temporada=r["temporada"], pid=int(r["partido_id"]), local=r["local"],
                               visit=r["visitante"], pl=float(r["pts_local"]), pv=float(r["pts_visitante"])))
    juegos.sort(key=lambda j: (j["fecha"], j["pid"]))
    cierres = defaultdict(dict)
    with open(carpeta / "s3_cierres.csv", encoding="utf8") as f:
        for r in csv.DictReader(f):
            c = cierres[int(r["partido_id"])]
            cuota = float(r["cuota"])
            if r["mercado"] == "h2h":
                c.setdefault("h2h", {})[r["lado"]] = cuota
            elif r["mercado"] == "spreads" and r["lado"] == "local":
                c["spread_linea"] = float(r["linea"])
                c.setdefault("spread", {})["local"] = cuota
            elif r["mercado"] == "spreads":
                c.setdefault("spread", {})["visit"] = cuota
            elif r["mercado"] == "totals":
                c["total_linea"] = float(r["linea"])
                c.setdefault("total", {})[r["lado"]] = cuota
    return juegos, cierres


def recorrer(juegos, p: Parametros):
    """Predice cada partido con los ratings previos y luego los actualiza. Devuelve (mu_local, mu_visit) por partido."""
    r, salida, temporada, ultimo = Ratings(), [], None, {}
    for j in juegos:
        if j["temporada"] != temporada:
            if temporada is not None:
                nucleo.nueva_temporada(r, p)
            temporada = j["temporada"]
        dia = date.fromisoformat(j["fecha"])
        dias = {lado: (dia - ultimo[j[lado]]).days if j[lado] in ultimo else 7 for lado in ("local", "visit")}
        j["dias"] = dias
        ajuste = nucleo.ajuste_descanso(dias["local"], dias["visit"], p)
        salida.append(r.esperado(j["local"], j["visit"], ajuste))
        nucleo.actualizar(r, j["local"], j["visit"], j["pl"], j["pv"], p, ajuste)
        ultimo[j["local"]] = ultimo[j["visit"]] = dia
    return salida


def ajustar(juegos, temporadas_ajuste):
    """Rejilla de (eta, arrastre, eta_liga) por RMSE del margen en las dos últimas temporadas de ajuste."""
    validar = set(temporadas_ajuste[-2:])
    mejor = None
    for eta, arrastre, eta_liga in itertools.product((0.02, 0.03, 0.045, 0.06, 0.08), (0.5, 0.65, 0.8), (0.002, 0.01)):
        p = Parametros(eta=eta, arrastre=arrastre, eta_liga=eta_liga)
        mus = recorrer([j for j in juegos if j["temporada"] in temporadas_ajuste], p)
        sel = [(m, j) for m, j in zip(mus, [j for j in juegos if j["temporada"] in temporadas_ajuste]) if j["temporada"] in validar]
        e = rmse([m[0] - m[1] for m, _ in sel], [j["pl"] - j["pv"] for _, j in sel])
        et = rmse([m[0] + m[1] for m, _ in sel], [j["pl"] + j["pv"] for _, j in sel])
        puntuacion = e + 0.5 * et          # el total pesa la mitad: su error es mayor y menos explotable
        if mejor is None or puntuacion < mejor[0]:
            mejor = (puntuacion, p, e, et)
    return mejor


def main(carpeta: Path, prueba: str):
    juegos, cierres = leer(carpeta)
    temporadas = sorted({j["temporada"] for j in juegos})
    ajuste = [t for t in temporadas if t < prueba]
    print(f"{len(juegos)} partidos; ajuste {ajuste}; prueba {prueba}")

    _, p, e_val, et_val = ajustar(juegos, ajuste)
    print(f"parámetros: eta={p.eta} arrastre={p.arrastre} eta_liga={p.eta_liga} (RMSE margen {e_val:.3f}, total {et_val:.3f} en validación)")

    # efecto de jugar en la noche siguiente: se mide en los residuos del ajuste (sin ese término) y se fija
    mus0 = recorrer(juegos, p)
    fila = [(1.0, 1.0 if j["dias"]["local"] == 1 else 0.0, 1.0 if j["dias"]["visit"] == 1 else 0.0,
             (j["pl"] - j["pv"]) - (m[0] - m[1])) for m, j in zip(mus0, juegos) if j["temporada"] in ajuste[1:]]
    xa = np.array([f[:3] for f in fila])
    coef = np.linalg.lstsq(xa, np.array([f[3] for f in fila]), rcond=None)[0]
    efecto = float((-coef[1] + coef[2]) / 2)
    print(f"efecto de jugar en la noche siguiente (margen): local {coef[1]:+.2f}, visitante {coef[2]:+.2f} -> {efecto:.2f} por equipo")
    p = Parametros(eta=p.eta, arrastre=p.arrastre, eta_liga=p.eta_liga, efecto_b2b=efecto)
    mus = recorrer(juegos, p)
    # desviaciones medidas SOLO en el ajuste, sin la primera temporada (calentamiento)
    res = [(m, j) for m, j in zip(mus, juegos) if j["temporada"] in ajuste[1:]]
    r_margen = np.array([(j["pl"] - j["pv"]) - (m[0] - m[1]) for m, j in res])
    r_total = np.array([(j["pl"] + j["pv"]) - (m[0] + m[1]) for m, j in res])
    sigma_margen, sigma_total = float(r_margen.std()), float(r_total.std())
    print(f"sigma margen {sigma_margen:.3f} (sesgo {r_margen.mean():+.2f}), sigma total {sigma_total:.3f} (sesgo {r_total.mean():+.2f})")

    # mezcla con la línea del mercado (solo informativa): pesos por MCO sobre el ajuste con cierre
    def linea_margen(pid):
        return -cierres[pid]["spread_linea"] if "spread_linea" in cierres.get(pid, {}) else None

    ajuste_con = [(m, j) for m, j in zip(mus, juegos) if j["temporada"] in ajuste[1:] and linea_margen(j["pid"]) is not None]
    x = np.array([[m[0] - m[1], linea_margen(j["pid"])] for m, j in ajuste_con])
    y = np.array([j["pl"] - j["pv"] for _, j in ajuste_con])
    w = np.linalg.lstsq(x, y, rcond=None)[0]
    print(f"pesos de mezcla del margen (modelo, mercado) sobre {len(y)} partidos de ajuste: {w.round(3)}")

    prueba_juegos = [(m, j) for m, j in zip(mus, juegos) if j["temporada"] == prueba]
    informe = {"parametros": dict(eta=p.eta, arrastre=p.arrastre, eta_liga=p.eta_liga, efecto_b2b=efecto), "sigma_margen": sigma_margen,
               "sigma_total": sigma_total, "n_prueba": len(prueba_juegos), "pesos_mezcla_margen": w.tolist()}
    informe["rmse_margen_modelo"] = rmse([m[0] - m[1] for m, _ in prueba_juegos], [j["pl"] - j["pv"] for _, j in prueba_juegos])
    informe["rmse_total_modelo"] = rmse([m[0] + m[1] for m, _ in prueba_juegos], [j["pl"] + j["pv"] for _, j in prueba_juegos])

    filas = defaultdict(lambda: defaultdict(list))
    sim_ok = {"revisados": 0, "violaciones": 0}
    for i, (m, j) in enumerate(prueba_juegos):
        c = cierres.get(j["pid"])
        marcador = nucleo.simular(m[0], m[1], sigma_margen, sigma_total, n=N_SIM, semilla=j["pid"])
        margen_real, total_real = j["pl"] - j["pv"], j["pl"] + j["pv"]
        # coherencia por construcción: se comprueba en una de cada 4 partidos
        if i % 4 == 0:
            sim_ok["revisados"] += 1
            g = mercados.ganador(marcador)
            fallos = [
                not (mercados.handicap(marcador, -2.5) > mercados.handicap(marcador, -5.5) > mercados.handicap(marcador, -9.5)),
                not (mercados.total(marcador, m[0] + m[1] - 8) > mercados.total(marcador, m[0] + m[1]) > mercados.total(marcador, m[0] + m[1] + 8)),
                abs(mercados.handicap(marcador, 0.0) - g) > 1e-9,
                abs(sum(mercados.margen_de_victoria(marcador).values()) - 1) > 1e-9,
                mercados.total_equipo(marcador, "local", 100.5) + mercados.total_equipo(marcador, "local", 100.5, "under") - 1 > 1e-9,
            ]
            sim_ok["violaciones"] += int(any(fallos))
        if not c or "h2h" not in c:
            continue
        filas["ganador"]["modelo"].append(mercados.ganador(marcador))
        filas["ganador"]["mercado"].append(desvig(c["h2h"]["local"], c["h2h"]["visit"]))
        filas["ganador"]["y"].append(1.0 if margen_real > 0 else 0.0)
        if "spread_linea" in c and c["spread_linea"] % 1 != 0 and "spread" in c:
            linea = c["spread_linea"]
            filas["handicap"]["modelo"].append(mercados.handicap(marcador, linea))
            filas["handicap"]["mercado"].append(desvig(c["spread"]["local"], c["spread"]["visit"]))
            filas["handicap"]["y"].append(1.0 if margen_real + linea > 0 else 0.0)
            filas["margen_linea"]["mercado"].append(-linea)
            filas["margen_linea"]["mezcla"].append(w[0] * (m[0] - m[1]) + w[1] * (-linea))
            filas["margen_linea"]["modelo"].append(m[0] - m[1])
            filas["margen_linea"]["y"].append(margen_real)
        if "total_linea" in c and c["total_linea"] % 1 != 0 and "total" in c:
            linea = c["total_linea"]
            filas["total"]["modelo"].append(mercados.total(marcador, linea))
            filas["total"]["mercado"].append(desvig(c["total"]["over"], c["total"]["under"]))
            filas["total"]["y"].append(1.0 if total_real > linea else 0.0)
            filas["total_linea"]["mercado"].append(linea)
            filas["total_linea"]["modelo"].append(m[0] + m[1])
            filas["total_linea"]["y"].append(total_real)

    informe["coherencia"] = sim_ok
    for nombre in ("ganador", "handicap", "total"):
        f = filas[nombre]
        y = np.array(f["y"])
        pend, inter = pendiente_calibracion(np.array(f["modelo"]), y)
        d, lo, hi = ic_diferencia(f["modelo"], f["mercado"], y)
        informe[nombre] = dict(n=len(y), brier_modelo=brier(f["modelo"], y), brier_mercado=brier(f["mercado"], y),
                               logloss_modelo=logloss(f["modelo"], y), logloss_mercado=logloss(f["mercado"], y),
                               pendiente=pend, intercepto=inter, dif_brier=d, dif_ic95=[lo, hi])
    ml, tl = filas["margen_linea"], filas["total_linea"]
    informe["rmse_con_cierre"] = dict(
        margen_modelo=rmse(ml["modelo"], ml["y"]), margen_mercado=rmse(ml["mercado"], ml["y"]), margen_mezcla=rmse(ml["mezcla"], ml["y"]),
        total_modelo=rmse(tl["modelo"], tl["y"]), total_mercado=rmse(tl["mercado"], tl["y"]), n=len(ml["y"]))
    print(json.dumps(informe, indent=1, ensure_ascii=False))
    (carpeta / "informe_s3.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False), encoding="utf8")


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "2025-26")
