"""Dixon-Coles con gradiente analítico (prototipo de auditoría, NO producción).

Misma función objetivo que `qf.model.dixon_coles.DixonColes.fit`; solo cambia que se le da a L-BFGS-B el gradiente
exacto en vez de diferencias finitas. Variantes opcionales para la auditoría:
  - ridge_crudo: el ridge se expresa en "partidos recientes equivalentes" (se multiplica por la media de los pesos
    normalizados), en vez de quedar diluido por la normalización.
  - suma_cero_activos: la suma cero por liga se pondera por la muestra efectiva, para que los equipos sin datos no
    sirvan de holgura.
"""
import math

import numpy as np
from scipy.optimize import minimize

from qf.model import dixon_coles as dcm
from qf.model.dixon_coles import DCParams, DixonColes, team_key


class DixonColesRapido(DixonColes):
    def __init__(self, *a, ridge_crudo: float | None = None, suma_cero_activos: bool = False,
                 maxiter: int = 5000, **k):
        super().__init__(*a, **k)
        self.ridge_crudo = ridge_crudo
        self.suma_cero_activos = suma_cero_activos
        self.maxiter = maxiter
        self.resultado = None

    def fit(self, df, as_of=None):
        from datetime import datetime, timezone
        as_of = as_of or datetime.now(timezone.utc)
        df = df.dropna(subset=["home_goals", "away_goals"]).copy()
        comp_col = df["league_id"].fillna("_").astype(str).tolist() if "league_id" in df.columns else ["_"] * len(df)

        def _tl(col):
            if col not in df.columns:
                return list(comp_col)
            s = df[col].astype("object")
            return [c if (v is None or v != v or not str(v).strip()) else str(v) for v, c in zip(s.tolist(), comp_col)]

        hlg_col, alg_col = _tl("home_league"), _tl("away_league")
        leagues = sorted(set(comp_col) | set(hlg_col) | set(alg_col))
        self._lidx = {lg: i for i, lg in enumerate(leagues)}
        L = len(leagues)
        ci = np.array([self._lidx[x] for x in comp_col])
        lh = np.array([self._lidx[x] for x in hlg_col])
        la = np.array([self._lidx[x] for x in alg_col])
        hkeys = [team_key(lg, t) for lg, t in zip(hlg_col, df["home_team"])]
        akeys = [team_key(lg, t) for lg, t in zip(alg_col, df["away_team"])]
        teams = sorted(set(hkeys) | set(akeys))
        self._idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)
        hi = np.array([self._idx[k] for k in hkeys])
        ai = np.array([self._idx[k] for k in akeys])
        hg = df["home_goals"].to_numpy(float)
        ag = df["away_goals"].to_numpy(float)
        team_league = np.array([self._lidx[k.split("||", 1)[0]] for k in teams])

        from qf.model.xg import xg_at_cutoff
        hx, ax = xg_at_cutoff(df, as_of)
        b = self.xg_blend
        y_h = np.where(np.isnan(hx), hg, (1 - b) * hg + b * hx)
        y_a = np.where(np.isnan(ax), ag, (1 - b) * ag + b * ax)
        w_raw = self._weights(df["kickoff_utc"].to_numpy(), as_of)
        eff = np.zeros(n)
        np.add.at(eff, hi, w_raw)
        np.add.at(eff, ai, w_raw)
        w = w_raw / w_raw.mean()
        ridge = self.ridge if self.ridge_crudo is None else self.ridge_crudo / w_raw.mean()
        # Pesos de la suma cero: uniformes (producción) o proporcionales a la muestra efectiva.
        if self.suma_cero_activos:
            pz = eff + 1e-6
        else:
            pz = np.ones(n)
        pz_norm = np.zeros(n)
        for j in range(L):
            m_ = team_league == j
            if m_.any():
                pz_norm[m_] = pz[m_] / pz[m_].sum()

        m00 = (hg == 0) & (ag == 0)
        m01 = (hg == 0) & (ag == 1)
        m10 = (hg == 1) & (ag == 0)
        m11 = (hg == 1) & (ag == 1)
        base0 = math.log(max(float(np.mean([y_h.mean(), y_a.mean()])), 0.2))

        def f_g(p):
            atk, dfn = p[:n], p[n:2 * n]
            ha, base, stg = p[2 * n:2 * n + L], p[2 * n + L:2 * n + 2 * L], p[2 * n + 2 * L:2 * n + 3 * L]
            rho = p[-1]
            eh = base[ci] + ha[ci] + atk[hi] + stg[lh] - dfn[ai] - stg[la]
            ea = base[ci] + atk[ai] + stg[la] - dfn[hi] - stg[lh]
            lam, mu = np.exp(np.clip(eh, -13.8, 3.2)), np.exp(np.clip(ea, -13.8, 3.2))
            tau = np.ones_like(lam)
            dl = np.zeros_like(lam)   # dtau/dlam
            dm = np.zeros_like(lam)   # dtau/dmu
            dr = np.zeros_like(lam)   # dtau/drho
            tau[m00] = 1 - lam[m00] * mu[m00] * rho; dl[m00] = -mu[m00] * rho; dm[m00] = -lam[m00] * rho; dr[m00] = -lam[m00] * mu[m00]
            tau[m01] = 1 + lam[m01] * rho; dl[m01] = rho; dr[m01] = lam[m01]
            tau[m10] = 1 + mu[m10] * rho; dm[m10] = rho; dr[m10] = mu[m10]
            tau[m11] = 1 - rho; dr[m11] = -1.0
            tau_c = np.clip(tau, 1e-9, None)
            ll = y_h * eh - lam + y_a * ea - mu + np.log(tau_c)
            gh = -w * (y_h - lam + lam * dl / tau_c)
            ga = -w * (y_a - mu + mu * dm / tau_c)
            g = np.zeros_like(p)
            ga_atk, ga_dfn = g[:n], g[n:2 * n]
            np.add.at(ga_atk, hi, gh); np.add.at(ga_dfn, ai, -gh)
            np.add.at(ga_atk, ai, ga); np.add.at(ga_dfn, hi, -ga)
            gha = np.zeros(L); gb = np.zeros(L); gs = np.zeros(L)
            np.add.at(gha, ci, gh); np.add.at(gb, ci, gh + ga)
            np.add.at(gs, lh, gh - ga); np.add.at(gs, la, ga - gh)
            g[2 * n:2 * n + L] = gha; g[2 * n + L:2 * n + 2 * L] = gb; g[2 * n + 2 * L:2 * n + 3 * L] = gs
            g[-1] = -np.sum(w * dr / tau_c)
            pen = ridge * (np.sum(atk ** 2) + np.sum(dfn ** 2))
            g[:n] += 2 * ridge * atk; g[n:2 * n] += 2 * ridge * dfn
            for j in range(L):
                m_ = team_league == j
                if m_.any():
                    ma = np.sum(pz_norm[m_] * atk[m_]); md = np.sum(pz_norm[m_] * dfn[m_])
                    pen += dcm.SUM_ZERO * (ma ** 2 + md ** 2)
                    g[:n][m_] += 2 * dcm.SUM_ZERO * ma * pz_norm[m_]
                    g[n:2 * n][m_] += 2 * dcm.SUM_ZERO * md * pz_norm[m_]
            if L > 1:
                for off, peso, x in ((2 * n, dcm.POOL_HOME_ADV, ha), (2 * n + L, dcm.POOL_BASE, base),
                                     (2 * n + 2 * L, dcm.POOL_STRENGTH, stg)):
                    pen += peso * float(np.sum((x - x.mean()) ** 2))
                    g[off:off + L] += 2 * peso * (x - x.mean())
            return float(-np.sum(w * ll) + pen), g

        self._f_g = f_g
        x0 = np.concatenate([np.zeros(n), np.zeros(n), np.full(L, 0.25), np.full(L, base0), np.zeros(L), [-0.03]])
        bounds = ([(-2.5, 2.5)] * (2 * n) + [(-0.5, 1.0)] * L + [(-1.5, 1.8)] * L + [(-1.0, 1.0)] * L + [(-0.25, 0.25)])
        res = minimize(f_g, x0, jac=True, method="L-BFGS-B", bounds=bounds,
                       options={"maxiter": self.maxiter, "maxfun": 10 * self.maxiter, "ftol": 1e-12, "gtol": 1e-6})
        self.resultado = res
        p = res.x
        atk, dfn = p[:n], p[n:2 * n]
        ha, base, stg = p[2 * n:2 * n + L], p[2 * n + L:2 * n + 2 * L], p[2 * n + 2 * L:2 * n + 3 * L]
        lam_f = np.clip(np.exp(base[ci] + ha[ci] + atk[hi] + stg[lh] - dfn[ai] - stg[la]), 1e-6, 25)
        mu_f = np.clip(np.exp(base[ci] + atk[ai] + stg[la] - dfn[hi] - stg[lh]), 1e-6, 25)
        I_prior = 2.0 * self.ridge * float(w_raw.mean())
        I_atk, I_dfn = np.full(n, I_prior), np.full(n, I_prior)
        np.add.at(I_atk, hi, w_raw * lam_f); np.add.at(I_atk, ai, w_raw * mu_f)
        np.add.at(I_dfn, hi, w_raw * mu_f); np.add.at(I_dfn, ai, w_raw * lam_f)
        self.params = DCParams(teams=teams, attack=atk.tolist(), defence=dfn.tolist(), leagues=leagues,
                               home_adv=ha.tolist(), base=base.tolist(), strength=stg.tolist(),
                               team_leagues=[leagues[j] for j in team_league], effective_n=eff.tolist(),
                               se_attack=(1 / np.sqrt(I_atk)).tolist(), se_defence=(1 / np.sqrt(I_dfn)).tolist(),
                               rho=float(p[-1]), halflife_days=self.halflife, xg_blend=self.xg_blend, ridge=self.ridge,
                               fitted_at=as_of.isoformat(), n_matches=int(len(df)),
                               n_matches_by_league={lg: int((ci == j).sum()) for lg, j in self._lidx.items()})
        return self
