"""
Cargar el historial de Segunda sin duplicar clubes (2026-10-11).

Al activar el modelo en las ligas "solo sharp" hay que cargar su historial de
football-data. El cargador buscaba cada nombre SOLO en la liga que cargaba: el
Racing, que hoy está en LaLiga, no aparece en LaLiga 2, así que el historial de
Segunda lo habría creado otra vez y partido su historia en dos, sin ningún
error. Lo mismo con cada club que haya subido o bajado en doce temporadas.
"""
from __future__ import annotations

import pytest

from qf import normalize
from qf.ingest import history_fd


# Racing (id 10) juega hoy en LaLiga; su nombre de football-data ya es alias.
# Deportivo (11) también en LaLiga, solo con el nombre de API-Football.
# Sporting de Gijón (12) en LaLiga 2. Sporting (13) es el de Portugal: otro país.
PAIS = {"racing santander": {10}, "la coruna": {11}, "deportivo la coruna": {11},
        "sp gijon": {12}, "sporting gijon": {12}}


@pytest.fixture
def catalogo(monkeypatch):
    monkeypatch.setattr(normalize, "_alias_map",
                        lambda source: {"santander": {10}, "sporting": {13}})
    monkeypatch.setattr(normalize, "_paises", lambda: (
        {10: ("es.laliga", "Spain"), 11: ("es.laliga", "Spain"),
         12: ("es.laliga2", "Spain"), 13: ("pt.primeira", "Portugal")},
        {"es.laliga": "Spain", "es.laliga2": "Spain", "pt.primeira": "Portugal"}))
    monkeypatch.setattr(normalize, "_pais_teams", lambda league_id: PAIS)


def test_alias_de_otra_division_del_pais_se_reutiliza(catalogo):
    c = normalize.clasificar_historial("Santander", "football_data", "es.laliga2")
    assert c == {"decision": "existe", "team_id": 10, "via": "alias"}


def test_nombre_exacto_de_otra_fuente_se_reutiliza(catalogo):
    """El Deportivo solo existe con su nombre de API-Football, en Primera."""
    c = normalize.clasificar_historial("La Coruna", "football_data", "es.laliga2")
    assert c["decision"] == "existe" and c["team_id"] == 11


def test_un_alias_de_otro_pais_no_vale(catalogo):
    """'Sporting' es alias del Sporting de Portugal: en España no puede usarse."""
    c = normalize.clasificar_historial("Sporting", "football_data", "es.laliga2")
    assert c["decision"] != "existe"


def test_un_parecido_no_se_crea_ni_se_acepta(catalogo):
    c = normalize.clasificar_historial("Racing Santander B", "football_data", "es.laliga2")
    assert c["decision"] == "dudoso" and c["candidatos"] == [10]


def test_un_nombre_sin_parecido_es_nuevo(catalogo):
    c = normalize.clasificar_historial("Xerez", "football_data", "es.laliga2")
    assert c == {"decision": "nuevo"}


def test_un_nombre_exacto_de_dos_clubes_no_se_adivina(monkeypatch, catalogo):
    monkeypatch.setattr(normalize, "_pais_teams",
                        lambda league_id: {"real union": {20, 21}})
    c = normalize.clasificar_historial("Real Union", "football_data", "es.laliga2")
    assert c["decision"] == "dudoso"


@pytest.fixture
def base(monkeypatch, catalogo):
    escrito = {"sql": [], "alias": [], "pendientes": []}
    monkeypatch.setattr(history_fd, "execute", lambda sql, p=None: escrito["sql"].append(sql))
    monkeypatch.setattr(history_fd, "query_one", lambda sql, p=None: {"team_id": 99})
    monkeypatch.setattr(history_fd, "register_alias",
                        lambda raw, src, tid: escrito["alias"].append((raw, tid)))
    monkeypatch.setattr(history_fd, "_record_unresolved",
                        lambda raw, *a: escrito["pendientes"].append(raw))
    monkeypatch.setattr(history_fd, "clear_cache", lambda: None)
    return escrito


def test_cargar_un_ascendido_no_crea_equipo(base):
    assert history_fd._ensure_team("es.laliga2", "Santander") == 10
    assert not any("INSERT INTO teams" in s for s in base["sql"])


def test_el_nombre_exacto_queda_como_alias_de_football_data(base):
    assert history_fd._ensure_team("es.laliga2", "La Coruna") == 11
    assert base["alias"] == [("La Coruna", 11)]


def test_un_dudoso_se_salta_y_queda_pendiente(base):
    assert history_fd._ensure_team("es.laliga2", "Racing Santander B") is None
    assert base["pendientes"] == ["Racing Santander B"]
    assert not any("INSERT INTO teams" in s for s in base["sql"])


def test_un_club_nuevo_se_crea_en_la_liga_que_se_carga(base):
    assert history_fd._ensure_team("es.laliga2", "Xerez") == 99
    assert sum("INSERT INTO teams" in s for s in base["sql"]) == 1
    assert base["alias"] == [("Xerez", 99)]


# ---------------------------------------------------------------------------
# CSV de otra liga (fallo real del ensayo, 2026-10-11): `new/CHL.csv` responde
# con la Superliga china.
# ---------------------------------------------------------------------------

import pandas as pd  # noqa: E402

CHILE = {"league_id": "cl.primera", "fd_code": "CHL", "country": "Chile"}


def test_el_csv_chino_servido_como_chile_se_rechaza():
    # El BOM del UTF-8 leído en latin-1 queda pegado al nombre de la columna.
    df = pd.DataFrame({"ï»¿Country": ["China"], "Home": ["Beijing Guoan"]})
    assert history_fd.csv_ajeno(df, CHILE) is not None


def test_el_csv_de_su_pais_se_acepta():
    df = pd.DataFrame({"ï»¿Country": ["Norway"], "Home": ["Molde"]})
    assert history_fd.csv_ajeno(df, {"fd_code": "NOR", "country": "Norway"}) is None


def test_el_principal_se_comprueba_por_div():
    df = pd.DataFrame({"Div": ["E0"], "HomeTeam": ["Arsenal"]})
    assert history_fd.csv_ajeno(df, {"fd_code": "E1", "country": "England"}) is not None
    assert history_fd.csv_ajeno(df, {"fd_code": "E0", "country": "England"}) is None
