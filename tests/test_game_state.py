"""
Verificación del xG ajustado por estado del partido.

El test que justifica el módulo entero es el del AUTOGOL: el marcador se
reconstruye desde los remates que acabaron en gol, y un autogol no es un
remate del equipo que anota. Si no se detecta, el estado del partido queda mal
desde ese minuto y contamina el objetivo del modelo sin dar ningún error.
Medido sobre Liga MX, pasa en el 7,8% de los partidos.
"""
from __future__ import annotations

import pandas as pd
import pytest

from qf.ingest.game_state import (
    REGULATION_END,
    STATES,
    estimate_ratios,
    goal_timeline,
    match_state_data,
    minutes_by_state,
    parse_minute,
    state_segments,
    xg_by_state,
)


def tiros(filas) -> pd.DataFrame:
    """filas: (Home_Away, Minute, xG, Outcome[, Match_Half])"""
    filas = [f if len(f) == 5 else f + (1,) for f in filas]
    return pd.DataFrame(filas, columns=["Home_Away", "Minute", "xG",
                                        "Outcome", "Match_Half"])


# ---------------------------------------------------------------------------
# Minutos
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entrada,esperado", [
    ("7", 7.0), ("73", 73.0), ("90", 90.0),
    ("45+2", 45.02), ("90+5", 90.05),
])
def test_parse_minute(entrada, esperado):
    assert parse_minute(entrada) == pytest.approx(esperado)


def test_el_descuento_conserva_el_orden():
    """45+2 debe ir DESPUÉS del 45 y ANTES del 46, no desplazarse al 47."""
    assert parse_minute("45") < parse_minute("45+2") < parse_minute("46")


def test_la_prorroga_se_descarta():
    """
    Solo ocurre en eliminatorias (liguilla) y es un contexto distinto al de
    liga, que es lo que modela la fuerza.
    """
    assert parse_minute("95", half=3) is None
    assert parse_minute("115", half=4) is None
    assert parse_minute("95", half=2) == 95.0


def test_minuto_invalido_es_none():
    assert parse_minute(None) is None
    assert parse_minute("no es minuto") is None
    assert parse_minute(float("nan")) is None


# ---------------------------------------------------------------------------
# Cronología y segmentos
# ---------------------------------------------------------------------------

def test_goal_timeline_ordena_y_filtra():
    df = tiros([
        ("Away", "70", 0.5, "Goal"),
        ("Home", "20", 0.4, "Goal"),
        ("Home", "35", 0.3, "Saved"),      # no es gol
        ("Home", "45+1", 0.2, "Goal"),
    ])
    assert goal_timeline(df) == [(20.0, "Home"), (45.01, "Home"), (70.0, "Away")]


def test_segmentos_sin_goles_es_todo_el_partido_empatado():
    seg = state_segments([])
    assert seg == [(0.0, REGULATION_END, 0)]


def test_segmentos_con_goles():
    seg = state_segments([(20.0, "Home"), (70.0, "Away")])
    assert seg == [(0.0, 20.0, 0), (20.0, 70.0, 1), (70.0, 90.0, 0)]


def test_los_minutos_por_estado_suman_el_partido():
    tl = [(10.0, "Home"), (55.0, "Away"), (80.0, "Away")]
    mins = minutes_by_state(tl)
    for lado in ("Home", "Away"):
        assert sum(mins[lado].values()) == pytest.approx(REGULATION_END)


def test_los_estados_son_espejo_entre_los_dos_equipos():
    """Si el local va ganando, el visitante va perdiendo el mismo rato."""
    tl = [(30.0, "Home")]
    mins = minutes_by_state(tl)
    assert mins["Home"]["leading"] == pytest.approx(mins["Away"]["trailing"])
    assert mins["Home"]["level"] == pytest.approx(mins["Away"]["level"])


# ---------------------------------------------------------------------------
# Asignación de xG a estados
# ---------------------------------------------------------------------------

def test_el_xg_se_asigna_al_estado_previo_al_remate():
    """
    Un gol en el minuto 20 no cuenta como 'iba ganando': en el instante del
    remate todavía estaba empatado. El estado se evalúa JUSTO ANTES.
    """
    df = tiros([
        ("Home", "20", 0.40, "Goal"),      # empatado al rematar
        ("Home", "60", 0.30, "Saved"),     # ya ganando
        ("Away", "70", 0.25, "Saved"),     # perdiendo
    ])
    tl = goal_timeline(df)
    xgs = xg_by_state(df, tl)
    assert xgs["Home"]["level"] == pytest.approx(0.40)
    assert xgs["Home"]["leading"] == pytest.approx(0.30)
    assert xgs["Away"]["trailing"] == pytest.approx(0.25)
    assert xgs["Away"]["level"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Ratios y ajuste
# ---------------------------------------------------------------------------

def test_los_ratios_se_normalizan_al_empate():
    muestras = [
        ({"level": 1.0, "leading": 0.5, "trailing": 2.0},
         {"level": 45.0, "leading": 45.0, "trailing": 45.0}),
    ]
    r = estimate_ratios(muestras)
    assert r.ratios["level"] == pytest.approx(1.0)
    assert r.ratios["leading"] == pytest.approx(0.5)   # produce la mitad
    assert r.ratios["trailing"] == pytest.approx(2.0)  # produce el doble


def test_el_ajuste_penaliza_el_xg_acumulado_yendo_por_detras():
    """
    Un equipo volcado que acumula xG perdiendo debe quedar ajustado A LA BAJA:
    ese volumen viene del marcador, no de su calidad.
    """
    r = estimate_ratios([
        ({"level": 1.0, "leading": 0.5, "trailing": 2.0},
         {"level": 45.0, "leading": 45.0, "trailing": 45.0}),
    ])
    assert r.adjust({"trailing": 2.0, "level": 0.0, "leading": 0.0}) == pytest.approx(1.0)
    # Y el xG generado en empate no se toca.
    assert r.adjust({"level": 1.5, "leading": 0.0, "trailing": 0.0}) == pytest.approx(1.5)


def test_sin_xg_en_empate_no_se_normaliza_a_ciegas():
    r = estimate_ratios([({"level": 0.0, "leading": 1.0, "trailing": 1.0},
                          {"level": 0.0, "leading": 45.0, "trailing": 45.0})])
    assert all(v == 1.0 for v in r.ratios.values())


# ---------------------------------------------------------------------------
# La protección contra autogoles
# ---------------------------------------------------------------------------

def test_devuelve_datos_cuando_el_marcador_cuadra():
    df = tiros([
        ("Home", "20", 0.40, "Goal"),
        ("Away", "70", 0.35, "Goal"),
        ("Home", "80", 0.10, "Off Target"),
    ])
    d = match_state_data(df, home_goals=1, away_goals=1)
    assert d is not None
    assert sum(d["home_minutes"].values()) == pytest.approx(REGULATION_END)


def test_devuelve_none_si_hubo_autogol():
    """
    El caso real: la BD dice 1-2 pero los remates solo explican 1-1, porque uno
    de los goles fue en propia puerta. Preferimos no tener el dato a tenerlo
    mal.
    """
    df = tiros([
        ("Home", "20", 0.40, "Goal"),
        ("Away", "70", 0.35, "Goal"),
    ])
    assert match_state_data(df, home_goals=1, away_goals=2) is None
    assert match_state_data(df, home_goals=2, away_goals=1) is None


def test_devuelve_none_si_faltan_goles_por_prorroga():
    """Gol en la prórroga: cuenta en el marcador pero se descarta del estado."""
    df = pd.DataFrame([
        ("Home", "20", 0.40, "Goal", 1),
        ("Home", "105", 0.50, "Goal", 3),   # prórroga
    ], columns=["Home_Away", "Minute", "xG", "Outcome", "Match_Half"])
    assert match_state_data(df, home_goals=2, away_goals=0) is None


def test_partido_sin_goles_es_todo_empate():
    df = tiros([
        ("Home", "30", 0.20, "Saved"),
        ("Away", "60", 0.15, "Off Target"),
    ])
    d = match_state_data(df, home_goals=0, away_goals=0)
    assert d["home_minutes"]["level"] == pytest.approx(REGULATION_END)
    assert d["home_xg_state"]["level"] == pytest.approx(0.20)


def test_los_estados_declarados_son_los_tres_esperados():
    assert set(STATES) == {"trailing", "level", "leading"}
