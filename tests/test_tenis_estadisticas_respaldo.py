"""Respaldo de estadísticas de tenis: clasificación desde SportsAPIPro y H2H/forma desde el archivo propio."""
from qf.api import tenis_estadisticas as te
from qf.ingest import tenis_estadisticas_respaldo as rs


def fila(k, a, b, fecha, ganador="First Player", estado="Finished", tipo="Atp Singles"):
    return {"event_key": k, "event_date": fecha, "event_time": "12:00", "event_first_player": "P%d" % a, "first_player_key": a,
            "event_second_player": "P%d" % b, "second_player_key": b, "event_type_type": tipo, "event_status": estado,
            "event_winner": ganador, "tournament_name": "Basel", "tournament_round": "ATP Basel - Final",
            "scores": [{"score_first": "6", "score_second": "3", "score_set": "1"}, {"score_first": "6", "score_second": "4", "score_set": "2"}]}


def test_clasificacion_usa_la_clave_de_api_tennis_y_el_movimiento():
    rankings = [{"ranking": 1, "points": 9550, "previousRanking": 2, "country": {}, "rowName": "A. Zverev",
                 "team": {"id": 57163, "name": "Alexander Zverev"}},
                {"ranking": 2, "points": 9000, "previousRanking": 1, "team": {"id": 99, "name": "Otro"}},
                {"ranking": 3, "points": 8000, "previousRanking": 3, "team": {"id": 7, "name": "Tercero"}},
                {"ranking": None, "team": {"id": 8}}]
    filas = rs.clasificacion(rankings, "ATP", {57163: 2072})
    assert [(f["place"], f["player_key"], f["movement"], f["points"]) for f in filas] == [
        (1, 2072, "up", "9550"), (2, rs.SINTETICO + 99, "down", "9000"), (3, rs.SINTETICO + 7, "same", "8000")]
    assert all(f["league"] == "ATP" for f in filas)


def test_h2h_local_une_archivo_y_cache_sin_repetir_y_ordena_por_fecha():
    archivo = [fila(3, 1, 2, "2026-10-30"), fila(4, 2, 1, "2026-10-31", "First Player"), fila(5, 1, 9, "2026-10-29"),
               fila(6, 1, 2, "2026-10-28", estado="")]                       # sin terminar: no cuenta
    ix = rs.indice_partidos(archivo)
    cache = {"result": {"H2H": [fila(1, 1, 2, "2025-05-01"), fila(3, 1, 2, "2026-10-30")], "firstPlayerResults": [fila(7, 1, 8, "2026-09-01")],
                        "secondPlayerResults": []}}
    r = rs.h2h_local(ix, 1, 2, cache)["result"]
    assert [f["event_key"] for f in r["H2H"]] == [4, 3, 1]
    assert [f["event_key"] for f in r["firstPlayerResults"]] == [4, 3, 5, 7]
    assert [f["event_key"] for f in r["secondPlayerResults"]] == [4, 3]


def test_el_resultado_alimenta_el_resumidor_actual_sin_cambios():
    ix = rs.indice_partidos([fila(3, 1, 2, "2026-10-30"), fila(4, 2, 1, "2026-10-31", "Second Player")])
    h2h = rs.h2h_local(ix, 1, 2)
    standings = {1: {"place": 5, "points": "5000", "movement": "up"}}
    ev = te.build_event({"event_key": 99, "first_player_key": 1, "second_player_key": 2, "surface": "Hard", "circuit": "ATP"},
                        {1: None, 2: None}, standings, h2h, __import__("datetime").date(2026, 11, 1))
    assert ev["h2h"]["first_wins"] == 2 and ev["h2h"]["second_wins"] == 0
    assert ev["players"][0]["rank"] == 5 and ev["players"][0]["movement"] == "up"


def test_sin_partidos_devuelve_listas_vacias():
    r = rs.h2h_local(rs.indice_partidos([]), 1, 2)["result"]
    assert r == {"H2H": [], "firstPlayerResults": [], "secondPlayerResults": []}
