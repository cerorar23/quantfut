"""Reglas y análisis de SofaScore con eventos SINTÉTICOS (sin base de datos).

Incluye el constructor de eventos que usan también las pruebas de base de datos y la independiente.
Datos absurdos a propósito: ganador contra los sets, 8-6 con tie-break, 1 set «finished», duración 0 y 900 min,
primeros ganados > dentro, ronda vacía, mejor_de 4, mismo id en ambos lados, evento de fútbol.
"""
import copy
import json
from datetime import datetime, timezone

import pytest

from tenis.carga import sofascore_reglas as r
from tenis.carga.sofascore_parseo import analizar, resumen

INICIO = int(datetime(2026, 5, 26, 13, 0, tzinfo=timezone.utc).timestamp())
TORNEO_INICIO = int(datetime(2026, 5, 24, tzinfo=timezone.utc).timestamp())
TORNEO_FIN = int(datetime(2026, 6, 7, 20, 0, tzinfo=timezone.utc).timestamp())
NACIMIENTO = int(datetime(1990, 4, 2, tzinfo=timezone.utc).timestamp())

# Campos que NUNCA pueden acabar en la evidencia (plan §A.4).
PROHIBIDOS = {"firstToServe", "ranking", "currentRanking", "prizeCurrent", "userCount", "point", "changes",
              "h2h", "team_streaks", "prizeTotal", "birthCity", "residenceCity"}


def _marcador(sets, lado: int) -> dict:
    """lado 0 = local, 1 = visitante: periodN y periodNTieBreak de cada set."""
    d = {}
    for n, s in enumerate(sets, start=1):
        d[f"period{n}"] = s[lado]
        tb = s[2 + lado]
        if tb is not None:
            d[f"period{n}TieBreak"] = tb
    return d


def _equipo(id_, nombre, plays="right-handed", altura=1.85, nacimiento=NACIMIENTO, pais="ESP", tipo=1):
    return {"id": id_, "name": nombre, "fullName": nombre, "type": tipo, "subTeams": [],
            "country": {"alpha3": pais, "alpha2": pais[:2]},
            "playerTeamInfo": {"plays": plays, "height": altura, "birthDateTimestamp": nacimiento,
                               "ranking": 11, "currentRanking": 11, "prizeCurrent": 3444788, "userCount": 99}}


def evento(sets=((6, 3, None, None), (6, 4, None, None)), ganador=1, codigo=100, tipo="finished",
           ronda="Round of 32", mejor_de=3, id_local=101, id_visitante=202, circuito="atp", puntos=2000,
           nombre_torneo="Roland Garros, Men", deporte="tennis", nombre_local="Ana Uno",
           nombre_visitante="Bea Dos", evento_id=9001, duraciones=(2400, 2700), con_fin_torneo=True):
    """Evento de SofaScore sintético y coherente (salvo lo que el test cambie)."""
    tiempo = {f"period{n}": d for n, d in enumerate(duraciones[:len(sets)], start=1)}
    if sets:
        tiempo["currentPeriodStartTimestamp"] = INICIO + sum(duraciones[:len(sets) - 1])
    torneo = {"category": {"slug": circuito, "sport": {"slug": deporte, "name": "Tennis"}},
              "uniqueTournament": {"id": 2487 if circuito == "atp" else 9120, "name": nombre_torneo,
                                   "tennisPoints": puntos, "groundType": "Red clay"},
              "startTimestamp": TORNEO_INICIO, "name": nombre_torneo}
    if con_fin_torneo:
        torneo["endTimestamp"] = TORNEO_FIN
    return {
        "id": evento_id, "startTimestamp": INICIO, "defaultPeriodCount": mejor_de,
        "tournament": torneo, "season": {"year": "2026", "name": "2026 Roland Garros Men Singles"},
        "roundInfo": {"name": ronda} if ronda is not None else {},
        "status": {"code": codigo, "type": tipo, "description": {100: "Ended", 92: "Retired",
                                                                91: "Walkover"}.get(codigo, "Canceled")},
        "winnerCode": ganador, "groundType": "Red clay",
        "homeTeam": _equipo(id_local, nombre_local), "awayTeam": _equipo(id_visitante, nombre_visitante,
                                                                         plays="left-handed", altura=1.80),
        "homeScore": _marcador(sets, 0), "awayScore": _marcador(sets, 1),
        "time": tiempo,
        "ranking_del_partido_sin_uso": 4321,
    }


def _item(clave, local, visitante, total_local=None, total_visitante=None, tipo="team"):
    it = {"key": clave, "name": clave, "valueType": tipo, "homeValue": local, "awayValue": visitante}
    if total_local is not None:
        it["homeTotal"] = total_local
        it["awayTotal"] = total_visitante
    return it


def estadistica_json(pd_l=40, ps_l=60, pg_l=30, sg_l=12, aces=7, dobles=2, juegos=11, bps_l=2, bpa_l=4,
                     pd_v=35, ps_v=58, pg_v=20, sg_v=10, bps_v=1, bpa_v=3, aces_v=2, dobles_v=3, juegos_v=10):
    """Estadística del periodo ALL. Valores por lado: primeros dentro/total, primeros ganados, segundos ganados."""
    items = [
        {"key": "aces", "name": "Aces", "valueType": "event", "homeValue": aces, "awayValue": aces_v},
        {"key": "doubleFaults", "name": "Double faults", "valueType": "event", "homeValue": dobles,
         "awayValue": dobles_v},
        {"key": "serviceGamesTotal", "name": "Service games played", "valueType": "event", "homeValue": juegos,
         "awayValue": juegos_v},
        _item("firstServeAccuracy", pd_l, pd_v, ps_l, ps_v),
        _item("secondServeAccuracy", ps_l - pd_l, ps_v - pd_v, ps_l - pd_l, ps_v - pd_v),
        _item("firstServePointsAccuracy", pg_l, pg_v, pd_l, pd_v),
        _item("secondServePointsAccuracy", sg_l, sg_v, ps_l - pd_l, ps_v - pd_v),
        _item("breakPointsSaved", bps_l, bps_v, bpa_l, bpa_v),
    ]
    return {"statistics": [{"period": "ALL", "groups": [{"groupName": "Service", "statisticsItems": items}]},
                           {"period": "1ST", "groups": [{"groupName": "Service", "statisticsItems": items}]}]}


def _juego(j_global: int, saque: int, ganadores: list, ganador_juego: int, tb: bool):
    """Un juego de punto a punto. Regular: se listan los estados tras cada punto MENOS el último (que se omite,
    como hace SofaScore); tie-break: todos los puntos."""
    h = a = 0
    puntos = []
    etiq = {0: "0", 1: "15", 2: "30", 3: "40"}
    # Regular: el último punto cierra el juego y no se lista; sus estados no se muestran.
    listados = ganadores if tb else ganadores[:-1]
    for w in listados:
        if w == 1:
            h += 1
        else:
            a += 1
        if tb:
            puntos.append({"homePoint": str(h), "awayPoint": str(a)})
        else:
            if h >= 3 and a >= 3:
                pantalla = ("40", "40") if h == a else ("A", "40") if h - a == 1 else ("40", "A")
            else:
                pantalla = (etiq[h], etiq[a])
            puntos.append({"homePoint": pantalla[0], "awayPoint": pantalla[1]})
    return {"game": j_global, "points": puntos,
            "score": {"homeScore": 0, "awayScore": 0, "serving": saque, "scoring": ganador_juego}}


def pbp_desde(sets) -> dict:
    """Punto a punto coherente con un marcador: `sets` = [(gl, gv, tbl, tbv)] en codificación local.
    Los juegos regulares se ganan 4-0 o 0-4 (sin deuce); el tie-break reproduce la secuencia exacta."""
    salida = []
    g = 0
    for n, (gl, gv, tbl, tbv) in enumerate(sets, start=1):
        hay_tb = tbl is not None or tbv is not None
        if hay_tb:
            ganador_set = 1 if gl > gv else 2
            w, p = (gl, gv) if ganador_set == 1 else (gv, gl)
            tbw, tbp = (tbl, tbv) if ganador_set == 1 else (tbv, tbl)
            regulares = [ganador_set] * (w - 1) + [3 - ganador_set] * p
            tb_seq = []
            for _ in range(tbp):
                tb_seq += [3 - ganador_set, ganador_set]
            tb_seq += [ganador_set] * (tbw - tbp)
        else:
            regulares = [1] * gl + [2] * gv
            tb_seq = None
        juegos = []
        for ganador_juego in regulares:
            g += 1
            saque = 1 if g % 2 == 1 else 2
            juegos.append(_juego(len(juegos) + 1, saque, [ganador_juego] * 4, ganador_juego, False))
        if tb_seq is not None:
            g += 1
            saque = 1 if g % 2 == 1 else 2
            juegos.append(_juego(len(juegos) + 1, saque, tb_seq, ganador_set, True))
        salida.append({"set": n, "games": list(reversed(juegos))})
    return {"pointByPoint": salida}


def sets_de(evento_dict) -> list:
    """Marcador en codificación local a partir de un evento (mismo orden que el constructor)."""
    sets = []
    for n in range(1, 6):
        if f"period{n}" not in evento_dict["homeScore"] or f"period{n}" not in evento_dict["awayScore"]:
            break
        sets.append((evento_dict["homeScore"][f"period{n}"], evento_dict["awayScore"][f"period{n}"],
                     evento_dict["homeScore"].get(f"period{n}TieBreak"),
                     evento_dict["awayScore"].get(f"period{n}TieBreak")))
    return sets


def _sin_prohibidos(obj, ruta="") -> list:
    """Rutas de claves prohibidas dentro de un objeto (recursivo)."""
    hallazgos = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in PROHIBIDOS:
                hallazgos.append(f"{ruta}/{k}")
            hallazgos += _sin_prohibidos(v, f"{ruta}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hallazgos += _sin_prohibidos(v, f"{ruta}[{i}]")
    return hallazgos


# ---------- Reglas puras ----------

@pytest.mark.parametrize("nombre,esperado", [
    ("Round of 16", "R16"), ("Quarterfinals", "QF"), ("Semifinals", "SF"), ("Final", "F"),
    ("Round of 32", "R32"), ("Round of 64", "R64"), ("Round of 128", "R128"), ("Round robin", "RR"),
    ("Qualification round 1", "Q1"), ("Qualification Round 2", "Q2"), ("QUARTERFINALS", "QF"),
    ("", None), (None, None), ("Qualification Final", "QL"), ("Qualifications", None),
])
def test_ronda_normaliza_y_rechaza(nombre, esperado):
    assert r.ronda(nombre) == esperado


@pytest.mark.parametrize("circuito,puntos,nombre,esperado", [
    ("atp", 2000, "Roland Garros, Men", "GS"), ("atp", 1000, "Miami", "M1000"),
    ("wta", 1000, "WTA 1000 Rome", "WTA1000"), ("atp", 500, "Doha", "500"), ("wta", 250, "Hobart", "250"),
    ("atp", 1500, "ATP Finals", "Finales"), ("wta", 1500, "WTA Finals", "Finales"),
    ("atp", 0, "Davis Cup Qualifiers", "equipos"), ("wta", 500, "Billie Jean King Cup", "equipos"),
    ("atp", 1000, "Olympic Games", "JJOO"),
])
def test_categoria_por_nombre_y_puntos(circuito, puntos, nombre, esperado):
    assert r.categoria(circuito, puntos, nombre)[0] == esperado


def test_categoria_neutra_lleva_aviso():
    cat, aviso = r.categoria("atp", 125, "Challenger de algo")
    assert cat == "250" and aviso == "categoria_neutra:125"


@pytest.mark.parametrize("ground,esperado", [
    ("Hardcourt outdoor", ("hard", False)), ("Hardcourt indoor", ("hard", True)),
    ("Red clay", ("clay", False)), ("Red clay indoor", ("clay", True)), ("Green clay", ("clay", False)),
    ("Grass", ("grass", False)), ("Carpet indoor", ("carpet", True)),
])
def test_superficie_mapeada(ground, esperado):
    sup, indoor, aviso = r.superficie(ground)
    assert (sup, indoor) == esperado and aviso is None


def test_superficie_desconocida_es_nula_con_aviso():
    assert r.superficie("Mud") == (None, None, "superficie_desconocida:Mud")


@pytest.mark.parametrize("sets,ultimo,esperado", [
    (((6, 4, None, None),), True, (1, None)),
    (((7, 5, None, None),), False, (1, None)),
    (((7, 6, 7, 4),), False, (1, None)),
    (((7, 6, None, None),), False, (1, None)),                        # sin puntos de tie-break: NULL, no inválido
    (((7, 6, None, None),), True, (1, None)),
    (((8, 6, 8, 6),), True, (None, "set_invalido")),                   # 8-6 con tie-break: incoherente
    (((7, 4, None, None),), True, (None, "set_invalido")),
    (((8, 6, None, None),), False, (None, "set_invalido")),          # ventaja solo en el último set
    (((8, 6, None, None),), True, (1, None)),
    (((1, 0, 10, 8),), True, (1, None)),                              # súper tie-break final
    (((1, 0, 10, 8),), False, (None, "set_invalido")),
    (((6, 6, None, None),), True, (None, "set_empatado")),
    (((6, None, None, None),), True, (None, "set_incompleto")),
])
def test_validacion_de_sets(sets, ultimo, esperado):
    gl, gv, tbl, tbv = sets[0]
    assert r.valida_set(gl, gv, tbl, tbv, ultimo) == esperado


@pytest.mark.parametrize("codigo,esperado", [(100, "completado"), (92, "retirada"), (91, "walkover"),
                                             (97, "descalificado"), (98, "descalificado"), (5, None)])
def test_estado_por_codigo_de_status(codigo, esperado):
    assert r.estado_base({"code": codigo, "type": "finished", "description": "x"}) == esperado


def test_duracion_cero_y_900_min_son_nulas():
    assert r.duracion_min({"period1": 0, "period2": 0}, 2) is None
    assert r.duracion_min({"period1": 54000}, 1) is None            # 900 min
    assert r.duracion_min({"period1": 2400, "period2": 2700}, 2) == 85


def test_fin_estimado_conservador_y_sin_duraciones():
    tiempo = {"period1": 2400, "period2": 2700, "currentPeriodStartTimestamp": INICIO + 2400}
    fin = r.fin_estimado(INICIO, tiempo, 2)
    # max(inicio+5100, (inicio+2400)+2700) = inicio+5100; +30 min
    assert int(fin.timestamp()) == INICIO + 5100 + 1800
    assert int(r.fin_estimado(INICIO, {}, 2).timestamp()) == INICIO + 6 * 3600


def test_estadistica_coherente_y_definicion():
    items = r.estadisticas_all(estadistica_json())
    fila, motivo = r.estadistica(items, "home")
    assert motivo is None
    assert fila["puntos_saque"] == 60 and fila["primeros_dentro"] == 40 and fila["primeros_ganados"] == 30
    assert fila["segundos_ganados"] == 12 and fila["juegos_saque"] == 11
    assert fila["bp_salvados"] == 2 and fila["bp_afrontados"] == 4 and fila["aces"] == 7


def test_estadistica_primeros_ganados_mayor_que_dentro_se_rechaza():
    items = r.estadisticas_all(estadistica_json(pg_l=45, pd_l=40))
    assert r.estadistica(items, "home") == (None, "incoherente")


def test_estadistica_cero_puntos_de_saque_es_faltante():
    items = r.estadisticas_all(estadistica_json(ps_l=0, pd_l=0, pg_l=0, sg_l=0))
    assert r.estadistica(items, "home") == (None, "cero_imposible")


def test_estadistica_ignora_periodos_parciales():
    data = estadistica_json()
    data["statistics"][0]["period"] = "1ST"          # el ALL desaparece: no hay datos del partido completo
    assert r.estadisticas_all(data) == {}


# ---------- Punto a punto ----------

def test_pbp_coherente_se_deriva_con_el_punto_final_implicito():
    e = evento()
    filas, motivo = r.juegos_pbp(pbp_desde(sets_de(e)), sets_de(e))
    assert motivo is None
    assert len(filas) == 9 + 10                        # 6-3 y 6-4: 19 juegos
    assert all(f["puntos"] == "SSSS" or f["puntos"] == "RRRR" for f in filas)
    assert filas[0]["puntos"] == "SSSS" and filas[0]["es_tiebreak"] is False


def test_pbp_tiebreak_se_deriva_y_cierra():
    sets = [(6, 4, None, None), (7, 6, 7, 5)]
    e = evento(sets=sets, duraciones=(2400, 3600, 2700))
    filas, motivo = r.juegos_pbp(pbp_desde(sets), sets)
    assert motivo is None
    tb = [f for f in filas if f["es_tiebreak"]]
    assert len(tb) == 1 and tb[0]["set_n"] == 2 and len(tb[0]["puntos"]) == 12   # 5-5 tras 10 puntos + 2 del ganador


def test_pbp_juego_que_falta_se_rechaza():
    e = evento()
    pbp = pbp_desde(sets_de(e))
    pbp["pointByPoint"][0]["games"] = pbp["pointByPoint"][0]["games"][:-1]   # se pierde el juego 1
    assert r.juegos_pbp(pbp, sets_de(e)) == (None, "pbp_juegos_no_consecutivos")


def test_pbp_recuento_de_juegos_distinto_del_marcador_se_rechaza():
    e = evento()
    pbp = pbp_desde(sets_de(e))
    # El listado va en orden inverso: games[-1] es el juego 1 (ganado 4-0 por el local).
    pbp["pointByPoint"][0]["games"][-1]["score"]["scoring"] = 2
    assert r.juegos_pbp(pbp, sets_de(e)) == (None, "pbp_final_no_deducible")


def test_pbp_saque_que_no_alterna_se_rechaza():
    e = evento()
    pbp = pbp_desde(sets_de(e))
    pbp["pointByPoint"][0]["games"][0]["score"]["serving"] = pbp["pointByPoint"][0]["games"][1]["score"]["serving"]
    assert r.juegos_pbp(pbp, sets_de(e))[1] in ("pbp_saque_no_alterna",)


def test_pbp_ganador_del_juego_no_deducible_se_rechaza():
    e = evento(sets=((6, 4, None, None), (6, 4, None, None)))
    pbp = pbp_desde(sets_de(e))
    juego = pbp["pointByPoint"][0]["games"][0]
    juego["points"] = [{"homePoint": "0", "awayPoint": "15"}, {"homePoint": "15", "awayPoint": "15"}]
    juego["score"]["scoring"] = 2
    assert r.juegos_pbp(pbp, sets_de(e))[1] == "pbp_final_no_deducible"


# ---------- Análisis del evento ----------

def test_evento_valido_se_acepta_y_no_lleva_campos_prohibidos_en_la_salida():
    e = evento()
    a = analizar(e, estadistica_json(), pbp_desde(sets_de(e)))
    assert a["rechazo"] is None and a["excluido"] is None
    assert a["resultado"]["estado"] == "completado" and a["resultado"]["sets_completos"] == 2
    assert a["resultado"]["ganador"] == 1 and a["resultado"]["sets"] == [[6, 3, None, None], [6, 4, None, None]]
    assert a["partido"]["visible_desde"] == datetime.fromtimestamp(INICIO, tz=timezone.utc) - r.VENTANA_PARTIDO
    assert _sin_prohibidos(a) == []
    assert _sin_prohibidos(resumen(e)) == []


def test_ganador_que_contradice_los_sets_se_rechaza():
    assert analizar(evento(ganador=2), None, None)["rechazo"] == "completado_incoherente"


def test_partido_finished_de_un_set_se_rechaza():
    e = evento(sets=((6, 3, None, None),))
    assert analizar(e, None, None)["rechazo"] == "completado_incoherente"


def test_set_8_6_con_tiebreak_se_rechaza():
    e = evento(sets=((8, 6, 8, 6), (6, 4, None, None)))
    assert analizar(e, None, None)["rechazo"] == "set_invalido"


def test_retirada_guarda_solo_sets_completos_y_avisa_del_parcial():
    e = evento(sets=((6, 3, None, None), (2, 1, None, None)), codigo=92, tipo="finished", ganador=1)
    a = analizar(e, None, None)
    assert a["rechazo"] is None
    assert a["resultado"]["estado"] == "retirada" and a["resultado"]["retira"] == 2
    assert a["resultado"]["sets"] == [[6, 3, None, None]] and a["resultado"]["sets_completos"] == 1
    assert any(av.startswith("set_parcial_excluido") for av in a["avisos"])


def test_walkover_con_marcador_se_rechaza_y_sin_marcador_no_tiene_sets():
    assert analizar(evento(codigo=91, ganador=1), None, None)["rechazo"] == "walkover_con_marcador"
    e = evento(sets=(), codigo=91, ganador=1)
    a = analizar(e, None, None)
    assert a["rechazo"] is None and a["resultado"]["ganador"] is None and a["resultado"]["sets"] is None


def test_ronda_vacia_se_rechaza():
    assert analizar(evento(ronda=None), None, None)["rechazo"] == "ronda_desconocida"


def test_mejor_de_4_se_rechaza():
    assert analizar(evento(mejor_de=4), None, None)["rechazo"] == "mejor_de_no_valido"


def test_mismo_jugador_en_local_y_visitante_se_rechaza():
    assert analizar(evento(id_visitante=101), None, None)["rechazo"] == "mismo_jugador"


def test_evento_de_futbol_se_excluye():
    a = analizar(evento(deporte="football"), None, None)
    assert a["excluido"] == "no_tenis" and a["rechazo"] is None


def test_dobles_se_excluyen():
    e = evento()
    e["homeTeam"]["name"] = "Ana Uno / Eva Dos"
    assert analizar(e, None, None)["excluido"] == "doble"


def test_estadistica_incoherente_no_tumba_el_partido_pero_avisa():
    e = evento()
    a = analizar(e, estadistica_json(pg_l=45, pd_l=40), None)
    assert a["rechazo"] is None
    assert a["estadistica"]["local"] is None and a["estadistica"]["visitante"] is not None
    assert "estadistica_local:incoherente" in a["avisos"]


def test_orden_de_ids_no_cambia_el_resultado_local_codificado():
    e = evento(id_local=500, id_visitante=7)
    a = analizar(e, None, None)
    assert a["resultado"]["ganador"] == 1 and a["jugadores"]["local"]["id_fuente"] == "500"


def test_ids_de_jugador_con_mano_altura_y_fecha():
    e = evento()
    a = analizar(e, None, None)
    local = a["jugadores"]["local"]
    assert local["mano"] == "D" and local["altura_cm"] == "185" and local["pais"] == "ESP"
    assert local["fecha_nacimiento"] == "1990-04-02"
    assert a["jugadores"]["visitante"]["mano"] == "Z"


def test_prohibidos_no_se_leen_aunque_esten_en_el_original():
    e = copy.deepcopy(evento())
    e["firstToServe"] = 1
    e["changes"] = {"changes": ["x"]}
    e["h2h"] = {"x": 1}
    a = analizar(e, None, None)
    assert _sin_prohibidos(a) == []
    assert "ranking_del_partido_sin_uso" not in json.dumps(a, default=str)
