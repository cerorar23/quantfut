"""Calendario y resultados desde el archivo de PropLine: sin red ni base."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from qf.ingest import propline_partidos as pp

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
LIGA = dict(league_id="gb.premier_league", odds_api_key="soccer_epl", sport="soccer_epl",
            season_style="european", cross_league=False)


def ev(eid, status, home="Arsenal", away="Chelsea", ko=NOW - timedelta(hours=4), hs=None, as_=None):
    return dict(id=eid, status=status, home_team=home, away_team=away,
                commence_time=ko.isoformat().replace("+00:00", "Z"), home_score=hs, away_score=as_)


@pytest.mark.parametrize("hs,as_,esperado", [
    (2, 1, (2, 1)), ("3", "0", (3, 0)), (None, 1, None), (True, 0, None), (-1, 0, None), ("2.5", 1, None)])
def test_marcador_solo_enteros(hs, as_, esperado):
    assert pp._marcador(dict(home_score=hs, away_score=as_)) == esperado


@pytest.fixture
def sql(monkeypatch):
    log = []
    monkeypatch.setattr(pp, "execute", lambda q, p=(): log.append((" ".join(q.split()), p)) or 1)
    monkeypatch.setattr(pp, "record_health", lambda *a, **k: None)
    monkeypatch.setattr(pp, "_ligas", lambda: [dict(LIGA)])
    return log


def test_resultados_cierra_anula_y_deja_abierto(monkeypatch, sql):
    ko = NOW - timedelta(hours=4)
    pend = [dict(match_id="m1", league_id=LIGA["league_id"], kickoff_utc=ko, home_team_id=1, away_team_id=2, propline_id="10"),
            dict(match_id="m2", league_id=LIGA["league_id"], kickoff_utc=ko, home_team_id=3, away_team_id=4, propline_id="11"),
            dict(match_id="m3", league_id=LIGA["league_id"], kickoff_utc=ko, home_team_id=5, away_team_id=6, propline_id="12"),
            dict(match_id="m4", league_id=LIGA["league_id"], kickoff_utc=ko, home_team_id=7, away_team_id=8, propline_id="99")]
    monkeypatch.setattr(pp, "query", lambda q, p=(): [] if "AS pid" in q else pend)
    eventos = [ev("10", "final", hs=2, as_=0), ev("11", "cancelled"), ev("12", "in_progress", hs=1, as_=1)]
    monkeypatch.setattr(pp, "_scores", lambda sport, now: (eventos, {"received_at": "x"}))
    monkeypatch.setattr(pp, "_corners", lambda sport, eid, now: (7, 3) if eid == "10" else (None, None))
    from qf.ingest import results
    anulados = []
    monkeypatch.setattr(results, "_void_picks", anulados.append)
    import qf.eval.clv as clv
    monkeypatch.setattr(clv, "settle_pending", lambda: {"ok": 1})
    out = pp.resultados(NOW)
    assert (out["cerrados"], out["anulados"], out["abiertos"], out["sin_evento"]) == (1, 1, 1, 1)
    assert out["corners"] == 1 and out["settled"] == {"ok": 1}
    cierre = [p for q, p in sql if q.startswith("UPDATE matches SET status = 'finished'")]
    assert cierre == [(2, 0, 7, 3, "10", "m1")]
    assert ("UPDATE matches SET status = 'postponed' WHERE match_id = %s", ("m2",)) in sql
    assert anulados == ["m2"]


def test_resultados_sin_archivo_no_cierra_nada(monkeypatch, sql):
    pend = [dict(match_id="m1", league_id=LIGA["league_id"], kickoff_utc=NOW - timedelta(hours=4),
                 home_team_id=1, away_team_id=2, propline_id=None)]
    monkeypatch.setattr(pp, "query", lambda q, p=(): pend)
    monkeypatch.setattr(pp, "_scores", lambda sport, now: ([], None))
    out = pp.resultados(NOW)
    assert out["cerrados"] == 0 and out["sin_evento"] == 1 and sql == []


def test_evento_sin_id_exige_equipos_y_unico(monkeypatch):
    p = dict(propline_id=None, kickoff_utc=NOW, home_team_id=1, away_team_id=2)
    ids = {"Arsenal": 1, "Chelsea": 2, "Spurs": 3}
    monkeypatch.setattr(pp, "equipo", lambda liga, n, registrar=True: ids.get(n))
    assert pp._evento_de(LIGA, p, [ev("1", "final", ko=NOW)])["id"] == "1"
    assert pp._evento_de(LIGA, p, [ev("1", "final", ko=NOW), ev("2", "final", ko=NOW + timedelta(hours=2))]) is None
    assert pp._evento_de(LIGA, p, [ev("1", "final", ko=NOW + timedelta(days=3))]) is None
    assert pp._evento_de(LIGA, p, [ev("1", "final", home="Spurs", ko=NOW)]) is None


def test_calendario_inserta_reprograma_y_no_crea_equipos(monkeypatch, sql):
    futuro = NOW + timedelta(days=2)
    eventos = [ev("20", "upcoming", ko=futuro), ev("21", "upcoming", home="Spurs", ko=futuro),
               ev("22", "upcoming", home="Desconocido", ko=futuro), ev("23", "final", ko=NOW - timedelta(hours=5)),
               ev("24", "upcoming", home="Spurs", away="Arsenal", ko=futuro)]
    monkeypatch.setattr(pp, "_scores", lambda sport, now: (eventos, {"received_at": "x"}))
    ids = {"Arsenal": 1, "Chelsea": 2, "Spurs": 3}
    monkeypatch.setattr(pp, "equipo", lambda liga, n, registrar=True: ids.get(n))
    existentes = {("21",): dict(match_id="e21", kickoff_utc=futuro - timedelta(hours=3), status="scheduled",
                                external_ids={"propline": "21"}),
                  ("24",): dict(match_id="e24", kickoff_utc=futuro, status="finished", external_ids={})}
    monkeypatch.setattr(pp, "_partido", lambda liga, e, h, a, ko: existentes.get((e["id"],)))
    monkeypatch.setattr(pp, "_partido_por_pareja", lambda liga, e, ko: None)
    monkeypatch.setattr(pp, "_no_dar_de_alta", lambda *a: None)
    monkeypatch.setattr(pp, "query", lambda q, p=(): [dict(team_id=1, canonical_name="Arsenal"),
                                                     dict(team_id=2, canonical_name="Chelsea")])
    out = pp.calendario(NOW)
    assert (out["insertados"], out["reprogramados"], out["sin_resolver"]) == (1, 1, 1)
    alta = [p for q, p in sql if q.startswith("INSERT INTO matches")]
    assert len(alta) == 1 and alta[0][0].startswith("gb.premier_league:2627:arsenal-chelsea:")
    assert alta[0][-1] == "20"
    assert ("UPDATE matches SET kickoff_utc = %s, status = 'scheduled' WHERE match_id = %s", (futuro, "e21")) in sql
    assert ("DELETE FROM odds_capture_log WHERE match_id = %s", ("e21",)) in sql
    assert not any("e24" in str(p) for q, p in sql)
    assert not any("INSERT INTO teams" in q for q, p in sql)


def test_pareja_exige_los_dos_nombres_y_un_solo_evento():
    p = dict(kickoff_utc=NOW, home_team_id=1, away_team_id=2)
    nombres = {1: {"man city", "manchester city"}, 2: {"coventry"}}
    city = ev("1", "final", home="Manchester City", away="Coventry City", ko=NOW)
    united = ev("2", "final", home="Manchester United", away="Fulham FC", ko=NOW)
    assert pp.por_pareja([city, united], p, nombres)["id"] == "1"
    # Solo el local parecido no basta.
    assert pp.por_pareja([united], p, nombres) is None
    # Dos eventos que encajan: no se adivina.
    assert pp.por_pareja([city, dict(city, id="3")], p, nombres) is None
    assert pp.por_pareja([dict(city, commence_time="2026-10-28T12:00:00Z")], p, nombres) is None


def test_resultado_por_pareja_aprende_alias_y_no_reusa_eventos(monkeypatch):
    p = dict(propline_id=None, kickoff_utc=NOW, home_team_id=1, away_team_id=2)
    monkeypatch.setattr(pp, "equipo", lambda liga, n, registrar=True: None)
    monkeypatch.setattr(pp, "_nombres", lambda ids: {1: {"aston villa"}, 2: {"man city", "manchester city"}})
    aprendidos = []
    monkeypatch.setattr(pp, "register_alias", lambda a, s, t: aprendidos.append((a, s, t)))
    evento = ev("7", "final", home="Aston Villa", away="Manchester City", ko=NOW)
    assert pp._evento_de(LIGA, p, [evento], usados={"7"}) is None and not aprendidos
    assert pp._evento_de(LIGA, p, [evento])["id"] == "7"
    assert aprendidos == [("Aston Villa", "propline", 1), ("Manchester City", "propline", 2)]


def test_no_se_crea_cruce_invertido_duplicado_ni_difuso(monkeypatch):
    ids = {"Toronto FC": 1, "Philadelphia Union": 2, "Philly": 2}
    exactos = {"Toronto FC": 1, "Philadelphia Union": 2}
    monkeypatch.setattr(pp, "equipo", lambda liga, n, registrar=True: ids.get(n))
    monkeypatch.setattr(pp, "exacto", lambda liga, n: exactos.get(n))
    ko = NOW + timedelta(days=12)
    nuevo = ev("1", "upcoming", home="Toronto FC", away="Philadelphia Union", ko=ko)
    monkeypatch.setattr(pp, "query_one", lambda q, p=(): None)
    assert pp._no_dar_de_alta(LIGA, nuevo, [nuevo], 1, 2, ko) is None
    gemelo = ev("2", "upcoming", home="Philadelphia Union", away="Toronto FC", ko=ko)
    assert pp._no_dar_de_alta(LIGA, nuevo, [nuevo, gemelo], 1, 2, ko) == "evento_gemelo"
    difuso = dict(nuevo, away_team="Philly")
    assert pp._no_dar_de_alta(LIGA, difuso, [difuso], 1, 2, ko) == "nombre_no_exacto"
    vistos = []
    monkeypatch.setattr(pp, "query_one", lambda q, p=(): vistos.append(p) or {"x": 1})
    assert pp._no_dar_de_alta(LIGA, nuevo, [nuevo], 1, 2, ko) == "cruce_ya_existe"
    assert vistos[0][1:5] == (1, 2, 2, 1)   # busca los dos sentidos


def test_copa_solo_acepta_nombre_exacto(monkeypatch):
    copa = dict(LIGA, league_id="eu.ucl", cross_league=True)
    registrados = []
    monkeypatch.setattr(pp, "_record_unresolved", lambda *a: registrados.append(a))
    monkeypatch.setattr(pp, "match_team", lambda n, s, l: (5, "rangers", 92.0))
    assert pp.equipo(copa, "Angers") is None and registrados
    monkeypatch.setattr(pp, "match_team", lambda n, s, l: (5, "rangers", 100.0))
    assert pp.equipo(copa, "Rangers") == 5
    monkeypatch.setattr(pp, "match_team", lambda n, s, l: (7, "hull city", 91.0))
    assert pp.equipo(LIGA, "Hull City AFC") == 7
    # Un alias aprendido por pareja vale también en copa (es exacto).
    monkeypatch.setattr(pp, "match_team", lambda n, s, l: (9, "x", 100.0) if s == "propline" else (None, None, 0.0))
    assert pp.equipo(copa, "Olympique Lyonnais") == 9


def test_los_jobs_de_resultados_y_calendario_usan_propline(monkeypatch):
    from qf.ingest import fixtures, results
    monkeypatch.setattr(pp, "resultados", lambda hours_back=72: {"via": "propline", "h": hours_back})
    monkeypatch.setattr(pp, "calendario", lambda: {"via": "propline"})
    assert results.close_recent() == {"via": "propline", "h": 72}
    assert fixtures.run() == {"via": "propline"}


def test_casas_blandas_solo_cerca_y_cada_pocas_horas(monkeypatch):
    from qf.ingest import propline_ingest as pi
    monkeypatch.setattr(pi, "settings", SimpleNamespace(sharp_book="pinnacle", soft_books=("onexbet", "coderemx"),
                                                       propline_soft_horizon_hours=48, propline_soft_every_hours=3))
    obs = datetime(2026, 10, 25, 9, 7, tzinfo=timezone.utc)
    assert pi.soft_allowed(obs, obs + timedelta(hours=20)) == {"pinnacle", "1xbet", "coderemx"}
    assert pi.soft_allowed(obs, obs + timedelta(hours=60)) == {"pinnacle"}
    assert pi.soft_allowed(obs + timedelta(hours=1), obs + timedelta(hours=20)) == {"pinnacle"}
