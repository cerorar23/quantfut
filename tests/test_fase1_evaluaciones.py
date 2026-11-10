import numpy as np


def test_umbral_por_dias_endurece_al_inicio_y_nunca_baja_de_prob_min():
    from qf.eval.escalera_umbral_dias import umbral
    from qf.publish import escalera as es
    inicio = umbral(es.PROB_RETO, 1.0, 2, es.DIAS_MAX, 0.04, 0.0)
    final = umbral(es.PROB_RETO, 1.0, 2, 1, 0.04, 0.0)
    assert inicio > final
    assert umbral(es.PROB_RETO, 1.0, 2, 1, 0.0, 0.5) == es.PROB_MIN
