"""Filtro de covarianza completa (variante del 6-nov): reducción al filtro anterior, propiedades de la covarianza,
no-fuga, simetría y reproducibilidad."""
import hashlib

import numpy as np
import pandas as pd

from tenis.modelo import datos as dm
from tenis.modelo.rating import filtrar
from tenis.modelo.rating_completo import filtrar_completo
from tenis.modelo.sintetico import mundo, psi_prueba, tablas_prueba
from test_modelo_propiedades import intercambiar


def preparar(p, e):
    return dm.preparar(p, e, "atp", 2030)


def test_cruzadas_forzadas_a_cero_reproducen_el_filtro_anterior():
    p, e = mundo(semilla=61, n_semanas=40)          # cada jugador juega una vez por bloque
    e["visible_resultado_utc"] = p.corte_utc + pd.Timedelta(days=6)    # fatiga no nula
    d = preparar(p, e)
    viejo = filtrar(d, psi_prueba(), tablas_prueba())
    cero = filtrar_completo(d, psi_prueba(), tablas_prueba(), cruzadas=False)
    np.testing.assert_allclose(cero.pi, viejo.pi, rtol=0, atol=1e-12, equal_nan=True)
    np.testing.assert_allclose(cero.var_rho, viejo.var_rho, rtol=0, atol=1e-12, equal_nan=True)


def test_covarianza_simetrica_semidefinida_y_con_cruces():
    p, e = mundo(semilla=62, n_semanas=40)
    s = filtrar_completo(preparar(p, e), psi_prueba(), tablas_prueba())
    st = s.estado
    act = np.flatnonzero(st.jugador_de >= 0)
    c = st.c[np.ix_(act, act)]
    assert np.max(np.abs(c - c.T)) < 1e-14
    assert np.linalg.eigvalsh(c).min() > -1e-12
    fuera = c[~np.eye(len(act), dtype=bool)]
    assert np.abs(fuera).max() > 1e-6                      # la covarianza cruzada existe y se usa
    viejo = filtrar(preparar(p, e), psi_prueba(), tablas_prueba())
    ok = np.isfinite(s.pi)
    assert np.any(np.abs(s.var_rho[ok] - viejo.var_rho[ok]) > 1e-6)


def test_la_actualizacion_reduce_la_varianza_del_diferencial():
    p, e = mundo(semilla=63, n_semanas=3)
    d = preparar(p, e)
    s = filtrar_completo(d, psi_prueba(), tablas_prueba())
    st = s.estado
    a, b = int(d.p.j1.iloc[0]), int(d.p.j2.iloc[0])
    ahora = int(st.t[[a, b]].max())
    antes = st.var_diferencial(a, b, 1.0, 2, ahora)
    tab = tablas_prueba()[(0, 2)]
    _, l1, l2 = tab.log_m(st.rho(a, b, 1.0, 2))
    st.actualizar_bloque([(a, b, 1.0, 2, l1, -l2)])
    assert st.var_diferencial(a, b, 1.0, 2, ahora) < antes


def test_no_fuga_y_resultado_propio():
    p, e = mundo(semilla=64, n_semanas=30)
    d = preparar(p, e)
    base = filtrar_completo(d, psi_prueba(), tablas_prueba())
    ok = np.isfinite(base.pi)
    assert np.all(base.ult_vis[ok] < d.p.corte_ns.to_numpy()[ok])
    i = 40
    gan = d.e.gan.copy(); gan.iat[i] = 3 - gan.iat[i]
    s = filtrar_completo(d, psi_prueba(), tablas_prueba(), ganadores=gan)
    antes = d.p.corte_ns.to_numpy() <= d.e.vis_ns.iat[i]
    np.testing.assert_array_equal(s.pi[antes], base.pi[antes])
    assert np.any(s.pi[~antes & ok] != base.pi[~antes & ok])


def test_simetria_y_reproducibilidad():
    p, e = mundo(semilla=65, n_semanas=30)
    s = filtrar_completo(preparar(p, e), psi_prueba(), tablas_prueba())
    s2 = filtrar_completo(preparar(*intercambiar(p, e)), psi_prueba(), tablas_prueba())
    ok = np.isfinite(s.pi)
    np.testing.assert_allclose(s2.pi[ok], 1 - s.pi[ok], rtol=0, atol=1e-12)
    rng = np.random.default_rng(1)
    s3 = filtrar_completo(preparar(p.iloc[rng.permutation(len(p))], e.iloc[rng.permutation(len(e))]), psi_prueba(), tablas_prueba())
    h = lambda x: hashlib.sha256(np.nan_to_num(x.pi, nan=-1).tobytes()).hexdigest()
    assert h(s) == h(s3)


def test_ventana_de_activos_saca_y_devuelve_al_jugador():
    p, e = mundo(semilla=66, n_semanas=12)
    # un jugador desaparece 3 años y vuelve: sale de C y vuelve con su marginal (cruces a 0)
    j = p.jugador_1.iloc[0]
    tarde = (p.jugador_1 == j) | (p.jugador_2 == j)
    sem = p.partido_key.str[1:4].astype(int)
    mover = tarde & (sem >= 8)
    p.loc[mover, "corte_utc"] += pd.Timedelta(days=3 * 365)
    e.loc[mover.to_numpy(), "visible_resultado_utc"] += pd.Timedelta(days=3 * 365)
    s = filtrar_completo(preparar(p, e), psi_prueba(), tablas_prueba(), ventana_anios=1.0)
    assert np.isfinite(s.pi[np.isfinite(s.pi)]).all() and s.estado.v_fuera.max() > 0
