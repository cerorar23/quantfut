from datetime import datetime, timedelta, UTC

import pytest

from nba.api.mercados_partido import construir, resolver
from test_mercados import equipo_dist, jugador_dist, partido_con_mercados

CORTE = datetime(2026, 11, 4, 23, tzinfo=UTC)


def sello(mercado="equipo", entidad=None, corte=CORTE):
    dist = equipo_dist() if mercado == "equipo" else jugador_dist()
    return (mercado, entidad, "a" * 64, corte, corte + timedelta(seconds=1),
            {"nombre": "Jugador", "lado": "local"}, dist)


def cuota(mercado, linea, lado, entidad=None, recibido=None, precio=1.9, casa="casa"):
    return (mercado, entidad, linea, lado, casa, precio, recibido or CORTE - timedelta(minutes=5))


def test_todas_las_lineas_y_lados_sin_reducir_a_una_seleccion_por_familia():
    cuotas = [cuota("totals", linea, lado) for linea in (200.5, 220.5, 240.5) for lado in ("over", "under")]
    cuotas += [cuota("player_points", linea, lado, 10) for linea in (20.5, 27.5) for lado in ("over", "under")]
    cuotas += [cuota("spreads", -5.5, "local"), cuota("spreads", 5.5, "visit"),
               cuota("team_totals", 110.5, "over", 1), cuota("team_totals", 110.5, "under", 1)]
    data = construir(99, 1, 2, [sello(), sello("jugador:puntos", 10)], cuotas)
    rows = data["markets"]
    assert len(rows) == 16
    assert len({r["id"] for r in rows}) == len(rows)
    assert {r["market"] for r in rows} == {"winner", "handicap", "game_total", "team_points", "player_points"}
    for market in ("winner", "handicap"):
        assert sum(r["probability"] for r in rows if r["market"] == market) == pytest.approx(1)
    for linea in (200.5, 220.5, 240.5):
        assert sum(r["probability"] for r in rows if r["market"] == "game_total" and r["line"] == linea) == pytest.approx(1)


def test_sin_lineas_se_conservan_todas_las_proyecciones_y_los_dos_ganadores():
    sellos = [sello(), *(sello(f"jugador:{m}", j) for j in (10, 11) for m in ("puntos", "rebotes", "asistencias", "triples"))]
    data = construir(99, 1, 2, sellos, [])
    assert len(data["markets"]) == 2 and len(data["projections"]) == 8
    assert all(r["line"] is None and r["price"] is None for r in data["markets"])
    assert construir(99, 1, 2, [], [cuota("totals", 220.5, "over")])["markets"] == []


def test_cada_jugador_respeta_su_corte_y_no_usa_cuotas_posteriores():
    temprano = CORTE - timedelta(hours=1)
    cuotas = [cuota("player_points", 20.5, "over", 10, CORTE - timedelta(minutes=30)),
              cuota("player_points", 25.5, "over", 10, temprano - timedelta(minutes=1)),
              cuota("totals", 220.5, "over", recibido=CORTE + timedelta(seconds=1))]
    rows = construir(99, 1, 2, [sello(), sello("jugador:puntos", 10, temprano)], cuotas)["markets"]
    assert len(rows) == 3 and rows[-1]["line"] == 25.5


def test_ultima_cuota_por_casa_y_mejor_precio_entre_casas_sin_duplicar_ganadores():
    cuotas = [cuota("h2h", 0, "local"), cuota("totals", 220.5, "over", precio=1.8),
              cuota("totals", 220.5, "over", recibido=CORTE - timedelta(minutes=10), precio=9.0),
              cuota("totals", 220.5, "over", precio=2.0, casa="otra")]
    rows = construir(99, 1, 2, [sello()], cuotas)["markets"]
    assert len(rows) == 3
    assert rows[-1]["price"] == 2.0 and rows[-1]["book"] == "otra"


def test_linea_entera_conserva_push_y_condicion_de_participacion():
    rows = construir(99, 1, 2, [sello("jugador:puntos", 10)],
                     [cuota("player_points", 27, lado, 10) for lado in ("over", "under")])["markets"]
    assert len(rows) == 2
    assert sum(r["probability"] for r in rows) == pytest.approx(1)
    assert all(r["push_probability"] > 0 and r["conditional"] for r in rows)


def test_endpoint_entrega_lineas_proyecciones_y_no_cambia_el_radar(partido_con_mercados):
    client, pid, fecha, jugador = partido_con_mercados
    response = client.get(f"/nba/v1/partido/{pid}/mercados")
    assert response.status_code == 200
    data = response.json()
    assert data["partido_id"] == pid
    assert len([r for r in data["markets"] if r["market"] == "winner"]) == 2
    puntos = [r for r in data["markets"] if r["market"] == "player_points"]
    assert {r["side"] for r in puntos} == {"over", "under"}
    assert all(r["player_id"] == jugador and isinstance(r["team"], str) for r in puntos)
    assert jugador != 2544 and all(r["photo_id"] == 2544 for r in puntos)
    assert len(data["projections"]) == 1
    assert data["projections"][0]["photo_id"] == 2544
    assert not any(r["market"] == "game_total" and r["line"] == 210.5 for r in data["markets"])
    assert client.get(f"/nba/v1/mercados?fecha={fecha}").status_code == 200
    assert client.get("/nba/v1/partido/999999/mercados").status_code == 404


def test_estado_de_jugador_con_resultado_final_push_y_no_participacion():
    data = construir(99, 1, 2, [sello(), sello("jugador:puntos", 10)],
                     [cuota("player_points", linea, lado, 10) for linea in (20.5, 25) for lado in ("over", "under")])
    resolver(data, 1, 2, {(1, "puntos"): 110, (2, "puntos"): 100, (10, "puntos"): 25})
    props = [r for r in data["markets"] if r["player_id"]]
    assert [r["outcome"] for r in props] == ["win", "loss", "push", "push"]
    resolver(data, 1, 2, {(1, "puntos"): 110, (2, "puntos"): 100})
    assert all(r["outcome"] is None for r in props)
    resolver(data, 1, 2, {(1, "puntos"): 110, (2, "puntos"): 100, (10, "jugo"): 0})
    assert all(r["outcome"] == "void" for r in props)
    resolver(data, 1, 2, {(1, "puntos"): 110, (10, "puntos"): 25})
    assert all(r["outcome"] is None for r in data["markets"])
