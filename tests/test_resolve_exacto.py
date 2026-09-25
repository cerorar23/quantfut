"""
`resolve_team` sin liga que acote tiene que exigir coincidencia EXACTA.

El caso real que lo motiva salió al conectar The Odds API: sus eventos de
Champions y Europa League llegan sin liga doméstica, así que `odds_worker` los
resolvía contra las 13 competiciones a la vez. Con el umbral difuso de 90:

    'Rangers' (Escocia)          -> 'Angers'      (Ligue 1)     92,3
    'Atletico Madrid' (España)   -> 'Atletico MG' (Brasil)      76,9

El primero pasa el umbral. Y como un difuso aceptado se GRABA como alias
permanente, el error no se queda en ese partido: contamina la fuente entera
sin producir ningún error.
"""
from __future__ import annotations

import pytest

from qf import normalize


@pytest.fixture
def catalogo(monkeypatch):
    """Dos ligas con el par de nombres que el difuso confunde."""
    equipos = {"angers": 1, "paris sg": 2, "atletico mg": 3, "flamengo rj": 4}
    monkeypatch.setattr(normalize, "_alias_map", lambda source: {})
    monkeypatch.setattr(normalize, "_league_teams", lambda league_id: equipos)
    monkeypatch.setattr(
        normalize, "query_one",
        lambda *a, **k: {"canonical_name": "Angers"})
    registrados: list[tuple] = []
    monkeypatch.setattr(normalize, "register_alias",
                        lambda *a: registrados.append(a))
    monkeypatch.setattr(normalize, "_record_unresolved", lambda *a: None)
    return registrados


def test_difuso_cruza_continentes_por_encima_del_umbral(catalogo):
    """Documenta el peligro: sin exact, 'Rangers' se acepta como 'Angers'."""
    tid, cand, score = normalize.match_team("Rangers", "odds_api", None)
    assert tid == 1 and score >= normalize.AUTO_ACCEPT


def test_exacto_por_defecto_lo_rechaza(catalogo):
    assert normalize.resolve_team("Rangers", "odds_api") is None
    assert catalogo == [], "un rechazo no puede dejar alias grabado"


def test_exacto_sigue_aceptando_el_nombre_canonico(catalogo):
    assert normalize.resolve_team("Angers", "odds_api") == "Angers"


def test_exacto_desactivado_recupera_el_difuso(catalogo):
    assert normalize.resolve_team("Rangers", "odds_api", exact=False) == "Angers"


def test_seen_in_anota_la_copa_sin_acotar_la_busqueda(monkeypatch, catalogo):
    pools, anotados = [], []
    equipos = {"angers": 1}
    monkeypatch.setattr(normalize, "_league_teams",
                        lambda league_id: pools.append(league_id) or equipos)
    monkeypatch.setattr(normalize, "_record_unresolved",
                        lambda raw, src, league, cand, score: anotados.append(league))
    assert normalize.resolve_team("Rangers", "odds_api", seen_in="eu.ucl") is None
    assert pools == [None], "seen_in no puede restringir el catálogo de búsqueda"
    assert anotados == ["eu.ucl"]
