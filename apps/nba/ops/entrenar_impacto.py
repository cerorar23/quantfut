"""Entrenamiento LOCAL del artefacto de impacto por jugador y de las desviaciones de la mezcla equipo + jugadores (versión 2.1 del equipo).

    python apps/nba/ops/entrenar_impacto.py CARPETA SALIDA.json [STINTS.pkl LAM_RAPM VIDA_RAPM C_PRIOR LAM_RIDGE]

Con STINTS.pkl (de preparar_stints_s3c.py) el ridge del margen se centra en un a priori por jugador estimado sobre tramos de quinteto
(S3c); sin él, la configuración anterior (ridge λ = 10 hacia 0).

Reproduce la configuración medida en el Sprint 3b (ridge λ = 10, vida media 730 días, minutos esperados con partes y rol) y:
  1. mide, hacia adelante en 2023-24 y 2024-25, las desviaciones del margen y del total de la MEZCLA (media del rating de equipo y del
     modelo de jugadores), que son las que usa el motor al simular;
  2. ajusta el impacto con TODOS los partidos disponibles y lo guarda como artefacto versionado (el servidor no entrena, D4).
"""
from datetime import date
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import evaluar_s3 as e3  # noqa: E402
import evaluar_s3b as e3b  # noqa: E402
from nba.v2 import plantilla  # noqa: E402
from nba.v2.nucleo import Parametros  # noqa: E402
from nba.v2.plantilla import PartidoFila  # noqa: E402

LAM, VIDA = 10.0, 730.0


def main(carpeta: Path, salida: Path, rapm_args: tuple | None = None):
    lam, c_prior, rapm = LAM, 0.0, None
    if rapm_args:
        import pickle
        import evaluar_s3c as e3c
        pkl, lam_rapm, vida_rapm, c_prior, lam = rapm_args
        rapm = e3c.Rapm(pickle.load(open(pkl, "rb")), lam_rapm, vida_rapm)
        e3b.prior_en = lambda corte, c, n0=0.0, vida_=0.0: {j: c * b for j, b in rapm.beta(corte).items()}
    juegos, _ = e3.leer(carpeta)
    p_nucleo = Parametros(eta=0.045, arrastre=0.65, eta_liga=0.01, efecto_b2b=2.90)
    mus_nucleo = e3.recorrer(juegos, p_nucleo)                    # también deja j["dias"]
    por_pid = {g["pid"]: g for g in juegos}
    for g in juegos:
        g["dia"] = date.fromisoformat(g["fecha"]).toordinal()
    cajas, estados = e3b.leer_cajas(carpeta, por_pid)
    registros = e3b.registrar_candidatos(juegos, cajas, estados)
    tabla_estado, tabla_sp = e3b.tablas_p_juega(juegos, registros, "2023-24")
    esperados = {pid: e3b.minutos_del_partido(reg, tabla_estado, tabla_sp) for pid, reg in registros.items()}
    reales = {pid: {lado: dict(cajas[pid][lado]) for lado in ("local", "visit")} for pid in registros}
    descansos = {g["pid"]: (1.0 if g["dias"]["visit"] == 1 else 0.0) - (1.0 if g["dias"]["local"] == 1 else 0.0) for g in juegos}
    filas = [PartidoFila(g["dia"], g["pl"] - g["pv"], g["pl"] + g["pv"], reales[g["pid"]]["local"], reales[g["pid"]]["visit"], descansos[g["pid"]])
             for g in juegos if g["pid"] in reales]

    temporadas = sorted({g["temporada"] for g in juegos})
    validar = {"2023-24", "2024-25"}
    primero = min(g["dia"] for g in juegos if g["temporada"] == temporadas[1])
    val = [g for g in juegos if g["pid"] in registros and g["temporada"] in validar]
    pred = e3b.predecir_bloques(filas, esperados, val, lam, VIDA, primero, descansos, c_prior)
    nuc = {g["pid"]: m for g, m in zip(juegos, mus_nucleo)}
    res_m, res_t, res_mj, res_tj = [], [], [], []
    for g in val:
        pm, pt = pred[g["pid"]]
        nm, nt = nuc[g["pid"]][0] - nuc[g["pid"]][1], nuc[g["pid"]][0] + nuc[g["pid"]][1]
        res_m.append((g["pl"] - g["pv"]) - (pm + nm) / 2)
        res_t.append((g["pl"] + g["pv"]) - (pt + nt) / 2)
        res_mj.append((g["pl"] - g["pv"]) - nm)
        res_tj.append((g["pl"] + g["pv"]) - nt)
    prior = e3b.prior_en(max(g["dia"] for g in juegos) + 1, c_prior) if rapm else None
    imp = plantilla.ajustar(filas, lam, lam, VIDA, prior_beta=prior)
    artefacto = {
        "formato": 1, "entrenado": date.today().isoformat(), "datos_hasta": max(g["fecha"] for g in juegos), "lam": lam, "vida_media_dias": VIDA,
        "a_priori": ({"tipo": "rapm_quintetos", "lam_rapm": rapm_args[1], "vida_rapm": rapm_args[2], "c": c_prior} if rapm else {"tipo": "ninguno"}),
        "partidos_entrenamiento": len(filas), "jugadores": len(imp.beta),
        "c_margen": round(imp.c_margen, 5), "d_margen": round(imp.d_margen, 5), "c_total": round(imp.c_total, 5), "d_total": round(imp.d_total, 5),
        "sigma_margen_mezcla": round(float(np.std(res_m)), 4), "sigma_total_mezcla": round(float(np.std(res_t)), 4),
        "validacion": {"temporadas": sorted(validar), "n": len(val), "rmse_margen_mezcla": round(e3.rmse(res_m, np.zeros(len(res_m))), 4),
                       "rmse_margen_equipo": round(e3.rmse(res_mj, np.zeros(len(res_mj))), 4),
                       "rmse_total_mezcla": round(e3.rmse(res_t, np.zeros(len(res_t))), 4), "rmse_total_equipo": round(e3.rmse(res_tj, np.zeros(len(res_tj))), 4)},
        "beta": {str(k): round(v, 4) for k, v in sorted(imp.beta.items())}, "tau": {str(k): round(v, 4) for k, v in sorted(imp.tau.items())},
    }
    salida.write_text(json.dumps(artefacto, ensure_ascii=False, sort_keys=True), encoding="utf8")
    print("artefacto", salida, hashlib.sha256(salida.read_bytes()).hexdigest()[:12], "jugadores", len(imp.beta))
    print({k: artefacto[k] for k in ("c_margen", "d_margen", "c_total", "sigma_margen_mezcla", "sigma_total_mezcla", "validacion")})


if __name__ == "__main__":
    extra = (sys.argv[3], float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6]), float(sys.argv[7])) if len(sys.argv) > 3 else None
    main(Path(sys.argv[1]), Path(sys.argv[2]), extra)
