import copy
import json

import pytest

from nba import stats_proxy

HOME, AWAY = 100, 200


def line(minutes, points=0, fgm=0, fga=0, threes=0, fg3a=0, ftm=0, fta=0, oreb=0, dreb=0, ast=0, tov=0, pf=0):
    return dict(minutes=minutes, fieldGoalsMade=fgm, fieldGoalsAttempted=fga, threePointersMade=threes,
                threePointersAttempted=fg3a, freeThrowsMade=ftm, freeThrowsAttempted=fta, reboundsOffensive=oreb,
                reboundsDefensive=dreb, reboundsTotal=oreb + dreb, assists=ast, steals=0, blocks=0, turnovers=tov,
                foulsPersonal=pf, points=points, plusMinusPoints=0.)


def side(team_id, tricode, first_id, scorer_points):
    """Five players: one scorer (all the points via free throws), four bench-warmers; team minutes 240."""
    players = [dict(personId=first_id, firstName='A', familyName='B', comment='',
                    statistics=line('48:00', points=scorer_points, ftm=scorer_points, fta=scorer_points, dreb=3))]
    players += [dict(personId=first_id + k, firstName='C', familyName='D', comment='',
                     statistics=line('48:00', oreb=1)) for k in range(1, 5)]
    players.append(dict(personId=first_id + 9, firstName='E', familyName='F', comment='DNP - Coach\'s Decision',
                        statistics=line('')))
    total = line('240:00', points=scorer_points, ftm=scorer_points, fta=scorer_points, oreb=4, dreb=3)
    return dict(teamId=team_id, teamCity='X', teamName=tricode, teamTricode=tricode, players=players, statistics=total)


def payload(game_id='0022500001'):
    return dict(boxScoreTraditional=dict(gameId=game_id, homeTeamId=HOME, awayTeamId=AWAY,
                                         homeTeam=side(HOME, 'HHH', 1000, 100), awayTeam=side(AWAY, 'AAA', 2000, 90)))


def base_rows(game_id='0022500001'):
    rows = []
    for team, first, points in ((HOME, 1000, 100), (AWAY, 2000, 90)):
        for k in range(5):
            rows.append(dict(game_id=game_id, date='2025-10-27', season='2025-26', season_type='regular',
                             player_id=first + k, team_id=team, name='N', participated=True, minutes=48.,
                             points=points if k == 0 else 0, rebounds=3 if k == 0 else 1, assists=0, status=''))
        rows.append(dict(game_id=game_id, date='2025-10-27', season='2025-26', season_type='regular',
                         player_id=first + 9, team_id=team, name='N', participated=False, minutes=0., points=0,
                         rebounds=0, assists=0, status=''))
    return rows


def test_a_consistent_official_box_is_accepted():
    assert stats_proxy.validate('0022500001', payload(), base_rows()) == []


def test_extended_rows_carry_the_official_counts_and_zeros_for_dnp():
    rows = stats_proxy.extend_rows('0022500001', payload(), base_rows())
    scorer = next(r for r in rows if r['player_id'] == 1000)
    assert (scorer['fta'], scorer['ftm'], scorer['dreb'], scorer['count_source']) == (100, 100, 3, 'nba_stats_v3_proxy')
    assert next(r for r in rows if r['player_id'] == 1009)['fta'] == 0
    game = stats_proxy.game_entry('0022500001', payload(), base_rows())
    assert game['home']['matchup'] == 'HHH vs. AAA' and game['away']['matchup'] == 'AAA @ HHH'
    assert game['home']['minutes'] == 48. and game['home']['players_tov'] == 0


@pytest.mark.parametrize('mutate, issue', [
    (lambda b: b['homeTeam']['players'][1]['statistics'].update(minutes='47:60'), 'minutes_60'),
    (lambda b: b['homeTeam']['statistics'].update(points=101), 'team_sum_points'),
    (lambda b: b['homeTeam']['statistics'].update(minutes='240:20'), 'team_minutes'),
    (lambda b: b['awayTeam']['players'][0]['statistics'].update(reboundsTotal=9), 'player_identity'),
    (lambda b: b['homeTeam']['players'][5]['statistics'].update(foulsPersonal=2), 'dnp_inconsistent'),
    (lambda b: b.update(gameId='0022500002'), 'game_id'),
    (lambda b: b.update(homeTeamId=AWAY), 'home_away'),
])
def test_official_box_corruptions_are_rejected(mutate, issue):
    broken = copy.deepcopy(payload())
    mutate(broken['boxScoreTraditional'])
    assert issue in stats_proxy.validate('0022500001', broken, base_rows())


def test_disagreement_with_the_base_rows_is_rejected_not_resolved():
    base = base_rows()
    base[0]['points'] += 1
    assert 'base_counts' in stats_proxy.validate('0022500001', payload(), base)
    base = base_rows()
    base[1]['minutes'] = 30.
    assert 'base_minutes' in stats_proxy.validate('0022500001', payload(), base)


def test_a_tied_final_is_rejected():
    tied = payload()
    box = tied['boxScoreTraditional']
    for team in (box['homeTeam'], box['awayTeam']):
        team['players'][0]['statistics'].update(points=95, freeThrowsMade=95, freeThrowsAttempted=95)
        team['statistics'].update(points=95, freeThrowsMade=95, freeThrowsAttempted=95)
    base = base_rows()
    for r in base:
        if r['player_id'] in (1000, 2000):
            r['points'] = 95
    assert 'tied_final' in stats_proxy.validate('0022500001', tied, base)


def rotation(game_id='0022500001', end=28800):
    def table(name, team, first):
        rows = [[game_id, team, first + k, 0, end, 100 if k == 0 else 0] for k in range(5)]
        return dict(name=name, headers=['GAME_ID', 'TEAM_ID', 'PERSON_ID', 'IN_TIME_REAL', 'OUT_TIME_REAL',
                                        'PLAYER_PTS'], rowSet=rows)
    away = table('AwayTeam', AWAY, 2000)
    away['rowSet'][0][-1] = 90
    return dict(resultSets=[table('HomeTeam', HOME, 1000), away])


def test_rotation_with_five_on_the_floor_is_accepted():
    assert stats_proxy.validate_rotation('0022500001', rotation(), base_rows()) == []


@pytest.mark.parametrize('mutate, issue', [
    (lambda r: r['resultSets'][0]['rowSet'].pop(), 'not_five_on_floor'),
    (lambda r: r['resultSets'][0]['rowSet'].append(['0022500001', HOME, 1001, 0, 100, 0]), 'overlap'),
    (lambda r: r['resultSets'][0]['rowSet'][0].__setitem__(5, 99), 'points'),
    (lambda r: [row.__setitem__(4, 28000) for t in r['resultSets'] for row in t['rowSet']], 'duration'),
])
def test_rotation_corruptions_are_rejected(mutate, issue):
    broken = rotation()
    mutate(broken)
    assert issue in stats_proxy.validate_rotation('0022500001', broken, base_rows())


def test_capture_never_exceeds_the_credit_ceiling(tmp_path, monkeypatch):
    calls = []

    def fake(game_id, tier, key, timeout=120, resource='box'):
        calls.append(game_id)
        body = json.dumps(payload(game_id)).encode()
        return dict(game_id=game_id, tier=tier, status=200, credits=stats_proxy.CREDITS[tier], bytes=len(body)), body

    monkeypatch.setattr(stats_proxy, 'fetch', fake)
    summary = stats_proxy.capture(['a', 'b', 'c', 'd'], 'premium', 25, tmp_path, key='unused', pause=0)
    assert calls == ['a', 'b'] and summary['credits_spent'] == 20
    assert (tmp_path / 'a.json').exists() and not (tmp_path / 'c.json').exists()


def test_capture_stops_after_two_consecutive_failures(tmp_path, monkeypatch):
    def fake(game_id, tier, key, timeout=120, resource='box'):
        return dict(game_id=game_id, tier=tier, status=422, credits=0, bytes=1), b'{"code":"RESP001"}'

    monkeypatch.setattr(stats_proxy, 'fetch', fake)
    summary = stats_proxy.capture(['a', 'b', 'c'], 'basic', 10, tmp_path, key='unused', pause=0)
    assert summary['requests'] == 2 and summary['credits_spent'] == 0
    assert not list(tmp_path.glob('*.json'))
