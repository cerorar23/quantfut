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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--circuitos", nargs="+", default=["atp", "wta"])
    ap.add_argument("--maxiter", type=int, default=30)
    ap.add_argument("--trabajadores", type=int, default=6)
    ap.add_argument("--salida", default=str(SALIDA / "hiperparametros.json"))
    a = ap.parse_args()
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
