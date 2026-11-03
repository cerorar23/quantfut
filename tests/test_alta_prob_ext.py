"""Alta probabilidad ampliada 62-95 %: selección pura y corte de lote."""
from datetime import date

from qf.publish import alta_prob as ap
from qf.publish import hashchain


def _c(market, sel, prob, line=None):
    return ap.Candidato(market, sel, line, prob)


def test_elegir_ext_devuelve_todos_en_rango_de_mayor_a_menor_probabilidad():
    cands = [_c("h2h", "home", 0.61), _c("h2h", "away", 0.62), _c("double_chance", "1X", 0.80),
             _c("totals", "over", 0.951, 2.5), _c("totals", "under", 0.70, 3.5)]
    out = ap.elegir_ext(cands)
    assert [(c.market, c.prob) for c in out] == [("double_chance", 0.80), ("totals", 0.70),
                                                 ("h2h", 0.62)]


def test_elegir_ext_respeta_exclusion_por_grupo():
    cands = [_c("team_totals_home", "over", 0.75, 0.5), _c("h2h", "home", 0.70)]
    assert [c.market for c in ap.elegir_ext(cands, {"team_totals"})] == ["h2h"]


def test_listas_ext_solo_con_mercados_aprobados():
    assert ("under", 2.5) not in ap.GOLES_EXT
    assert ap.BTTS_EXT == ("yes",)
    assert all(m == "corners" for m, _, _ in ap.CORNERS_EXT)
    assert ap.PROB_MIN_EXT == 0.62


def test_corte_del_lote_ext():
    assert not hashchain.lote_lleva_alta_ext(date(2026, 10, 11))
    assert hashchain.lote_lleva_alta_ext(date(2026, 10, 12))


def test_ampliada_descarta_los_candidatos_sin_cuota():
    from datetime import datetime, timezone

    from qf.publish import alta_prob_ext as ae
    from qf.publish import picks as pk
    snap = pk.Snapshot("propline", datetime(2026, 10, 25, 8, tzinfo=timezone.utc),
                       {"pinnacle": {"home": 1.18, "draw": 7.5, "away": 15.0}})
    todos, _ = ae.candidatos(snap, [], None, [], set())
    assert {c.market for c in todos} >= {"h2h", "double_chance"}
    con, _ = ae.candidatos(snap, [], None, [], set(),
                           cuota=lambda c: (1.15, "bet365") if c.market == "h2h" else (None, None))
    assert con and all(c.market == "h2h" for c in con)
