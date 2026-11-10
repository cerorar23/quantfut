"""T1 (2026-11-09): ¿un Elo ponderado por juegos del ganador mejora la línea base de la auditoría?

Uso: python apps/tenis/ops/evaluar_elo_ponderado.py [--reps 2000]
Mismos partidos, mismo protocolo que `evaluar_wf` (visibilidad por bloques, K = 24, 2019-2024): Elo general con
gamma = 0 (el de siempre), 1 y 2. Pérdida logarítmica por fila, diferencias emparejadas y bootstrap por día.
También se compara con el modelo del rediseño (`predicciones_wf.parquet`) sobre las filas comunes.
Criterio fijado antes de medir: gamma > 0 entra como línea base solo si su mejora frente a gamma = 0 tiene el IC95
entero bajo cero en pérdida (ATP y WTA); no se elige gamma con datos de reserva (2025-26 no se lee).
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from tenis.modelo import datos as dm
from tenis.modelo.linea_base import elo

SALIDA = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\modelo_s3")
GAMMAS = (0.0, 1.0, 2.0)


def perdida(p1, y1):
    p1 = np.clip(p1, 1e-6, 1 - 1e-6)
    return -(y1 * np.log(p1) + (1 - y1) * np.log1p(-p1))


def ic(diff, dias, reps, rng):
    """Bootstrap por día de la media de `diff` (agrupa partidos del mismo día)."""
    _, inv = np.unique(dias, return_inverse=True)
    k = inv.max() + 1
    s, n = np.bincount(inv, weights=diff, minlength=k), np.bincount(inv, minlength=k)
    m = np.empty(reps)
    for i in range(reps):
        j = rng.integers(0, k, k)
        m[i] = s[j].sum() / n[j].sum()
    return float(diff.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=2000)
    a = ap.parse_args()
    p, e = dm.cargar_export(hasta=2024)
    juegos = pd.read_parquet(dm.RUTA_EXPORT / "eventos_resultado.parquet",
                             columns=["partido_key", "juegos_1", "juegos_2"], filters=[("temporada", "<=", 2024)])
    e = e.merge(juegos.drop_duplicates("partido_key"), on="partido_key", how="left")
    pred = pd.read_parquet(SALIDA / "predicciones_wf.parquet", columns=["partido_key", "pi_lado1"])
    rng = np.random.default_rng(20261109)
    informe = {}
    for c in ("atp", "wta"):
        d = dm.preparar(p, e, c, 2024)
        t = d.p.temporada.to_numpy()
        ok = (t >= 2019) & (t <= 2024) & d.liquida & (d.y1 >= 0)
        res = {g: elo(d, gamma=g)["p_elo"] for g in GAMMAS}
        ok &= ~np.isnan(res[0.0])
        y = d.y1[ok].astype(float)
        dias = (d.p.corte_ns.to_numpy()[ok] // (86400 * 10**9))
        ll = {g: perdida(res[g][ok], y) for g in GAMMAS}
        out = {"n": int(ok.sum()), "logloss": {str(g): round(float(ll[g].mean()), 5) for g in GAMMAS}}
        for g in GAMMAS[1:]:
            m, lo, hi = ic(ll[g] - ll[0.0], dias, a.reps, rng)
            out[f"gamma{g:g}_menos_gamma0"] = {"dif": round(m, 5), "ic95": [round(lo, 5), round(hi, 5)], "entra": hi < 0}
        mod = d.p.loc[ok, ["partido_key"]].merge(pred, on="partido_key", how="left")["pi_lado1"].to_numpy()
        com = ~np.isnan(mod)
        out["comunes_con_modelo"] = int(com.sum())
        llm = perdida(mod[com], y[com])
        out["logloss_modelo"] = round(float(llm.mean()), 5)
        for g in GAMMAS:
            out[f"modelo_menos_elo_gamma{g:g}"] = dict(zip(
                ("dif", "lo", "hi"), (round(x, 5) for x in ic(llm - ll[g][com], dias[com], a.reps, rng))))
        informe[c] = out
    print(json.dumps(informe, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
