"""Estimación del factor de inflación de varianza predictiva c_inf (opción A, 7-nov-2026).

Protocolo (plan §I G-calibración, opción A):
- c_inf ≥ 0 entra SOLO en la predicción: v_pred = v + c_inf. La actualización (log_m) no cambia.
- Se estima maximizando la log-verosimilitud predictiva un paso adelante en temporadas ≤ 2018
  (misma ventana que los hiperparámetros de R y P). Búsqueda en línea (dorada) sobre c_inf ≥ 0.
- Los parámetros Ψ quedan CONGELADOS (se leen de hiperparametros.json).
- Se evalúa en 2019–2024 con las compuertas del plan (G-calibración: pendiente IC95 ⊇ 1 y |b−1| ≤ 0,10;
  intercepto IC95 ⊇ 0). Si no pasa, se informa y se para; la reserva 2025–2026 NO se abre.
- El resultado se añade a hiperparametros.json como campo "c_inf" por circuito.

Uso:
    python apps/tenis/ops/estimar_c_inf.py [--circuitos atp wta] [--reps 2000]
"""
import argparse
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from tenis.modelo import datos as dm
from tenis.modelo import evaluacion as ev
from tenis.modelo import hiperparametros as hp
from tenis.modelo import tabla
from tenis.modelo.parametros import Psi
from tenis.modelo.rating import filtrar

SALIDA = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\modelo_s3")
VENTANA_AJUSTE = (2007, 2018)
EVAL = (2019, 2024)
SEMILLA = 20261107


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def _pi_con_cinf(d, psi_base: Psi, tabs: dict, c_inf: float) -> np.ndarray:
    """Probabilidades del filtro R con c_inf dado (Ψ congelado)."""
    from dataclasses import replace
    psi = replace(psi_base, c_inf=c_inf)
    return filtrar(d, psi, tabs).pi


def _loglik_ajuste(pi: np.ndarray, d, ventana=VENTANA_AJUSTE) -> float:
    """Log-verosimilitud predictiva en la ventana de ajuste (misma que los hiperparámetros)."""
    t = d.p.temporada.to_numpy()
    sel = np.isfinite(pi) & d.liquida & (t >= ventana[0]) & (t <= ventana[1])
    y, q = d.y1[sel], np.clip(pi[sel], 1e-12, 1 - 1e-12)
    return float(np.sum(np.where(y == 1, np.log(q), np.log1p(-q))))


def busqueda_dorada(fn, lo: float, hi: float, tol: float = 1e-5, max_iter: int = 60) -> tuple[float, float]:
    """Maximiza fn en [lo, hi] con búsqueda de la sección dorada. Devuelve (c_inf_opt, f_opt)."""
    phi = (math.sqrt(5) - 1) / 2
    a, b = lo, hi
    c, d = b - phi * (b - a), a + phi * (b - a)
    fc, fd = fn(c), fn(d)
    for _ in range(max_iter):
        if abs(b - a) < tol:
            break
        if fc < fd:
            a, c, fc = c, d, fd
            d = a + phi * (b - a)
            fd = fn(d)
        else:
            b, d, fd = d, c, fc
            c = b - phi * (b - a)
            fc = fn(c)
    best = c if fc >= fd else d
    return float(best), max(fc, fd)


def estimar_circuito(d, cfg: dict, hi_cinf: float = 0.5) -> dict:
    """Estima c_inf para un circuito. Devuelve dict con resultado y diagnóstico.

    Optimización matemática:
    El filtro de rating y los estados m, V son 100% independientes de c_inf (la actualización usa
    log_m que no tiene c_inf). Por tanto, se ejecuta filtrar() una sola vez para obtener (rho, var_rho),
    y la búsqueda dorada solo evalúa tabla.prob(rho, var, c_inf) sobre los partidos de la ventana.
    El resultado es matemáticamente idéntico a re-ejecutar el filtro completo en cada iteración.
    """
    psi_base = Psi.desde_dict(cfg["psi_r"])
    tabs = tabla.construir_todas(tuple(cfg["lbar"]), psi_base.sigma_eps, psi_base.rho_eps)

    s2_gen = psi_base.sigma_r ** 2
    s2_ch = s2_gen if psi_base.sigma_r_challenger is None else psi_base.sigma_r_challenger ** 2
    conv = {}

    def tabla_de(f, s, nivel):
        base, s2 = tabs[(f, s)], (s2_ch if nivel else s2_gen)
        if s2 <= 0.0:
            return base
        if (id(base), s2) not in conv:
            conv[(id(base), s2)] = tabla.convolucionar(base, s2)
        return conv[(id(base), s2)]

    t0 = time.time()
    log(f"  Ejecutando filtro base una vez para extraer trayectoria de rho...")
    sal = filtrar(d, psi_base, tabs)
    log(f"  Filtro completado en {time.time() - t0:.1f} s. Extrayendo partidos de la ventana {VENTANA_AJUSTE}...")

    t = d.p.temporada.to_numpy()
    sel = np.isfinite(sal.rho) & d.liquida & (t >= VENTANA_AJUSTE[0]) & (t <= VENTANA_AJUSTE[1])
    
    fmt = d.p.fmt.to_numpy()[sel]
    sup = d.p.sup.to_numpy()[sel]
    niv = (d.p.nivel.to_numpy() if "nivel" in d.p else np.zeros(len(d.p), int))[sel]
    rhos = sal.rho[sel]
    vars_ = sal.var_rho[sel]
    ys = d.y1[sel].astype(int)

    items = [(tabla_de(int(f), int(s), int(nv)), float(r), float(v), int(y))
             for f, s, nv, r, v, y in zip(fmt, sup, niv, rhos, vars_, ys)]
    log(f"  {len(items)} partidos para optimización de c_inf.")

    evaluados = {}

    def objetivo(c: float) -> float:
        if c in evaluados:
            return evaluados[c]
        ll = 0.0
        for tb, r, v, y in items:
            p = tb.prob(r, v, c)
            p = 1e-12 if p < 1e-12 else (1.0 - 1e-12 if p > 1.0 - 1e-12 else p)
            ll += math.log(p) if y == 1 else math.log(1.0 - p)
        evaluados[c] = ll
        return ll

    ll_base = objetivo(0.0)
    log(f"  c_inf = 0.000000 -> ll ajuste = {ll_base:.3f}")

    t_opt = time.time()
    c_opt, ll_opt = busqueda_dorada(objetivo, 0.0, hi_cinf)
    log(f"  Busqueda dorada ({len(evaluados)} evals) en {time.time() - t_opt:.2f} s: c_inf = {c_opt:.6f}, ll = {ll_opt:.3f} (delta = {ll_opt - ll_base:+.3f})")

    return {
        "c_inf": c_opt,
        "ll_ajuste_base": ll_base,
        "ll_ajuste_opt": ll_opt,
        "delta_ll_ajuste": ll_opt - ll_base,
        "n_evaluaciones": len(evaluados),
    }


def evaluar_calibracion(d, cfg: dict, c_inf: float, rng, reps: int) -> dict:
    """Walk-forward 2019–2024 con c_inf estimado y compuerta G-calibración."""
    from dataclasses import replace
    psi = replace(Psi.desde_dict(cfg["psi_r"]), c_inf=c_inf)
    tabs = tabla.construir_todas(tuple(cfg["lbar"]), psi.sigma_eps, psi.rho_eps)

    s2_gen = psi.sigma_r ** 2
    s2_ch = s2_gen if psi.sigma_r_challenger is None else psi.sigma_r_challenger ** 2
    conv = {}

    def tabla_de(f, s, nivel):
        base, s2 = tabs[(f, s)], (s2_ch if nivel else s2_gen)
        if s2 <= 0.0:
            return base
        if (id(base), s2) not in conv:
            conv[(id(base), s2)] = tabla.convolucionar(base, s2)
        return conv[(id(base), s2)]

    sal = filtrar(d, psi, tabs)
    t = d.p.temporada.to_numpy()
    sel = np.isfinite(sal.pi) & d.liquida & (t >= EVAL[0]) & (t <= EVAL[1])
    y_ev, pi_ev = d.y1[sel], sal.pi[sel]

    fmt = d.p.fmt.to_numpy()[sel]
    sup = d.p.sup.to_numpy()[sel]
    niv = (d.p.nivel.to_numpy() if "nivel" in d.p else np.zeros(len(d.p), int))[sel]
    rhos = sal.rho[sel]
    vars_ = sal.var_rho[sel]
    pi_base_ev = np.array([tabla_de(int(f), int(s), int(nv)).prob(float(r), float(v), 0.0)
                           for f, s, nv, r, v in zip(fmt, sup, niv, rhos, vars_)])

    cal_cinf = ev.calibracion(y_ev, pi_ev, rng, reps)
    cal_base = ev.calibracion(y_ev, pi_base_ev, rng, reps)

    pasa = (cal_cinf["pend_lo"] <= 1 <= cal_cinf["pend_hi"]
            and abs(cal_cinf["pendiente"] - 1) <= 0.10
            and cal_cinf["int_lo"] <= 0 <= cal_cinf["int_hi"])

    log(f"  G-calibración c_inf={c_inf:.5f}: pendiente {cal_cinf['pendiente']:.4f} "
        f"IC95 [{cal_cinf['pend_lo']:.4f}, {cal_cinf['pend_hi']:.4f}] "
        f"intercepto {cal_cinf['intercepto']:.4f} IC95 [{cal_cinf['int_lo']:.4f}, {cal_cinf['int_hi']:.4f}] "
        f"-> {'PASA' if pasa else 'FALLA'}")
    log(f"  base (c_inf=0): pendiente {cal_base['pendiente']:.4f} IC95 [{cal_base['pend_lo']:.4f}, {cal_base['pend_hi']:.4f}]")

    mets_cinf = ev.metricas(y_ev, pi_ev)
    mets_base = ev.metricas(y_ev, pi_base_ev)
    log(f"  log-loss eval: base {mets_base['logloss']:.5f}  c_inf {mets_cinf['logloss']:.5f}  "
        f"delta = {mets_cinf['logloss'] - mets_base['logloss']:+.5f}")

    return {
        "G_calibracion": {"pasa": pasa, **cal_cinf},
        "G_calibracion_base": cal_base,
        "metricas_cinf": mets_cinf,
        "metricas_base": mets_base,
        "n_evaluados": int(sel.sum()),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--circuitos", nargs="+", default=["atp", "wta"])
    ap.add_argument("--reps", type=int, default=ev.REPS)
    ap.add_argument("--hi", type=float, default=0.5, help="límite superior de la búsqueda de c_inf")
    ap.add_argument("--dir", default=str(SALIDA))
    ap.add_argument("--dry-run", action="store_true", help="no guarda nada en hiperparametros.json")
    a = ap.parse_args()

    salida = Path(a.dir)
    hpj = hp.leer(salida / "hiperparametros.json")
    rng = np.random.default_rng(SEMILLA)

    p, e = dm.cargar_export(hasta=2024)
    resultados = {}

    for c in a.circuitos:
        log(f"\n=== Circuito {c.upper()} - estimacion c_inf ===")
        cfg = hpj["circuitos"][c]
        d = dm.preparar(p, e, c, 2024)

        est = estimar_circuito(d, cfg, hi_cinf=a.hi)
        log(f"\n--- {c.upper()} - evaluacion walk-forward 2019-2024 ---")
        evaluacion = evaluar_calibracion(d, cfg, est["c_inf"], rng, a.reps)

        resultados[c] = {"estimacion": est, "evaluacion": evaluacion}
        pasa = evaluacion["G_calibracion"]["pasa"]
        log(f"\n{c.upper()}: c_inf = {est['c_inf']:.6f}  G-calibracion {'PASA' if pasa else 'FALLA'}")
        if not pasa:
            log(f"ATENCION: G-calibracion no pasa para {c}. Revisar diagnostico antes de continuar.")

    # Guardar resultado en hiperparametros.json (solo si --dry-run no está activo)
    if not a.dry_run:
        hpj_actual = hp.leer(salida / "hiperparametros.json")
        for c in a.circuitos:
            c_inf_val = resultados[c]["estimacion"]["c_inf"]
            hpj_actual["circuitos"][c]["psi_r"]["c_inf"] = c_inf_val
            hpj_actual["circuitos"][c]["c_inf"] = c_inf_val
            hpj_actual["circuitos"][c]["c_inf_evaluacion"] = resultados[c]["evaluacion"]
            log(f"Guardando c_inf = {c_inf_val:.6f} para {c} en hiperparametros.json")
        hpj_actual["c_inf_fecha"] = "2026-11-07"
        hpj_actual["c_inf_protocolo"] = (
            "factor de inflación de varianza predictiva (opción A): v_pred = v + c_inf, solo en Tabla.prob(); "
            "estimado por MV predictiva ≤ 2018 (búsqueda dorada); Ψ congelado; evaluado en 2019–2024"
        )
        hp.escribir(salida / "hiperparametros.json", hpj_actual)
        log(f"hiperparametros.json actualizado con c_inf.")
    else:
        log("\n--dry-run: no se escribió nada.")

    # Resumen final
    log("\n=== RESUMEN ===")
    for c in a.circuitos:
        est = resultados[c]["estimacion"]
        cal = resultados[c]["evaluacion"]["G_calibracion"]
        log(f"  {c.upper()}: c_inf = {est['c_inf']:.6f}  pendiente = {cal['pendiente']:.4f} "
            f"IC95 [{cal['pend_lo']:.4f}, {cal['pend_hi']:.4f}]  "
            f"{'PASA' if cal['pasa'] else 'FALLA'}")

    (salida / "c_inf_resultado.json").write_text(
        json.dumps(resultados, indent=1, ensure_ascii=False, default=float), encoding="utf-8"
    )
    log(f"Resultado completo en {salida / 'c_inf_resultado.json'}")


if __name__ == "__main__":
    sys.exit(main())
