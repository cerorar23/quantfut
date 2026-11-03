import pytest

from nba import extended_box as eb

# points, rebounds, assists, threes, steals, blocks, fgm, fga, fg3a, ftm, fta, oreb, dreb, tov, pf, plus_minus
A = (20, 6, 3, 2, 1, 0, 7, 15, 5, 4, 5, 2, 4, 2, 3, 5.0)
B = (10, 4, 1, 0, 0, 1, 4, 9, 1, 2, 2, 1, 3, 1, 2, -5.0)
ZERO = (0,) * 15 + (0.0,)


def accepted(pid, team, counts, gid='0022400001', participated=True):
    return dict(game_id=gid, date='2024-10-22', season='2024-25', season_type='regular', id_namespace='nba',
                player_id=pid, team_id=team, name=f'p{pid}', minutes=30. if participated else None,
                participated=participated, status='', points=counts[0], rebounds=counts[1], assists=counts[2],
                threes=counts[3], steals=counts[4], blocks=counts[5])


def team_box(team, home, players, tov_extra=1, gid='0022400001'):
    sums = {k: sum(p[i] for p in players) for i, k in enumerate(eb.COUNTS)}
    return dict(game_id=gid, date='2024-10-22', season='2024-25', team_id=team, name=f't{team}', matchup='x',
                home=home, **{k: sums[k] for k in eb.TEAM_BOX}, tov=sums['tov'] + tov_extra, minutes=48.,
                possessions=100, pace=99.)


def setup(b_counts=B, tov_extra=1):
    rows = [accepted(1, 10, A), accepted(2, 11, b_counts), accepted(3, 11, ZERO, participated=False)]
    candidates = {('0022400001', 1, 10): {A}, ('0022400001', 2, 11): {b_counts}, ('0022400001', 3, 11): {ZERO}}
    teams = {('0022400001', 10): team_box(10, True, [A], tov_extra),
             ('0022400001', 11): team_box(11, False, [b_counts, ZERO], tov_extra)}
    return rows, candidates, teams


def test_identities_and_minutes():
    row = dict(zip(eb.COUNTS, A))
    assert eb.identities(row)
    assert not eb.identities(row | dict(points=21))
    assert not eb.identities(row | dict(oreb=3))
    assert eb.minutes_mmss('33:18') == pytest.approx(33.3) and eb.minutes_mmss('') is None


def test_accepted_rows_are_extended_and_team_turnovers_separated():
    rows, games, bad, issues = eb.extend_accepted(*setup())
    assert not bad and not issues and len(rows) == 3
    assert rows[0]['fga'] == 15 and rows[0]['count_source'] == 'accepted_base'
    home = games[0]['home']
    assert home['team_turnovers'] == 1 and home['players_tov'] == 2
    assert home['possessions_estimate'] == pytest.approx(15 - 2 + 2 + .44 * 5)


def test_conflicting_sources_quarantine_the_game():
    rows, candidates, teams = setup()
    candidates[('0022400001', 1, 10)] = {A, A[:7] + (16,) + A[8:]}
    out, games, bad, issues = eb.extend_accepted(rows, candidates, teams)
    assert bad == {'0022400001'} and not out and not games and issues['missing_or_conflicting_counts'] == 1


def test_team_box_mismatch_and_negative_team_turnovers_quarantine():
    rows, candidates, teams = setup()
    teams[('0022400001', 10)]['fga'] += 1
    assert eb.extend_accepted(rows, candidates, teams)[3]['team_count_reconciliation'] == 1
    rows, candidates, teams = setup(tov_extra=-1)
    assert eb.extend_accepted(rows, candidates, teams)[3]['team_turnovers_negative'] == 2


def raw(gid, pid, team, side, counts, city='T', name='One', year=2024, minutes='30:00'):
    r = dict(game_id=gid, person_id=pid, team_id=team, side=side, team_city=city, team_name=name, first_name='F',
             family_name=str(pid), minutes=minutes, comment='', file_year=year)
    r.update({eb.SNAKE[k]: v for k, v in zip(eb.COUNTS, counts)})
    return r


def api(home, away, hp, ap, start, status='Finished'):
    return dict(stage=3, season=2023, status=dict(long=status), date=dict(start=start),
                teams=dict(home=dict(name=home), visitors=dict(name=away)),
                scores=dict(home=dict(points=hp), visitors=dict(points=ap)))


def test_single_source_orders_play_in_first_and_matches_api(tmp_path):
    rows = [raw('0042300101', 1, 10, 'home', A, 'T', 'One'), raw('0042300101', 2, 11, 'away', B, 'T', 'Two'),
            raw('0052300101', 1, 10, 'away', B, 'T', 'One'), raw('0052300101', 2, 11, 'home', A, 'T', 'Two')]
    import json
    (tmp_path / 'games_2023.json').write_text(json.dumps(dict(response=[
        api('T One', 'T Two', 20, 10, '2024-04-21T00:30:00.000Z'),
        api('T Two', 'T One', 20, 10, '2024-04-17T00:00:00.000Z'),
        api('T One', 'T Two', None, None, '2024-05-01T00:00:00.000Z', status='Scheduled')])))
    out, games, issues = eb.single_source(rows, eb.api_postseason(tmp_path))
    assert not issues
    assert [(g['game_id'], g['date'], g['season_type']) for g in games] == [
        ('0052300101', '2024-04-16', 'play_in'), ('0042300101', '2024-04-20', 'playoffs')]
    assert all(r['count_source'] == 'sportsdataverse_only' and r['season'] == '2023-24' for r in out)
    assert games[0]['home']['team_turnovers'] is None and games[0]['home']['possessions'] is None


def test_single_source_rejects_api_disagreement(tmp_path):
    import json
    rows = [raw('0042300101', 1, 10, 'home', A, 'T', 'One'), raw('0042300101', 2, 11, 'away', B, 'T', 'Two')]
    (tmp_path / 'games_2023.json').write_text(json.dumps(dict(response=[api('T One', 'T Two', 21, 10, '2024-04-21T00:30:00Z')])))
    out, games, issues = eb.single_source(rows, eb.api_postseason(tmp_path))
    assert not out and issues == dict(api_mismatch=1)


def test_reference_check_rejects_any_changed_regular_row():
    rows, games, _, _ = eb.extend_accepted(*setup())
    reference = [{k: r[k] for k in accepted(1, 10, A)} for r in rows]
    assert eb.check_reference(rows, games, reference, [dict(game_id='0022400001')]) == []
    reference[0]['minutes'] = 31.
    with pytest.raises(ValueError, match='differs'):
        eb.check_reference(rows, games, reference, [dict(game_id='0022400001')])
