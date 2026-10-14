import json
import urllib.error

import pytest

from qf.ingest import pitchapi_history as p


class Reply:
    def __init__(self, status, body):
        self.status, self.body = status, body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def client(*replies):
    queue = list(replies)
    calls = []

    def opener(request, timeout):
        calls.append(request)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    c = p.Client('k', opener=opener, sleep=lambda s: None)
    c.calls = calls
    return c


def http(status, retry=None):
    import email.message
    headers = email.message.Message()
    if retry:
        headers['Retry-After'] = str(retry)
    return urllib.error.HTTPError('u', status, 'x', headers, __import__('io').BytesIO(b'{"error":1}'))


def test_sends_key_and_user_agent_and_retries_429():
    c = client(http(429, 1), Reply(200, b'{"data":1}'))
    status, body, received = c.get('/v1/x')
    assert (status, body) == (200, b'{"data":1}') and received.endswith('Z')
    assert c.calls[0].get_header('X-api-key') == 'k'
    assert c.calls[0].get_header('User-agent') == p.USER_AGENT


def test_original_is_frozen_and_failures_are_not_repeated(tmp_path):
    c = client(Reply(404, b'{"error":"x"}'))
    first = p.fetch(c, tmp_path, 'stats', 'm_1', '/v1/matches/m_1/stats')
    again = p.fetch(c, tmp_path, 'stats', 'm_1', '/v1/matches/m_1/stats')
    assert first == again and first['status'] == 404 and len(c.calls) == 1


def test_tampered_original_is_rejected(tmp_path):
    p.fetch(client(Reply(200, b'{"data":1}')), tmp_path, 'stats', 'm_1', '/x')
    path = p.store_path(tmp_path, 'stats', 'm_1').with_name('m_1.json.gz')
    import gzip
    path.write_bytes(gzip.compress(b'{"data":2}'))
    with pytest.raises(ValueError, match='pitchapi_original_changed'):
        p.load(tmp_path, 'stats', 'm_1')


def stats(home, away):
    return json.dumps({'data': {'periods': [{'period': '1st', 'groups': [{'items': [
        {'key': 'expected_goals', 'home': '9', 'away': '9'}]}]}, {'period': 'All', 'groups': [
        {'items': [{'key': 'expected_goals', 'home': home, 'away': away}]}]}]}})


def test_team_xg_reads_the_full_match_period_only():
    assert p.team_xg(stats('0.78', '4.39')) == (0.78, 4.39)
    assert p.team_xg(stats(None, '1')) is None
