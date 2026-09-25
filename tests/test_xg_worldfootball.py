"""
Verificación de la agregación de xG tiro a tiro a xG por partido.

El xG de equipo es la suma del xG de sus tiros. Lo que hay que demostrar es
que se agrupa por el partido correcto: agrupar por fecha y equipo parece
equivalente y no lo es —rompe en jornadas dobles y en aplazados—, y el error
sería silencioso porque produce números plausibles.
"""
from __future__ import annotations

import pandas as pd
import pytest

from qf.ingest.xg_worldfootball import (
    ASSETS,
    ON_TARGET,
    RDS_ASSETS,
    match_stats,
)


def tiros(filas) -> pd.DataFrame:
    """filas: (MatchURL, Date, Squad, Home_Away, xG[, Outcome, PSxG, Distance])"""
    cols = ["MatchURL", "Date", "Squad", "Home_Away", "xG",
            "Outcome", "PSxG", "Distance"]
    filas = [tuple(f) + (None,) * (len(cols) - len(f)) for f in filas]
    return pd.DataFrame(filas, columns=cols)


def test_suma_el_xg_de_los_tiros_de_cada_lado():
    df = tiros([
        ("/m1", "2024-03-01", "America", "Home", 0.10),
        ("/m1", "2024-03-01", "America", "Home", 0.25),
        ("/m1", "2024-03-01", "America", "Home", 0.05),
        ("/m1", "2024-03-01", "Cruz Azul", "Away", 0.40),
        ("/m1", "2024-03-01", "Cruz Azul", "Away", 0.15),
    ])
    out = match_stats(df)
    assert len(out) == 1
    fila = out.iloc[0]
    assert fila["home_team"] == "America"
    assert fila["away_team"] == "Cruz Azul"
    assert fila["home_xg"] == pytest.approx(0.40)
    assert fila["away_xg"] == pytest.approx(0.55)


def test_separa_dos_partidos_del_mismo_equipo_el_mismo_dia():
    """
    El caso que rompe si se agrupa por fecha y equipo en vez de por partido.
    Ocurre de verdad con aplazados reprogramados.
    """
    df = tiros([
        ("/m1", "2024-03-01", "America", "Home", 1.0),
        ("/m1", "2024-03-01", "Toluca", "Away", 0.5),
        ("/m2", "2024-03-01", "America", "Away", 0.3),
        ("/m2", "2024-03-01", "Pumas", "Home", 0.7),
    ])
    out = match_stats(df).sort_values("MatchURL")
    assert len(out) == 2
    assert out.iloc[0]["home_xg"] == pytest.approx(1.0)
    assert out.iloc[1]["home_team"] == "Pumas"
    assert out.iloc[1]["away_xg"] == pytest.approx(0.3)


def test_ignora_tiros_sin_xg():
    df = tiros([
        ("/m1", "2024-03-01", "A", "Home", 0.30),
        ("/m1", "2024-03-01", "A", "Home", None),
        ("/m1", "2024-03-01", "B", "Away", 0.20),
    ])
    out = match_stats(df)
    assert out.iloc[0]["home_xg"] == pytest.approx(0.30)


def test_descarta_partidos_con_un_solo_lado():
    """Sin los dos lados no hay partido que actualizar."""
    df = tiros([("/m1", "2024-03-01", "A", "Home", 0.30)])
    assert len(match_stats(df)) == 0


def test_columnas_faltantes_es_error_explicito():
    """
    Si el proyecto externo cambia el esquema, hay que enterarse por una
    excepción y no por una tabla de xG que se queda vacía sin motivo.
    """
    df = pd.DataFrame({"MatchURL": ["/m1"], "Date": ["2024-03-01"]})
    with pytest.raises(ValueError, match="columnas"):
        match_stats(df)


def test_la_fecha_se_convierte_a_datetime():
    df = tiros([
        ("/m1", "2024-03-01", "A", "Home", 0.3),
        ("/m1", "2024-03-01", "B", "Away", 0.2),
    ])
    assert pd.api.types.is_datetime64_any_dtype(match_stats(df)["Date"])


def test_cuenta_remates_y_remates_a_puerta():
    """
    'A puerta' es gol o parada. 'Saved off Target' y 'Woodwork' NO cuentan,
    que es la definición de FBref. Confundirlo inflaría el dato justo en las
    ligas donde es la única fuente que hay.
    """
    df = tiros([
        ("/m1", "2024-03-01", "A", "Home", 0.30, "Goal", 0.75, 8.0),
        ("/m1", "2024-03-01", "A", "Home", 0.10, "Saved", 0.22, 16.0),
        ("/m1", "2024-03-01", "A", "Home", 0.05, "Off Target", None, 24.0),
        ("/m1", "2024-03-01", "A", "Home", 0.04, "Blocked", None, 12.0),
        ("/m1", "2024-03-01", "A", "Home", 0.03, "Woodwork", None, 20.0),
        ("/m1", "2024-03-01", "A", "Home", 0.02, "Saved off Target", None, 30.0),
        ("/m1", "2024-03-01", "B", "Away", 0.20, "Goal", 0.60, 10.0),
    ])
    out = match_stats(df).iloc[0]
    assert out["home_shots"] == 6
    assert out["home_shots_target"] == 2      # solo Goal + Saved
    assert out["away_shots"] == 1
    assert out["away_shots_target"] == 1


def test_on_target_es_exactamente_gol_y_parada():
    assert ON_TARGET == {"Goal", "Saved"}


def test_suma_psxg_solo_de_los_remates_que_lo_tienen():
    """PSxG solo existe para remates a puerta; los demás no deben sumar cero
    artificialmente ni romper la suma."""
    df = tiros([
        ("/m1", "2024-03-01", "A", "Home", 0.30, "Goal", 0.75, 8.0),
        ("/m1", "2024-03-01", "A", "Home", 0.10, "Off Target", None, 25.0),
        ("/m1", "2024-03-01", "B", "Away", 0.20, "Saved", 0.35, 12.0),
    ])
    out = match_stats(df).iloc[0]
    assert out["home_psxg"] == pytest.approx(0.75)
    assert out["away_psxg"] == pytest.approx(0.35)


def test_distancia_media_de_remate():
    df = tiros([
        ("/m1", "2024-03-01", "A", "Home", 0.30, "Goal", 0.75, 10.0),
        ("/m1", "2024-03-01", "A", "Home", 0.10, "Off Target", None, 20.0),
        ("/m1", "2024-03-01", "B", "Away", 0.20, "Saved", 0.35, 15.0),
    ])
    out = match_stats(df).iloc[0]
    assert out["home_shot_distance"] == pytest.approx(15.0)
    assert out["away_shot_distance"] == pytest.approx(15.0)


def test_el_recuento_de_remates_ignora_los_que_no_tienen_xg():
    """
    Si se contaran los remates sin xG, el número de tiros no cuadraría con el
    xG agregado y las dos métricas contarían poblaciones distintas.
    """
    df = tiros([
        ("/m1", "2024-03-01", "A", "Home", 0.30, "Goal", 0.75, 10.0),
        ("/m1", "2024-03-01", "A", "Home", None, "Off Target", None, 20.0),
        ("/m1", "2024-03-01", "B", "Away", 0.20, "Saved", 0.35, 15.0),
    ])
    assert match_stats(df).iloc[0]["home_shots"] == 1


def test_funciona_sin_columnas_opcionales():
    """Si un dataset no trae PSxG ni Distance, el xG debe seguir saliendo."""
    df = pd.DataFrame([
        ("/m1", "2024-03-01", "A", "Home", 0.30),
        ("/m1", "2024-03-01", "B", "Away", 0.20),
    ], columns=["MatchURL", "Date", "Squad", "Home_Away", "xG"])
    out = match_stats(df)
    assert len(out) == 1
    assert out.iloc[0]["home_xg"] == pytest.approx(0.30)


def test_argentina_va_por_la_via_rds_no_por_la_de_tiros():
    """
    ar.primera no tiene fichero de tiros en ese repositorio, solo el xG ya
    agregado del release `match_results`, y solo en .rds. Las dos rutas tienen
    que ser DISJUNTAS: si una liga apareciera en las dos, `run()` usaría la de
    tiros (más rica) y la otra quedaría muerta sin que nadie se enterara.
    """
    assert "ar.primera" not in ASSETS
    assert "ar.primera" in RDS_ASSETS
    assert set(ASSETS) & set(RDS_ASSETS) == set()


def test_todas_las_ligas_del_catalogo_tienen_una_via_de_xg():
    """
    Las 8 ligas domésticas deben estar en una de las dos rutas. Las copas
    europeas no: su xG entra con el propio partido (ingest/uefa_cups.py).
    """
    domesticas = {"gb.premier_league", "es.laliga", "it.serie_a",
                  "nl.eredivisie", "mx.liga_mx", "br.serie_a", "us.mls",
                  "ar.primera", "de.bundesliga", "fr.ligue_1", "pt.primeira"}
    assert domesticas <= (set(ASSETS) | set(RDS_ASSETS))
