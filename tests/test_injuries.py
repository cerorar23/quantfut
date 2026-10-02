"""
`injuries.ingest_match` asigna cada baja a su lado comparando el id de equipo
de API-Football. Hasta el 2-oct-2026 lo comparaba con `matches.home_team_id`
(numeración interna, p. ej. 49060) en vez de con `teams.af_team_id` (1595):
nunca coincidía y se descartaron todas las bajas sin ningún aviso.
"""
from __future__ import annotations

from qf.ingest import injuries

MATCH = {"match_id": "us.mls:2026:seattlesoun-sportingkan:20261002",
         "home_team_id": 49060, "away_team_id": 49039,
         "home_af_team_id": 1595, "away_af_team_id": 1611, "af_id": "1490463"}


def _baja(team_id: int, player_id: int) -> dict:
    return {"team": {"id": team_id}, "player": {
        "id": player_id, "name": f"J{player_id}", "type": "Missing Fixture",
        "reason": "Injury"}}


def _ingesta(monkeypatch, resp: list[dict]) -> tuple[dict, list[tuple]]:
    insertados = []

    def execute(sql, params=None):
        insertados.append((sql, params))
        return 1

    monkeypatch.setattr(injuries.af, "get", lambda *a, **k: (resp, {}))
    monkeypatch.setattr(injuries.af, "check_quota", lambda meta: None)
    monkeypatch.setattr(injuries, "execute", execute)
    return injuries.ingest_match(MATCH), insertados


def test_las_bajas_se_asignan_por_el_id_de_api_football(monkeypatch):
    r, ins = _ingesta(monkeypatch, [_baja(1595, 1), _baja(1611, 2), _baja(1611, 3)])
    lados = [p[1] for sql, p in ins
             if "INSERT INTO injuries" in sql and "capture_log" not in sql]
    assert lados == ["home", "away", "away"]
    assert r["stored"] == 3


def test_el_log_registra_lo_guardado(monkeypatch):
    _, ins = _ingesta(monkeypatch, [_baja(1595, 1)])
    log = [p for sql, p in ins if "injuries_capture_log" in sql]
    assert log == [(MATCH["match_id"], 1)]


def test_una_baja_de_equipo_desconocido_no_se_descarta_en_silencio(monkeypatch, caplog):
    r, _ = _ingesta(monkeypatch, [_baja(9999, 1), _baja(1595, 2)])
    assert r["stored"] == 1
    assert r["discarded"] == 1
    assert "9999" in caplog.text


def test_pending_matches_trae_los_ids_de_api_football_de_los_equipos(monkeypatch):
    capturado = []
    monkeypatch.setattr(injuries, "query",
                        lambda sql, params=None: capturado.append(sql) or [])
    injuries.pending_matches()
    sql = capturado[0]
    assert "AS home_af_team_id" in sql and "AS away_af_team_id" in sql
