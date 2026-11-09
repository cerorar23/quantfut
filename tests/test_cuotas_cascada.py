"""Cascada de cuotas PropLine -> The Odds API -> SportsAPIPro: respuestas grabadas/sintéticas, sin red.

El cuerpo de tenis es la respuesta REAL de `/v2/tennis/api/match/17511576/odds/pre-match` del 9-nov-2026 (plan gratuito).
Los de baloncesto (totales) y fútbol son sintéticos con el mismo esquema: sus nombres de mercado no están verificados.
"""
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import test_cuotas_nba as base
from test_cuotas_respaldo import NOW, SEALED, STAMP, Red, entorno, libro, oevento  # noqa: F401  (fixture `entorno`)

from qf.api import cuotas_nba as cn
from qf.ingest import cuotas_respaldo as cr
from qf.ingest import cuotas_respaldo_futbol as rf
from qf.ingest import cuotas_sportsapipro as csp
from qf.ingest import propline_shared as pl
from qf.publish import regla_publicacion

UTC = timezone.utc

TENIS_REAL = {"success": True, "matchId": 17511576, "endpoint": "odds/1/all", "data": {"markets": [
    {"sourceId": 204228674, "structureType": 1, "marketId": 1, "marketName": "Full time", "isLive": False,
     "fid": 204228674, "suspended": False, "id": 465339904, "marketGroup": "Home/Away", "marketPeriod": "Match",
     "choices": [{"initialFractionalValue": "12/5", "fractionalValue": "2/1", "sourceId": 406346285, "name": "1",
                  "winning": False, "change": -1},
                 {"initialFractionalValue": "33/100", "fractionalValue": "2/5", "sourceId": 406346325, "name": "2",
                  "winning": True, "change": 1}]},
    {"sourceId": 204228674, "structureType": 1, "marketId": 11, "marketName": "First set winner", "isLive": False,
     "fid": 204228674, "suspended": False, "id": 465500374, "marketGroup": "Home/Away", "marketPeriod": "1st set",
     "choices": [{"fractionalValue": "7/4", "name": "1"}, {"fractionalValue": "4/9", "name": "2"}]},
    {"sourceId": 204228674, "structureType": 2, "marketId": 12, "marketName": "Total games won", "choiceGroup": "22.5",
     "isLive": False, "fid": 204228674, "suspended": False, "id": 465500375, "marketGroup": "Total sets/games",
     "marketPeriod": "Extra time",
     "choices": [{"fractionalValue": "5/6", "name": "Over", "winning": False, "change": -1},
                 {"fractionalValue": "5/6", "name": "Under", "winning": True, "change": 1}]}],
    "eventId": 17511576, "liveStreamUrl": None}, "source": "live", "cacheHit": True}


def mercado(id_, nombre, choices, linea=None, grupo="", periodo="Match"):
    m = {"marketId": id_, "marketName": nombre, "marketGroup": grupo, "marketPeriod": periodo, "isLive": False,
         "suspended": False, "choices": [{"name": n, "fractionalValue": f} for n, f in choices]}
    if linea is not None:
        m["choiceGroup"] = str(linea)
    return m


class SP:
    """Doble de SportsAPIPro: registra las URL y responde calendario y cuotas grabados."""
    def __init__(self, eventos=None, cuerpo=None, status=200):
        self.urls, self.eventos, self.cuerpo, self.status = [], eventos or [], cuerpo, status

    def __call__(self, url):
        self.urls.append(url)
        if "/schedule/" in url:
            return 200, json.dumps({"events": self.eventos}).encode()
        return self.status, json.dumps(self.cuerpo or {}).encode()

    def de_cuotas(self):
        return [u for u in self.urls if "/odds/" in u]


def evento_sp(eid, local, visitante, inicio):
    return {"id": eid, "homeTeam": {"name": local}, "awayTeam": {"name": visitante},
            "startTimestamp": int(inicio.timestamp())}


# --- piezas puras ---------------------------------------------------------------------------------------------

def test_fraccion_a_decimal():
    assert csp.fraccion_a_decimal("7/4") == 2.75 and csp.fraccion_a_decimal("1/50") == 1.02
    assert csp.fraccion_a_decimal("EVS") == 2.0 and csp.fraccion_a_decimal("2.40") == 2.4
    assert csp.fraccion_a_decimal("1/0") is None and csp.fraccion_a_decimal("0/5") is None
    assert csp.fraccion_a_decimal(None) is None and csp.fraccion_a_decimal("abc") is None


def test_mercados_reales_de_tenis():
    ms = csp.mercados(TENIS_REAL)
    assert csp._ganador(ms) == {"1": 3.0, "2": 1.4}
    h = dict(key="winner", market="winner", selection="A")
    filas = csp.filas_item(ms, "tenis", h, "Jannik Sinner", "Carlos Alcaraz")
    assert [(f["side"], f["price_decimal"]) for f in filas] == [("A", 3.0), ("B", 1.4)]
    # Evento invertido respecto del sello: el «1» de SofaScore es nuestro jugador B.
    filas = csp.filas_item(ms, "tenis", h, "Jannik Sinner", "Carlos Alcaraz", invertido=True)
    assert [(f["side"], f["price_decimal"]) for f in filas] == [("A", 1.4), ("B", 3.0)]
    t = dict(key="games_total-0", market="games_total", selection="over", line=22.5)
    filas = csp.filas_item(ms, "tenis", t, "a", "b")
    assert {(f["name"], f["point"]) for f in filas} == {("Over", 22.5), ("Under", 22.5)}


def test_mercado_en_juego_o_suspendido_no_cuenta():
    doc = json.loads(json.dumps(TENIS_REAL))
    doc["data"]["markets"][0]["suspended"] = True
    assert csp._ganador(csp.mercados(doc)) is None
    doc["data"]["markets"][0].update(suspended=False, isLive=True)
    assert csp._ganador(csp.mercados(doc)) is None


@pytest.mark.parametrize("a,b,ok", [
    ("Carlos Alcaraz", "Alcaraz C.", True), ("Carlos Alcaraz", "Alcaraz, Carlos", True),
    ("Jannik Sinner", "Sinner J.", True), ("Carlos Alcaraz", "Alcaraz R.", False),
    ("Carlos Alcaraz", "Carlos Alcaraz Garfia", False), ("Sinner", "Sinner J.", False)])
def test_mismo_jugador(a, b, ok):
    assert csp.mismo_jugador(a, b) is ok


def test_busca_evento_unico_y_sin_adivinar():
    inicio = datetime(2026, 11, 10, 14, 0, tzinfo=UTC)
    uno = evento_sp(1, "Alcaraz C.", "Sinner J.", inicio)
    assert csp.busca_evento([uno], "Jannik Sinner", "Carlos Alcaraz", inicio, tenis=True) == (uno, True)
    assert csp.busca_evento([uno], "Carlos Alcaraz", "Jannik Sinner", inicio, tenis=True) == (uno, False)
    otro = evento_sp(2, "Alcaraz C.", "Sinner J.", inicio + timedelta(minutes=10))
    assert csp.busca_evento([uno, otro], "Carlos Alcaraz", "Jannik Sinner", inicio, tenis=True) is None
    lejos = evento_sp(3, "Alcaraz C.", "Sinner J.", inicio + timedelta(hours=2))
    assert csp.busca_evento([lejos], "Carlos Alcaraz", "Jannik Sinner", inicio, tenis=True) is None
    # Equipos (no tenis): nombre exacto y orden fijo.
    eq = evento_sp(4, "Boston Celtics", "New York Knicks", inicio)
    assert csp.busca_evento([eq], "Boston Celtics", "New York Knicks", inicio, tenis=False) == (eq, False)
    assert csp.busca_evento([eq], "New York Knicks", "Boston Celtics", inicio, tenis=False) is None


# --- cliente --------------------------------------------------------------------------------------------------

def test_cliente_archiva_y_para_en_429(tmp_path):
    estados = iter([(200, b"{}"), (429, b"{}"), (200, b"{}")])
    cli = csp.Cliente("k", call=lambda u: next(estados), clock=lambda: NOW, raiz=tmp_path / "idx")
    assert cli.get("tennis/schedule/2026-11-10", "calendario", "x")[1] == {}
    with pytest.raises(csp.SinCupo):
        cli.get("tennis/schedule/2026-11-11", "calendario", "y")
    with pytest.raises(csp.SinCupo):   # agotado: ya no se llama
        cli.get("tennis/schedule/2026-11-12", "calendario", "z")
    assert cli.peticiones == 2 and cli.db.execute("select count(*) from receipts").fetchone()[0] == 2


def test_cliente_tope_diario_propio(tmp_path):
    cli = csp.Cliente("k", call=lambda u: (200, b"{}"), clock=lambda: NOW, raiz=tmp_path / "idx", tope=2)
    cli.get("a", "k", "1")
    cli.get("b", "k", "2")
    with pytest.raises(csp.SinCupo):
        cli.get("c", "k", "3")


# --- cascada NBA / tenis ---------------------------------------------------------------------------------------

TIPOFF = datetime(2026, 10, 31, 20, 0, tzinfo=UTC)      # SportsAPIPro solo da prepartido: el partido debe ser futuro


def futuro(cs):
    cs[0]["games"][0]["tipoff_utc"] = TIPOFF.isoformat()
    return cs


def calendario_nba():
    return [evento_sp(777, "Boston Celtics", "New York Knicks", TIPOFF)]


def cuerpo_nba(total=1.91):
    return {"data": {"markets": [
        mercado(1, "Full time", [("1", "1/2"), ("2", "13/8")], grupo="Home/Away"),
        mercado(99, "Game total", [("Over", "10/11"), ("Under", "10/11")], linea=215.5, grupo="Total", periodo="Full time")]}}


def pasada(cache, red, sp, **kw):
    out = []
    info = {}
    cr.correr(key=kw.pop("key", "no-es-una-clave"), cache_path=str(cache), get=red, now=kw.pop("now", NOW), salida=out.append,
              sp_key="sp", sp_call=sp, sp_raiz=kw.pop("sp_raiz", None), info=info, ejecutar=True, **kw)
    return out, info


def overlay(archive, cs, cache):
    return cr.aplica_nba(cn.nba_overlay(archive, cs, now=NOW), cr.leer_cache(cache))["events"]["0022600099"]["quotes"]


def test_nivel2_resuelve_y_sportsapipro_no_se_toca(entorno):
    archive, cs, cache = entorno
    sp = SP(calendario_nba(), cuerpo_nba())
    pasada(cache, Red(), sp)
    assert sp.urls == []                                     # The Odds API la encontró: no se gasta el 3er nivel
    assert overlay(archive, cs, cache)["game_total||215.5"]["over"]["src"] == "the-odds-api"


def test_nivel3_cubre_lo_que_the_odds_api_no_encuentra(entorno):
    archive, cs, cache = entorno
    futuro(cs)
    sp = SP(calendario_nba(), cuerpo_nba())
    out, info = pasada(cache, Red(eventos=[]), sp)           # The Odds API sin el evento
    assert info["nuevas"] == 0 and info["nuevas_sportsapipro"] == 2      # ganador y total: PropLine no los tiene
    assert [u.split("/v2/")[1].split("?")[0] for u in sp.urls] == [
        "basketball/schedule/2026-10-31", "basketball/api/match/777/odds/pre-match"]
    q = overlay(archive, cs, cache)["game_total||215.5"]
    assert q["over"]["src"] == "sportsapipro" and q["over"]["post_sello"] is True
    assert q["over"]["price"] == pytest.approx(1 + 10 / 11, abs=1e-3) and q["over"]["book"] == "sofascore"
    # La recepción es la real (posterior al sello) y se conserva.
    assert pl.parse_time(q["over"]["as_of"]) == NOW and pl.parse_time(q["over"]["as_of"]) > SEALED
    g = overlay(archive, cs, cache)["winner||"]
    assert g["home"]["price"] == pytest.approx(1.5) and g["away"]["price"] == pytest.approx(1 + 13 / 8)


def test_nivel3_cuando_a_the_odds_api_se_le_acaban_los_creditos(entorno):
    archive, cs, cache = entorno
    futuro(cs)
    # El evento sí existe en The Odds API, pero pedir sus cuotas (20 créditos) dejaría el saldo bajo el suelo.
    red = Red(saldo=505, eventos=[oevento(commence_time=pl.stamp(TIPOFF))])
    sp = SP(calendario_nba(), cuerpo_nba())
    out, info = pasada(cache, red, sp)
    assert info["suelo"] is True and info["nuevas"] == 0 and info["nuevas_sportsapipro"] == 2
    assert any("pasa a SportsAPIPro" in x for x in out)


def test_sin_clave_de_the_odds_api_sportsapipro_corre(entorno):
    archive, cs, cache = entorno
    futuro(cs)
    red = Red()
    sp = SP(calendario_nba(), cuerpo_nba())
    cr.correr(key="", cache_path=str(cache), get=red, now=NOW, salida=lambda x: None, sp_key="sp", sp_call=sp,
              ejecutar=True)
    assert red.llamadas == [] and len(sp.de_cuotas()) == 1


def test_sin_ninguna_clave_no_hace_nada(entorno, monkeypatch):
    archive, cs, cache = entorno
    out = []
    cr.correr(key="", cache_path=str(cache), salida=out.append, sp_key="", ejecutar=True)
    assert out == ["sin ODDS_API_RESPALDO_KEY, SPORTSAPIPRO_KEY ni THERUNDOWN_API_KEY: no hay nada que hacer"]


def test_reintentos_acotados_no_queman_el_cupo(entorno):
    archive, cs, cache = entorno
    futuro(cs)
    sp = SP([], {})                                          # el evento nunca aparece
    for minutos in (0, 10, 30):                              # dentro de la hora: un solo intento
        pasada(cache, Red(eventos=[]), sp, now=NOW + timedelta(minutes=minutos))
    n1 = len(sp.urls)
    assert n1 >= 1
    pasada(cache, Red(eventos=[]), sp, now=NOW + timedelta(minutes=70))   # segundo (y último) intento
    n2 = len(sp.urls)
    assert n2 > n1
    pasada(cache, Red(eventos=[]), sp, now=NOW + timedelta(hours=5))
    assert len(sp.urls) == n2                                # agotados: ya no se pide más


def test_429_de_sportsapipro_corta_la_pasada(entorno, tmp_path):
    archive, cs, cache = entorno
    futuro(cs)
    llamadas = []

    def sp(url):
        llamadas.append(url)
        return 429, b"{}"
    out, info = pasada(cache, Red(eventos=[]), sp)
    assert info["nuevas_sportsapipro"] == 0 and len(llamadas) == 1 and any("429" in x for x in out)


def test_la_cache_de_sportsapipro_no_publica_y_el_ganador_de_tenis_se_ve():
    a, b = "Jannik Sinner", "Carlos Alcaraz"
    inicio = datetime(2026, 11, 10, 14, 0, tzinfo=UTC)
    sello = inicio - timedelta(hours=4)
    h = cr.Hueco("tenis", "T1", None, a, b, inicio, sello, [
        dict(key="winner", market="winner", odds_market="h2h", line=None, selection="A"),
        dict(key="games_total-0", market="games_total", odds_market="totals", line=22.5, selection="over"),
        dict(key="tiebreak-3", market="tiebreak", odds_market="x", line=None, selection="yes")])
    sp = SP([evento_sp(9, "Sinner J.", "Alcaraz C.", inicio)], TENIS_REAL)
    cli = csp.Cliente("k", call=sp, clock=lambda: sello + timedelta(hours=1))
    entries = {}
    assert cr.nivel3_sportsapipro(cli, [h], entries, {}, sello + timedelta(hours=1)) == 2   # sin hándicap/props
    out = cr.aplica_tenis(dict(events={"T1": {"winner": None, "games_total-0": None, "tiebreak-3": None}}), entries)
    q = out["events"]["T1"]
    assert q["winner"]["price"] == 3.0 and q["winner"]["side"] == "A" and q["winner"]["post_sello"] is True
    assert q["games_total-0"]["price"] == pytest.approx(1.8333, abs=1e-3) and q["tiebreak-3"] is None
    # La regla de publicación ignora lo post-sello: sin precio, el mercado no es publicable.
    feed = {"events": [{"id": "T1", "markets": [{"id": "winner-A", "probability": 0.6}]}]}
    assert regla_publicacion.publicables_tenis(feed, {"T1": {"winner-A": q["winner"]}}) == {}


def test_regla_ignora_cuota_post_sello():
    assert regla_publicacion._precio_publicable({"price": 1.9, "post_sello": True}) is None
    assert regla_publicacion._precio_publicable({"price": 1.9}) == 1.9
    assert regla_publicacion._precio_publicable(None) is None


def test_auto_con_tope_de_creditos_agotado_sportsapipro_sigue(entorno, monkeypatch):
    archive, cs, cache = entorno
    futuro(cs)
    s = cr.settings
    s.cuotas_respaldo_auto, s.cuotas_respaldo_auto_max, s.cuotas_respaldo_diario = True, 100, 0
    s.cuotas_respaldo_cache = str(cache)
    s.sportsapipro_key = None
    red = Red()
    assert cr.auto(key="k", get=red, now=NOW, alerta=lambda m: None)["estado"] == "tope_diario" and red.llamadas == []
    sp = SP(calendario_nba(), cuerpo_nba())
    r = cr.auto(key="k", get=red, now=NOW, alerta=lambda m: None, sp_key="sp", sp_call=sp, huecos_futbol=[])
    assert r["estado"] == "ok" and red.de_pago() == [] and len(sp.de_cuotas()) == 1
    assert overlay(archive, cs, cache)["game_total||215.5"]["over"]["src"] == "sportsapipro"


# --- fútbol (solo consulta) ------------------------------------------------------------------------------------

KO = datetime(2026, 11, 10, 19, 0, tzinfo=UTC)


def canon(x):
    return x.strip().lower()


def test_cuotas_de_cache_respeta_edad_pit_y_casas():
    e = dict(fuente="the-odds-api", captured_at=(KO - timedelta(hours=2)).isoformat(), rows=[
        dict(bookmaker="betano", market="h2h", selection="home", line=None, price=2.1),
        dict(bookmaker="betsson", market="h2h", selection="home", line=None, price=2.2),
        dict(bookmaker="pinnacle", market="h2h", selection="home", line=None, price=2.5),     # no es casa de suscriptores
        dict(bookmaker="betano", market="totals", selection="over", line=2.5, price=1.9)])
    r = rf.cuotas_de_cache({"M": e}, "M", KO, ("betano", "betsson"), canon)
    assert r["h2h:home:None"][:2] == (2.2, "betsson") and r["totals:over:2.5"][0] == 1.9
    assert rf.cuotas_de_cache({"M": e}, "M", KO - timedelta(hours=3), ("betano",), canon) == {}   # aún no existía
    assert rf.cuotas_de_cache({"M": e}, "M", KO + timedelta(hours=5), ("betano",), canon) == {}   # más de 6 h
    assert rf.cuotas_de_cache({}, "M", KO, ("betano",), canon) == {}
    s = dict(fuente="sportsapipro", captured_at=(KO - timedelta(hours=1)).isoformat(), rows=[
        dict(bookmaker="sofascore", market="h2h", selection="draw", line=None, price=3.4)])
    assert rf.cuotas_de_cache({"M|sp": s}, "M", KO, ("betano",), canon)["h2h:draw:None"][1] == "sofascore"
    # Si cotizan las dos, la casa de un suscriptor (The Odds API) gana y SportsAPIPro solo rellena lo que falta.
    s["rows"].append(dict(bookmaker="sofascore", market="h2h", selection="home", line=None, price=9.0))
    mezcla = rf.cuotas_de_cache({"M": e, "M|sp": s}, "M", KO, ("betano", "betsson"), canon)
    assert mezcla["h2h:home:None"][:2] == (2.2, "betsson") and mezcla["h2h:draw:None"][1] == "sofascore"


def test_filas_de_sportsapipro_futbol_respuesta_real():
    """Mercados y nombres de la respuesta REAL de FA Cup (partido 17364669, 9-nov-2026): periodo «Full-time»."""
    ft = "Full-time"
    ms = csp.mercados({"data": {"markets": [
        mercado(1, "Full time", [("1", "79/100"), ("X", "14/5"), ("2", "31/10")], grupo="1X2", periodo=ft),
        mercado(2, "Double chance", [("1X", "2/9"), ("X2", "10/11"), ("12", "1/4")], grupo="Double chance", periodo=ft),
        mercado(3, "1st half", [("1", "13/10"), ("X", "11/8"), ("2", "10/3")], grupo="1X2", periodo="1st half"),
        mercado(4, "Draw no bet", [("1", "4/11"), ("2", "2/1")], grupo="Draw no bet", periodo=ft),
        mercado(5, "Both teams to score", [("Yes", "8/13"), ("No", "6/5")], grupo="Both teams to score", periodo=ft),
        mercado(9, "Match goals", [("Over", "1/33"), ("Under", "14/1")], linea=0.5, grupo="Match goals", periodo=ft),
        mercado(9, "Match goals", [("Over", "4/6"), ("Under", "6/5")], linea=2.5, grupo="Match goals", periodo=ft),
        mercado(17, "Asian handicap", [("(-0.5) Plymouth Parkway", "33/40"), ("(0.5) Berkhamsted Town", "41/40")],
                grupo="Asian Handicap", periodo=ft),
        mercado(21, "Corners 2-Way", [("Over", "1/1"), ("Under", "8/11")], linea=10.5, grupo="Corners 2-Way", periodo=ft),
        mercado(6, "First team to score", [("No goal", "12/1")], grupo="First team to score", periodo=ft)]}})
    filas = rf._filas_sportsapipro(ms)
    claves = {(f["market"], f["selection"], f["line"]) for f in filas}
    assert claves == {("h2h", "home", None), ("h2h", "draw", None), ("h2h", "away", None),
                      ("totals", "over", 0.5), ("totals", "under", 0.5), ("totals", "over", 2.5), ("totals", "under", 2.5),
                      ("btts", "yes", None), ("btts", "no", None),
                      ("double_chance", "1X", None), ("double_chance", "X2", None), ("double_chance", "12", None),
                      ("corners", "over", 10.5), ("corners", "under", 10.5)}
    assert next(f for f in filas if f["selection"] == "home")["price"] == pytest.approx(1.79)
    assert next(f for f in filas if f["market"] == "totals" and f["line"] == 2.5 and f["selection"] == "over")["price"]         == pytest.approx(1 + 4 / 6, abs=1e-3)
    # La 1.ª parte y el hándicap no se confunden con el partido completo.
    assert rf._filas_sportsapipro(csp.mercados({"data": {"markets": [
        mercado(3, "1st half", [("1", "13/10"), ("X", "11/8"), ("2", "10/3")], periodo="1st half")]}})) == []
    assert rf._filas_sportsapipro(csp.mercados({"data": {"markets": [mercado(1, "Full time", [("1", "6/4")])]}})) == []


def test_baloncesto_respuesta_real_game_total():
    """Respuesta REAL NBA (Hawks-Lakers, 9-nov-2026): «Game total» marketId 18, periodo Match, línea en choiceGroup."""
    ms = csp.mercados({"data": {"markets": [
        mercado(1, "Full time", [("1", "21/25"), ("2", "99/100")], grupo="Home/Away"),
        mercado(3, "1st half", [("1", "50/57"), ("2", "50/53")], grupo="Home/Away", periodo="1st half"),
        mercado(16, "Point spread", [("(-1.5) Atlanta Hawks", "100/109"), ("(+1.5) Los Angeles Lakers", "100/111")],
                grupo="Point spread"),
        mercado(18, "Game total", [("Over", "10/11"), ("Under", "10/11")], linea=236.5, grupo="Over/Under")]}})
    t = dict(key="game_total||236.5", market="game_total", line=236.5)
    filas = csp.filas_item(ms, "nba", t, "Atlanta Hawks", "Los Angeles Lakers")
    assert {(f["name"], f["point"]) for f in filas} == {("Over", 236.5), ("Under", 236.5)}
    assert csp.filas_item(ms, "nba", dict(key="w", market="winner"), "Atlanta Hawks", "Los Angeles Lakers")[0]["price_decimal"]         == pytest.approx(1 + 21 / 25)


@pytest.fixture
def futbol(tmp_path, monkeypatch):
    from qf.ingest import odds_worker as ow
    from qf.ingest import sportsapipro_alineaciones as spa
    h = dict(match_id="M1", league_id="eu.epl", kickoff_utc=KO, odds_api_key="soccer_epl")
    eventos = [oevento(id="OE9", commence_time=KO.isoformat(), home_team="Arsenal", away_team="Chelsea")]
    libros = [dict(key="betano", markets=[dict(key="h2h", outcomes=[
        dict(name="Arsenal", price=2.0), dict(name="Chelsea", price=3.8), dict(name="Draw", price=3.3)])])]
    eventos[0]["bookmakers"] = libros
    monkeypatch.setattr(ow, "_markets_for", lambda k: "h2h")
    monkeypatch.setattr(ow, "match_meta", lambda ids: {"M1": dict(match_id="M1", kickoff_utc=KO, league_id="eu.epl")})
    monkeypatch.setattr(ow, "match_events", lambda evs, meta, otras=(): [(evs[0], "M1")] if evs else [])
    monkeypatch.setattr(spa, "abrir", lambda raiz: object())
    monkeypatch.setattr(spa, "carpeta", lambda: tmp_path)
    monkeypatch.setattr(rf, "settings", SimpleNamespace(
        cuotas_respaldo_cache=str(tmp_path / "c.json"), odds_api_respaldo_key="k", sportsapipro_key="s",
        artifact_dir=None, cuotas_sportsapipro_diario=0, odds_api_regions="eu", soft_books=("betano",)))
    return h, eventos, spa, tmp_path


class RedFutbol:
    def __init__(self, eventos, saldo=2000):
        self.eventos, self.saldo, self.llamadas = eventos, saldo, []

    def __call__(self, path, params):
        self.llamadas.append((path, dict(params)))
        if path == "/v4/sports":
            return 200, {"x-requests-remaining": str(self.saldo)}, []
        self.saldo -= 1
        return 200, {"x-requests-remaining": str(self.saldo), "x-requests-last": "1"}, self.eventos


def test_futbol_nivel2_una_peticion_por_liga(futbol):
    h, eventos, spa, tmp = futbol
    red = RedFutbol(eventos)
    out = rf.correr(ejecutar=True, get=red, now=KO - timedelta(hours=5), lista_huecos=[h], sp_key="", salida=lambda x: None)
    assert out["the_odds_api"] == 1 and [p for p, _ in red.llamadas if p != "/v4/sports"] == ["/v4/sports/soccer_epl/odds"]
    ent = rf.leer_cache(tmp / "cuotas_respaldo_futbol.json")
    assert ent["M1"]["fuente"] == "the-odds-api" and {r["selection"] for r in ent["M1"]["rows"]} == {"home", "away", "draw"}


def test_futbol_cae_a_sportsapipro_sin_creditos(futbol, monkeypatch):
    h, eventos, spa, tmp = futbol
    monkeypatch.setattr(spa, "event_id", lambda db, hh: 555)
    cuerpo = {"data": {"markets": [mercado(1, "Full time", [("1", "6/4"), ("X", "5/2"), ("2", "2/1")], grupo="1X2")]}}
    sp = SP(cuerpo=cuerpo)
    red = RedFutbol(eventos, saldo=500)                      # saldo en el suelo: The Odds API no se toca
    ahora = KO - timedelta(hours=5)
    out = rf.correr(ejecutar=True, get=red, now=ahora, lista_huecos=[h], sp_call=sp, salida=lambda x: None)
    assert out["the_odds_api"] == 0 and out["sportsapipro"] == 1
    assert [u.split("/v2/")[1] for u in sp.urls] == ["football/api/match/555/odds/pre-match"]
    ent = rf.leer_cache(tmp / "cuotas_respaldo_futbol.json")
    assert ent["M1|sp"]["fuente"] == "sportsapipro" and ent["M1|sp"]["captured_at"] == ahora.isoformat()
    assert "M1" not in ent


def test_futbol_sin_calendario_archivado_no_gasta_peticiones(futbol, monkeypatch):
    h, eventos, spa, tmp = futbol
    monkeypatch.setattr(spa, "event_id", lambda db, hh: None)
    sp = SP()
    out = rf.correr(ejecutar=True, get=RedFutbol([], saldo=500), now=KO - timedelta(hours=5), lista_huecos=[h],
                    sp_call=sp, salida=lambda x: None)
    assert out["sportsapipro"] == 0 and sp.urls == []


def test_futbol_partido_con_entrada_vigente_no_es_hueco(futbol):
    h, eventos, spa, tmp = futbol
    ahora = KO - timedelta(hours=5)
    filas = [dict(bookmaker="betano", market="h2h", selection=s, line=None, price=2.0) for s in ("home", "draw", "away")]
    rf.escribir_cache(tmp / "cuotas_respaldo_futbol.json", {"M1": dict(fuente="the-odds-api", captured_at=ahora.isoformat(),
                                                                       rows=filas)}, ahora)
    red = RedFutbol(eventos)
    out = rf.correr(ejecutar=True, get=red, now=ahora + timedelta(hours=1), lista_huecos=[h], sp_key="")
    assert out["estado"] == "sin_huecos" and red.llamadas == []


def test_futbol_sin_claves_no_hace_nada(futbol, monkeypatch):
    h, eventos, spa, tmp = futbol
    out = rf.correr(ejecutar=True, key="", sp_key="", lista_huecos=[h])
    assert out == {"estado": "sin_configuracion"}


def test_nivel3_no_pide_partidos_ya_empezados(entorno):
    archive, cs, cache = entorno                 # el partido del fixture empezó antes de NOW: sin prepartido que pedir
    sp = SP(calendario_nba(), cuerpo_nba())
    out, info = pasada(cache, Red(eventos=[]), sp)
    assert sp.urls == [] and info["nuevas_sportsapipro"] == 0


def test_futbol_casas_que_no_son_de_los_suscriptores_pasan_al_nivel_3(futbol, monkeypatch):
    h, eventos, spa, tmp = futbol
    eventos[0]["bookmakers"][0]["key"] = "leovegas_se"          # The Odds API cotiza, pero no es casa de los suscriptores
    monkeypatch.setattr(spa, "event_id", lambda db, hh: 555)
    cuerpo = {"data": {"markets": [mercado(1, "Full time", [("1", "6/4"), ("X", "5/2"), ("2", "2/1")], grupo="1X2")]}}
    sp = SP(cuerpo=cuerpo)
    out = rf.correr(ejecutar=True, get=RedFutbol(eventos), now=KO - timedelta(hours=5), lista_huecos=[h], sp_call=sp,
                    salida=lambda x: None)
    assert out["the_odds_api"] == 1 and out["sportsapipro"] == 1
    ent = rf.leer_cache(tmp / "cuotas_respaldo_futbol.json")
    assert set(ent) == {"M1", "M1|sp"}


def test_ficha_del_partido_lee_el_respaldo_y_propline_gana(futbol, monkeypatch):
    from qf.api import partido_mercados as pm
    import qf.config
    h, eventos, spa, tmp = futbol
    ahora = KO - timedelta(hours=3)
    filas = [dict(bookmaker="betano", market="h2h", selection=s, line=None, price=p)
             for s, p in (("home", 2.0), ("draw", 3.3), ("away", 3.8))]
    rf.escribir_cache(tmp / "cuotas_respaldo_futbol.json", {"M1": dict(fuente="the-odds-api",
                      captured_at=ahora.isoformat(), rows=filas)}, ahora)
    monkeypatch.setattr(rf, "ruta_cache", lambda cache_path=None: tmp / "cuotas_respaldo_futbol.json")
    monkeypatch.setattr(pm, "query", lambda sql, params=(): [{"hasta": ahora}])
    monkeypatch.setattr(qf.config, "settings", SimpleNamespace(soft_books=("betano",)))
    propline = {"h2h:home:None": (1.5, "bet365", ahora)}
    out = pm._con_respaldo("M1", dict(propline))
    assert out["h2h:home:None"][0] == 1.5 and out["h2h:draw:None"][:2] == (3.3, "betano")   # PropLine gana
    assert pm._con_respaldo("OTRO", {}) == {}
    monkeypatch.setattr(rf, "ruta_cache", lambda cache_path=None: tmp / "no_existe.json")
    assert pm._con_respaldo("M1", dict(propline)) == propline                                  # caché ausente: no rompe
