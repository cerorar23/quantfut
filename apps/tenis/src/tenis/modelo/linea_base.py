"""Línea base reimplementada sobre los MISMOS partidos y el MISMO protocolo (plan §I G-línea base; aud. §6.2).

Elo general y Elo+superficie con K = 24 (el de la línea base de la auditoría), inicio 1500, actualizados por BLOQUES
de visibilidad: antes de pronosticar un partido se aplican todos los resultados con visible < corte y ninguno más; los
de un mismo instante se calculan desde el estado previo al bloque. Solo actualizan los completados (como la pieza R).
Elo+superficie = logística de (Δgeneral + Δsuperficie)/800 (la mezcla 50/50 de la auditoría).
El Elo recalibrado es `recalibracion.por_temporada` sobre p_elo (temporadas previas desde 2012).
"""
from collections import defaultdict

import numpy as np

K_ELO = 24.0
# Proporción típica de juegos del ganador (6-4 6-4 = 0,60; 6-2 6-3 = 0,71): normaliza el peso para que K siga
# siendo «el de un partido medio» (T1, 2026-11-09; variante inspirada en el Weighted Elo de Angelini et al. 2022).
COMPARTE_GANADOR = 0.64


def elo(d, k: float = K_ELO, gamma: float = 0.0) -> dict:
    """`gamma` > 0 escala cada actualización por (juegos del ganador / juegos totales / 0,64)^gamma; exige
    `juegos_1` y `juegos_2` en `d.e`. Con gamma = 0 es exactamente el Elo de siempre."""
    p, e = d.p, d.e
    peso = [1.0] * len(e)
    if gamma:
        g1 = np.nan_to_num(e.juegos_1.to_numpy(float)); g2 = np.nan_to_num(e.juegos_2.to_numpy(float))
        tot = g1 + g2
        gan = np.where(e.gan.to_numpy() == 1, g1, g2)
        cuota = np.where(tot > 0, gan / np.maximum(tot, 1.0), COMPARTE_GANADOR)
        peso = ((np.clip(cuota, 0.5, 1.0) / COMPARTE_GANADOR) ** gamma).tolist()
    corte, j1, j2, sup = p.corte_ns.tolist(), p.j1.tolist(), p.j2.tolist(), p.sup.tolist()
    e_vis, e_j1, e_j2, e_gan = e.vis_ns.tolist(), e.j1.tolist(), e.j2.tolist(), e.gan.tolist()
    e_act, e_pidx = e.actualiza.tolist(), e.pidx.tolist()
    e_sup = [sup[q] if q >= 0 else -1 for q in e_pidx]
    gen, srf = defaultdict(lambda: 1500.0), defaultdict(lambda: 1500.0)
    p_gen, p_sup = np.full(len(p), np.nan), np.full(len(p), np.nan)
    ie, n_e = 0, len(e)
    for i in range(len(p)):
        while ie < n_e and e_vis[ie] < corte[i]:
            je = ie
            dg, ds = defaultdict(float), defaultdict(float)
            while je < n_e and e_vis[je] == e_vis[ie]:
                if e_act[je] and e_gan[je] in (1, 2):
                    w, l = (e_j1[je], e_j2[je]) if e_gan[je] == 1 else (e_j2[je], e_j1[je])
                    pw = 1 / (1 + 10 ** (-(gen[w] - gen[l]) / 400))
                    dg[w] += k * peso[je] * (1 - pw); dg[l] -= k * peso[je] * (1 - pw)
                    s = e_sup[je]
                    if s >= 0:
                        ps = 1 / (1 + 10 ** (-(srf[(w, s)] - srf[(l, s)]) / 400))
                        ds[(w, s)] += k * peso[je] * (1 - ps); ds[(l, s)] -= k * peso[je] * (1 - ps)
                je += 1
            for x, val in dg.items():
                gen[x] += val
            for x, val in ds.items():
                srf[x] += val
            ie = je
        a, b, s = j1[i], j2[i], sup[i]
        dif = gen[a] - gen[b]
        p_gen[i] = 1 / (1 + 10 ** (-dif / 400))
        if s >= 0:
            p_sup[i] = 1 / (1 + 10 ** (-(dif + srf[(a, s)] - srf[(b, s)]) / 800))
    return {"p_elo": p_gen, "p_elo_sup": p_sup}
