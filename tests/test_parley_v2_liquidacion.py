from datetime import datetime, timedelta, timezone

import pytest

from qf.publish import parley_v2_datos as datos
from qf.publish import parley_v2_liquidacion as liq

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)
INICIO = datetime(2026, 11, 7, 18, 0, tzinfo=timezone.utc)
EVENTO = ["77", "tennis", INICIO.isoformat(), "Local", "Visita"]


def pata(mercado="h2h", sel="home", linea=None, **kw):
    base = dict(deporte="tenis", mercado=mercado, seleccion=sel, linea=linea, jugador_id=None, casa="bet365",
                inicio_utc=INICIO, evento=EVENTO)
    base.update(kw)
    return base


def fila(market, name, resolution, casa="bet365", point=None, **kw):
    return dict(market=market, name=name, resolution=resolution, bookmaker=casa, point=point, period=None, team=None,
                player_id=kw.pop("player_id", None), **kw)


def test_ganador_totales_y_handicap_de_tenis_con_la_calificacion_de_propline():
    filas = [fila("h2h", "Local", "won"), fila("h2h", "Visita", "lost"),
             fila("totals", "Over", "lost", point=22.5), fila("totals", "Under", "won", point=22.5),
             fila("spreads", "Local", "won", point=-3.5), fila("spreads", "Visita", "lost", point=3.5)]
    assert liq.resolver_propline(pata(), filas) == "win"
    assert liq.resolver_propline(pata(sel="away"), filas) == "loss"
    assert liq.resolver_propline(pata("total_games", "over", 22.5), filas) == "loss"
    assert liq.resolver_propline(pata("total_games", "under", 22.5), filas) == "win"
    assert liq.resolver_propline(pata("handicap_games", "home", -3.5), filas) == "win"
    assert liq.resolver_propline(pata("handicap_games", "away", 3.5), filas) == "loss"
    assert liq.resolver_propline(pata("total_games", "over", 23.5), filas) is None        # otra línea


def test_props_exigen_el_mismo_jugador_y_linea():
    filas = [fila("player_points", "Over", "won", point=24.5, player_id=11),
             fila("player_points", "Over", "lost", point=24.5, player_id=12)]
    p = pata("player_points", "over", 24.5, jugador_id="11", deporte="nba")
    assert liq.resolver_propline(p, filas) == "win"
    assert liq.resolver_propline(dict(p, jugador_id="12"), filas) == "loss"
    assert liq.resolver_propline(dict(p, jugador_id="13"), filas) is None


def test_prefiere_la_casa_de_la_pata_luego_la_mayoria_y_sin_acuerdo_no_liquida():
    filas = [fila("h2h", "Local", "won", "betano"), fila("h2h", "Local", "lost", "bet365")]
    assert liq.resolver_propline(pata(), filas) == "loss"                                   # su casa
    sin_casa = [fila("h2h", "Local", "won", "a"), fila("h2h", "Local", "won", "b"), fila("h2h", "Local", "push", "c")]
    assert liq.resolver_propline(pata(casa="otra"), sin_casa) == "win"                       # mayoría
    empate = [fila("h2h", "Local", "won", "a"), fila("h2h", "Local", "lost", "b")]
    assert liq.resolver_propline(pata(casa="otra"), empate) is None
    assert liq.resolver_propline(pata(), [fila("h2h", "Local", None)]) is None              # sin calificar


def test_pata_sin_calificacion_se_anula_pasado_el_margen():
    assert liq.resultado_pata(pata(), NOW, filas_propline=[]) is None
    tarde = NOW + timedelta(hours=100)
    assert liq.resultado_pata(pata(), tarde, filas_propline=[]) == ("void", None, "sin_calificacion")
    assert liq.resultado_pata(pata(), NOW, filas_propline=[fila("h2h", "Local", "won")]) == ("win", None, "propline")


def test_pata_de_futbol_usa_las_reglas_del_parley_actual():
    f = dict(deporte="futbol", mercado="totals", seleccion="over", linea=2.5, inicio_utc=INICIO, evento=[], jugador_id=None, casa="b")
    fila_f = dict(status="finished", kickoff_utc=INICIO, kickoff_original=INICIO, home_goals=2, away_goals=1,
                  home_corners=None, away_corners=None, home_yellow=None, away_yellow=None, home_red=None, away_red=None)
    assert liq.resultado_pata(f, NOW, fila_futbol=fila_f)[:2] == ("win", None)
    assert liq.resultado_pata(f, NOW) is None


def test_ticket_pierde_con_una_perdida_paga_a_cuota_1_las_devueltas_y_espera_si_falta_alguna():
    assert liq.liquidar_ticket([("win", 1.5), ("win", 1.4)]) == {"outcome": "ganado", "factor_pago": 2.1}
    assert liq.liquidar_ticket([("win", 1.5), ("loss", 1.4)])["outcome"] == "perdido"
    assert liq.liquidar_ticket([("win", 1.5), ("void", 1.4)]) == {"outcome": "ganado", "factor_pago": 1.5}
    assert liq.liquidar_ticket([("void", 1.5), ("push", 1.4)])["outcome"] == "nulo"
    assert liq.liquidar_ticket([("win", 1.5), (None, 1.4)]) is None


def test_liquidar_pendientes_guarda_patas_y_cierra_el_ticket(monkeypatch):
    guardadas, cerrados = [], []
    pendientes = [dict(pata_id="p1", deporte="tenis", evento_id="77", mercado="h2h", seleccion="home", linea=None,
                       jugador_id=None, casa="bet365", inicio_utc=INICIO, evento=EVENTO),
                  dict(pata_id="p2", deporte="nba", evento_id="9", mercado="player_points", seleccion="over", linea=24.5,
                       jugador_id="11", casa="bet365", inicio_utc=INICIO, evento=["9", "basketball_nba", "x", "L", "V"])]
    monkeypatch.setattr(liq, "_pendientes", lambda now: pendientes)
    monkeypatch.setattr(liq, "_guardar_pata", lambda i, o, v, f: guardadas.append((i, o, f)) or 1)
    monkeypatch.setattr(liq, "_tickets_pendientes", lambda: [
        {"ticket_id": "t1", "price": 1.5, "outcome": "win"}, {"ticket_id": "t1", "price": 1.6, "outcome": "win"},
        {"ticket_id": "t2", "price": 1.5, "outcome": "win"}, {"ticket_id": "t2", "price": 1.6, "outcome": None}])
    monkeypatch.setattr(liq, "_guardar_ticket", lambda i, o, f: cerrados.append((i, o, f)) or 1)
    por_sport = {"tennis": [fila("h2h", "Local", "won")],
                 "basketball_nba": [fila("player_points", "Over", "lost", point=24.5, player_id=11)]}
    r = liq.liquidar_pendientes(NOW, leer_filas=lambda sport, ev, now: por_sport[sport])
    assert r == {"patas": 2, "tickets": 1}
    assert guardadas == [("p1", "win", "propline"), ("p2", "loss", "propline")]
    assert cerrados == [("t1", "ganado", 2.4)]


def test_el_id_de_evento_de_futbol_conserva_el_match_id_completo():
    from qf.publish.alta_prob import Candidato
    from qf.publish.parley_ext import OpcionExterna
    from datetime import timezone as tz
    mk = lambda mid, dep: OpcionExterna(match_id=mid, cand=Candidato("h2h", "home", None, .6), price=1.5, book="b",
                                        odds_source="t", odds_as_of=NOW, deporte=dep)
    assert datos._pata(mk("es.laliga:2425:cadiz-celta:20250225", "futbol"))["evento_id"] == "es.laliga:2425:cadiz-celta:20250225"
    assert datos._pata(mk("tenis:123", "tenis"))["evento_id"] == "123"
