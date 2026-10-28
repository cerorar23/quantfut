"""NBA y tenis en la escalera desde el archivo PropLine compartido (publish/escalera_ext.py)."""
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from qf.ingest import propline_shared as pl
from qf.publish import escalera as es
from qf.publish import escalera_ext as ext

NOW = datetime(2026, 10, 28, 7, 30, tzinfo=timezone.utc)


def _salida(nombre, lado, precio):
    return dict(name=nombre, side=lado, price=precio, point=None, player_id=None,
                book_updated_at="2026-10-28T07:00:00Z", last_seen_at="2026-10-28T07:29:00Z")


def _casa(key, local, visit, p_local, p_visit):
    return dict(key=key, markets=[dict(key="h2h", period=None, team=None, line_type="main",
                outcomes=[_salida(local, "home", p_local), _salida(visit, "away", p_visit)])])


def _partido(id_, sport, local, visit, casas, inicio="2026-10-28T09:00:00Z"):
    return dict(id=id_, sport_key=sport, commence_time=inicio, home_team=local, away_team=visit,
                bookmakers=casas)


def _archivo(tmp_path, ruta, cuerpo, ahora=NOW):
    def get(path, params, key):
        return 200, {"X-Daily-Remaining": "4900"}, json.dumps(cuerpo).encode()
    pl.Collector(tmp_path, "CLAVE", get=get, clock=lambda: ahora).capture(ruta)


@pytest.fixture
def ajustes(monkeypatch):
    s = replace(ext.settings, sharp_book="pinnacle", soft_books=("bovada", "strendus"),
                devig_method="shin")
    monkeypatch.setattr(ext, "settings", s)


def test_tenis_y_nba_con_pinnacle_sin_margen_y_la_mejor_cuota_de_la_lista(tmp_path, ajustes):
    _archivo(tmp_path, "/v1/sports/tennis/odds", [
        _partido("t1", "tennis_atp_paris", "Jannik Sinner", "Qualifier X", [
            _casa("pinnacle", "Jannik Sinner", "Qualifier X", -1600, 900),
            _casa("bovada", "Jannik Sinner", "Qualifier X", -1400, 750),
            _casa("strendus", "Jannik Sinner", "Qualifier X", -2000, 800),
            _casa("unibet", "Jannik Sinner", "Qualifier X", -1000, 600)]),     # fuera de la lista
        _partido("t2", "tennis_wta", "A", "B", [_casa("bovada", "A", "B", -900, 500)])])  # sin Pinnacle
    _archivo(tmp_path, "/v1/sports/basketball_nba/odds", [
        _partido("n1", "basketball_nba", "Boston Celtics", "Washington Wizards", [
            _casa("pinnacle", "Boston Celtics", "Washington Wizards", -900, 600),
            _casa("bovada", "Boston Celtics", "Washington Wizards", -800, 550)]),
        _partido("n2", "basketball_nba", "C", "D", [_casa("pinnacle", "C", "D", -900, 600),
                                                    _casa("bovada", "C", "D", -800, 550)],
                 inicio="2026-10-28T18:00:00Z")])               # después de la próxima pasada
    ops = {(o.match_id, o.cand.selection): o for o in ext.opciones(NOW, tmp_path)}
    assert set(ops) == {("tenis:t1", "home"), ("tenis:t1", "away"),
                        ("nba:n1", "home"), ("nba:n1", "away")}
    sinner = ops[("tenis:t1", "home")]
    assert sinner.deporte == "tenis" and sinner.book == "bovada" and sinner.price == pytest.approx(1 + 100 / 1400)
    assert 0.9 < sinner.cand.prob < 0.95 and sinner.evento[1:2] == ("tennis_atp_paris",)
    assert sinner.evento[3:] == ("Jannik Sinner", "Qualifier X") and sinner.odds_source == "propline"
    # Tope por deporte: el tenis llega a 97 %, la NBA no pasa de 95 %.
    assert es.PROB_MAX_DEPORTE["tenis"] == 0.97 and es.PROB_MAX_DEPORTE["nba"] == es.PROB_MAX


def test_sin_archivo_no_hay_candidatos_ni_se_crea_nada(tmp_path):
    vacio = tmp_path / "no_existe"
    assert ext.opciones(NOW, vacio) == [] and not vacio.exists()


def _paso(**kw):
    return {"deporte": "tenis", "evento_id": "t1", "selection": "home", "book": "bovada",
            "evento_local": "Jannik Sinner", "evento_visitante": "Qualifier X",
            "evento_inicio": NOW - timedelta(hours=8), **kw}


def _resultados(tmp_path, bovada="won", pinnacle="won", ahora=NOW):
    def casa(key, res):
        return dict(key=key, markets=[dict(key="h2h", period=None, team=None, outcomes=[
            dict(name="Jannik Sinner", resolution=res), dict(name="Qualifier X", resolution=None)])])
    _archivo(tmp_path, "/v1/sports/tennis/events/t1/results",
             dict(id="t1", status="final", bookmakers=[casa("bovada", bovada), casa("pinnacle", pinnacle)]),
             ahora)


def test_liquida_con_la_calificacion_de_la_casa_del_escalon(tmp_path, ajustes):
    _resultados(tmp_path, bovada="void", pinnacle="won")       # retirada: la casa la anula
    assert ext.resultado(_paso(), NOW, tmp_path) == ("void", None, None, None)
    otra = tmp_path / "otra"
    _resultados(otra, bovada=None, pinnacle="lost")
    assert ext.resultado(_paso(), NOW, otra) == ("loss", None, None, None)


def test_sin_calificacion_espera_y_pasado_el_margen_es_nulo(tmp_path, ajustes):
    assert ext.resultado(_paso(), NOW, tmp_path) is None
    viejo = _paso(evento_inicio=NOW - ext.MARGEN_SIN_RESULTADO - timedelta(hours=1))
    assert ext.resultado(viejo, NOW, tmp_path) == ("void", None, None, None)


def test_un_reto_puede_mezclar_tenis_y_futbol_y_el_anterior_solo_futbol():
    tenis = es.Opcion("tenis:t1", es.Candidato("h2h", "home", None, 0.96), 1.04, "bovada", deporte="tenis")
    futbol = es.Opcion("eng.1:m1", es.Candidato("h2h", "home", None, 0.86), 1.12, "bet365")
    plan = es.planificar([], [], [tenis, futbol])
    assert [o.match_id for o in plan[0][2]] == ["tenis:t1", "eng.1:m1"]       # 0,96 · 0,86 ≥ 0,80
    anterior = es.Abierto(5, 1, 3, prob_objetivo=None, cuota_min=1.03, cuota_max=1.40)
    assert es.elegir([tenis, futbol], anterior).match_id == "eng.1:m1"
