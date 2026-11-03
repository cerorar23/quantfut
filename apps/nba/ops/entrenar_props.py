"""Entrenamiento LOCAL del artefacto de props (el VPS solo infiere con artefactos versionados, decisión D4).

    python apps/nba/ops/entrenar_props.py CARPETA SALIDA.json

Usa todas las temporadas disponibles (2021-22 en adelante) con los mismos archivos que `evaluar_s4.py`: prior de tasa por nivel de rol,
residuos de minutos por tramo, sobredispersión por estadística y probabilidades de jugar (por estado del parte y, sin parte, por tramo de
minutos esperados). (k, decaimiento) vienen de la validación del Sprint 4 (30 minutos, 0,97).
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
import evaluar_s4 as e4  # noqa: E402
from nba.v2 import minutos, props  # noqa: E402

K, DECAIMIENTO = 30.0, 0.97


def main(carpeta: Path, salida: Path):
    juegos, _ = e3.leer(carpeta)
    for g in juegos:
        g["dia"] = date.fromisoformat(g["fecha"]).toordinal()
    por_pid = {g["pid"]: g for g in juegos}
    filas, _, _ = e4.construir_filas(carpeta, juegos)
    mp = filas["mp"].astype(float)
    prior = props.prior_por_nivel(mp, filas["m"], filas["y"])
    res = minutos.ajustar_residuos(zip(mp, filas["m"]))
    tasa = props.tasa_por_minuto(filas["mh"], filas["sh"], prior[props.nivel(mp)], K, DECAIMIENTO)
    alfas = [props.estimar_alfa(tasa[:, s] * filas["m"], filas["y"][:, s]) for s in range(len(props.ESTADISTICAS))]
    cajas, estados = e3b.leer_cajas(carpeta, por_pid)
    registros = e3b.registrar_candidatos(juegos, cajas, estados)
    p_estado, p_sin_parte = e3b.tablas_p_juega(juegos, registros, "9999")
    artefacto = {
        "formato": 1, "entrenado": date.today().isoformat(), "datos_hasta": max(g["fecha"] for g in juegos),
        "filas_entrenamiento": int(len(mp)), "k_minutos": K, "decaimiento": DECAIMIENTO,
        "estadisticas": list(props.ESTADISTICAS), "bordes_rol": list(props.BORDES_ROL),
        "prior_por_nivel": prior.round(6).tolist(),
        "residuos_minutos": {"cortes": list(res.cortes), "cuantiles": [np.round(c, 4).tolist() for c in res.cuantiles]},
        "alfa": dict(zip(props.ESTADISTICAS, np.round(alfas, 5).tolist())),
        "p_juega_estado": {k: round(v, 5) for k, v in p_estado.items()},
        "p_juega_sin_parte_por_tramo": {str(k): round(v, 5) for k, v in p_sin_parte.items()},
        "tramos_minutos": list(e3b.TRAMOS),
    }
    salida.write_text(json.dumps(artefacto, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf8")
    print("artefacto", salida, hashlib.sha256(salida.read_bytes()).hexdigest()[:12], "filas", len(mp), "alfas", artefacto["alfa"])
    print("P(juega) por estado:", artefacto["p_juega_estado"], "sin parte por tramo:", artefacto["p_juega_sin_parte_por_tramo"])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
