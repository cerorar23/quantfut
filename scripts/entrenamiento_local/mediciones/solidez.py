"""Solidez de los bloques que pasan: la misma puerta con 4 particiones de validación (20/30/40/50 % final)."""
import json
import sys

import pandas as pd

from qf.model import ajuste, contexto

oos = pd.read_pickle(sys.argv[1])
frame = contexto.marco_contexto(oos)
contexto.registrar_bloques()
casos = [["altitud"], ["altitud_salto"], ["epi_total"], ["epi_grupos"], ["clima"], ["bajas"],
         ["altitud_salto", "epi_total"], ["altitud", "epi_grupos"]]
out = {}
for bloques in casos:
    fila = {}
    for h in (0.2, 0.3, 0.4, 0.5):
        r = ajuste.comparar(frame, [], bloques, holdout_frac=h)
        fila[h] = {"ok": r["ok"], "d": r["delta_rps_media"], "p95": r["delta_rps_p95"], "n": r["n_val"],
                   "ligas": f'{r["leagues_improved"]}/{len(r["by_league"])}'}
    out["+".join(bloques)] = fila
    print("+".join(bloques), {h: (v["ok"], v["d"], v["p95"], v["ligas"]) for h, v in fila.items()}, flush=True)
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1, default=str)
