"""Walk-forward 2019–2024 con Ψ CONGELADO (entrenado con ≤ 2018) y compuertas del plan §I (S3).

Uso: python apps/tenis/ops/evaluar_wf.py [--repetir] [--reps 2000]
- Filtro R de 2005 a 2024 (la reserva 2025–2026 no se lee) para el modelo completo y las dos ablaciones.
- Pieza P (Ŝ) y unión C en una muestra; línea base Elo / Elo+superficie / Elo recalibrado sobre los MISMOS partidos.
- Escribe modelo_s3/predicciones_wf.parquet (todos los partidos pronosticables 2019–2024) y evaluacion_wf.json.
"""
import argparse
import hashlib
import io
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from tenis.modelo import datos as dm
from tenis.modelo import evaluacion as ev
from tenis.modelo import hiperparametros as hp
from tenis.modelo import recalibracion as rc
from tenis.modelo import tabla
from tenis.modelo.linea_base import elo
from tenis.modelo.parametros import Psi
from tenis.modelo.puntos import PsiP, filtrar_p, observaciones
from tenis.modelo.rating import filtrar
from tenis.modelo.union import unir

SALIDA = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\modelo_s3")
EVAL, HASTA, SEMILLA = (2019, 2024), 2024, 20261105
COLS_PRED = ["partido_key", "circuito", "temporada", "corte_utc", "pi_lado1", "prior_ranking_1", "prior_ranking_2",
             "prior_ranking", "historia_corta", "fatiga_desconocida", "rho", "var_rho", "fatiga_1", "fatiga_2", "S_hat"]


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def sha_df(df: pd.DataFrame) -> str:
    buf = io.StringIO()
    df.to_csv(buf, index=False, float_format="%.12g")
    return hashlib.sha256(buf.getvalue().encode("utf-8")).hexdigest()


def correr_circuito(d, cfg: dict, obs) -> pd.DataFrame:
    psi = Psi.desde_dict(cfg["psi_r"])
    tabs = tabla.construir_todas(tuple(cfg["lbar"]), psi.sigma_eps, psi.rho_eps)
    tabs_c = tabla.construir_todas((cfg["lbar_comun"],) * 4, psi.sigma_eps, psi.rho_eps)
    t0 = time.time()
    sal = filtrar(d, psi, tabs)
    log(f"{d.circuito}: filtro completo {time.time() - t0:.0f} s, {sal.n_actualizaciones} actualizaciones")
    s_ss = filtrar(d, Psi.desde_dict(cfg["ablacion_sin_superficie"]["psi_r"]), tabs_c)
    s_sf = filtrar(d, Psi.desde_dict(cfg["ablacion_sin_fatiga"]["psi_r"]), tabs)
    _, s_hat, _ = filtrar_p(d, obs, PsiP(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in cfg["psi_p"].items()}))
    el = elo(d)
    p = d.p
    f = pd.DataFrame({"partido_key": p.partido_key, "circuito": p.circuito, "temporada": p.temporada,
                      "corte_utc": p.corte_utc, "pi_lado1": sal.pi, "prior_ranking_1": sal.prior1,
                      "prior_ranking_2": sal.prior2, "prior_ranking": sal.prior1 | sal.prior2,
                      "historia_corta": (p.n_prev_1.fillna(0) < 20) | (p.n_prev_2.fillna(0) < 20),
                      "fatiga_desconocida": sal.fat_desc, "rho": sal.rho, "var_rho": sal.var_rho,
                      "fatiga_1": sal.f1, "fatiga_2": sal.f2, "S_hat": s_hat,
                      # columnas internas de evaluación (no se guardan en predicciones_wf)
                      "motivo": sal.motivo, "ult_vis": sal.ult_vis, "corte_ns": p.corte_ns, "fmt": p.fmt,
                      "y1": d.y1, "liquida": d.liquida, "pi_sin_sup": s_ss.pi, "pi_sin_fat": s_sf.pi,
                      "p_elo": el["p_elo"], "p_elo_sup": el["p_elo_sup"], "superficie": p.superficie,
                      "categoria": p.categoria.fillna("sin_categoria"), "ronda": p.ronda, "mejor_de": p.mejor_de,
                      "n_prev_min": np.minimum(p.n_prev_1.fillna(0), p.n_prev_2.fillna(0))})
    for col, base in (("pi_recal", "pi_lado1"), ("p_elo_cal", "p_elo")):
        f[col], bs = rc.por_temporada(f.temporada, f[base], f.y1, f.liquida & f[base].notna(), range(EVAL[0], EVAL[1] + 1), 2012)
        cfg.setdefault("_pendientes_recal", {})[col] = bs
    return f


def evaluar(f: pd.DataFrame, cfg: dict, rng, reps: int) -> dict:
    t = f.temporada.to_numpy()
    s = f[(t >= EVAL[0]) & (t <= EVAL[1]) & f.pi_lado1.notna() & f.liquida].copy()
    y, pi = s.y1.to_numpy(), s.pi_lado1.to_numpy()
    out = {"n_evaluados": int(len(s)), "metricas": {}, "comparaciones": {}, "por_temporada_brier": {}}
    for col in ("pi_lado1", "pi_recal", "p_elo", "p_elo_sup", "p_elo_cal", "pi_sin_sup", "pi_sin_fat"):
        out["metricas"][col] = ev.metricas(y, s[col].to_numpy())
    for nombre, ref in (("vs_elo_recalibrado", "p_elo_cal"), ("vs_elo", "p_elo"), ("vs_elo_superficie", "p_elo_sup"),
                        ("recal_menos_sin_capa", None), ("vs_sin_superficie", "pi_sin_sup"), ("vs_sin_fatiga", "pi_sin_fat")):
        if ref is None:
            out["comparaciones"][nombre] = ev.por_origen(s.temporada, y, s.pi_recal, pi, rng, reps)
        else:
            out["comparaciones"][nombre] = ev.por_origen(s.temporada, y, pi, s[ref], rng, reps)
    out["calibracion"] = {c: ev.calibracion(y, s[c].to_numpy(), rng, reps) for c in ("pi_lado1", "p_elo_cal")}
    for temp, g in s.groupby("temporada"):
        out["por_temporada_brier"][int(temp)] = {"n": int(len(g)), "brier": float(ev.brier(g.y1, g.pi_lado1).mean()),
                                                 "logloss": float(ev.perdida(g.y1, g.pi_lado1).mean())}
    f90 = cfg["fijo_r"]["f90"]
    s["seg_fatiga"] = np.where((s.fatiga_1 > f90) | (s.fatiga_2 > f90), "F>F90",
                               np.where(s.fatiga_desconocida, "desconocida", "F<=F90"))
    fav = np.maximum(s.p_elo_cal, 1 - s.p_elo_cal)
    s["fav_elo_cal"] = pd.cut(fav, [0.5, 0.6, 0.7, 0.8, 1.0], include_lowest=True).astype(str)
    s["rango_pi"] = pd.cut(np.maximum(pi, 1 - pi), [0.5, 0.6, 0.7, 0.8, 0.9, 1.0], include_lowest=True).astype(str)
    s["historia"] = np.where(s.n_prev_min < 20, "<20", ">=20")
    s["prior"] = np.where(s.prior_ranking, "prior_ranking", "con_resultados")
    s["mejor_de"] = s.mejor_de.astype(str)
    s["gana_favorito_modelo"] = np.where((pi >= 0.5) == (y == 1), "favorito_gana", "favorito_pierde")
    segs = []
    for var in ("superficie", "categoria", "ronda", "mejor_de", "fav_elo_cal", "rango_pi", "historia", "prior",
                "seg_fatiga", "fatiga_desconocida"):
        for val, g in s.groupby(var):
            if len(g) < 200:
                continue
            gy, gp = g.y1.to_numpy(), g.pi_lado1.to_numpy()
            fila = {"variable": var, "valor": str(val), "n": int(len(g)), "ll_modelo": float(ev.perdida(gy, gp).mean()),
                    "ll_elo_cal": float(ev.perdida(gy, g.p_elo_cal).mean()), "brier_modelo": float(ev.brier(gy, gp).mean()),
                    "pendiente": ev.logistica(rc.logit(gp), gy.astype(float))[1]}
            fila["vs_elo_cal"] = ev.por_origen(g.temporada, gy, gp, g.p_elo_cal, rng, 500)["combinado"]
            if var in ("superficie", "seg_fatiga"):
                fila["vs_sin_superficie"] = ev.por_origen(g.temporada, gy, gp, g.pi_sin_sup, rng, 500)["combinado"]
                fila["vs_sin_fatiga"] = ev.por_origen(g.temporada, gy, gp, g.pi_sin_fat, rng, 500)["combinado"]
            segs.append(fila)
    out["segmentos"] = segs
    # fiabilidad por decil de π (calibración por rango)
    q = pd.qcut(pi, 10, labels=False, duplicates="drop")
    out["fiabilidad"] = [{"decil": int(k), "pi_media": float(pi[q == k].mean()), "frec": float(y[q == k].mean()),
                          "n": int((q == k).sum())} for k in np.unique(q)]
    return out


def compuertas(r: dict) -> dict:
    lb = r["comparaciones"]["vs_elo_recalibrado"]["combinado"]
    cal = r["calibracion"]["pi_lado1"]
    rec = r["comparaciones"]["recal_menos_sin_capa"]["combinado"]
    bri = [v["brier"] for v in r["por_temporada_brier"].values() if v["n"] >= 500] + [r["metricas"]["pi_lado1"]["brier"]]
    return {"G_linea_base": {"pasa": lb["hi"] <= 0.002, "objetivo_dif_negativa": lb["dif_logloss"] < 0, **lb},
            "G_calibracion": {"pasa": bool(cal["pend_lo"] <= 1 <= cal["pend_hi"] and abs(cal["pendiente"] - 1) <= 0.10
                                           and cal["int_lo"] <= 0 <= cal["int_hi"]), **cal},
            "G_recalibracion": {"capa_activa": rec["hi"] < 0, **rec},
            "G_cordura": {"pasa": min(bri) >= 0.18, "brier_minimo": min(bri)}}


def no_fuga(f: pd.DataFrame) -> dict:
    """Ningún pronóstico usó un evento con visible ≥ su corte (ult_vis < corte_ns en todos)."""
    s = f[f.pi_lado1.notna()]
    return {"pronosticos": int(len(s)), "violaciones": int((s.ult_vis >= s.corte_ns).sum())}


def muestra_union(f: pd.DataFrame, cfg: dict, rng, n: int = 120) -> dict:
    s = f[(f.temporada >= EVAL[0]) & f.pi_lado1.notna() & f.S_hat.notna()]
    s = s.iloc[rng.choice(len(s), size=min(n, len(s)), replace=False)]
    errs, rech = [], 0
    for r in s.itertuples():
        try:
            u = unir(r.S_hat, r.pi_lado1, r.fmt, cfg["psi_r"]["sigma_eps"], cfg["psi_r"]["rho_eps"], r.var_rho)
            errs.append(abs(u.pi_logrado - r.pi_lado1))
        except ValueError:
            rech += 1
    return {"n": int(len(s)), "rechazados": rech, "max_err_pi": float(max(errs)) if errs else None,
            "S_hat_media": float(s.S_hat.mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repetir", action="store_true", help="segunda corrida del filtro para comparar el sha256")
    ap.add_argument("--reps", type=int, default=ev.REPS)
    ap.add_argument("--circuitos", nargs="+", default=["atp", "wta"])
    ap.add_argument("--dir", default=str(SALIDA), help="carpeta con hiperparametros.json y de salida")
    a = ap.parse_args()
    salida = Path(a.dir)
    hpj = hp.leer(salida / "hiperparametros.json")
    p, e = dm.cargar_export(hasta=HASTA)
    stats = pd.read_parquet(dm.RUTA_EXPORT / "estadisticas_saque.parquet",
                            columns=["partido_key", "lado", "puntos_saque", "puntos_saque_ganados", "visible_desde"])
    rng = np.random.default_rng(SEMILLA)
    informe, preds, filas = {"sha256_hiperparametros": hp.huella(hpj), "reps": a.reps, "circuitos": {}}, [], []
    for c in a.circuitos:
        cfg = hpj["circuitos"][c]
        d = dm.preparar(p, e, c, HASTA)
        f = correr_circuito(d, cfg, observaciones(d, stats))
        t = f.temporada.to_numpy()
        pr = f[(t >= EVAL[0]) & (t <= EVAL[1]) & f.pi_lado1.notna()][COLS_PRED].reset_index(drop=True)
        r = evaluar(f, cfg, rng, a.reps)
        r["compuertas"] = compuertas(r)
        r["no_fuga"] = no_fuga(f)
        r["pendientes_recal"] = cfg.get("_pendientes_recal")
        r["union_muestra"] = muestra_union(f, cfg, rng)
        r["omitidos_2019_2024"] = f[(t >= EVAL[0]) & (t <= EVAL[1])].motivo.value_counts(dropna=False).rename(
            index=lambda k: k or "pronosticado").to_dict()
        r["sha256_predicciones"] = sha_df(pr)
        if a.repetir:
            r["sha256_segunda_corrida"] = sha_df(correr_circuito(d, cfg, observaciones(d, stats))
                                                 .pipe(lambda g: g[(g.temporada >= EVAL[0]) & (g.temporada <= EVAL[1])
                                                                   & g.pi_lado1.notna()][COLS_PRED].reset_index(drop=True)))
        informe["circuitos"][c] = r
        preds.append(pr)
        filas.append(f[(t >= EVAL[0]) & (t <= EVAL[1]) & f.pi_lado1.notna()].drop(columns=["motivo"]))
        log(f"{c}: compuertas {json.dumps(r['compuertas'], default=float)[:600]}")
    todo = pd.concat(preds, ignore_index=True)
    todo.to_parquet(salida / "predicciones_wf.parquet", index=False)
    informe["sha256_predicciones_total"] = sha_df(todo)
    # filas de evaluación (con etiquetas y líneas base) para diagnósticos posteriores sin volver a correr el filtro
    pd.concat(filas, ignore_index=True).to_parquet(salida / "evaluacion_filas.parquet", index=False)
    (salida / "evaluacion_wf.json").write_text(json.dumps(informe, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    log(f"predicciones_wf.parquet: {len(todo)} filas, sha256 {informe['sha256_predicciones_total']}")


if __name__ == "__main__":
    sys.exit(main())
