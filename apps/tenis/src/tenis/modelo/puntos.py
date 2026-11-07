"""Pieza P (plan D.2): probabilidad de punto al saque/resto por jugador, con superficie y forma del día.

    y_A = logit emp. de W_A/N_A = μ_s + κ^P_s·(α_A − β_B) + (a_{A,s} − b_{B,s}) + ε_A + ruido binomial
    (ε_A, ε_B) ~ N₂(0, σ_ε²·[[1, ρ_ε], [ρ_ε, 1]])   (forma del día del partido)

Filtro de Kalman sobre logits empíricos (ruido binomial 1/(N·p̂·(1 − p̂)) con p̂ predicho) en orden de visibilidad de
las estadísticas; α, β con paseo aleatorio (τ_α, τ_β), a, b estáticos con prior N(0, σ_ab²), μ_s con paseo lento τ_μ.
Aproximación declarada: estados escalares independientes (campo medio; se descartan covarianzas cruzadas).
Entrega Ŝ = E[p_A + p_B] en el corte (aprox. probit de E[expit(η)]), σ_ε, ρ_ε y ℓ̄_s (media de μ_s en el ajuste).
"""
import math
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .datos import HARD
from .estado import ANIO_NS

MU0, VAR_MU0 = 0.5, 0.25


@dataclass(frozen=True)
class PsiP:
    sigma_alpha0: float
    sigma_beta0: float
    tau_alpha: float
    tau_beta: float
    sigma_ab: float
    kappa: tuple          # κ^P (Clay, Grass, Hard ≡ 1, Indoor)
    sigma_eps: float
    rho_eps: float
    tau_mu: float

    def __post_init__(self):
        if self.kappa[HARD] != 1.0 or min(self.kappa) <= 0 or not -1 < self.rho_eps < 1:
            raise ValueError("κ^P_Hard ≡ 1, κ > 0 y ρ_ε ∈ (−1, 1)")

    def como_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(self).items()}


def observaciones(d, stats: pd.DataFrame) -> pd.DataFrame:
    """Una fila por partido con estadísticas de los dos lados (en el orden de lados de la exportación)."""
    s = stats[stats.partido_key.isin(set(d.p.partido_key))]
    a = s[s.lado == 1].set_index("partido_key")[["puntos_saque", "puntos_saque_ganados", "visible_desde"]]
    b = s[s.lado == 2].set_index("partido_key")[["puntos_saque", "puntos_saque_ganados"]]
    o = a.join(b, lsuffix="_1", rsuffix="_2", how="inner").dropna()
    # Imposibles (ganados > jugados: 15 filas de SofaScore 2023–2026 en la exportación) fuera, con el partido entero.
    o = o[(o.puntos_saque_1 > 0) & (o.puntos_saque_2 > 0) & (o.puntos_saque_ganados_1 >= 0) & (o.puntos_saque_ganados_2 >= 0)
          & (o.puntos_saque_ganados_1 <= o.puntos_saque_1) & (o.puntos_saque_ganados_2 <= o.puntos_saque_2)]
    info = d.p.set_index("partido_key")[["j1", "j2", "sup", "temporada"]]
    o = o.join(info, how="inner").reset_index()
    idx_v = pd.DatetimeIndex(o.visible_desde)
    idx_v = idx_v.tz_convert("UTC") if idx_v.tz is not None else idx_v.tz_localize("UTC")
    o["vis_ns"] = idx_v.astype("datetime64[ns, UTC]").astype("int64").to_numpy()
    o = o[o.sup >= 0]
    return o.sort_values(["vis_ns", "partido_key"], kind="mergesort").reset_index(drop=True)


def filtrar_p(d, obs: pd.DataFrame, psi: PsiP, ventana=(2007, 2018), predecir=True):
    """Devuelve (log-verosimilitud predictiva en la ventana, Ŝ por partido de d.p, media de μ_s en la ventana)."""
    n_j = d.n_jugadores
    ma, mb = [0.0] * n_j, [0.0] * n_j
    va, vb = [psi.sigma_alpha0 ** 2] * n_j, [psi.sigma_beta0 ** 2] * n_j
    sa, sb = [[0.0] * 4 for _ in range(n_j)], [[0.0] * 4 for _ in range(n_j)]
    vsa, vsb = [[psi.sigma_ab ** 2] * 4 for _ in range(n_j)], [[psi.sigma_ab ** 2] * 4 for _ in range(n_j)]
    t = [None] * n_j
    mu, vmu, tmu = [MU0] * 4, [VAR_MU0] * 4, [None] * 4
    se2, cov_e = psi.sigma_eps ** 2, psi.rho_eps * psi.sigma_eps ** 2
    ta2, tb2, tm2 = psi.tau_alpha ** 2, psi.tau_beta ** 2, psi.tau_mu ** 2
    ll, suma_mu, n_mu = 0.0, [0.0] * 4, [0] * 4

    def prop(j, now):
        if t[j] is not None and now > t[j]:
            dt = (now - t[j]) / ANIO_NS
            va[j] += ta2 * dt; vb[j] += tb2 * dt
        t[j] = now

    cols = [obs[c].tolist() for c in ("vis_ns", "j1", "j2", "sup", "puntos_saque_1", "puntos_saque_ganados_1",
                                      "puntos_saque_2", "puntos_saque_ganados_2", "temporada")]
    p_corte, p_j1, p_j2, p_sup = d.p.corte_ns.tolist(), d.p.j1.tolist(), d.p.j2.tolist(), d.p.sup.tolist()
    s_hat = np.full(len(d.p), np.nan)
    io, n_o = 0, len(cols[0])

    def aplicar(i):
        nonlocal ll
        vis, a, b, s, n1, w1, n2, w2, temp = (c[i] for c in cols)
        prop(a, vis); prop(b, vis)
        if tmu[s] is not None and vis > tmu[s]:
            vmu[s] += tm2 * (vis - tmu[s]) / ANIO_NS
        tmu[s] = vis
        k = psi.kappa[s]
        e1 = mu[s] + k * (ma[a] - mb[b]) + sa[a][s] - sb[b][s]
        e2 = mu[s] + k * (ma[b] - mb[a]) + sa[b][s] - sb[a][s]
        y1 = math.log((w1 + 0.5) / (n1 - w1 + 0.5)); y2 = math.log((w2 + 0.5) / (n2 - w2 + 0.5))
        p1, p2 = 1 / (1 + math.exp(-e1)), 1 / (1 + math.exp(-e2))
        s11 = vmu[s] + k * k * (va[a] + vb[b]) + vsa[a][s] + vsb[b][s] + se2 + 1 / (n1 * p1 * (1 - p1))
        s22 = vmu[s] + k * k * (va[b] + vb[a]) + vsa[b][s] + vsb[a][s] + se2 + 1 / (n2 * p2 * (1 - p2))
        s12 = vmu[s] + cov_e
        det = s11 * s22 - s12 * s12
        i11, i22, i12 = s22 / det, s11 / det, -s12 / det
        r1, r2 = y1 - e1, y2 - e2
        if ventana[0] <= temp <= ventana[1]:
            ll += -math.log(2 * math.pi) - 0.5 * math.log(det) - 0.5 * (r1 * r1 * i11 + 2 * r1 * r2 * i12 + r2 * r2 * i22)
            suma_mu[s] += mu[s]; n_mu[s] += 1
        # (vector de estado, índice, var, h1, h2): cada estado escalar aparece en una o en las dos observaciones
        for lista, j, h1, h2 in ((ma, a, k, 0.0), (mb, b, -k, 0.0), (ma, b, 0.0, k), (mb, a, 0.0, -k)):
            vv = va if lista is ma else vb
            _upd(lista, vv, j, h1, h2, i11, i12, i22, r1, r2)
        for lista, vv, j, h1, h2 in ((sa[a], vsa[a], s, 1.0, 0.0), (sb[b], vsb[b], s, -1.0, 0.0),
                                     (sa[b], vsa[b], s, 0.0, 1.0), (sb[a], vsb[a], s, 0.0, -1.0)):
            _upd(lista, vv, j, h1, h2, i11, i12, i22, r1, r2)
        _upd(mu, vmu, s, 1.0, 1.0, i11, i12, i22, r1, r2)

    for i in range(len(p_corte)):
        while io < n_o and cols[0][io] < p_corte[i]:
            aplicar(io); io += 1
        if predecir and p_sup[i] >= 0:
            a, b, s = p_j1[i], p_j2[i], p_sup[i]
            s_hat[i] = _esperanza_suma(psi, s, mu, vmu, ma, mb, va, vb, sa, sb, vsa, vsb, a, b, t, tmu, p_corte[i])
    while io < n_o:
        aplicar(io); io += 1
    lbar = tuple(suma_mu[s] / n_mu[s] if n_mu[s] else float("nan") for s in range(4))
    return ll, s_hat, lbar


def _upd(m, v, j, h1, h2, i11, i12, i22, r1, r2):
    """Actualización de Kalman de un estado escalar con dos observaciones correlacionadas (S⁻¹ = [[i11, i12], [i12, i22]])."""
    kx = v[j] * (h1 * i11 + h2 * i12)
    ky = v[j] * (h1 * i12 + h2 * i22)
    m[j] += kx * r1 + ky * r2
    v[j] -= v[j] * (kx * h1 + ky * h2)


def _esperanza_suma(psi, s, mu, vmu, ma, mb, va, vb, sa, sb, vsa, vsb, a, b, t, tmu, now):
    k, se2 = psi.kappa[s], psi.sigma_eps ** 2

    def var_al(j, v0, tau):
        return v0 + (tau ** 2 * (now - t[j]) / ANIO_NS if t[j] is not None and now > t[j] else 0.0)
    vm = vmu[s] + (psi.tau_mu ** 2 * (now - tmu[s]) / ANIO_NS if tmu[s] is not None and now > tmu[s] else 0.0)
    tot = 0.0
    for x, y in ((a, b), (b, a)):
        e = mu[s] + k * (ma[x] - mb[y]) + sa[x][s] - sb[y][s]
        var = vm + k * k * (var_al(x, va[x], psi.tau_alpha) + var_al(y, vb[y], psi.tau_beta)) + vsa[x][s] + vsb[y][s] + se2
        tot += 1 / (1 + math.exp(-e / math.sqrt(1 + math.pi * var / 8)))
    return tot
