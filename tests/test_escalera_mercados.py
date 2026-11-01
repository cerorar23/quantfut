"""Córners, tarjetas y ambos anotan en la escalera: modelo, cuotas y liquidación."""
from datetime import datetime, timedelta, timezone

import pytest

from qf.ingest.estadisticas import arbitro
from qf.model import estadisticas_mercado as em
from qf.publish import escalera_datos as ed
from qf.publish.alta_prob import Candidato

T0 = datetime(2024, 8, 1, tzinfo=timezone.utc)


def _liga(acc, n_jornadas=40, extra=None):
    """Seis equipos; 'A' saca siempre 7 córners en casa y 6 fuera, el resto 4."""
    equipos = list("ABCDEF")
    t = T0
    for j in range(n_jornadas):
        for i in range(0, 6, 2):
            l, v = equipos[(i + j) % 6], equipos[(i + 1 + j) % 6]
            acc.agregar(t, l, v, 7 if l == "A" else 4, 6 if v == "A" else 4, extra)
        t += timedelta(days=4)
    return t


def test_el_equipo_que_saca_mas_corners_sube_la_media_y_se_encoge_a_la_liga():
    acc = em.Acumulador(prior=6.0, media_vida=365.0)
    t = _liga(acc)
    con_a = sum(acc.lambdas(t, "A", "B"))
    sin_a = sum(acc.lambdas(t, "C", "B"))
    assert con_a > sin_a
    fuerte = em.Acumulador(prior=200.0, media_vida=365.0)
    _liga(fuerte)
    # Con mucho encogimiento, A se parece más a la media de la liga.
    assert sum(fuerte.lambdas(t, "A", "B")) < con_a


def test_sin_partidos_suficientes_no_hay_probabilidad():
    acc = em.Acumulador()
    acc.agregar(T0, "A", "B", 5, 4)
    assert acc.lambdas(T0, "A", "B") is None


def test_preguntar_no_mira_partidos_que_aun_no_se_anadieron():
    acc = em.Acumulador(prior=6.0, media_vida=365.0)
    t = _liga(acc)
    antes = acc.lambdas(t, "A", "B")
    acc.agregar(t, "A", "B", 20, 20)
    assert acc.lambdas(t, "A", "B") != antes             # solo cambia al añadirlo


def test_arbitro_tarjetero_sube_las_tarjetas():
    acc = em.Acumulador(usar_arbitro=True, prior=6.0, media_vida=365.0)
    t = _liga(acc, extra="J Normal")
    for _ in range(15):
        acc.agregar(t, "C", "D", 7, 7, "M Duro")          # 14 frente a ~8 de media
        t += timedelta(days=1)
    assert sum(acc.lambdas(t, "E", "F", "M Duro")) > sum(acc.lambdas(t, "E", "F", "J Normal"))


def test_probabilidades_de_linea_suman_uno_y_solo_lineas_medias():
    for phi in (1.0, 1.2):
        pr = em.prob_total(9.8, phi, 9.5)
        assert pr["over"] + pr["under"] == pytest.approx(1.0)
    assert em.prob_total(9.8, 1.2, 7.5)["over"] > em.prob_total(9.8, 1.2, 10.5)["over"]
    with pytest.raises(ValueError):
        em.prob_total(9.8, 1.2, 9.0)


def test_nombre_del_arbitro_igual_en_las_dos_fuentes():
    assert arbitro("Michael Oliver, England") == arbitro("M Oliver") == "M Oliver"



def test_mejor_cuota_de_la_lista_para_cada_linea():
    t = datetime(2026, 10, 8, 7, tzinfo=timezone.utc)
    filas = [{"bookmaker": "betano", "market": "corners", "selection": "over", "line": 8.5,
              "price": 1.33, "provider_updated_at": t},
             {"bookmaker": "onexbet", "market": "corners", "selection": "over", "line": 8.5,
              "price": 1.36, "provider_updated_at": t},
             {"bookmaker": "casa_ajena", "market": "corners", "selection": "over", "line": 8.5,
              "price": 1.50, "provider_updated_at": t},
             {"bookmaker": "betano", "market": "corners", "selection": "over", "line": 9.5,
              "price": 1.60, "provider_updated_at": t}]
    price, book, _ = ed._ref_casa(filas, Candidato("corners", "over", 8.5, 0.8))
    assert (price, book) == (1.36, "1xbet")


def _cuota(book, market, selection, line, price):
    return {"bookmaker": book, "market": market, "selection": selection, "line": line,
            "price": price, "provider_updated_at": datetime(2026, 10, 8, 21, tzinfo=timezone.utc)}


def test_probabilidad_prudente_se_queda_con_la_menor():
    filas = [_cuota("betano", "cards", "under", 6.5, 1.35),
             _cuota("betano", "cards", "over", 6.5, 3.05)]
    c = Candidato("cards", "under", 6.5, 0.82)
    pm = ed.prob_mercado(filas, c)
    assert 0.68 < pm < 0.71                                  # casa sin margen
    assert ed.prudente(c, filas).prob == pytest.approx(pm)
    # Si el modelo es el más prudente, manda el modelo.
    assert ed.prudente(Candidato("cards", "under", 6.5, 0.60), filas).prob == 0.60


def test_pinnacle_manda_sobre_las_casas_y_sin_dos_lados_no_entra():
    filas = [_cuota("betano", "corners", "over", 7.5, 1.50),
             _cuota("betano", "corners", "under", 7.5, 2.50),
             _cuota("pinnacle", "corners", "over", 7.5, 1.47),
             _cuota("pinnacle", "corners", "under", 7.5, 2.52),
             _cuota("onexbet", "corners", "over", 8.5, 1.80)]
    sola_pinnacle = ed.prob_mercado([f for f in filas if f["bookmaker"] == "pinnacle"],
                                    Candidato("corners", "over", 7.5, 0.9))
    assert ed.prob_mercado(filas, Candidato("corners", "over", 7.5, 0.9)) == sola_pinnacle
    assert ed.prudente(Candidato("corners", "over", 8.5, 0.9), filas) is None


def _fila(market, selection, line, **kw):
    base = {"status": "finished", "kickoff_utc": datetime(2026, 10, 9, 18, tzinfo=timezone.utc),
            "home_goals": 2, "away_goals": 1, "home_corners": 6, "away_corners": 4,
            "home_yellow": 2, "away_yellow": 1, "home_red": 1, "away_red": 0,
            "market": market, "selection": selection, "line": line}
    return {**base, **kw}


def test_liquidacion_de_corners_tarjetas_y_ambos_anotan():
    ahora = datetime(2026, 10, 10, tzinfo=timezone.utc)
    assert ed.resultado(_fila("corners", "over", 8.5), ahora) == ("win", 2, 1, 10)
    assert ed.resultado(_fila("corners", "under", 9.5), ahora)[0] == "loss"
    # Tarjetas: 2 + 1 amarillas + 1 roja = 4, una por tarjeta.
    assert ed.resultado(_fila("cards", "under", 4.5), ahora) == ("win", 2, 1, 4)
    assert ed.resultado(_fila("btts", "yes", None), ahora) == ("win", 2, 1, None)
    assert ed.resultado(_fila("btts", "no", None), ahora)[0] == "loss"


def test_sin_estadisticas_se_espera_y_luego_es_nulo():
    fila = _fila("corners", "over", 8.5, home_corners=None)
    assert ed.resultado(fila, datetime(2026, 10, 10, tzinfo=timezone.utc)) is None
    assert ed.resultado(fila, datetime(2026, 10, 13, tzinfo=timezone.utc)) == ("void", None, None, None)


def test_textos_en_la_web():
    assert ed.texto("corners", "over", 8.5, "A", "B") == "Más de 8,5 córners"
    assert ed.texto("btts", "no", None, "A", "B") == "No marcan los dos"
    assert ed.texto("h2h", "home", None, "Dortmund", "Werder") == "Gana Dortmund"


def test_corners_de_cada_equipo_modelo_y_liquidacion():
    # El local con 7 córners esperados frente al visitante con 3.
    assert em.prob("corners_home", (7.0, 3.0), "over", 3.5) > em.prob("corners_away", (7.0, 3.0), "over", 3.5)
    ahora = datetime(2026, 10, 10, tzinfo=timezone.utc)
    assert ed.resultado(_fila("corners_home", "over", 3.5), ahora) == ("win", 2, 1, 6)
    assert ed.resultado(_fila("corners_away", "over", 4.5), ahora) == ("loss", 2, 1, 4)
    assert ed.texto("corners_away", "under", 7.5, "A", "Betis") == "Menos de 7,5 córners de Betis"
