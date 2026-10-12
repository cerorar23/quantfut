from datetime import datetime, timezone

from qf.ingest import live


def test_live_run_writes_only_matches_in_window(monkeypatch):
    calls = []
    monkeypatch.setattr(live, '_candidatos', lambda: {'10': 'm1', '11': 'm2'})
    monkeypatch.setattr(live.af, 'get', lambda ep, p: ([
        {'fixture': {'id': 10, 'status': {'short': '2H', 'elapsed': 48}}, 'goals': {'home': 1, 'away': 0}},
        {'fixture': {'id': 11, 'status': {'short': 'FT', 'elapsed': 90}}, 'goals': {'home': 2, 'away': 2}},
        {'fixture': {'id': 99, 'status': {'short': '1H', 'elapsed': 5}}, 'goals': {'home': 0, 'away': 0}},
    ], {}))
    monkeypatch.setattr(live.af, 'check_quota', lambda m: None)
    monkeypatch.setattr(live.af, 'record_health', lambda *a, **k: None)
    monkeypatch.setattr(live, 'execute', lambda sql, p=(): calls.append(p) or 1)
    out = live.run()
    assert out['en_juego'] == 1
    assert calls[0] == (1, 0, 48, '2H', 'm1')


def test_no_candidates_makes_no_api_call(monkeypatch):
    monkeypatch.setattr(live, '_candidatos', lambda: {})
    monkeypatch.setattr(live.af, 'get', lambda *a: (_ for _ in ()).throw(AssertionError('gasta cuota')))
    monkeypatch.setattr(live.af, 'record_health', lambda *a, **k: None)
    monkeypatch.setattr(live, 'execute', lambda sql, p=(): 0)
    assert live.run()['en_juego'] == 0
