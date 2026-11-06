import math

import pytest
from datetime import datetime, timedelta, timezone

from qf.config import settings
from qf.model.devig import consensus_devig
from qf.publish import parley_ext as ext
from qf.publish import parley_v2 as v2

NOW = datetime(2026, 11, 6, 9, 35, tzinfo=timezone.utc)
RECIBIDA = NOW - timedelta(minutes=20)


def mercado(key, salidas):
    return {"key": key, "outcomes": salidas}


def h2h(local, visit, pl, pv, **extra):
    return mercado("h2h", [dict(name=local, price=pl, point=None, **extra),
                           dict(name=visit, price=pv, point=None, **extra)])


def casa(key, *mercados):
    return {"key": key, "markets": list(mercados)}


def evento(i, inicio=None, sport="tennis", books=None, recibida=RECIBIDA):
    return {"id": i, "sport_key": sport, "commence_time": (inicio or NOW + timedelta(hours=5)).isoformat(),
            "home_team": f"L{i}", "away_team": f"V{i}", "_received_at": recibida.isoformat(),
            "bookmakers": books or []}


def ganador(i, pin=(1.50, 2.70), blanda=(1.55, 2.60), **kw):
    return evento(i, books=[casa("pinnacle", h2h(f"L{i}", f"V{i}", *pin)),
                            casa("bet365", h2h(f"L{i}", f"V{i}", *blanda))], **kw)


def test_probabilidad_de_consenso_con_pinnacle_como_peso_y_cuota_de_la_casa():
    ops = ext.candidatos({"tenis": [ganador(1)]}, NOW)
    assert len(ops) == 2
    local = next(o for o in ops if o.cand.selection == "home")
    esperado = consensus_devig({"pinnacle": {"home": 1.50, "away": 2.70}, "bet365": {"home": 1.55, "away": 2.60}},
                               settings.devig_method, sharp_book="pinnacle")["home"]
    assert math.isclose(local.cand.prob, esperado)
    assert local.price == 1.55 and local.book == "bet365" and local.match_id == "tenis:1"
    assert local.cand.market == "h2h" and local.odds_source == "propline" and local.odds_as_of == RECIBIDA
    assert local.deporte == "tenis" and local.evento[0] == "1" and local.evento[3:] == ("L1", "V1")
    assert local.n_casas_ref == 2 and local.referencia == "preferida"


def test_pinnacle_no_es_obligatorio_basta_el_consenso_de_otras_casas():
    sin = evento(1, books=[casa("bet365", h2h("L1", "V1", 1.50, 2.70)),
                           casa("betano", h2h("L1", "V1", 1.56, 2.50))])
    ops = ext.candidatos({"tenis": [sin]}, NOW)
    assert len(ops) == 2 and all(o.referencia == "consenso" and o.n_casas_ref == 2 for o in ops)
    local = next(o for o in ops if o.cand.selection == "home")
    esperado = consensus_devig({"bet365": {"home": 1.50, "away": 2.70}, "betano": {"home": 1.56, "away": 2.50}},
                               settings.devig_method)["home"]
    assert math.isclose(local.cand.prob, esperado) and local.price == 1.56


def test_una_sola_casa_que_no_es_pinnacle_no_alcanza_para_un_consenso():
    sola = evento(1, books=[casa("bet365", h2h("L1", "V1", 1.5, 2.6))])
    assert ext.opciones({"tenis": [sola]}, NOW) == []
    # Una casa de referencia que no cotiza la lista de apuestas no genera ofertas.
    solo_pin = evento(2, books=[casa("pinnacle", h2h("L2", "V2", 1.5, 2.6))])
    assert ext.opciones({"tenis": [solo_pin]}, NOW) == []


def test_mejor_cuota_entre_casas_y_guarda_de_atipicas():
    books = [casa("pinnacle", h2h("L1", "V1", 1.50, 2.70))]
    for nombre, precio in (("bet365", 1.55), ("betano", 1.57), ("1xbet", 1.95)):
        books.append(casa(nombre, h2h("L1", "V1", precio, 2.4)))
    ops = ext.candidatos({"tenis": [evento(1, books=books)]}, NOW)
    local = next(o for o in ops if o.cand.selection == "home")
    assert local.price == 1.57 and local.book == "betano"        # 1.95 > 1.57 × 1.05: atípica


def test_ventana_de_inicio():
    antes = ganador(1, inicio=NOW + timedelta(minutes=29))
    justo = ganador(2, inicio=NOW + timedelta(minutes=30))
    lejos = ganador(3, inicio=NOW + timedelta(hours=24))
    ids = {o.match_id for o in ext.opciones({"tenis": [antes, justo, lejos]}, NOW)}
    assert ids == {"tenis:2"}


def test_cuota_vieja_o_sin_recepcion_no_entra():
    vieja = ganador(1, blanda=(1.55, 2.60))
    for m in vieja["bookmakers"][1]["markets"]:
        for o in m["outcomes"]:
            o["last_update"] = (NOW - timedelta(hours=7)).isoformat()
    assert ext.opciones({"tenis": [vieja]}, NOW) == []
    sin_recibo = ganador(2)
    sin_recibo.pop("_received_at")
    assert ext.opciones({"tenis": [sin_recibo]}, NOW) == []
    futuro = ganador(3, recibida=NOW + timedelta(minutes=1))
    assert ext.opciones({"tenis": [futuro]}, NOW) == []


def test_totales_y_handicap_solo_con_lineas_media_y_el_mismo_contrato():
    def tot(punto, over, under):
        return mercado("totals", [dict(name="Over", price=over, point=punto),
                                  dict(name="Under", price=under, point=punto)])

    def spr(local, visit, ph, pl=1.9, pv=1.9):
        return mercado("spreads", [dict(name=local, price=pl, point=ph), dict(name=visit, price=pv, point=-ph)])
    e = evento(1, books=[
        casa("pinnacle", tot(22.5, 1.90, 1.95), spr("L1", "V1", -3.5)),
        casa("bet365", tot(22.5, 1.95, 1.90), spr("L1", "V1", -3.5, 1.92, 1.88)),
        casa("betano", tot(23.5, 2.30, 1.60), spr("L1", "V1", -2.5, 1.80, 2.00))])   # otra línea: no empareja
    ops = ext.candidatos({"tenis": [e]}, NOW)
    por = {(o.cand.market, o.cand.selection, o.cand.line): o for o in ops}
    assert set(por) == {("total_games", "over", 22.5), ("total_games", "under", 22.5),
                        ("handicap_games", "home", -3.5), ("handicap_games", "away", 3.5)}
    assert por[("total_games", "over", 22.5)].price == 1.95 and por[("total_games", "over", 22.5)].book == "bet365"
    entero = evento(2, books=[casa("pinnacle", tot(22.0, 1.9, 1.9)), casa("bet365", tot(22.0, 1.9, 1.9))])
    assert ext.opciones({"tenis": [entero]}, NOW) == []


def test_nba_usa_los_nombres_de_mercado_del_selector():
    def tot(punto):
        return mercado("totals", [dict(name="Over", price=1.9, point=punto), dict(name="Under", price=1.9, point=punto)])
    e = evento(9, sport="basketball_nba", books=[casa("pinnacle", tot(221.5)), casa("bet365", tot(221.5))])
    mercados = {o.cand.market for o in ext.opciones({"nba": [e]}, NOW)}
    assert mercados == {"totals"} and ext.opciones({"nba": [e]}, NOW)[0].match_id == "nba:9"


def test_el_selector_arma_tickets_con_patas_de_tenis_y_nba():
    eventos = {"tenis": [ganador(i, pin=(1.40 + .02 * i, 3.2), blanda=(1.40 + .02 * i, 3.1)) for i in range(1, 9)],
               "nba": [evento(100 + i, sport="basketball_nba",
                              books=[casa("pinnacle", h2h(f"L{100 + i}", f"V{100 + i}", 1.45, 2.8)),
                                     casa("bet365", h2h(f"L{100 + i}", f"V{100 + i}", 1.50, 2.7))])
                       for i in range(4)]}
    ops = ext.candidatos(eventos, NOW)
    plan = v2.armar_plan(ops, ahora=NOW)
    assert plan.tickets, plan.abstenciones
    legs = [o for t in plan.tickets for o in t.legs]
    assert {o.deporte for o in legs} <= {"tenis", "nba"} and any(o.deporte == "tenis" for o in legs)
    assert len({o.match_id for o in legs}) == len(legs)
    assert all(t.estado == "solo_referencia" for t in plan.tickets)


# ------------------------------------------------------------------ props de jugador NBA
def prop(mercado_key, jugador, pid, punto, over, under, **extra):
    return mercado(mercado_key, [dict(name="Over", price=over, point=punto, player_id=pid, description=jugador, **extra),
                                 dict(name="Under", price=under, point=punto, player_id=pid, description=jugador, **extra)])


def test_props_de_jugador_con_consenso_mejor_cuota_y_jugador():
    e = evento(7, sport="basketball_nba", books=[
        casa("pinnacle", prop("player_points", "A. Jugador", 11, 24.5, 1.90, 1.95)),
        casa("bet365", prop("player_points", "A. Jugador", 11, 24.5, 1.95, 1.88)),
        casa("betano", prop("player_points", "A. Jugador", 11, 24.5, 1.92, 1.90))])
    ops = ext.candidatos({"nba_props": [e]}, NOW)
    over = next(o for o in ops if o.cand.selection == "over")
    assert over.cand.market == "player_points" and over.cand.line == 24.5 and over.match_id == "nba:7"
    assert over.price == 1.95 and over.book == "bet365" and over.jugador == ("11", "A. Jugador")
    assert over.n_casas_ref == 3 and over.referencia == "preferida"
    assert v2.familia(over.cand.market) == v2.LINEA


def test_props_solo_lineas_media_dos_lados_y_mercados_medidos():
    e = evento(7, sport="basketball_nba", books=[
        casa("bet365", prop("player_points", "A", 11, 24.0, 1.9, 1.9),            # línea entera: puede devolverse
             prop("player_blocks", "A", 11, 1.5, 1.9, 1.9),                       # mercado no medido
             mercado("player_assists", [dict(name="Over", price=1.9, point=5.5, player_id=11, description="A")])),
        casa("betano", prop("player_points", "A", 11, 24.0, 1.9, 1.9))])
    assert ext.opciones({"nba_props": [e]}, NOW) == []


def test_un_prop_necesita_dos_casas_o_pinnacle_y_el_mismo_jugador_en_ambos_lados():
    una = evento(1, sport="basketball_nba", books=[casa("bet365", prop("player_points", "A", 11, 24.5, 1.9, 1.9))])
    assert ext.opciones({"nba_props": [una]}, NOW) == []
    mezclado = mercado("player_points", [dict(name="Over", price=1.9, point=24.5, player_id=11, description="A"),
                                         dict(name="Under", price=1.9, point=24.5, player_id=12, description="B")])
    e = evento(2, sport="basketball_nba", books=[casa("bet365", mezclado), casa("betano", mezclado)])
    assert ext.opciones({"nba_props": [e]}, NOW) == []


def test_props_feed_filtra_cotizaciones_con_marcas_y_arma_los_dos_lados(monkeypatch):
    pytest.importorskip("qf.ingest.propline_shared")   # aún sin versionar en esta rama; está en producción
    def out(nombre, precio, **kw):
        return dict(name=nombre, description="A. Jugador", player_id=11, point=24.5, price=precio, **kw)

    def libro(clave, *salidas):
        return {"key": clave, "markets": [{"key": "player_points", "outcomes": list(salidas)}]}
    crudo = {"id": "7", "sport_key": "basketball_nba", "commence_time": (NOW + timedelta(hours=5)).isoformat(),
             "home_team": "L", "away_team": "V", "bookmakers": [
                 libro("bet365", out("Over", -110), out("Under", -110)),
                 libro("betano", out("Over", -105), out("Under", -115, allowed_wager_types="over")),   # lado restringido
                 libro("prizepicks", out("Over", -110), out("Under", -110))]}                          # DFS
    feed = ext.props_feed([crudo], RECIBIDA.isoformat())
    assert len(feed) == 1 and [b["key"] for b in feed[0]["bookmakers"]] == ["bet365"]
    assert {o["name"] for o in feed[0]["bookmakers"][0]["markets"][0]["outcomes"]} == {"Over", "Under"}
    assert feed[0]["_received_at"] == RECIBIDA.isoformat()


def test_combos_de_jugador_no_medidos_quedan_en_el_tope_de_lo_no_medido():
    assert v2.familia("player_points_rebounds_assists") == v2.SIN_MEDIR
    assert v2.familia("player_blocks") == v2.SIN_MEDIR


def test_el_selector_usa_props_y_solo_una_pata_por_partido():
    def juego(i):
        libros = [casa("bet365", h2h(f"L{i}", f"V{i}", 1.50, 2.6), ), casa("betano", h2h(f"L{i}", f"V{i}", 1.52, 2.5))]
        return evento(i, sport="basketball_nba", books=libros)

    def props(i):
        return evento(i, sport="basketball_nba", books=[
            casa("bet365", prop("player_rebounds", f"P{i}", i, 7.5, 1.70, 2.05)),
            casa("betano", prop("player_rebounds", f"P{i}", i, 7.5, 1.72, 2.02))])
    eventos = {"nba": [juego(i) for i in range(1, 7)], "nba_props": [props(i) for i in range(1, 7)]}
    ops = ext.candidatos(eventos, NOW)
    assert any(o.cand.market == "player_rebounds" for o in ops) and any(o.cand.market == "h2h" for o in ops)
    plan = v2.armar_plan(ops, ahora=NOW)
    ids = [o.match_id for t in plan.tickets for o in t.legs]
    assert plan.tickets and len(ids) == len(set(ids))
