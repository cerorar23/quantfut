"""Pieza R con FILTRO COMPLETO (variante aprobada el 6-nov): θ conjunta con covarianza cruzada entre jugadores activos.

Mismas reglas que `rating.filtrar` (orden por visible < corte, bloques simultáneos, solo completados actualizan,
omisiones, fatiga, prior por ranking, enlace exacto con la tabla), pero:
- la predicción usa Var(θ_A − θ_B) con su covarianza cruzada (C_AB) sumada a la Σ del enlace;
- cada bloque es una actualización de Laplace CONJUNTA de rango K (Woodbury) sobre todo el estado.
`rating.filtrar` (campo medio) se conserva sin tocar como alternativa. `cruzadas=False` fuerza C diagonal.
"""
from collections import defaultdict

import numpy as np

from .covarianza import EstadoConjunto
from .estado import ANIO_NS
from .fatiga import DIA_NS, fatiga, termino
from .prior_ranking import estado_inicial
from .rating import HISTORIAL_MAX, SalidaFiltro
from .superficie import multiplicador

VENTANA_ACTIVOS_ANIOS = 2.0
BARRIDO_NS = 30 * DIA_NS


def filtrar_completo(d, psi, tablas: dict, cruzadas: bool = True, ventana_anios: float = VENTANA_ACTIVOS_ANIOS,
                     ganadores=None) -> SalidaFiltro:
    if psi.sigma_r != 0.0 or psi.sigma_r_challenger:
        raise ValueError("el filtro completo se ajusta sin σ_R (el parche σ_R fue rechazado por la MV)")
    p, e = d.p, d.e
    n_p = len(p)
    corte, j1, j2 = p.corte_ns.tolist(), p.j1.tolist(), p.j2.tolist()
    sup, fmt, pre = p.sup.tolist(), p.fmt.tolist(), p.pregs.tolist()
    rk1, rk2 = p.rank1.tolist(), p.rank2.tolist()
    vetado = (p.excluir_motivo.notna() | p.equipos).tolist()
    e_vis, e_j1, e_j2 = e.vis_ns.tolist(), e.j1.tolist(), e.j2.tolist()
    e_gan = (e.gan if ganadores is None else ganadores).tolist()
    e_min1, e_min2, e_walk = e.min1.tolist(), e.min2.tolist(), e.walk.tolist()
    e_act, e_pidx, n_e = e.actualiza.tolist(), e.pidx.tolist(), len(e)
    st = EstadoConjunto(d.n_jugadores, psi, cruzadas)
    nupd, hist = np.zeros(d.n_jugadores, int), [[] for _ in range(d.n_jugadores)]
    k_m, c_m = [None] * n_p, [0.0] * n_p
    out = {c: np.full(n_p, np.nan) for c in ("pi", "rho", "var_rho", "f1", "f2")}
    fat_desc, pr1, pr2 = np.zeros(n_p, bool), np.zeros(n_p, bool), np.zeros(n_p, bool)
    motivo, ult = np.full(n_p, None, dtype=object), np.full(n_p, np.iinfo(np.int64).min, dtype=np.int64)
    ventana_ns, cuenta = int(ventana_anios * ANIO_NS), {"act": 0, "mult": 0, "barrido": 0}

    def bloque(i0, i1):
        ev = []
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
                st.asegurar_activo(j); st.propagar(j, vis)
            ev.append((a, b, k, s, q, i))
        if not ev:
            return
        terms = []
        for a, b, k, s, q, i in ev:                         # g, h con el estado PREVIO al bloque
            rho = st.rho(a, b, k, s) - c_m[q]
            tab = tablas[(fmt[q], s)]
            if e_gan[i] == 1:
                _, l1, l2 = tab.log_m(rho); g, h = l1, -l2
            else:
                _, l1, l2 = tab.log_m(-rho); g, h = -l1, -l2
            terms.append((a, b, k, s, g, max(h, 0.0)))
        st.actualizar_bloque(terms)
        cuenta["mult"] += len(terms) > 1
        for a, b, *_ in terms:
            nupd[a] += 1; nupd[b] += 1; cuenta["act"] += 2

    ie, proximo_barrido = 0, (corte[0] if n_p else 0)
    for i in range(n_p):
        c = corte[i]
        while ie < n_e and e_vis[ie] < c:
            je = ie + 1
            while je < n_e and e_vis[je] == e_vis[ie]:
                je += 1
            bloque(ie, je); ie = je
        if ie:
            ult[i] = e_vis[ie - 1]
        if c >= proximo_barrido:
            st.barrer(c, ventana_ns); proximo_barrido = c + BARRIDO_NS; cuenta["barrido"] += 1
        a, b, s, f = j1[i], j2[i], sup[i], fmt[i]
        if vetado[i]:
            motivo[i] = "excluido_o_equipos"; continue
        if s < 0:
            motivo[i] = "superficie_desconocida"; continue
        if f < 0:
            motivo[i] = "formato_desconocido"; continue
        ini = {}
        for j, rk in ((a, rk1[i]), (b, rk2[i])):
            if not st.existe[j]:
                ini[j] = estado_inicial(rk, psi)
        if any(v is None for v in ini.values()):
            motivo[i] = "sin_historia_ni_ranking"; continue
        for j, (m0, v0) in ini.items():
            st.alta(j, m0[0], v0[0][0], np.array(v0)[1:, 1:], c)
        for j in (a, b):
            st.asegurar_activo(j)
        pr1[i], pr2[i] = nupd[a] == 0, nupd[b] == 0
        k = multiplicador(psi.kappa, s, psi.gamma, (pre[i], 0.0, 0.0))
        fa, fb = fatiga(hist[a], c, psi.lam), fatiga(hist[b], c, psi.lam)
        ft = termino(fa, fb, psi.phi, psi.f90)
        fat_desc[i] = ft is None
        out["f1"][i] = np.nan if fa is None else fa
        out["f2"][i] = np.nan if fb is None else fb
        rho = st.rho(a, b, k, s) - (ft or 0.0)
        var = st.var_diferencial(a, b, k, s, c)
        k_m[i], c_m[i] = k, (ft or 0.0)
        out["pi"][i], out["rho"][i], out["var_rho"][i] = tablas[(f, s)].prob(rho, var, psi.c_inf), rho, var
    sal = SalidaFiltro(out["pi"], out["rho"], out["var_rho"], out["f1"], out["f2"], fat_desc, pr1, pr2, motivo, ult,
                       cuenta["act"], cuenta["mult"])
    sal.estado = st
    return sal
