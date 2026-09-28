"""
Un alias no cruza países.

'Vitoria' (Brasil) y 'Vitória SC' (Guimarães) se normalizan igual. Con un
solo equipo por alias, el Guimarães entró en la Primeira como el Vitória
brasileño (partido del 11-oct, 27-sep). Ahora el alias se acota a la liga o
a otra división del mismo país; en copas, si es ambiguo, no se adivina.
"""
from __future__ import annotations

import pytest

from qf import normalize

BRASIL, GUIMARAES, LAS_PALMAS = 39917, 77425, 500


@pytest.fixture
def base(monkeypatch):
    alias = {"vitoria": {BRASIL, GUIMARAES}, "las palmas": {LAS_PALMAS}}
    monkeypatch.setattr(normalize, "_alias_map", lambda source: alias)
    monkeypatch.setattr(normalize, "_paises", lambda: (
        {BRASIL: ("br.serie_a", "Brazil"), GUIMARAES: ("pt.primeira", "Portugal"),
         LAS_PALMAS: ("es.laliga", "Spain")},
        {"br.serie_a": "Brazil", "pt.primeira": "Portugal", "es.laliga": "Spain",
         "es.laliga2": "Spain", "eu.uel": "Europe"}))
    monkeypatch.setattr(normalize, "_league_teams", lambda league_id: {})


def test_el_mismo_alias_resuelve_segun_la_liga(base):
    assert normalize.match_team("Vitória SC", "api_football", "pt.primeira")[0] == GUIMARAES
    assert normalize.match_team("Vitoria", "api_football", "br.serie_a")[0] == BRASIL


def test_una_division_hermana_si_vale(base):
    assert normalize.match_team("Las Palmas", "api_football", "es.laliga2")[0] == LAS_PALMAS


def test_en_copa_un_alias_ambiguo_no_se_adivina(base):
    assert normalize.match_team("Vitória SC", "api_football", None)[0] is None
    assert normalize.match_team("Las Palmas", "api_football", None)[0] == LAS_PALMAS


def test_un_alias_de_otro_pais_no_se_acepta(base):
    assert normalize.match_team("Las Palmas", "api_football", "br.serie_a")[0] is None
