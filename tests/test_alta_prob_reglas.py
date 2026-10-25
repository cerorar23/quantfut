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


def test_menos_de_4_5_goles_excluido_por_decision_del_usuario():
    # 2026-10-06: el usuario lo excluye de la regla (se paga a 1,09-1,17).
    assert ("under", 4.5) not in ap.MERCADOS_GOLES_HABILITADOS
    # 2026-10-09: "más de 2,5" entra tras pasar la prueba de la ampliación.
    assert set(ap.MERCADOS_GOLES_HABILITADOS) == {("over", 1.5), ("under", 3.5), ("over", 2.5)}
    m = score_matrix(1.0, 0.8, -0.06)
    ajuste = ap.ajuste_goles(market_1x2(m), 2.5, totals_fair_over(m, 2.5), -0.06)
    assert all(c.line != 4.5 for c in ap.candidatos_goles(ajuste))


def test_marca_cada_equipo_desde_el_ajuste():
    m = score_matrix(1.6, 0.9, -0.06)
    aj = ap.ajuste_goles(market_1x2(m), 2.5, totals_fair_over(m, 2.5), -0.06)
    c = {x.market: x for x in ap.candidatos_equipo(aj)}
    assert set(c) == {"team_totals_home", "team_totals_away"}
    ma = score_matrix(aj["lambda"], aj["mu"], aj["rho"])
    assert c["team_totals_home"].prob == pytest.approx(1 - float(ma[0, :].sum()), abs=1e-12)
    assert c["team_totals_away"].prob == pytest.approx(1 - float(ma[:, 0].sum()), abs=1e-12)
    assert all(x.selection == "over" and x.line == 0.5 for x in c.values())
    assert ap.candidatos_equipo(None) == [] and ap.candidatos_equipo(aj, ()) == []


def test_desempate_con_goles_de_un_equipo():
    cands = [ap.Candidato("double_chance", "1X", None, 0.85),
             ap.Candidato("team_totals_home", "over", 0.5, 0.85),
             ap.Candidato("totals", "over", 1.5, 0.85)]
    assert ap.elegir(cands).market == "totals"
    assert ap.elegir([cands[0], cands[1]]).market == "team_totals_home"


def test_texto_marca_un_equipo():
    assert ap.texto("team_totals_home", "over", 0.5, "Cruzeiro", "Sao Paulo") == "Marca Cruzeiro"
    assert ap.texto("team_totals_away", "over", 0.5, "Cruzeiro", "Sao Paulo") == "Marca Sao Paulo"
    # Otra línea u otro lado no es «marca»: decirlo así cambiaba el pronóstico.
    assert ap.texto("team_totals_home", "over", 1.5, "Cruzeiro", "Sao Paulo") == "Más de 1,5 goles de Cruzeiro"
    assert ap.texto("team_totals_away", "under", 1.5, "Cruzeiro", "Sao Paulo") == "Menos de 1,5 goles de Sao Paulo"


def test_bloquear_el_grupo_team_totals_excluye_los_dos_lados():
    # `control` devuelve el grupo "team_totals"; `elegir` tiene que dejar fuera
    # tanto "marca el local" como "marca el visitante" y seguir con otro mercado.
    local = ap.Candidato("team_totals_home", "over", 0.5, 0.82)
    visitante = ap.Candidato("team_totals_away", "over", 0.5, 0.83)
    doble = ap.Candidato("double_chance", "1X", None, 0.90)
    assert ap.elegir([local, visitante, doble]) == local
    assert ap.elegir([local, visitante, doble], excluir={"team_totals"}) == doble
    assert ap.elegir([local, visitante], excluir={"team_totals"}) is None
    # El nombre exacto de un lado sigue valiendo, y no arrastra al otro.
    assert ap.elegir([local, visitante, doble], excluir={"team_totals_home"}) == visitante
