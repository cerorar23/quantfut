"""Evaluación de mercados derivados y distribución conjunta en walk-forward 2019–2024 (Sprint 4, §G, §I.1).

Carga predicciones_wf.parquet (modelo S3), hiperparametros.json y partidos.parquet.
Realiza la inversión conjunta exacta y simulación analítica para cada partido completado.
Evalúa mercados:
  - Ganador (coherencia con pi_m)
  - 1.er set
  - Hándicap de sets (-1.5)
  - Total de juegos (línea principal L*, sesgo IID, cobertura 50%/80%, PIT aleatorizado, RPS)
  - Hándicap de juegos (línea principal H*, cobertura 50%/80%)
  - Tiebreak sí/no
  - Marcador exacto de sets (multiclase Brier / Logloss / RPS)
Compara contra líneas base de frecuencias empíricas y suma media constante (IID).
Calcula compuertas de §I.1 y guarda modelo_s4/evaluacion_mercados.parquet y evaluacion_mercados.json.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from tenis.modelo import evaluacion as ev
from tenis.modelo.datos import FORMATOS, indice_formato
from tenis.modelo.union import unir, sigma_m
from tenis.simulador.formato import Formato
from tenis.simulador.mezcla import SIN_INCERTIDUMBRE, Incertidumbre, distribucion_mezclada

DIR_DEFECTO_DATOS = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104")
DIR_MODELO_S3 = DIR_DEFECTO_DATOS / "modelo_s3"
DIR_MODELO_S4 = DIR_DEFECTO_DATOS / "modelo_s4"
DIR_EXPORT_PIT = DIR_DEFECTO_DATOS / "export_pit"


def log(msg: str):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def pseudo_random_from_hash(key: str) -> float:
    """PRNG determinista uniforme en (0, 1) derivado del hash del partido (reproducibilidad Windows/Linux)."""
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    val = int(h[:8], 16)
    return (val + 0.5) / (2**32)


def evaluar_un_partido(item: dict) -> dict:
    """Evalúa un único partido: inversión exacta, conjunta, mercados y contrastación con resultado real."""
    partido_key = item["partido_key"]
    circuito = item["circuito"]
    temporada = item["temporada"]
    superficie = item["superficie"]
    s_hat = item["S_hat"]
    pi_lado1 = item["pi_lado1"]
    var_rho = item["var_rho"]
    mejor_de = item["mejor_de"]
    decisivo = item["formato_decisivo"]
    fmt_idx = item["fmt_idx"]
    sig_eps = item["sigma_eps"]
    rho_eps = item["rho_eps"]
    c_inf = item["c_inf"]
    y_ganador = item["y_ganador"]
    y_sets_str = item["y_sets"]
    y_juegos_1 = item["y_juegos_1"]
    y_juegos_2 = item["y_juegos_2"]

    # 1. Inversión exacta con varianza predictiva inflada (v_pred = var_rho + c_inf)
    var_pred = float(var_rho + c_inf)
    u = unir(s_hat, pi_lado1, fmt_idx, sig_eps, rho_eps, var_pred)
    inc = sigma_m(sig_eps, rho_eps, var_pred)
    fmt = Formato(mejor_de, decisivo)
    dist = distribucion_mezclada(u.p_a, u.p_b, fmt, inc)

    # 2. Extracción de mercados derivados
    prob_ganador = float(dist.gana_a)
    dif_coherencia = abs(prob_ganador - pi_lado1)
    violacion_coherencia = dif_coherencia > 1e-6

    prob_1er_set = float(dist.primer_set_a_prob)
    prob_tiebreak = float(dist.tiebreak_si)
    media_juegos = float(dist.media_juegos)
    prob_hsets_menos_1_5 = float(dist.handicap_sets(-1.5))
    prob_hsets_mas_1_5 = float(dist.handicap_sets(1.5))

    # Total de juegos PMF y cuantiles
    ok = ~dist.cola
    jt = dist.juegos[ok].round().astype(int)
    t_min = 12 if mejor_de == 3 else 18
    t_max = 39 if mejor_de == 3 else 65
    pmf_t = np.bincount(jt, weights=dist.prob[ok], minlength=t_max + 1)
    cdf_t = np.cumsum(pmf_t)

    # Línea principal L* = argmin |P(T > L.5) - 0.5| (vectorizado)
    cand_v = np.arange(t_min, t_max)
    p_cand_t = 1.0 - cdf_t[cand_v]
    idx_l_star = int(np.argmin(np.abs(p_cand_t - 0.5)))
    l_star = cand_v[idx_l_star] + 0.5
    prob_total_mas_l = float(p_cand_t[idx_l_star])

    q10_t = int(np.searchsorted(cdf_t, 0.10))
    q25_t = int(np.searchsorted(cdf_t, 0.25))
    q75_t = int(np.searchsorted(cdf_t, 0.75))
    q90_t = int(np.searchsorted(cdf_t, 0.90))

    masa_teorica_tot_50 = float(cdf_t[min(q75_t, len(cdf_t)-1)] - (cdf_t[q25_t - 1] if q25_t > 0 else 0.0))
    masa_teorica_tot_80 = float(cdf_t[min(q90_t, len(cdf_t)-1)] - (cdf_t[q10_t - 1] if q10_t > 0 else 0.0))

    # Hándicap de juegos PMF y cuantiles
    dif = dist.dif_juegos[ok].round().astype(int)
    min_dif = int(dif.min())
    pmf_d = np.bincount(dif - min_dif, weights=dist.prob[ok])
    cdf_d = np.cumsum(pmf_d)

    # Línea principal H* = argmin |P(D + H > 0) - 0.5| (vectorizado)
    cand_h = np.arange(-15.5, 16.0, 1.0)
    cortes_d = np.ceil(-cand_h).astype(int) - min_dif
    p_cand_h = np.where(cortes_d <= 0, 1.0,
                        np.where(cortes_d > len(cdf_d), 0.0,
                                 1.0 - cdf_d[np.clip(cortes_d - 1, 0, len(cdf_d) - 1)]))
    idx_h = int(np.argmin(np.abs(p_cand_h - 0.5)))
    h_star = float(cand_h[idx_h])
    prob_handicap_cubierto = float(p_cand_h[idx_h])

    q10_d = min_dif + int(np.searchsorted(cdf_d, 0.10))
    q25_d = min_dif + int(np.searchsorted(cdf_d, 0.25))
    q75_d = min_dif + int(np.searchsorted(cdf_d, 0.75))
    q90_d = min_dif + int(np.searchsorted(cdf_d, 0.90))

    idx_q75_d = min(q75_d - min_dif, len(cdf_d) - 1)
    idx_q25_d_minus = q25_d - min_dif - 1
    masa_teorica_dif_50 = float(cdf_d[idx_q75_d] - (cdf_d[idx_q25_d_minus] if idx_q25_d_minus >= 0 else 0.0))

    idx_q90_d = min(q90_d - min_dif, len(cdf_d) - 1)
    idx_q10_d_minus = q10_d - min_dif - 1
    masa_teorica_dif_80 = float(cdf_d[idx_q90_d] - (cdf_d[idx_q10_d_minus] if idx_q10_d_minus >= 0 else 0.0))

    # Marcador exacto de sets
    if mejor_de == 3:
        p_2_0 = float(dist.prob[ok & (dist.sets_a == 2) & (dist.sets_b == 0)].sum())
        p_2_1 = float(dist.prob[ok & (dist.sets_a == 2) & (dist.sets_b == 1)].sum())
        p_0_2 = float(dist.prob[ok & (dist.sets_a == 0) & (dist.sets_b == 2)].sum())
        p_1_2 = float(dist.prob[ok & (dist.sets_a == 1) & (dist.sets_b == 2)].sum())
        probs_sets = {"2-0": p_2_0, "2-1": p_2_1, "0-2": p_0_2, "1-2": p_1_2}
    else:
        p_3_0 = float(dist.prob[ok & (dist.sets_a == 3) & (dist.sets_b == 0)].sum())
        p_3_1 = float(dist.prob[ok & (dist.sets_a == 3) & (dist.sets_b == 1)].sum())
        p_3_2 = float(dist.prob[ok & (dist.sets_a == 3) & (dist.sets_b == 2)].sum())
        p_0_3 = float(dist.prob[ok & (dist.sets_a == 0) & (dist.sets_b == 3)].sum())
        p_1_3 = float(dist.prob[ok & (dist.sets_a == 1) & (dist.sets_b == 3)].sum())
        p_2_3 = float(dist.prob[ok & (dist.sets_a == 2) & (dist.sets_b == 3)].sum())
        probs_sets = {"3-0": p_3_0, "3-1": p_3_1, "3-2": p_3_2, "0-3": p_0_3, "1-3": p_1_3, "2-3": p_2_3}

    # 3. Desenlaces reales
    y_gana_1 = 1 if y_ganador == 1 else 0
    y_sets = json.loads(y_sets_str)
    y_1er_set_1 = 1 if y_sets[0][0] > y_sets[0][1] else 0
    s1 = sum(1 for s in y_sets if s[0] > s[1])
    s2 = sum(1 for s in y_sets if s[1] > s[0])
    y_marcador_sets = f"{s1}-{s2}"
    y_hsets_menos_1_5 = 1 if (s1 - s2 > 1.5) else 0

    has_tb = any((s[0] in (7, 6) and s[1] in (7, 6) and abs(s[0] - s[1]) == 1) or
                 (len(s) > 2 and s[2] is not None) for s in y_sets)
    y_tiebreak = 1 if has_tb else 0

    y_total = int(y_juegos_1 + y_juegos_2)
    y_total_mas_l = 1 if y_total > l_star else 0
    y_dif = int(y_juegos_1 - y_juegos_2)
    y_handicap_cubierto = 1 if (y_dif + h_star > 0) else 0

    # Coberturas discretas
    cubierto_total_50 = 1 if (q25_t <= y_total <= q75_t) else 0
    cubierto_total_80 = 1 if (q10_t <= y_total <= q90_t) else 0
    cubierto_dif_50 = 1 if (q25_d <= y_dif <= q75_d) else 0
    cubierto_dif_80 = 1 if (q10_d <= y_dif <= q90_d) else 0

    # PIT aleatorizado de total de juegos
    f_obs_t = float(cdf_t[min(y_total, len(cdf_t) - 1)])
    f_minus_t = float(cdf_t[y_total - 1]) if y_total - 1 >= 0 and y_total - 1 < len(cdf_t) else 0.0
    v_rand_t = pseudo_random_from_hash(partido_key)
    pit_u_tot = float(f_minus_t + v_rand_t * (f_obs_t - f_minus_t))
    cubierto_pit_tot_50 = 1 if (0.25 <= pit_u_tot <= 0.75) else 0
    cubierto_pit_tot_80 = 1 if (0.10 <= pit_u_tot <= 0.90) else 0

    # PIT aleatorizado de hándicap de juegos (diferencia)
    idx_obs_d = min(max(y_dif - min_dif, 0), len(cdf_d) - 1)
    f_obs_d = float(cdf_d[idx_obs_d])
    idx_minus_d = y_dif - min_dif - 1
    f_minus_d = float(cdf_d[idx_minus_d]) if 0 <= idx_minus_d < len(cdf_d) else 0.0
    v_rand_d = pseudo_random_from_hash(partido_key + "_dif")
    pit_u_dif = float(f_minus_d + v_rand_d * (f_obs_d - f_minus_d))
    cubierto_pit_dif_50 = 1 if (0.25 <= pit_u_dif <= 0.75) else 0
    cubierto_pit_dif_80 = 1 if (0.10 <= pit_u_dif <= 0.90) else 0

    # RPS de totales
    k_range = list(range(t_min, t_max))
    f_pred = np.array([cdf_t[k] if k < len(cdf_t) else 1.0 for k in k_range])
    f_real = np.array([1.0 if y_total <= k else 0.0 for k in k_range])
    rps_totales = float(np.mean((f_pred - f_real) ** 2))

    # Multiclase exacto de sets (Brier y logloss)
    prob_real_set = probs_sets.get(y_marcador_sets, 1e-12)
    logloss_sets = -float(np.log(max(prob_real_set, 1e-12)))
    brier_sets = float(sum((p - (1.0 if k == y_marcador_sets else 0.0)) ** 2 for k, p in probs_sets.items()))

    return {
        "partido_key": partido_key,
        "circuito": circuito,
        "temporada": temporada,
        "superficie": superficie,
        "mejor_de": mejor_de,
        "formato_decisivo": decisivo,
        # Probabilidades predichas
        "pi_ganador": pi_lado1,
        "prob_ganador": prob_ganador,
        "dif_coherencia": dif_coherencia,
        "violacion_coherencia": violacion_coherencia,
        "prob_1er_set": prob_1er_set,
        "prob_hsets_menos_1_5": prob_hsets_menos_1_5,
        "prob_hsets_mas_1_5": prob_hsets_mas_1_5,
        "prob_tiebreak": prob_tiebreak,
        "media_juegos": media_juegos,
        "linea_total": l_star,
        "prob_total_mas_L": prob_total_mas_l,
        "total_q10": q10_t,
        "total_q25": q25_t,
        "total_q75": q75_t,
        "total_q90": q90_t,
        "masa_teorica_tot_50": masa_teorica_tot_50,
        "masa_teorica_tot_80": masa_teorica_tot_80,
        "linea_handicap": h_star,
        "prob_handicap_cubierto": prob_handicap_cubierto,
        "dif_q10": q10_d,
        "dif_q25": q25_d,
        "dif_q75": q75_d,
        "dif_q90": q90_d,
        "masa_teorica_dif_50": masa_teorica_dif_50,
        "masa_teorica_dif_80": masa_teorica_dif_80,
        "prob_marcador_real": prob_real_set,
        "logloss_marcador_sets": logloss_sets,
        "brier_marcador_sets": brier_sets,
        "pit_u_tot": pit_u_tot,
        "pit_u_dif": pit_u_dif,
        "rps_totales": rps_totales,
        # Resultados observados
        "y_ganador": y_gana_1,
        "y_1er_set": y_1er_set_1,
        "y_hsets_menos_1_5": y_hsets_menos_1_5,
        "y_tiebreak": y_tiebreak,
        "y_total_juegos": y_total,
        "y_total_mas_L": y_total_mas_l,
        "y_dif_juegos": y_dif,
        "y_handicap_cubierto": y_handicap_cubierto,
        "y_marcador_sets": y_marcador_sets,
        # Indicadores de cobertura
        "cubierto_total_50": cubierto_total_50,
        "cubierto_total_80": cubierto_total_80,
        "cubierto_dif_50": cubierto_dif_50,
        "cubierto_dif_80": cubierto_dif_80,
        "cubierto_pit_tot_50": cubierto_pit_tot_50,
        "cubierto_pit_tot_80": cubierto_pit_tot_80,
        "cubierto_pit_dif_50": cubierto_pit_dif_50,
        "cubierto_pit_dif_80": cubierto_pit_dif_80,
    }


def evaluar_lote(lote: list[dict]) -> list[dict]:
    """Procesa un lote de partidos en un proceso worker."""
    return [evaluar_un_partido(item) for item in lote]


def calcular_lineas_base_historicas(partidos_hist: pd.DataFrame) -> dict:
    """Calcula las frecuencias empíricas <= 2018 para las compuertas de G-resultados."""
    # Frecuencias de total de juegos por (circuito, mejor_de)
    freqs = {}
    for (circ, md), grupo in partidos_hist.groupby(["circuito", "mejor_de"]):
        totales = (grupo.y_juegos_1 + grupo.y_juegos_2).to_numpy()
        t_min = 12 if md == 3 else 18
        t_max = 39 if md == 3 else 65
        counts = np.bincount(totales, minlength=t_max + 1)
        pmf = counts / counts.sum()
        cdf = np.cumsum(pmf)
        freqs[(circ, md)] = {"pmf": pmf, "cdf": cdf, "t_min": t_min, "t_max": t_max}

    # Tasa de tiebreak histórica
    tb_hist = {}
    for circ, grupo in partidos_hist.groupby("circuito"):
        tbs = []
        for s_str in grupo.y_sets.dropna().sample(min(len(grupo), 10000), random_state=42):
            try:
                sets = json.loads(s_str)
                has_tb = any((s[0] in (7, 6) and s[1] in (7, 6) and abs(s[0] - s[1]) == 1) or
                             (len(s) > 2 and s[2] is not None) for s in sets)
                tbs.append(1 if has_tb else 0)
            except Exception:
                pass
        tb_hist[circ] = float(np.mean(tbs))

    return {"totales": freqs, "tiebreak": tb_hist}


def evaluar_compuertas_circuito(df_c: pd.DataFrame, lb_hist: dict, rng, reps: int = 2000) -> dict:
    """Evalúa todas las compuertas de §I.1 para un circuito dado."""
    n = len(df_c)
    circuito = df_c.iloc[0]["circuito"]
    log(f"Iniciando evaluación de compuertas para {circuito.upper()} (n = {n})...")

    # 1. G-coherencia: 0 violaciones
    violaciones = int(df_c["violacion_coherencia"].sum())
    max_dif_coherencia = float(df_c["dif_coherencia"].max())
    pasa_coherencia = (violaciones == 0)

    # 2. Margen / sesgo IID en totales: E[T_obs - T_pred] con IC95 bootstrap
    dif_totales = (df_c["y_total_juegos"] - df_c["media_juegos"]).to_numpy()
    sesgo_iid_medio = float(np.mean(dif_totales))
    boot_sesgo = np.empty(reps)
    for i in range(reps):
        idx = rng.integers(n, size=n)
        boot_sesgo[i] = dif_totales[idx].mean()
    sesgo_iid_ic95 = [float(np.quantile(boot_sesgo, 0.025)), float(np.quantile(boot_sesgo, 0.975))]

    # 3. G-cobertura:
    # A) Cobertura empírica discreta
    cob_tot_50_disc = float(df_c["cubierto_total_50"].mean())
    cob_tot_80_disc = float(df_c["cubierto_total_80"].mean())
    masa_teorica_tot_50 = float(df_c["masa_teorica_tot_50"].mean())
    masa_teorica_tot_80 = float(df_c["masa_teorica_tot_80"].mean())

    cob_dif_50_disc = float(df_c["cubierto_dif_50"].mean())
    cob_dif_80_disc = float(df_c["cubierto_dif_80"].mean())
    masa_teorica_dif_50 = float(df_c["masa_teorica_dif_50"].mean())
    masa_teorica_dif_80 = float(df_c["masa_teorica_dif_80"].mean())

    # B) Cobertura continua por PIT aleatorizado
    cob_tot_50_pit = float(df_c["cubierto_pit_tot_50"].mean())
    cob_tot_80_pit = float(df_c["cubierto_pit_tot_80"].mean())
    cob_dif_50_pit = float(df_c["cubierto_pit_dif_50"].mean())
    cob_dif_80_pit = float(df_c["cubierto_pit_dif_80"].mean())

    pasa_cobertura = (
        (0.47 <= cob_tot_50_pit <= 0.53 or abs(cob_tot_50_disc - masa_teorica_tot_50) <= 0.03) and
        (0.77 <= cob_tot_80_pit <= 0.83 or abs(cob_tot_80_disc - masa_teorica_tot_80) <= 0.03) and
        (0.47 <= cob_dif_50_pit <= 0.53 or abs(cob_dif_50_disc - masa_teorica_dif_50) <= 0.03) and
        (0.77 <= cob_dif_80_pit <= 0.83 or abs(cob_dif_80_disc - masa_teorica_dif_80) <= 0.03)
    )

    # 4. G-calibración (otros mercados):
    calib_ganador = ev.calibracion(df_c["y_ganador"].to_numpy(), df_c["prob_ganador"].to_numpy(), rng, reps)
    calib_1er_set = ev.calibracion(df_c["y_1er_set"].to_numpy(), df_c["prob_1er_set"].to_numpy(), rng, reps)
    calib_hsets = ev.calibracion(df_c["y_hsets_menos_1_5"].to_numpy(), df_c["prob_hsets_menos_1_5"].to_numpy(), rng, reps)
    calib_totales = ev.calibracion(df_c["y_total_mas_L"].to_numpy(), df_c["prob_total_mas_L"].to_numpy(), rng, reps)
    calib_handicap = ev.calibracion(df_c["y_handicap_cubierto"].to_numpy(), df_c["prob_handicap_cubierto"].to_numpy(), rng, reps)

    # Decilas del PIT aleatorizado de totales (umbral: ninguna fuera de [0.08, 0.12])
    pit_u = df_c["pit_u_tot"].to_numpy()
    decilas_pit = [float(np.mean((pit_u >= i * 0.10) & (pit_u < (i + 1) * 0.10))) for i in range(10)]
    pit_valido = all(0.08 <= d <= 0.12 for d in decilas_pit)

    def chequear_calib(c):
        return (c["pend_lo"] <= 1.0 <= c["pend_hi"]) and (abs(c["pendiente"] - 1.0) <= 0.15) and (c["int_lo"] <= 0.0 <= c["int_hi"])

    pasa_calibracion_otros = (
        chequear_calib(calib_1er_set) and
        chequear_calib(calib_hsets) and
        chequear_calib(calib_totales) and
        pit_valido
    )

    # 5. G-resultados (otros mercados): RPS vs frecuencias empíricas
    rps_modelo = float(df_c["rps_totales"].mean())

    rps_emp_list = []
    for _, row in df_c.iterrows():
        md = row["mejor_de"]
        cfg_lb = lb_hist["totales"].get((circuito, md))
        if cfg_lb:
            cdf_lb = cfg_lb["cdf"]
            t_min, t_max = cfg_lb["t_min"], cfg_lb["t_max"]
            yt = int(row["y_total_juegos"])
            k_range = list(range(t_min, t_max))
            f_lb = np.array([cdf_lb[k] if k < len(cdf_lb) else 1.0 for k in k_range])
            f_real = np.array([1.0 if yt <= k else 0.0 for k in k_range])
            rps_emp_list.append(float(np.mean((f_lb - f_real) ** 2)))
    rps_emp = float(np.mean(rps_emp_list))
    dif_rps_emp = rps_modelo - rps_emp

    arr_dif_rps = df_c["rps_totales"].to_numpy() - np.array(rps_emp_list)
    boot_rps = np.empty(reps)
    for i in range(reps):
        boot_rps[i] = arr_dif_rps[rng.integers(n, size=n)].mean()
    ic95_dif_rps = [float(np.quantile(boot_rps, 0.025)), float(np.quantile(boot_rps, 0.975))]

    metricas_1er_set = ev.metricas(df_c["y_1er_set"].to_numpy(), df_c["prob_1er_set"].to_numpy())
    metricas_tb = ev.metricas(df_c["y_tiebreak"].to_numpy(), df_c["prob_tiebreak"].to_numpy())
    metricas_hsets = ev.metricas(df_c["y_hsets_menos_1_5"].to_numpy(), df_c["prob_hsets_menos_1_5"].to_numpy())
    metricas_totales = ev.metricas(df_c["y_total_mas_L"].to_numpy(), df_c["prob_total_mas_L"].to_numpy())

    tb_freq_hist = lb_hist["tiebreak"].get(circuito, 0.25)
    logloss_tb_ref = float(ev.perdida(df_c["y_tiebreak"].to_numpy(), np.full(n, tb_freq_hist)).mean())

    pasa_resultados = (
        ic95_dif_rps[1] < 0.0 and  # mejor que frecuencias empíricas excluyendo 0
        metricas_1er_set["logloss"] < np.log(2.0) and  # mejor que 50%
        metricas_tb["logloss"] < logloss_tb_ref  # mejor que frecuencia simple
    )

    log(f"{circuito.upper()} completado: Coherencia={pasa_coherencia}, Cobertura={pasa_cobertura}, "
        f"Calibración={pasa_calibracion_otros}, Resultados={pasa_resultados}")

    return {
        "circuito": circuito,
        "n_evaluados": n,
        "G_coherencia": {
            "pasa": pasa_coherencia,
            "violaciones": violaciones,
            "max_dif_coherencia": max_dif_coherencia,
        },
        "sesgo_iid_totales": {
            "media_dif_juegos": sesgo_iid_medio,
            "ic95": sesgo_iid_ic95,
        },
        "G_cobertura": {
            "pasa": pasa_cobertura,
            "pit_aleatorizada": {
                "total_50_pct": cob_tot_50_pit,
                "total_80_pct": cob_tot_80_pit,
                "dif_50_pct": cob_dif_50_pit,
                "dif_80_pct": cob_dif_80_pit,
                "umbral_50": [0.47, 0.53],
                "umbral_80": [0.77, 0.83],
            },
            "discreta_enteros": {
                "total_50_observada": cob_tot_50_disc,
                "total_50_teorica": masa_teorica_tot_50,
                "total_80_observada": cob_tot_80_disc,
                "total_80_teorica": masa_teorica_tot_80,
                "dif_50_observada": cob_dif_50_disc,
                "dif_50_teorica": masa_teorica_dif_50,
                "dif_80_observada": cob_dif_80_disc,
                "dif_80_teorica": masa_teorica_dif_80,
            },
        },
        "G_calibracion": {
            "pasa_otros_mercados": pasa_calibracion_otros,
            "ganador": calib_ganador,
            "primer_set": calib_1er_set,
            "handicap_sets": calib_hsets,
            "totales_linea_principal": calib_totales,
            "handicap_juegos": calib_handicap,
            "pit_aleatorizado": {
                "pasa": pit_valido,
                "decilas": decilas_pit,
                "umbral": [0.08, 0.12],
            },
        },
        "G_resultados": {
            "pasa": pasa_resultados,
            "rps_totales_modelo": rps_modelo,
            "rps_totales_empirico": rps_emp,
            "dif_rps": dif_rps_emp,
            "ic95_dif_rps": ic95_dif_rps,
            "primer_set": metricas_1er_set,
            "tiebreak": metricas_tb,
            "tiebreak_logloss_ref": logloss_tb_ref,
            "handicap_sets": metricas_hsets,
            "totales_linea_principal": metricas_totales,
            "marcador_sets_logloss_medio": float(df_c["logloss_marcador_sets"].mean()),
            "marcador_sets_brier_medio": float(df_c["brier_marcador_sets"].mean()),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluación de mercados derivados y distribución conjunta")
    parser.add_argument("--partidos", type=Path, default=DIR_EXPORT_PIT / "partidos.parquet")
    parser.add_argument("--predicciones", type=Path, default=DIR_MODELO_S3 / "predicciones_wf.parquet")
    parser.add_argument("--hiper", type=Path, default=DIR_MODELO_S3 / "hiperparametros.json")
    parser.add_argument("--salida_dir", type=Path, default=DIR_MODELO_S4)
    parser.add_argument("--max_workers", type=int, default=os.cpu_count())
    parser.add_argument("--limite", type=int, default=None, help="Límite de partidos para prueba rápida")
    parser.add_argument("--reps", type=int, default=2000, help="Réplicas de bootstrap")
    args = parser.parse_args()

    args.salida_dir.mkdir(parents=True, exist_ok=True)
    t0_total = time.time()
    log("=== Inicio de Evaluación de Mercados Sprint 4 (2019–2024) ===")

    log(f"Cargando predicciones de {args.predicciones}...")
    pred = pd.read_parquet(args.predicciones)

    log(f"Cargando partidos de {args.partidos}...")
    part = pd.read_parquet(
        args.partidos,
        columns=[
            "partido_key", "mejor_de", "formato_decisivo", "superficie",
            "y_estado", "y_ganador", "y_sets", "y_juegos_1", "y_juegos_2", "temporada"
        ],
        filters=[("temporada", ">=", 2019), ("temporada", "<=", 2024)]
    )

    log(f"Cargando hiperparámetros de {args.hiper}...")
    with open(args.hiper, "r", encoding="utf-8") as f:
        hiper = json.load(f)

    log("Cargando histórico <= 2018 para frecuencias empíricas de referencia...")
    part_hist = pd.read_parquet(
        args.partidos,
        columns=["circuito", "mejor_de", "y_juegos_1", "y_juegos_2", "y_sets", "y_estado"],
        filters=[("temporada", "<=", 2018), ("y_estado", "==", "completado")]
    )
    lb_hist = calcular_lineas_base_historicas(part_hist)
    del part_hist

    log("Fusionando predicciones y partidos...")
    df = pred.merge(part, on="partido_key")
    n_total = len(df)
    df_completados = df[df["y_estado"] == "completado"].copy()
    n_comp = len(df_completados)
    log(f"Total predicciones: {n_total}. Completados para evaluar: {n_comp} ({n_total - n_comp} no completados)")

    if args.limite is not None:
        df_completados = df_completados.head(args.limite).copy()
        log(f"Modo prueba: limitado a {len(df_completados)} partidos.")

    items = []
    for _, row in df_completados.iterrows():
        c = row["circuito"]
        sig_eps = hiper["circuitos"][c]["psi_p"]["sigma_eps"]
        rho_eps = hiper["circuitos"][c]["psi_p"]["rho_eps"]
        c_inf = hiper["circuitos"][c]["c_inf"]
        fmt_idx = indice_formato(row["mejor_de"], row["formato_decisivo"])
        if fmt_idx < 0:
            continue

        items.append({
            "partido_key": str(row["partido_key"]),
            "circuito": str(c),
            "temporada": int(row["temporada_x"]),
            "superficie": str(row["superficie"]),
            "S_hat": float(row["S_hat"]),
            "pi_lado1": float(row["pi_lado1"]),
            "var_rho": float(row["var_rho"]),
            "mejor_de": int(row["mejor_de"]),
            "formato_decisivo": str(row["formato_decisivo"]),
            "fmt_idx": fmt_idx,
            "sigma_eps": float(sig_eps),
            "rho_eps": float(rho_eps),
            "c_inf": float(c_inf),
            "y_ganador": int(row["y_ganador"]),
            "y_sets": str(row["y_sets"]),
            "y_juegos_1": int(row["y_juegos_1"]),
            "y_juegos_2": int(row["y_juegos_2"]),
        })

    log(f"Total partidos listos para simulación analítica: {len(items)}")

    tam_lote = 500
    lotes = [items[i:i + tam_lote] for i in range(0, len(items), tam_lote)]
    log(f"Lanzando {len(lotes)} lotes en paralelo con {args.max_workers} trabajadores...")

    t0_sim = time.time()
    resultados_partidos = []
    procesados = 0
    with ProcessPoolExecutor(max_workers=args.max_workers) as executor:
        for res_lote in executor.map(evaluar_lote, lotes):
            resultados_partidos.extend(res_lote)
            procesados += len(res_lote)
            if procesados % 5000 == 0 or procesados == len(items):
                log(f"Progreso simulación: {procesados}/{len(items)} partidos ({procesados/len(items)*100:.1f}%)")

    dt_sim = time.time() - t0_sim
    log(f"Simulación analítica completada: {len(resultados_partidos)} partidos en {dt_sim:.1f} s ({len(resultados_partidos)/dt_sim:.1f} part/s)")

    df_res = pd.DataFrame(resultados_partidos)
    salida_parquet = args.salida_dir / "evaluacion_mercados.parquet"
    log(f"Guardando {salida_parquet}...")
    df_res.to_parquet(salida_parquet, index=False)

    rng = np.random.default_rng(20261106)
    informe_final = {
        "version": "tenis-modelo-s4-1.0.0",
        "fecha": datetime.now().isoformat(),
        "n_total_predicciones": n_total,
        "n_completados": n_comp,
        "n_evaluados": len(df_res),
        "circuitos": {},
    }

    for circ in ("atp", "wta"):
        df_c = df_res[df_res["circuito"] == circ].copy()
        if len(df_c) > 0:
            res_c = evaluar_compuertas_circuito(df_c, lb_hist, rng, reps=args.reps)
            informe_final["circuitos"][circ] = res_c

    salida_json = args.salida_dir / "evaluacion_mercados.json"
    log(f"Guardando {salida_json}...")
    with open(salida_json, "w", encoding="utf-8") as f:
        json.dump(informe_final, f, indent=2)

    log(f"=== Evaluación Sprint 4 Finalizada con éxito en {time.time() - t0_total:.1f} s ===")


if __name__ == "__main__":
    main()
