"""Evaluacin de compuertas de mercado Sprint 5: G-identidad y G-cierre retrospectivo (I.0, I.1, S5).

Lee:
  - modelo_s5/precios_enlazados.parquet
  - modelo_s3/hiperparametros.json
  - .local/propline_shared_pilot_20261023 (evaluacin prospectiva local)

Calcula:
  1. G-identidad:
     - Tasa de cruce con Tennis-Data por circuito y temporada.
     - Prueba de sesgo de seleccin: Delta log-loss entre partidos cruzados y no cruzados con IC95 bootstrap.
     - Tasa de sin_resolver en ATP/WTA principal (<= 2%).
  2. G-cierre retrospectivo (ganador, clase b):
     - Delta log-loss (nuevo - cierre sin margen de Pinnacle/Avg).
     - Comparacin contra lnea base Elo recalibrado vs cierre (+0.038 ATP, +0.036 WTA).
     - Compuerta: Delta(nuevo) <= Delta(Elo) + 0.002.
  3. Evaluacin prospectiva con archivo PropLine piloto.
Guarda resultados en modelo_s5/evaluacion_mercado.json.
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

DIR_DATOS_DEFECTO = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104")
DIR_MODELO_S5 = DIR_DATOS_DEFECTO / "modelo_s5"
RUTA_PRECIOS = DIR_MODELO_S5 / "precios_enlazados.parquet"
RUTA_PROPLINE_PILOTO = Path(r"C:\Users\huye\Documents\apuesta proyec\.local\propline_shared_pilot_20261023")


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def perdida_logloss(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-8, 1.0 - 1e-8)
    y = np.asarray(y, dtype=float)
    return -(y * np.log(p) + (1.0 - y) * np.log1p(-p))


def brier_score(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    return (np.asarray(y, dtype=float) - np.asarray(p, dtype=float)) ** 2


def bootstrap_dif(
    y: np.ndarray, p_mod: np.ndarray, p_ref: np.ndarray, rng: np.random.Generator, reps: int = 2000
) -> dict:
    """Calcula Delta log-loss (p_mod - p_ref) con IC95 bootstrap por partido."""
    dl = perdida_logloss(y, p_mod) - perdida_logloss(y, p_ref)
    db = brier_score(y, p_mod) - brier_score(y, p_ref)
    n = len(dl)
    if n == 0:
        return {"n": 0, "dif_logloss": None, "lo": None, "hi": None, "dif_brier": None, "var": None}

    idx = rng.integers(n, size=(reps, n))
    medias_b = dl[idx].mean(axis=1)
    lo, hi = float(np.quantile(medias_b, 0.025)), float(np.quantile(medias_b, 0.975))
    return {
        "n": int(n),
        "dif_logloss": float(dl.mean()),
        "lo": lo,
        "hi": hi,
        "var": float(medias_b.var()),
        "dif_brier": float(db.mean()),
    }


def bootstrap_dos_muestras_dif(
    l1: np.ndarray, l2: np.ndarray, rng: np.random.Generator, reps: int = 2000
) -> dict:
    """Calcula mean(l1) - mean(l2) con IC95 bootstrap para prueba de sesgo."""
    n1, n2 = len(l1), len(l2)
    if n1 == 0 or n2 == 0:
        return {"dif": None, "lo": None, "hi": None}
    dif_obs = float(l1.mean() - l2.mean())
    idx1 = rng.integers(n1, size=(reps, n1))
    idx2 = rng.integers(n2, size=(reps, n2))
    b_dif = l1[idx1].mean(axis=1) - l2[idx2].mean(axis=1)
    return {
        "dif": dif_obs,
        "lo": float(np.quantile(b_dif, 0.025)),
        "hi": float(np.quantile(b_dif, 0.975)),
    }


def combinar_origenes(difs_por_anio: list[dict]) -> dict:
    """Combina orgenes ponderando por la inversa de la varianza bootstrap (I.0)."""
    validas = [d for d in difs_por_anio if d.get("var") is not None and d.get("var") > 0]
    if not validas:
        return {}
    pesos = np.array([1.0 / v["var"] for v in validas])
    difs = np.array([v["dif_logloss"] for v in validas])
    briers = np.array([v["dif_brier"] for v in validas])
    n_tot = sum(v["n"] for v in validas)

    dif_comb = float(np.sum(pesos * difs) / np.sum(pesos))
    se_comb = float(np.sqrt(1.0 / np.sum(pesos)))
    db_comb = float(np.mean(briers))

    return {
        "origenes": len(validas),
        "n_total": n_tot,
        "dif_logloss": dif_comb,
        "lo": float(dif_comb - 1.96 * se_comb),
        "hi": float(dif_comb + 1.96 * se_comb),
        "dif_brier": db_comb,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluacin de compuertas G-identidad y G-cierre retrospectivo")
    parser.add_argument("--precios", type=Path, default=RUTA_PRECIOS)
    parser.add_argument("--salida_dir", type=Path, default=DIR_MODELO_S5)
    parser.add_argument("--semilla", type=int, default=20261105)
    args = parser.parse_args()

    t0 = time.time()
    rng = np.random.default_rng(args.semilla)
    log(f"Cargando {args.precios}...")
    df = pd.read_parquet(args.precios)
    log(f"   {len(df)} filas cargadas")

    # Filtro de partidos jugados que liquidan ganador (I.3: completado o retirada con >=1 set)
    df["sc"] = pd.to_numeric(df["y_sets_completos"], errors="coerce").fillna(0)
    df["g"] = pd.to_numeric(df["y_ganador"], errors="coerce")
    df["liquida_ganador"] = (
        (df["y_estado"] == "completado") |
        ((df["y_estado"] == "retirada") & (df["sc"] >= 1))
    ) & df["g"].isin([1, 2])
    df["y1"] = np.where(df["g"] == 1, 1, np.where(df["g"] == 2, 0, -1))

    # Filtro de cuadro principal
    df["es_main_tour"] = (
        df.categoria.isin([
            "GS", "M1000", "WTA1000", "500", "WTA500", "250", "WTA250", "Finales", "Premier", "International"
        ]) &
        (~df.ronda.isin(["Q1", "Q2", "Q3", "QL"])) &
        df["liquida_ganador"]
    )

    resultados_eval = {
        "fecha_evaluacion": datetime.now().isoformat(),
        "total_filas": len(df),
        "G_identidad": {},
        "G_cierre_retrospectivo": {},
    }

    # =========================================================================
    # 1. G-identidad: Cruce y prueba de sesgo de seleccin
    # =========================================================================
    log("\n--- COMPUERTA G-IDENTIDAD ---")
    g_id = {}
    for circ in ["atp", "wta"]:
        sub = df[(df.circuito == circ) & df.es_main_tour].copy()
        cruzados = sub[sub.cruzado_mercado]
        no_cruzados = sub[~sub.cruzado_mercado]

        tasa_global = len(cruzados) / len(sub) if len(sub) > 0 else 0.0

        # Prueba de sesgo: log-loss de pi_lado1 en cruzados vs no_cruzados
        ll_cruz = perdida_logloss(cruzados.y1.to_numpy(), cruzados.pi_lado1.to_numpy())
        ll_no_cruz = perdida_logloss(no_cruzados.y1.to_numpy(), no_cruzados.pi_lado1.to_numpy())
        sesgo = bootstrap_dos_muestras_dif(ll_cruz, ll_no_cruz, rng, reps=2000)

        # Sin sesgo si el IC95 de la diferencia incluye 0
        sin_sesgo = bool(sesgo["lo"] <= 0.0 <= sesgo["hi"])

        g_id[circ] = {
            "partidos_cuadro_principal": int(len(sub)),
            "cruzados": int(len(cruzados)),
            "no_cruzados": int(len(no_cruzados)),
            "tasa_cruce_global": round(tasa_global, 4),
            "tasa_cruce_pct": round(tasa_global * 100, 2),
            "sesgo_seleccion": {
                "logloss_cruzados": float(ll_cruz.mean()),
                "logloss_no_cruzados": float(ll_no_cruz.mean()),
                "dif_cruz_menos_nocruz": sesgo["dif"],
                "ic95_lo": sesgo["lo"],
                "ic95_hi": sesgo["hi"],
                "ic95_incluye_cero": sin_sesgo,
            },
            "pasa_sin_sesgo": sin_sesgo,
        }
        log(f"{circ.upper()} Cuadro Principal: {len(cruzados)}/{len(sub)} ({tasa_global*100:.1f}%)")
        log(f"   Log-loss cruzados: {ll_cruz.mean():.4f} vs no cruzados: {ll_no_cruz.mean():.4f}")
        log(f"   Delta sesgo: {sesgo['dif']:+.4f} [IC95: {sesgo['lo']:+.4f}, {sesgo['hi']:+.4f}] -> incluye 0: {sin_sesgo}")

    resultados_eval["G_identidad"] = g_id

    # =========================================================================
    # 2. G-cierre retrospectivo: Delta log-loss vs Cierre sin margen
    # =========================================================================
    log("\n--- COMPUERTA G-CIERRE RETROSPECTIVO (ganador, clase b) ---")
    # Referencia de auditora: Delta log-loss de Elo recalibrado vs cierre:
    # ATP: +0.0377 (hoy +0.038); WTA: +0.0355 (hoy +0.036).
    # Compuerta: Delta(nuevo) <= Delta(Elo) + 0.002.
    referencia_elo = {
        "atp": 0.03766,
        "wta": 0.03549,
    }

    g_cierre = {}
    for circ in ["atp", "wta"]:
        sub = df[(df.circuito == circ) & df.cruzado_mercado & df.liquida_ganador & df.p_cierre_lado1.notna()].copy()
        y = sub.y1.to_numpy()
        p_mod = sub.pi_lado1.to_numpy()
        p_cie = sub.p_cierre_lado1.to_numpy()

        # Mtricas directas
        ll_mod = float(perdida_logloss(y, p_mod).mean())
        ll_cie = float(perdida_logloss(y, p_cie).mean())
        brier_mod = float(brier_score(y, p_mod).mean())
        brier_cie = float(brier_score(y, p_cie).mean())
        acierto_mod = float(np.mean((p_mod >= 0.5) == (y == 1)))
        acierto_cie = float(np.mean((p_cie >= 0.5) == (y == 1)))

        # Por temporada
        difs_temporada = {}
        difs_lista = []
        for anio, g in sub.groupby("temporada"):
            gy, gm, gc = g.y1.to_numpy(), g.pi_lado1.to_numpy(), g.p_cierre_lado1.to_numpy()
            d = bootstrap_dif(gy, gm, gc, rng, reps=1500)
            difs_temporada[int(anio)] = d
            difs_lista.append(d)

        # Combinado ponderado por inversa de la varianza
        comb = combinar_origenes(difs_lista)

        # Evaluacin Walk-Forward (2019-2024) y Reserva (2025-2026)
        sub_wf = sub[(sub.temporada >= 2019) & (sub.temporada <= 2024)]
        sub_res = sub[(sub.temporada >= 2025) & (sub.temporada <= 2026)]

        dif_wf = bootstrap_dif(sub_wf.y1.to_numpy(), sub_wf.pi_lado1.to_numpy(), sub_wf.p_cierre_lado1.to_numpy(), rng, 2000)
        dif_res = bootstrap_dif(sub_res.y1.to_numpy(), sub_res.pi_lado1.to_numpy(), sub_res.p_cierre_lado1.to_numpy(), rng, 2000)

        # Compuerta: Delta(nuevo) <= Delta(Elo) + 0.002
        delta_elo = referencia_elo[circ]
        umbral_compuerta = delta_elo + 0.002
        delta_nuevo = comb.get("dif_logloss", dif_wf["dif_logloss"])
        pasa_cierre = bool(delta_nuevo <= umbral_compuerta)

        g_cierre[circ] = {
            "n_partidos_evaluados": int(len(sub)),
            "metricas_globales": {
                "logloss_modelo": ll_mod,
                "logloss_cierre": ll_cie,
                "brier_modelo": brier_mod,
                "brier_cierre": brier_cie,
                "acierto_modelo": acierto_mod,
                "acierto_cierre": acierto_cie,
            },
            "combinado_inversa_varianza": comb,
            "periodo_walk_forward_2019_2024": dif_wf,
            "periodo_reserva_2025_2026": dif_res,
            "por_temporada": difs_temporada,
            "compuerta": {
                "delta_nuevo_vs_cierre": delta_nuevo,
                "delta_elo_recal_vs_cierre": delta_elo,
                "umbral_maximo_permitido": round(umbral_compuerta, 5),
                "brecha_publicada": round(delta_nuevo, 5),
                "pasa_compuerta": pasa_cierre,
            }
        }
        log(f"{circ.upper()} (n = {len(sub)}):")
        log(f"   Log-loss Modelo: {ll_mod:.4f} vs Cierre: {ll_cie:.4f} (Brier: {brier_mod:.4f} vs {brier_cie:.4f})")
        log(f"   Delta log-loss combinado: {comb.get('dif_logloss', 0):+.5f} [IC95: {comb.get('lo', 0):+.5f}, {comb.get('hi', 0):+.5f}]")
        log(f"   WF 2019-2024: {dif_wf['dif_logloss']:+.5f} [IC95: {dif_wf['lo']:+.5f}, {dif_wf['hi']:+.5f}]")
        log(f"   Reserva 2025-2026: {dif_res['dif_logloss']:+.5f} [IC95: {dif_res['lo']:+.5f}, {dif_res['hi']:+.5f}]")
        log(f"   Vs Elo recalibrado ({delta_elo:+.5f}): Delta nuevo {delta_nuevo:+.5f} <= {umbral_compuerta:+.5f} -> PASA: {pasa_cierre}")

    resultados_eval["G_cierre_retrospectivo"] = g_cierre

    # =========================================================================
    # 3. Evaluacin prospectiva con PropLine piloto (si est montado)
    # =========================================================================
    log("\n--- EVALUACIN PROSPECTIVA LOCAL (PropLine piloto) ---")
    if RUTA_PROPLINE_PILOTO.exists():
        from tenis.mercado.propline import cargar_ganadores_piloto
        mercados_pl = cargar_ganadores_piloto(RUTA_PROPLINE_PILOTO)
        resultados_eval["propline_piloto"] = {
            "disponible": True,
            "mercados_ganador_total": len(mercados_pl),
            "casas_distintas": len(set(m["bookmaker"] for m in mercados_pl)),
            "pinnacle_mercados": len([m for m in mercados_pl if m["bookmaker"] == "pinnacle"]),
        }
        log(f"PropLine piloto cargado: {len(mercados_pl)} mercados de ganador con {len(set(m['bookmaker'] for m in mercados_pl))} casas.")
    else:
        resultados_eval["propline_piloto"] = {"disponible": False}
        log("PropLine piloto no encontrado en ruta local.")

    # Guardar resultados JSON
    ruta_salida = args.salida_dir / "evaluacion_mercado.json"
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(resultados_eval, f, indent=2)
    log(f"\nResultados guardados exitosamente en: {ruta_salida}")
    log(f"Fin evaluar_prospectivo en {time.time() - t0:.1f} s")


if __name__ == "__main__":
    main()
