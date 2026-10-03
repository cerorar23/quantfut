"""
Carga de resultados de Champions y Europa League que faltan (dic-2024 → hoy).

`worldfootballR_data` dejó de publicar las copas en dic-2024 (README,
corrección 2026-10-02). Se recuperan de API-Football por el camino ya
probado: insertar como programados y que `results.close_recent()` los
cierre. Lo que fijan estos tests:
  - se pide la temporada y el rango que se dice, no la temporada en curso;
  - al cargar hacia atrás no se duplica un partido que ya existe por otra
    fuente (mismos equipos, ±36 h), porque `matches` no tiene clave natural;
  - en copa NUNCA se da de alta un equipo (CLAUDE.md);
  - el ensayo en seco no escribe nada.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from qf.ingest import fixtures

COPA = {"league_id": "eu.ucl", "api_football_id": 2, "season_style": "european",
        "cross_league": True}
DESDE = datetime(2024, 12, 13, tzinfo=timezone.utc)
HASTA = datetime(2026, 10, 2, tzinfo=timezone.utc)


def _fx(fid: int, fecha: str, local: str, visitante: str, estado: str = "FT") -> dict:
    return {"fixture": {"id": fid, "date": fecha, "status": {"short": estado}},
            "teams": {"home": {"name": local}, "away": {"name": visitante}}}


@pytest.fixture
def api(monkeypatch):
    llamadas = []

    def get(endpoint, params):
        llamadas.append((endpoint, params))
        return ([_fx(1, "2025-02-11T20:00:00+00:00", "Real Madrid", "Manchester City"),
                 _fx(2, "2025-02-12T20:00:00+00:00", "Celtic", "Bayern München")],
                {"empty": False})

    monkeypatch.setattr(fixtures.af, "get", get)
    monkeypatch.setattr(fixtures.af, "check_quota", lambda meta: None)
    return llamadas


def test_pide_la_temporada_y_el_rango_indicados(api, monkeypatch):
    monkeypatch.setattr(fixtures, "_resolve", lambda lg, name: None)
    fixtures.ingest_league(COPA, desde=DESDE, season=2024, hasta=HASTA)
    _, params = api[0]
    assert params["season"] == 2024
    assert params["from"] == "2024-12-13" and params["to"] == "2026-10-02"


def test_al_cargar_hacia_atras_no_duplica(api, monkeypatch):
    ids = {"Real Madrid": 1, "Manchester City": 2, "Celtic": None, "Bayern München": 3}
    monkeypatch.setattr(fixtures, "_resolve", lambda lg, name: ids[name])
    insertados = []
    monkeypatch.setattr(fixtures, "execute",
                        lambda sql, params=None: insertados.append(params) or 1)

    def query_one(sql, params=None):
        if "external_ids ->> 'api_football'" in sql:
            return None
        if "kickoff_utc BETWEEN" in sql:
            return {"match_id": "ya-estaba"}      # existe por otra fuente
        return {"canonical_name": "x"}

    monkeypatch.setattr(fixtures, "query_one", query_one)
    r = fixtures.ingest_league(COPA, desde=DESDE, season=2024, hasta=HASTA)
    assert insertados == []
    assert r["duplicated"] == 1 and r["unresolved"] == 1


def test_en_copa_no_se_da_de_alta_ningun_equipo(api, monkeypatch):
    altas = []
    monkeypatch.setattr(fixtures, "resolve_or_register",
                        lambda *a, **k: altas.append(a) or 99)
    monkeypatch.setattr(fixtures, "match_team", lambda raw, src, lg: (None, None, 0.0))
    monkeypatch.setattr(fixtures, "_record_unresolved", lambda *a, **k: None)
    fixtures.ingest_league(COPA, desde=DESDE, season=2024, hasta=HASTA)
    assert altas == []


def test_el_ensayo_no_escribe_y_cuenta(api, monkeypatch):
    def prohibido(*a, **k):
        raise AssertionError("el ensayo escribió en la base")

    monkeypatch.setattr(fixtures, "execute", prohibido)
    monkeypatch.setattr(fixtures, "_record_unresolved", prohibido)
    monkeypatch.setattr(fixtures, "query", lambda sql, params=None: [COPA])
    monkeypatch.setattr(fixtures, "query_one", lambda sql, params=None: None)
    exacto = {"real madrid": 1, "manchester city": 2, "bayern munchen": 3}
    monkeypatch.setattr(fixtures, "match_team", lambda raw, src, lg: (
        (exacto[raw.lower().replace("ü", "u")], raw, 100.0)
        if raw.lower().replace("ü", "u") in exacto else (None, "celta", 72.7)))
    r = fixtures.ensayo_copas(DESDE, [2024], hasta=HASTA)
    fila = r["eu.ucl"][2024]
    assert fila["terminados"] == 2
    assert fila["entrarian"] == 1
    assert fila["sin_resolver"] == {"Celtic": ["celta", 72.7]}
