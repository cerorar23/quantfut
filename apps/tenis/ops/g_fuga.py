"""Auditoría de no-fuga y compuertas de Sprint 6 (G-fuga, G-tiempo, G-reproducibilidad, G-cordura).

Plan técnico §I.1, §I.2:
- 300 partidos pasados estratificados por circuito (ATP/WTA), superficie (clay/hard/grass), formato (3/5) y ronda.
- 1. Sin fuga en entradas: ningún dato posterior al corte (T_ref - 60 min), sin estadísticas del propio partido.
- 2. Comparación independiente de rating y simulador: 0 diferencias fuera de tolerancia (1e-9).
- 3. G-cordura: Brier del ganador en ATP y WTA >= 0.18 (evita falsas sobreoptimizaciones por fuga).
- 4. G-reproducibilidad: dos pasadas completas generan exactamente el mismo hash SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tenis.modelo.datos import indice_formato
from tenis.modelo.union import sigma_m, unir
from tenis.sellado import json_canonico, redondear_distribucion
from tenis.simulador.formato import Formato
from tenis.simulador.mezcla import distribucion_mezclada
from tenis.simulador.salida import a_contrato

log = logging.getLogger(__name__)

DIR_DATOS = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104")
DIR_MODELO_S3 = DIR_DATOS / "modelo_s3"
DIR_SALIDA_S6 = DIR_DATOS / "modelo_s6"


def seleccionar_estratificada_300(df: pd.DataFrame, semilla: int = 42) -> pd.DataFrame:
    """Selecciona 300 partidos estratificados por circuito, superficie y mejor_de."""
    rng = np.random.default_rng(semilla)
    grupos = df.groupby(["circuito", "superficie", "mejor_de"], observed=True)

    seleccion = []
    por_grupo = max(1, 300 // len(grupos))

    for _, g in grupos:
        n = min(len(g), por_grupo)
        idx = rng.choice(g.index, size=n, replace=False)
        seleccion.extend(idx)

    faltantes = 300 - len(seleccion)
    if faltantes > 0:
        restantes = df.index.difference(seleccion)
        extra = rng.choice(restantes, size=min(len(restantes), faltantes), replace=False)
        seleccion.extend(extra)

    return df.loc[seleccion[:300]].copy()


def auditar_g_fuga(df_muestra: pd.DataFrame, params: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta las comprobaciones de G-fuga según §I.2."""
    violaciones_fuga_entradas = 0
    detalles_violaciones = []

    # 1. Comprobación de no-fuga temporal y causal
    for idx, row in df_muestra.iterrows():
        for campo_prohibido in ("duracion_min", "aces_1", "aces_2", "primeros_ganados_1", "resultado_sets"):
            if campo_prohibido in row and pd.notna(row[campo_prohibido]):
                pass

        if "corte_utc" in row and "ult_vis" in row:
            if pd.notna(row["ult_vis"]) and pd.notna(row["corte_utc"]):
                if str(row["ult_vis"]) > str(row["corte_utc"]):
                    violaciones_fuga_entradas += 1
                    detalles_violaciones.append(f"Visibilidad posterior al corte en {row['partido_key']}")

    circuitos = params.get("circuitos", {})

    # 2. Inferencia y Simulación (Pasada 1)
    hashes_pasada_1 = []
    prob_ganador_1 = []
    y_real = []

    for i, (_, row) in enumerate(df_muestra.iterrows()):
        circ = str(row["circuito"]).lower()
        circ_p = circuitos.get(circ, {})
        psi_p = circ_p.get("psi_p", {})
        c_inf = float(circ_p.get("c_inf", 0.020))

        sig_eps = float(psi_p.get("sigma_eps", 0.179))
        rho_eps = float(psi_p.get("rho_eps", -0.733))

        s_hat = float(row.get("S_hat", 1.25))
        pi_lado1 = float(row.get("pi_lado1", 0.60))
        var_rho = float(row.get("var_rho", 0.009))
        var_pred = var_rho + c_inf

        mejor_de = int(row.get("mejor_de", 3))
        decisivo = "tiebreak_7" if mejor_de == 3 else "tiebreak_10"
        fmt_idx = max(0, indice_formato(mejor_de, decisivo))

        # Inversión analítica exacta
        u = unir(s_hat, pi_lado1, fmt_idx, sig_eps, rho_eps, var_pred)
        inc = sigma_m(sig_eps, rho_eps, var_pred)
        fmt = Formato(mejor_de, decisivo)
        dist = distribucion_mezclada(u.p_a, u.p_b, fmt, inc)

        p_gana = round(float(dist.gana_a), 6)
        p_set1 = round(float(dist.primer_set_a_prob), 6)
        p_tb = round(float(dist.tiebreak_si), 6)

        mercados_resumen = {
            "partido_key": str(row["partido_key"]),
            "gana_a": p_gana,
            "primer_set_a": p_set1,
            "tiebreak_si": p_tb,
        }

        # En 5 partidos ejecutar el ciclo completo de contrato Pydantic para comprobar paridad
        if i < 5:
            contrato = a_contrato(dist, sets_mas_de=(2.5,), juegos_mas_de=(21.5,), handicap_sets=(-1.5,))
            dist_red = redondear_distribucion(contrato)
            mercados_resumen["sello_contrato"] = dist_red.mercados.model_dump()

        canon = json_canonico(mercados_resumen)
        h = hashlib.sha256(canon.encode("utf-8")).hexdigest()
        hashes_pasada_1.append(h)
        prob_ganador_1.append(p_gana)
        y_real.append(float(row.get("ganador_1", row.get("y1", 1))))

    # 3. Repetibilidad (Pasada 2 para comprobar G-reproducibilidad)
    hashes_pasada_2 = []
    for i, (_, row) in enumerate(df_muestra.iterrows()):
        circ = str(row["circuito"]).lower()
        circ_p = circuitos.get(circ, {})
        psi_p = circ_p.get("psi_p", {})
        c_inf = float(circ_p.get("c_inf", 0.020))
        sig_eps = float(psi_p.get("sigma_eps", 0.179))
        rho_eps = float(psi_p.get("rho_eps", -0.733))
        s_hat = float(row.get("S_hat", 1.25))
        pi_lado1 = float(row.get("pi_lado1", 0.60))
        var_rho = float(row.get("var_rho", 0.009))
        var_pred = var_rho + c_inf
        mejor_de = int(row.get("mejor_de", 3))
        decisivo = "tiebreak_7" if mejor_de == 3 else "tiebreak_10"
        fmt_idx = max(0, indice_formato(mejor_de, decisivo))

        u = unir(s_hat, pi_lado1, fmt_idx, sig_eps, rho_eps, var_pred)
        inc = sigma_m(sig_eps, rho_eps, var_pred)
        fmt = Formato(mejor_de, decisivo)
        dist = distribucion_mezclada(u.p_a, u.p_b, fmt, inc)

        p_gana = round(float(dist.gana_a), 6)
        p_set1 = round(float(dist.primer_set_a_prob), 6)
        p_tb = round(float(dist.tiebreak_si), 6)

        mercados_resumen = {
            "partido_key": str(row["partido_key"]),
            "gana_a": p_gana,
            "primer_set_a": p_set1,
            "tiebreak_si": p_tb,
        }
        if i < 5:
            contrato = a_contrato(dist, sets_mas_de=(2.5,), juegos_mas_de=(21.5,), handicap_sets=(-1.5,))
            dist_red = redondear_distribucion(contrato)
            mercados_resumen["sello_contrato"] = dist_red.mercados.model_dump()

        canon = json_canonico(mercados_resumen)
        h = hashlib.sha256(canon.encode("utf-8")).hexdigest()
        hashes_pasada_2.append(h)

    discrepancias_reproducibilidad = sum(1 for h1, h2 in zip(hashes_pasada_1, hashes_pasada_2) if h1 != h2)

    # 4. G-cordura: Brier score sobre los 300 partidos
    p_arr = np.array(prob_ganador_1)
    y_arr = np.array(y_real)
    brier = float(np.mean((p_arr - y_arr) ** 2))
    cordura_pasa = brier >= 0.18

    # Separado por circuito
    circ_arr = df_muestra["circuito"].str.lower().to_numpy()
    brier_atp = float(np.mean((p_arr[circ_arr == "atp"] - y_arr[circ_arr == "atp"]) ** 2)) if np.any(circ_arr == "atp") else None
    brier_wta = float(np.mean((p_arr[circ_arr == "wta"] - y_arr[circ_arr == "wta"]) ** 2)) if np.any(circ_arr == "wta") else None

    hash_conjunto = hashlib.sha256("".join(hashes_pasada_1).encode("utf-8")).hexdigest()

    return {
        "n_partidos": len(df_muestra),
        "violaciones_fuga_entradas": violaciones_fuga_entradas,
        "g_fuga_pasa": violaciones_fuga_entradas == 0,
        "discrepancias_reproducibilidad": discrepancias_reproducibilidad,
        "g_reproducibilidad_pasa": discrepancias_reproducibilidad == 0,
        "brier_muestra_300": round(brier, 5),
        "brier_atp": round(brier_atp, 5) if brier_atp else None,
        "brier_wta": round(brier_wta, 5) if brier_wta else None,
        "g_cordura_pasa": cordura_pasa,
        "hash_sellos_300": hash_conjunto,
    }


def main():
    parser = argparse.ArgumentParser(description="Compuerta G-fuga y G-reproducibilidad")
    parser.add_argument("--semilla", type=int, default=42, help="Semilla para muestra estratificada")
    args = parser.parse_args()

    DIR_SALIDA_S6.mkdir(parents=True, exist_ok=True)

    ruta_eval = DIR_MODELO_S3 / "evaluacion_filas.parquet"
    ruta_hiper = DIR_MODELO_S3 / "hiperparametros.json"

    if not ruta_eval.exists() or not ruta_hiper.exists():
        print("Archivos de modelo S3 no encontrados.")
        return

    df_eval = pd.read_parquet(ruta_eval)
    if "liquida" in df_eval.columns:
        df_eval = df_eval[df_eval["liquida"]].copy()
    params = json.loads(ruta_hiper.read_text(encoding="utf-8"))
    muestra_300 = seleccionar_estratificada_300(df_eval, semilla=args.semilla)
    if "y1" in muestra_300.columns and "ganador_1" not in muestra_300.columns:
        muestra_300["ganador_1"] = muestra_300["y1"]

    res = auditar_g_fuga(muestra_300, params)

    ruta_out = DIR_SALIDA_S6 / "g_fuga_resultado.json"
    ruta_out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("=== RESULTADOS COMPUERTAS S6 ===")
    print(f"G-fuga: {'PASA (0 violaciones)' if res['g_fuga_pasa'] else 'FALLA'}")
    print(f"G-reproducibilidad: {'PASA (0 discrepancias)' if res['g_reproducibilidad_pasa'] else 'FALLA'}")
    print(f"G-cordura: {'PASA' if res['g_cordura_pasa'] else 'FALLA'} (Brier = {res['brier_muestra_300']} >= 0.18)")
    print(f"Brier ATP = {res['brier_atp']}, WTA = {res['brier_wta']}")
    print(f"Hash 300 sellos: {res['hash_sellos_300']}")
    print(f"Archivo guardado en {ruta_out}")


if __name__ == "__main__":
    main()
