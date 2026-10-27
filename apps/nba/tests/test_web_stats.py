from datetime import UTC, datetime
import json

import pytest

from nba import web_stats as ws

NOW = datetime(2026, 10, 27, 12, tzinfo=UTC)


def game(gid, day, home, away, hp, ap):
    return ws.normalize(f'00{gid}', day, home, away, hp, ap)


BOS, BKN, NYK, CHI = 'Boston Celtics', 'Brooklyn Nets', 'New York Knicks', 'Chicago Bulls'
GAMES = [
    game('22500001', '2026-02-27', BOS, BKN, 148, 111),     # temporada anterior: solo H2H y «temporada pasada»
    game('22500002', '2026-04-01', BKN, BOS, 99, 113),
    game('22600001', '2026-10-20', BOS, NYK, 107, 103),
    game('22600002', '2026-10-23', CHI, BOS, 90, 120),
    game('22600003', '2026-10-24', BKN, NYK, 100, 90),
    game('22600004', '2026-10-26', BOS, CHI, 134, 99),
    game('10600001', '2026-10-05', BOS, BKN, 80, 70),       # pretemporada: no cuenta
]


def test_normalize_rejects_ties_and_bad_ids():
    assert game('22600009', '2026-10-27', BOS, BKN, 100, 100) is None
    assert ws.normalize('abc', '2026-10-27', BOS, BKN, 100, 99) is None
    assert ws.normalize('0022600009', '2026-10-27', BOS, BOS, 100, 99) is None
    assert ws.normalize('0022600009', '2026-10-27', BOS, BKN, True, 99) is None


def test_season_boundaries():
    assert ws.season_of('2026-10-20') == '2026-27'
    assert ws.season_of('2027-04-10') == '2026-27'
    assert ws.season_of('2026-09-30') == '2026-27'
    assert ws.season_of('2026-06-20') == '2025-26'


def test_team_block_counts_only_regular_season_and_before_the_date():
    block = ws.team_block(ws.merge_games(GAMES), BOS, '2026-10-27')
    assert (block['season']['won'], block['season']['lost']) == (3, 0)
    assert block['home']['won'] == 2 and block['away']['won'] == 1
    assert block['streak'] == 3
    assert block['scoring'] == dict(games=3, points_for=120.3, points_against=97.3)
    assert block['rest_days'] == 0 and block['back_to_back'] is True     # jugó el 26 y juega el 27
    assert block['last_season']['won'] == 2 and block['last_season']['lost'] == 0
    assert [v['opponent'] for v in block['form']['all']] == [CHI, CHI, NYK, BKN, BKN]
    assert block['form']['all'][0]['date'] == '2026-10-26'               # más reciente primero
    assert len(block['form']['home']) == 3 and len(block['form']['away']) == 2
    assert all(v['home'] for v in block['form']['home']) and not any(v['home'] for v in block['form']['away'])


def test_a_played_game_does_not_include_itself():
    games = ws.merge_games(GAMES)
    block = ws.team_block(games, BOS, '2026-10-26')                       # el 26 aún no cuenta el partido del 26
    assert block['season']['won'] == 2
    assert block['form']['all'][0]['date'] == '2026-10-23'


def test_preseason_games_are_ignored_everywhere():
    games = ws.merge_games(GAMES)
    assert '0010600001' in [g['game_id'] for g in games]                # existe en los datos, pero no se usa
    h2h = ws.head_to_head(games, BOS, BKN, '2026-10-27')
    assert [m['date'] for m in h2h['matches']] == ['2026-04-01', '2026-02-27']
    assert (h2h['home_wins'], h2h['away_wins']) == (2, 0) and h2h['average_total'] == 235.5


def test_rest_is_not_reported_after_a_long_gap():
    block = ws.team_block(ws.merge_games(GAMES), BKN, '2026-10-27')      # último partido el 24
    assert block['rest_days'] == 2 and block['back_to_back'] is False
    far = ws.team_block(ws.merge_games(GAMES[:2]), BKN, '2026-10-27')    # último partido en abril
    assert far['rest_days'] is None and far['back_to_back'] is None


def test_streak_signs():
    views = lambda *won: [dict(won=w) for w in won]
    assert ws.streak(views(True, True, False)) == 2
    assert ws.streak(views(False, True)) == -1
    assert ws.streak([]) == 0


def test_standings_rank_by_win_rate_inside_the_conference():
    games = ws.merge_games(GAMES)
    boston = ws.standings_rank(games, BOS, '2026-10-27')
    assert boston == dict(rank=1, of=15, conference='este')
    assert ws.standings_rank(games, 'Utah Jazz', '2026-10-27')['rank'] is None   # sin partidos: no se inventa posición
    assert ws.standings_rank(games, 'Equipo Inventado', '2026-10-27') == dict(rank=None, of=0, conference=None)


def test_merge_drops_a_game_two_sources_disagree_about():
    a = [game('22600001', '2026-10-20', BOS, NYK, 107, 103)]
    b = [game('22600001', '2026-10-20', BOS, NYK, 107, 104), game('22600002', '2026-10-23', CHI, BOS, 90, 120)]
    assert [g['game_id'] for g in ws.merge_games(a, b)] == ['0022600002']
    assert [g['game_id'] for g in ws.merge_games(a, a)] == ['0022600001']


def test_build_feed_is_json_safe_and_skips_foreign_ids():
    events = [dict(event_id='0022600005', home_team=BOS, away_team=BKN, tipoff_utc='2026-10-27T21:30:00+00:00'),
              dict(event_id='not-a-number', home_team=BOS, away_team=BKN, tipoff_utc='2026-10-27T21:30:00+00:00')]
    feed = ws.build_feed(GAMES, events, NOW)
    assert list(feed['events']) == ['0022600005']
    event = feed['events']['0022600005']
    assert event['as_of'] == '2026-10-27' and [t['name'] for t in event['teams']] == [BOS, BKN]
    json.dumps(feed, allow_nan=False)
    assert 'hash' not in json.dumps(feed).lower()


def test_tipoff_after_midnight_utc_uses_the_eastern_date():
    assert ws.et_day('2026-10-27T02:00:00+00:00') == '2026-10-26'


def test_from_box_reads_the_dashboard_shape():
    row = dict(game_id='0022600001', date='2026-10-20', home=dict(name=BOS, points=107), away=dict(name=NYK, points=103))
    assert ws.from_box(row)['hp'] == 107
    assert ws.from_box(dict(row, home=dict(name=BOS, points=None))) is None


def fake_dashboard(monkeypatch, events_by_folder):
    import sys
    import types

    class LiveCohort:
        def __init__(self, folder):
            self.folder = folder

        def data(self, now):
            events = events_by_folder[self.folder.name]
            if isinstance(events, Exception):
                raise events
            return dict(events=events)

    module = types.ModuleType('nba.multimarket_live_dashboard')
    module.LiveCohort = LiveCohort
    monkeypatch.setitem(sys.modules, 'nba.multimarket_live_dashboard', module)


def cohort_folder(root, name, completed):
    folder = root / name
    folder.mkdir()
    (folder / 'bundle.seal.json').write_text('{}')
    (folder / 'completed_games.json').write_text(json.dumps(dict(games=completed)))
    return folder


def test_read_cohorts_uses_verified_results_and_skips_held_or_broken_cohorts(tmp_path, monkeypatch):
    box = lambda gid, day, h, a, hp, ap: dict(game_id=gid, date=day, home=dict(name=h, points=hp), away=dict(name=a, points=ap))
    cohort_folder(tmp_path, 'c1', [box('0022600001', '2026-10-20', BOS, NYK, 107, 103)])
    cohort_folder(tmp_path, 'c2', [box('0022600002', '2026-10-23', 'Equipo Roto', NYK, 1, 2)])
    cohort_folder(tmp_path, 'c3', [])
    event = lambda gid, status, final=None: dict(event_id=gid, home_team=BOS, away_team=CHI, tipoff_utc='2026-10-26T23:30:00+00:00', status=status, final=final)
    fake_dashboard(monkeypatch, {
        'c1': [event('0022600004', 'evaluated', dict(home=134, away=99)), event('0022600005', 'pending'), event('0022600006', 'validation_hold', dict(home=1, away=2))],
        'c2': ValueError('live cohort bundle changed'),
        'c3': [event('0022600007', 'awaiting_result')],
    })
    games, events = ws.read_cohorts(tmp_path, NOW)
    ids = sorted(g['game_id'] for g in games if g)
    assert ids == ['0022600001', '0022600004']                      # c2 no validó: no aporta ni sus partidos terminados
    assert '0022600006' not in ids                      # en cuarentena: ni evento ni resultado
    assert sorted(e['event_id'] for e in events) == ['0022600004', '0022600005', '0022600007']
    final = next(g for g in games if g and g['game_id'] == '0022600004')
    assert (final['date'], final['hp'], final['ap']) == ('2026-10-26', 134, 99)   # fecha del Este, no la UTC


def test_cli_writes_a_valid_feed_atomically(tmp_path, monkeypatch):
    box = lambda gid, day, h, a, hp, ap: dict(game_id=gid, date=day, home=dict(name=h, points=hp), away=dict(name=a, points=ap))
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'games.json').write_text(json.dumps([box('0022500001', '2026-02-27', BOS, BKN, 148, 111)]))
    cohorts = tmp_path / 'cohorts'
    cohorts.mkdir()
    cohort_folder(cohorts, 'c1', [box('0022600001', '2026-10-20', BOS, NYK, 107, 103)])
    fake_dashboard(monkeypatch, {'c1': [dict(event_id='0022600130', home_team=BOS, away_team=BKN, tipoff_utc='2026-10-27T23:30:00+00:00', status='pending', final=None)]})
    out = tmp_path / 'out' / 'nba_stats.json'
    out.parent.mkdir()
    import sys
    monkeypatch.setattr(sys, 'argv', ['web_stats', '--cohorts', str(cohorts), '--data', str(data), '--output', str(out)])
    ws.main()
    feed = json.loads(out.read_text(encoding='utf8'))
    assert list(feed['events']) == ['0022600130'] and feed['games_used'] == 2
    assert not list(out.parent.glob('*.tmp'))
