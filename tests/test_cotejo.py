from datetime import datetime, timedelta, timezone

from qf.ingest.cotejo import compare, promote

NOW = datetime(2026, 10, 14, 12, 40, tzinfo=timezone.utc)
LEAGUES = {'l_X': 'xx.liga'}
MAPPING = {'t_A': 1, 't_B': 2}


def pitch(i, home='t_A', away='t_B', score=(2, 1), status='finished', when='2026-10-12T18:00:00Z', league='l_X'):
    return {'id': f'm_{i}', 'league': {'id': league}, 'status': status, 'time_utc': when,
            'score_home': score[0], 'score_away': score[1],
            'home_team': {'id': home, 'name': home}, 'away_team': {'id': away, 'name': away}}


def row(i='x1', status='finished', goals=(2, 1), kickoff=datetime(2026, 10, 12, 18, tzinfo=timezone.utc),
        home=1, away=2, xg=None):
    return {'match_id': i, 'league_id': 'xx.liga', 'kickoff_utc': kickoff, 'status': status,
            'home_team_id': home, 'away_team_id': away, 'home_goals': goals[0], 'away_goals': goals[1],
            'home_xg': xg, 'away_xg': xg}


def test_matching_result_is_a_pair_without_discrepancy():
    pairs, disc, votes, unmapped = compare([pitch(1)], [row()], MAPPING, LEAGUES, NOW)
    assert len(pairs) == 1 and disc == [] and votes == [] and unmapped == 0


def test_different_score_is_reported_never_fixed():
    _, disc, _, _ = compare([pitch(1, score=(3, 1))], [row()], MAPPING, LEAGUES, NOW)
    assert [d['kind'] for d in disc] == ['score'] and disc[0]['detail']['db'] == [2, 1]


def test_open_match_that_pitchapi_finished_is_pending():
    _, disc, _, _ = compare([pitch(1)], [row(status='scheduled', goals=(None, None))], MAPPING, LEAGUES, NOW)
    assert [d['kind'] for d in disc] == ['result_pending']


def test_recent_open_match_is_not_flagged_yet():
    soon = NOW - timedelta(hours=2)
    _, disc, _, _ = compare([pitch(1, when='2026-10-14T10:40:00Z')],
                              [row(status='scheduled', goals=(None, None), kickoff=soon)], MAPPING, LEAGUES, NOW)
    assert disc == []


def test_missing_match_between_known_clubs_is_reported():
    _, disc, _, _ = compare([pitch(1)], [], MAPPING, LEAGUES, NOW)
    assert [d['kind'] for d in disc] == ['missing_in_db']


def test_two_candidates_never_assert_anything():
    pairs, disc, _, _ = compare([pitch(1, score=(9, 9))], [row('a'), row('b')], MAPPING, LEAGUES, NOW)
    assert pairs == [] and disc == []


def test_unknown_team_only_votes_with_a_single_exact_candidate():
    _, disc, votes, unmapped = compare([pitch(1, home='t_NEW')], [row()], {'t_B': 2}, LEAGUES, NOW)
    assert unmapped == 1 and disc == [] and votes == [('t_NEW', 1, 'm_1'), ('t_B', 2, 'm_1')]
    _, _, votes, _ = compare([pitch(1, home='t_NEW')], [row('a'), row('b')], {'t_B': 2}, LEAGUES, NOW)
    assert votes == []


def test_other_leagues_and_unfinished_pitch_matches_are_ignored():
    pairs, disc, votes, _ = compare([pitch(1, league='l_OTHER'), pitch(2, status='upcoming', score=(None, None))],
                                      [row()], MAPPING, LEAGUES, NOW)
    assert (pairs, disc, votes) == ([], [], [])


def test_promote_needs_three_votes_dominance_and_a_free_club():
    rows = [('t_N', 7, 3), ('t_FEW', 8, 2), ('t_MIX', 9, 5), ('t_MIX', 10, 1), ('t_TAKEN', 11, 4)]
    assert promote(rows, owned_clubs={11}, mapped_teams=set()) == [('t_N', 7, 3)]
    assert promote([('t_A', 7, 5), ('t_B', 7, 5)], set(), set()) == []
    assert promote([('t_N', 7, 5)], set(), {'t_N'}) == []
