import copy
import gzip
import hashlib
import json
import os
import random
from pathlib import Path

import pytest

from qf.ingest.sofascore_history import normalize_bundle
from qf.ingest.sofascore_local import (PROVIDER, compose_original, finished_event_ids, league_tournaments,
                                       match_dir, normalize_local_bundle, read_match)

LOCAL_ARCHIVE = Path(os.environ.get('QF_SOFASCORE_LOCAL', r'C:\Users\huye\Documents\SOFASCORE\data\v3'))
GOLDEN_ID = 13981422  # Genoa 0-0 Lecce, Serie A 25/26


def blocks():
    def team(tid, name):
        return {'id': tid, 'name': name, 'sport': {'id': 1}, 'gender': 'M', 'national': False}

    def item(key, h, a):
        return {'key': key, 'homeValue': h, 'awayValue': a}

    def players(tid, start):
        return [{'teamId': tid, 'player': {'id': start + i, 'name': 'P%d' % (start + i)},
                 'substitute': False, 'statistics': {'minutesPlayed': 90, 'rating': 6.5}}
                for i in range(11)]

    return {
        'event': {'id': 555, 'startTimestamp': 1755970200, 'status': {'type': 'finished', 'code': 100},
                  'homeTeam': team(10, 'Genoa'), 'awayTeam': team(20, 'Lecce'),
                  'homeScore': {'normaltime': 0, 'current': 0}, 'awayScore': {'normaltime': 1, 'current': 1},
                  'tournament': {'uniqueTournament': {'id': 23}, 'category': {'alpha2': 'IT'}},
                  'season': {'year': '25/26'}},
        'statistics': {'statistics': [{'period': 'ALL', 'groups': [{'statisticsItems': [
            item('expectedGoals', 0.5, 0.37), item('totalShotsOnGoal', 5, 7),
            item('shotsOnGoal', 2, 3), item('cornerKicks', 3, 7)]}]}]},
        'lineups': {'confirmed': True,
                    'home': {'formation': '4-2-3-1', 'players': players(10, 1),
                             'missingPlayers': [{'player': {'id': 90, 'name': 'Lesionado'}, 'type': 'missing',
                                                 'reason': 1, 'description': 'Thigh Injury'}]},
                    'away': {'formation': '4-3-3', 'players': players(20, 30), 'missingPlayers': []}},
        'managers': {'homeManager': {'id': 1, 'name': 'A'}, 'awayManager': {'id': 2, 'name': 'B'}},
    }


def write_match(folder, data, empty=(), fetched=None):
    """Escribe un partido con el formato del archivo: bloques `.json.gz` y manifest con hashes."""
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {'id': data['event']['id'], 'created_at': '2026-10-30T14:44:59+00:00',
                'observation': {'observed_at_utc': '2026-10-30T14:44:37+00:00'}, 'slices': {}}
    for i, (name, content) in enumerate(data.items()):
        stamp = (fetched or {}).get(name, '2026-10-30T14:44:%02d+00:00' % (37 + i))
        raw = json.dumps(content).encode()
        (folder / (name + '.json.gz')).write_bytes(gzip.compress(raw))
        manifest['slices'][name] = {'state': 'ok', 'fetched_at': stamp, 'bytes': len(raw),
                                    'sha256': hashlib.sha256(raw).hexdigest()}
    for name in empty:
        manifest['slices'][name] = {'state': 'empty', 'empty': {'reason': '404'}}
    (folder / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    return folder


def load(folder, league='it.serie_a'):
    b, s, m = read_match(folder)
    return normalize_local_bundle(league, b, s, m)


def test_partido_valido_con_proveedor_y_recepcion_propios(tmp_path):
    folder = write_match(tmp_path / 'p', blocks(),
                         fetched={'event': '2026-10-30T14:44:37+00:00', 'lineups': '2026-10-30T14:44:54+00:00'})
    row, raw, meta = load(folder)
    assert row['provider'] == PROVIDER == 'sofascore_local' and row['source_match_id'] == '555'
    assert row['league_id'] == 'it.serie_a' and row['home_goals'] == 0 and row['away_goals'] == 1
    assert (row['home_xg'], row['away_xg']) == (0.5, 0.37)
    assert row['counts'] == {'home_shots': 5, 'away_shots': 7, 'home_shots_target': 2,
                             'away_shots_target': 3, 'home_corners': 3, 'away_corners': 7}
    assert [l['complete'] for l in row['lineups']] == [True, True]
    assert len(row['players']) == 22 and row['absences'][0]['source_player_id'] == 90
    assert row['raw_sha256'] == meta['sha256'] == hashlib.sha256(raw).hexdigest()
    assert meta['captured_at'] == '2026-10-30T14:44:54+00:00'  # el mayor fetched_at
    assert row['captured_at'].startswith('2026-10-30T14:44:54')


def test_el_original_no_depende_del_orden_de_los_bloques():
    a = blocks()
    b = dict(reversed(list(copy.deepcopy(a).items())))
    assert compose_original(a)[1] == compose_original(b)[1]
    a['event']['id'] = 556
    assert compose_original(a)[1] != compose_original(b)[1]


def test_un_bloque_alterado_invalida_el_partido(tmp_path):
    folder = write_match(tmp_path / 'p', blocks())
    altered = blocks()['lineups']
    altered['home']['formation'] = '3-5-2'
    (folder / 'lineups.json.gz').write_bytes(gzip.compress(json.dumps(altered).encode()))
    with pytest.raises(ValueError, match='slice_hash_mismatch:lineups'):
        read_match(folder)


def test_bloque_ausente_en_disco_se_rechaza(tmp_path):
    folder = write_match(tmp_path / 'p', blocks())
    (folder / 'statistics.json.gz').unlink()
    with pytest.raises(ValueError, match='slice_missing:statistics'):
        read_match(folder)


def test_bloques_vacios_opcionales_se_toleran_y_los_requeridos_no(tmp_path):
    folder = write_match(tmp_path / 'p', blocks(), empty=('pregame_form', 'momentum'))
    row, _, meta = load(folder)
    assert meta['slices']['pregame_form']['state'] == 'empty' and row['provider'] == PROVIDER
    sin_alineacion = blocks()
    del sin_alineacion['lineups']
    folder = write_match(tmp_path / 'q', sin_alineacion, empty=('lineups',))
    with pytest.raises(ValueError, match='required_slice_missing:lineups'):
        load(folder)


def test_manifest_de_otro_partido(tmp_path):
    folder = write_match(tmp_path / 'p', blocks())
    manifest = json.loads((folder / 'manifest.json').read_text())
    manifest['id'] = 999
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='manifest_event_mismatch'):
        load(folder)


def test_reglas_comunes_torneo_y_pais(tmp_path):
    data = blocks()
    data['event']['tournament']['uniqueTournament']['id'] = 17
    with pytest.raises(ValueError, match='wrong_tournament'):
        load(write_match(tmp_path / 'a', data))
    data = blocks()
    data['event']['tournament']['category']['alpha2'] = 'ES'
    with pytest.raises(ValueError, match='wrong_competition_country'):
        load(write_match(tmp_path / 'b', data))
    data = blocks()
    data['event']['status'] = {'type': 'inprogress', 'code': 7}
    with pytest.raises(ValueError, match='unfinished_event'):
        load(write_match(tmp_path / 'c', data))


def test_equipo_actual_del_jugador_no_lo_expulsa_del_once(tmp_path):
    """La descarga es posterior al partido: `teamId` es el club actual, no el de ese día."""
    data = blocks()
    data['lineups']['home']['players'][3]['teamId'] = 777
    row, _, _ = load(write_match(tmp_path / 'p', data))
    assert row['statistics']['player_identity_issues'] == []
    assert row['statistics']['player_team_id_differs'] == [
        {'side': 'home', 'source_player_id': 4, 'reported_team_id': 777}]
    assert len(row['players']) == 22
    assert [l['complete'] for l in row['lineups']] == [True, True]


def test_el_mismo_jugador_en_los_dos_lados_sigue_siendo_conflicto(tmp_path):
    data = blocks()
    data['lineups']['away']['players'][0]['player']['id'] = data['lineups']['home']['players'][0]['player']['id']
    with pytest.raises(ValueError, match='player_team_or_identity_conflict'):
        load(write_match(tmp_path / 'p', data))


def test_apify_conserva_la_regla_estricta_del_equipo():
    data = {k: v for k, v in blocks().items() if k in ('event', 'statistics', 'lineups')}
    data['event']['tournament'] = {'uniqueTournament': {'id': 18}, 'category': {'alpha2': 'EN'}}
    data['lineups']['home']['players'][3]['teamId'] = 777
    raw = json.dumps(data).encode()
    row = normalize_bundle('gb.championship', raw, {'sha256': hashlib.sha256(raw).hexdigest(),
                                                    'captured_at': '2026-10-30T14:44:54Z'})
    assert row['statistics']['player_identity_issues'][0]['source_player_id'] == 4
    assert 'player_team_id_differs' not in row['statistics']
    assert [l['complete'] for l in row['lineups']] == [False, True]


def test_recepcion_anterior_al_partido_se_rechaza(tmp_path):
    data = blocks()
    folder = write_match(tmp_path / 'p', data,
                         fetched={n: '2025-08-01T00:00:00+00:00' for n in data})
    with pytest.raises(ValueError, match='invalid_capture_time'):
        load(folder)


def test_registro_provisional_se_rechaza_hasta_que_pase_la_ventana(tmp_path):
    """El scraper relee un partido terminado durante 72 h; antes de eso sus cifras pueden cambiar."""
    folder = write_match(tmp_path / 'p', blocks())
    manifest = json.loads((folder / 'manifest.json').read_text())
    manifest['observation']['observed_at_utc'] = '2025-08-23T20:30:00+00:00'  # 3 h después del inicio
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='provisional_record'):
        load(folder)
    manifest['observation']['observed_at_utc'] = '2025-08-26T18:00:00+00:00'  # 72 h y 30 min después
    (folder / 'manifest.json').write_text(json.dumps(manifest))
    assert load(folder)[0]['source_match_id'] == '555'


def test_calendario_con_fecha_minima_y_torneos_de_mexico(tmp_path):
    def schedule(tournament, season, events):
        folder = tmp_path / 'tournaments' / str(tournament) / 'seasons' / str(season) / 'schedule'
        folder.mkdir(parents=True)
        (folder / 'round_1.json.gz').write_bytes(gzip.compress(json.dumps({'events': events}).encode()))

    def event(i, start, kind='finished'):
        return {'id': i, 'startTimestamp': start, 'status': {'type': kind}}

    schedule(11620, 1, [event(1, 1_700_000_000)])
    schedule(11621, 2, [event(2, 1_793_450_000), event(3, 1_793_450_100, 'notstarted')])
    assert league_tournaments('mx.liga_mx') == [11620, 11621] and league_tournaments('it.serie_a') == [23]
    assert finished_event_ids(tmp_path, league_tournaments('mx.liga_mx')) == [1, 2]
    assert finished_event_ids(tmp_path, league_tournaments('mx.liga_mx'), since='2026-10-31') == [2]
    assert finished_event_ids(tmp_path, 11620) == [1]


def test_el_normalizador_de_apify_no_cambia():
    """normalize_bundle sigue dando el mismo resultado: solo se extrajo `normalize_payload`."""
    data = {k: v for k, v in blocks().items() if k in ('event', 'statistics', 'lineups')}
    data['event']['tournament'] = {'uniqueTournament': {'id': 18}, 'category': {'alpha2': 'EN'}}
    raw = json.dumps(data).encode()
    meta = {'sha256': hashlib.sha256(raw).hexdigest(), 'captured_at': '2026-10-30T14:44:54Z'}
    row = normalize_bundle('gb.championship', raw, meta)
    assert row['provider'] == 'sofascore' and row['raw_sha256'] == meta['sha256']
    assert row['counts']['home_shots_target'] is None  # `shotsOnTarget` no existe en este origen


@pytest.mark.skipif(not (match_dir(LOCAL_ARCHIVE, GOLDEN_ID) / 'manifest.json').exists(),
                    reason='archivo SofaScore local no disponible')
def test_partido_de_oro_genoa_lecce():
    row, raw, meta = load(match_dir(LOCAL_ARCHIVE, GOLDEN_ID))
    assert row['source_match_id'] == str(GOLDEN_ID) and row['provider'] == PROVIDER
    assert (row['home_name'], row['away_name']) == ('Genoa', 'Lecce')
    assert (row['home_goals'], row['away_goals']) == (0, 0)
    assert (row['home_xg'], row['away_xg']) == (0.5, 0.37)
    # coinciden con producción (conciliación F0 del 31-oct)
    assert row['counts'] == {'home_shots': 5, 'away_shots': 7, 'home_shots_target': 2,
                             'away_shots_target': 0, 'home_corners': 3, 'away_corners': 7}
    assert [l['complete'] for l in row['lineups']] == [True, True]
    assert [l['formation'] for l in row['lineups']] == ['4-2-3-1', '4-3-3']
    assert row['statistics']['player_identity_issues'] == []
    # El archivo trae el club actual de cada jugador: muchos suplentes ya no están en su equipo.
    assert len(row['statistics']['player_team_id_differs']) > 0
    assert len(row['absences']) == 4
    assert meta['slices']['pregame_form']['state'] == 'empty'
    assert len(raw) > 50_000 and row['raw_sha256'] == meta['sha256']
