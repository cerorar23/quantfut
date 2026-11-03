"""Conversor SportsAPIPro -> `get_fixtures` de API-Tennis: ids que el motor ya conoce, orientación y estados."""
import json
from datetime import datetime, timezone

from qf.ingest import tenis_formato_api_tennis as tf

TS = int(datetime(2026, 10, 30, 14, 30, tzinfo=timezone.utc).timestamp())


def ev(i=1, estado="finished", desc="Ended", gana=1, categoria="ATP", torneo="Basel, Switzerland", utid=2400, **k):
    return {"id": i, "startTimestamp": TS, "status": {"type": estado, "description": desc}, "winnerCode": gana,
            "homeTeam": {"id": 10, "name": "Jan-Lennard Struff", "shortName": "J. Struff"},
            "awayTeam": {"id": 11, "name": "Nuno Borges", "shortName": "N. Borges"},
            "homeScore": {"current": 2, "period1": 6, "period2": 7, "period2TieBreak": 4},
            "awayScore": {"current": 0, "period1": 3, "period2": 6, "period2TieBreak": 7},
            "roundInfo": {"name": "Round of 16"}, "season": {"year": "2026"},
            "tournament": {"name": torneo, "category": {"name": categoria}, "uniqueTournament": {"id": utid}}, **k}


def ix(**k):
    base = {"jugadores": {10: 78, 11: 77}, "torneos": {2400: (1700, "Basel")}, "partidos": {}}
    return {**base, **k}


def test_partido_nuevo_usa_las_claves_de_api_tennis_cuando_las_conoce():
    f = tf.convertir(ev(), ix())
    assert (f["first_player_key"], f["second_player_key"], f["tournament_key"]) == (78, 77, 1700)
    assert f["event_key"] == tf.SINTETICO + 1 and f["tournament_name"] == "Basel"
    assert (f["event_status"], f["event_winner"], f["event_final_result"]) == ("Finished", "First Player", "2 - 0")
    assert f["scores"] == [{"score_first": "6", "score_second": "3", "score_set": "1"},
                           {"score_first": "7", "score_second": "6", "score_set": "2"}]   # sin puntos de desempate
    assert (f["event_date"], f["event_time"], f["event_type_type"]) == ("2026-10-30", "14:30", "Atp Singles")


def test_jugador_o_torneo_desconocido_entra_con_clave_sintetica():
    f = tf.convertir(ev(), ix(jugadores={10: 78}, torneos={}))
    assert f["second_player_key"] == tf.SINTETICO + 11 and f["tournament_key"] == tf.SINTETICO + 2400
    assert f["tournament_name"] == "Basel"                          # sin la coma del país


def test_partido_ya_emparejado_conserva_event_key_y_quien_era_primero():
    conocido = {"event_key": 12170000, "first_key": 77, "second_key": 78, "directo": 0}
    f = tf.convertir(ev(gana=1), ix(partidos={1: conocido}))
    assert f["event_key"] == 12170000 and f["first_player_key"] == 77 and f["event_first_player"] == "N. Borges"
    assert f["event_winner"] == "Second Player"                     # ganó el local, que en API-Tennis era el segundo
    assert f["event_final_result"] == "0 - 2" and f["scores"][0] == {"score_first": "3", "score_second": "6", "score_set": "1"}


def test_estados():
    assert tf.estado(ev(desc="Retired")) == "Retired" and tf.estado(ev(desc="Walkover")) == "Walk Over"
    assert tf.estado(ev(estado="notstarted")) == "" and tf.estado(ev(estado="canceled")) == "Cancelled"
    assert tf.estado(ev(estado="inprogress")) == "Set 2" and tf.estado(ev(estado="postponed")) == "Interrupted"
    f = tf.convertir(ev(estado="notstarted", gana=None), ix())
    assert f["event_winner"] is None and f["event_final_result"] == "-" and f["event_live"] == "0"


def test_dobles_y_otros_circuitos_no_se_convierten():
    assert tf.convertir(ev(torneo="Basel, Doubles"), ix()) is None
    assert tf.convertir(ev(categoria="Challenger"), ix()) is None


def test_respuesta_filtra_circuito_y_fechas_y_sale_en_el_formato_del_motor():
    eventos = [ev(1), ev(2, categoria="WTA"), dict(ev(3), startTimestamp=TS + 10 * 86400)]
    cuerpo = json.loads(tf.respuesta(eventos, ix(), "265", "2026-10-30", "2026-11-01"))
    assert cuerpo["success"] == 1 and [r["sofascore_event"] for r in cuerpo["result"]] == [1]
    assert json.loads(tf.respuesta(eventos, ix(), "266", "2026-10-30", "2026-11-01"))["result"][0]["event_type_type"] == "Wta Singles"


def test_claves_de_jugador_ambiguas_no_se_usan():
    assert tf.convertir(ev(), ix(jugadores={}))["first_player_key"] == tf.SINTETICO + 10
