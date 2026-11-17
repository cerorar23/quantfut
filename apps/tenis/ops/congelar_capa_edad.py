"""Congela la capa de edad en un artefacto de hiperparámetros NUEVO (no toca el existente ni la base de datos).

Uso: python apps/tenis/ops/congelar_capa_edad.py --dir <carpeta con hiperparametros.json y evaluacion_wf.json>
                                                 [--salida hiperparametros_capa_edad.json]

- Lee `evaluacion_wf.json` (salida de `evaluar_wf.py`) y exige, por circuito, que `G_capa_edad.capa_activa` sea verdadera:
  el IC95 de Δ log-loss frente a la capa de pendiente actual debe quedar por debajo de 0. Si un circuito no pasa, no
  se le añade capa y se avisa.
- Añade `circuitos[c]["capa_edad"]` (b, β, escala, n, rango de temporadas) al JSON de hiperparámetros y lo escribe con su
  propia huella sha256. Registrarlo como `artefacto_activo` (nueva `version_modelo`) es una decisión de despliegue aparte.
"""
import argparse
import json
import sys
from pathlib import Path

from tenis.modelo import capa_edad as ce
from tenis.modelo import hiperparametros as hp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--salida", default="hiperparametros_capa_edad.json")
    a = ap.parse_args()
    carpeta = Path(a.dir)
    hpj = hp.leer(carpeta / "hiperparametros.json")
    informe = json.loads((carpeta / "evaluacion_wf.json").read_text(encoding="utf-8"))
    if informe.get("sha256_hiperparametros") != hp.huella(hpj):
        sys.exit("evaluacion_wf.json no corresponde a este hiperparametros.json (huellas distintas)")
    puestas = []
    for c, r in informe["circuitos"].items():
        g = r["compuertas"].get("G_capa_edad")
        if not g or not g["capa_activa"] or not r.get("capa_edad_final"):
            print(f"{c}: la capa de edad NO pasa su compuerta; no se añade")
            continue
        capa = ce.CapaEdad.desde_dict(r["capa_edad_final"])          # valida rangos y finitud
        hpj["circuitos"][c]["capa_edad"] = capa.como_dict()
        puestas.append(c)
        print(f"{c}: b={capa.pendiente:.4f} β={capa.beta:.4f} escala={capa.escala:.3f} años, n={capa.n}, "
              f"temporadas {capa.desde}-{capa.hasta}; Δlog-loss {g['dif_logloss']:+.4f} [{g['lo']:+.4f}, {g['hi']:+.4f}]")
    if not puestas:
        sys.exit("ningún circuito pasa la compuerta: no se escribe artefacto")
    hpj["nota_capa_edad"] = ("Capa de edad 17-nov-2026: logit π' = b·logit π + β·(Δedad/escala), sin intercepto; reemplaza la "
                             "pendiente de recalibración. Ver docs/tenis_capa_edad_20261117.md.")
    sha = hp.escribir(carpeta / a.salida, hpj)
    print(f"escrito {carpeta / a.salida}  sha256_contenido={sha}")


if __name__ == "__main__":
    main()
