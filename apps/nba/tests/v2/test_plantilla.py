import numpy as np
import pytest

from nba.v2 import plantilla
from nba.v2.plantilla import Impacto, PartidoFila


def _rotacion(rng, ids):
    """Cinco titulares con 30-40 minutos y el resto repartido para sumar 240."""
    n = len(ids)
    pesos = rng.dirichlet(np.ones(n) * 0.6)
    return {j: float(m) for j, m in zip(ids, 240 * pesos)}


def test_minutos_esperados_suman_240_y_reparten_lo_del_ausente():
    candidatos = {1: (34.0, 1.0), 2: (30.0, 1.0), 3: (28.0, 0.0), 4: (20.0, 0.5)}
    e = plantilla.minutos_esperados(candidatos)
    assert sum(e.values()) == pytest.approx(240.0)
    assert 3 not in e                                              # ausente seguro: sin minutos
    assert e[1] > e[2] > e[4] > 0
    assert plantilla.minutos_esperados({1: (30.0, 0.0)}) == {}


def test_ridge_recupera_el_impacto_de_los_jugadores():
    rng = np.random.default_rng(0)
    equipos = {t: list(range(t * 10, t * 10 + 10)) for t in range(10)}
    beta = {j: rng.normal(0, 3) for ids in equipos.values() for j in ids}
    filas = []
    for d in range(1500):
        a, b = rng.choice(10, 2, replace=False)
        local, visit = _rotacion(rng, equipos[a]), _rotacion(rng, equipos[b])
        margen = (2.5 + sum(beta[j] * m for j, m in local.items()) / 48 - sum(beta[j] * m for j, m in visit.items()) / 48
                  + rng.normal(0, 12))
        filas.append(PartidoFila(d, margen, 224 + rng.normal(0, 18), local, visit))
    imp = plantilla.ajustar(filas, lam_margen=20.0, lam_total=20.0, vida_media_dias=1e9)
    comunes = sorted(beta)
    r = np.corrcoef([beta[j] for j in comunes], [imp.beta[j] for j in comunes])[0, 1]
    assert r > 0.85 and imp.c_margen == pytest.approx(2.5, abs=1.0)
    # predicción lineal: sin jugadores solo queda el intercepto
    assert imp.margen({}, {}) == pytest.approx(imp.c_margen)


def test_solo_usa_partidos_anteriores_al_corte_y_el_decaimiento_pesa_lo_reciente():
    local, visit = {1: 240.0}, {2: 240.0}
    antiguos = [PartidoFila(d, 10.0, 220.0, local, visit) for d in range(100)]
    recientes = [PartidoFila(200 + d, -10.0, 220.0, local, visit) for d in range(100)]
    todos = antiguos + recientes
    sin_corte = plantilla.ajustar(todos, 1.0, 1.0, vida_media_dias=30.0)
    con_corte = plantilla.ajustar(todos, 1.0, 1.0, vida_media_dias=30.0, dia_corte=100)
    assert con_corte.margen(local, visit) == pytest.approx(10.0, abs=0.5)         # los recientes no se ven
    assert sin_corte.margen(local, visit) < 0                                      # lo reciente manda
    assert plantilla.ajustar([], 1.0, 1.0, 30.0) == Impacto()
