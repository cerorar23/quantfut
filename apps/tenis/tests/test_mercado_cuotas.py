"""Pruebas unitarias del mdulo de mercado, cuotas y liquidacin (Sprint 5, B.4, I.0, I.3).

Cubre:
  1. Pruebas absurdas de cuotas (decimal <= 1, americana |x| < 100, un solo lado, en juego, suspendida, DFS, bolsa).
  2. Pareja repetida en la misma observacin -> sin mercado (decisin 24-oct).
  3. Liquidacin solo lee tenis.resultado propio (falla taxativamente si lee calificacin de PropLine).
  4. Liquidacin de retiradas y walkovers (regla de la casa de referencia).
  5. Reproduccin independiente del margen mediano de Pinnacle (2.46 % en Tennis-Data y 4.74 % en PropLine piloto).
"""
import math
from pathlib import Path
import pytest

from tenis.mercado.devig import (
    cuota_americana_a_decimal,
    cuota_decimal_a_americana,
    calcular_margen,
    devig_proporcional,
    devig_dos_vias,
)
from tenis.mercado.liquidacion import (
    liquidar_ganador,
    liquidar_primer_set,
    liquidar_handicap_sets,
    liquidar_totales_juegos,
    liquidar_handicap_juegos,
    liquidar_tiebreak,
    validar_resultado_propio,
)
from tenis.mercado.propline import (
    EXCHANGE_OR_DFS,
    es_cotizacion_valida,
    extraer_mercados_dos_vias,
    cargar_ganadores_piloto,
)
from tenis.mercado.tennis_data_hist import (
    cargar_tennis_data_raw,
    procesar_cuotas_partidos,
    calcular_margen_mediano_pinnacle,
)
from tenis.mercado.enlace import (
    extraer_claves_jugador,
    son_jugadores_compatibles,
    enlazar_partido_con_cuotas,
    construir_indice_cuotas,
)

DIR_REPO = Path(r"C:\Users\huye\Documents\apuesta proyec")
RUTA_ODDS_RAW = DIR_REPO / "data/tennis/tennis_data_manual_processed/odds_raw.parquet"
RUTA_PROPLINE_PILOTO = DIR_REPO / ".local/propline_shared_pilot_20261023"


# ---------------------------------------------------------------------------
# 1. Pruebas absurdas de conversin de cuotas
# ---------------------------------------------------------------------------
def test_cuota_americana_absurdas():
    # |x| < 100 rechazada
    with pytest.raises(ValueError, match="absurda en \\(-100, 100\\)"):
        cuota_americana_a_decimal(50)
    with pytest.raises(ValueError, match="absurda en \\(-100, 100\\)"):
        cuota_americana_a_decimal(-80)
    with pytest.raises(ValueError, match="absurda en \\(-100, 100\\)"):
        cuota_americana_a_decimal(0)

    # Valores no numricos o no finitos
    with pytest.raises(ValueError):
        cuota_americana_a_decimal("no_es_numero")
    with pytest.raises(ValueError):
        cuota_americana_a_decimal(float("nan"))
    with pytest.raises(ValueError):
        cuota_americana_a_decimal(float("inf"))

    # Casos vlidos
    assert abs(cuota_americana_a_decimal(150) - 2.50) < 1e-9
    assert abs(cuota_americana_a_decimal(-200) - 1.50) < 1e-9
    assert abs(cuota_americana_a_decimal(-100) - 2.00) < 1e-9
    assert abs(cuota_americana_a_decimal(100) - 2.00) < 1e-9


def test_cuota_decimal_absurdas():
    # Decimal <= 1.0 rechazada
    with pytest.raises(ValueError, match="absurda o <= 1.0"):
        cuota_decimal_a_americana(1.0)
    with pytest.raises(ValueError, match="absurda o <= 1.0"):
        cuota_decimal_a_americana(0.8)
    with pytest.raises(ValueError, match="absurda o <= 1.0"):
        cuota_decimal_a_americana(-1.5)
    with pytest.raises(ValueError):
        cuota_decimal_a_americana(float("nan"))

    # Casos vlidos
    assert cuota_decimal_a_americana(2.50) == 150
    assert cuota_decimal_a_americana(1.50) == -200
    assert cuota_decimal_a_americana(2.00) == 100


# ---------------------------------------------------------------------------
# 2. Pruebas de des-marginado proporcional
# ---------------------------------------------------------------------------
def test_devig_un_solo_lado_rechazado():
    # Un solo lado no permite calcular probabilidad sin margen
    with pytest.raises(ValueError, match="un solo lado"):
        devig_proporcional([1.80])
    with pytest.raises(ValueError, match="un solo lado"):
        calcular_margen([1.80])

    p1, p2, m = devig_dos_vias(1.80, None)
    assert p1 is None and p2 is None and m is None


def test_devig_proporcional_matematica():
    # Mercado simtrico
    p = devig_proporcional([1.90, 1.90])
    assert len(p) == 2
    assert abs(p[0] - 0.5) < 1e-9
    assert abs(p[1] - 0.5) < 1e-9
    assert abs(sum(p) - 1.0) < 1e-9

    # Mercado asimtrico
    # 1.25 -> inv = 0.8, 4.00 -> inv = 0.25, suma = 1.05, margen = 0.05
    p_asim = devig_proporcional([1.25, 4.00])
    assert abs(p_asim[0] - (0.8 / 1.05)) < 1e-9
    assert abs(p_asim[1] - (0.25 / 1.05)) < 1e-9
    assert abs(sum(p_asim) - 1.0) < 1e-9

    p1, p2, marg = devig_dos_vias(1.25, 4.00)
    assert abs(p1 - (0.8 / 1.05)) < 1e-9
    assert abs(marg - 0.05) < 1e-9


# ---------------------------------------------------------------------------
# 3. PropLine: exclusin de DFS, exchanges, apuestas en vivo y parejas repetidas
# ---------------------------------------------------------------------------
def test_propline_exclusion_dfs_exchange_in_play():
    # Cotizacin regular vlida
    q_ok = {"bookmaker": "pinnacle", "price_decimal": 1.90, "flags": []}
    assert es_cotizacion_valida(q_ok) is True

    # DFS excluido
    q_dfs = {"bookmaker": "prizepicks", "price_decimal": 1.90, "flags": ["dfs_not_single_bet"]}
    assert es_cotizacion_valida(q_dfs) is False

    # Exchange excluido
    q_ex = {"bookmaker": "betfair_ex", "price_decimal": 1.90, "flags": ["exchange_contract_requires_rules"]}
    assert es_cotizacion_valida(q_ex) is False

    # En vivo / suspendido excluido
    q_live = {"bookmaker": "pinnacle", "price_decimal": 1.90, "flags": ["in_play_or_started"]}
    assert es_cotizacion_valida(q_live) is False
    q_susp = {"bookmaker": "pinnacle", "price_decimal": 1.90, "flags": ["suspended"]}
    assert es_cotizacion_valida(q_susp) is False


def test_propline_pareja_repetida_sin_mercado():
    # Pareja repetida en la misma observacin con lneas contradictorias -> descartar (sin mercado)
    quotes = [
        {"event_id": "ev1", "bookmaker": "pinnacle", "market": "h2h", "period": None, "line_type": "main",
         "point": None, "description": "", "name": "Alcaraz C.", "price_decimal": 1.50, "flags": []},
        {"event_id": "ev1", "bookmaker": "pinnacle", "market": "h2h", "period": None, "line_type": "main",
         "point": None, "description": "", "name": "Sinner J.", "price_decimal": 2.70, "flags": []},
        # Misma clave con otra pareja diferente o repetida en el mismo evento
        {"event_id": "ev1", "bookmaker": "pinnacle", "market": "h2h", "period": None, "line_type": "main",
         "point": None, "description": "", "name": "Alcaraz C.", "price_decimal": 1.60, "flags": []},
        {"event_id": "ev1", "bookmaker": "pinnacle", "market": "h2h", "period": None, "line_type": "main",
         "point": None, "description": "", "name": "Medvedev D.", "price_decimal": 2.40, "flags": []},
    ]
    mercados = extraer_mercados_dos_vias(quotes)
    # Al haber dos parejas distintas en el mismo evento y mercado, se excluye defensivamente
    assert len(mercados) == 0


# ---------------------------------------------------------------------------
# 4. Liquidacin con resultados propios y prohibicin estricta de PropLine
# ---------------------------------------------------------------------------
def test_liquidacion_prohibe_calificacion_propline():
    res_invalido_1 = {"y_estado": "completado", "y_ganador": 1, "propline_winner": 1}
    with pytest.raises(ValueError, match="Liquidacin prohibida: se detectaron campos de calificacin de PropLine"):
        liquidar_ganador(res_invalido_1)

    res_invalido_2 = {"estado": "completado", "ganador": 1, "calificacion_propline": "settled"}
    with pytest.raises(ValueError, match="Liquidacin prohibida: se detectaron campos de calificacin de PropLine"):
        validar_resultado_propio(res_invalido_2)

    res_invalido_3 = {"estado": "completado", "ganador": 1, "settled_by_propline": True}
    with pytest.raises(ValueError, match="Liquidacin prohibida"):
        liquidar_totales_juegos(res_invalido_3, 22.5)


def test_liquidacion_completado_todos_mercados():
    res = {
        "y_estado": "completado",
        "y_ganador": 1,
        "y_sets_completos": 3,
        "y_sets": [[6, 4], [3, 6], [7, 6]],
        "y_juegos_1": 16,
        "y_juegos_2": 16,
    }
    assert liquidar_ganador(res) == 1
    assert liquidar_primer_set(res) == 1

    # Hndicap de sets: J1 gan 2 sets, J2 gan 1 set
    # Lnea -1.5 lado 1: 2 - 1.5 = 0.5 < 1 -> gana J2 (2)
    assert liquidar_handicap_sets(res, -1.5) == 2
    # Lnea +1.5 lado 1: 2 + 1.5 = 3.5 > 1 -> gana J1 (1)
    assert liquidar_handicap_sets(res, 1.5) == 1

    # Totales de juegos: total = 32
    assert liquidar_totales_juegos(res, 30.5) == "over"
    assert liquidar_totales_juegos(res, 33.5) == "under"
    assert liquidar_totales_juegos(res, 32.0) is None  # Push

    # Hndicap de juegos: diff = (16 + h) - 16 = h
    assert liquidar_handicap_juegos(res, -1.5) == 2
    assert liquidar_handicap_juegos(res, 1.5) == 1
    assert liquidar_handicap_juegos(res, 0.0) is None  # Push

    # Tiebreak: 7-6 en set 3
    assert liquidar_tiebreak(res) is True


def test_liquidacion_retirada_un_set():
    # 6-4 2-1 ret., J1 avanza (gana)
    res = {
        "y_estado": "retirada",
        "y_ganador": 1,
        "y_sets_completos": 1,
        "y_sets": [[6, 4], [2, 1]],
        "y_juegos_1": 8,
        "y_juegos_2": 5,
    }
    # Ganador liquida (gana quien avanza segn regla de casa)
    assert liquidar_ganador(res) == 1
    # 1.er set termin: liquida
    assert liquidar_primer_set(res) == 1
    # Totales, hndicaps y tiebreak: Nulos (None)
    assert liquidar_handicap_sets(res, -1.5) is None
    assert liquidar_totales_juegos(res, 21.5) is None
    assert liquidar_handicap_juegos(res, -2.5) is None
    assert liquidar_tiebreak(res) is None


def test_liquidacion_retirada_cero_sets():
    # Retirada en el 1.er set (3-2 ret.)
    res = {
        "y_estado": "retirada",
        "y_ganador": 1,
        "y_sets_completos": 0,
        "y_sets": [[3, 2]],
    }
    # Todo nulo
    assert liquidar_ganador(res) is None
    assert liquidar_primer_set(res) is None
    assert liquidar_totales_juegos(res, 20.5) is None


def test_liquidacion_walkover():
    res = {
        "y_estado": "walkover",
        "y_ganador": 1,
        "y_sets_completos": 0,
    }
    assert liquidar_ganador(res) is None
    assert liquidar_primer_set(res) is None
    assert liquidar_totales_juegos(res, 21.5) is None


# ---------------------------------------------------------------------------
# 5. Enlace e identidad
# ---------------------------------------------------------------------------
def test_normalizacion_y_claves_enlace():
    assert son_jugadores_compatibles("Carlos Alcaraz", "Alcaraz C.") is True
    assert son_jugadores_compatibles("Alexander Zverev", "Zverev A.") is True
    assert son_jugadores_compatibles("Felix Auger-Aliassime", "Auger-Aliassime F.") is True
    assert son_jugadores_compatibles("Alex de Minaur", "de Minaur A.") is True

    # Personas claramente distintas no deben ser compatibles
    assert son_jugadores_compatibles("Carlos Alcaraz", "Jannik Sinner") is False
    assert son_jugadores_compatibles("Novak Djokovic", "Djere L.") is False


# ---------------------------------------------------------------------------
# 6. Reproduccin independiente de mrgenes de Pinnacle en Tennis-Data y PropLine
# ---------------------------------------------------------------------------
def test_reproduccion_margen_pinnacle_tennis_data():
    """Reproduce el margen mediano de Pinnacle (2.46 %) sobre Tennis-Data."""
    if not RUTA_ODDS_RAW.exists():
        pytest.skip(f"No existe {RUTA_ODDS_RAW}")

    df_raw = cargar_tennis_data_raw(RUTA_ODDS_RAW, desde_anio=2000)
    partidos = procesar_cuotas_partidos(df_raw)
    res_margen = calcular_margen_mediano_pinnacle(partidos)

    assert res_margen["n"] > 90000, f"Se esperaban > 90k partidos con cuota PS, obtenidos {res_margen['n']}"
    # Mediana debe ser 2.46 % (0.02456... redondeado a 2 decimales pct = 2.46)
    assert res_margen["mediana_pct"] == 2.46, f"Mediana obtenida: {res_margen['mediana_pct']}% vs esperada 2.46%"
    assert 0.0245 <= res_margen["mediana"] <= 0.02465


def test_reproduccion_margen_pinnacle_propline_piloto():
    """Reproduce el margen mediano de Pinnacle (4.74 %, n = 76) en el piloto de PropLine."""
    from statistics import median

    if not RUTA_PROPLINE_PILOTO.exists():
        pytest.skip(f"No existe {RUTA_PROPLINE_PILOTO}")

    mercados = cargar_ganadores_piloto(RUTA_PROPLINE_PILOTO, excluir_en_juego=False)
    pinnacle_mercados = [m for m in mercados if m["bookmaker"] == "pinnacle"]

    assert len(pinnacle_mercados) == 76, f"Se esperaban n = 76 mercados de Pinnacle, obtenidos {len(pinnacle_mercados)}"
    margenes = [m["margen"] for m in pinnacle_mercados]
    med = median(margenes)
    med_pct = round(med * 100, 2)

    assert med_pct == 4.74, f"Mediana obtenida: {med_pct}% vs esperada 4.74%"
    assert 0.0470 <= med <= 0.0476
