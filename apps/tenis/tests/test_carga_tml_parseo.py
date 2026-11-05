"""Carga TML, parte pura (sin base): marcadores, filas absurdas, orientación y reglas de visibilidad."""
from datetime import date, datetime, timedelta, timezone

import pytest

from tenis.carga import tml_campos as campos
from tenis.carga.tml_carga import filas
from tenis.carga.tml_orientar import orientar
from tenis.carga.tml_parseo import analizar_fila
from tenis.carga.tml_reglas import (DESFASE_7, DESFASE_14, categoria, dias_de_edicion, fecha_fin, inicio_visible,
                                    lunes_de, lunes_semana_fin, por_equipos, visible_desde_partido,
                                    visible_desde_ronda)
from tenis.carga.tml_score import parsear_marcador

COLUMNAS = ["tourney_id", "tourney_name", "surface", "draw_size", "tourney_level", "indoor", "tourney_date",
            "match_num", "winner_id", "winner_seed", "winner_entry", "winner_name", "winner_hand", "winner_ht",
            "winner_ioc", "winner_age", "winner_rank", "winner_rank_points", "loser_id", "loser_seed", "loser_entry",
            "loser_name", "loser_hand", "loser_ht", "loser_ioc", "loser_age", "loser_rank", "loser_rank_points",
            "score", "best_of", "round", "minutes", "w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon",
            "w_SvGms", "w_bpSaved", "w_bpFaced", "l_ace", "l_df", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon",
            "l_SvGms", "l_bpSaved", "l_bpFaced"]
BASE = {c: "" for c in COLUMNAS}
BASE.update({"tourney_id": "2025-9900", "tourney_name": "Roland Garros", "surface": "Clay", "tourney_level": "G",
             "tourney_date": "20250526", "winner_id": "AA10", "loser_id": "BB20", "winner_name": "Ana Uno",
             "loser_name": "Bea Dos", "winner_hand": "R", "loser_hand": "L", "winner_ht": "180", "loser_ht": "0",
             "winner_ioc": "ESP", "loser_ioc": "", "winner_rank": "5", "loser_rank": "40",
             "winner_rank_points": "4000", "loser_rank_points": "1500", "score": "6-3 6-4", "best_of": "3",
             "round": "R32", "minutes": "95", "w_svpt": "60", "w_1stIn": "40", "w_1stWon": "30",
             "w_2ndWon": "12", "w_SvGms": "10", "w_bpSaved": "2", "w_bpFaced": "3", "w_ace": "7", "w_df": "2",
             "l_svpt": "58", "l_1stIn": "35", "l_1stWon": "20", "l_2ndWon": "10", "l_SvGms": "10",
             "l_bpSaved": "1", "l_bpFaced": "4", "l_ace": "2", "l_df": "3"})


def fila(**cambios) -> dict:
    return {**BASE, **cambios}


def analizar(fichero="2025.csv", **cambios):
    return analizar_fila(fila(**cambios), fichero)


# --- Marcadores -----------------------------------------------------------------------------------------------

def test_completado_dos_sets_limpio():
    m = parsear_marcador("6-3 6-4", 3)
    assert m.estado == "completado" and m.sets_completos == 2
    assert m.sets == ((6, 3, None, None), (6, 4, None, None))


def test_completado_de_un_solo_set_se_rechaza():
    assert parsear_marcador("6-3", 3).motivo == "completado_de_un_set"


def test_walkover_con_marcador_se_rechaza_y_sin_marcador_es_walkover():
    assert parsear_marcador("6-3 6-4 W/O", 3).motivo == "walkover_con_marcador"
    m = parsear_marcador("W/O", 3)
    assert m.estado == "walkover" and m.sets is None and m.sets_completos is None


def test_retirada_en_segundo_set_cuenta_solo_el_set_terminado():
    m = parsear_marcador("6-3 2-1 RET", 3)
    assert m.estado == "retirada" and m.sets_completos == 1


def test_7_6_sin_puntos_de_tiebreak_y_sets_de_ventaja_son_datos_historicos_validos():
    """Decisión del 5-nov: TML antiguo (1968-1990) no registra los puntos del tie-break y hubo sets de ventaja.
    Faltante = NULL, no inválido; el set cuenta y el partido se carga."""
    m = parsear_marcador("7-6 6-3", 3)
    assert m.motivo is None and m.estado == "completado" and m.sets[0] == (7, 6, None, None)
    m = parsear_marcador("8-6 6-3", 3)
    assert m.motivo is None and m.sets[0] == (8, 6, None, None)
    m = parsear_marcador("6-4 3-6 13-11", 3)
    assert m.motivo is None and m.sets_completos == 3


@pytest.mark.parametrize("marcador", ["7-4 6-3", "5-4 6-3", "9-6 6-3", "6-6 6-3", "8-5 6-3", "7-7 6-3", "10-3 6-4"])
def test_sets_imposibles_siguen_rechazandose(marcador):
    assert parsear_marcador(marcador, 3).motivo == "set_invalido"


def test_formato_no_valido_y_set_de_mas():
    assert parsear_marcador("6-3 6-4", 4).motivo == "completado_incoherente"
    assert parsear_marcador("6-3 6-4 6-4 6-4", 3).motivo == "mas_sets_que_formato"


def test_tiebreak_se_asigna_al_que_perdio_el_set_y_el_ganador_tiene_max_7_o_p_mas_2():
    m = parsear_marcador("6-7(5) 6-3 6-4", 3)
    assert m.sets[0] == (6, 7, 5, 7)
    m2 = parsear_marcador("7-6(10) 3-6 6-4", 3)
    assert m2.sets[0] == (7, 6, 12, 10)


def test_super_tiebreak_final_se_guarda_como_set_1_0():
    m = parsear_marcador("6-4 5-7 [10-7]", 3)
    assert m.estado == "completado" and m.super_tiebreak is True
    assert m.sets[2] == (1, 0, 10, 7)


def test_super_tiebreak_inconsistente_con_el_resultado_se_rechaza():
    assert parsear_marcador("7-6(5) 5-7 [3-10]", 3).motivo == "completado_incoherente"


@pytest.mark.parametrize("texto", ["", "ABD", "Played and unfinished", "&nbsp;"])
def test_sin_sets_y_estado_no_completado_es_cancelado(texto):
    assert parsear_marcador(texto, 3).estado == "cancelado"


def test_abandono_con_sets_y_marcador_ilegible_se_rechazan():
    assert parsear_marcador("4-6 2-1 WEA", 3).motivo is not None
    assert parsear_marcador("RET+H64", 3).motivo == "marcador_ilegible"
    assert parsear_marcador("7-(6)7 6-3 6-4", 3).motivo == "marcador_ilegible"


def test_descalificado_sin_ganador_y_con_sets_parciales():
    m = parsear_marcador("1-6 7-5 4-1 DEF", 3)
    assert m.estado == "descalificado" and m.sets_completos == 2


# --- Filas absurdas ------------------------------------------------------------------------------------------

def test_fila_sana_se_analiza_completa():
    a = analizar()
    assert a.motivo is None and not a.doble
    assert a.circuito == "atp" and a.anio == 2025 and a.clave == "9900"
    assert a.categoria == "GS" and a.dias == 14 and a.superficie == "clay"
    assert a.duracion == 95 and a.mejor_de == 3 and a.ronda == "R32"


@pytest.mark.parametrize("minutos, esperado", [("0", None), ("700", None), ("", None), ("600", 600)])
def test_duracion_fuera_de_rango_es_nula_y_se_avisa(minutos, esperado):
    a = analizar(minutes=minutos)
    assert a.duracion == esperado and a.motivo is None


def test_estadistica_incoherente_rechaza_solo_la_estadistica():
    a = analizar(w_1stWon="50")
    assert a.stat_motivo == "estadistica_incoherente"
    assert a.motivo is None and a.stats is None


def test_nombre_con_barra_es_doble_y_se_excluye():
    assert analizar(winner_name="Ana/Eva").doble is True


@pytest.mark.parametrize("cambio, motivo", [
    ({"winner_id": ""}, "id_jugador_vacio"),
    ({"loser_id": "AA10"}, "mismo_jugador"),
    ({"round": "3rd/4th"}, "ronda_no_valida"),
    ({"round": "Fs"}, "ronda_no_valida"),
    ({"best_of": "1"}, "formato_no_valido"),
    ({"tourney_date": "20251399"}, "fecha_no_valida"),
    ({"tourney_id": "1967-southern-pro"}, "temporada_anterior_al_esquema"),
])
def test_filas_que_se_rechazan_con_motivo(cambio, motivo):
    assert analizar(**cambio).motivo == motivo


def test_entrada_fuera_de_lista_es_nula_y_se_avisa():
    a = analizar(winner_entry="XX", loser_entry="WC")
    assert a.entradas == (None, "WC") and "entrada_no_mapeada" in a.avisos


def test_mano_ambidiestro_no_se_escribe():
    assert campos.mano("A") is None and campos.mano("R") == "D" and campos.mano("L") == "Z"
    assert campos.altura("0") is None and campos.altura("180") == "180"


def test_estadistica_faltante_es_nula_y_nunca_cero():
    e = campos.estadisticas({"w_ace": ""}, "w")
    assert e["aces"] is None and campos.sin_datos({k: None for k in e})


def test_clave_de_torneo_de_team_tie_incluye_el_anio():
    a = analizar(tourney_id="W-FC-2026-QLS-M-AUS-GBR-01", tourney_level="D", tourney_name="Billie Jean King Cup")
    assert a.anio == 2026 and a.clave == "w-fc-2026-qls-m-aus-gbr-01"
    assert a.categoria == "equipos" and a.por_equipos is True


def test_filas_del_csv_se_leen_como_dict(tmp_path):
    texto = ",".join(COLUMNAS) + "\n" + ",".join(BASE[c] for c in COLUMNAS) + "\n"
    rows = list(filas(texto.encode("utf-8")))
    assert len(rows) == 1 and rows[0][0]["winner_id"] == "AA10" and rows[0][1] == 2


# --- Orientación ---------------------------------------------------------------------------------------------

def test_orientacion_cuando_jugador_1_es_el_perdedor_de_tml():
    a = analizar()
    o = orientar(a, jug_w=900, jug_l=100, edicion_id=7, inicio_edicion=date(2025, 5, 26), dias_edicion=14)
    p = o["partido"]
    assert (p["jugador_1"], p["jugador_2"]) == (100, 900)
    assert o["resultado"]["ganador"] == 2 and o["resultado"]["retira"] is None
    assert o["resultado"]["sets"] == [[3, 6, None, None], [4, 6, None, None]]
    por_lado = {e["lado"]: e for e in o["estadisticas"]}
    assert por_lado[2]["aces"] == 7 and por_lado[1]["aces"] == 2  # el ganador de TML es el lado 2


def test_orientacion_retirada_marca_al_que_retira():
    a = analizar(score="6-3 2-1 RET")
    o = orientar(a, jug_w=10, jug_l=20, edicion_id=1, inicio_edicion=date(2025, 5, 26), dias_edicion=14)
    assert o["resultado"]["estado"] == "retirada" and o["resultado"]["ganador"] == 1
    assert o["resultado"]["retira"] == 2 and o["resultado"]["sets_completos"] == 1


# --- Reglas de visibilidad y edición -------------------------------------------------------------------------

@pytest.mark.parametrize("dias", [7, 14])
def test_visible_desde_crece_estrictamente_en_la_cadena_principal_y_en_las_previas(dias):
    tabla = DESFASE_14 if dias == 14 else DESFASE_7
    for cadena in (["R128", "R64", "R32", "R16", "QF", "SF", "F"], ["Q1", "Q2", "Q3"]):
        valores = [tabla[r] for r in cadena]
        assert valores == sorted(set(valores)), valores     # sin empates: el corte «fin de la ronda anterior» no ve la propia


@pytest.mark.parametrize("dias,rondas", [(7, {"R32", "R16", "QF", "SF", "F"}), (14, {"R128", "R64", "R32", "R16", "QF", "SF", "F"}),
                                         (7, {"R64", "R32", "R16", "QF", "SF", "F"})])
def test_protocolo_retro_el_corte_ve_la_pareja_y_la_ronda_anterior_pero_no_el_propio_resultado(dias, rondas):
    """Corte retro de un partido = visible_desde de la pareja + 1 s: ve su pareja y los resultados de las rondas
    anteriores de la edición, nunca el resultado propio (ni de rondas posteriores)."""
    inicio = date(2025, 5, 26)
    orden = [r for r in ("R128", "R64", "R32", "R16", "QF", "SF", "F") if r in rondas]
    for i, r in enumerate(orden):
        pareja = visible_desde_partido(r, inicio, dias, rondas)
        corte = pareja + timedelta(seconds=1)
        propio = visible_desde_ronda(r, inicio, dias)
        assert propio > corte, (r, pareja, propio)                                   # el propio resultado NO se ve
        for anterior in orden[:i]:
            assert visible_desde_ronda(anterior, inicio, dias) < corte, (r, anterior)  # el de las anteriores SÍ
        for posterior in orden[i + 1:]:
            assert visible_desde_ronda(posterior, inicio, dias) > corte
    assert visible_desde_partido(orden[0], inicio, dias, rondas) == inicio_visible(inicio)   # la primera ronda: inicio
    assert visible_desde_partido("R256", inicio, dias, rondas) is None


@pytest.mark.parametrize("dias", [7, 14])
def test_ningun_visible_desde_supera_fecha_fin_mas_un_dia(dias):
    inicio = date(2025, 5, 26)
    tope = fecha_fin(inicio, dias) + timedelta(days=1)
    for ronda in list(DESFASE_7) + ["R256", "BR"]:
        v = visible_desde_ronda(ronda, inicio, dias)
        if v is not None:
            assert v.date() <= tope


def test_tabla_7_dias_y_fin_de_semana_de_la_edicion():
    inicio = date(2025, 5, 26)  # lunes
    assert visible_desde_ronda("R32", inicio, 7) == datetime(2025, 5, 29, tzinfo=timezone.utc)   # L+3d (estricto: R64 = L+2d)
    assert visible_desde_ronda("F", inicio, 7) == datetime(2025, 6, 2, tzinfo=timezone.utc)
    assert visible_desde_ronda("R256", inicio, 7) is None
    assert lunes_semana_fin(inicio, 7) == date(2025, 5, 26)
    assert lunes_semana_fin(inicio, 14) == date(2025, 6, 2)
    assert lunes_de(date(2025, 5, 25)) == date(2025, 5, 19)  # domingo: lunes anterior
    assert inicio_visible(inicio) == datetime(2025, 5, 26, tzinfo=timezone.utc)


def test_categorias_y_equipos_por_nombre():
    assert categoria("atp", "C", "Some Challenger") == ("Challenger", None)
    assert categoria("wta", "I", "Auckland") == ("250", None)
    assert categoria("atp", "A", "Rome") == ("250", "nivel_no_verificado:atp:A")
    assert categoria("wta", "", "x") == (None, None)
    assert categoria("atp", "G", "Davis Cup X") == ("equipos", None)
    assert por_equipos("D", "x") and por_equipos("250", "Laver Cup") and not por_equipos("250", "Rome")
    assert dias_de_edicion("G") == 14 and dias_de_edicion("1000") == 14 and dias_de_edicion("250") == 7


# --- Ceros imposibles de saque (hallazgo del 5-nov: TML codifica el faltante como 0) --------------------------------

def _ceros_perdedor():
    return {"l_svpt": "0", "l_1stIn": "0", "l_1stWon": "0", "l_2ndWon": "0", "l_SvGms": "0", "l_bpSaved": "0",
            "l_bpFaced": "0", "l_ace": "0", "l_df": "0"}


def test_partido_terminado_con_cero_puntos_de_saque_deja_ese_lado_sin_estadistica():
    a = analizar(**_ceros_perdedor())        # 6-3 6-4 completado: el perdedor no puede tener 0 puntos de saque
    assert a.stats is not None and a.stats[0]["puntos_saque"] == 60          # el lado con datos se conserva
    assert all(v is None for v in a.stats[1].values())                        # NULL, nunca 0
    assert "estadistica_cero_imposible" in a.avisos


def test_ambos_lados_a_cero_en_partido_terminado_no_escribe_estadistica():
    a = analizar(**_ceros_perdedor(), w_svpt="0", w_1stIn="0", w_1stWon="0", w_2ndWon="0", w_SvGms="0", w_bpSaved="0",
                 w_bpFaced="0", w_ace="0", w_df="0")
    assert a.stats is None and a.stat_motivo is None


def test_retirada_muy_temprana_conserva_los_ceros_posibles():
    a = analizar(score="1-0 RET", **_ceros_perdedor())
    assert a.stats is not None and a.stats[1]["puntos_saque"] == 0
