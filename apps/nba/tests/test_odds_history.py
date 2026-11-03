from datetime import UTC, datetime, timedelta
import json

import pytest

from nba import odds_history as oh

GAMES = [
    dict(game_id='g1', date='2025-01-14', season='2024-25', home=dict(name='Boston Celtics'), away=dict(name='Miami Heat')),
    dict(game_id='g2', date='2025-01-14', season='2024-25', home=dict(name='Denver Nuggets'), away=dict(name='Utah Jazz')),
    dict(game_id='g3', date='2025-01-18', season='2024-25', home=dict(name='Boston Celtics'), away=dict(name='Utah Jazz')),
    dict(game_id='g4', date='2023-01-14', season='2022-23', home=dict(name='Boston Celtics'), away=dict(name='Utah Jazz')),
]
TIPS = {'g1': datetime(2025, 1, 15, 0, 30, tzinfo=UTC), 'g2': datetime(2025, 1, 15, 2, 0, tzinfo=UTC)}


class Reply:
    def __init__(self, body, last=10, remaining=20000, status=200):
        self.content, self.status_code = json.dumps(body).encode(), status
        self.headers = {'x-requests-last': str(last), 'x-requests-remaining': str(remaining)}


class Client:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def get(self, url, params, timeout):
        self.calls.append(params['date'])
        return self.replies.pop(0)


def test_plan_has_one_slot_per_game_day_and_costs_ten_credits_per_market():
    p = oh.plan(GAMES, TIPS, {'2024-25'})
    assert [s['day'] for s in p['slots']] == ['2025-01-14', '2025-01-18']
    assert p['slots'][0]['time'] == '2025-01-15T00:00:00+00:00' and p['slots'][0]['time_source'] == 'tipoff'
    assert p['slots'][1]['time_source'] == 'fallback' and p['slots'][1]['time'].endswith('16:30:00+00:00')
    assert p['credits_per_snapshot'] == 10 and p['total_credits'] == 20
    assert oh.plan(GAMES, TIPS, {'2024-25'}, ('h2h', 'totals'))['total_credits'] == 40


def test_nothing_is_bought_before_november_first():
    p = oh.plan(GAMES, TIPS, {'2024-25'})
    client = Client([Reply({})])
    with pytest.raises(PermissionError):
        oh.fetch(p, '.', 'k', cap=100, reserve=0, now=datetime(2026, 10, 31, 23, 59, tzinfo=UTC), client=client)
    assert client.calls == []


def test_fetch_caches_each_response_respects_cap_and_never_repays(tmp_path):
    p = oh.plan(GAMES, TIPS, {'2024-25'})
    now = datetime(2026, 11, 2, tzinfo=UTC)
    first = oh.fetch(p, tmp_path, 'k', cap=10, reserve=0, now=now, client=Client([Reply({'data': []})]))
    assert first['fetched'] == 1 and first['stop'] == 'cap' and len(oh.cached(p, tmp_path)) == 1
    again = Client([Reply({'data': []})])
    second = oh.fetch(p, tmp_path, 'k', cap=100, reserve=0, now=now, client=again)
    assert second['fetched'] == 1 and len(again.calls) == 1 and second['stop'] is None
    assert len(oh.cached(p, tmp_path)) == 2 and len((tmp_path / 'manifest.jsonl').read_text().splitlines()) == 2


def test_reserve_error_and_unexpected_cost_stop_the_run(tmp_path):
    p = oh.plan(GAMES, TIPS, {'2024-25'})
    now = datetime(2026, 11, 2, tzinfo=UTC)
    r = oh.fetch(p, tmp_path / 'a', 'k', cap=100, reserve=15000, now=now, client=Client([Reply({}, remaining=15005), Reply({})]))
    assert r['fetched'] == 1 and r['stop'] == 'reserve'
    e = oh.fetch(p, tmp_path / 'b', 'k', cap=100, reserve=0, now=now, client=Client([Reply({}, status=429)]))
    assert e['fetched'] == 0 and e['stop'] == 'http_429'
    c = oh.fetch(p, tmp_path / 'c', 'k', cap=100, reserve=0, now=now, client=Client([Reply({}, last=30)]))
    assert c['stop'] == 'unexpected_cost'


def event(home, away, start, updated, home_price=1.5, away_price=2.7):
    return dict(home_team=home, away_team=away, commence_time=start, bookmakers=[
        dict(key='pinnacle', last_update=updated, markets=[dict(key='h2h', last_update=updated, outcomes=[
            dict(name=home, price=home_price), dict(name=away, price=away_price)])])])


def test_load_matches_games_and_rejects_started_stale_or_unmatched(tmp_path):
    p = oh.plan(GAMES, TIPS, {'2024-25'})
    snap = {'timestamp': '2025-01-15T00:00:00Z', 'data': [
        event('Boston Celtics', 'Miami Heat', '2025-01-15T00:30:00Z', '2025-01-14T23:55:00Z'),
        event('Denver Nuggets', 'Utah Jazz', '2025-01-15T02:00:00Z', '2025-01-14T10:00:00Z'),
        event('Boston Celtics', 'Utah Jazz', '2025-01-14T23:00:00Z', '2025-01-14T22:00:00Z'),
        event('Phoenix Suns', 'Utah Jazz', '2025-01-15T02:00:00Z', '2025-01-14T23:55:00Z')]}
    (tmp_path / (p['slots'][0]['name'] + '.json')).write_text(json.dumps(snap))
    rows, stats = oh.load(p, tmp_path, GAMES)
    assert [r['game_id'] for r in rows] == ['g1']
    assert rows[0]['home_no_vig'] == pytest.approx((1 / 1.5) / (1 / 1.5 + 1 / 2.7)) and rows[0]['minutes_to_tipoff'] == 30
    assert stats['already_started'] == 1 and stats['invalid_or_stale_price'] == 1 and stats['unmatched_event'] == 1
    assert stats['missing_snapshot'] == 1


def test_the_providers_clippers_spelling_matches_the_history_and_the_price_side_is_right(tmp_path):
    games = GAMES + [dict(game_id='g5', date='2025-01-14', season='2024-25', home=dict(name='LA Clippers'), away=dict(name='Miami Heat'))]
    p = oh.plan(games, TIPS, {'2024-25'})
    snap = {'timestamp': '2025-01-15T00:00:00Z', 'data': [
        event('Los Angeles Clippers', 'Miami Heat', '2025-01-15T00:30:00Z', '2025-01-14T23:55:00Z', home_price=1.4, away_price=3.2)]}
    (tmp_path / (p['slots'][0]['name'] + '.json')).write_text(json.dumps(snap))
    rows, stats = oh.load(p, tmp_path, games)
    assert [r['game_id'] for r in rows] == ['g5'] and stats.get('unmatched_event', 0) == 0
    assert rows[0]['home_decimal'] == 1.4 and rows[0]['home_no_vig'] > .5


def test_power_devig_sums_to_one_and_loads_more_margin_on_the_longshot():
    home, away = 1.25, 4.4  # clear favourite
    p = oh.power_no_vig(home, away)
    q = oh.power_no_vig(away, home)
    assert p + q == pytest.approx(1, abs=1e-9)
    proportional = (1 / home) / (1 / home + 1 / away)
    assert p > proportional  # the favourite keeps more probability than under the proportional split
    assert oh.power_no_vig(1.9, 1.9) == pytest.approx(.5)


def test_a_game_is_never_priced_from_the_snapshot_of_the_day_before(tmp_path):
    games = GAMES + [dict(game_id='g6', date='2025-01-15', season='2024-25', home=dict(name='Boston Celtics'), away=dict(name='Utah Jazz'))]
    p = oh.plan(games, TIPS, {'2024-25'})
    # the 2025-01-14 snapshot also lists the next day's game, with a price a day old
    snap = {'timestamp': '2025-01-15T00:00:00Z', 'data': [
        event('Boston Celtics', 'Miami Heat', '2025-01-15T00:30:00Z', '2025-01-14T23:55:00Z'),
        event('Boston Celtics', 'Utah Jazz', '2025-01-15T19:00:00Z', '2025-01-14T23:55:00Z')]}
    (tmp_path / (p['slots'][0]['name'] + '.json')).write_text(json.dumps(snap))
    rows, stats = oh.load(p, tmp_path, games)
    assert [r['game_id'] for r in rows] == ['g1'] and stats['snapshot_other_day'] == 1


def test_the_date_sent_to_the_historical_endpoint_ends_in_z_not_in_an_offset(tmp_path):
    p = oh.plan(GAMES, TIPS, {'2024-25'})
    client = Client([Reply({'data': []}), Reply({'data': []})])
    oh.fetch(p, tmp_path, 'k', cap=100, reserve=0, now=datetime(2026, 11, 2, tzinfo=UTC), client=client)
    # the provider answered 422 INVALID_HISTORICAL_TIMESTAMP to '...+00:00' on 2026-10-23
    assert client.calls == ['2025-01-15T00:00:00Z', '2025-01-18T16:30:00Z']
    assert oh.api_time('2025-01-15T00:00:00+00:00') == '2025-01-15T00:00:00Z'
    assert oh.api_time('2025-01-14T19:00:00-05:00') == '2025-01-15T00:00:00Z'
