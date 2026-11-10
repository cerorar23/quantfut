"""
T8 (2026-11-09): ¿una cota Venn-Abers sustituye a «p calibrada − 1,28·sd»?

La probabilidad prudente del parley (`Calibrador.calibrar`) resta 1,28
desviaciones del bootstrap del ajuste: supone normalidad y no mira el ruido de
las etiquetas. Venn-Abers (van der Laan y Alaa, ICML 2025) da un intervalo
[p0, p1] ajustando la isotónica dos veces, con el punto nuevo etiquetado 0 y 1;
su límite inferior p0 tiene garantía de calibración en muestra finita.

Mismos datos y partición que el parley (football-data, 7 ligas; 1X2 y goles
2,5; una categoría por mercado y banda de cuota; entreno+validación para ajustar,
test al final con embargo). Se comparan las dos cotas SOBRE EL TEST:
  * validez: media(gana) − media(cota) en cada decil de cota (n ≥ 50). Una cota
    prudente no debe quedar por encima de lo que ocurre (hueco ≥ −2·EE);
  * estrechez: media(p_calibrada − cota). A igual validez, gana la más estrecha.
Criterio inicial (fijado antes de medir y DESCARTADO tras verlo): «gana la más
estrecha». Falló: el límite p0 de Venn-Abers casi coincide con la p calibrada
(estrechez ≈ 0), es decir, no resta ninguna prudencia, y «más estrecha» lo
premiaba por eso. Criterio vigente: la cota prudente debe cumplir en agregado y
por deciles Y dejar margen; se reportan el hueco medio y el peor decil, y la
decisión es de quien lea, no un booleano.

Uso: python -m qf.eval.prudente_venn_abers [--cache .local/fd_cache]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from . import alta_prob_calibracion as apc
from . import parley_calibracion as pc
from . import soft_vs_sharp as sv
from .escalera_prueba import candidatos


def venn_abers_bajo(p_fit: np.ndarray, y_fit: np.ndarray, p_nuevo: np.ndarray) -> np.ndarray:
    """Límite inferior p0 de Venn-Abers para cada p nueva."""
    out = np.empty(len(p_nuevo))
    for i, s in enumerate(p_nuevo):
        iso = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        x = np.append(p_fit, s)
        iso.fit(x, np.append(y_fit, 0.0))
        out[i] = float(iso.predict([s])[0])
    return out


def deciles(cota: np.ndarray, y: np.ndarray, minimo: int = 50) -> list[dict]:
    corte = np.quantile(cota, np.linspace(0, 1, 11))
    idx = np.clip(np.digitize(cota, corte[1:-1]), 0, 9)
    filas = []
    for k in range(10):
        m = idx == k
        if m.sum() < minimo:
            continue
        hueco = float(y[m].mean() - cota[m].mean())
        ee = float(np.sqrt(y[m].mean() * (1 - y[m].mean()) / m.sum()))
        filas.append({"n": int(m.sum()), "cota": round(float(cota[m].mean()), 4),
                      "hueco": round(hueco, 4), "valido": hueco >= -2 * ee})
    return filas


def run(cache: Path) -> dict:
    raw, dataset = sv.load_csvs(apc.LIGAS, sv.DEFAULT_SEASONS, cache)
    c = candidatos(raw, 1.20, 2.50)
    actual, vaa, pcal, ys = [], [], [], []
    for _, g in c.groupby([c["market"], c["price"].map(pc.banda)]):
        fechas = g["fecha"].to_numpy(dtype="datetime64[D]")
        p, y = g["p"].to_numpy(float), g["won"].to_numpy(float)
        r = pc.ajustar_categoria(fechas, p, y)
        if r.get("estado") != "ok":
            continue
        tr, va, te = pc.particion_temporal(fechas)
        uso = np.concatenate([tr, va])
        pc_te = pc._aplicar(r["metodo"], r["params"], p[te])
        sd = np.interp(p[te], r["nodos"], r["sd"])
        actual.append(np.maximum(pc_te - pc.Z_PRUDENTE * sd, 1e-4))
        vaa.append(venn_abers_bajo(p[uso], y[uso], p[te]))
        pcal.append(pc_te)
        ys.append(y[te])
    if not ys:
        return {"error": "ninguna categoría con artefacto"}
    A, V, P, Y = (np.concatenate(v) for v in (actual, vaa, pcal, ys))
    out = {"dataset_sha256": dataset["sha256"], "n_test": int(len(Y)), "acierto_test": round(float(Y.mean()), 4)}
    for nombre, cota in (("actual_p_menos_1.28sd", A), ("venn_abers_p0", V)):
        d = deciles(cota, Y)
        out[nombre] = {"cota_media": round(float(cota.mean()), 4),
                       "hueco_medio": round(float(Y.mean() - cota.mean()), 4),
                       "peor_hueco_decil": min(f["hueco"] for f in d),
                       "estrechez_media": round(float((P - cota).mean()), 4),
                       "deciles": d, "todos_validos": all(f["valido"] for f in d)}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", type=Path, default=Path(".local/fd_cache"))
    print(json.dumps(run(ap.parse_args().cache), indent=1, ensure_ascii=False))
