"""Comprueba el gradiente analítico y compara con el ajuste de producción en el mismo corte."""
import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy.optimize import approx_fprime

sys.path.insert(0, "/tmp")
from dc_rapido import DixonColesRapido  # noqa: E402
from qf.model.train import load_training_data  # noqa: E402

df = load_training_data()
df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
corte = datetime(2026, 10, 19, tzinfo=timezone.utc)

# 1) gradiente: muestra pequeña
peq = df[df.kickoff_utc > "2025-06-01"]
m = DixonColesRapido(maxiter=3)
m.fit(peq, as_of=corte)
x = m.resultado.x + np.random.default_rng(0).normal(0, 0.05, len(m.resultado.x))
x[-1] = -0.05
f0, g = m._f_g(x)
idx = np.random.default_rng(1).choice(len(x), 25, replace=False).tolist() + [len(x) - 1]
num = [(m._f_g(np.where(np.arange(len(x)) == i, x + 1e-5, x))[0] - m._f_g(np.where(np.arange(len(x)) == i, x - 1e-5, x))[0]) / 2e-5 for i in idx]
err = np.max(np.abs(np.array(num) - g[idx]) / (np.abs(g[idx]) + 1e-3))
print(f"gradiente: error relativo máximo {err:.2e}", flush=True)

# 2) ajuste completo, convergencia y tiempo
for nombre, kw in (("rapido", {}), ("rapido+suma_cero_activos", {"suma_cero_activos": True})):
    t = time.time()
    m = DixonColesRapido(**kw)
    m.fit(df, as_of=corte)
    r = m.resultado
    print(f"{nombre}: success={r.success} msg={r.message} nit={r.nit} nfev={r.nfev} fun={r.fun:.2f} {time.time() - t:.0f}s", flush=True)
    eff = np.array(m.params.effective_n); atk = np.array(m.params.attack)
    print(f"   eff<1 |ataque| medio {np.abs(atk[eff < 1]).mean():.3f} max {np.abs(atk[eff < 1]).max():.3f}; rho {m.params.rho:.4f}", flush=True)
    for h, a, lg in (("Hull", "Aston Villa", "gb.premier_league"), ("Coventry", "Newcastle", "gb.premier_league"),
                     ("Barcelona", "Real Madrid", "es.laliga")):
        p = m.predict(h, a, lg)["1x2"]
        print(f"   {h}-{a}: {p['home']:.3f}/{p['draw']:.3f}/{p['away']:.3f}", flush=True)
print("producción (medido antes): success=False fun=84343.69 1384 s", flush=True)
