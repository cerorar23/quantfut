"""Referencia independiente del filtro R (apps/tenis/ops/referencia_rating.py): física del partido, enlace M̄_f,
propiedades del filtro y casos absurdos. No depende de los ficheros del otro agente ni de la base."""
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ops"))
import referencia_rating as rr  # noqa: E402

FORMATOS = [(3, "tiebreak_7"), (3, "tiebreak_10"), (3, "supertiebreak_10"), (3, "ventaja"),
            (5, "tiebreak_7"), (5, "tiebreak_10"), (5, "ventaja")]
PARES = [(0.6, 0.55), (0.66, 0.60), (0.5, 0.5), (0.72, 0.58), (0.35, 0.45), (0.9, 0.2), (0.51, 0.69)]


# ------------------------------------------------------------------ física del partido
@pytest.mark.parametrize("mejor_de,dec", FORMATOS)
def test_cerrada_igual_a_punto_a_punto(mejor_de, dec):
    for pa, pb in PARES:
        rap = float(rr.p_partido(pa, pb, mejor_de, dec))
        lento = rr.p_partido_lento(pa, pb, mejor_de, dec)
        assert abs(rap - lento) < 1e-12, (pa, pb, rap, lento)


def test_juego_conocido():
    assert float(rr.p_juego(0.5)) == pytest.approx(0.5, abs=1e-15)
    assert float(rr.p_juego(0.6)) == pytest.approx(0.735729, abs=1e-6)        # valor clásico
    assert float(rr.p_juego(1.0)) == 1.0 and float(rr.p_juego(0.0)) == 0.0


@pytest.mark.parametrize("mejor_de,dec", FORMATOS)
def test_simetria_y_monotonia(mejor_de, dec):
    assert float(rr.p_partido(0.6, 0.6, mejor_de, dec)) == pytest.approx(0.5, abs=1e-14)
    for pa, pb in PARES:
        assert float(rr.p_partido(pa, pb, mejor_de, dec)) + float(rr.p_partido(pb, pa, mejor_de, dec)) \
            == pytest.approx(1.0, abs=1e-13)
    xs = np.linspace(0.3, 0.9, 61)
    v = rr.p_partido(xs, np.full_like(xs, 0.6), mejor_de, dec)
    assert np.all(np.diff(v) > 0)


def test_mejor_de_5_amplifica():
    assert float(rr.p_partido(0.64, 0.60, 5, "tiebreak_7")) > float(rr.p_partido(0.64, 0.60, 3, "tiebreak_7")) > 0.5


def test_formato_absurdo():
    with pytest.raises(ValueError):
        rr.p_partido(0.6, 0.6, 4, "tiebreak_7")
    with pytest.raises(ValueError):
        rr.p_partido(0.6, 0.6, 3, "desconocido")


# ------------------------------------------------------------------ enlace M̄_f
def test_mbar_sin_sigma_es_el_partido():
    ell = rr.math.log(0.62 / 0.38)
    for rho in (-0.3, 0.0, 0.2):
        pa, pb = rr.expit(ell + rho), rr.expit(ell - rho)
        assert float(rr.m_barra(ell, [rho], np.zeros((2, 2)), 3, "tiebreak_7", 11)[0]) == \
            pytest.approx(float(rr.p_partido(pa, pb, 3, "tiebreak_7")), abs=1e-14)


def test_mbar_valores_del_plan():
    """§D.4: p 0,66/0,60 a 3 sets 0,775 sin forma del día y 0,694 con σ_ε 0,22, ρ_ε −0,45; δ* = 0,0311 con
    Ŝ = 1,25 da 0,700 (p_A 0,6561, p_B 0,5939). El plan redondea a 3 decimales (y δ* a 4)."""
    S = rr.sigma_eps(0.22, -0.45)

    def mb(pa, pb, sig):
        la, lb = math.log(pa / (1 - pa)), math.log(pb / (1 - pb))
        ell, rho = (la + lb) / 2, (la - lb) / 2
        return float(rr.m_barra(ell, [rho], sig, 3, "tiebreak_7", 40)[0])
    assert mb(0.66, 0.60, np.zeros((2, 2))) == pytest.approx(0.775, abs=6e-4)
    assert mb(0.66, 0.60, S) == pytest.approx(0.694, abs=6e-4)
    assert mb(0.6561, 0.5939, S) == pytest.approx(0.700, abs=3e-4)


def test_mbar_simetrica_y_cuadratura():
    """Con Σ_ε solo, q = 11 se queda a ~6e-7 (q = 20 a 1e-11); con incertidumbre de parámetros grande (J V Jᵀ) y mejor de 5, q = 11 se
    equivoca ~5e-4 (integrando muy empinado): por eso la predicción de referencia usa q_pred = 60."""
    Se = rr.sigma_eps(0.22, -0.45)
    S = Se + 0.05 * np.array([[1, -1], [-1, 1]])
    for dec in ("tiebreak_7", "ventaja"):
        a = rr.m_barra(0.6, [0.15, -0.15], S, 5, dec, 11)
        assert a[0] + a[1] == pytest.approx(1.0, abs=1e-13)
        exacto = rr.m_barra(0.6, [0.15], Se, 3, dec, 60)[0]
        assert 1e-8 < abs(rr.m_barra(0.6, [0.15], Se, 3, dec, 11)[0] - exacto) < 5e-6     # q = 11: ~6e-7–2e-6
        assert abs(rr.m_barra(0.6, [0.15], Se, 3, dec, 20)[0] - exacto) < 1e-8
        assert abs(rr.m_barra(0.6, [0.15], S, 5, dec, 40)[0] - rr.m_barra(0.6, [0.15], S, 5, dec, 60)[0]) < 1e-7
        assert abs(a[0] - rr.m_barra(0.6, [0.15], S, 5, dec, 60)[0]) > 1e-4


@pytest.mark.parametrize("mejor_de,dec", FORMATOS)
def test_coincide_con_la_api_publica_del_simulador(mejor_de, dec):
    """Comprobación cruzada (solo API pública): sin Σ a 1e-13; con Σ, q alto en ambos, a 1e-12. El simulador
    llama `super_tiebreak_10` a lo que la exportación llama `supertiebreak_10` (hallazgo del informe)."""
    from tenis.simulador import Formato, Incertidumbre, prob_ganar
    fmt = Formato(mejor_de, dec.replace("supertiebreak", "super_tiebreak"))
    for pa, pb in PARES[:5]:
        assert prob_ganar(pa, pb, fmt, Incertidumbre(0.0, 0.0)) == \
            pytest.approx(float(rr.p_partido(pa, pb, mejor_de, dec)), abs=1e-13)
        la, lb = math.log(pa / (1 - pa)), math.log(pb / (1 - pb))
        cov = 0.03 * np.array([[1.0, -1.0], [-1.0, 1.0]])
        S = rr.sigma_eps(0.22, -0.45) + cov
        ref = float(rr.m_barra((la + lb) / 2, [(la - lb) / 2], S, mejor_de, dec, 60)[0])
        sim = prob_ganar(pa, pb, fmt, Incertidumbre(0.22, -0.45, tuple(map(tuple, cov))), q=40)
        assert sim == pytest.approx(ref, abs=1e-9)       # q = 40 del simulador aún no está en 1e-12 a 5 sets


def test_mbar_sigma_singular():
    """σ_ε = 0 con incertidumbre de parámetros: Σ singular (solo dirección (1, −1)); eigh lo admite."""
    S = 0.04 * np.array([[1.0, -1.0], [-1.0, 1.0]])
    v = float(rr.m_barra(0.6, [0.1], S, 3, "tiebreak_7", 30)[0])
    assert 0.5 < v < float(rr.m_barra(0.6, [0.1], np.zeros((2, 2)), 3, "tiebreak_7", 30)[0])


# ------------------------------------------------------------------ filtro
def _p(sup="Hard", corte=1000.0, t_ref=None, pa=None, pb=None, indoor=None, mejor_de=3, dec="tiebreak_7", ctx=None):
    return rr.Partido(superficie=sup, indoor=indoor, mejor_de=mejor_de, decisivo=dec, contextos=ctx or {},
                      corte=corte, t_ref=corte if t_ref is None else t_ref, puntos_a=pa, puntos_b=pb)


def test_hiper_absurdos():
    hp = rr.hiper_demo()
    with pytest.raises(ValueError):
        replace(hp, phi=(-0.01, 0.0)).validar()
    with pytest.raises(ValueError):
        replace(hp, kappa={**hp.kappa, "Hard": 1.1}).validar()
    with pytest.raises(NotImplementedError):
        replace(hp, omega_juegos=0.3).validar()


def test_prior_por_ranking_y_sin_ranking():
    hp = rr.hiper_demo()
    f = rr.Filtro(hp)
    alto = f.predecir(_p(pa=5000, pb=100), "a", "b")
    assert alto["prior_a"] and alto["prior_b"] and alto["pi"] > 0.5
    igual = f.predecir(_p(pa=800, pb=800), "a", "b")
    assert igual["pi"] == pytest.approx(0.5, abs=1e-12)
    m, P = hp.prior(None)
    assert m[0] == hp.theta_sin_ranking and P[0, 0] == hp.prior_var
    assert not f.m                              # predecir no crea estado


def test_simetria_del_filtro():
    hp = rr.hiper_demo()
    f = rr.Filtro(hp)
    for k in range(30):
        f.actualizar(_p(sup=rr.SUPERFICIES[k % 4], corte=float(k), pa=900, pb=600), "a", "b", gana_a=k % 3 != 0)
    for sup in rr.SUPERFICIES:
        x = f.predecir(_p(sup=sup, corte=40.0), "a", "b")["pi"]
        y = f.predecir(_p(sup=sup, corte=40.0), "b", "a")["pi"]
        assert x + y == pytest.approx(1.0, abs=1e-12)


def test_actualizacion_va_en_la_direccion_correcta_y_reduce_varianza():
    hp = rr.hiper_demo()
    f = rr.Filtro(hp)
    p = _p(sup="Clay", pa=1000, pb=1000)
    m0, P0 = hp.prior(1000)
    f.actualizar(p, "a", "b", gana_a=True)
    assert f.m["a"][0] > m0[0] and f.m["b"][0] < m0[0]
    k = 1 + rr.SUPERFICIES.index("Clay")
    assert f.m["a"][k] > 0 and f.m["b"][k] < 0
    assert f.m["a"][1 + rr.SUPERFICIES.index("Grass")] > 0     # Ω con correlación 0,5 propaga
    assert f.P["a"][0, 0] < P0[0, 0]
    assert f.m["a"][0] - m0[0] == pytest.approx(m0[0] - f.m["b"][0], abs=1e-12)   # simetría A/B


def test_laplace_es_la_formula_del_plan():
    """V⁺ = (V⁻¹ + H)⁻¹ y m⁺ = m + V⁺∇ℓ(m), con H = −ℓ''·g gᵀ; comprobado con inversas explícitas."""
    hp = rr.hiper_demo()
    f = rr.Filtro(hp)
    p = _p(sup="Grass", pa=2000, pb=700, indoor=None)
    r = f._rho_y_var(p, "a", "b")
    h = 1e-4
    M = rr.m_barra(hp.ell["Grass"], [r["rho"] - h, r["rho"], r["rho"] + h], rr.sigma_eps(hp.s_eps, hp.r_eps),
                   3, "tiebreak_7", hp.q)
    L = np.log1p(-M)                           # gana B
    d1, d2 = (L[2] - L[0]) / (2 * h), (L[2] - 2 * L[1] + L[0]) / h**2
    e1, e2 = f.derivadas(p, r["rho"], False)
    assert abs(e1 - d1) < 1e-7 and abs(e2 - d2) < 1e-6
    d1, d2 = e1, e2
    g, V = r["g"], r["V"]
    Vp = np.linalg.inv(np.linalg.inv(V) - d2 * np.outer(g, g))
    mp = r["m"] + Vp @ g * d1
    f.actualizar(p, "a", "b", gana_a=False)
    np.testing.assert_allclose(f.m["a"], mp[:6], atol=1e-12)
    np.testing.assert_allclose(f.P["b"], Vp[6:, 6:], atol=1e-12)


def test_derivadas_por_diferencias_coinciden_con_paso_menor():
    hp = rr.hiper_demo()
    f1, f2 = rr.Filtro(hp), rr.Filtro(replace(hp, h_dif=1e-3))
    for f in (f1, f2):
        f.actualizar(_p(pa=1500, pb=500), "a", "b", gana_a=False)
    assert abs(f1.m["a"][0] - f2.m["a"][0]) < 1e-10
    assert abs(f1.P["a"][0, 0] - f2.P["a"][0, 0]) < 1e-10


def test_inactividad_aumenta_varianza():
    hp = rr.hiper_demo()
    f = rr.Filtro(hp)
    f.actualizar(_p(corte=0.0, pa=1000, pb=1000), "a", "b", True)
    _, P59, _ = f.estado_en("a", 59.0, None)
    _, P61, _ = f.estado_en("a", 61.0, None)
    _, P3a, _ = f.estado_en("a", 3 * 365.0, None)
    salto = P61[0, 0] - P59[0, 0] - hp.tau_theta**2 * 2
    assert salto == pytest.approx(hp.inact_var, abs=1e-15)
    assert P3a[0, 0] > P61[0, 0]
    assert P3a[1, 1] > P59[1, 1]


def test_fatiga_cero_sin_efecto_y_phi_cero_sin_efecto():
    hp = rr.hiper_demo()
    base = rr.Filtro(hp).predecir(_p(corte=100.0, pa=900, pb=900), "a", "b")["pi"]
    f = rr.Filtro(hp)
    f.registrar_minutos("a", vis=99.5, fin=99.4, minutos=0.0, jugado=True)       # jugó 0 minutos
    assert f.predecir(_p(corte=100.0, pa=900, pb=900), "a", "b")["pi"] == pytest.approx(base, abs=1e-15)
    f.registrar_minutos("a", vis=99.5, fin=99.4, minutos=240.0, jugado=True)
    cansado = f.predecir(_p(corte=100.0, pa=900, pb=900), "a", "b")
    assert cansado["pi"] < base and cansado["F_a"] == pytest.approx(240 * hp.lam**0.6)
    f0 = rr.Filtro(replace(hp, phi=(0.0, 0.0)))
    f0.registrar_minutos("a", vis=99.5, fin=99.4, minutos=240.0, jugado=True)
    assert f0.predecir(_p(corte=100.0, pa=900, pb=900), "a", "b")["pi"] == pytest.approx(base, abs=1e-15)


def test_fatiga_ventana_y_visibilidad():
    hp = rr.hiper_demo()
    h = []
    h.append((95.0, 95.0, 100.0, True))              # 5 días antes: fuera de 96 h
    h.append((99.0, 96.1, 100.0, True))              # 3,9 días: dentro
    h.append((100.0, 99.0, 100.0, True))             # visible justo en el corte: NO visible (c > vis)
    h.append((99.5, 99.0, None, True))               # minutos desconocidos
    h.append((99.5, 99.0, None, False))              # walkover/cancelado sin minutos: no marca
    F, desc = rr.fatiga(h, corte=100.0, t_ref=100.0, hp=hp)
    assert F == pytest.approx(100.0 * hp.lam**3.9) and desc
    g1, g2 = rr.g_fatiga(hp.F90 + 60.0, hp)
    assert g2 == pytest.approx(1.0) and g1 == pytest.approx((hp.F90 + 60) / 60)


def test_superficie_multiplicador_e_iota():
    hp = replace(rr.hiper_demo(), kappa={"Clay": 0.5, "Grass": 2.0, "Hard": 1.0, "Indoor": 1.0}, zeta=2.0)
    g = rr.vector_g(_p(sup="Grass"), hp)
    assert g[0] == 2.0 and g[2] == 1.0 and g[5] == 0.0 and np.allclose(g[6:], -g[:6])
    g = rr.vector_g(_p(sup="Clay", indoor=True, ctx={"jjoo": True}), replace(hp, gamma={"jjoo": 0.1}))
    assert g[0] == pytest.approx(0.5 * 1.1) and g[1] == 1.0 and g[5] == 2.0
    assert rr.vector_g(_p(sup="Clay", indoor=None), hp)[5] == 0.0        # indoor desconocido ⇒ ι = 0


# ------------------------------------------------------------------ ejecución sobre una tabla sintética
def _tabla():
    t0 = pd.Timestamp("2020-01-06", tz="UTC")
    filas = []

    def fila(k, a, b, gan, estado="completado", dia=0, mins=90, sup="Hard", fmt="tiebreak_7", mejor_de=3,
             n1=30, n2=30, p1=1000.0, p2=1000.0, vis_h=30):
        corte = t0 + pd.Timedelta(days=dia)
        filas.append(dict(orden=0, partido_key=k, circuito="atp", jugador_1=a, jugador_2=b, superficie=sup,
                          indoor=None, mejor_de=mejor_de, formato_decisivo=fmt, estado=estado, ganador=gan,
                          minutos_1=None if mins is None else mins, minutos_2=None if mins is None else mins,
                          actualiza_rating=estado == "completado", inicio_utc=pd.NaT, corte_utc=corte,
                          visible_resultado_utc=corte + pd.Timedelta(hours=vis_h), semana_previa_gs=False,
                          por_equipos=False, jjoo=False, puntos_1=p1, puntos_2=p2, rank_1=1, rank_2=2,
                          n_prev_1=n1, n_prev_2=n2, excluir_motivo=None, marcas=None))
    fila("m1", 1, 2, 1, dia=0)
    fila("m2", 1, 3, None, estado="walkover", dia=1, mins=None)
    fila("m3", 1, 2, 2, estado="retirada", dia=2, mins=50)
    fila("m4", 1, 2, 1, dia=3)          # objetivo: ve m1 (vis día 1,25), m2 y m3 (vis día 3,25 > corte día 3: NO)
    fila("m5", 4, 5, 1, dia=3, n1=0, p1=None)                       # sin historia ni ranking
    fila("m6", 1, 2, 1, dia=4, fmt="desconocido")
    df = pd.DataFrame(filas).sort_values("visible_resultado_utc", kind="stable").reset_index(drop=True)
    df["orden"] = np.arange(1, len(df) + 1)
    df["n_prev_1"] = df["n_prev_1"].astype(int); df["n_prev_2"] = df["n_prev_2"].astype(int)
    return df


def test_ejecutar_respeta_visibilidad_y_no_actualiza_walkover_ni_retirada():
    hp = replace(rr.hiper_demo(), phi=(0.0, 0.0))
    df = _tabla()
    out = rr.ejecutar(df, {"atp": hp}, {"m1", "m4", "m5", "m6"}).set_index("partido_key")
    assert out.loc["m1", "pi_ref"] == pytest.approx(0.5, abs=1e-12)        # sin estado, mismos puntos
    # m4 solo ve m1 (m2 visible en el día 2,25 pero es walkover; m3 visible en el día 3,25 ≥ corte)
    f = rr.Filtro(hp)
    f.actualizar(rr._partido_de_fila(next(df[df.partido_key == "m1"].itertuples(index=False))), 1, 2, True)
    esperado = f.predecir(rr._partido_de_fila(next(df[df.partido_key == "m4"].itertuples(index=False))), 1, 2)
    assert out.loc["m4", "pi_ref"] == pytest.approx(esperado["pi"], abs=1e-15)
    assert out.loc["m5", "motivo"] == "jugador_sin_historia" and math.isnan(out.loc["m5", "pi_ref"])
    assert out.loc["m6", "motivo"] == "formato_desconocido"


def test_ejecutar_independiente_de_la_muestra():
    """Pronosticar más o menos partidos no cambia el estado del filtro (los priores temporales no se guardan)."""
    hp = rr.hiper_demo()
    df = _tabla()
    a = rr.ejecutar(df, {"atp": hp}, {"m4"}).set_index("partido_key")
    b = rr.ejecutar(df, {"atp": hp}, {"m1", "m4", "m5"}).set_index("partido_key")
    assert a.loc["m4", "pi_ref"] == b.loc["m4", "pi_ref"]
