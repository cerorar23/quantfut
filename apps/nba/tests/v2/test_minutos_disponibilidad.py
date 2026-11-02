import numpy as np
import pytest

from nba.v2 import disponibilidad as disp
from nba.v2 import minutos
from nba.v2.distribucion import Distribucion


def test_distribucion_media_cuantiles_y_empates():
    d = Distribucion.de_muestras([10, 20, 30], [1, 1, 2])
    assert d.media() == pytest.approx(22.5) and d.cuantil(0.5) == 20 and d.cuantil(0.99) == 30 and d.cuantil(0.0) == 10
    assert d.prob_mas_de(20) == pytest.approx(0.5 + 0.5 * 0.25) and d.prob_menos_de(20) == pytest.approx(0.25 + 0.125)
    assert d.prob_mas_de(5) == 1 and d.prob_menos_de(5) == 0
    assert d.pinball(25, 0.5) == pytest.approx(0.5 * 5)                         # y por encima del cuantil
    with pytest.raises(ValueError):
        Distribucion.de_muestras([])


def test_mezcla_de_distribuciones_suma_uno():
    m = Distribucion.mezcla([(0.25, Distribucion.de_muestras([0.0])), (0.75, Distribucion.de_muestras([30.0, 34.0]))])
    assert m.pesos.sum() == pytest.approx(1) and m.media() == pytest.approx(0.75 * 32) and m.prob_mas_de(0) == pytest.approx(0.75 + 0.5 * 0.25)


def residuos_simples():
    return minutos.ajustar_residuos([(10.0, 10.0 + e) for e in np.linspace(-3, 3, 400)] +
                                    [(20.0, 20.0 + e) for e in np.linspace(-5, 5, 400)] +
                                    [(30.0, 30.0 + e) for e in np.linspace(-6, 6, 400)])


def test_punto_pesa_mas_lo_reciente_e_ignora_ceros_y_pocos_partidos():
    historial = [20.0] * 10 + [34.0] * 10
    assert np.mean(historial) < minutos.punto(historial) < 34.0
    assert minutos.punto([30.0] * 4) is None
    assert minutos.punto([None, 0, 0.0] + [25.0] * 5) == pytest.approx(25.0)
    s = sum(0.7 ** k for k in range(1, 20))                                       # 19 partidos de 10 min y el último de 40
    assert minutos.punto([10.0] * 30 + [40.0]) == pytest.approx((40 * 1 + 10 * s) / (1 + s))


def test_residuos_por_tramo_y_distribucion_condicionada():
    r = residuos_simples()
    assert minutos.tramo(10, r.cortes) == 0 and minutos.tramo(15, r.cortes) == 1 and minutos.tramo(30, r.cortes) == 2
    d = minutos.condicionada([30.0] * 8, r)
    assert d.media() == pytest.approx(30.0, abs=0.2)
    assert d.cuantil(0.1) == pytest.approx(30 - 4.8, abs=0.3) and d.cuantil(0.9) == pytest.approx(30 + 4.8, abs=0.3)
    chico = minutos.condicionada([8.0] * 8, r)
    assert chico.cuantil(0.9) - chico.cuantil(0.1) < d.cuantil(0.9) - d.cuantil(0.1)             # menos minutos, menos dispersión
    assert chico.valores.min() >= 0 and minutos.condicionada([30.0] * 3, r) is None
    with pytest.raises(ValueError):
        minutos.ajustar_residuos([])


def test_prediccion_con_masa_en_cero():
    r = residuos_simples()
    historial = [30.0, 32.0, 28.0, 31.0, 29.0, 33.0]
    p0 = minutos.prediccion(historial, 0.0, r)
    assert p0.media() == 0 and p0.valores.tolist() == [0.0]
    p1 = minutos.prediccion(historial, 1.0, r)
    assert p1.valores.min() > 20
    p = minutos.prediccion(historial, 0.5, r)
    assert p.prob_menos_de(1) == pytest.approx(0.5) and p.media() == pytest.approx(0.5 * minutos.condicionada(historial, r).media())


def test_media_ultimos_es_la_linea_base():
    assert minutos.media_ultimos([10, 20, 30, 40, 50, 60]) == pytest.approx(40.0)         # 20..60 → últimos 5
    assert minutos.media_ultimos([10, 20]) is None


def test_wilson_y_tabla_de_estados():
    lo, hi = disp.wilson(0, 100)
    assert lo == 0 and 0 < hi < 0.05
    assert disp.wilson(0, 0) == (0.0, 1.0)
    t = disp.tabla_estados([("Out", False)] * 90 + [("Out", True)] * 10 + [("Probable", True)] * 8 + [("Probable", False)] * 2)
    assert t["Out"]["n"] == 100 and t["Out"]["p"] == pytest.approx(0.10) and t["Probable"]["p"] == pytest.approx(0.8)
    assert t["Out"]["lo"] < 0.10 < t["Out"]["hi"]


def test_prob_juega_usa_la_tabla_y_el_valor_sin_parte():
    assert disp.prob_juega("Out") < disp.prob_juega("Questionable") < disp.prob_juega("Probable")
    assert disp.prob_juega(None) == disp.P_SIN_PARTE and disp.prob_juega("raro") == disp.P_SIN_PARTE
    assert disp.prob_juega("Out", {"Out": 0.3}) == 0.3


def test_escenarios_suman_uno_y_enumeran_los_mas_inciertos():
    e = disp.escenarios({1: 0.5, 2: 0.9, 3: 0.2, 4: 0.99, 5: 0.0})
    assert sum(x.prob for x in e) == pytest.approx(1) and len(e) == 8
    assert all(5 in x.ausentes for x in e)                                           # el 5 está fuera con certeza
    mejor = e[0]
    assert mejor.prob == pytest.approx(0.5 * 0.9 * 0.8)                              # 1 juega, 2 juega, 3 no juega
    assert disp.escenarios({1: 1.0, 2: 0.0}) == [disp.Escenario(1.0, frozenset({2}))]


def test_escenarios_no_inventan_incertidumbre():
    e = disp.escenarios({i: 1.0 for i in range(10)})
    assert len(e) == 1 and e[0].ausentes == frozenset() and e[0].prob == 1.0
