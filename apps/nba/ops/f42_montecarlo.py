"""F4.2 — Monte Carlo del marcador: convergencia, semillas, tiempos y huella reproducible.

    python apps/nba/ops/f42_montecarlo.py CARPETA_CON_predicciones_s3b.json [convergencia|huella]

* convergencia: con 200 partidos reales de la temporada de prueba (media de la mezcla equipo + jugadores y desviaciones de producción), compara
  el resultado con n = 1.000 … 100.000 simulaciones frente a una referencia de 2.000.000 con otra semilla, en 20 semillas por tamaño.
* huella: sha256 de las muestras de casos fijos (media, desviaciones, semilla): debe ser idéntica en cualquier máquina con la misma versión de numpy.
"""
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nba.v2 import mercados, nucleo  # noqa: E402

SIGMA_MARGEN, SIGMA_TOTAL = 14.06, 18.43
TAMANOS = (1_000, 5_000, 20_000, 100_000)
REFERENCIA_N = 2_000_000


def cantidades(m: nucleo.Marcador, linea_total: float, linea_margen: float):
    mg, tt = m.margen(), m.total()
    return np.array([mercados.ganador(m), mercados.total(m, linea_total), mercados.handicap(m, linea_margen), mg.cuantil(0.1), mg.cuantil(0.9),
                     tt.cuantil(0.1), tt.cuantil(0.9)])


def convergencia(carpeta: Path):
    datos = [g for g in json.loads((carpeta / "predicciones_s3b.json").read_text(encoding="utf8")) if g["temporada"] == "2025-26"]
    datos = datos[:: max(1, len(datos) // 200)][:200]
    nombres = ["p_local", "P(total más de línea)", "P(local cubre −3,5)", "cuantil 10 % margen", "cuantil 90 % margen", "cuantil 10 % total", "cuantil 90 % total"]
    error = {n: [] for n in TAMANOS}
    for i, g in enumerate(datos):
        margen = ((g["equipo_mu"][0] - g["equipo_mu"][1]) + g["jugadores_margen"]) / 2
        total = g["equipo_mu"][0] + g["equipo_mu"][1]
        mu_l, mu_v = (total + margen) / 2, (total - margen) / 2
        linea_total = round(total - 0.5) + 0.5
        ref = cantidades(nucleo.simular(mu_l, mu_v, SIGMA_MARGEN, SIGMA_TOTAL, n=REFERENCIA_N, semilla=10_000_000 + i), linea_total, -3.5)
        for n in TAMANOS:
            for s in range(20):
                est = cantidades(nucleo.simular(mu_l, mu_v, SIGMA_MARGEN, SIGMA_TOTAL, n=n, semilla=s * 1000 + i), linea_total, -3.5)
                error[n].append(np.abs(est - ref))
    print(f"{len(datos)} partidos × 20 semillas por tamaño; referencia {REFERENCIA_N:,} simulaciones")
    print("| n | " + " | ".join(nombres[:3]) + " | cuantiles (puntos) |")
    print("|---|---|---|---|---|")
    for n in TAMANOS:
        e = np.array(error[n])
        p = e[:, :3] * 100
        print(f"| {n:,} | " + " | ".join(f"media {p[:, k].mean():.2f} pp · p99 {np.percentile(p[:, k], 99):.2f} pp" for k in range(3))
              + f" | media {e[:, 3:].mean():.2f} · p99 {np.percentile(e[:, 3:], 99):.2f} |")
    print("error típico teórico de una probabilidad 50 %:", {n: round(100 * (0.25 / n) ** 0.5, 3) for n in TAMANOS}, "pp")
    for n in (20_000, 100_000, 400_000):
        t0 = time.perf_counter()
        for s in range(20):
            nucleo.simular(113.0, 110.0, SIGMA_MARGEN, SIGMA_TOTAL, n=n, semilla=s)
        print(f"tiempo por simulación con n = {n:,}: {1000 * (time.perf_counter() - t0) / 20:.1f} ms")
    # semillas consecutivas (los id de partido lo son): los flujos no deben correlacionarse
    r = [np.corrcoef(nucleo.simular(113.0, 110.0, 14.0, 18.0, n=20_000, semilla=s).muestras[:, 0],
                     nucleo.simular(113.0, 110.0, 14.0, 18.0, n=20_000, semilla=s + 1).muestras[:, 0])[0, 1] for s in range(1000, 1100)]
    print(f"correlación entre flujos de semillas consecutivas: media {np.mean(r):+.4f}, máx |r| {np.max(np.abs(r)):.4f} (esperado ≈ ±{1 / 20000 ** 0.5:.4f})")


def huella():
    casos = [(113.0, 110.0, 14.06, 18.43, 1), (120.5, 98.25, 14.06, 18.43, 424242), (100.0, 100.0, 13.0, 18.0, 0), (130.0, 90.0, 14.06, 18.43, 2**31 - 1)]
    for mu_l, mu_v, sm, st, semilla in casos:
        m = nucleo.simular(mu_l, mu_v, sm, st, n=20_000, semilla=semilla)
        print(f"numpy {np.__version__} caso {mu_l}/{mu_v}/{semilla}: {hashlib.sha256(np.ascontiguousarray(m.muestras).tobytes()).hexdigest()}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    accion = sys.argv[2] if len(sys.argv) > 2 else "convergencia"
    convergencia(Path(sys.argv[1])) if accion == "convergencia" else huella()
