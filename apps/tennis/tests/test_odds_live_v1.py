"""Artificial API replies only: no credentials and no provider requests."""
import json
import pytest
from tennis_odds_live_v1 import run, football_reserve, latest_market, devigged


def fake(remaining=9000):
    calls = []

    def transport(path, params):
        calls.append((path, params))
        if path == 'sports':
            body = [dict(key='tennis_atp_x', group='Tennis', active=True), dict(key='tennis_wta_y', group='Tennis', active=True),
                    dict(key='soccer_epl', group='Soccer', active=True), dict(key='tennis_atp_z', group='Tennis', active=False)]
            return json.dumps(body).encode(), {'x-requests-last': '0', 'x-requests-remaining': str(remaining), 'x-requests-used': '0'}
        event = dict(id='e1', commence_time='2026-10-20T12:00:00Z', home_team='Ana Paz', away_team='Eva Sol',
                     bookmakers=[dict(key='b1', markets=[dict(key='h2h', outcomes=[dict(name='Ana Paz', price=1.5), dict(name='Eva Sol', price=2.6)])])])
        return json.dumps([event]).encode(), {'x-requests-last': '1', 'x-requests-remaining': str(remaining - 1), 'x-requests-used': '1'}
    return transport, calls


def test_one_region_h2h_two_slots_per_day_and_active_tennis_only(tmp_path):
    transport, calls = fake()
    r = run(tmp_path, 'k', transport, clock=lambda: '2026-10-20T01:00:00+00:00')
    assert [c['sport_key'] for c in r['captured']] == ['tennis_atp_x', 'tennis_wta_y']
    assert all(p == dict(regions='eu', markets='h2h', oddsFormat='decimal', dateFormat='iso') for path, p in calls if path != 'sports')
    again = run(tmp_path, 'k', transport, clock=lambda: '2026-10-20T05:00:00+00:00')
    assert not again['captured'] and len(again['skipped']) == 2
    pm = run(tmp_path, 'k', transport, clock=lambda: '2026-10-20T13:00:00+00:00')
    assert len(pm['captured']) == 2


def test_monthly_cap_and_football_reserve_block_paid_calls(tmp_path):
    transport, _ = fake(remaining=football_reserve('2026-10-20T01:00:00+00:00'))
    r = run(tmp_path, 'k', transport, clock=lambda: '2026-10-20T01:00:00+00:00')
    assert not r['captured'] and 'Credit limit' in r['blocked']['reason']
    transport, _ = fake()
    r = run(tmp_path / 'b', 'k', transport, clock=lambda: '2026-10-20T01:00:00+00:00', monthly_cap=1)
    assert len(r['captured']) == 1 and r['blocked'] is not None


def test_latest_market_devigs_and_respects_time(tmp_path):
    transport, _ = fake()
    run(tmp_path, 'k', transport, clock=lambda: '2026-10-20T01:00:00+00:00')
    m = latest_market(tmp_path, 'Eva Sol', 'Ana Paz', '2026-10-20T11:00:00Z')
    assert m['probability_a'] == pytest.approx((1/2.6) / (1/1.5 + 1/2.6)) and m['bookmakers'] == 1
    assert latest_market(tmp_path, 'Eva Sol', 'Ana Paz', '2026-10-19T11:00:00Z') is None
    assert devigged(dict(bookmakers=[]), 'a', 'b') == (None, 0)
