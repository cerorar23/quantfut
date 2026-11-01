"""¿Converge el ajuste de Dixon-Coles? Captura el resultado de scipy.minimize (solo lectura)."""
import time
from datetime import datetime, timezone

import pandas as pd
import scipy.optimize

from qf.model import dixon_coles
from qf.model.train import load_training_data

capt = {}
orig = scipy.optimize.minimize


def espia(*a, **k):
    t = time.time()
    r = orig(*a, **k)
    capt.update(success=r.success, message=str(r.message), nit=r.nit, nfev=r.nfev, fun=float(r.fun),
                nparams=len(r.x), seg=round(time.time() - t))
    return r


dixon_coles.minimize = espia
df = load_training_data()
df["kickoff_utc"] = pd.to_datetime(df["kickoff_utc"], utc=True)
print("partidos", len(df), "desde", df.kickoff_utc.min(), flush=True)
m = dixon_coles.DixonColes()
m.fit(df, as_of=datetime(2026, 10, 19, tzinfo=timezone.utc))
print("completo:", capt, flush=True)
p = m.params
import numpy as np
eff = np.array(p.effective_n)
atk, dfn = np.array(p.attack), np.array(p.defence)
for nombre, mask in (("eff<1", eff < 1), ("1<=eff<5", (eff >= 1) & (eff < 5)), ("eff>=5", eff >= 5)):
    print(f"{nombre}: equipos {mask.sum()} |ataque| medio {np.abs(atk[mask]).mean():.3f} max {np.abs(atk[mask]).max():.3f} |defensa| max {np.abs(dfn[mask]).max():.3f}")
for t in ("gb.premier_league||Hull", "gb.premier_league||Coventry", "nl.eredivisie||Cambuur", "nl.eredivisie||Telstar"):
    if t in m._idx:
        i = m._idx[t]
        print(t, "eff", round(eff[i], 2), "atk", round(atk[i], 3), "def", round(dfn[i], 3))
