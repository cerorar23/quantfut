"""El lector de cuotas de PropLine reconoce los alias que aprenden su calendario y sus resultados (25-oct-2026)."""
from datetime import datetime, timezone

from qf.ingest import odds_worker as ow

KO = datetime(2026, 10, 26, 19, 0, tzinfo=timezone.utc)
META = {"m1": {"home": "Excelsior", "away": "Tromso", "kickoff_utc": KO, "league_id": "nl.eredivisie"}}
EV = {"id": "e1", "home_team": "SBV Excelsior", "away_team": "Tromso", "commence_time": "2026-10-26T19:00:00Z"}


def _alias(monkeypatch, propline: dict[str, int]):
    nombres = {1: "Excelsior", 2: "Tromso"}
    registrados = []

    def match_team(raw, source, league_id=None):
        tid = propline.get(raw) if source == "propline" else None
        return (tid, raw, 100.0) if tid else (None, None, 0.0)

    def resolve_team(raw, source, league_id=None, exact=True, seen_in=None):
        if raw in nombres.values():
            return raw
        registrados.append((raw, source, seen_in))
        return None

    monkeypatch.setattr(ow, "match_team", match_team)
    monkeypatch.setattr(ow, "resolve_team", resolve_team)
    monkeypatch.setattr(ow, "query_one", lambda sql, p: {"canonical_name": nombres[p[0]]})
    return registrados


def test_usa_el_alias_de_propline(monkeypatch):
    registrados = _alias(monkeypatch, {"SBV Excelsior": 1})
    assert ow.match_events([EV], META, otras_fuentes=("propline",)) == [(EV, "m1")]
    assert registrados == []


def test_sin_otras_fuentes_queda_como_antes(monkeypatch):
    registrados = _alias(monkeypatch, {"SBV Excelsior": 1})
    assert ow.match_events([EV], META) == []
    assert registrados == [("SBV Excelsior", "odds_api", "nl.eredivisie")]
