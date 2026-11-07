"""Prueba preregistrada de persistencia de presión / factor clutch (plan técnico §E.4, Paso 0).

Calcula la persistencia entre temporadas consecutivas del residuo de puntos de break:
    r_{i,m} = bp_salvados - bp_afrontados · p̃_{i,m}
con p̃ la proporción de puntos de saque ganados fuera de los break points.
Media estandarizada por jugador y temporada (jugadores con ≥ 50 break points afrontados).

Criterio preregistrado (§E.4):
    Si r < 0,10 o su IC95 (bootstrap por jugador) incluye 0, se descarta clutch por jugador
    (modelo P2) y se conserva P0 (IID + efecto aleatorio del partido).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

BASE_EXPORT = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\export_pit")
SALIDA_S4 = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\modelo_s4")
SEMILLA_DEFECTO = 20261105
UMBRAL_BP_TEMPORADA = 50
REPS_BOOTSTRAP = 2000


def calcular_residuos_partido(df_saque: pd.DataFrame, df_partidos: pd.DataFrame, hasta_temporada: int = 2024) -> pd.DataFrame:
    """Calcula el residuo r_{i,m} = bp_salvados - bp_afrontados * p̃ para cada jugador y partido."""
    cols_part = ["partido_key", "corte_utc", "circuito", "temporada"]
    m = df_saque.merge(df_partidos[cols_part], on="partido_key", how="inner")
    if hasta_temporada is not None:
        m = m[m["temporada"] <= hasta_temporada].copy()

    # Filtro de coherencia física
    ok = (
        (m["bp_afrontados"] > 0)
        & (m["puntos_saque"] > m["bp_afrontados"])
        & (m["puntos_saque_ganados"] >= m["bp_salvados"])
        & (m["bp_salvados"] >= 0)
    )
    v = m[ok].copy()

    n_nobp = v["puntos_saque"] - v["bp_afrontados"]
    w_nobp = v["puntos_saque_ganados"] - v["bp_salvados"]
    p_tilde = w_nobp / n_nobp

    v["residuo"] = v["bp_salvados"] - v["bp_afrontados"] * p_tilde
    return v


def agregar_por_jugador_temporada(df_residuos: pd.DataFrame, min_bp: int = UMBRAL_BP_TEMPORADA) -> pd.DataFrame:
    """Agrega residuos por (circuito, jugador_id, temporada) y estandariza."""
    ag = (
        df_residuos.groupby(["circuito", "jugador_id", "temporada"])
        .agg(
            bp_tot=("bp_afrontados", "sum"),
            bp_salvados=("bp_salvados", "sum"),
            res_sum=("residuo", "sum"),
            n_partidos=("partido_key", "count"),
        )
        .reset_index()
    )

    ag_fil = ag[ag["bp_tot"] >= min_bp].copy()
    ag_fil["res_std"] = ag_fil["res_sum"] / np.sqrt(ag_fil["bp_tot"])
    return ag_fil


def emparejar_temporadas_consecutivas(df_ag: pd.DataFrame) -> pd.DataFrame:
    """Empareja temporadas consecutivas (t, t+1) para cada jugador."""
    df_ord = df_ag.sort_values(["circuito", "jugador_id", "temporada"]).copy()
    df_ord["temp_sig"] = df_ord.groupby(["circuito", "jugador_id"])["temporada"].shift(-1)
    df_ord["res_sig"] = df_ord.groupby(["circuito", "jugador_id"])["res_std"].shift(-1)

    pares = df_ord[df_ord["temp_sig"] == df_ord["temporada"] + 1].dropna(subset=["res_sig"]).copy()
    return pares


def bootstrap_spearman(pares: pd.DataFrame, reps: int = REPS_BOOTSTRAP, semilla: int = SEMILLA_DEFECTO) -> tuple[float, float]:
    """Bootstrap remuestreando JUGADORES (clusters), para no romper la correlación intra-jugador."""
    jugadores = pares["jugador_id"].unique()
    n_jug = len(jugadores)
    rng = np.random.default_rng(semilla)

    indices_por_jugador = {j: pares.index[pares["jugador_id"] == j].to_numpy() for j in jugadores}

    valores_r = []
    for _ in range(reps):
        jug_muestra = rng.choice(jugadores, size=n_jug, replace=True)
        idx_muestra = np.concatenate([indices_por_jugador[j] for j in jug_muestra])
        sub = pares.loc[idx_muestra]
        r, _ = spearmanr(sub["res_std"], sub["res_sig"])
        if np.isfinite(r):
            valores_r.append(r)

    lo = float(np.percentile(valores_r, 2.5))
    hi = float(np.percentile(valores_r, 97.5))
    return lo, hi


def evaluar_paso_0(
    df_saque: pd.DataFrame,
    df_partidos: pd.DataFrame,
    hasta_temporada: int = 2024,
    reps: int = REPS_BOOTSTRAP,
    semilla: int = SEMILLA_DEFECTO,
) -> dict:
    t0 = time.time()
    residuos = calcular_residuos_partido(df_saque, df_partidos, hasta_temporada=hasta_temporada)
    agregado = agregar_por_jugador_temporada(residuos, min_bp=UMBRAL_BP_TEMPORADA)
    pares = emparejar_temporadas_consecutivas(agregado)

    resultados = {
        "fecha": pd.Timestamp.now(tz="UTC").isoformat(),
        "umbral_bp_temporada": UMBRAL_BP_TEMPORADA,
        "hasta_temporada": hasta_temporada,
        "filas_saque_validas": len(residuos),
        "circuitos": {},
    }

    for circ in ["atp", "wta"]:
        p_circ = pares[pares["circuito"] == circ].copy()
        n_pares = len(p_circ)
        n_jug = p_circ["jugador_id"].nunique()

        r_est, pval = spearmanr(p_circ["res_std"], p_circ["res_sig"])
        r_est = float(r_est)
        pval = float(pval)

        lo, hi = bootstrap_spearman(p_circ, reps=reps, semilla=semilla)

        # Regla §E.4: si r < 0.10 o IC95 incluye 0, clutch descartado
        hay_clutch = (r_est >= 0.10) and (lo > 0.0)
        criterio = "descarta_p2" if not hay_clutch else "procede_a_p1_p2"

        resultados["circuitos"][circ] = {
            "n_pares_consecutivos": n_pares,
            "n_jugadores_unicos": n_jug,
            "spearman_r": r_est,
            "p_valor": pval,
            "ic95_lo": lo,
            "ic95_hi": hi,
            "umbral_preregistrado_r": 0.10,
            "r_menor_que_umbral": r_est < 0.10,
            "ic95_incluye_cero": lo <= 0.0 <= hi,
            "decision": criterio,
        }

    # Decisión conjunta
    p2_descartado = all(c["decision"] == "descarta_p2" for c in resultados["circuitos"].values())
    resultados["decision_final"] = (
        "P2_DESCARTADO (sin clutch individual persistente por jugador; se conserva P0 IID + efecto del partido)"
        if p2_descartado
        else "EVALUAR_P1_P2"
    )
    resultados["segundos_computo"] = round(time.time() - t0, 2)
    return resultados


def main():
    parser = argparse.ArgumentParser(description="Prueba preregistrada de persistencia de presión (§E.4)")
    parser.add_argument("--export", default=str(BASE_EXPORT), help="Ruta a carpeta export_pit")
    parser.add_argument("--salida", default=str(SALIDA_S4), help="Ruta a carpeta modelo_s4")
    parser.add_argument("--reps", type=int, default=REPS_BOOTSTRAP, help="Réplicas bootstrap")
    parser.add_argument("--semilla", type=int, default=SEMILLA_DEFECTO, help="Semilla aleatoria")
    parser.add_argument("--hasta", type=int, default=2024, help="Última temporada permitida (≤ 2024)")
    args = parser.parse_args()

    dir_export = Path(args.export)
    dir_salida = Path(args.salida)
    dir_salida.mkdir(parents=True, exist_ok=True)

    print(f"Cargando estadísticas de saque y partidos desde {dir_export}...", flush=True)
    df_saque = pd.read_parquet(dir_export / "estadisticas_saque.parquet")
    df_partidos = pd.read_parquet(dir_export / "partidos.parquet")

    print(f"Ejecutando prueba de persistencia de presión (Paso 0 §E.4) hasta {args.hasta}...", flush=True)
    res = evaluar_paso_0(df_saque, df_partidos, hasta_temporada=args.hasta, reps=args.reps, semilla=args.semilla)

    ruta_json = dir_salida / "prueba_presion.json"
    ruta_json.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 70)
    print("RESULTADOS DE LA PRUEBA PREREGISTRADA DE PRESIÓN (§E.4, Paso 0):")
    print("=" * 70)
    for circ, d in res["circuitos"].items():
        print(f"\n[{circ.upper()}] (n={d['n_pares_consecutivos']} pares, {d['n_jugadores_unicos']} jugadores):")
        print(f"  Spearman r: {d['spearman_r']:.4f} (p = {d['p_valor']:.4e})")
        print(f"  IC95 bootstrap por jugador: [{d['ic95_lo']:.4f}, {d['ic95_hi']:.4f}]")
        print(f"  ¿r < 0.10?: {d['r_menor_que_umbral']}")
        print(f"  ¿IC95 incluye 0?: {d['ic95_incluye_cero']}")
        print(f"  Decisión: {d['decision']}")

    print("\n" + "-" * 70)
    print(f"VEREDICTO FINAL: {res['decision_final']}")
    print(f"Informe guardado en: {ruta_json}")
    print("=" * 70)


if __name__ == "__main__":
    main()
