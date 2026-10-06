"""El criterio de la prueba histórica, fijado antes de ver los resultados."""
import numpy as np
import pandas as pd

from qf.eval import alta_prob_calibracion as cal


def _f(mercado, prob, aciertos, n):
    won = np.zeros(n, dtype=bool)
    won[:aciertos] = True
    return pd.DataFrame({"mercado": mercado, "prob": prob, "won": won,
                         "elegido": True, "week": "2024-01-01/2024-01-07"})


def test_pasa_si_cumple_lo_prometido():
    r = cal.evaluar(_f("totals over 1.5", 0.86, 172, 200))
    assert r["totals over 1.5"]["pasa"] is True


def test_no_pasa_si_un_tramo_queda_dos_errores_por_debajo():
    # Prometido 86 %, real 76 %: SE = sqrt(.86*.14/200) = 2,45 pts.
    r = cal.evaluar(_f("totals under 3.5", 0.86, 152, 200))
    assert r["totals under 3.5"]["pasa"] is False


def test_tramo_pequeno_no_decide_pero_el_conjunto_si():
    # n = 60 < 100: el tramo no decide; el déficit total (−5 pts) sí.
    r = cal.evaluar(_f("h2h", 0.85, 48, 60))
    assert r["h2h"]["tramos"][0]["decide"] is False
    assert r["h2h"]["pasa"] is False


def test_deficit_de_un_punto_es_el_limite():
    r = cal.evaluar(_f("double_chance", 0.87, 860, 1000))   # −1,0 pts exacto
    assert r["double_chance"]["diferencia_pts"] == -1.0
    assert r["double_chance"]["pasa"] is True
