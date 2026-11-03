import json
from datetime import UTC, datetime

import pytest

from nba import multimarket_v13_live as live
from nba.audit import write_json

HOME, AWAY = 1610612741, 1610612747


def card(slug, day):
    return f'<a href="/game/{slug}" data-track="click" data-content="AAA @ BBB, {day}">'.encode()


def page(gid, status, tip='2026-10-21T23:00:00Z', home=110, away=104):
    team = lambda tid, pts, city: dict(teamId=tid, teamCity=city, teamName='Club', teamTricode=city[:3].upper(), score=pts,
                                       statistics=dict(points=pts),
                                       players=[dict(personId=tid + 1, firstName='Ana', familyName=city, comment='',
                                                     statistics=dict(minutes='30:00', points=pts, reboundsTotal=7, assists=4))])
    game = dict(gameId=gid, gameStatus=status, gameTimeUTC=tip, homeTeamId=HOME, awayTeamId=AWAY,
                homeTeam=team(HOME, home, 'Bbb'), awayTeam=team(AWAY, away, 'Aaa'))
    return ('<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(dict(props=dict(pageProps=dict(game=game)))) + '</script>').encode()


class Site:
    """Two days of games: g1 on 10-20 (final), g2 on 10-21 (status given)."""

    def __init__(self, second_status=3):
        self.second_status, self.calls = second_status, []

    def __call__(self, url):
        self.calls.append(url)
        if 'games?date=' in url:
            day = url.rsplit('=', 1)[1]
            slug = {'2026-10-20': 'aaa-vs-bbb-0022600001', '2026-10-21': 'aaa-vs-bbb-0022600002'}[day]
            return 200, card(slug, day)
        gid = url.split('/game/')[1].split('/')[0].rsplit('-', 1)[1]
        tip = {'0022600001': '2026-10-20T23:00:00Z', '0022600002': '2026-10-21T23:00:00Z'}[gid]
        return 200, page(gid, 3 if gid == '0022600001' else self.second_status, tip)


def test_second_run_downloads_nothing_it_already_has(tmp_path):
    cache = tmp_path / 'cache'
    first = Site()
    games, not_final = live.completed('2026-10-20', '2026-10-21', first, cache)
    assert [g['game_id'] for g in games] == ['0022600001', '0022600002'] and not_final == []
    assert len(first.calls) == 4  # per day: card + box score
    again = Site()
    games2, _ = live.completed('2026-10-20', '2026-10-21', again, cache)
    assert games2 == games and again.calls == []


def test_only_the_new_day_is_fetched_when_the_window_grows(tmp_path):
    cache = tmp_path / 'cache'
    live.completed('2026-10-20', '2026-10-20', Site(), cache)
    grown = Site()
    games, _ = live.completed('2026-10-20', '2026-10-21', grown, cache)
    assert len(games) == 2 and len(grown.calls) == 2 and 'date=2026-10-21' in grown.calls[0]


def test_a_game_that_is_not_final_is_reported_and_never_cached(tmp_path):
    cache = tmp_path / 'cache'
    games, not_final = live.completed('2026-10-20', '2026-10-21', Site(second_status=2), cache)
    assert [g['game_id'] for g in games] == ['0022600001']
    assert not_final == [dict(game_id='0022600002', date='2026-10-21', status=2, tipoff_utc='2026-10-21T23:00:00+00:00')]
    assert not (cache / 'games' / '0022600002.json').exists() and not (cache / 'days' / '2026-10-21.json').exists()
    assert (cache / 'days' / '2026-10-20.json').exists()
    # once the game finishes the next run picks it up
    games, not_final = live.completed('2026-10-20', '2026-10-21', Site(second_status=3), cache)
    assert len(games) == 2 and not_final == []


def test_without_a_cache_behaviour_is_unchanged(tmp_path):
    site = Site()
    games, _ = live.completed('2026-10-20', '2026-10-21', site)
    again = Site()
    live.completed('2026-10-20', '2026-10-21', again)
    assert len(games) == 2 and len(again.calls) == len(site.calls) == 4


def test_a_corrupt_or_mismatched_cache_entry_is_an_error_not_a_silent_miss(tmp_path):
    cache = tmp_path / 'cache'
    live.completed('2026-10-20', '2026-10-20', Site(), cache)
    path = cache / 'games' / '0022600001.json'
    entry = json.loads(path.read_bytes())
    write_json(path, dict(entry, date='2026-10-19'))
    with pytest.raises(ValueError, match='corrupt completed-game cache'):
        live.completed('2026-10-20', '2026-10-20', Site(), cache)


def test_box_score_with_another_game_id_is_refused(tmp_path):
    def wrong(url):
        status, body = Site()(url)
        return status, body.replace(b'0022600001', b'0022600099') if 'box-score' in url else body
    with pytest.raises(ValueError, match='game id disagrees'):
        live.completed('2026-10-20', '2026-10-20', wrong)


def seal_inputs(tmp_path, monkeypatch):
    from test_multimarket_v13_live import DAY, PROTOCOL, V12, fake_get, history_games, model, parsed_report, player_rows
    from nba import injury_pdf
    model_dir = tmp_path / 'model'
    model_dir.mkdir()
    write_json(model_dir / 'model.json', model())
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received))
    return model_dir, DAY, PROTOCOL, V12, fake_get, history_games, player_rows


def test_seal_refuses_when_a_past_game_is_still_in_progress(tmp_path, monkeypatch):
    model_dir, day, protocol, v12, fake_get, history_games, player_rows = seal_inputs(tmp_path, monkeypatch)

    def get(url):
        if url.endswith('/box-score') and '0022600099' in url:
            return 200, page('0022600099', 2, '2026-10-20T23:00:00Z')
        if 'games?date=2026-10-20' in url:
            return 200, card('aaa-vs-bbb-0022600099', '2026-10-20')
        return fake_get(url)
    with pytest.raises(ValueError, match='past games not final'):
        live.seal(model_dir, tmp_path / 'cohort', day, player_rows(), history_games(), protocol, v12,
                  now=datetime(2026, 10, 21, 14, 29, tzinfo=UTC), get=get, first_completed_day='2026-10-20', cache=tmp_path / 'c')


def test_seal_records_a_postponed_game_and_uses_the_cache(tmp_path, monkeypatch):
    model_dir, day, protocol, v12, fake_get, history_games, player_rows = seal_inputs(tmp_path, monkeypatch)

    def get(url):
        if 'games?date=2026-10-20' in url:
            return 200, card('aaa-vs-bbb-0022600099', '2026-10-20')
        if '0022600099' in url:
            return 200, page('0022600099', 1, '2026-10-20T23:00:00Z')
        return fake_get(url)
    result = live.seal(model_dir, tmp_path / 'cohort', day, player_rows(), history_games(), protocol, v12,
                       now=datetime(2026, 10, 21, 14, 29, tzinfo=UTC), get=get, first_completed_day='2026-10-20', cache=tmp_path / 'c')
    sealed = json.loads((tmp_path / 'cohort' / 'completed_games.json').read_bytes())
    assert result['games'] == 1 and sealed['games'] == []
    assert [g['game_id'] for g in sealed['not_final']] == ['0022600099'] and sealed['not_final'][0]['status'] == 1


def test_box_score_minutes_and_player_rows():
    assert live.box_minutes('') == 0 and live.box_minutes('33:15') == pytest.approx(33.25)
    assert live.box_minutes('PT23M56.00S') == pytest.approx(23 + 56 / 60) and live.box_minutes('PT00M00.00S') == 0
    # nba.com rounding: a full minute written as :60 (the producer stopped on '10:60' on 2026-10-24)
    assert live.box_minutes('10:60') == pytest.approx(11.) and live.box_minutes('PT10M60.00S') == pytest.approx(11.)
    with pytest.raises(ValueError):
        live.box_minutes('10:61')
    for bad in ('PT33M75.00S', '33', '33:75'):
        with pytest.raises(ValueError):
            live.box_minutes(bad)
    game = dict(homeTeam=dict(teamId=HOME, players=[
                    dict(personId=7, firstName='Ana', familyName='Uno', comment='', statistics=dict(minutes='12:30', points=9, reboundsTotal=3, assists=2)),
                    dict(personId=8, firstName='Eva', familyName='Dos', comment="DNP - Coach's Decision", statistics=dict(minutes='', points=0, reboundsTotal=0, assists=0))]),
                awayTeam=dict(teamId=AWAY, players=[]))
    played, rested = live.player_rows(game, '0022600001', '2026-10-20')
    assert (played['participated'], played['minutes'], played['name'], played['team_id']) == (True, 12.5, 'Ana Uno', HOME)
    assert (played['points'], played['rebounds'], played['assists']) == (9, 3, 2)
    assert (rested['participated'], rested['minutes']) == (False, 0.)


def test_target_season_box_scores_value_players_without_history(tmp_path, monkeypatch):
    model_dir, day, protocol, v12, fake_get, history_games, player_rows = seal_inputs(tmp_path, monkeypatch)
    from test_multimarket_v13_live import parsed_report
    from nba import injury_pdf
    # 'Ana Bbb' (home player of the pages below) only exists in five finished 2026-27 games
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received, name='Bbb, Ana'))
    days = [f'2026-10-{d}' for d in range(16, 21)]

    def get(url):
        for i, d in enumerate(days):
            gid = f'00226000{20 + i}'
            if f'games?date={d}' in url:
                return 200, card(f'aaa-vs-bbb-{gid}', d)
            if gid in url:
                return 200, page(gid, 3, f'{d}T23:00:00Z')
        return fake_get(url)
    now = datetime(2026, 10, 21, 14, 29, tzinfo=UTC)
    with_season = live.seal(model_dir, tmp_path / 'a', day, player_rows(), history_games(), protocol, v12, now=now, get=get,
                            first_completed_day=days[0], cache=tmp_path / 'c')
    without = live.seal(model_dir, tmp_path / 'b', day, player_rows(), history_games(), protocol, v12, now=now, get=get,
                        first_completed_day=day)
    used = lambda folder: json.loads((folder / 'bundle.json').read_bytes())['games'][0]['availability']
    assert with_season['games'] == without['games'] == 1
    assert used(tmp_path / 'a')['used'] == 1 and used(tmp_path / 'a')['unknown_player'] == 0
    assert used(tmp_path / 'b')['used'] == 0 and used(tmp_path / 'b')['unknown_player'] == 1
    completed = json.loads((tmp_path / 'a' / 'completed_games.json').read_bytes())
    assert len(completed['games']) == 5 and all('players' not in g for g in completed['games'])
