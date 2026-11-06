"""Pieza R (plan D.3): filtro de rating con superficie, fatiga y contextos; enlace EXACTO con el simulador.

    ρ_m = κ_s·(1 + Σγ_k z_k)·(θ_A − θ_B) + (d_{A,s} − d_{B,s}) − [φ1·(g1(F_A) − g1(F_B)) + φ2·(g2(F_A) − g2(F_B))]
    P_R(A gana) = M̄_f(expit(ℓ̄_s + ρ), expit(ℓ̄_s − ρ); Σ_ε + v·[[1,−1],[−1,1]]),   v = aᵀ V_A a + aᵀ V_B a

Orden: los partidos se recorren por corte; antes de cada uno se aplican TODOS los eventos con visible < corte (y
ninguno más), en bloques de igual visibilidad (simultáneos ⇒ independientes del orden de llegada). Solo actualizan
los completados (walkover y retirada no). Un formato o superficie desconocidos, equipos/JJOO y un jugador sin estado
ni ranking ⇒ no se pronostica (motivo contado) y su resultado no actualiza. Fatiga desconocida ⇒ el término se omite
(no se rellena con 0) y el partido se marca.
"""
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from . import estado as est
from .fatiga import fatiga, termino
from .prior_ranking import estado_inicial
from .superficie import multiplicador
from .tabla import convolucionar

HISTORIAL_MAX = 12


@dataclass
class SalidaFiltro:
    pi: np.ndarray          # π(lado 1 gana); NaN si no se pronostica
    rho: np.ndarray
    var_rho: np.ndarray
    f1: np.ndarray          # fatiga (minutos ponderados); NaN si desconocida
    f2: np.ndarray
    fat_desc: np.ndarray
    prior1: np.ndarray      # el lado aún no tiene ningún resultado propio en el filtro (solo prior por ranking)
    prior2: np.ndarray
    motivo: np.ndarray      # None si se pronostica
    ult_vis: np.ndarray     # máximo visible aplicado antes de pronosticar (prueba de no-fuga)
    n_actualizaciones: int
    n_bloques_multiples: int


def filtrar(d, psi, tablas: dict, ganadores=None) -> SalidaFiltro:
    """`tablas[(fmt, sup)]` = Tabla. `ganadores` sustituye a la columna de eventos (solo para pruebas de fuga)."""
    p, e = d.p, d.e
    n_p, n_j = len(p), d.n_jugadores
    corte = p.corte_ns.tolist(); j1, j2 = p.j1.tolist(), p.j2.tolist()
    sup, fmt, pre = p.sup.tolist(), p.fmt.tolist(), p.pregs.tolist()
    rk1, rk2, claves = p.rank1.tolist(), p.rank2.tolist(), p.partido_key.tolist()
    vetado = (p.excluir_motivo.notna() | p.equipos).tolist()
    e_vis, e_j1, e_j2 = e.vis_ns.tolist(), e.j1.tolist(), e.j2.tolist()
    e_gan = (e.gan if ganadores is None else ganadores).tolist()
    e_min1, e_min2, e_walk = e.min1.tolist(), e.min2.tolist(), e.walk.tolist()
    e_act, e_pidx, n_e = e.actualiza.tolist(), e.pidx.tolist(), len(e)
    m, v, t, nupd = [None] * n_j, [None] * n_j, [0] * n_j, [0] * n_j
    hist = [[] for _ in range(n_j)]
    k_m, c_m = [None] * n_p, [0.0] * n_p
    out = {c: np.full(n_p, np.nan) for c in ("pi", "rho", "var_rho", "f1", "f2")}
    fat_desc, pr1, pr2 = np.zeros(n_p, bool), np.zeros(n_p, bool), np.zeros(n_p, bool)
    motivo, ult = np.full(n_p, None, dtype=object), np.full(n_p, np.iinfo(np.int64).min, dtype=np.int64)
    cuenta = {"act": 0, "mult": 0}
    niv = p.nivel.tolist() if "nivel" in p else [0] * n_p
    s2_gen = psi.sigma_r ** 2
    s2_ch = s2_gen if psi.sigma_r_challenger is None else psi.sigma_r_challenger ** 2
    conv = {}

    def tabla_de(f, s, nivel):
        """Enlace con σ_R² (parche G-calibración); con σ_R = 0 es la tabla original, sin tocar."""
        base, s2 = tablas[(f, s)], (s2_ch if nivel else s2_gen)
        if s2 <= 0.0:
            return base
        if (id(base), s2) not in conv:
            conv[(id(base), s2)] = convolucionar(base, s2)
        return conv[(id(base), s2)]

    def bloque(i0, i1):
        terms = defaultdict(list)
        for i in range(i0, i1):
            vis = e_vis[i]
            for j, mins in ((e_j1[i], e_min1[i]), (e_j2[i], e_min2[i])):
                hist[j].append((vis, mins, e_walk[i]))
                del hist[j][:-HISTORIAL_MAX]
            q = e_pidx[i]
            if not e_act[i] or q < 0 or k_m[q] is None or e_gan[i] not in (1, 2):
                continue
            a, b, s, k = e_j1[i], e_j2[i], sup[q], k_m[q]
            for j in (a, b):
                est.propagar(v[j], vis - t[j], psi); t[j] = vis
            rho = k * (m[a][0] - m[b][0]) + m[a][s + 1] - m[b][s + 1] - c_m[q]
            tab = tabla_de(fmt[q], s, niv[q])
            if e_gan[i] == 1:
                _, l1, l2 = tab.log_m(rho); g, h = l1, -l2
            else:
                _, l1, l2 = tab.log_m(-rho); g, h = -l1, -l2
            h = max(h, 0.0)
            qa, qb = est.var_dir(v[a], 0, psi, k, s), est.var_dir(v[b], 0, psi, k, s)
            terms[a].append((claves[q], 1, k, s, g / (1 + h * qb), h / (1 + h * qb)))
            terms[b].append((claves[q], -1, k, s, g / (1 + h * qa), h / (1 + h * qa)))
        for j, lst in terms.items():
            if len(lst) == 1:
                est.actualizar_uno(m[j], v[j], *lst[0][1:])
            else:
                est.actualizar_varios(m[j], v[j], [x[1:] for x in sorted(lst)]); cuenta["mult"] += 1
            nupd[j] += 1; cuenta["act"] += 1

    ie = 0
    for i in range(n_p):
        c = corte[i]
        while ie < n_e and e_vis[ie] < c:
            je = ie + 1
            while je < n_e and e_vis[je] == e_vis[ie]:
                je += 1
            bloque(ie, je); ie = je
        if ie:
            ult[i] = e_vis[ie - 1]
        a, b, s, f = j1[i], j2[i], sup[i], fmt[i]
        if vetado[i]:
            motivo[i] = "excluido_o_equipos"; continue
        if s < 0:
            motivo[i] = "superficie_desconocida"; continue
        if f < 0:
            motivo[i] = "formato_desconocido"; continue
        if (m[a] is None and estado_inicial(rk1[i], psi) is None) or (m[b] is None and estado_inicial(rk2[i], psi) is None):
            motivo[i] = "sin_historia_ni_ranking"; continue
        for j, rk in ((a, rk1[i]), (b, rk2[i])):
            if m[j] is None:
                m[j], v[j] = estado_inicial(rk, psi); t[j] = c
        pr1[i], pr2[i] = nupd[a] == 0, nupd[b] == 0
        k = multiplicador(psi.kappa, s, psi.gamma, (pre[i], 0.0, 0.0))
        fa, fb = fatiga(hist[a], c, psi.lam), fatiga(hist[b], c, psi.lam)
        ft = termino(fa, fb, psi.phi, psi.f90)
        fat_desc[i] = ft is None
        out["f1"][i] = np.nan if fa is None else fa
        out["f2"][i] = np.nan if fb is None else fb
        rho = k * (m[a][0] - m[b][0]) + m[a][s + 1] - m[b][s + 1] - (ft or 0.0)
        var = est.var_dir(v[a], c - t[a], psi, k, s) + est.var_dir(v[b], c - t[b], psi, k, s)
        k_m[i], c_m[i] = k, (ft or 0.0)
        out["pi"][i], out["rho"][i], out["var_rho"][i] = tabla_de(f, s, niv[i]).prob(rho, var), rho, var
    return SalidaFiltro(out["pi"], out["rho"], out["var_rho"], out["f1"], out["f2"], fat_desc, pr1, pr2, motivo, ult,
                        cuenta["act"], cuenta["mult"])
