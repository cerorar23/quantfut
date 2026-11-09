"""Cuarto nivel de la cascada de cuotas (TheRundown Free): respuestas con la forma REAL del 9-nov-2026, sin red.

Los eventos de NBA y tenis reproducen la estructura medida con la clave Free (mercados 1/2/3, participantes con `type`,
`lines[].value` y `prices` por afiliado en cuota americana). Fútbol sigue la documentación (1X2 con tres participantes)
porque ese día no había partidos de las ligas del catálogo: su forma NO está verificada con datos reales.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import test_cuotas_nba as base
from test_cuotas_respaldo import NOW, SEALED, Red, entorno  # noqa: F401  (fixture `entorno`)
from test_cuotas_cascada import TIPOFF, futuro, futbol, KO, RedFutbol, mercado, SP, canon  # noqa: F401

from qf.api import cuotas_nba as cn
from qf.ingest import cuotas_respaldo as cr
from qf.ingest import cuotas_respaldo_futbol as rf
from qf.ingest import cuotas_therundown as crd
from qf.ingest import propline_shared as pl
from qf.publish import regla_publicacion

UTC = timezone.utc


def precio(p, **kw):
    return dict(id="1", price=p, is_main_line=True, updated_at="2026-11-09T12:00:00Z", **kw)


def linea(valor, **precios):
    d = dict(id="x" * 32, prices={a: precio(p) for a, p in precios.items()})
    if valor is not None:
        d["value"] = valor
    return d


def part(id_, tipo, nombre, *lineas):
    return dict(id=id_, type=tipo, name=nombre, lines=list(lineas))


def evento_nba(inicio=TIPOFF, local="Boston Celtics", visita="New York Knicks", total="215.5"):
    """Forma real de un evento NBA con mercados 1, 2 y 3 (`teams` = [visitante, local])."""
    return dict(event_id="ev-nba-1", event_date=inicio.strftime("%Y-%m-%dT%H:%M:%SZ"),
                teams=[dict(team_id=2, name="New York", is_away=True), dict(team_id=1, name="Boston", is_home=True)],
                score=dict(event_status="STATUS_SCHEDULED"), markets=[
        dict(market_id=1, period_id=0, name="moneyline", participants=[
            part(1, "TYPE_TEAM", local, linea(None, **{"19": -490, "22": -500, "23": -490})),
            part(2, "TYPE_TEAM", visita, linea(None, **{"22": 375, "23": 380, "19": 376}))]),
        dict(market_id=2, period_id=0, name="handicap", participants=[
            part(1, "TYPE_TEAM", local, linea("-10.5", **{"22": -110, "19": -112})),
            part(2, "TYPE_TEAM", visita, linea("+10.5", **{"22": -110, "19": -108}))]),
        dict(market_id=3, period_id=0, name="totals", participants=[
            part(9, "TYPE_RESULT", "Over", linea(total, **{"22": -110, "23": -112}), linea("217.5", **{"19": -113})),
            part(10, "TYPE_RESULT", "Under", linea(total, **{"22": -110, "23": -108}), linea("217.5", **{"19": -107}))])])


def evento_tenis(inicio, a="Adrian Mannarino", b="Aleksandr Shevchenko"):
    """Forma real (ATP, 10-nov-2026): ganador, hándicap de juegos con varias líneas y total 22.5."""
    return dict(event_id="ev-ten-1", event_date=inicio.strftime("%Y-%m-%dT%H:%M:%SZ"),
                teams=[dict(name="Mannarino"), dict(name="Shevchenko")], score=dict(event_status="STATUS_SCHEDULED"),
                markets=[
        dict(market_id=1, period_id=0, name="moneyline", participants=[
            part(1, "TYPE_TEAM", a, linea(None, **{"23": -134, "19": -130, "22": -130})),
            part(2, "TYPE_TEAM", b, linea(None, **{"23": 110, "19": 107, "22": 100}))]),
        dict(market_id=2, period_id=0, name="handicap", participants=[
            part(1, "TYPE_TEAM", a, linea("-1.5", **{"23": -120, "22": -110}), linea("-2.5", **{"19": 110})),
            part(2, "TYPE_TEAM", b, linea("+1.5", **{"23": -130, "22": -135}), linea("+2.5", **{"19": -175}))]),
        dict(market_id=3, period_id=0, name="totals", participants=[
            part(9, "TYPE_RESULT", "Over", linea("22.5", **{"23": -120, "22": -120, "19": -140})),
            part(10, "TYPE_RESULT", "Under", linea("22.5", **{"22": -118, "19": -105, "23": -110}))])])


class RD:
    """Doble de TheRundown: registra las URL (sin clave) y responde eventos por (sport_id, fecha)."""
    def __init__(self, eventos=None, status=200, restante=19000):
        self.urls, self.eventos, self.status, self.restante = [], eventos or {}, status, restante

    def __call__(self, url):
        self.urls.append(url)
        sid, fecha = url.split("/sports/")[1].split("?")[0].split("/events/")
        cab = {"x-datapoints": "100", "x-datapoints-remaining": str(self.restante)}
        return self.status, cab, json.dumps({"events": self.eventos.get((int(sid), fecha), [])}).encode()


def sin_pausa(_):
    pass


@pytest.fixture(autouse=True)
def reloj_fijo(monkeypatch):
    """Las fechas del fixture son de octubre: la caducidad de 24 h se evalúa contra el reloj de la prueba."""
    ahora = {"t": NOW + timedelta(minutes=5)}
    monkeypatch.setattr(cr, "_ahora", lambda: ahora["t"])
    return ahora


# --- piezas puras ---------------------------------------------------------------------------------------------

def test_americano_a_decimal():
    assert crd.americano_a_decimal(-110) == pytest.approx(1.9091, abs=1e-4)
    assert crd.americano_a_decimal(150) == 2.5 and crd.americano_a_decimal("+101") == pytest.approx(2.01)
    assert crd.americano_a_decimal(-490) == pytest.approx(1.2041, abs=1e-4)
    for malo in (0.0001, 0, 50, -50, None, "x", float("nan")):
        assert crd.americano_a_decimal(malo) is None


def test_lineas_ignora_cerradas_y_sentinela():
    e = evento_nba()
    e["markets"][0]["participants"][0]["lines"][0]["prices"]["22"] = precio(-500, closed_at="2026-11-09T13:00:00Z")
    e["markets"][0]["participants"][0]["lines"][0]["prices"]["23"] = precio(0.0001)
    ml = crd.lineas(e, 1)[0]
    assert set(ml["precios"]) == {"draftkings"}
    e["markets"][0]["period_id"] = 1          # un periodo que no es el partido completo no cuenta
    assert crd.lineas(e, 1) == [l for l in crd.lineas(e, 1) if False]


def test_filas_nba_ganador_y_total():
    e = evento_nba()
    w = crd.filas_item(e, "nba", dict(market="winner"), "Boston Celtics", "New York Knicks")
    assert {(f["side"], f["bookmaker"]) for f in w} >= {("home", "draftkings"), ("away", "fanduel")}
    t = crd.filas_item(e, "nba", dict(market="game_total", line=215.5), "Boston Celtics", "New York Knicks")
    assert {(f["name"], f["point"]) for f in t} == {("Over", 215.5), ("Under", 215.5)}   # la 217.5 no sirve: no se guarda
    from qf.ingest.cuotas_referencia import best_quote
    q = best_quote(t, line=215.5, side="over", sealed_at=NOW, received_at=NOW)
    assert q.book == "betmgm" and q.price == pytest.approx(1.9091, abs=1e-4) and q.books == 2    # -110 gana a -112
    assert best_quote(t, line=216.5, side="over", sealed_at=NOW, received_at=NOW) is None


def test_filas_tenis_ganador_total_y_handicap():
    e = evento_tenis(datetime(2026, 11, 10, 12, 0, tzinfo=UTC))
    a, b = "Adrian Mannarino", "Aleksandr Shevchenko"
    w = crd.filas_item(e, "tenis", dict(market="winner"), a, b)
    assert {(f["side"], f["bookmaker"]) for f in w} >= {("A", "fanduel"), ("B", "betmgm")}
    t = crd.filas_item(e, "tenis", dict(market="games_total", line=22.5), a, b)
    assert {(f["name"], f["point"]) for f in t} == {("Over", 22.5), ("Under", 22.5)}
    h = crd.filas_item(e, "tenis", dict(market="games_handicap", line=-1.5, selection="A"), a, b)
    from qf.ingest.cuotas_referencia import best_quote
    q = best_quote(h, line=-1.5, side="A", sealed_at=NOW, received_at=NOW)
    assert q.book == "betmgm" and q.price == pytest.approx(1 + 100 / 110, abs=1e-4)             # -110 gana a -120
    # Jugadores en otro orden o con «Apellido I.»: el lado se decide por el nombre, no por la posición.
    w2 = crd.filas_item(e, "tenis", dict(market="winner"), "Shevchenko A.", "Mannarino A.")
    assert {f["side"] for f in w2 if f["bookmaker"] == "fanduel"} == {"A", "B"}
    assert next(f for f in w2 if f["bookmaker"] == "fanduel" and f["side"] == "A")["price_decimal"] == pytest.approx(2.1)
    assert crd.filas_item(e, "tenis", dict(market="player_points"), a, b) == []     # props: no existen en Free


def test_busca_evento_unico_y_por_nombres_de_participante():
    ini = TIPOFF
    uno = evento_nba(ini)
    terminado = dict(event_id="old", event_date=ini.strftime("%Y-%m-%dT%H:%M:%SZ"), teams=[], markets=[])
    assert crd.busca_evento([terminado, uno], "Boston Celtics", "New York Knicks", ini, tenis=False) is uno
    assert crd.busca_evento([uno], "New York Knicks", "Boston Celtics", ini, tenis=False) is uno     # orden indiferente
    otro = dict(evento_nba(ini + timedelta(minutes=30)), event_id="otro")
    assert crd.busca_evento([uno, otro], "Boston Celtics", "New York Knicks", ini, tenis=False) is None  # dos: duda
    assert crd.busca_evento([evento_nba(ini + timedelta(hours=4))], "Boston Celtics", "New York Knicks", ini,
                            tenis=False) is None
    # «Los Angeles» es ambiguo en el evento (Lakers y Clippers): el participante tiene el nombre completo.
    assert crd.busca_evento([uno], "Boston", "New York Knicks", ini, tenis=False) is None


# --- cliente --------------------------------------------------------------------------------------------------

class Reloj:
    def __init__(self):
        self.t, self.pausas = 100.0, []

    def __call__(self):
        return self.t

    def duerme(self, s):
        self.pausas.append(round(s, 3))
        self.t += s


def test_cliente_respeta_1_peticion_por_segundo_y_no_filtra_la_clave():
    reloj, rd = Reloj(), RD()
    cli = crd.Cliente("clave-secreta", call=rd, sleep=reloj.duerme, clock=reloj)
    cli.eventos(4, "2026-11-10")
    cli.eventos(38, "2026-11-10")
    assert reloj.pausas and reloj.pausas[0] == pytest.approx(crd.PAUSA, abs=0.01)
    assert all("clave-secreta" not in u and "apiKey" not in u for u in rd.urls)
    assert "market_ids=1,2,3" in rd.urls[0] and "main_line=true" in rd.urls[0]     # sin main_line costaría 24 veces más
    assert cli.peticiones == 2 and cli.puntos == 200 and cli.restante == 19000


@pytest.mark.parametrize("status", [429, 403, 401])
def test_cliente_para_en_429_403_401(status):
    cli = crd.Cliente("k", call=RD(status=status), sleep=sin_pausa)
    with pytest.raises(crd.SinCupo):
        cli.eventos(4, "2026-11-10")
    with pytest.raises(crd.SinCupo):                    # agotado: ya no se llama
        cli.eventos(4, "2026-11-11")
    assert cli.peticiones == 1


def test_cliente_respeta_la_reserva_de_puntos():
    rd = RD(restante=1500)                              # bajo la reserva de 2000
    cli = crd.Cliente("k", call=rd, sleep=sin_pausa)
    cli.eventos(4, "2026-11-10")
    with pytest.raises(crd.SinCupo):
        cli.eventos(38, "2026-11-10")
    assert len(rd.urls) == 1


# --- cascada NBA / tenis ---------------------------------------------------------------------------------------

def pasada(cache, rd, **kw):
    out, info = [], {}
    cr.correr(key=kw.pop("key", "k"), cache_path=str(cache), get=kw.pop("get", Red(eventos=[])),
              now=kw.pop("now", NOW), salida=out.append, sp_key=kw.pop("sp_key", ""), rd_key="rd", rd_call=rd,
              rd_sleep=sin_pausa, info=info, ejecutar=True, **kw)
    return out, info


def overlay(archive, cs, cache):
    return cr.aplica_nba(cn.nba_overlay(archive, cs, now=NOW), cr.leer_cache(cache))["events"]["0022600099"]["quotes"]


def test_nivel4_resuelve_lo_que_ninguno_encontro(entorno):
    archive, cs, cache = entorno
    futuro(cs)
    rd = RD({(4, "2026-10-31"): [evento_nba()]})
    out, info = pasada(cache, rd)
    assert info["nuevas"] == 0 and info["nuevas_sportsapipro"] == 0 and info["nuevas_therundown"] == 2
    assert [u.split("/api/v2")[1].split("?")[0] for u in rd.urls] == ["/sports/4/events/2026-10-31"]
    q = overlay(archive, cs, cache)
    assert q["game_total||215.5"]["over"]["src"] == "therundown" and q["game_total||215.5"]["over"]["post_sello"] is True
    assert q["game_total||215.5"]["over"]["book"] == "betmgm"
    assert pl.parse_time(q["game_total||215.5"]["over"]["as_of"]) == NOW
    assert q["winner||"]["home"]["price"] == pytest.approx(1 + 100 / 490, abs=1e-4)


def test_sportsapipro_gana_a_therundown_cuando_resuelve(entorno):
    archive, cs, cache = entorno
    futuro(cs)
    sp = SP([dict(id=777, homeTeam=dict(name="Boston Celtics"), awayTeam=dict(name="New York Knicks"),
                  startTimestamp=int(TIPOFF.timestamp()))],
            {"data": {"markets": [mercado(1, "Full time", [("1", "1/2"), ("2", "13/8")], grupo="Home/Away"),
                                  mercado(18, "Game total", [("Over", "10/11"), ("Under", "10/11")], linea=215.5,
                                          grupo="Over/Under")]}})
    rd = RD({(4, "2026-10-31"): [evento_nba()]})
    out, info = pasada(cache, rd, sp_key="sp", sp_call=sp)
    assert info["nuevas_sportsapipro"] == 2 and info["nuevas_therundown"] == 0 and rd.urls == []


def test_nivel4_sin_clave_o_con_partido_ya_empezado_no_pide(entorno):
    archive, cs, cache = entorno                      # el partido del fixture ya empezó antes de NOW
    rd = RD({(4, "2026-10-31"): [evento_nba()]})
    pasada(cache, rd)
    assert rd.urls == []
    out = []
    cr.correr(key="", sp_key="", rd_key="", cache_path=str(cache), salida=out.append, ejecutar=True)
    assert out == ["sin ODDS_API_RESPALDO_KEY, SPORTSAPIPRO_KEY ni THERUNDOWN_API_KEY: no hay nada que hacer"]


def test_nivel4_429_corta_y_reintentos_acotados(entorno):
    archive, cs, cache = entorno
    futuro(cs)
    rd = RD(status=429)
    out, info = pasada(cache, rd)
    assert info["nuevas_therundown"] == 0 and len(rd.urls) == 1 and any("429" in x for x in out)
    # Evento ausente: un intento por hora, dos como máximo.
    rd = RD({})
    for minutos in (0, 10, 70, 300):
        pasada(cache, rd, now=NOW + timedelta(minutes=minutos))
    assert len(rd.urls) == 2


def test_interruptor_y_caducidad_de_24_horas(entorno, monkeypatch, reloj_fijo):
    archive, cs, cache = entorno
    futuro(cs)
    pasada(cache, RD({(4, "2026-10-31"): [evento_nba()]}))
    assert overlay(archive, cs, cache)["game_total||215.5"]["over"]["src"] == "therundown"
    monkeypatch.setenv("CUOTAS_THERUNDOWN_MOSTRAR", "0")
    assert overlay(archive, cs, cache)["game_total||215.5"] == dict(over=None, under=None)   # oculto sin tocar la caché
    monkeypatch.delenv("CUOTAS_THERUNDOWN_MOSTRAR")
    reloj_fijo["t"] = NOW + timedelta(hours=25)           # más de 24 h desde la recepción: la lectura ya no la sirve
    assert overlay(archive, cs, cache)["game_total||215.5"] == dict(over=None, under=None)
    # A las 24 h ya no se sirve ni se conserva (licencia).
    entradas = cr.leer_cache(cache)
    assert any(e.get("fuente") == "therundown" for e in entradas.values())
    cr.escribir_cache(cache, entradas, NOW + timedelta(hours=25))
    assert not any(e.get("fuente") == "therundown" for e in cr.leer_cache(cache).values())
    cr.escribir_cache(cache, entradas, NOW + timedelta(hours=23))
    assert any(e.get("fuente") == "therundown" for e in cr.leer_cache(cache).values())


def test_la_regla_de_publicacion_ignora_therundown():
    assert regla_publicacion._precio_publicable({"price": 1.9, "post_sello": True, "src": "therundown"}) is None


def test_nivel4_tenis_ganador_total_y_handicap():
    a, b = "Adrian Mannarino", "Aleksandr Shevchenko"
    ini = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    sello = ini - timedelta(hours=3)
    h = cr.Hueco("tenis", "T1", None, a, b, ini, sello, [
        dict(key="winner", market="winner", odds_market="h2h", line=None, selection="A"),
        dict(key="games_total-0", market="games_total", odds_market="totals", line=22.5, selection="over"),
        dict(key="games_handicap-1", market="games_handicap", odds_market="spreads", line=-1.5, selection="A"),
        dict(key="tiebreak-3", market="tiebreak", odds_market="x", line=None, selection="yes")])
    rd = RD({(38, "2026-11-10"): [evento_tenis(ini)]})
    cli = crd.Cliente("k", call=rd, sleep=sin_pausa)
    entries = {}
    ahora = sello + timedelta(hours=1)
    assert cr.nivel4_therundown(cli, [h], entries, {}, ahora) == 3
    out = cr.aplica_tenis(dict(events={"T1": {k: None for k in ("winner", "games_total-0", "games_handicap-1", "tiebreak-3")}}),
                          entries)["events"]["T1"]
    assert out["winner"]["src"] == "therundown" and out["winner"]["book"] == "betmgm"          # empate de precio: la menor
    assert out["games_total-0"]["side"] == "over" and out["games_handicap-1"]["side"] == "A" and out["tiebreak-3"] is None
    assert [u.split("/api/v2")[1].split("?")[0] for u in rd.urls] == ["/sports/38/events/2026-11-10"]
    # WTA: si ATP no tiene el partido se prueba el circuito femenino.
    rd2 = RD({(39, "2026-11-10"): [evento_tenis(ini)]})
    assert cr.nivel4_therundown(crd.Cliente("k", call=rd2, sleep=sin_pausa), [h], {}, {}, ahora) == 3
    assert [u.split("/api/v2")[1].split("?")[0] for u in rd2.urls] == ["/sports/38/events/2026-11-10",
                                                                        "/sports/39/events/2026-11-10"]


def test_auto_con_creditos_agotados_therundown_sigue(entorno):
    archive, cs, cache = entorno
    futuro(cs)
    s = cr.settings
    s.cuotas_respaldo_auto, s.cuotas_respaldo_auto_max, s.cuotas_respaldo_diario = True, 100, 0
    s.cuotas_respaldo_cache, s.sportsapipro_key, s.therundown_key = str(cache), None, None
    red = Red()
    assert cr.auto(key="k", get=red, now=NOW, alerta=lambda m: None)["estado"] == "tope_diario"
    rd = RD({(4, "2026-10-31"): [evento_nba()]})
    r = cr.auto(key="k", get=red, now=NOW, alerta=lambda m: None, rd_key="rd", rd_call=rd, rd_sleep=sin_pausa,
                huecos_futbol=[])
    assert r["estado"] == "ok" and red.de_pago() == [] and len(rd.urls) == 1


# --- fútbol (solo consulta) ------------------------------------------------------------------------------------

def evento_futbol(inicio=KO, local="Arsenal", visita="Chelsea"):
    """1X2 con tres participantes (el empate como tercer participante), hándicap y total. Forma según la documentación."""
    return dict(event_id="ev-fut-1", event_date=inicio.strftime("%Y-%m-%dT%H:%M:%SZ"), teams=[], markets=[
        dict(market_id=1, period_id=0, name="moneyline", participants=[
            part(1, "TYPE_TEAM", local, linea(None, **{"19": 120, "23": 125})),
            part(2, "TYPE_TEAM", visita, linea(None, **{"19": 210, "23": 205})),
            part(0, "TYPE_RESULT", "Draw", linea(None, **{"19": 240, "23": 245}))]),
        dict(market_id=2, period_id=0, name="handicap", participants=[
            part(1, "TYPE_TEAM", local, linea("-0.5", **{"19": 120})), part(2, "TYPE_TEAM", visita, linea("+0.5", **{"19": -150}))]),
        dict(market_id=3, period_id=0, name="totals", participants=[
            part(9, "TYPE_RESULT", "Over", linea("2.5", **{"19": -110})), part(10, "TYPE_RESULT", "Under", linea("2.5", **{"19": -110}))])])


def test_filas_futbol_1x2_handicap_y_totales():
    filas = crd.filas_futbol(evento_futbol(), "Arsenal", "Chelsea")
    claves = {(f["market"], f["selection"], f["line"]) for f in filas}
    assert claves == {("h2h", "home", None), ("h2h", "away", None), ("h2h", "draw", None),
                      ("spreads", "home", -0.5), ("spreads", "away", 0.5), ("totals", "over", 2.5), ("totals", "under", 2.5)}
    assert next(f for f in filas if f["selection"] == "draw" and f["bookmaker"] == "fanduel")["price"] == pytest.approx(3.45)


def test_futbol_nivel4_y_mezcla_con_los_demas(futbol, monkeypatch):
    from qf.ingest import odds_worker as ow
    h, eventos, spa, tmp = futbol
    h["odds_api_key"] = "soccer_epl"
    eventos[0]["bookmakers"][0]["key"] = "leovegas_se"            # The Odds API cotiza, pero no es casa de suscriptores
    monkeypatch.setattr(ow, "match_meta", lambda ids: {"M1": dict(match_id="M1", kickoff_utc=KO, league_id="eu.epl",
                                                                   home="Arsenal", away="Chelsea")})
    monkeypatch.setattr(spa, "event_id", lambda db, hh: None)       # SportsAPIPro sin calendario: no pide nada
    rd = RD({(11, KO.date().isoformat()): [evento_futbol()]})
    ahora = KO - timedelta(hours=5)
    out = rf.correr(ejecutar=True, get=RedFutbol(eventos), now=ahora, lista_huecos=[h], sp_call=SP(), rd_key="rd",
                    rd_call=rd, rd_sleep=sin_pausa, resolutor=lambda nombre, canonico: crd.norm(nombre) == crd.norm(canonico),
                    salida=lambda x: None)
    assert out["therundown"] == 1 and out["peticiones_therundown"] == 1
    ent = rf.leer_cache(tmp / "cuotas_respaldo_futbol.json")
    assert set(ent) == {"M1", "M1|rd"} and ent["M1|rd"]["fuente"] == "therundown"
    mejor = rf.cuotas_de_cache(ent, "M1", ahora + timedelta(minutes=5), ("betano",), canon)
    assert mejor["h2h:home:None"][1] in ("draftkings", "fanduel") and mejor["totals:over:2.5"][0] == pytest.approx(1.9091, abs=1e-4)
    # Interruptor: oculta TheRundown sin tocar la caché; no rellena lo que ya cubren otras fuentes.
    monkeypatch.setenv("CUOTAS_THERUNDOWN_MOSTRAR", "0")
    assert rf.cuotas_de_cache(ent, "M1", ahora + timedelta(minutes=5), ("betano",), canon) == {}


def test_futbol_therundown_solo_ligas_de_su_catalogo(futbol, monkeypatch):
    from qf.ingest import odds_worker as ow
    h, eventos, spa, tmp = futbol
    h["odds_api_key"] = "soccer_brazil_campeonato"                 # fuera del catálogo de TheRundown
    monkeypatch.setattr(ow, "match_meta", lambda ids: {"M1": dict(match_id="M1", kickoff_utc=KO, league_id="br.a",
                                                                   home="Arsenal", away="Chelsea")})
    monkeypatch.setattr(spa, "event_id", lambda db, hh: None)
    rd = RD()
    eventos[0]["bookmakers"][0]["key"] = "leovegas_se"
    rf.correr(ejecutar=True, get=RedFutbol(eventos), now=KO - timedelta(hours=5), lista_huecos=[h], sp_call=SP(),
              rd_key="rd", rd_call=rd, rd_sleep=sin_pausa, resolutor=lambda a, b: False, salida=lambda x: None)
    assert rd.urls == []
    ent = rf.leer_cache(tmp / "cuotas_respaldo_futbol.json")
    assert "M1|rd" not in ent


def test_futbol_cache_de_therundown_caduca_a_las_24_horas(tmp_path):
    ahora = KO - timedelta(hours=5)
    ent = {"M1|rd": dict(fuente="therundown", captured_at=(ahora - timedelta(hours=25)).isoformat(), rows=[]),
           "M2|rd": dict(fuente="therundown", captured_at=(ahora - timedelta(hours=23)).isoformat(), rows=[]),
           "M3": dict(fuente="the-odds-api", captured_at=(ahora - timedelta(hours=30)).isoformat(), rows=[])}
    rf.escribir_cache(tmp_path / "c.json", ent, ahora)
    assert set(rf.leer_cache(tmp_path / "c.json")) == {"M2|rd", "M3"}


def test_futbol_respuesta_real_epl_20261121():
    """Respuesta REAL de TheRundown (EPL, 21-nov-2026, 2 eventos): el empate llega como participante `Draw` (id 3) y el
    hándicap trae a veces líneas distintas por casa (la principal de cada una)."""
    from pathlib import Path
    doc = json.loads((Path(__file__).parent / "fixtures" / "therundown_epl_20261121.json").read_text(encoding="utf-8"))
    ini = datetime(2026, 11, 21, 12, 30, tzinfo=UTC)
    e = crd.busca_evento(doc["events"], "Manchester City", "Fulham", ini, tenis=False)
    assert e is not None and e["event_id"].startswith("a416d9fe")
    assert crd.busca_evento(doc["events"], "Manchester City", "Chelsea", ini, tenis=False) is None
    filas = crd.filas_futbol(e, "Manchester City", "Fulham")
    assert {(f["market"], f["selection"], f["line"]) for f in filas} == {
        ("h2h", "home", None), ("h2h", "draw", None), ("h2h", "away", None),
        ("spreads", "home", -1.5), ("spreads", "away", 1.5), ("totals", "over", 3.5), ("totals", "under", 3.5)}
    mejor = {}
    for f in filas:
        k = (f["market"], f["selection"], f["line"])
        mejor[k] = max(mejor.get(k, (0, "")), (f["price"], f["bookmaker"]))
    assert mejor[("h2h", "draw", None)] == (4.8, "fanduel") and mejor[("h2h", "away", None)][0] == 6.0   # +500 en dos casas
    assert mejor[("h2h", "home", None)][0] == pytest.approx(1.4348, abs=1e-4)
    # El segundo evento tiene líneas de hándicap distintas por casa: cada una queda con su propia línea.
    e2 = crd.busca_evento(doc["events"], "Aston Villa", "Sunderland", datetime(2026, 11, 21, 15, 0, tzinfo=UTC), tenis=False)
    lineas_h = {(f["selection"], f["line"]) for f in crd.filas_futbol(e2, "Aston Villa", "Sunderland") if f["market"] == "spreads"}
    assert lineas_h == {("home", -0.5), ("home", -1.5), ("away", 0.5), ("away", 1.5)}


def test_interruptor_por_archivo_en_el_volumen(tmp_path, monkeypatch):
    """Ocultar sin reiniciar: crear `cuotas_therundown_oculto` junto a la caché basta (la lectura se refresca cada 5 s)."""
    monkeypatch.setenv("CUOTAS_RESPALDO_CACHE", str(tmp_path / "cuotas_respaldo.json"))
    monkeypatch.delenv("CUOTAS_THERUNDOWN_MOSTRAR", raising=False)
    monkeypatch.setattr(crd, "_oculto", [0.0, False])
    assert crd.mostrar() is True
    (tmp_path / crd.ARCHIVO_OCULTAR).write_text("", encoding="utf-8")
    assert crd.mostrar() is True                       # aún dentro de la ventana de 5 s: usa la lectura anterior
    monkeypatch.setattr(crd, "_oculto", [0.0, False])  # pasa la ventana
    assert crd.mostrar() is False
    (tmp_path / crd.ARCHIVO_OCULTAR).unlink()
    monkeypatch.setattr(crd, "_oculto", [0.0, True])
    assert crd.mostrar() is True
    monkeypatch.setenv("CUOTAS_THERUNDOWN_MOSTRAR", "0")                # la variable sigue mandando
    assert crd.mostrar() is False


def test_no_se_guardan_entradas_de_otra_linea_caso_real_de_produccion(entorno):
    """9-nov 16:30 UTC: el nivel 4 guardó 7 entradas de hándicap cuyas filas eran de otras líneas (la sellada +5.5 frente a
    las ±1.5 que cotizan las casas): inútiles y, además, marcaban el hueco como resuelto durante 24 h."""
    a, b = "Adrian Mannarino", "Aleksandr Shevchenko"
    ini = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
    sello = ini - timedelta(hours=3)
    items = [dict(key=f"games_handicap-{i}", market="games_handicap", odds_market="spreads", line=l, selection="A")
             for i, l in ((14, 0.0), (16, 3.5), (17, 5.5), (12, -1.5), (13, -2.5))]
    items.append(dict(key="games_total-3", market="games_total", odds_market="totals", line=21.5, selection="over"))
    h = cr.Hueco("tenis", "T1", None, a, b, ini, sello, items)
    entries = {}
    cli = crd.Cliente("k", call=RD({(38, "2026-11-10"): [evento_tenis(ini)]}), sleep=sin_pausa)
    n = cr.nivel4_therundown(cli, [h], entries, {}, sello + timedelta(hours=1))
    # El evento cotiza hándicap ±1.5 (betmgm/fanduel) y ±2.5 (draftkings) y el total 22.5: solo -1.5 y -2.5 existen.
    assert n == 2 and set(entries) == {"T1|games_handicap-12", "T1|games_handicap-13"}
    # Sin ninguna línea coincidente no hay entrada (y por tanto el hueco sigue abierto para un siguiente intento).
    cli = crd.Cliente("k", call=RD({(38, "2026-11-10"): [evento_tenis(ini)]}), sleep=sin_pausa)
    h2 = cr.Hueco("tenis", "T2", None, a, b, ini, sello, items[:3] + items[5:])
    assert cr.nivel4_therundown(cli, [h2], {}, {}, sello + timedelta(hours=1)) == 0


def test_sportsapipro_totales_solo_de_la_linea_sellada():
    from qf.ingest import cuotas_sportsapipro as csp
    ms = csp.mercados({"data": {"markets": [
        dict(marketId=12, marketName="Total games won", choiceGroup="22.5", marketGroup="x", marketPeriod="Match",
             choices=[dict(name="Over", fractionalValue="5/6"), dict(name="Under", fractionalValue="5/6")])]}})
    assert csp.filas_item(ms, "tenis", dict(market="games_total", line=22.5), "a", "b")
    assert csp.filas_item(ms, "tenis", dict(market="games_total", line=22.0), "a", "b") == []
