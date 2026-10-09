import json

import httpx
import pytest

from nba.cli import main
from nba.config import Settings
from nba.odds_capture import BoundedOddsCapture
from nba.odds_sources import selected_request, source_plan

EVENT = 'a' * 32
BOOKS = 'onexbet,betsson,codere_it,betano_uk'


def test_selected_versions_reach_provider_and_immutable_receipt(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[], headers={'x-requests-last': '0' if len(calls) == 1 else '1',
            'x-requests-used': str(len(calls)-1), 'x-requests-remaining': str(10000-len(calls)+1)})
    capture = BoundedOddsCapture(tmp_path/'capture', 'test_only_credential', 3,
        client=httpx.Client(transport=httpx.MockTransport(handler)))
    capture.request('quota.json', 'sports', {}, 0)
    capture.request_selected('markets.json', EVENT)
    assert len(calls) == 2
    assert calls[1].url.params['bookmakers'] == BOOKS
    assert 'regions' not in calls[1].url.params
    receipt = json.loads((capture.root/'manifest.json').read_bytes())
    assert receipt['files'][1]['parameters_without_credentials']['bookmakers'] == BOOKS
    assert receipt['charged_credits'] == 1 and not receipt['actionable']
    assert 'test_only_credential' not in (capture.root/'manifest.json').read_text()


def test_selection_cannot_bypass_existing_budget(tmp_path):
    capture = BoundedOddsCapture(tmp_path/'capture', 'test_only_credential', 3,
        client=httpx.Client(transport=httpx.MockTransport(lambda r: pytest.fail('unbudgeted network call'))))
    assert capture.request_selected('markets.json', EVENT) is None
    assert capture.meta['stopped'] and not (capture.root/'markets.json').exists()


def test_cross_region_filter_and_historical_reservation_do_not_broaden_scope():
    spec = selected_request(EVENT, kind='odds', date='2025-10-21T16:00:00-06:00')
    assert spec['path'] == f'historical/sports/basketball_nba/events/{EVENT}/odds'
    assert spec['max_cost'] == 30
    assert spec['parameters'] == dict(bookmakers=BOOKS, dateFormat='iso', oddsFormat='decimal',
        markets='h2h,spreads,totals', date='2025-10-21T22:00:00Z')
    plan = source_plan(EVENT, 'basketball_nba_preseason')
    assert '/basketball_nba_preseason/' in plan['requests']['discover']['path']
    assert not plan['selection']['nba_player_props_documented_for_selected_regions']
    assert not plan['selection']['mexican_contract_equivalence_verified']
    assert not plan['actionable'] and not plan['selection']['current_quotes_verified']


@pytest.mark.parametrize('kwargs', [
    dict(event_id='../escape'), dict(event_id=EVENT, sport='soccer_epl'),
    dict(event_id=EVENT, kind='markets', date='2025-10-21T22:00:00Z'),
    dict(event_id=EVENT, kind='odds', markets='player_points'),
    dict(event_id=EVENT, kind='odds', markets=['h2h', 'h2h']),
    dict(event_id=EVENT, kind='odds', markets=['h2h', 'spreads', 'totals', 'player_points']),
])
def test_invalid_scope_or_cost_shape_rejected(kwargs):
    with pytest.raises(ValueError):
        selected_request(**kwargs)


def test_offline_cli_does_not_read_credentials_create_audit_or_call_network(monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['quantnba', 'odds-source-plan'])
    monkeypatch.setattr(Settings, 'load', lambda: pytest.fail('offline plan read private settings'))
    monkeypatch.setattr(httpx, 'Client', lambda *a, **kw: pytest.fail('offline plan created network client'))
    main()
    output = json.loads(capsys.readouterr().out)
    assert [s['bookmaker_key'] for s in output['selection']['sources']] == BOOKS.split(',')
    assert output['requests'] is None and output['paid_API_calls'] == 0
