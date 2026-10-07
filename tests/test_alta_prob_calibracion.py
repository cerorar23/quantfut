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


def test_criterio_a_falla_aunque_criterio_b_pase():
    # Un mercado con dos tramos: el 80-85 falla (a), el 85-90 pasa, pero
    # global pasa (b). Por tanto pasa = False (porque (a) falló).
    # Tramo 1: n=200, prometido 82%, real 70% (70 < 82-2*SE=76.6%) → falla (a)
    # Tramo 2: n=2000, prometido 87%, real 90% (90 > 87-2*SE=82.2%) → pasa (a)
    # Global: prometido 86.55%, real 88.18%, dif +1.63 → pasa (b)
    f1 = _f("totals under 5.5", 0.82, 140, 200)
    f2 = _f("totals under 5.5", 0.87, 1800, 2000)
    f = pd.concat([f1, f2], ignore_index=True)
    r = cal.evaluar(f)
    assert r["totals under 5.5"]["pasa"] is False
    assert r["totals under 5.5"]["diferencia_pts"] > -1.0  # Criterio (b) pasa
    assert r["totals under 5.5"]["tramos"][0]["decide"] is True
    assert r["totals under 5.5"]["tramos"][0]["pasa"] is False  # Tramo (a) falla


def _raw(*partidos):
    """football-data sintético: (local, visitante, PSH, PSD, PSA, P>2.5, P<2.5, goles)."""
    return pd.DataFrame([
        {"Date": "10/08/2024", "HomeTeam": h, "AwayTeam": a, "FTHG": hg, "FTAG": ag,
         "league_id": "gb.premier_league", "season": "2024-25",
         "PSH": psh, "PSD": psd, "PSA": psa, "P>2.5": po, "P<2.5": pu}
        for h, a, psh, psd, psa, po, pu, hg, ag in partidos])


def test_regla_completa_mide_la_regla_desplegada_no_las_lineas_excluidas():
    # Partido igualado de ~2,6 goles esperados: el 1X2, la doble oportunidad,
    # "más de 1,5", "menos de 3,5" y "marca un equipo" quedan bajo el 80 %; solo
    # "menos de 4,5" (~87 %) está en rango. Se MIDE (aparece en `filas`), pero
    # no está habilitado: no puede ser el elegido. Con la regla anterior (elegir
    # entre todas las líneas medidas) sí lo habría sido.
    raw = _raw(("A", "B", 2.60, 3.60, 2.90, 1.95, 1.95, 1, 0))
    f = cal.filas(raw, cal.RHO_POR_DEFECTO)
    assert list(f["mercado"]) == ["totals under 4.5"]
    assert ("under", 4.5) not in cal.ap.MERCADOS_GOLES_HABILITADOS
    assert not f["elegido"].any()
    # `regla_completa` se calcula sobre los elegidos: aquí no hay ninguno.
    assert f[f["elegido"]].empty


def test_regla_completa_elige_entre_los_habilitados():
    # Favorito claro: la doble 1X (~0,88), "marca el local" (~0,87) y "menos de
    # 4,5" (~0,85) entran en rango. Con la regla anterior el elegido era "menos
    # de 4,5" (la menor probabilidad); ahora es el de menor probabilidad ENTRE
    # LOS HABILITADOS ("marca el local"), y la línea excluida sigue medida.
    raw = _raw(("A", "B", 1.45, 4.40, 7.50, 1.80, 2.05, 2, 0))
    f = cal.filas(raw, cal.RHO_POR_DEFECTO)
    assert set(f["mercado"]) == {"double_chance", "totals under 4.5", "team_totals_home"}
    excluida = f[f["mercado"] == "totals under 4.5"].iloc[0]
    habilitados = f[f["mercado"] != "totals under 4.5"]
    assert excluida["prob"] < habilitados["prob"].min()      # con la regla vieja ganaba ella
    elegidos = f[f["elegido"]]
    assert list(elegidos["mercado"]) == ["team_totals_home"]
    assert elegidos.iloc[0]["prob"] == habilitados["prob"].min()
