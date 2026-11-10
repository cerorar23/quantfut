"""Escalera de NBA y tenis con hándicap y total del partido, y escalera sin partidos de fútbol."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from qf.ingest import propline_shared as pl
from qf.publish import daily
from qf.publish import escalera as es
from qf.publish import escalera_datos as ed
from qf.publish import escalera_ext as ext

NOW = datetime(2026, 11, 10, 7, 30, tzinfo=timezone.utc)
INICIO = "2026-11-10T09:00:00Z"


def _salida(nombre, lado, precio, punto=None):
    return dict(name=nombre, side=lado, price=precio, point=punto, player_id=None,
                book_updated_at="2026-11-10T07:00:00Z", last_seen_at="2026-11-10T07:29:00Z")


def _mercado(clave, salidas):
    return dict(key=clave, period=None, team=None, line_type="main", outcomes=salidas)


def _casa(key, local, visit, *, h2h=None, spread=None, total=None):
    mercados = []
    if h2h:
        mercados.append(_mercado("h2h", [_salida(local, "home", h2h[0]), _salida(visit, "away", h2h[1])]))
    if spread:      # (línea del local, precio local, precio visitante)
        linea, pl_, pv = spread
        mercados.append(_mercado("spreads", [_salida(local, "home", pl_, linea), _salida(visit, "away", pv, -linea)]))
    if total:       # (línea, over, under)
        linea, o, u = total
        mercados.append(_mercado("totals", [_salida("Over", None, o, linea), _salida("Under", None, u, linea)]))
    return dict(key=key, markets=mercados)


def _archivo(tmp_path, ruta, cuerpo, ahora=NOW):
    def get(path, params, key):
        return 200, {"X-Daily-Remaining": "4900"}, json.dumps(cuerpo).encode()
    pl.Collector(tmp_path, "CLAVE", get=get, clock=lambda: ahora).capture(ruta)


@pytest.fixture
def ajustes(monkeypatch):
    monkeypatch.setattr(ext, "settings", replace(ext.settings, sharp_book="pinnacle", devig_method="shin"))


def _partido(id_, sport, local, visit, casas):
    return dict(id=id_, sport_key=sport, commence_time=INICIO, home_team=local, away_team=visit, bookmakers=casas)


def test_nba_hándicap_y_total_en_lineas_medias_con_consenso_y_la_mejor_cuota_de_todas_las_casas(tmp_path, ajustes):
    _archivo(tmp_path, "/v1/sports/basketball_nba/odds", [_partido("n1", "basketball_nba", "Celtics", "Wizards", [
        _casa("pinnacle", "Celtics", "Wizards", spread=(-7.5, -110, -110), total=(224.5, -110, -110)),
        _casa("bovada", "Celtics", "Wizards", spread=(-7.5, -105, -115), total=(224.5, -108, -112)),
        _casa("unibet", "Celtics", "Wizards", spread=(-7.5, -102, -118), total=(224.0, -110, -110)),   # línea entera
        _casa("strendus", "Celtics", "Wizards", spread=(-7.0, -110, -110))])])                        # línea entera
    ops = {(o.cand.market, o.cand.selection): o for o in ext.opciones(NOW, tmp_path)
           if o.cand.market in ("totals", "spreads")}
    assert set(ops) == {("totals", "over"), ("totals", "under"), ("spreads", "home"), ("spreads", "away")}
    assert ops[("totals", "over")].cand.line == 224.5 and ops[("totals", "under")].cand.line == 224.5
    assert ops[("spreads", "home")].cand.line == -7.5 and ops[("spreads", "away")].cand.line == 7.5
    assert ops[("spreads", "home")].price == pytest.approx(1 + 100 / 102) and ops[("spreads", "home")].book == "unibet"
    assert ops[("totals", "over")].price == pytest.approx(1 + 100 / 108)
    assert ops[("spreads", "home")].cand.prob + ops[("spreads", "away")].cand.prob == pytest.approx(1)
    assert 0.45 < ops[("totals", "over")].cand.prob < 0.55 and ops[("totals", "over")].deporte == "nba"


def test_las_lineas_alternativas_dan_los_candidatos_de_alta_probabilidad(tmp_path, ajustes):
    def alt(clave, salidas):
        m = _mercado(clave, salidas)
        m["line_type"] = "alternate"
        return m
    casas = []
    for key, (a, b) in (("pinnacle", (-260, 215)), ("bovada", (-250, 200))):
        c = _casa(key, "Celtics", "Wizards", spread=(-7.5, -110, -110))
        c["markets"].append(alt("spreads", [_salida("Celtics", "home", a, -3.5), _salida("Wizards", "away", b, 3.5)]))
        casas.append(c)
    _archivo(tmp_path, "/v1/sports/basketball_nba/odds", [_partido("n1", "basketball_nba", "Celtics", "Wizards", casas)])
    ops = {(o.cand.selection, o.cand.line): o for o in ext.opciones(NOW, tmp_path) if o.cand.market == "spreads"}
    assert set(ops) == {("home", -7.5), ("away", 7.5), ("home", -3.5), ("away", 3.5)}
    alta = ops[("home", -3.5)]
    assert 0.69 < alta.cand.prob < 0.75 and alta.price == pytest.approx(1 + 100 / 250)
    assert es.valida(alta, prob_min=es.PROB_MIN, prob_max=es.PROB_MAX) and not es.valida(ops[("home", -7.5)], prob_min=es.PROB_MIN)


def test_el_consenso_pide_dos_casas_y_sin_pinnacle_tambien_vale(tmp_path, ajustes):
    _archivo(tmp_path, "/v1/sports/basketball_nba/odds", [
        _partido("n1", "basketball_nba", "A", "B", [_casa("bovada", "A", "B", total=(220.5, -110, -110))]),
        _partido("n2", "basketball_nba", "C", "D", [_casa("bovada", "C", "D", total=(220.5, -110, -110)),
                                                    _casa("unibet", "C", "D", total=(220.5, -112, -108))])])
    assert {o.match_id for o in ext.opciones(NOW, tmp_path) if o.cand.market == "totals"} == {"nba:n2"}


def test_tenis_guarda_total_y_handicap_de_juegos_con_los_nombres_del_parley(tmp_path, ajustes):
    _archivo(tmp_path, "/v1/sports/tennis/odds", [_partido("t1", "tennis_atp", "Sinner", "Rival", [
        _casa("pinnacle", "Sinner", "Rival", h2h=(-1500, 800), spread=(-4.5, -120, 100), total=(21.5, -110, -110)),
        _casa("bovada", "Sinner", "Rival", h2h=(-1400, 750), spread=(-4.5, -125, 105), total=(21.5, -115, -105))])])
    ops = {(o.cand.market, o.cand.selection): o for o in ext.opciones(NOW, tmp_path)}
    assert {k for k in ops if k[0] != "h2h"} == {("total_games", "over"), ("total_games", "under"),
                                                 ("handicap_games", "home"), ("handicap_games", "away")}
    assert ops[("handicap_games", "away")].cand.line == 4.5 and ops[("total_games", "over")].deporte == "tenis"
    assert all(es.valida(o, prob_min=0.0) or o.price < es.CUOTA_MIN or o.price > es.CUOTA_MAX for o in ops.values())
    assert "total_games" in es.MERCADOS_RETO and "handicap_games" in es.MERCADOS_RETO


def _paso(**kw):
    return {"deporte": "nba", "evento_id": "n1", "evento_local": "Los Angeles Lakers", "evento_visitante": "Detroit Pistons",
            "evento_inicio": NOW - timedelta(hours=8), "book": "bovada", "market": "spreads", "selection": "home",
            "line": -7.5, **kw}


def _resultados(tmp_path, filas):
    def casa(key, f):
        return dict(key=key, markets=[
            dict(key="spreads", period=None, team=None, outcomes=[
                dict(name=f["local"], point=-7.5, resolution=f["res"]), dict(name=f["visit"], point=7.5, resolution=None),
                dict(name=f["local"], point=-3.5, resolution="lost")]),
            dict(key="totals", period=None, team=None, outcomes=[
                dict(name="Over", point=220.5, resolution="won"), dict(name="Under", point=220.5, resolution="lost")])])
    _archivo(tmp_path, "/v1/sports/basketball_nba/events/n1/results",
             dict(id="n1", status="final", bookmakers=[casa(k, f) for k, f in filas.items()]))


def test_liquida_el_handicap_por_linea_y_por_nombre_aunque_la_casa_lo_escriba_distinto(tmp_path, ajustes):
    _resultados(tmp_path, {"bovada": dict(local="LA Lakers", visit="DET Pistons", res="won"),
                           "pinnacle": dict(local="Los Angeles Lakers", visit="Detroit Pistons", res="lost")})
    assert ext.resultado(_paso(), NOW, tmp_path) == ("win", None, None, None)
    assert ext.resultado(_paso(line=-3.5), NOW, tmp_path) == ("loss", None, None, None)   # solo cuenta la línea del escalón


def test_liquida_el_total_y_usa_las_demas_casas_si_coinciden(tmp_path, ajustes):
    _resultados(tmp_path, {"unibet": dict(local="A", visit="B", res="won"), "codere": dict(local="A", visit="B", res="won")})
    assert ext.resultado(_paso(market="totals", selection="over", line=220.5), NOW, tmp_path) == ("win", None, None, None)
    assert ext.resultado(_paso(market="totals", selection="under", line=220.5), NOW, tmp_path) == ("loss", None, None, None)
    otra = tmp_path / "discrepan"
    _resultados(otra, {"unibet": dict(local="A", visit="B", res="won"), "codere": dict(local="A", visit="B", res="lost")})
    assert ext.resultado(_paso(), NOW, otra) is None            # ni su casa ni Pinnacle, y las demás no coinciden


def test_textos_de_nba_y_tenis():
    assert ed.texto("totals", "over", 224.5, "A", "B", "nba") == "Más de 224,5 puntos"
    assert ed.texto("spreads", "away", 7.5, "A", "B", "nba") == "B +7,5 (hándicap de puntos)"
    assert ed.texto("total_games", "under", 21.5, "A", "B", "tenis") == "Menos de 21,5 juegos"
    assert ed.texto("handicap_games", "home", -4.5, "A", "B", "tenis") == "A -4,5 (hándicap de juegos)"
    assert ed.texto("totals", "over", 2.5, "A", "B") == "Más de 2,5 goles"        # fútbol, igual que antes


# ---------------------------------------------------------------- sin fútbol


@pytest.fixture
def sin_futbol(monkeypatch):
    orden = []
    monkeypatch.setattr(daily, "generate_predictions", lambda: [])
    monkeypatch.setattr(daily, "_sharp_only_upcoming", lambda hours=36: [])
    monkeypatch.setattr(daily, "seal", lambda: orden.append("seal") or {"chain_sha256": "ab" * 32})
    monkeypatch.setattr(daily.tg, "alert", lambda m: orden.append("alerta"))
    return orden


def test_sin_predicciones_de_futbol_la_escalera_se_elige_y_el_lote_se_sella(monkeypatch, sin_futbol):
    monkeypatch.setattr(daily, "_escalera", lambda: sin_futbol.append("escalera") or {"estado": "elegido", "plan": [{"reto_id": 1}]})
    out = daily.run()
    assert sin_futbol == ["alerta", "escalera", "seal"]            # elegir ANTES de sellar
    assert out["predictions"] == 0 and out["sealed"] is True and out["escalera"]["estado"] == "elegido"


def test_sin_predicciones_ni_escalon_no_se_sella_nada(monkeypatch, sin_futbol):
    monkeypatch.setattr(daily, "_escalera", lambda: sin_futbol.append("escalera") or {"estado": "sin_candidato", "plan": []})
    out = daily.run()
    assert "seal" not in sin_futbol and out["sealed"] is False and out["predictions"] == 0


def test_si_el_sello_falla_con_escalon_se_avisa(monkeypatch, sin_futbol):
    monkeypatch.setattr(daily, "_escalera", lambda: {"estado": "elegido", "plan": [{"reto_id": 1}]})
    monkeypatch.setattr(daily, "seal", lambda: {})
    daily.run()
    assert sin_futbol.count("alerta") == 2                           # sin predicciones + escalón sin sellar
