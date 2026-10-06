"""Reglas de la línea de alta probabilidad, sin base de datos."""
import pytest

from qf.ingest import af_odds
from qf.model.pricing import market_1x2, score_matrix, totals_fair_over
from qf.publish import alta_prob as ap

P = {"home": 0.62, "draw": 0.24, "away": 0.14}


def test_doble_oportunidad_es_la_suma_exacta():
    d = {c.selection: c.prob for c in ap.candidatos_doble(P)}
    assert d == pytest.approx({"1X": 0.86, "X2": 0.38, "12": 0.76})
    assert all(c.market == "double_chance" for c in ap.candidatos_doble(P))


def test_elige_el_de_menor_probabilidad_dentro_del_rango():
    cands = [ap.Candidato("h2h", "home", None, 0.82),
             ap.Candidato("double_chance", "1X", None, 0.93),
             ap.Candidato("totals", "under", 4.5, 0.97)]
    assert ap.elegir(cands) == cands[0]


def test_nada_si_ninguno_entra():
    assert ap.elegir([ap.Candidato("h2h", "home", None, 0.79),
                      ap.Candidato("double_chance", "1X", None, 0.951)]) is None


def test_limites_incluidos():
    assert ap.elegir([ap.Candidato("h2h", "home", None, 0.80)]).prob == 0.80
    assert ap.elegir([ap.Candidato("double_chance", "1X", None, 0.95)]).prob == 0.95


def test_desempate_1x2_goles_doble():
    cands = [ap.Candidato("double_chance", "1X", None, 0.85),
             ap.Candidato("totals", "under", 3.5, 0.85),
             ap.Candidato("h2h", "home", None, 0.85)]
    assert ap.elegir(cands).market == "h2h"
    assert ap.elegir(cands[:2]).market == "totals"


def test_excluir_un_mercado_bloqueado():
    cands = [ap.Candidato("h2h", "home", None, 0.82),
             ap.Candidato("double_chance", "1X", None, 0.93)]
    assert ap.elegir(cands, excluir={"h2h"}).market == "double_chance"


def test_goles_desde_un_ajuste_al_mercado():
    m = score_matrix(1.7, 0.9, -0.06)
    p = market_1x2(m)
    ajuste = ap.ajuste_goles(p, 2.75, totals_fair_over(m, 2.75), -0.06)
    assert ajuste is not None and ajuste["linea"] == 2.75
    goles = {(c.selection, c.line): c.prob
             for c in ap.candidatos_goles(ajuste, ap.LINEAS_GOLES)}
    m_ajuste = score_matrix(ajuste["lambda"], ajuste["mu"], -0.06)
    assert goles[("over", 1.5)] == pytest.approx(float(m_ajuste.sum() - m_ajuste[0, 0] - m_ajuste[1, 0] - m_ajuste[0, 1]), abs=1e-9)


def test_sin_mercados_habilitados_no_hay_goles():
    m = score_matrix(1.7, 0.9, -0.06)
    ajuste = ap.ajuste_goles(market_1x2(m), 2.5, totals_fair_over(m, 2.5), -0.06)
    assert ap.candidatos_goles(ajuste, ()) == []
    assert ap.candidatos_goles(None, ap.LINEAS_GOLES) == []


def test_ajuste_incoherente_se_rechaza():
    # 1X2 equilibrado con un over 2,5 al 97 %: ninguna pareja de lambdas
    # reproduce las dos cosas a menos de 0,01.
    assert ap.ajuste_goles({"home": 0.4, "draw": 0.3, "away": 0.3}, 2.5, 0.97, -0.06) is None


@pytest.mark.parametrize("market,sel,line,esperado", [
    ("h2h", "home", None, "Gana Cruzeiro"),
    ("h2h", "away", None, "Gana Sao Paulo"),
    ("double_chance", "1X", None, "Cruzeiro o empate"),
    ("double_chance", "X2", None, "Sao Paulo o empate"),
    ("double_chance", "12", None, "Cruzeiro o Sao Paulo (sin empate)"),
    ("totals", "over", 1.5, "Más de 1,5 goles"),
    ("totals", "under", 4.5, "Menos de 4,5 goles"),
])
def test_texto(market, sel, line, esperado):
    assert ap.texto(market, sel, line, "Cruzeiro", "Sao Paulo") == esperado


def test_las_lineas_de_goles_se_guardan_tambien_de_las_casas_blandas():
    # `af_odds` solo guarda de las casas blandas las LINEAS_BLANDAS (de Pinnacle,
    # todas). Si se habilita una línea nueva aquí sin añadirla allí, el
    # pronóstico se elegiría sin cuota de referencia de las casas de los
    # suscriptores.
    lineas = {ln for _, ln in ap.LINEAS_GOLES}
    assert lineas <= set(af_odds.LINEAS_BLANDAS)
    assert {ln for _, ln in ap.MERCADOS_GOLES_HABILITADOS} <= set(af_odds.LINEAS_BLANDAS)
