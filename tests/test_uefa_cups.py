"""
Verificación de la ingesta de copas europeas.

El test que justifica el módulo entero es el del NOMBRE CON PAÍS PEGADO. FBref
escribe 'Girona es' al local y 'eng Arsenal' al visitante: el código va detrás
en un lado y delante en el otro. Leerlo mal no da ningún error, simplemente
deja el nombre con basura, el equipo no se resuelve y el partido se descarta
en silencio. Como el módulo NUNCA crea equipos, el síntoma sería "las copas
están vacías" sin una sola línea de log que diga por qué.
"""
from __future__ import annotations

import pandas as pd
import pytest

from qf.ingest.uefa_cups import (
    COUNTRY_LEAGUE,
    season_label,
    split_country,
)


# ---------------------------------------------------------------------------
# Nombre y país
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,pais,nombre", [
    ("Girona es", "es", "Girona"),
    ("Bayern Munich de", "de", "Bayern Munich"),
    ("Dinamo Zagreb hr", "hr", "Dinamo Zagreb"),
    ("Manchester City eng", "eng", "Manchester City"),
])
def test_el_local_lleva_el_pais_detras(raw, pais, nombre):
    assert split_country(raw, "home") == (pais, nombre)


@pytest.mark.parametrize("raw,pais,nombre", [
    ("eng Arsenal", "eng", "Arsenal"),
    ("it Milan", "it", "Milan"),
    ("sk Slovan Bratislava", "sk", "Slovan Bratislava"),
])
def test_el_visitante_lo_lleva_delante(raw, pais, nombre):
    assert split_country(raw, "away") == (pais, nombre)


def test_el_lado_equivocado_no_inventa_un_pais():
    """
    Leer un nombre de local como si fuera de visitante debe devolver país None,
    no morder la primera palabra del nombre. Si se tragara 'Bayern' como
    código, el equipo se buscaría por 'Munich' y no se encontraría nunca.
    """
    pais, nombre = split_country("Bayern Munich de", "away")
    assert pais is None
    assert nombre == "Bayern Munich de"


def test_un_nombre_sin_pais_se_devuelve_entero():
    assert split_country("Real Madrid", "home") == (None, "Real Madrid")


def test_no_se_muerde_una_palabra_del_nombre():
    """
    El código de país es SIEMPRE minúscula y los nombres van capitalizados.
    Exigirlo es lo que impide que 'Ajax' o 'Porto' pierdan letras.
    """
    assert split_country("Ajax", "home") == (None, "Ajax")
    assert split_country("Ajax nl", "home") == ("nl", "Ajax")


# ---------------------------------------------------------------------------
# Temporada
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("fin,etiqueta", [
    (2016, "1516"), (2025, "2425"), (2000, "9900"), (2010, "0910"),
])
def test_la_temporada_usa_la_misma_etiqueta_que_el_resto(fin, etiqueta):
    """
    Tiene que coincidir con lo que escribe history_fd o los mismos años
    quedarían con dos etiquetas distintas en la tabla matches.
    """
    assert season_label(fin) == etiqueta


def test_el_cambio_de_siglo_no_rompe_la_etiqueta():
    assert season_label(2000) == "9900"


# ---------------------------------------------------------------------------
# Catálogo de países
# ---------------------------------------------------------------------------

def test_solo_se_mapean_paises_que_tenemos_dados_de_alta():
    """
    Mapear un país cuya liga no está en el catálogo haría que la ingesta
    buscara el equipo en una liga inexistente. Descartar es lo correcto.

    Los que siguen fuera son los que marcan la siguiente ampliación:
    Bélgica, Rusia, Turquía, Ucrania y Grecia.
    """
    assert "be" not in COUNTRY_LEAGUE
    assert "tr" not in COUNTRY_LEAGUE
    assert COUNTRY_LEAGUE["eng"] == "gb.premier_league"
    assert COUNTRY_LEAGUE["es"] == "es.laliga"
    assert COUNTRY_LEAGUE["de"] == "de.bundesliga"


def test_todo_pais_mapeado_apunta_a_una_liga_del_catalogo():
    """
    Un código mal escrito o una liga borrada dejarían la ingesta buscando
    equipos en un league_id inexistente: 0 resultados, 0 errores, copas
    vacías. Esta lista tiene que cuadrar con db/002 + db/007 + db/010.
    """
    catalogo = {"gb.premier_league", "es.laliga", "it.serie_a", "nl.eredivisie",
                "mx.liga_mx", "br.serie_a", "ar.primera", "us.mls",
                "de.bundesliga", "fr.ligue_1", "pt.primeira"}
    assert set(COUNTRY_LEAGUE.values()) <= catalogo


def test_ninguna_liga_esta_mapeada_dos_veces():
    """Dos códigos apuntando a la misma liga sería un error de copiar y pegar."""
    ligas = list(COUNTRY_LEAGUE.values())
    assert len(ligas) == len(set(ligas))


# ---------------------------------------------------------------------------
# Un partido completo, tal y como llega del dataset
# ---------------------------------------------------------------------------

def test_una_fila_real_se_parte_en_sus_dos_equipos():
    fila = pd.Series({
        "Season_End_Year": 2025,
        "Date": "2025-01-29",
        "Home": "Girona es",
        "Away": "eng Arsenal",
        "HomeGoals": 1.0,
        "AwayGoals": 2.0,
        "Home_xG": 0.9,
        "Away_xG": 1.8,
    })
    pais_h, nombre_h = split_country(fila["Home"], "home")
    pais_a, nombre_a = split_country(fila["Away"], "away")
    assert (COUNTRY_LEAGUE[pais_h], nombre_h) == ("es.laliga", "Girona")
    assert (COUNTRY_LEAGUE[pais_a], nombre_a) == ("gb.premier_league", "Arsenal")
    assert season_label(fila["Season_End_Year"]) == "2425"
