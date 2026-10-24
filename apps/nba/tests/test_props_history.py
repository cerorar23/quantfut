from datetime import UTC, datetime
import json

from nba import props_history as ph

GAMES = [
    dict(game_id='g1', date='2025-01-14', season='2024-25', home=dict(name='Boston Celtics'), away=dict(name='Miami Heat')),
    dict(game_id='g2', date='2025-01-14', season='2024-25', home=dict(name='LA Clippers'), away=dict(name='Utah Jazz')),
    dict(game_id='g3', date='2023-01-14', season='2022-23', home=dict(name='Boston Celtics'), away=dict(name='Utah Jazz')),
]
TIPS = {'g1': datetime(2025, 1, 15, 0, 30, tzinfo=UTC)}
NOW = datetime(2026, 10, 24, tzinfo=UTC)
EVENTS = dict(timestamp='x', data=[
    dict(id='e1', commence_time='2025-01-15T00:30:00Z', home_team='Boston Celtics', away_team='Miami Heat'),
    dict(id='e2', commence_time='2025-01-15T02:00:00Z', home_team='Los Angeles Clippers', away_team='Utah Jazz')])
ODDS = dict(timestamp='2025-01-15T00:00:00Z', data=dict(id='e1', commence_time='2025-01-15T00:30:00Z', bookmakers=[
    dict(key='fanduel', last_update='2025-01-14T23:58:00Z', markets=[dict(key='player_points', outcomes=[
        dict(name='Over', description='Jayson Tatum', price=1.9, point=27.5),
        dict(name='Under', description='Jayson Tatum', price=1.9, point=27.5),
        dict(name='Over', description='Derrick White', price=1.8, point=12.5)])])]))


class Reply:
    def __init__(self, body, last, remaining=100000, status=200):
        self.content, self.status_code = json.dumps(body).encode(), status
        self.headers = {'x-requests-last': str(last), 'x-requests-remaining': str(remaining)}


class Client:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def get(self, url, params, timeout):
        self.calls.append((url, params))
        return self.replies.pop(0)


def test_plan_costs_forty_credits_per_game_plus_one_per_day():
    p = ph.plan(GAMES, TIPS, {'2024-25'})
    assert [e['game_id'] for e in p['games']] == ['g1', 'g2']
    assert p['games'][0]['time'] == '2025-01-15T00:00:00+00:00' and p['games'][1]['time_source'] == 'fallback'
    assert p['credits_per_game'] == 40 and p['event_list_credits'] == 1 and p['total_credits'] == 81


def test_fetch_lists_events_then_pays_each_game_and_caches(tmp_path):
    p = ph.plan(GAMES, TIPS, {'2024-25'})
    client = Client([Reply(EVENTS, 1), Reply(ODDS, 40), Reply(ODDS, 30)])
    summary = ph.fetch(p, tmp_path, 'k', cap=1000, reserve=0, now=NOW, client=client)
    assert summary['fetched'] == 2 and summary['credits_spent'] == 71 and summary['stop'] is None
    assert client.calls[1][0].endswith('/events/e1/odds') and client.calls[2][0].endswith('/events/e2/odds')
    assert client.calls[1][1]['markets'] == ','.join(ph.MARKETS) and client.calls[1][1]['date'] == '2025-01-15T00:00:00Z'
    again = ph.fetch(p, tmp_path, 'k', cap=1000, reserve=0, now=NOW, client=Client([]))
    assert again['fetched'] == 0 and again['pending_before'] == 0


def test_fetch_stops_at_cap_reserve_error_and_unexpected_cost(tmp_path):
    p = ph.plan(GAMES, TIPS, {'2024-25'})
    assert ph.fetch(p, tmp_path / 'a', 'k', cap=40, reserve=0, now=NOW, client=Client([Reply(EVENTS, 1)]))['stop'] == 'cap'
    assert ph.fetch(p, tmp_path / 'b', 'k', cap=1000, reserve=100000, now=NOW, client=Client([Reply(EVENTS, 1, 100000 - 1)]))['stop'] == 'reserve'
    assert ph.fetch(p, tmp_path / 'c', 'k', cap=1000, reserve=0, now=NOW, client=Client([Reply({}, 0, status=401)]))['stop'] == 'http_401'
    stopped = ph.fetch(p, tmp_path / 'd', 'k', cap=1000, reserve=0, now=NOW, client=Client([Reply(EVENTS, 1), Reply(ODDS, 50)]))
    assert stopped['stop'] == 'unexpected_cost' and stopped['fetched'] == 1


def test_fetch_skips_games_without_event_and_honours_limit(tmp_path):
    p = ph.plan(GAMES, TIPS, {'2024-25'})
    only_first = dict(EVENTS, data=EVENTS['data'][:1])
    summary = ph.fetch(p, tmp_path, 'k', cap=1000, reserve=0, now=NOW, client=Client([Reply(only_first, 1), Reply(ODDS, 40)]))
    assert summary['fetched'] == 1 and summary['no_event'] == ['g2']
    limited = ph.fetch(p, tmp_path / 'l', 'k', cap=1000, reserve=0, now=NOW, client=Client([Reply(EVENTS, 1), Reply(ODDS, 40)]), limit=1)
    assert limited['fetched'] == 1


def test_load_keeps_only_two_sided_lines(tmp_path):
    p = ph.plan(GAMES, TIPS, {'2024-25'})
    ph.fetch(p, tmp_path, 'k', cap=1000, reserve=0, now=NOW, client=Client([Reply(EVENTS, 1), Reply(ODDS, 40), Reply(ODDS, 40)]))
    rows, stats = ph.load(p, tmp_path)
    assert len(rows) == 2 and stats['one_sided_line'] == 2 and stats['games'] == 2
    assert rows[0]['player'] == 'Jayson Tatum' and rows[0]['line'] == 27.5 and rows[0]['minutes_to_tipoff'] == 30
