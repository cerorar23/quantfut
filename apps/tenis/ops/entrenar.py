"""Entrena en el PC (plan D.8, K.2 S3): Ψ_P y Ψ_R por circuito con temporadas ≤ 2018 y los CONGELA en
`modelo_s3/hiperparametros.json` (con huella sha256). La reserva 2025–2026 no se lee; 2019–2024 tampoco.

Uso: python apps/tenis/ops/entrenar.py [--circuitos atp wta] [--maxiter 30] [--trabajadores 6]
Pasos por circuito: (1) P por MV predictiva → σ_ε, ρ_ε, ℓ̄_s; (2) tablas de M̄_f; (3) F90 con λ = 0,75;
(4) Ψ_R completo; (5) rejilla preregistrada λ ∈ {0,5; 0,75; 0,9} reajustando solo φ; (6) ablaciones reajustadas con
arranque en caliente (sin superficie: κ ≡ 1, d ≡ 0, ℓ̄ común; sin fatiga: φ ≡ 0).
"""
import argparse
import json
import math
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from tenis.modelo import datos as dm
from tenis.modelo import hiperparametros as hp
from tenis.modelo import tabla
from tenis.modelo.puntos import filtrar_p, observaciones
from tenis.modelo.rating import filtrar
from tenis.simulador.formato import Formato
from tenis.simulador.mezcla import Incertidumbre

SALIDA = Path(r"C:\Users\huye\Documents\apuesta proyec\data\tennis\rediseno_20261104\modelo_s3")
HASTA = 2018
X0_P = [math.log(0.154), math.log(0.124), math.log(0.096), math.log(0.066), math.log(0.067), 0.0, 0.0, 0.0,
        math.log(0.22), math.atanh(-0.45), math.log(0.02)]
X0_R = [math.log(0.1), math.log(0.1), math.log(0.15), -0.05, 0.0, 0.0, 0.0, math.log(0.05), math.log(0.02), 0.0,
        -3.0, -3.0, 0.0]
LAMBDAS = (0.5, 0.75, 0.9)
ESPECIFICACION = {
    "tiempo": "ns UTC; Δt en años = Δns/(365,25·86400e9); inactividad en días por encima de 60",
    "orden": "partidos por (corte_utc, partido_key); antes de cada uno se aplican los eventos con visible_resultado_utc < corte en bloques de igual visibilidad, cada bloque desde el estado previo (Woodbury si un jugador aparece varias veces; términos ordenados por partido_key)",
    "actualiza": "solo eventos estado=completado cuyo partido se pronosticó; walkover y retirada no; un evento repetido (misma partido_key) se aplica una vez",
    "no_pronosticable": "excluir_motivo no nulo, por_equipos o jjoo, superficie nula, formato no soportado (solo (3|5, tiebreak_7|tiebreak_10|ventaja)), o un lado sin estado y sin rank PIT",
    "prior": "θ0 = b_rank·(ln rank − ln 100), var σ_θ0²; d ~ N(0, σ_d²Ω), Ω equicorrelada r_Ω; t_last = corte del partido que lo inicializa",
    "propagacion": "V_θθ += τ_θ²Δt + τ_I²·max(0, días−60)/365,25; V_dd += τ_d²Δt·Ω; desde la última actualización (la predicción no modifica el estado)",
    "rho": "κ_s(1+γ_pregs·z)·(θ1−θ2) + d1_s − d2_s − [φ1(F1−F2)/60 + φ2(max(0,F1−F90)−max(0,F2−F90))/60]; término de fatiga 0 y marca si F desconocida",
    "fatiga": "F = Σ λ^(Δ días)·minutos de eventos del jugador con 0 < corte − visible ≤ 96 h; walkover = 0; minutos nulos en un partido jugado ⇒ desconocida",
    "enlace": "π = E_u[M(ρ+u)]/(E_u[M(ρ+u)] + E_u[M(−ρ+u)]), u ~ N(0, v), v = aᵀV1a + aᵀV2a, a = κ_s(1+γz)e_θ + e_ds; M(ρ) = simulador.mezcla.prob_ganar(expit(ℓ̄_s+ρ), expit(ℓ̄_s−ρ), formato, Incertidumbre(σ_ε, ρ_ε)); ρ recortado a ±r_lim (M(−r_lim) ≥ 1e-13)",
    "actualizacion": "g = ∂ln M/∂ρ (ganador lado 1) o −∂ln M(−ρ)/∂ρ, h = max(0, −∂²); h_ef = h/(1+h·q_rival), g_ef = g/(1+h·q_rival); m += V a g_ef/(1+h_ef q), V −= h_ef/(1+h_ef q)·(Va)(Va)ᵀ",
}


def log(msg):
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def errores_tablas(tabs, lbar, inc) -> dict:
    rng = np.random.default_rng(20261105)
    vistos, peor, peor_v = set(), 0.0, 0.0
    for (f, s), tb in tabs.items():
        if id(tb) in vistos:
            continue
        vistos.add(id(tb))
        fm = Formato(*dm.FORMATOS[f])
        peor = max(peor, tabla.error_tabla(tb, lbar[s], fm, inc, rng.uniform(-1.5, 1.5, 25) + 0.0037))
        peor_v = max(peor_v, tabla.error_con_v(tb, lbar[s], fm, inc, [(0.05, 0.01), (-0.2, 0.05), (0.35, 0.12)]))
    return {"max_error_tabla_v0": peor, "max_error_con_v_q61": peor_v, "tablas_distintas": len(vistos)}


def f90_de(d, sal, ventana=hp.VENTANA) -> float:
    t = d.p.temporada.to_numpy()
    sel = np.isfinite(sal.pi) & (t >= ventana[0]) & (t <= ventana[1])
    f = np.r_[sal.f1[sel], sal.f2[sel]]
    return float(np.percentile(f[np.isfinite(f)], 90))


def entrenar_circuito(d, obs, a) -> dict:
    r = {"n_partidos_ajuste": int(len(d.p)), "n_obs_p": int(len(obs))}
    log(f"{d.circuito}: pieza P ({len(obs)} partidos con estadísticas)")
    xp, fp, _ = hp.ajustar(hp._obj_p, X0_P, {"d": d, "obs": obs}, maxiter=a.maxiter, trabajadores=a.trabajadores)
    psip = hp.psip_desde_vector(xp)
    _, _, lbar = filtrar_p(d, obs, psip, hp.VENTANA, predecir=False)
    t = obs.temporada.to_numpy()
    cnt = np.bincount(obs.sup[(t >= hp.VENTANA[0]) & (t <= hp.VENTANA[1])], minlength=4)
    lbar_comun = float(np.dot(cnt, lbar) / cnt.sum())
    r |= {"psi_p": psip.como_dict(), "x_p": dict(zip(hp.NOMBRES_P, xp.tolist())), "menos_loglik_p": fp,
          "lbar": list(lbar), "lbar_comun": lbar_comun}
    log(f"{d.circuito}: P listo σ_ε={psip.sigma_eps:.4f} ρ_ε={psip.rho_eps:.3f} ℓ̄={np.round(lbar, 4)}")
    tabs = tabla.construir_todas(lbar, psip.sigma_eps, psip.rho_eps)
    tabs_c = tabla.construir_todas((lbar_comun,) * 4, psip.sigma_eps, psip.rho_eps)
    r["error_tablas"] = errores_tablas(tabs, lbar, Incertidumbre(psip.sigma_eps, psip.rho_eps))
    log(f"{d.circuito}: tablas {r['error_tablas']}")
    fijo = {"sigma_eps": psip.sigma_eps, "rho_eps": psip.rho_eps, "lbar": list(lbar), "lam": 0.75, "f90": 0.0}
    fijo["f90"] = f90_de(d, filtrar(d, hp.psi_desde_vector(X0_R, fijo), tabs))
    base = {"d": d, "tablas": tabs, "fijo": fijo, "ablacion": ""}
    log(f"{d.circuito}: pieza R, F90(λ=0,75) = {fijo['f90']:.1f}")
    x, f, _ = hp.ajustar(hp._obj_r, X0_R, base, maxiter=a.maxiter, trabajadores=a.trabajadores)
    rejilla = {0.75: {"menos_loglik": f, "f90": fijo["f90"], "x": x.tolist()}}
    for lam in (0.5, 0.9):
        fl = dict(fijo, lam=lam)
        fl["f90"] = f90_de(d, filtrar(d, hp.psi_desde_vector(x, fl), tabs))
        xl, fv, _ = hp.ajustar(hp._obj_r, x, dict(base, fijo=fl), libres=[10, 11], maxiter=min(10, a.maxiter),
                               trabajadores=a.trabajadores)
        rejilla[lam] = {"menos_loglik": fv, "f90": fl["f90"], "x": xl.tolist()}
        log(f"{d.circuito}: λ={lam} −ll={fv:.3f} (λ=0,75: {f:.3f})")
    lam = min(rejilla, key=lambda k: rejilla[k]["menos_loglik"])
    x, fijo = np.array(rejilla[lam]["x"]), dict(fijo, lam=lam, f90=rejilla[lam]["f90"])
    psi = hp.psi_desde_vector(x, fijo)
    log(f"{d.circuito}: Ψ_R {psi.como_dict()}")
    x_ss, f_ss, _ = hp.ajustar(hp._obj_r, x, {"d": d, "tablas": tabs_c, "fijo": fijo, "ablacion": "sin_superficie"},
                               libres=[0, 1, 2, 3, 10, 11, 12], maxiter=min(15, a.maxiter), trabajadores=a.trabajadores)
    x_sf, f_sf, _ = hp.ajustar(hp._obj_r, x, dict(base, fijo=fijo, ablacion="sin_fatiga"),
                               libres=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 12], maxiter=min(15, a.maxiter),
                               trabajadores=a.trabajadores)
    log(f"{d.circuito}: ablaciones −ll sin superficie {f_ss:.3f}, sin fatiga {f_sf:.3f}, completo {rejilla[lam]['menos_loglik']:.3f}")
    return r | {"fijo_r": fijo, "psi_r": psi.como_dict(), "x_r": dict(zip(hp.NOMBRES_R, x.tolist())),
                "menos_loglik_r": rejilla[lam]["menos_loglik"], "rejilla_lambda": {str(k): v for k, v in rejilla.items()},
                "lambda_elegido": lam,
                "ablacion_sin_superficie": {"psi_r": hp.psi_desde_vector(x_ss, fijo, "sin_superficie").como_dict(),
                                            "x_r": x_ss.tolist(), "menos_loglik": f_ss},
                "ablacion_sin_fatiga": {"psi_r": hp.psi_desde_vector(x_sf, fijo, "sin_fatiga").como_dict(),
                                        "x_r": x_sf.tolist(), "menos_loglik": f_sf}}


def parche_sigma_r(a):
    """Parche G-calibración (6-nov): σ_R² del partido en el enlace de R, por MV con ≤ 2018 y el resto CONGELADO;
    variante registrada σ_R Challenger/gira; reajuste corto de todo; ablaciones con su σ_R. Conserva el JSON anterior."""
    ruta = Path(a.salida)
    antes = ruta.with_name("hiperparametros_antes_parche.json")
    if not antes.exists():
        shutil.copyfile(ruta, antes)
    hpj = hp.leer(antes)
    p, e = dm.cargar_export(hasta=HASTA)
    for c in a.circuitos:
        cfg, d = hpj["circuitos"][c], dm.preparar(p, e, c, HASTA)
        fijo, x = cfg["fijo_r"], [cfg["x_r"][n] for n in hp.NOMBRES_R[:13]]
        tabs = tabla.construir_todas(tuple(cfg["lbar"]), fijo["sigma_eps"], fijo["rho_eps"])
        tabs_c = tabla.construir_todas((cfg["lbar_comun"],) * 4, fijo["sigma_eps"], fijo["rho_eps"])
        base = {"d": d, "tablas": tabs, "fijo": fijo, "ablacion": ""}
        log(f"{c}: σ_R con el resto congelado (−ll anterior {cfg['menos_loglik_r']:.3f})")
        x1, f1, _ = hp.ajustar(hp._obj_r, x + [math.log(0.15)], base, libres=[13], maxiter=15, trabajadores=a.trabajadores)
        log(f"{c}: σ_R = {math.exp(x1[13]):.4f}, −ll {f1:.3f}")
        parche = {"menos_loglik_antes": cfg["menos_loglik_r"], "sigma_r_solo": math.exp(x1[13]), "menos_loglik_sigma_r_solo": f1}
        if (d.p.nivel == 1).any():
            x2, f2, _ = hp.ajustar(hp._obj_r, list(x1) + [x1[13]], base, libres=[13, 14], maxiter=15, trabajadores=a.trabajadores)
            lr = 2 * (f1 - f2)
            cfg["variante_challenger"] = {"psi_r": hp.psi_desde_vector(x2, fijo).como_dict(), "x_r": x2.tolist(),
                                          "menos_loglik": f2, "razon_verosimilitud": lr, "justificada_chi2_1gl": lr > 3.84}
            log(f"{c}: variante Challenger σ_R gira {math.exp(x2[13]):.4f} / Challenger {math.exp(x2[14]):.4f}, 2Δll = {lr:.2f}")
        x3, f3, _ = hp.ajustar(hp._obj_r, x1, base, maxiter=a.maxiter, trabajadores=a.trabajadores)
        xf, ff = (x3, f3) if f3 < f1 else (x1, f1)
        log(f"{c}: reajuste corto −ll {f3:.3f} (σ_R {math.exp(x3[13]):.4f}); se queda {'reajuste' if f3 < f1 else 'solo σ_R'}")
        psi_a, psi_f = hp.psi_desde_vector(x, fijo), hp.psi_desde_vector(xf, fijo)
        parche |= {"menos_loglik_reajuste_corto": f3, "usa_reajuste": bool(f3 < f1),
                   "platt_2012_2018_antes": hp.pendiente_platt(d, filtrar(d, psi_a, tabs).pi),
                   "platt_2012_2018_despues": hp.pendiente_platt(d, filtrar(d, psi_f, tabs).pi)}
        log(f"{c}: Platt 2012–2018 {parche['platt_2012_2018_antes']:.3f} → {parche['platt_2012_2018_despues']:.3f}")
        for nombre, abl, tb in (("ablacion_sin_superficie", "sin_superficie", tabs_c), ("ablacion_sin_fatiga", "sin_fatiga", tabs)):
            xa, fa, _ = hp.ajustar(hp._obj_r, list(cfg[nombre]["x_r"]) + [xf[13]], dict(base, tablas=tb, ablacion=abl),
                                   libres=[13], maxiter=10, trabajadores=a.trabajadores)
            cfg[nombre] = {"psi_r": hp.psi_desde_vector(xa, fijo, abl).como_dict(), "x_r": xa.tolist(), "menos_loglik": fa}
        cfg |= {"psi_r": psi_f.como_dict(), "x_r": dict(zip(hp.NOMBRES_R, xf.tolist())), "menos_loglik_r": ff,
                "parche_sigma_r": parche}
    hpj["parche_sigma_r"] = {"fecha": "2026-11-06", "sha256_antes": hp.huella(hp.leer(antes)),
                             "regla": "Σ_m += σ_R²·[[1,−1],[−1,1]] en verosimilitud y predicción; resto congelado salvo reajuste corto"}
    sha = hp.escribir(ruta, hpj)
    log(f"{ruta} escrito, sha256 {sha}")


def filtro_completo(a):
    """Variante «filtro completo» (6-nov): θ con covarianza cruzada. Parte del Ψ campo medio sin σ_R
    (`hiperparametros_antes_parche.json`) y reajusta SOLO lo que cambia al corregir el filtro (τ_θ, τ_I, σ_θ0, b_rank)
    con ≤ 2018; el resto queda congelado. Conserva el JSON del parche σ_R y el campo medio como alternativa."""
    ruta = Path(a.salida)
    if not ruta.with_name("hiperparametros_parche_sigma_r.json").exists():
        shutil.copyfile(ruta, ruta.with_name("hiperparametros_parche_sigma_r.json"))
    hpj = hp.leer(ruta.with_name("hiperparametros_antes_parche.json"))
    from tenis.modelo.parametros import Psi
    from tenis.modelo.rating_completo import VENTANA_ACTIVOS_ANIOS, filtrar_completo
    p, e = dm.cargar_export(hasta=HASTA)
    libres = [0, 1, 2, 3]
    for c in a.circuitos:
        cfg, d = hpj["circuitos"][c], dm.preparar(p, e, c, HASTA)
        fijo, x = cfg["fijo_r"], [cfg["x_r"][n] for n in hp.NOMBRES_R[:13]]
        tabs = tabla.construir_todas(tuple(cfg["lbar"]), fijo["sigma_eps"], fijo["rho_eps"])
        tabs_c = tabla.construir_todas((cfg["lbar_comun"],) * 4, fijo["sigma_eps"], fijo["rho_eps"])
        alternativa = {k: cfg[k] for k in ("psi_r", "x_r", "menos_loglik_r", "ablacion_sin_superficie", "ablacion_sin_fatiga")}
        base = {"d": d, "tablas": tabs, "fijo": fijo, "ablacion": ""}
        log(f"{c}: filtro completo, reajuste de {[hp.NOMBRES_R[i] for i in libres]} (−ll campo medio {cfg['menos_loglik_r']:.3f})")
        xn, fn, _ = hp.ajustar(hp._obj_rc, x, base, libres=libres, maxiter=a.maxiter, trabajadores=a.trabajadores)
        psi_n = hp.psi_desde_vector(xn, fijo)
        info = {"menos_loglik_campo_medio": cfg["menos_loglik_r"], "menos_loglik_completo": fn,
                "platt_2012_2018_campo_medio": hp.pendiente_platt(d, filtrar(d, Psi.desde_dict(cfg["psi_r"]), tabs).pi),
                "platt_2012_2018_completo": hp.pendiente_platt(d, filtrar_completo(d, psi_n, tabs).pi),
                "libres": [hp.NOMBRES_R[i] for i in libres], "ventana_activos_anios": VENTANA_ACTIVOS_ANIOS}
        log(f"{c}: −ll {fn:.3f}; Platt 2012–2018 {info['platt_2012_2018_campo_medio']:.3f} → {info['platt_2012_2018_completo']:.3f}")
        for nombre, abl, tb in (("ablacion_sin_superficie", "sin_superficie", tabs_c), ("ablacion_sin_fatiga", "sin_fatiga", tabs)):
            xa0 = list(cfg[nombre]["x_r"])[:13]
            xa0[:4] = xn[:4]
            xa, fa, _ = hp.ajustar(hp._obj_rc, xa0, dict(base, tablas=tb, ablacion=abl), libres=libres,
                                   maxiter=min(5, a.maxiter), trabajadores=a.trabajadores)
            cfg[nombre] = {"psi_r": hp.psi_desde_vector(xa, fijo, abl).como_dict(), "x_r": xa.tolist(), "menos_loglik": fa}
            log(f"{c}: {nombre} −ll {fa:.3f}")
        cfg |= {"filtro": "covarianza_completa", "psi_r": psi_n.como_dict(), "x_r": dict(zip(hp.NOMBRES_R, xn.tolist())),
                "menos_loglik_r": fn, "filtro_completo": info, "alternativa_campo_medio": alternativa}
    hpj["filtro_completo"] = {"fecha": "2026-11-06", "regla": "θ conjunta con covarianza cruzada (ventana de activos), d por jugador "
                              "con cov(θ_i, d_i); predicción con Var(θ_A − θ_B) incluida C_AB; bloques con Laplace conjunta (Woodbury)"}
    sha = hp.escribir(ruta, hpj)
    log(f"{ruta} escrito, sha256 {sha}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--circuitos", nargs="+", default=["atp", "wta"])
    ap.add_argument("--maxiter", type=int, default=30)
    ap.add_argument("--trabajadores", type=int, default=6)
    ap.add_argument("--salida", default=str(SALIDA / "hiperparametros.json"))
    ap.add_argument("--parche-sigma-r", action="store_true", help="solo el parche σ_R sobre el JSON existente")
    ap.add_argument("--filtro-completo", action="store_true", help="variante con covarianza cruzada de θ")
    ap.add_argument("--hilos-blas", type=int, default=2)
    a = ap.parse_args()
    for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[v] = str(a.hilos_blas)      # lo heredan los trabajadores (se fija antes de importar numpy en ellos)
    if a.parche_sigma_r:
        return parche_sigma_r(a)
    if a.filtro_completo:
        return filtro_completo(a)
    t0 = time.time()
    p, e = dm.cargar_export(hasta=HASTA)
    stats = pd.read_parquet(dm.RUTA_EXPORT / "estadisticas_saque.parquet",
                            columns=["partido_key", "lado", "puntos_saque", "puntos_saque_ganados", "visible_desde"])
    manif = json.loads((dm.RUTA_EXPORT / "manifiesto.json").read_text(encoding="utf-8"))
    salida = {"version": "tenis-modelo-s3-1.0.0", "temporadas_ajuste": [2005, HASTA], "ventana_verosimilitud": list(hp.VENTANA),
              "sha256_export": manif["sha256_export"], "especificacion": ESPECIFICACION,
              "priors": {"ln_kappa_de": hp.S_LOG_KAPPA, "gamma_de": hp.S_GAMMA}, "circuitos": {}}
    for c in a.circuitos:
        d = dm.preparar(p, e, c, HASTA)
        salida["circuitos"][c] = entrenar_circuito(d, observaciones(d, stats), a)
    salida["segundos"] = round(time.time() - t0)
    sha = hp.escribir(Path(a.salida), salida)
    log(f"{a.salida} escrito, sha256 {sha}")


if __name__ == "__main__":
    sys.exit(main())
