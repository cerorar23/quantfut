"""Prevent live, suspended, wrong-house, and incomplete odds entering recovery."""
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'recover_oddspapi', Path(__file__).parents[1] / 'scripts/recover_oddspapi_closes.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def history():
    outcomes = {}
    for oid, price in zip(('101', '102', '103'), (2.2, 3.5, 3.4)):
        outcomes[oid] = {'players': {'0': [
            {'createdAt': '2026-09-13T15:29:00Z', 'price': price, 'active': None},
            {'createdAt': '2026-09-13T15:29:30Z', 'price': 1.1, 'active': False},
            {'createdAt': '2026-09-13T15:30:00Z', 'price': 1.2, 'active': True},
            {'createdAt': '2026-09-13T15:40:00Z', 'price': 20, 'active': True},
        ]}}
    return {'bookmakers': {'pinnacle': {'markets': {'101': {'outcomes': outcomes}}}}}


EVENT = {'startTime': '2026-09-13T15:30:00Z',
         'trueStartTime': '2026-09-13T15:32:29Z'}


def test_reconstruct_before_kickoff_excludes_suspended_live_and_equal_timestamp():
    result = module.extract(EVENT, history())
    assert [result[k] for k in ('home', 'draw', 'away')] == [2.2, 3.5, 3.4]
    assert result['max_age_seconds'] == 60
    assert result['has_history_after_cutoff']
    assert result['close_verified'] is False


def test_actual_start_earlier_than_scheduled_is_respected():
    event = {**EVENT, 'trueStartTime': '2026-09-13T15:28:00Z'}
    assert module.extract(event, history()) is None


def test_does_not_substitute_other_book_market_or_incomplete_triple():
    data = history()
    data['bookmakers']['bet365'] = data['bookmakers'].pop('pinnacle')
    assert module.extract(EVENT, data) is None
    data = history()
    data['bookmakers']['pinnacle']['markets']['131'] = data['bookmakers']['pinnacle']['markets'].pop('101')
    assert module.extract(EVENT, data) is None
    data = history()
    del data['bookmakers']['pinnacle']['markets']['101']['outcomes']['103']
    assert module.extract(EVENT, data) is None


def test_unordered_history_and_offset_timestamps_compare_as_utc():
    data = history()
    for outcome in data['bookmakers']['pinnacle']['markets']['101']['outcomes'].values():
        snapshots = outcome['players']['0']
        latest = deepcopy(snapshots[0])
        latest.update(createdAt='2026-09-13T17:29:45+02:00', price=3.0, active=True)
        snapshots.insert(0, latest)
    result = module.extract(EVENT, data)
    assert result['home'] == 3
    assert result['max_age_seconds'] == 15


def test_resume_rejects_corrupt_original_without_network(tmp_path, monkeypatch):
    monkeypatch.setenv('ODDSPAPI_API_KEY', 'test-only-placeholder')
    client = module.Client(tmp_path)
    (client.folder / 'sample.json.gz').write_bytes(gzip.compress(b'{}'))
    (client.folder / 'sample.receipt.json').write_text(
        json.dumps({'status': 200, 'sha256': 'incorrect'}), encoding='utf-8')
    with pytest.raises(ValueError, match='archive_hash_mismatch'):
        client.get('historical-odds', {'fixtureId': 'sample'}, 'sample')


def test_matching_refuses_duplicate_events_even_with_exact_names(tmp_path):
    root = tmp_path / 'originals'
    root.mkdir()
    event = {'fixtureId': 'one', 'startTime': EVENT['startTime'],
             'participant1Name': 'Home', 'participant2Name': 'Away'}
    events = [event, {**event, 'fixtureId': 'two'}]
    (root / 'fixtures_17.json.gz').write_bytes(gzip.compress(json.dumps(events).encode()))
    rows = [{'match_id': 'm', 'league_id': 'gb.premier_league',
             'kickoff_utc': EVENT['startTime'], 'local': 'Home', 'visita': 'Away'}]
    snapshot = {'teams': [{'team_id': 1, 'canonical_name': 'Home'},
                          {'team_id': 2, 'canonical_name': 'Away'}],
                'aliases': [], 'matches': [{'match_id': 'm', 'home_team_id': 1,
                                            'away_team_id': 2}]}
    matches, unresolved = module.associate(tmp_path, rows, snapshot)
    assert matches == []
    assert unresolved[0]['reason'] == 'ambiguous'
