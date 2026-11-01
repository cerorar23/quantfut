"""Estadísticas de tenis: resumen de respuestas de API-Tennis, sin red y sin datos inventados."""
import json
from datetime import date, datetime, timezone

from qf.api import tenis_estadisticas as te

HOY = date(2026, 10, 27)


def fila(key, fecha, primero, segundo, ganador, resultado, sets, ronda='WTA Tokyo - 1/16-finals', tipo='Wta Singles', estado='Finished', qual='False'):
    return {'event_key': key, 'event_date': fecha, 'event_first_player': f'P{primero}', 'first_player_key': primero,
            'event_second_player': f'P{segundo}', 'second_player_key': segundo, 'event_final_result': resultado,
            'event_winner': ganador, 'event_status': estado, 'event_type_type': tipo, 'tournament_name': 'Tokyo',
            'tournament_round': ronda, 'event_qualification': qual,
            'scores': [{'score_first': str(a), 'score_second': str(b), 'score_set': str(i + 1)} for i, (a, b) in enumerate(sets)]}


# Jugador 1: gana, gana, pierde en tres sets con tie-break, pierde en cuartos; y un partido de dobles
R1 = [fila(1, '2026-10-26', 1, 9, 'First Player', '2 - 0', [(6, 1), (6, 2)]),
      fila(2, '2026-10-20', 9, 1, 'Second Player', '0 - 2', [(3, 6), (4, 6)], '1/8-finals'),
      fila(3, '2026-09-01', 1, 8, 'Second Player', '1 - 2', [(6, 4), (6, 7), (3, 6)]),
      fila(4, '2026-05-02', 7, 1, 'Second Player', '0 - 2', [(5, 7), (4, 6)], 'WTA Rome - 1/4-finals'),
      fila(5, '2026-10-25', 1, 5, 'First Player', '2 - 0', [(6, 3), (6, 3)], tipo='Wta Doubles')]


def test_partido_resume_desde_el_punto_de_vista_del_jugador():
    ganado = te.match_summary(R1[1], 1)
    assert ganado['won'] is True and ganado['opponent'] == 'P9' and ganado['score'] == '6-3 6-4'
    perdido = te.match_summary(R1[2], 1)
    assert perdido['won'] is False and perdido['sets'] == 3 and perdido['tiebreak'] is True and perdido['stage'] == 'inicial'
    assert te.match_summary(R1[3], 1)['stage'] == 'avanzada'


def test_dobles_cancelados_y_ajenos_no_cuentan():
    assert te.match_summary(R1[4], 1) is None
    assert te.match_summary({**R1[0], 'event_status': 'Cancelled', 'event_winner': ''}, 1) is None
    assert te.match_summary(R1[0], 99) is None


def test_forma_ventanas_racha_y_porcentajes():
    f = te.form(R1, 1, HOY)
    assert [m['date'] for m in f['matches']] == ['2026-10-26', '2026-10-20', '2026-09-01', '2026-05-02']
    assert f['windows']['30'] == {'won': 2, 'lost': 0, 'rate': 1.0, 'matches': 2}
    assert f['windows']['90']['matches'] == 3 and f['windows']['360']['matches'] == 4
    assert f['streak'] == 2
    assert f['over_2_5_sets'] == .25 and f['tiebreaks'] == .25
    assert f['stages']['inicial']['matches'] == 2 and f['stages']['avanzada']['matches'] == 2
    assert 0 <= f['index'] <= 100
    assert te.form([], 1, HOY) is None


def test_partidos_suspendidos_no_cuentan_para_sets_ni_tie_breaks():
    incompleto = fila(9, '2026-10-27', 1, 9, 'First Player', '1 - 0', [(6, 3), (0, 0), (0, 0)])
    f = te.form(R1 + [incompleto], 1, HOY)
    assert te.match_summary(incompleto, 1)['complete'] is False and te.match_summary(incompleto, 1)['sets'] == 1
    assert f['complete_matches'] == 4 and f['over_2_5_sets'] == .25
    assert te.form([incompleto], 1, HOY)['over_2_5_sets'] is None


def test_la_racha_negativa_es_negativa():
    perdidos = [fila(i, f'2026-10-{20 + i}', 1, 9, 'Second Player', '0 - 2', [(3, 6), (3, 6)]) for i in range(3)]
    assert te.form(perdidos, 1, HOY)['streak'] == -3


def test_perfil_usa_solo_individuales_y_suma_superficies():
    stats = [{'season': '2026', 'type': 'singles', 'rank': '30', 'titles': '1', 'matches_won': '40', 'matches_lost': '20',
              'hard_won': '30', 'hard_lost': '10', 'clay_won': '8', 'clay_lost': '8', 'grass_won': '2', 'grass_lost': '2'},
             {'season': '2025', 'type': 'singles', 'rank': '60', 'titles': '0', 'matches_won': '20', 'matches_lost': '20',
              'hard_won': '12', 'hard_lost': '10', 'clay_won': '', 'clay_lost': '', 'grass_won': '', 'grass_lost': ''},
             {'season': '2026', 'type': 'doubles', 'rank': '500', 'titles': '9', 'matches_won': '99', 'matches_lost': '0',
              'hard_won': '99', 'hard_lost': '0', 'clay_won': '', 'clay_lost': '', 'grass_won': '', 'grass_lost': ''}]
    info = [{'player_key': 1, 'player_full_name': 'Ana Perez', 'player_country': 'Peru', 'player_bday': '23.05.2005', 'stats': stats}]
    p = te.profile(1, info, {'place': 31, 'points': '1500', 'movement': 'up'}, R1, HOY)
    assert p['name'] == 'Ana Perez' and p['age'] == 21 and p['rank'] == 31 and p['points'] == 1500
    assert p['season'] == {'season': 2026, 'titles': 1, 'won': 40, 'lost': 20, 'rate': .6667}
    assert p['career']['won'] == 60 and p['career']['lost'] == 40
    assert p['surfaces']['hard']['career'] == {'won': 42, 'lost': 20, 'rate': .6774}
    assert p['surfaces']['grass']['season']['won'] == 2
    assert [h['season'] for h in p['ranking_history']] == [2026, 2025] and p['ranking_history'][0]['rank'] == 30


def test_perfil_sin_datos_no_inventa_nada():
    p = te.profile(7, None, None, [], HOY)
    assert p['name'] is None and p['age'] is None and p['rank'] is None and p['form'] is None
    assert p['season'] is None and p['career']['rate'] is None and p['ranking_history'] == []


def test_cara_a_cara_cuenta_victorias_de_cada_lado():
    rows = [fila(1, '2026-10-26', 1, 9, 'First Player', '2 - 0', [(6, 1), (6, 2)]),
            fila(2, '2025-06-01', 9, 1, 'First Player', '2 - 1', [(6, 4), (3, 6), (6, 4)]),
            fila(3, '2024-06-01', 1, 9, 'First Player', '2 - 0', [(6, 4), (6, 4)])]
    h = te.head_to_head(rows, 1, 9)
    assert (h['first_wins'], h['second_wins']) == (2, 1) and h['matches'][0]['date'] == '2026-10-26'


def test_evento_completo_y_lectura_del_json_publico(tmp_path):
    h2h = {'result': {'H2H': [R1[0]], 'firstPlayerResults': R1, 'secondPlayerResults': []}}
    fixture = {'event_key': 12345, 'first_player_key': 1, 'second_player_key': 9, 'surface': 'Hard', 'circuit': 'WTA'}
    event = te.build_event(fixture, {1: None, 9: None}, {1: {'place': 3, 'points': '5000', 'movement': 'same'}}, h2h, HOY)
    assert event['event_id'] == '12345' and event['players'][0]['rank'] == 3 and event['players'][1]['form'] is None
    ahora = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
    feed = tmp_path / 'tennis_stats.json'
    feed.write_text(json.dumps({'generated_at': '2026-10-27T11:00:00+00:00', 'events': {'12345': event, 'x': {'players': []}}}), encoding='utf-8')
    leido = te.read_feed(feed, ahora)
    assert leido['state'] == 'ok' and list(leido['events']) == ['12345']
    feed.write_text(json.dumps({'generated_at': '2026-10-26T11:00:00+00:00', 'events': {'12345': event}}), encoding='utf-8')
    assert te.read_feed(feed, ahora) == {'state': 'stale', 'events': {}}
    assert te.read_feed(tmp_path / 'no_existe.json', ahora)['state'] == 'unavailable'


def test_la_ruta_publica_valida_el_id(monkeypatch, tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from qf.api import web
    feed = tmp_path / 'tennis_stats.json'
    ahora = datetime.now(timezone.utc).isoformat()
    evento = {'event_id': '12345', 'players': [{}, {}], 'h2h': {}}
    feed.write_text(json.dumps({'generated_at': ahora, 'events': {'12345': evento}}), encoding='utf-8')
    monkeypatch.setenv('QF_TENNIS_STATS_FEED', str(feed))
    te._cached.cache_clear()
    app = FastAPI()
    app.include_router(web.router)
    client = TestClient(app)
    ok = client.get('/web/deportes/tenis/estadisticas/12345')
    assert ok.status_code == 200 and ok.json()['source'] == 'API-Tennis' and ok.headers['cache-control'] == 'no-store'
    assert client.get('/web/deportes/tenis/estadisticas/99999').status_code == 404
    assert client.get('/web/deportes/tenis/estadisticas/abc').status_code == 404
