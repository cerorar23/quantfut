"""PROPIEDADES del modelo: simetría de lados, monotonía, orden de llegada y resultado duplicado."""
import numpy as np
import pandas as pd

from tenis.modelo import datos as dm
from tenis.modelo import estado as est
from tenis.modelo.rating import filtrar
from tenis.modelo.sintetico import mundo, psi_prueba, tablas_prueba


def correr(p, e, psi=None):
    d = dm.preparar(p, e, "atp", 2030)
    return d, filtrar(d, psi or psi_prueba(), tablas_prueba())


def intercambiar(p, e):
    p2, e2 = p.copy(), e.copy()
    for a, b in (("jugador_1", "jugador_2"), ("rank_1", "rank_2"), ("n_prev_1", "n_prev_2")):
        p2[a], p2[b] = p[b], p[a]
    for a, b in (("jugador_1", "jugador_2"), ("minutos_1", "minutos_2")):
        e2[a], e2[b] = e[b], e[a]
    p2["y_ganador"], e2["ganador"] = 3 - p.y_ganador, 3 - e.ganador
    return p2, e2


def test_intercambiar_lados_da_la_probabilidad_complementaria():
    p, e = mundo(semilla=11, n_semanas=40)
    # fatiga no nula: resultados visibles 6 días después del corte (≈ 1 día antes del corte siguiente),
    # minutos distintos por lado y algunos faltantes (fatiga desconocida)
    e["visible_resultado_utc"] = p.corte_utc + pd.Timedelta(days=6)
    e["minutos_1"] = e.minutos_1 + np.arange(len(e)) % 37
    e.loc[e.index % 29 == 0, "minutos_2"] = np.nan
    _, s = correr(p, e)
    assert np.nanmax(s.f1) > 0 and s.fat_desc.any()
    _, s2 = correr(*intercambiar(p, e))
    ok = np.isfinite(s.pi)
    assert ok.sum() > 200
    np.testing.assert_allclose(s2.pi[ok], 1 - s.pi[ok], rtol=0, atol=1e-12)
    np.testing.assert_allclose(s2.rho[ok], -s.rho[ok], rtol=0, atol=1e-12)


def test_monotonia_del_enlace_y_de_la_fatiga():
    tab = tablas_prueba()[(0, 2)]
    rhos = np.linspace(-1.5, 1.5, 301)
    for v in (0.0, 0.02, 0.4):
        pis = np.array([tab.prob(r, v) for r in rhos])
        assert np.all(np.diff(pis) > 0)
    # más incertidumbre acerca π a 0,5 (Glicko)
    assert tab.prob(0.2, 0.0) > tab.prob(0.2, 0.05) > tab.prob(0.2, 0.3) > 0.5
    psi = psi_prueba()
    from tenis.modelo.fatiga import termino
    assert termino(300.0, 0.0, psi.phi, psi.f90) > termino(100.0, 0.0, psi.phi, psi.f90) > 0


def test_mejor_ranking_y_mas_victorias_suben_la_probabilidad():
    p, e = mundo(semilla=12)
    _, s = correr(p, e)
    d = dm.preparar(p, e, "atp", 2030)
    primera = d.p.temporada.notna() & (d.p.corte_ns == d.p.corte_ns.min())
    sub = d.p[primera]
    pi = s.pi[primera.to_numpy()]
    mejor = (sub.rank1 < sub.rank2).to_numpy()
    assert np.all(pi[mejor] > 0.5) and np.all(pi[~mejor] < 0.5)
    # un jugador que gana todo sube su θ
    m = [0.0] * 5
    v = [[0.04 if i == j else 0.0 for j in range(5)] for i in range(5)]
    tab = tablas_prueba()[(0, 2)]
    _, l1, l2 = tab.log_m(0.0)
    est.actualizar_uno(m, v, 1, 1.0, 2, l1, -l2)
    assert m[0] > 0 and m[3] > 0 and v[0][0] < 0.04


def test_orden_de_llegada_con_la_misma_visibilidad_no_cambia_nada():
    p, e = mundo(semilla=13, n_semanas=25)
    # el mismo jugador en dos partidos del mismo instante de visibilidad (bloque con dos términos)
    extra = e.iloc[[0]].copy()
    extra["partido_key"], extra["jugador_2"] = "Z_EXTRA", e.jugador_1.iloc[5]
    pe = p.iloc[[0]].copy()
    pe["partido_key"], pe["jugador_2"], pe["rank_2"] = "Z_EXTRA", e.jugador_1.iloc[5], p.rank_1.iloc[5]
    p, e = pd.concat([p, pe], ignore_index=True), pd.concat([e, extra], ignore_index=True)
    _, s = correr(p, e)
    rng = np.random.default_rng(0)
    _, s2 = correr(p.iloc[rng.permutation(len(p))], e.iloc[rng.permutation(len(e))])
    np.testing.assert_array_equal(s.pi, s2.pi)
    # renombrar las claves (cambia el desempate dentro del bloque) tampoco cambia el resultado
    ren = {k: f"R{len(k)}{k[::-1]}" for k in p.partido_key}
    p3, e3 = p.assign(partido_key=p.partido_key.map(ren)), e.assign(partido_key=e.partido_key.map(ren))
    d3, s3 = correr(p3, e3)
    d, _ = correr(p, e)
    pos = pd.Series(np.arange(len(d3.p)), index=d3.p.partido_key)
    idx = pos[d.p.partido_key.map(ren)].to_numpy()
    np.testing.assert_allclose(s3.pi[idx], s.pi, rtol=0, atol=1e-12, equal_nan=True)
    assert s.n_bloques_multiples >= 1


def test_el_mismo_resultado_dos_veces_se_aplica_una_vez():
    p, e = mundo(semilla=14)
    _, s = correr(p, e)
    _, s2 = correr(p, pd.concat([e, e.iloc[:10]], ignore_index=True))
    np.testing.assert_array_equal(s.pi, s2.pi)
