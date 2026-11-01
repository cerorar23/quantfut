"""Walk-forward del Dixon-Coles base con otra media vida y/o ventana de validación más larga.

    wf.py <salida.pkl> <media_vida_días> [días_de_validación=1095]

Mismos cortes (cada 30 días), mismos datos y misma configuración de producción que `qf.model.train`; solo cambia
la ventana (3 años en vez de 1) para que las comparaciones tengan potencia. No toca la base ni los artefactos.
"""
import sys
from datetime import timedelta

from qf.eval.backtest import walk_forward_oos
from qf.model.train import load_training_data
from qf.config import settings

salida, hl = sys.argv[1], float(sys.argv[2])
dias = int(sys.argv[3]) if len(sys.argv) > 3 else 1095
df = load_training_data()
inicio = df["kickoff_utc"].max() - timedelta(days=dias)
print(f"partidos={len(df)} ventana desde {inicio:%F} media vida={hl} xg_blend={settings.xg_blend}", flush=True)
oos = walk_forward_oos(df, inicio, halflife=hl, xg_blend=settings.xg_blend)
oos.to_pickle(salida)
print(f"OOS {len(oos)} filas -> {salida}", flush=True)
