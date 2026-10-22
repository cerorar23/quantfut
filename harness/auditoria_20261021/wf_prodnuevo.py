"""Walk-forward 2024-01 -> 2026-10 con el dixon_coles.py NUEVO (copia aislada en /tmp/qfa/src)."""
import sys
import time

sys.path.insert(0, "/tmp/qfa/src")
import pandas as pd  # noqa: E402

import qf  # noqa: E402
from qf.eval.backtest import walk_forward_oos  # noqa: E402
from qf.model.train import load_training_data  # noqa: E402

assert qf.__file__.startswith("/tmp/qfa/"), qf.__file__
t = time.time()
df = load_training_data()
df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
oos = walk_forward_oos(df, "2024-01-01", halflife=270.0, xg_blend=0.65)
oos["conv"] = True
oos.to_pickle("/srv/quantfut/artifacts/audit/wf_prodnuevo.pkl")
print("FIN", len(oos), f"{(time.time() - t) / 60:.1f} min", flush=True)
