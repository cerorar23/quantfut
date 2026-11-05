import numpy as np
import pytest

from nba.v2 import mercados, nucleo
from nba.v2.nucleo import Parametros, Ratings


def test_ratings_neutros_dan_la_ventaja_local():
    r = Ratings()
    pl, pv = r.esperado("BOS", "NYK")
    assert pl - pv == pytest.approx(r.localia) and pl + pv == pytest.approx(r.liga)


def test_actualizar_premia_al_que_anota_mas_de_lo_esperado():
    r, p = Ratings(), Parametros()
    nucleo.actualizar(r, "BOS", "NYK", 130, 100, p)
    assert r.ataque["BOS"] > 0 and r.defensa["NYK"] > 0           # BOS ataca bien, NYK defiende mal
    assert r.ataque["NYK"] < 0 and r.defensa["BOS"] < 0
    pl, pv = r.esperado("BOS", "NYK")
    assert pl - pv > r.localia                                    # tras ganar por 30 se espera más margen
    assert r.partidos == 1


def test_los_ratings_convergen_a_la_diferencia_real_y_la_nueva_temporada_los_encoge():
    rng = np.random.default_rng(1)
    r, p = Ratings(liga=224.0, localia=2.6), Parametros()
    equipos = [f"T{i}" for i in range(8)]
    fuerza = dict(zip(equipos, rng.uniform(-6, 6, 8)))              # fuerza neta; mitad ataque, mitad defensa
    for _ in range(8000):
        a, b = rng.choice(equipos, 2, replace=False)
        # local anota 112 + 1,3 + o_a + d_b ; visitante 112 - 1,3 + o_b + d_a, con o = f/2 y d = -f/2
        mu_l = 112 + 1.3 + fuerza[a] / 2 - fuerza[b] / 2
        mu_v = 112 - 1.3 + fuerza[b] / 2 - fuerza[a] / 2
        nucleo.actualizar(r, a, b, rng.normal(mu_l, 11), rng.normal(mu_v, 11), p)
    real = []
    predicho = []
    for a in equipos:
        for b in equipos:
            if a != b:
                pl, pv = r.esperado(a, b)
                real.append(2.6 + fuerza[a] - fuerza[b])
                predicho.append(pl - pv)
    pendiente = np.polyfit(real, predicho, 1)[0]
    assert pendiente == pytest.approx(1.0, abs=0.2) and np.corrcoef(real, predicho)[0, 1] > 0.85
    antes = r.ataque["T0"]
    nucleo.nueva_temporada(r, p)
    assert r.ataque["T0"] == pytest.approx(antes * p.arrastre)


def test_simular_respeta_medias_y_nunca_empata():
    m = nucleo.simular(115.0, 110.0, 13.0, 18.0, n=40000, semilla=3)
    assert m.muestras.shape == (40000, 2) and (m.muestras[:, 0] != m.muestras[:, 1]).all()
    assert m.margen().media() == pytest.approx(5.0, abs=0.35) and m.total().media() == pytest.approx(225.0, abs=0.5)
    assert np.std(m.muestras[:, 0] - m.muestras[:, 1]) == pytest.approx(13.0, abs=0.5)
    otra = nucleo.simular(115.0, 110.0, 13.0, 18.0, n=40000, semilla=3)
    assert (m.muestras == otra.muestras).all()                                       # misma semilla, mismo resultado


def test_mercados_coherentes_con_un_solo_marcador():
    m = nucleo.simular(118.0, 108.0, 13.0, 18.0, n=60000, semilla=7)
    g = mercados.ganador(m)
    assert mercados.ganador(m, "visit") == pytest.approx(1 - g) and 0.7 < g < 0.85
    # monotonía: más difícil cubrir un hándicap mayor; más difícil superar un total mayor
    assert mercados.handicap(m, -3.5) > mercados.handicap(m, -6.5) > mercados.handicap(m, -9.5)
    assert mercados.total(m, 215.5) > mercados.total(m, 226.5) > mercados.total(m, 235.5)
    # el ganador equivale a cubrir un hándicap de 0; los lados suman 1
    assert mercados.handicap(m, 0.0) == pytest.approx(g, abs=0.01)
    assert mercados.handicap(m, -4.5, "local") + mercados.handicap(m, -4.5, "visit") == pytest.approx(1)
    assert mercados.total(m, 226.5, "over") + mercados.total(m, 226.5, "under") == pytest.approx(1)
    # cota de Fréchet: P(A y B) ≤ min(P(A), P(B)); aquí: ganar Y over ≤ ambos
    gana_y_over = float(np.mean((m.muestras[:, 0] > m.muestras[:, 1]) & (m.muestras.sum(axis=1) > 226.5)))
    assert gana_y_over <= min(g, mercados.total(m, 226.5)) + 1e-12


def test_total_de_equipo_y_margen_de_victoria():
    m = nucleo.simular(118.0, 108.0, 13.0, 18.0, n=60000, semilla=9)
    assert mercados.total_equipo(m, "local", 113.5) > 0.5                              # el local espera 118
    assert mercados.total_equipo(m, "local", 117.5) + mercados.total_equipo(m, "local", 117.5, "under") == pytest.approx(1)
    assert mercados.total_equipo(m, "local", 117.5) > mercados.total_equipo(m, "visit", 117.5)
    tramos = mercados.margen_de_victoria(m)
    assert set(tramos) == {"1-5", "6-10", "11-15", "16+"} and sum(tramos.values()) == pytest.approx(1)


def test_lineas_enteras_se_condicionan_a_no_push():
    m = nucleo.Marcador(np.array([[100.0, 90.0], [100.0, 90.0], [95.0, 90.0], [90.0, 100.0]]))   # márgenes 10, 10, 5, -10
    assert mercados.handicap(m, -10.0) == 0.0                        # cero victorias entre dos contratos con acción
    assert mercados.total(m, 190.0) == 0.0                           # tres pushes y una derrota


def test_ajuste_de_descanso_mueve_el_margen_sin_tocar_el_total():
    p = Parametros(efecto_b2b=2.5)
    assert nucleo.ajuste_descanso(1, 3, p) == -2.5            # el local juega en la noche siguiente
    assert nucleo.ajuste_descanso(3, 1, p) == 2.5
    assert nucleo.ajuste_descanso(1, 1, p) == 0.0 and nucleo.ajuste_descanso(2, 4, p) == 0.0
    r = Ratings()
    base_l, base_v = r.esperado("BOS", "NYK")
    pl, pv = r.esperado("BOS", "NYK", -2.5)
    assert (pl - pv) == pytest.approx((base_l - base_v) - 2.5) and (pl + pv) == pytest.approx(base_l + base_v)
