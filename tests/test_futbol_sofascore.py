import copy
import os
from pathlib import Path

import pytest

from qf.ingest import futbol_sofascore as fs
from qf.ingest.sofascore_local import normalize_local_bundle

MATCH = 'it.serie_a:2526:genoa-lecce:20250823'


def blocks():
    def team(tid, name):
        return {'id': tid, 'name': name, 'sport': {'id': 1}, 'gender': 'M', 'national': False}

    def item(key, h, a):
        return {'key': key, 'homeValue': h, 'awayValue': a}

    def player(tid, pid, sub=False, stats=None):
        return {'teamId': tid, 'player': {'id': pid, 'name': 'P%d' % pid}, 'substitute': sub,
                'position': 'M', 'jerseyNumber': str(pid % 90), 'statistics': stats if stats is not None else {}}

    home = [player(10, 1 + i, stats={'minutesPlayed': 90, 'rating': 6.5, 'goals': 1 if i == 0 else 0,
                                     'totalPass': 30, 'accuratePass': 25, 'kilometersCovered': 10.5,
                                     'expectedGoals': 0.31, 'keyPass': 2, 'penaltyWon': 1, 'ballCarriesCount': 14,
                                     'metersCoveredSprintingKm': 0.4, 'dispossessed': 3,
                                     'ratingVersions': {'original': 6.5, 'alternative': 6.4}}) for i in range(11)]
    home.append(player(10, 40, sub=True))  # suplente sin minutos
    away = [player(20, 100 + i, stats={'minutesPlayed': 90, 'rating': 6.0}) for i in range(11)]
    return {
        'event': {'id': 555, 'startTimestamp': 1755970200, 'status': {'type': 'finished', 'code': 100},
                  'homeTeam': team(10, 'Genoa'), 'awayTeam': team(20, 'Lecce'),
                  'homeScore': {'normaltime': 0, 'current': 0, 'period1': 0},
                  'awayScore': {'normaltime': 1, 'current': 1, 'period1': 1},
                  'tournament': {'uniqueTournament': {'id': 23}, 'category': {'alpha2': 'IT'}},
                  'season': {'year': '25/26'}, 'roundInfo': {'round': 1},
                  'referee': {'id': 77, 'name': 'R', 'games': 388, 'yellowCards': 1804, 'redCards': 54, 'yellowRedCards': 34,
                              'country': {'alpha2': 'IT'}},
                  'venue': {'name': 'S', 'city': {'name': 'Genoa'}, 'capacity': 33205,
                            'venueCoordinates': {'latitude': 44.4, 'longitude': 8.9}},
                  'time': {'injuryTime1': 2, 'injuryTime2': 4}, 'attendance': 27626},
        'statistics': {'statistics': [
            {'period': 'ALL', 'groups': [{'statisticsItems': [
                item('expectedGoals', 0.5, 0.37), item('totalShotsOnGoal', 5, 7), item('shotsOnGoal', 2, 3),
                item('cornerKicks', 3, 7), item('ballPossession', 59, 41), item('passes', 435, 294),
                item('goalsPrevented', 0, 0.7043), item('highClaims', 1, 2), item('dispossessed', 8, 12),
                item('aerialDuelsPercentage', 16, 19)]}]},
            {'period': '1ST', 'groups': [{'statisticsItems': [item('ballPossession', 50, 50),
                                                              item('duelWonPercent', 55, 45),
                                                              item('cornerKicks', 1, 4), item('expectedGoals', 0.2, 0.1),
                                                              item('totalShotsOnGoal', 2, 3), item('shotsOnGoal', 1, 2),
                                                              item('yellowCards', 0, 2), item('redCards', 0, 1)]}]}]},
        'lineups': {'confirmed': True,
                    'home': {'formation': '4-2-3-1', 'players': home,
                             'missingPlayers': [{'player': {'id': 90, 'name': 'Lesionado'}, 'type': 'missing',
                                                 'reason': 1, 'description': 'Thigh Injury'}]},
                    'away': {'formation': '4-3-3', 'players': away, 'missingPlayers': []}},
        'managers': {'homeManager': {'id': 1, 'name': 'A'}, 'awayManager': {'id': 2, 'name': 'B'}},
        'shotmap': {'shotmap': [
            {'id': 9001, 'isHome': True, 'player': {'id': 3, 'name': 'P3'}, 'shotType': 'miss', 'situation': 'free-kick',
             'bodyPart': 'right-foot', 'playerCoordinates': {'x': 18.7, 'y': 70.9}, 'goalMouthLocation': 'close-right',
             'goalMouthCoordinates': {'x': 0, 'y': 43.9, 'z': 26.4}, 'xg': 0.05, 'xgot': 0, 'time': 82,
             'timeSeconds': 4882, 'blockCoordinates': {'x': 3.7, 'y': 47.3, 'z': 0}, 'goalType': 'regular',
             'goalkeeper': {'id': 882604, 'name': 'Portero'}, 'addedTime': 5, 'periodTimeSeconds': 249},
            {'id': 9002, 'isHome': False, 'player': {'id': 101, 'name': 'P101'}, 'shotType': 'goal', 'xg': 0.4,
             'xgot': 0.6, 'time': 12, 'timeSeconds': 700}]},
        'incidents': {'incidents': [
            {'incidentType': 'card', 'incidentClass': 'yellow', 'isHome': True, 'time': 86,
             'player': {'id': 2, 'name': 'P2'}, 'reason': 'Foul'},
            {'incidentType': 'substitution', 'incidentClass': 'regular', 'isHome': True, 'time': 60,
             'playerIn': {'id': 40, 'name': 'P40'}, 'playerOut': {'id': 5, 'name': 'P5'}},
            {'incidentType': 'period', 'text': 'FT', 'homeScore': 0, 'awayScore': 1, 'time': 90, 'addedTime': 999},
            {'incidentType': 'goal', 'incidentClass': 'regular', 'isHome': False, 'time': 12, 'player': {'id': 101, 'name': 'P101'},
             'assist1': {'id': 102, 'name': 'P102'}, 'homeScore': 0, 'awayScore': 1,
             'footballPassingNetworkAction': [{'player': {'id': 102, 'name': 'P102'}, 'eventType': 'pass', 'time': 11,
                                               'playerCoordinates': {'x': 41.2, 'y': 72.3},
                                               'passEndCoordinates': {'x': 55.9, 'y': 78.3}, 'isHome': False}]},
            {'incidentType': 'varDecision', 'incidentClass': 'cardUpgrade', 'isHome': True, 'time': 45, 'addedTime': 6,
             'confirmed': False},
            {'incidentType': 'injuryTime', 'length': 5, 'time': 90, 'addedTime': 0}]},
        'momentum': {'graphPoints': [{'minute': 1, 'value': -5}, {'minute': 45.5, 'value': 12}, {'minute': 90.5, 'value': 53}]},
        'average_positions': {'home': [{'player': {'id': 1, 'name': 'P1'}, 'averageX': 39.8, 'averageY': 37.3, 'pointsCount': 28}],
                              'away': [{'player': {'id': 100, 'name': 'P100'}, 'averageX': 60.1, 'averageY': 50.0, 'pointsCount': 20}],
                              'substitutions': []},
    }


def entities(data=None):
    data = data or blocks()
    states = {n: {'state': 'ok', 'sha256': 'x' * 64, 'fetched_at': '2026-10-30T14:44:%02d+00:00' % (10 + i), 'bytes': 10}
              for i, n in enumerate(data)}
    manifest = {'id': 555, 'observation': {'observed_at_utc': '2026-10-30T14:44:37+00:00'}}
    row, _raw, _meta = normalize_local_bundle('it.serie_a', data, states, manifest)
    return fs.build_entities(MATCH, data, row), row, states


def test_cada_tipo_sale_con_sus_filas_y_claves():
    out, _row, _states = entities()
    assert {k: len(v) for k, v in out.items()} == {
        'alineacion': 2, 'jugador': 23, 'baja': 1, 'entrenador': 2, 'contexto': 1, 'tiro': 2, 'incidencia': 6,
        'equipo': 4, 'momentum': 3, 'posicion': 2}
    for tipo, rows in out.items():
        assert all(r['match_id'] == MATCH and r['tipo'] == tipo and r['fuente'] == 'sofascore' for r in rows), tipo
        assert all(r['side'] in ('', 'home', 'away') and isinstance(r['jugador_id'], int) for r in rows), tipo
    claves = [(r['tipo'], r['side'], r['jugador_id'], r['evento']) for rows in out.values() for r in rows]
    assert len(claves) == len(set(claves))  # la clave primaria no se repite


def test_jugadores_conservan_al_suplente_sin_minutos_y_mapean_estadisticas():
    out, _row, _states = entities()
    by_id = {r['jugador_id']: r for r in out['jugador']}
    first = by_id[1]
    assert (first['titular'], first['minutos'], first['nota'], first['goles'], first['pases'], first['km']) == (
        True, 90.0, 6.5, 1, 30, 10.5)
    assert (first['xg'], first['pases_clave'], first['penaltis_ganados'], first['conducciones'],
            first['km_esprint'], first['perdidas_balon'], first['nota_alternativa']) == (0.31, 2, 1, 14, 0.4, 3, 6.4)
    bench = by_id[40]
    assert bench['titular'] is False and bench['minutos'] is None and bench['goles'] is None and bench['xg'] is None
    assert all(r['id_en_fuente'] == r['jugador_id'] for r in by_id.values())


def test_incidencias_tiros_equipo_momentum_y_posiciones():
    out, _row, _states = entities()
    inc = out['incidencia']
    sub = next(i for i in inc if i['subtipo'] == 'substitution')
    assert (sub['jugador_id'], sub['jugador2_id'], sub['side']) == (5, 40, 'home')  # sale 5, entra 40
    period = next(i for i in inc if i['subtipo'] == 'period')
    assert period['anadido'] is None and period['side'] == '' and period['texto'] == 'FT'  # 999 es un marcador
    goal = next(i for i in inc if i['subtipo'] == 'goal')
    assert (goal['jugador2_id'], goal['marcador_visita']) == (102, 1)
    assert goal['red_pases'] == [[102, 'pass', 11, 41.2, 72.3, 55.9, 78.3]]
    var = next(i for i in inc if i['subtipo'] == 'varDecision')
    assert var['clase'] == 'cardUpgrade' and var['confirmada'] is False
    assert next(i for i in inc if i['subtipo'] == 'injuryTime')['duracion'] == 5
    shots = {r['evento']: r for r in out['tiro']}
    assert shots[9001]['side'] == 'home' and shots[9001]['xg'] == 0.05 and shots[9001]['boca_z'] == 26.4
    assert (shots[9001]['bloqueo_x'], shots[9001]['tipo_gol'], shots[9001]['portero_id'], shots[9001]['anadido'],
            shots[9001]['segundos_periodo']) == (3.7, 'regular', 882604, 5, 249)
    assert shots[9002]['side'] == 'away' and shots[9002]['resultado'] == 'goal'
    team = {(r['side'], r['evento']): r for r in out['equipo']}
    assert team[('home', 0)]['posesion'] == 59 and team[('away', 0)]['goles_evitados'] == 0.7043
    assert team[('home', 0)]['pases'] == 435 and team[('home', 0)]['atrapadas_altas'] == 1
    assert team[('home', 0)]['perdidas_balon'] == 8 and team[('home', 0)]['pct_duelos_aereos'] == 16
    assert team[('home', 1)]['posesion'] == 50 and team[('home', 1)]['pct_duelos'] == 55  # primera parte
    # por mitad no hay otro sitio: matches solo guarda el partido completo
    assert (team[('away', 1)]['corners'], team[('away', 1)]['xg'], team[('away', 1)]['tiros_totales'],
            team[('away', 1)]['tiros_puerta'], team[('away', 1)]['amarillas'], team[('away', 1)]['rojas']) == (4, 0.1, 3, 2, 2, 1)
    assert team[('home', 0)]['corners'] is None and team[('home', 0)]['xg'] is None  # el partido completo vive en matches
    assert ('home', 2) not in team  # la fuente no trae segunda parte
    points = {r['evento']: r for r in out['momentum']}
    assert points[91]['minuto_decimal'] == 45.5 and points[91]['minuto'] == 45 and points[91]['momentum'] == 12
    assert points[181]['minuto_decimal'] == 90.5  # los medios minutos no chocan con los enteros
    pos = {r['jugador_id']: r for r in out['posicion']}
    assert (pos[1]['pos_x'], pos[1]['pos_y'], pos[1]['puntos'], pos[1]['side']) == (39.8, 37.3, 28, 'home')
    assert out['contexto'][0]['asistencia'] == 27626
    # quién arbitra: la trayectoria (partidos, tarjetas) se contó al descargar y es posterior al partido
    assert (out['contexto'][0]['nombre'], out['contexto'][0]['id_en_fuente']) == ('R', 77)


def test_lo_que_ya_esta_en_matches_no_se_repite():
    # marcador, xG, córners, tiros totales y a puerta y tarjetas del partido completo ya viven en `matches`;
    # por mitad solo existen aquí
    assert not set(fs.EN_MATCHES.values()) & set(fs.EQUIPO.values())
    assert 'asistencia' not in fs.JUGADOR and 'arbitro' not in fs.JUGADOR


def test_la_tabla_cubre_todo_lo_que_trae_el_scraper_salvo_lo_decidido_fuera():
    """Cada clave de estadística de jugador o de equipo de un partido real tiene columna, salvo lo ya guardado en
    `matches` y metadatos del origen."""
    import json
    export = Path(os.environ.get('QF_EXPORT_SOFASCORE', r'C:\Users\huye\Documents\Codex\2026-10-29\fun\outputs\sofascore'))
    archivo = export / 'Premier-Fulham-Bournemouth-14023948-datos.json'
    if not archivo.exists():
        pytest.skip('export de ejemplo no disponible')
    d = json.loads(archivo.read_text(encoding='utf-8'))['bloques']
    jugador = set()
    for side in ('home', 'away'):
        for p in d['alineaciones'][side]['players']:
            jugador |= set(p.get('statistics') or {})
    assert jugador - set(fs.JUGADOR.values()) <= {'ratingVersions', 'statisticsType'}
    equipo = set()
    for periodo in d['estadisticas']['statistics']:
        for g in periodo['groups']:
            equipo |= {i['key'] for i in g['statisticsItems']}
    assert equipo - set(fs.EQUIPO.values()) <= set(fs.EN_MATCHES.values())
    tiro = set()
    for t in d['tiros']['shotmap']:
        tiro |= set(t)
    assert tiro <= {'id', 'isHome', 'player', 'shotType', 'situation', 'bodyPart', 'playerCoordinates',
                    'goalMouthLocation', 'goalMouthCoordinates', 'xg', 'xgot', 'time', 'timeSeconds', 'addedTime',
                    'blockCoordinates', 'goalType', 'goalkeeper', 'periodTimeSeconds', 'incidentType', 'draw',
                    'reversedPeriodTime', 'reversedPeriodTimeSeconds'}


def test_numeros_invalidos_no_rompen_la_carga():
    assert fs.num(None) is None and fs.num(True) is None and fs.num('x') is None
    assert fs.num(float('nan')) is None and fs.num(40000, integer=True) is None
    assert fs.num(7.0, integer=True) == 7


def test_baja_con_motivo_no_entero_se_guarda_sin_codigo():
    data = blocks()
    data['lineups']['home']['missingPlayers'][0]['reason'] = 'raro'
    out, _row, _states = entities(data)
    assert out['baja'][0]['motivo_codigo'] is None and out['baja'][0]['estado'] == 'missing'


# ── base de datos real: la migración se aplica y se deshace dentro de una transacción ──────────────

def pg_connection():
    if os.getenv('QF_TEST_POSTGRES') != '1':
        pytest.skip('requires PostgreSQL')
    import psycopg
    return psycopg.connect(os.environ['PG_DSN'])


STUBS = """
CREATE SCHEMA qf_t; SET LOCAL search_path = qf_t, public;
CREATE TABLE matches (match_id TEXT PRIMARY KEY, referee TEXT, referee_fotmob TEXT, stadium_id BIGINT,
    kickoff_utc TIMESTAMPTZ DEFAULT now(), home_team_id BIGINT DEFAULT 1, away_team_id BIGINT DEFAULT 2);
CREATE TABLE fotmob_partido (match_id TEXT PRIMARY KEY, source_match_id TEXT, recibido_en TIMESTAMPTZ DEFAULT now(),
    formacion_local TEXT, formacion_visita TEXT, entrenador_local_id BIGINT, entrenador_local TEXT,
    entrenador_visita_id BIGINT, entrenador_visita TEXT, clima_temperatura_c REAL, clima_humedad REAL,
    clima_precipitacion REAL, clima_nubosidad REAL);
CREATE TABLE fotmob_jugador_partido (match_id TEXT, side TEXT, jugador_id BIGINT, nombre TEXT, titular BOOLEAN,
    posicion_id INTEGER, posicion_habitual_id INTEGER, camiseta TEXT, edad INTEGER, valor_mercado BIGINT, rating REAL);
CREATE TABLE fotmob_baja (match_id TEXT, side TEXT, jugador_id BIGINT, nombre TEXT, edad INTEGER, posicion_id INTEGER,
    valor_mercado BIGINT, tipo TEXT, lesion_id INTEGER, regreso_texto TEXT, regreso_fecha TIMESTAMPTZ);
CREATE TABLE historical_football_player_stats (provider TEXT, source_match_id TEXT, side TEXT, source_player_id BIGINT,
    player_name TEXT, minutes REAL, starter BOOLEAN, statistics JSONB);
CREATE VIEW v_fotmob_jugador_partido AS
  SELECT j.match_id, j.side, j.jugador_id, j.nombre, j.titular, j.posicion_id, j.posicion_habitual_id, j.camiseta,
         j.edad, j.valor_mercado, j.rating, ps.minutes AS minutos, ps.statistics AS estadisticas
    FROM fotmob_jugador_partido j JOIN fotmob_partido p USING (match_id)
    LEFT JOIN historical_football_player_stats ps ON ps.provider = 'fotmob' AND ps.source_match_id = p.source_match_id
         AND ps.side = j.side AND ps.source_player_id = j.jugador_id;
CREATE TABLE clima_era5_partido (match_id TEXT, temperatura_c REAL, humedad_pct REAL, viento_ms REAL,
    precipitacion_mm REAL, nubosidad_pct REAL, calculado_en TIMESTAMPTZ DEFAULT now());
CREATE TABLE estadios (stadium_id BIGINT, name TEXT, city TEXT, country TEXT, lat DOUBLE PRECISION, lon DOUBLE PRECISION,
    capacity INTEGER, surface TEXT);
CREATE TABLE estadio_altitud (stadium_id BIGINT, altitud_m REAL, fuente TEXT, recibido_en TIMESTAMPTZ DEFAULT now());
"""

FM_STATS = ('[{"key":"top_stats","stats":{"G":{"key":"goals","stat":{"type":"integer","value":1}},'
            '"M":{"key":"minutes_played","stat":{"type":"integer","value":90}},'
            '"P":{"key":"accurate_passes","stat":{"type":"fractionWithPercentage","value":30,"total":40}},'
            '"T":{"key":"matchstats.headers.tackles","stat":{"type":"integer","value":3}}}}]')


def with_schema(connection):
    connection.execute(STUBS)
    root = Path(__file__).resolve().parents[1]
    for name in ('094_futbol_dato_unico.sql', '096_futbol_dato_ampliado.sql', '097_futbol_dato_mitades.sql'):
        sql = (root / 'db' / name).read_text(encoding='utf-8')
        connection.execute(sql.replace('BEGIN;', '').replace('COMMIT;', ''))
    connection.execute("INSERT INTO matches (match_id) VALUES (%s)", (MATCH,))


def item_for(data=None, sha=None):
    out, row, states = entities(data)
    if sha:
        row = dict(row, raw_sha256=sha)
    return {'match_id': MATCH, 'row': row, 'states': states, 'entities': out}


def add_fotmob(connection, match=MATCH):
    connection.execute("INSERT INTO fotmob_partido (match_id, source_match_id, formacion_local, formacion_visita, "
                       "entrenador_local_id, entrenador_local, entrenador_visita_id, entrenador_visita) "
                       "VALUES (%s,'fm1','4-4-2','3-5-2',9,'DT local',8,'DT visita')", (match,))
    connection.execute("INSERT INTO fotmob_jugador_partido VALUES (%s,'home',777,'P3',true,5,5,'10',27,5000000,7.1)", (match,))
    connection.execute("INSERT INTO fotmob_jugador_partido VALUES (%s,'home',778,'Solo FotMob',false,6,6,'20',20,NULL,6.0)", (match,))
    connection.execute("INSERT INTO historical_football_player_stats VALUES ('fotmob','fm1','home',777,'P3',90,true,%s::jsonb)", (FM_STATS,))
    connection.execute("INSERT INTO fotmob_baja VALUES (%s,'home',779,'Lesionado FM',30,5,NULL,'missing',1,'Lesion','2026-12-01T00:00:00+00:00')", (match,))


def por_tipo(connection, **filtros):
    donde = ' AND '.join('%s = %%s' % k for k in filtros) or 'TRUE'
    return dict(connection.execute("SELECT tipo, count(*) FROM futbol.dato WHERE %s GROUP BY 1" % donde,
                                   tuple(filtros.values())).fetchall())


def test_pg_todo_cae_en_una_sola_tabla_sin_repetidos_y_con_ids_canonicos():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            totals = fs.apply_batch(connection, [item_for()])
            assert totals['partidos'] == 1 and totals['filas_jugador'] == 23
            assert por_tipo(connection) == {'jugador': 23, 'baja': 1, 'alineacion': 2, 'entrenador': 2, 'contexto': 1,
                                            'tiro': 2, 'incidencia': 6, 'equipo': 4, 'momentum': 3, 'posicion': 2}
            fila = connection.execute("SELECT jugador_id, id_en_fuente, edad, fuente, pit FROM futbol.dato "
                                      "WHERE tipo='jugador' AND jugador_id=1").fetchone()
            assert fila[0] == fila[1] == 1 and fila[3] == 'sofascore' and fila[4] == 'posterior'
            assert connection.execute("SELECT pit, estado FROM futbol.dato WHERE tipo='baja'").fetchone() == ('reconstruido', 'missing')
            assert connection.execute("SELECT count(*) FROM futbol.jugador").fetchone()[0] >= 23
            tiro = connection.execute("SELECT evento, nombre, xg, boca_z, side FROM futbol.dato WHERE tipo='tiro' AND evento=9001").fetchone()
            assert tiro == (9001, 'P3', pytest.approx(0.05, abs=1e-6), pytest.approx(26.4, abs=1e-4), 'home')
            period = connection.execute("SELECT subtipo, side, anadido FROM futbol.dato WHERE tipo='incidencia' AND subtipo='period'").fetchone()
            assert period == ('period', '', None)
            gol = connection.execute("SELECT red_pases->0->>1, red_pases->0->>0 FROM futbol.dato WHERE subtipo='goal'").fetchone()
            assert gol == ('pass', '102')  # la red de pases se guarda como JSONB consultable
            assert connection.execute("SELECT asistencia FROM futbol.dato WHERE tipo='contexto'").fetchone() == (27626,)
            # repetir el mismo original no cambia nada
            assert fs.apply_batch(connection, [item_for()])['sin_cambios'] == 1
            assert connection.execute("SELECT count(*) FROM futbol.dato").fetchone()[0] == 46
        finally:
            connection.rollback()


def test_pg_adaptador_fotmob_traduce_campos_enlaza_ids_y_gana_la_prioridad():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            fs.apply_batch(connection, [item_for()])
            add_fotmob(connection)
            connection.execute("SELECT futbol.vincular_jugador('fotmob',777,3,'nombre_en_partido',5)")
            resultado = {r[0]: r[1:] for r in connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()}
            assert resultado['jugador'] == (1, 2) and resultado['baja'] == (1, 1)
            assert resultado['alineacion'] == (1, 2) and resultado['entrenador'] == (1, 2)
            cols = "jugador_id, id_en_fuente, fuente, minutos, nota, goles, pases, pases_acertados, entradas, edad, valor_mercado, camiseta"
            rows = {r[0]: r for r in connection.execute("SELECT %s FROM futbol.dato WHERE tipo='jugador' ORDER BY 1" % cols)}
            assert set(rows) == {3, -778}  # las 23 filas de SofaScore las reemplazan las de FotMob
            assert rows[3][1:] == (777, 'fotmob', 90.0, 7.1, 1, 40, 30, 3, 27, 5000000, '10')
            assert rows[-778][2] == 'fotmob' and rows[-778][4] == 6.0
            assert connection.execute("SELECT jugador_id FROM futbol.jugador_fuente_id WHERE fuente='fotmob' AND id_en_fuente=779").fetchone() == (-779,)
            fuentes = dict(connection.execute("SELECT tipo, min(fuente) FROM futbol.dato GROUP BY 1").fetchall())
            assert {fuentes[t] for t in ('jugador', 'baja', 'alineacion', 'entrenador')} == {'fotmob'}
            assert fuentes['tiro'] == fuentes['equipo'] == fuentes['momentum'] == 'sofascore'
            # SofaScore con un original nuevo ya no pisa lo que FotMob posee
            totals = fs.apply_batch(connection, [item_for(sha='e' * 64)])
            assert totals['tipo_de_mejor_fuente'] == 4 and 'filas_jugador' not in totals
            assert connection.execute("SELECT count(DISTINCT fuente) FROM futbol.dato WHERE tipo='jugador'").fetchone()[0] == 1
            # idempotente: repetir el adaptador no cambia las filas
            antes = connection.execute("SELECT count(*) FROM futbol.dato").fetchone()[0]
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()
            assert connection.execute("SELECT count(*) FROM futbol.dato").fetchone()[0] == antes
        finally:
            connection.rollback()


def test_pg_vincular_jugador_mueve_las_filas_al_id_de_sofascore():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            add_fotmob(connection)
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()
            assert connection.execute("SELECT count(*) FROM futbol.dato WHERE jugador_id=-778").fetchone()[0] == 1
            connection.execute("INSERT INTO futbol.jugador VALUES (5000, 'Solo FotMob')")
            movidas = connection.execute("SELECT futbol.vincular_jugador('fotmob',778,5000,'nombre_en_partido',4)").fetchone()[0]
            assert movidas == 1
            assert connection.execute("SELECT count(*) FROM futbol.dato WHERE jugador_id=-778").fetchone()[0] == 0
            assert connection.execute("SELECT count(*) FROM futbol.dato WHERE jugador_id=5000 AND tipo='jugador'").fetchone()[0] == 1
            assert connection.execute("SELECT count(*) FROM futbol.jugador WHERE jugador_id=-778").fetchone()[0] == 0
        finally:
            connection.rollback()


def test_pg_entidad_vacia_no_se_adueña_y_un_id_de_fuente_apunta_a_un_partido():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            data = blocks()
            data['lineups']['home']['missingPlayers'] = []  # SofaScore no informa bajas
            fs.apply_batch(connection, [item_for(data)])
            assert 'baja' not in por_tipo(connection) and por_tipo(connection)['jugador'] == 23
            connection.execute("INSERT INTO matches (match_id) VALUES ('otro')")
            other = item_for()
            other['match_id'] = 'otro'
            with pytest.raises(ValueError, match='source_match_points_to_other_match'):
                fs.apply_batch(connection, [other])
            prios = dict(connection.execute("SELECT fuente, prioridad FROM futbol.fuente").fetchall())
            assert prios['fotmob'] < prios['sofascore'] < prios['api_football']
        finally:
            connection.rollback()


def test_pg_clima_y_estadio_entran_en_la_misma_tabla_con_era5_y_opentopodata_primero():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            connection.execute("INSERT INTO matches (match_id, stadium_id) VALUES ('a', 1), ('b', NULL)")
            connection.execute("INSERT INTO clima_era5_partido (match_id, temperatura_c, humedad_pct, viento_ms) VALUES ('a',20,50,3)")
            connection.execute("INSERT INTO fotmob_partido (match_id, clima_temperatura_c, clima_humedad) VALUES ('a',99,99), ('b',15,70)")
            assert connection.execute("SELECT futbol.cargar_clima()").fetchone()[0] == 2
            clima = {r[0]: r[1:] for r in connection.execute("SELECT match_id, temperatura_c, fuente, viento_ms FROM futbol.dato WHERE tipo='clima'")}
            assert clima == {'a': (20.0, 'era5', 3.0), 'b': (15.0, 'fotmob', None)}  # ERA5 gana; FotMob solo donde falta
            connection.execute("SELECT futbol.cargar_clima()")  # idempotente y FotMob no pisa a ERA5
            assert connection.execute("SELECT temperatura_c, fuente FROM futbol.dato WHERE tipo='clima' AND match_id='a'").fetchone() == (20.0, 'era5')
            connection.execute("INSERT INTO estadios VALUES (1,'Estadio','Quito','EC',-0.2,-78.5,30000,'grass')")
            connection.execute("INSERT INTO estadio_altitud (stadium_id, altitud_m, fuente) VALUES (1, 2850, 'opentopodata/mapzen')")
            assert connection.execute("SELECT futbol.cargar_estadio()").fetchone()[0] == 1
            assert connection.execute("SELECT altitud_m, estadio_capacidad, fuente FROM futbol.dato WHERE tipo='estadio'").fetchone() == (2850.0, 30000, 'opentopodata')
        finally:
            connection.rollback()


OLD_DDL = """
              CREATE TABLE futbol.entidad_fuente (match_id TEXT, entidad TEXT, fuente TEXT, filas INT,
                                                  recibido_en TIMESTAMPTZ, PRIMARY KEY (match_id, entidad));
              CREATE TABLE futbol.jugador_partido (match_id TEXT, side TEXT, jugador_id BIGINT, fuente TEXT, nombre TEXT,
                posicion TEXT, titular BOOLEAN, camiseta TEXT, minutos REAL, nota REAL, goles SMALLINT, asistencias SMALLINT,
                xa REAL, tiros_puerta SMALLINT, tiros_fuera SMALLINT, tiros_bloq SMALLINT, grandes_ocasiones_creadas SMALLINT,
                grandes_ocasiones_falladas SMALLINT, pases SMALLINT, pases_acertados SMALLINT, balones_largos SMALLINT,
                balones_largos_acertados SMALLINT, centros SMALLINT, centros_acertados SMALLINT, duelos_ganados SMALLINT,
                duelos_perdidos SMALLINT, aereos_ganados SMALLINT, aereos_perdidos SMALLINT, entradas SMALLINT,
                entradas_ganadas SMALLINT, intercepciones SMALLINT, despejes SMALLINT, recuperaciones SMALLINT,
                perdidas SMALLINT, faltas SMALLINT, faltas_recibidas SMALLINT, fuera_juego SMALLINT, toques SMALLINT,
                paradas SMALLINT, km REAL, sprints SMALLINT, vel_max REAL, pit TEXT, edad SMALLINT, valor_mercado BIGINT,
                posicion_id INTEGER, id_en_fuente BIGINT);
              CREATE TABLE futbol.baja (match_id TEXT, side TEXT, jugador_id BIGINT, fuente TEXT, nombre TEXT, tipo TEXT,
                motivo_codigo INT, descripcion TEXT, pit TEXT, id_en_fuente BIGINT, regreso_texto TEXT, regreso_fecha TIMESTAMPTZ);
              CREATE TABLE futbol.alineacion (match_id TEXT, side TEXT, formacion TEXT, confirmada BOOLEAN, completa BOOLEAN,
                fuente TEXT, pit TEXT);
              CREATE TABLE futbol.entrenador (match_id TEXT, side TEXT, entrenador_id BIGINT, nombre TEXT, fuente TEXT);
              CREATE TABLE futbol.contexto (match_id TEXT, fuente TEXT, arbitro_partidos INT, arbitro_amarillas INT,
                arbitro_rojas INT, arbitro_doble_amarilla INT, arbitro_pais TEXT, estadio_ciudad TEXT, estadio_capacidad INT,
                estadio_lat DOUBLE PRECISION, estadio_lon DOUBLE PRECISION, ronda INT, descuento_1t SMALLINT,
                descuento_2t SMALLINT, goles_local_1t SMALLINT, goles_visita_1t SMALLINT);
              CREATE TABLE futbol.tiro (match_id TEXT, tiro_id BIGINT, side TEXT, fuente TEXT, jugador_id BIGINT, jugador TEXT,
                minuto SMALLINT, segundo INT, resultado TEXT, situacion TEXT, parte_cuerpo TEXT, x REAL, y REAL, boca TEXT,
                boca_x REAL, boca_y REAL, boca_z REAL, xg REAL, xgot REAL);
              CREATE TABLE futbol.incidencia (match_id TEXT, orden SMALLINT, fuente TEXT, tipo TEXT, clase TEXT, side TEXT,
                minuto SMALLINT, anadido SMALLINT, jugador_id BIGINT, jugador TEXT, jugador2_id BIGINT, jugador2 TEXT,
                razon TEXT, marcador_local SMALLINT, marcador_visita SMALLINT);
              CREATE TABLE futbol.estadistica_equipo (match_id TEXT, side TEXT, fuente TEXT, posesion REAL, xgot REAL,
                grandes_ocasiones SMALLINT, grandes_ocasiones_falladas SMALLINT, tiros_fuera SMALLINT, tiros_bloqueados SMALLINT,
                tiros_dentro_area SMALLINT, tiros_fuera_area SMALLINT, paradas SMALLINT, goles_evitados REAL, faltas SMALLINT,
                tiros_libres SMALLINT, fuera_juego SMALLINT, pases SMALLINT, pases_acertados SMALLINT,
                balones_largos_acertados SMALLINT, centros_acertados SMALLINT, entradas SMALLINT, intercepciones SMALLINT,
                recuperaciones SMALLINT, despejes SMALLINT, perdidas SMALLINT, toques_area_rival SMALLINT,
                entradas_ultimo_tercio SMALLINT, saques_banda SMALLINT, saques_puerta SMALLINT, km REAL, sprints SMALLINT);
              CREATE VIEW futbol.v_jugador_partido AS SELECT match_id FROM futbol.jugador_partido;
"""


def test_pg_migracion_095_absorbe_las_tablas_por_tipo_y_cuadra_las_filas():
    """Estado de producción antes de 095: tablas por tipo con datos y entidad_fuente; después, solo futbol.dato."""
    with pg_connection() as connection:
        try:
            with_schema(connection)
            connection.execute(OLD_DDL)
            connection.execute("""
              INSERT INTO futbol.entidad_fuente VALUES ('m1','jugador_partido','fotmob',1,'2026-10-30T10:00:00+00:00');
              INSERT INTO futbol.jugador_partido (match_id, side, jugador_id, fuente, nombre, titular, pit, minutos, goles)
                  VALUES ('m1','home',10,'fotmob','Uno',true,'posterior',90,1);
              INSERT INTO futbol.baja (match_id, side, jugador_id, fuente, nombre, tipo, pit) VALUES ('m1','home',11,'fotmob','Dos','missing','reconstruido');
              INSERT INTO futbol.alineacion VALUES ('m1','home','4-4-2',true,true,'fotmob','posterior');
              INSERT INTO futbol.entrenador VALUES ('m1','home',9,'DT','fotmob');
              INSERT INTO futbol.contexto (match_id, fuente, arbitro_partidos, estadio_ciudad) VALUES ('m1','sofascore',388,'Quito');
              INSERT INTO futbol.tiro (match_id, tiro_id, side, fuente, jugador_id, jugador, xg) VALUES ('m1',5,'home','sofascore',NULL,'Sin id',0.1);
              INSERT INTO futbol.incidencia (match_id, orden, fuente, tipo, side, jugador_id) VALUES ('m1',0,'sofascore','period',NULL,NULL);
              INSERT INTO futbol.estadistica_equipo (match_id, side, fuente, posesion, grandes_ocasiones, tiros_bloqueados)
                  VALUES ('m1','home','sofascore',59,2,4);
              INSERT INTO matches (match_id) VALUES ('m1');
            """)
            root = Path(__file__).resolve().parents[1]
            sql = (root / 'db' / '095_futbol_dato_absorbe_tablas.sql').read_text(encoding='utf-8')
            connection.execute(sql.replace('BEGIN;', '').replace('COMMIT;', ''))
            assert por_tipo(connection) == {'jugador': 1, 'baja': 1, 'alineacion': 1, 'entrenador': 1, 'contexto': 1,
                                            'tiro': 1, 'incidencia': 1, 'equipo': 1}
            fila = connection.execute("SELECT goles, minutos, recibido_en FROM futbol.dato WHERE tipo='jugador'").fetchone()
            assert fila[0] == 1 and fila[1] == 90.0 and fila[2].astimezone(__import__('datetime').timezone.utc).isoformat().startswith('2026-10-30T10:00')
            equipo = connection.execute("SELECT grandes_ocasiones_creadas, tiros_bloq FROM futbol.dato WHERE tipo='equipo'").fetchone()
            assert equipo == (2, 4)
            assert connection.execute("SELECT jugador_id, nombre FROM futbol.dato WHERE tipo='tiro'").fetchone() == (0, 'Sin id')
            assert connection.execute("SELECT to_regclass('futbol.jugador_partido')").fetchone()[0] is None  # retirada
            # una segunda aplicación no hace nada
            connection.execute(sql.replace('BEGIN;', '').replace('COMMIT;', ''))
            assert connection.execute("SELECT count(*) FROM futbol.dato WHERE tipo<>'clima'").fetchone()[0] == 8
        finally:
            connection.rollback()


def test_pg_la_migracion_095_se_deshace_si_las_filas_no_cuadran():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            connection.execute(OLD_DDL)
            # dos filas iguales en la tabla de origen: la clave de futbol.dato admite una, no cuadra y debe abortar
            connection.execute("INSERT INTO futbol.jugador_partido (match_id, side, jugador_id, fuente, pit) VALUES ('m1','home',1,'fotmob','posterior'), ('m1','home',1,'fotmob','posterior')")
            connection.execute("INSERT INTO matches (match_id) VALUES ('m1')")
            root = Path(__file__).resolve().parents[1]
            sql = (root / 'db' / '095_futbol_dato_absorbe_tablas.sql').read_text(encoding='utf-8')
            import psycopg
            with pytest.raises(psycopg.errors.RaiseException, match='no cuadran'):
                connection.execute(sql.replace('BEGIN;', '').replace('COMMIT;', ''))
        finally:
            connection.rollback()


# ── identidad: reglas de evidencia puras ─────────────────────────────────────────────────────────

def test_identidad_empareja_por_nombre_en_el_partido_y_descarta_lo_ambiguo():
    from qf.ingest import futbol_identidad as fi
    fotmob = [(1, 'Ángel Gómez'), (2, 'Mario Rossi'), (3, 'Mario Rossi')]
    sofa = [(10, 'Angel Gomez', 'A. Gómez'), (11, 'Mario Rossi', 'M. Rossi'), (12, 'Luis Verdi', 'L. Verdi')]
    assert fi.match_players(fotmob, sofa) == [(1, 10)]  # Rossi aparece dos veces en FotMob: ambiguo
    assert fi.match_players([(5, 'Vinicius Junior')], [(20, 'Vini Jr', 'Vinicius')]) == [(5, 20)]  # corto dentro del largo


def test_identidad_exige_repeticion_y_no_enlaza_conflictos():
    from collections import Counter
    from qf.ingest import futbol_identidad as fi
    pairs = Counter({(1, 10): 3, (2, 20): 1, (3, 30): 2, (3, 31): 1, (4, 40): 1})
    appearances = {1: 30, 2: 1, 3: 10, 4: 12}
    links = fi.decide_links(pairs, appearances)
    assert links == {1: (10, 3), 2: (20, 1)}  # 2: una sola aparición posible; 3 en conflicto; 4 sin más evidencia


def test_sin_partidos_nuevos_desde_la_fecha_no_es_un_error(tmp_path):
    """Un `--since` sin partidos asentados devolvía unsupported_or_mixed_providers en vez de terminar limpio."""
    import gzip
    import json
    archive = tmp_path / 'v3'
    (archive / 'tournaments' / '23' / 'seasons' / '1' / 'schedule').mkdir(parents=True)
    event = {'id': 1, 'startTimestamp': 1_700_000_000, 'status': {'type': 'finished'}}
    (archive / 'tournaments' / '23' / 'seasons' / '1' / 'schedule' / 'round_1.json.gz').write_bytes(
        gzip.compress(json.dumps({'events': [event]}).encode()))
    result = fs.run(None, archive, 'it.serie_a', tmp_path / 'trabajo', '2026-10-31', apply=False)
    assert result['sin_partidos_nuevos'] is True and result['normalizados'] == 0


# ── el interruptor de lectura del motor ──────────────────────────────────────────────────────────

def test_lectura_del_motor_por_defecto_sigue_en_las_tablas_de_origen(monkeypatch):
    from qf.model import jugadores
    consultas = []
    monkeypatch.delenv('FUTBOL_LECTURA', raising=False)
    monkeypatch.setattr('qf.db.query', lambda sql, params=(): consultas.append(sql) or [])
    jugadores.cargar_filas()
    assert 'fotmob_jugador_partido' in consultas[0] and 'futbol.' not in consultas[0]
    monkeypatch.setenv('FUTBOL_LECTURA', 'canonica')
    jugadores.cargar_filas()
    assert 'futbol.dato' in consultas[1] and "j.tipo = 'jugador'" in consultas[1] and 'j.nota AS rating' in consultas[1]


def test_once_previo_se_traduce_al_id_canonico_solo_con_la_lectura_canonica(monkeypatch):
    from qf.model import ajuste_xi
    consultas = []
    monkeypatch.setattr('qf.db.query', lambda sql, params=(): consultas.append(sql) or [])
    monkeypatch.delenv('FUTBOL_LECTURA', raising=False)
    ajuste_xi.once_confirmado('m')
    assert 'jugador_fuente_id' not in consultas[0] and 'jp.jugador_id AS jugador_id' in consultas[0]
    monkeypatch.setenv('FUTBOL_LECTURA', 'canonica')
    ajuste_xi.once_confirmado('m')
    assert 'futbol.jugador_fuente_id' in consultas[1] and "futbol.id_sintetico('fotmob', jp.jugador_id)" in consultas[1]


def test_pg_la_lectura_canonica_da_las_mismas_apariciones_con_el_id_unificado(monkeypatch):
    """Origen y canónica entregan el mismo contenido; solo cambia el id del jugador."""
    from qf.model import jugadores
    with pg_connection() as connection:
        try:
            with_schema(connection)
            fs.apply_batch(connection, [item_for()])
            add_fotmob(connection)
            connection.execute("SELECT futbol.vincular_jugador('fotmob',777,3,'nombre_en_partido',5)")
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()

            def consulta(sql, params=()):
                from psycopg.rows import dict_row
                with connection.cursor(row_factory=dict_row) as cursor:
                    return cursor.execute(sql, params).fetchall()

            monkeypatch.setattr('qf.db.query', consulta)
            monkeypatch.delenv('FUTBOL_LECTURA', raising=False)
            origen = jugadores.cargar_filas('2000-01-01').sort_values('valor_mercado').reset_index(drop=True)
            monkeypatch.setenv('FUTBOL_LECTURA', 'canonica')
            canonica = jugadores.cargar_filas('2000-01-01').sort_values('valor_mercado').reset_index(drop=True)
            cols = ['match_id', 'side', 'titular', 'posicion_id', 'valor_mercado', 'rating']
            assert origen[cols].equals(canonica[cols]) and len(origen) == 2
            assert sorted(origen['jugador_id']) == [777, 778] and sorted(canonica['jugador_id']) == [-778, 3]
        finally:
            connection.rollback()


def test_pg_los_ids_de_sofascore_sin_ficha_se_registran_en_la_identidad():
    from qf.ingest import futbol_identidad as fi
    with pg_connection() as connection:
        try:
            with_schema(connection)
            connection.execute("INSERT INTO futbol.dato (match_id, tipo, side, jugador_id, evento, fuente, recibido_en, nombre) "
                               "VALUES (%s,'tiro','home',4242,1,'sofascore',now(),'Tirador sin alineacion')", (MATCH,))
            assert fi.register_orphans(connection) == 1
            assert connection.execute("SELECT nombre FROM futbol.jugador WHERE jugador_id=4242").fetchone() == ('Tirador sin alineacion',)
            assert connection.execute("SELECT evidencia FROM futbol.jugador_fuente_id WHERE fuente='sofascore' AND id_en_fuente=4242").fetchone() == ('id_canonico',)
            assert fi.register_orphans(connection) == 0  # idempotente
        finally:
            connection.rollback()


def test_pg_sofascore_completa_lo_que_le_falta_a_la_fila_de_fotmob_sin_pisarla():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            fs.apply_batch(connection, [item_for()])
            add_fotmob(connection)
            connection.execute("SELECT futbol.vincular_jugador('fotmob',777,3,'nombre_en_partido',5)")
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()   # FotMob toma el partido a SofaScore
            cols = "fuente, fuente_extra, nota, minutos, goles, pases, valor_mercado, xg, pases_clave, penaltis_ganados, conducciones, nota_alternativa"
            fila = connection.execute("SELECT %s FROM futbol.dato WHERE tipo='jugador' AND jugador_id=3" % cols).fetchone()
            # al tomar el partido, FotMob conserva lo que SofaScore ya había dado y FotMob no trae
            assert fila[:7] == ('fotmob', 'sofascore', 7.1, 90.0, 1, 40, 5000000)
            assert fila[7:] == (pytest.approx(0.31, abs=1e-6), 2, 1, 14, pytest.approx(6.4, abs=1e-6))
            totals = fs.apply_batch(connection, [item_for(sha='d' * 64)])
            assert totals['tipo_de_mejor_fuente'] == 4
            assert totals.get('columnas_completadas', 0) == 0   # nada que completar: ya estaba
            # el jugador que no tiene pareja en SofaScore no recibe nada
            assert connection.execute("SELECT fuente_extra FROM futbol.dato WHERE tipo='jugador' AND jugador_id=-778").fetchone() == (None,)
            assert connection.execute("SELECT fuente, fuente_extra FROM futbol.dato WHERE tipo='baja'").fetchone()[0] == 'fotmob'
        finally:
            connection.rollback()


def test_pg_cargar_fotmob_de_nuevo_conserva_lo_completado_y_la_nota_es_siempre_la_de_fotmob():
    """La causa de fondo: antes cada carga de FotMob borraba lo que SofaScore había completado y obligaba a recargar."""
    with pg_connection() as connection:
        try:
            with_schema(connection)
            add_fotmob(connection)
            connection.execute("INSERT INTO futbol.jugador VALUES (3, 'P3') ON CONFLICT DO NOTHING")
            connection.execute("SELECT futbol.vincular_jugador('fotmob',777,3,'nombre_en_partido',5)")
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()         # FotMob primero
            fs.apply_batch(connection, [item_for()])                                       # SofaScore completa
            antes = connection.execute("SELECT xg, pases_clave, fuente_extra FROM futbol.dato WHERE tipo='jugador' AND jugador_id=3").fetchone()
            assert antes == (pytest.approx(0.31, abs=1e-6), 2, 'sofascore')
            for _ in range(2):                                                             # FotMob reescribe sus filas
                connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()
            assert connection.execute("SELECT xg, pases_clave, fuente_extra FROM futbol.dato WHERE tipo='jugador' AND jugador_id=3").fetchone() == antes
            # `nota` es entrada del motor: si FotMob la pierde, queda vacía y NO se rellena con la de otra fuente
            connection.execute("UPDATE fotmob_jugador_partido SET rating = NULL WHERE jugador_id = 777")
            connection.execute("UPDATE futbol.dato SET nota = 6.5 WHERE tipo='jugador' AND jugador_id=3")  # como la dejaría otra fuente
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()
            nota = connection.execute("SELECT nota, fuente FROM futbol.dato WHERE tipo='jugador' AND jugador_id=3").fetchone()
            assert nota[1] == 'fotmob' and nota[0] is None
            # un jugador que FotMob deja de informar desaparece (una sola fuente por partido)
            connection.execute("DELETE FROM fotmob_jugador_partido WHERE jugador_id = 778")
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()
            assert connection.execute("SELECT count(*) FROM futbol.dato WHERE tipo='jugador' AND jugador_id=-778").fetchone()[0] == 0
        finally:
            connection.rollback()


def test_pg_la_migracion_096_unifica_perdidas_de_equipo_y_acepta_los_tipos_nuevos():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            connection.execute("INSERT INTO futbol.dato (match_id, tipo, side, fuente, recibido_en, perdidas) "
                               "VALUES (%s,'equipo','home','sofascore',now(),9)", (MATCH,))
            root = Path(__file__).resolve().parents[1]
            sql = (root / 'db' / '096_futbol_dato_ampliado.sql').read_text(encoding='utf-8')
            connection.execute(sql.replace('BEGIN;', '').replace('COMMIT;', ''))  # repetirla no rompe nada (idempotente)
            assert connection.execute("SELECT perdidas, perdidas_balon FROM futbol.dato WHERE tipo='equipo'").fetchone() == (None, 9)
            connection.execute("INSERT INTO futbol.dato (match_id, tipo, fuente, recibido_en, momentum) VALUES (%s,'momentum','sofascore',now(),1)", (MATCH,))
            import psycopg
            with pytest.raises(psycopg.errors.CheckViolation):
                connection.execute("INSERT INTO futbol.dato (match_id, tipo, fuente, recibido_en) VALUES (%s,'inventado','sofascore',now())", (MATCH,))
        finally:
            connection.rollback()


def test_pg_cargar_fotmob_no_borra_las_bajas_de_otra_fuente_si_fotmob_no_informa_ninguna():
    with pg_connection() as connection:
        try:
            with_schema(connection)
            fs.apply_batch(connection, [item_for()])           # SofaScore trae 1 baja
            add_fotmob(connection)
            connection.execute("DELETE FROM fotmob_baja")      # FotMob no informa ninguna en este partido
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()
            assert connection.execute("SELECT fuente, count(*) FROM futbol.dato WHERE tipo='baja' GROUP BY 1").fetchall() == [('sofascore', 1)]
            connection.execute("INSERT INTO fotmob_baja VALUES (%s,'home',779,'Lesionado FM',30,5,NULL,'missing',1,'Lesion',NULL)", (MATCH,))
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()   # ahora FotMob sí informa: la sustituye
            assert connection.execute("SELECT fuente, count(*) FROM futbol.dato WHERE tipo='baja' GROUP BY 1").fetchall() == [('fotmob', 1)]
        finally:
            connection.rollback()


def test_pg_retirar_las_estadisticas_historicas_no_cambia_lo_ya_cargado_en_la_tabla_unica():
    """R1 del retiro de tablas: `historical_football_player_stats` se borra de los partidos ya cargados; volver a
    cargar FotMob sin esas filas no puede dejar vacío lo que ya estaba."""
    with pg_connection() as connection:
        try:
            with_schema(connection)
            add_fotmob(connection)
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()
            columnas = "minutos, goles, pases, pases_acertados, nota, titular"
            antes = connection.execute(f"SELECT {columnas} FROM futbol.dato WHERE tipo='jugador' AND jugador_id=-777").fetchone()
            assert antes[0] == 90 and antes[1] == 1
            connection.execute("DELETE FROM historical_football_player_stats")
            connection.execute("SELECT * FROM futbol.cargar_fotmob()").fetchall()
            despues = connection.execute(f"SELECT {columnas} FROM futbol.dato WHERE tipo='jugador' AND jugador_id=-777").fetchone()
            assert despues == antes
            assert connection.execute("SELECT count(*) FROM futbol.dato WHERE tipo='jugador'").fetchone()[0] == 2
        finally:
            connection.rollback()
