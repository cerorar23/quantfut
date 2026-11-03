"""Respaldo football-data.org: lógica pura (sin base de datos ni red)."""
from datetime import datetime, timedelta, timezone

from qf.ingest import fdorg_respaldo as f
from qf.ingest.cotejo import compare

NOW = datetime(2026, 10, 31, 13, 10, tzinfo=timezone.utc)
LEAGUES = {'PL': 'gb.premier_league'}
MAPPING = {'57': 1, '1076': 2}


def fd(i=1, status='FINISHED', score=(3, 0), duration='REGULAR', when='2026-10-30T19:00:00Z',
       home=57, away=1076, code='PL'):
    return {'id': i, 'utcDate': when, 'status': status, 'competition': {'code': code},
            'homeTeam': {'id': home, 'name': 'Arsenal FC'}, 'awayTeam': {'id': away, 'name': 'Coventry City FC'},
            'score': {'winner': 'HOME_TEAM', 'duration': duration,
                      'fullTime': {'home': score[0], 'away': score[1]}, 'halfTime': {'home': 2, 'away': 0}}}


def row(i='x1', status='finished', goals=(3, 0), kickoff=datetime(2026, 10, 30, 19, tzinfo=timezone.utc),
        home=1, away=2):
    return {'match_id': i, 'league_id': 'gb.premier_league', 'kickoff_utc': kickoff, 'status': status,
            'home_team_id': home, 'away_team_id': away, 'home_goals': goals[0], 'away_goals': goals[1]}


def test_adapter_maps_a_finished_match():
    c = f.to_common(fd())
    assert c['status'] == 'finished' and (c['score_home'], c['score_away']) == (3, 0)
    assert c['id'] == '1' and c['league']['id'] == 'PL' and c['home_team']['id'] == '57'


def test_adapter_skips_extra_time_and_penalties():
    assert f.to_common(fd(duration='EXTRA_TIME')) is None
    assert f.to_common(fd(duration='PENALTY_SHOOTOUT')) is None


def test_adapter_skips_postponed_live_and_scoreless_finished():
    for status in ('POSTPONED', 'IN_PLAY', 'PAUSED', 'SUSPENDED', 'CANCELLED', 'AWARDED'):
        assert f.to_common(fd(status=status)) is None
    broken = fd()
    broken['score']['fullTime'] = {'home': None, 'away': None}
    assert f.to_common(broken) is None


def test_adapter_marks_timed_as_scheduled_without_score():
    c = f.to_common(fd(status='TIMED', score=(None, None), when='2026-11-02T15:00:00Z'))
    assert c['status'] == 'scheduled' and c['score_home'] is None


def test_matching_result_has_no_discrepancy():
    _, disc, _, _ = compare([f.to_common(fd())], [row()], MAPPING, LEAGUES, NOW)
    assert disc == []


def test_score_difference_is_reported():
    _, disc, _, _ = compare([f.to_common(fd(score=(2, 0)))], [row()], MAPPING, LEAGUES, NOW)
    assert [d['kind'] for d in disc] == ['score']


def test_pending_needs_six_hours_not_four():
    ko = NOW - timedelta(hours=5)
    pending = row(status='scheduled', goals=(None, None), kickoff=ko)
    _, disc, _, _ = compare([f.to_common(fd(when=ko.isoformat().replace('+00:00', 'Z')))], [pending],
                            MAPPING, LEAGUES, NOW)
    assert [d['kind'] for d in disc] == ['result_pending']          # compare() ya avisa a las 4 h
    assert f.apply_pending_grace(disc, [pending], NOW) == []        # pero aquí se esperan 6 h
    old = row(status='scheduled', goals=(None, None), kickoff=NOW - timedelta(hours=7))
    disc2 = [{'kind': 'result_pending', 'match_id': 'x1'}]
    assert f.apply_pending_grace(disc2, [old], NOW) == disc2


def test_calendar_reports_a_missing_fixture_between_known_clubs():
    sched = f.to_common(fd(status='TIMED', score=(None, None), when='2026-11-02T15:00:00Z'))
    out = f.compare_calendar([sched], [], MAPPING, LEAGUES, NOW)
    assert [d['kind'] for d in out] == ['missing_in_db']
    assert out[0]['detail']['status'] == 'scheduled' and f.alertable(out[0]) is True      # saque en ~50 h


def test_calendar_missing_fixture_alerts_only_inside_72_hours():
    near = f.to_common(fd(status='TIMED', score=(None, None), when='2026-11-02T13:00:00Z'))
    far = f.to_common(fd(i=2, status='TIMED', score=(None, None), when='2026-11-05T13:00:00Z'))
    near_d, far_d = (f.compare_calendar([m], [], MAPPING, LEAGUES, NOW)[0] for m in (near, far))
    assert f.alertable(near_d) and not f.alertable(far_d)


def test_calendar_detects_a_moved_kickoff():
    ko = datetime(2026, 11, 2, 15, tzinfo=timezone.utc)
    sched = f.to_common(fd(status='TIMED', score=(None, None), when='2026-11-02T17:30:00Z'))
    out = f.compare_calendar([sched], [row(status='scheduled', goals=(None, None), kickoff=ko)],
                             MAPPING, LEAGUES, NOW)
    assert [d['kind'] for d in out] == ['kickoff_shift'] and out[0]['detail']['minutes'] == 150


def test_calendar_ignores_small_shifts_unknown_clubs_and_ambiguity():
    ko = datetime(2026, 11, 2, 15, tzinfo=timezone.utc)
    sched = f.to_common(fd(status='TIMED', score=(None, None), when='2026-11-02T15:30:00Z'))
    sch = row(status='scheduled', goals=(None, None), kickoff=ko)
    assert f.compare_calendar([sched], [sch], MAPPING, LEAGUES, NOW) == []
    assert f.compare_calendar([sched], [], {'57': 1}, LEAGUES, NOW) == []
    twin = row('x2', status='scheduled', goals=(None, None), kickoff=ko)
    far = f.to_common(fd(status='TIMED', score=(None, None), when='2026-11-02T20:00:00Z'))
    assert f.compare_calendar([far], [sch, twin], MAPPING, LEAGUES, NOW) == []


def test_alert_lines_are_short_and_readable():
    d = {'kind': 'score', 'league_id': 'gb.premier_league',
         'detail': {'home': 'Arsenal', 'away': 'Coventry', 'date': '2026-10-30', 'db': [3, 0], 'pitchapi': [2, 0]}}
    assert f.alert_line(d).startswith('score gb.premier_league Arsenal-Coventry')
