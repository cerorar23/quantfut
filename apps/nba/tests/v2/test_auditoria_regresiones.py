"""Regresiones de la auditoría del VPS del 4-nov: probabilidades, tiempo y conservación de masa."""
from datetime import date, datetime, UTC
import hashlib

import numpy as np
import pytest

from nba.api.app import prob_mas_de
from nba.contratos.validar import ContratoIncumplido, validar_jugador
from nba.v2 import mercados, plantilla, props, pit
from nba.v2.nucleo import Marcador


def test_push_es_devolucion_y_no_media_victoria():
    pmf = np.array([[.05, .80, .15, 0., 0., 0.]])
    assert props.prob_mas_de(pmf, np.array([1.]))[0] == pytest.approx(.75)
    m = Marcador(np.array([[102., 100.]] * 15 + [[101., 100.]] * 80 + [[99., 100.]] * 5))
    assert mercados.handicap(m, -1.) == pytest.approx(.75)


def test_cdf_degenerada_no_convierte_todo_push_en_995_por_ciento():
    p, _ = prob_mas_de([5.] * 199, 5.)
    assert p == 0.


def test_capacidad_individual_ademas_de_suma_de_minutos():
    candidatos = {j: (40. if j == 0 else 5., .85) for j in range(8)}
    m = plantilla.minutos_esperados(candidatos)
    assert sum(m.values()) == pytest.approx(240.)
    assert max(m.values()) <= 48.
    assert plantilla.minutos_esperados({1: (30., 1.), 2: (20., 1.)}) == {}


def test_conservar_la_cola_para_estrella_de_35_puntos():
    pmf = props.pmf_mezcla_adaptativa(np.array([1.]), np.full((1, 25), 35.), .22715, 70)[0]
    assert len(pmf) > 71 and pmf.sum() == pytest.approx(1., abs=1e-9)
    assert np.dot(np.arange(len(pmf)), pmf) == pytest.approx(35., abs=1e-5)
    assert pmf[71:].sum() == pytest.approx(.0414609479987, abs=1e-8)


def test_contrato_rechaza_resumen_que_contradice_la_pmf():
    malo = dict(pmf=[1., 0., 0., 0., 0., 0.], media=999., p10=3, p50=4, p90=5,
                p_juega=.8, minutos_esperados=30.)
    with pytest.raises(ContratoIncumplido):
        validar_jugador(malo)


def test_huella_combinada_depende_de_ambas_entradas_y_su_orden():
    a, b, c = 'a' * 64, 'b' * 64, 'c' * 64
    assert pit.combinar_huellas(a, b) != pit.combinar_huellas(a, c)
    assert pit.combinar_huellas(a, b) != pit.combinar_huellas(b, a)
    assert len(pit.combinar_huellas(a, b)) == 64


def test_bootstrap_respeta_unidad_independiente():
    from nba.v2.evaluacion import ic_diferencia
    p = np.repeat([.2, .8] * 10, 50)
    media, lo, hi = ic_diferencia(p, np.full(len(p), .5), np.zeros(len(p)),
                                 n=1000, semilla=11, grupos=np.repeat(np.arange(20), 50))
    assert media == pytest.approx(.09) and lo < 0 < hi


def test_minutos_del_join_no_pueden_ignorar_el_corte():
    from nba.v2.plantilla_pit import Q_ULTIMO_EQUIPO
    assert 'dm.recibido_en <= %(corte)s' in Q_ULTIMO_EQUIPO


def test_reconstruido_no_elude_recepcion_en_modo_operativo():
    assert "d.pit = 'reconstruido' OR" not in pit.HISTORIA


def test_calibracion_no_mezcla_versiones_ni_duplica_el_mismo_partido():
    from nba.api.app import calibracion_por_version
    filas = [(1, 7, 'vieja', .9, 100., 90.), (2, 7, 'vieja', .8, 100., 90.),
             (3, 8, 'vieja', .6, 80., 90.)]
    r = calibracion_por_version(filas, 'nueva')
    assert r['prospectivo']['con_resultado'] == 0 and not r['prospectivo']['calibracion_certificada']
    assert r['por_version']['vieja']['con_resultado'] == 2
    assert r['por_version']['vieja']['brier_ganador'] == pytest.approx((.2 ** 2 + .6 ** 2) / 2)
    assert r['por_version']['vieja']['logloss_ganador'] > 0


def test_void_push_y_dato_desconocido_son_estados_distintos():
    from nba.v2.contratos_apuesta import liquidar
    assert liquidar(0., 6., 'over', 1.9, jugo=False) == {'estado': 'void', 'beneficio': 0.}
    assert liquidar(6., 6., 'over', 1.9) == {'estado': 'push', 'beneficio': 0.}
    assert liquidar(None, 6., 'over', 1.9, jugo=None) == {'estado': 'pendiente', 'beneficio': None}


def test_api_conserva_las_masas_y_el_contrato_siempre_devuelto():
    from nba.api.app import contrato_linea
    r = contrato_linea({'masas': {'margen': {'soporte': [0, 1, 2], 'pmf': [.05, .8, .15]}}}, 'margen', 1.)
    assert r['p_mas'] == pytest.approx(.75) and r['p_push'] == pytest.approx(.8) and not r['aproximada']
    r = contrato_linea({'masas': {'margen': {'soporte': [1], 'pmf': [1.]}}}, 'margen', 1.)
    assert r['p_mas'] is None and r['p_menos'] is None and r['p_push'] == 1.
