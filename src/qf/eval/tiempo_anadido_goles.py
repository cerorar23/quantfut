"""
Diagnóstico (2026-11-09): ¿la deriva de goles de ago-nov 2026 (Dixon-Coles
subestima, `project_sesgo_goles_apagado`) viene del tiempo añadido?

Lee el archivo local de SofaScore (7 ligas, temporadas 23/24 a 26/27). Compara
la misma ventana (1-ago a 9-nov de cada temporada) para no mezclar calendario:
tiempo añadido medio (`time.injuryTime1 + injuryTime2`), goles por partido en
tiempo reglamentario y la pendiente de goles sobre minutos añadidos con
efectos fijos por liga. El archivo es reconstrucción, no punto en el tiempo:
sirve para diagnosticar, no para entrenar.

Uso: python -m qf.eval.tiempo_anadido_goles --raiz C:/.../SOFASCORE/data/v3/events
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
from datetime import datetime, timezone

import numpy as np

LIGAS = (17, 8, 23, 35, 34, 37, 238)
TEMPORADAS = {"23/24": 2023, "24/25": 2024, "25/26": 2025, "26/27": 2026}


def leer(raiz: str) -> list[dict]:
    filas = []
    for f in glob.glob(f"{raiz}/*/*/*/event.json.gz"):
        try:
            e = json.load(gzip.open(f))
            e = e.get("event", e)
            ut = e["tournament"]["uniqueTournament"]["id"]
            if ut not in LIGAS or e["status"]["type"] != "finished":
                continue
            t, h, a = e.get("time") or {}, e["homeScore"], e["awayScore"]
            if "injuryTime1" not in t or "injuryTime2" not in t:
                continue
            f1 = h.get("period1", 0) + a.get("period1", 0)
            f2 = h.get("period2", 0) + a.get("period2", 0)
            fecha = datetime.fromtimestamp(e["startTimestamp"], timezone.utc)
            filas.append({"liga": ut, "temp": e["season"]["year"], "fecha": fecha,
                          "anadido": t["injuryTime1"] + t["injuryTime2"],
                          "goles": f1 + f2, "goles2": f2})
        except Exception:
            continue
    return filas


def resumen(filas: list[dict]) -> dict:
    out = {}
    for temp, anio in TEMPORADAS.items():
        v = [r for r in filas if r["temp"] == temp
             and datetime(anio, 8, 1, tzinfo=timezone.utc) <= r["fecha"]
             < datetime(anio, 11, 10, tzinfo=timezone.utc)]
        if not v:
            continue
        g = np.array([r["goles"] for r in v], float)
        out[temp] = {"n": len(v), "anadido_min": round(float(np.mean([r["anadido"] for r in v])), 2),
                     "goles": round(float(g.mean()), 3),
                     "ee_goles": round(float(g.std(ddof=1) / np.sqrt(len(g))), 3),
                     "goles_2t": round(float(np.mean([r["goles2"] for r in v])), 3)}
    # Pendiente goles ~ minutos añadidos con efectos fijos de liga y temporada.
    v = [r for r in filas if r["temp"] in TEMPORADAS]
    llaves = sorted({(r["liga"], r["temp"]) for r in v})
    X = np.array([[r["anadido"]] + [float((r["liga"], r["temp"]) == k) for k in llaves] for r in v])
    y = np.array([r["goles"] for r in v], float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    xc = X[:, 0] - np.array([np.mean([w["anadido"] for w in v if (w["liga"], w["temp"]) == (r["liga"], r["temp"])]) for r in v])
    ee = float(np.sqrt(res.var(ddof=len(llaves) + 1) / (xc ** 2).sum()))
    out["pendiente_goles_por_min_anadido"] = {"beta": round(float(beta[0]), 4), "ee": round(ee, 4), "n": len(v)}
    return out


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--raiz", required=True)
    args = a.parse_args()
    print(json.dumps(resumen(leer(args.raiz)), ensure_ascii=False, indent=1))
