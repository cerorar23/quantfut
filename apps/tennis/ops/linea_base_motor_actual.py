# apps/tennis/ops/linea_base_motor_actual.py
"""Mide el candidato Markov del motor actual (predicciones congeladas 2025/2026 ya guardadas) frente al cierre de Pinnacle
y a la línea base independiente, sobre los MISMOS partidos (cruce por apellido+inicial y fecha ±16 días).

Las predicciones son las de `heldout_predictions.parquet` (origen 1-ene del año, modelo congelado, embargo 35 d). No se recalcula
nada del motor: se mide lo que ya produjo. El híbrido v7/v8 de producción NO es reproducible hacia atrás (se ajustó con 2025 y
sus entradas dinámicas no tienen historial sellado); solo existe en el archivo prospectivo (ver informe).
"""
from pathlib import Path
import numpy as np
import pandas as pd

import linea_base_datos as ld
import linea_base_walkforward as lw

RAIZ = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis")
DATOS = lw.SALIDA_DATOS


def claves_motor(nombre: str):
    t = ld._norm(nombre).split()
    if len(t) < 2:
        return set()
    return {("".join(t[k:]), t[0][0]) for k in range(1, len(t))}


def cruzar(circ: str, anio: int, canon: pd.DataFrame, td: pd.DataFrame):
    ex = pd.read_parquet(RAIZ / f"full_20261016/experiments/{circ}_{anio}/heldout_predictions.parquet")
    c = canon.set_index("match_id")
    ex = ex.join(c[["winner_name", "loser_name", "winner_id"]], on="match_id")
    ex["period"] = pd.to_datetime(ex["period"])
    idx = {}
    for r in td[td.anio.isin([anio, anio - 1, anio + 1])].itertuples():
        idx.setdefault((r.kw, r.kl), []).append(r)
    filas, sin, amb = [], 0, 0
    for r in ex.itertuples():
        kw_set, kl_set = claves_motor(r.winner_name), claves_motor(r.loser_name)
        cand = [t for kw in kw_set for kl in kl_set for t in idx.get((kw, kl), [])
                if abs((t.Date - r.period).days) <= 16]
        if not cand:
            sin += 1; continue
        if len({t.mid for t in cand}) > 1:
            amb += 1; continue
        t = cand[0]
        gana_a = r.a == r.winner_id
        p_gan = r.model_probability if gana_a else 1 - r.model_probability
        e_gan = r.elo_probability if gana_a else 1 - r.elo_probability
        es_gan = r.surface_elo_probability if gana_a else 1 - r.surface_elo_probability
        filas.append((t.mid, p_gan, e_gan, es_gan))
    out = pd.DataFrame(filas, columns=["mid", "p_motor_markov", "p_motor_elo", "p_motor_elo_sup"])
    print(f"{circ} {anio}: motor={len(ex)} cruzados={len(out)} sin_cruce={sin} ambiguos={amb} tasa={len(out)/len(ex):.3f}")
    return out, dict(circuito=circ, origen=anio, motor=len(ex), cruzados=len(out), sin_cruce=sin, ambiguos=amb)


def main():
    rng = np.random.default_rng(lw.SEMILLA + 2)
    cobertura, metr, difs = [], [], []
    for circ in ("ATP", "WTA"):
        td = pd.read_parquet(DATOS / f"linea_base_pred_{circ}.parquet")
        td["anio"] = td["Date"].dt.year
        td["kw"], td["kl"] = td["kw"].map(tuple), td["kl"].map(tuple)   # parquet devuelve arrays, no hasheables
        canon = pd.read_parquet(RAIZ / "full_20261016/canonical/matches.parquet", columns=["match_id", "winner_name", "loser_name", "winner_id"])
        for anio in (2025, 2026):
            out, cob = cruzar(circ, anio, canon, td)
            cobertura.append(cob)
            m0 = td.merge(out, on="mid", how="inner")
            # Pinnacle (m_ps) deja de existir en Tennis-Data desde feb-2026: se mide frente a ambas referencias
            for ref in ("m_ps", "m_avg"):
                m = m0[m0[ref].notna()]
                if len(m) < 50:
                    print(f"{circ} {anio} ref={ref}: solo {len(m)} partidos, no se mide")
                    continue
                for mod in ["p_motor_markov", "p_motor_elo", "p_motor_elo_sup", "p_elo", "p_elo_sup", "p_elo_cal", ref]:
                    y, p = lw.orientar(m, mod)
                    metr.append(dict(circuito=circ, origen=anio, ref=ref, modelo=mod, **lw.metricas(y, p), **lw.calibracion(y, p, rng, 150)))
                for mod in ["p_motor_markov", "p_motor_elo", "p_motor_elo_sup", "p_elo", "p_elo_cal"]:
                    y, pm = lw.orientar(m, mod); _, pr = lw.orientar(m, ref)
                    difs.append(dict(circuito=circ, origen=anio, modelo=mod, ref=ref, **lw.dif_bootstrap(y, pm, pr, rng)))
    t = DATOS / "tablas"
    pd.DataFrame(cobertura).to_csv(t / "motor_actual_cruce.csv", index=False)
    pd.DataFrame(metr).to_csv(t / "motor_actual_metricas.csv", index=False)
    d = pd.DataFrame(difs)
    d.to_csv(t / "motor_actual_dif_vs_cierre.csv", index=False)
    comb = pd.concat([lw.combinar(g).assign(ref=r) for r, g in d.groupby("ref")])
    comb.to_csv(t / "motor_actual_dif_combinada.csv", index=False)
    print(comb.round(4).to_string())


if __name__ == "__main__":
    main()
