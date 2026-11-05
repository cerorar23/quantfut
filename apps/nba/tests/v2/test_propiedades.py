"""Propiedades matemáticas con entradas aleatorias (semilla fija): lo que debe cumplirse para CUALQUIER entrada válida, no solo para los ejemplos."""
from datetime import datetime, UTC

import numpy as np
import pytest

from nba.api.app import prob_mas_de as prob_cuantiles
from nba.contratos.validar import validar_equipo
from nba.v2 import mercados, minutos, nucleo, plantilla, props, recalibracion, referencia, sellado

RNG = np.random.default_rng(20261103)


def test_pmf_de_conteo_es_una_distribucion_valida_y_la_probabilidad_decrece_con_la_linea():
    for _ in range(150):
        tasa, alfa, techo = RNG.uniform(0, 2.0), RNG.uniform(0.001, 1.0), int(RNG.integers(20, 90))
        muestras = RNG.uniform(1, 48, size=(1, 7))
        pmf = props.pmf_mezcla_adaptativa(np.array([tasa]), muestras, alfa, techo)[0]
        assert (pmf >= 0).all() and pmf.sum() <= 1 + 1e-9 and np.isfinite(pmf).all()
        if tasa * 48 < techo / 3 and alfa <= 0.3:                         # soporte suficiente y sobredispersión real (≤ 0,23 medida): casi toda la masa dentro
            assert pmf.sum() > 0.999
        lineas = np.sort(RNG.uniform(-1, techo + 5, 6))
        p = props.prob_mas_de(np.repeat(pmf[None, :], 6, axis=0), lineas)
        assert (np.diff(p) <= 1e-12).all() and ((p >= 0.0) & (p <= 1.0)).all()


def test_quitar_margen_suma_uno_conserva_el_orden_y_no_da_cero_ni_uno():
    for _ in range(200):
        n = int(RNG.integers(2, 5))
        cuotas = RNG.uniform(1.02, 40, n)
        for metodo in referencia.METODOS:
            p = np.array(referencia.quitar_margen(list(cuotas), metodo))
            assert p.sum() == pytest.approx(1.0, abs=1e-9) and (p > 0).all() and (p < 1).all()
            assert (np.argsort(-p) == np.argsort(-1 / cuotas)).all() or np.allclose(np.sort(1 / cuotas)[::-1][:2], np.sort(1 / cuotas)[::-1][:2])


def test_simulacion_de_marcador_y_mercados_son_coherentes_para_cualquier_entrada():
    for i in range(40):
        mu_l, mu_v = RNG.uniform(70, 150), RNG.uniform(70, 150)
        sm, st = RNG.uniform(5, 25), RNG.uniform(8, 30)
        m = nucleo.simular(mu_l, mu_v, sm, st, n=20_000, semilla=i)
        assert np.isfinite(m.muestras).all() and (m.muestras >= 0).all() and (m.muestras[:, 0] != m.muestras[:, 1]).all()
        g = mercados.ganador(m)
        assert 0 <= g <= 1 and mercados.handicap(m, 0.0) == pytest.approx(g, abs=1e-9)
        lineas = np.sort(RNG.uniform(-15, 15, 5))
        h = [mercados.handicap(m, l) for l in lineas]
        assert (np.diff(h) >= -1e-12).all()                              # cubrir un hándicap más generoso nunca es menos probable
        t = [mercados.total(m, l) for l in np.sort(RNG.uniform(150, 280, 5))]
        assert (np.diff(t) <= 1e-12).all()
        assert sum(mercados.margen_de_victoria(m).values()) == pytest.approx(1.0)


def test_los_cuantiles_selados_siempre_cumplen_el_contrato_de_equipo():
    for i in range(15):
        mu_l, mu_v = RNG.uniform(85, 135), RNG.uniform(85, 135)
        m = nucleo.simular(mu_l, mu_v, RNG.uniform(10, 18), RNG.uniform(14, 24), n=20_000, semilla=i)
        niveles = [k / 200 for k in range(1, 200)]
        dist = {"p_local": mercados.ganador(m), "mu": [mu_l, mu_v], "paso_cuantil": 0.005, "margen": [float(m.margen().cuantil(q)) for q in niveles],
                "total": [float(m.total().cuantil(q)) for q in niveles], "puntos_local": [float(m.puntos("local").cuantil(q)) for q in niveles],
                "puntos_visitante": [float(m.puntos("visit").cuantil(q)) for q in niveles]}
        validar_equipo(dist)
        q = dist["margen"]
        pr = [prob_cuantiles(q, x)[0] for x in np.sort(RNG.uniform(q[0] - 3, q[-1] + 3, 8))]
        assert (np.diff(pr) <= 1e-12).all() and all(0 <= x <= 1 for x in pr)


def test_minutos_esperados_suman_240_o_son_vacios_y_las_muestras_de_minutos_quedan_en_rango():
    for _ in range(100):
        cand = {j: (RNG.uniform(1, 45), RNG.uniform(0, 1)) for j in range(int(RNG.integers(0, 16)))}
        e = plantilla.minutos_esperados(cand)
        assert (not e) or sum(e.values()) == pytest.approx(240.0)
    res = minutos.ajustar_residuos([(float(m), float(m + RNG.normal(0, 5))) for m in RNG.uniform(3, 40, 4000)])
    s = minutos.muestras_condicionadas(RNG.uniform(0, 60, 200), res, 25)
    assert ((s >= 1.0) & (s <= minutos.MAXIMO)).all()


def test_probabilidad_recalibrada_nunca_es_cero_ni_uno_y_el_hash_cambia_con_cualquier_campo():
    p = recalibracion.p_ganador(RNG.uniform(-80, 80, 500), RNG.uniform(5, 25))
    assert ((p > 0) & (p < 1)).all()
    corte = datetime(2026, 11, 3, 1, tzinfo=UTC)
    base = dict(partido_id=1, mercado="equipo", periodo=0, entidad_id=None, version_modelo="v", version_datos="d" * 64, objetivo_en=corte, sellado_en=corte,
                escenarios={"a": 1}, distribucion={"p": 0.5}, hash_previo="0" * 64)
    h0 = sellado.calcular_hash(**base)
    assert sellado.calcular_hash(**base) == h0
    for campo, nuevo in (("partido_id", 2), ("mercado", "x"), ("version_modelo", "w"), ("escenarios", {"a": 2}), ("distribucion", {"p": 0.6}), ("hash_previo", "1" * 64),
                         ("objetivo_en", datetime(2026, 11, 3, 2, tzinfo=UTC)), ("entidad_id", 5)):
        assert sellado.calcular_hash(**dict(base, **{campo: nuevo})) != h0, campo
