import numpy as np, pandas as pd
from qf.db import query
from qf.model import ajuste, lineup_challenger as lc
f = query("""SELECT p.etapa, p.home_lambda, p.away_lambda, p.rho, m.home_goals, m.away_goals,
                    (p.data_completeness->'ajuste_altitud'->>'factor_local')::float fl,
                    (p.data_completeness->'ajuste_altitud'->>'factor_visita')::float fv
             FROM predictions p JOIN matches m USING (match_id)
             WHERE m.status='finished' AND m.home_goals IS NOT NULL AND p.data_completeness ? 'ajuste_altitud'
               AND p.generated_at > '2026-10-19'""")
d = pd.DataFrame(f)
for etapa, g in d.groupby("etapa"):
    mov = (np.abs(np.log(g.fl)) > 0.005) | (np.abs(np.log(g.fv)) > 0.005)
    h = g[mov]
    lam, mu, rho = (h[c].to_numpy(float) for c in ("home_lambda", "away_lambda", "rho"))
    res = np.where(h.home_goals > h.away_goals, 0, np.where(h.home_goals == h.away_goals, 1, 2))
    p0 = lc._probabilities(lam, mu, rho); p1 = lc._probabilities(lam * h.fl.to_numpy(), mu * h.fv.to_numpy(), rho)
    dl, p95 = ajuste._delta_rps(p0, p1, res)
    print(etapa, "partidos con efecto", len(h), "RPS sin", round(float(ajuste._rps_por_partido(p0, res).mean()), 5),
          "con", round(float(ajuste._rps_por_partido(p1, res).mean()), 5), "delta", dl, "p95", p95)
