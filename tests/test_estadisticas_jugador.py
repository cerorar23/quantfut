"""
Estadísticas por jugador (db/035, fuerza por jugador Fase A).

Lo que fijan: el lado se asigna por el id de equipo de API-Football, no por
el orden; los suplentes que no jugaron no se guardan; los recuentos nulos son
0 y la nota del proveedor, que llega como texto, se convierte a número.
"""
from __future__ import annotations

from qf.ingest.estadisticas_jugador import parse_jugadores


def _jugador(pid, minutos, pos="M", suplente=False, rating="7.1", **stats):
    s = {"games": {"minutes": minutos, "position": pos, "rating": rating,
                   "substitute": suplente},
         "shots": {"total": stats.get("tiros"), "on": stats.get("puerta")},
         "goals": {"total": stats.get("goles"), "assists": stats.get("asist"),
                   "saves": stats.get("paradas")},
         "passes": {"key": stats.get("clave")},
         "tackles": {"total": stats.get("entradas"), "interceptions": None},
         "duels": {"won": stats.get("duelos")},
         "dribbles": {"success": None}}
    return {"player": {"id": pid, "name": f"J{pid}"}, "statistics": [s]}


def _resp(primero_visitante=False):
    local = {"team": {"id": 538}, "players": [
        _jugador(1, 90, "F", tiros=4, puerta=2, goles=1, clave=1),
        _jugador(2, 25, "M", suplente=True, rating=None),
        _jugador(3, None, "D", suplente=True, rating=None)]}
    visita = {"team": {"id": 542}, "players": [_jugador(9, 90, "G", paradas=3)]}
    return [visita, local] if primero_visitante else [local, visita]


def test_el_lado_sale_del_id_de_equipo_no_del_orden():
    filas = parse_jugadores(_resp(primero_visitante=True), 538, 542)
    assert {f["player_id"]: f["side"] for f in filas} == {1: "home", 2: "home", 9: "away"}


def test_suplente_sin_minutos_no_se_guarda_y_nulos_son_cero():
    filas = {f["player_id"]: f for f in parse_jugadores(_resp(), 538, 542)}
    assert 3 not in filas
    delantero = filas[1]
    assert (delantero["tiros"], delantero["tiros_puerta"], delantero["goles"],
            delantero["pases_clave"], delantero["asistencias"]) == (4, 2, 1, 1, 0)
    assert delantero["titular"] is True and delantero["nota_proveedor"] == 7.1
    assert filas[2]["titular"] is False and filas[2]["nota_proveedor"] is None
    assert filas[9]["paradas"] == 3 and filas[9]["posicion"] == "G"


def test_sin_ids_de_equipo_usa_el_orden_del_proveedor():
    filas = parse_jugadores(_resp(), None, None)
    assert {f["player_id"]: f["side"] for f in filas}[9] == "away"


def test_respuesta_vacia():
    assert parse_jugadores([], 538, 542) == []
