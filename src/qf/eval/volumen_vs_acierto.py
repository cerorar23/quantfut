"""
Paso 2 (2026-11-09): la deriva de goles de ago-nov 2026, ¿es volumen (más ocasiones) o acierto (más goles por ocasión)?

Mismo archivo y misma ventana (1-ago a 9-nov) que `tiempo_anadido_goles`: 7 ligas, temporadas 23/24 a 26/27. Por
partido: goles en tiempo reglamentario, xG total, tiros totales y a puerta (`statistics.json.gz`, periodo ALL).
Se descompone goles = xG × (goles/xG): volumen es lo que mueve el xG (y los tiros); acierto, la razón goles/xG.
Las diferencias de 26/27 frente a la media de las tres anteriores llevan error típico por bootstrap de partidos.
Limitación: archivo reconstruido, no punto en el tiempo; el xG es del proveedor y su modelo puede haber cambiado.

Uso: python -m qf.eval.volumen_vs_acierto --raiz C:/.../SOFASCORE/data/v3/events
"""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
from datetime import datetime, timezone

import numpy as np

from .tiempo_anadido_goles import LIGAS, TEMPORADAS

CLAVES = {"expectedGoals": "xg", "totalShotsOnGoal": "tiros", "shotsOnGoal": "a_puerta"}


def leer(raiz: str) -> list[dict]:
    filas = []
    for f in glob.glob(f"{raiz}/*/*/*/event.json.gz"):
        try:
            e = json.load(gzip.open(f))
            e = e.get("event", e)
            if e["tournament"]["uniqueTournament"]["id"] not in LIGAS or e["status"]["type"] != "finished":
                continue
            temp = e["season"]["year"]
            if temp not in TEMPORADAS:
                continue
            fecha = datetime.fromtimestamp(e["startTimestamp"], timezone.utc)
            anio = TEMPORADAS[temp]
            if not datetime(anio, 8, 1, tzinfo=timezone.utc) <= fecha < datetime(anio, 11, 10, tzinfo=timezone.utc):
                continue
            h, a = e["homeScore"], e["awayScore"]
            goles = h.get("period1", 0) + h.get("period2", 0) + a.get("period1", 0) + a.get("period2", 0)
            s = json.load(gzip.open(os.path.join(os.path.dirname(f), "statistics.json.gz")))
            todo = next(p for p in s.get("statistics", s) if p.get("period") == "ALL")
            v = {}
            for g in todo["groups"]:
                for i in g["statisticsItems"]:
                    if i["key"] in CLAVES and CLAVES[i["key"]] not in v:
                        v[CLAVES[i["key"]]] = float(i["homeValue"]) + float(i["awayValue"])
            if len(v) == 3:
                filas.append({"temp": temp, "liga": e["tournament"]["uniqueTournament"]["id"], "goles": goles, **v})
        except Exception:
            continue
    return filas


def resumen(filas: list[dict], reps: int = 2000) -> dict:
    por = {t: [r for r in filas if r["temp"] == t] for t in TEMPORADAS}
    out = {}
    for t, v in por.items():
        if not v:
            continue
        g, x, ti, ap = (np.array([r[k] for r in v], float) for k in ("goles", "xg", "tiros", "a_puerta"))
        out[t] = {"n": len(v), "goles": round(g.mean(), 3), "xg": round(x.mean(), 3), "tiros": round(ti.mean(), 2),
                  "a_puerta": round(ap.mean(), 2), "goles_por_xg": round(g.sum() / x.sum(), 3),
                  "goles_por_a_puerta": round(g.sum() / ap.sum(), 3)}
    rng = np.random.default_rng(7)
    nuevo = por["26/27"]
    previo = [r for t in ("23/24", "24/25", "25/26") for r in por[t]]
    def estad(v):
        g, x, ap = (np.array([r[k] for r in v], float) for k in ("goles", "xg", "a_puerta"))
        return np.array([g.mean(), x.mean(), g.sum() / x.sum(), g.sum() / ap.sum(), ap.mean()])
    base = estad(nuevo) - estad(previo)
    dif = []
    for _ in range(reps):
        a = [nuevo[i] for i in rng.integers(0, len(nuevo), len(nuevo))]
        b = [previo[i] for i in rng.integers(0, len(previo), len(previo))]
        dif.append(estad(a) - estad(b))
    ee = np.std(dif, axis=0)
    nombres = ("goles", "xg", "goles_por_xg", "goles_por_a_puerta", "a_puerta")
    out["26/27_menos_media_23/24-25/26"] = {k: {"dif": round(float(b), 3), "ee": round(float(e), 3)}
                                            for k, b, e in zip(nombres, base, ee)}
    out["xg_por_liga_26/27_menos_previas"] = {}
    for liga in LIGAS:
        a = [r["xg"] for r in nuevo if r["liga"] == liga]
        b = [r["xg"] for r in previo if r["liga"] == liga]
        if a and b:
            out["xg_por_liga_26/27_menos_previas"][str(liga)] = {"n_nuevo": len(a), "xg_nuevo": round(float(np.mean(a)), 2),
                                                                 "xg_previo": round(float(np.mean(b)), 2)}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", required=True)
    print(json.dumps(resumen(leer(ap.parse_args().raiz)), indent=1, ensure_ascii=False))
