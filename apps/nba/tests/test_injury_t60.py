import gzip
import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from nba import injury_t60 as t

ET = ZoneInfo('America/New_York')


def et(year, month, day, hour, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=ET).astimezone(UTC)


def test_slot_is_the_latest_hourly_file_stamped_at_or_before_tipoff_minus_sixty():
    # 19:30 ET tip -> cutoff 18:30 -> the 06PM file (stamped 18:30)
    assert t.file_name(t.wanted_slot(et(2025, 12, 3, 19, 30))) == 'Injury-Report_2025-12-03_06PM.pdf'
    # 19:00 ET tip -> cutoff 18:00 -> the 05PM file (stamped 17:30)
    assert t.file_name(t.wanted_slot(et(2025, 12, 3, 19, 0))) == 'Injury-Report_2025-12-03_05PM.pdf'
    # noon ET tip -> cutoff 11:00 -> the 10AM file; AM/PM and 12-hour clock
    assert t.file_name(t.wanted_slot(et(2025, 12, 3, 12, 0))) == 'Injury-Report_2025-12-03_10AM.pdf'
    assert t.file_name(t.wanted_slot(et(2025, 12, 3, 13, 30), steps_back=1)) == 'Injury-Report_2025-12-03_11AM.pdf'
    assert t.file_name(t.wanted_slot(et(2025, 12, 3, 13, 0), steps_back=0)) == 'Injury-Report_2025-12-03_11AM.pdf'


def test_the_chosen_file_is_never_stamped_after_the_cutoff():
    for hour in range(12, 23):
        for minute in (0, 15, 30, 45):
            tip = et(2025, 12, 3, hour, minute)
            slot = t.wanted_slot(tip).replace(minute=30)
            assert slot.astimezone(UTC) <= tip - t.av.LEAD
            assert (tip - t.av.LEAD) - slot.astimezone(UTC) < __import__('datetime').timedelta(hours=1)


def games():
    return [dict(game_id=f'g{i}', date='2025-12-03', season='2025-26', home=dict(team_id=1, name='Boston Celtics'),
                 away=dict(team_id=2, name='Atlanta Hawks')) for i in range(3)]


def test_plan_groups_games_by_file_skips_held_files_and_unknown_tipoffs_and_walks_back_over_missing():
    tips = {'g0': et(2025, 12, 3, 19, 30), 'g1': et(2025, 12, 3, 19, 30)}
    assert t.plan(games(), tips) == [('Injury-Report_2025-12-03_06PM.pdf', 2)]
    assert t.plan(games(), tips, have={'Injury-Report_2025-12-03_06PM.pdf'}) == []
    assert t.plan(games(), tips, missing={'Injury-Report_2025-12-03_06PM.pdf'}) == [('Injury-Report_2025-12-03_05PM.pdf', 2)]
    assert t.plan(games(), tips, seasons=('2024-25',)) == []


class Bucket:
    """Answers 200 for known files and the bucket's 403 for the rest."""

    def __init__(self, files, control=True):
        self.files, self.calls, self.control = files, [], control

    def __call__(self, url):
        self.calls.append(url)
        if url == t.CONTROL:
            return (200, b'%PDF-control') if self.control else (403, b'denied')
        name = url.rsplit('/', 1)[1]
        return (200, b'%PDF-' + name.encode()) if name in self.files else (403, b'AccessDenied')


def test_fetch_stores_records_missing_and_resumes_without_repeating(tmp_path):
    bucket = Bucket({'a.pdf', 'c.pdf'})
    result = t.fetch(['a.pdf', 'b.pdf', 'c.pdf'], tmp_path, get=bucket, pause=0, sleep=lambda s: None)
    assert result == dict(requests=3, stored=2, missing=1)
    meta = json.loads((tmp_path / 'manifest.json').read_bytes())
    assert meta['missing'] == ['b.pdf'] and set(meta['files']) == {'a.pdf', 'c.pdf'} and (tmp_path / 'a.pdf').read_bytes().startswith(b'%PDF-')
    again = Bucket({'a.pdf', 'c.pdf'})
    assert t.fetch(['a.pdf', 'b.pdf', 'c.pdf'], tmp_path, get=again, sleep=lambda s: None)['requests'] == 0
    assert [u for u in again.calls if u != t.CONTROL] == []


def test_fetch_honours_the_request_cap(tmp_path):
    bucket = Bucket({f'{i}.pdf' for i in range(10)})
    assert t.fetch([f'{i}.pdf' for i in range(10)], tmp_path, get=bucket, cap=4, sleep=lambda s: None)['requests'] == 4


def test_fetch_stops_when_the_control_file_stops_answering(tmp_path):
    with pytest.raises(ValueError, match='control file'):
        t.fetch(['a.pdf'], tmp_path, get=Bucket({'a.pdf'}, control=False), sleep=lambda s: None)
    with pytest.raises(ValueError, match='previous run stopped'):
        t.fetch(['a.pdf'], tmp_path, get=Bucket({'a.pdf'}), sleep=lambda s: None)


def test_fetch_stops_on_an_unexpected_status(tmp_path):
    def odd(url):
        return (200, b'%PDF-x') if url == t.CONTROL else (429, b'')
    with pytest.raises(ValueError, match='HTTP 429'):
        t.fetch(['a.pdf'], tmp_path, get=odd, sleep=lambda s: None)


def test_fetch_refuses_to_overwrite_a_stored_file(tmp_path):
    (tmp_path / 'a.pdf').write_bytes(b'%PDF-old')
    with pytest.raises(ValueError, match='overwrite'):
        t.fetch(['a.pdf'], tmp_path, get=Bucket({'a.pdf'}), sleep=lambda s: None)


def parsed(rows, stamp='2025-12-03T23:30:00+00:00'):
    return dict(report_timestamp_utc=stamp, first_received_at_utc='2026-10-21T00:00:00+00:00', rows=rows)


def row(name='Tatum, Jayson', team='Boston Celtics', matchup='ATL@BOS', date='12/03/2025', status='Out'):
    return dict(matchup=matchup, game_date=date, team=team, player_name_raw=name, status_raw=status, reason_raw='Injury', report_submitted=True)


def test_join_adds_ids_resolves_exact_then_box_score_names_and_drops_unplaceable_rows():
    g = games()[:1]
    teams = t.team_ids(g)
    tips = {'g0': et(2025, 12, 3, 19, 30)}
    exact, by_key = {'Tatum, Jayson': '1628369'}, {t.name_key('Jaylen Brown'): '1627759'}
    report = parsed([row(), row('Brown, Jaylen'), row('Nobody, Ann'), row(matchup='ATL@LAL'), row(date='12/04/2025'), row(name='', team='Atlanta Hawks')])
    joined, counts = t.join_report(report, g, teams, tips, exact, by_key)
    assert counts == dict(rows=6, no_game=2, named=3, no_player=1)
    ids = [(r['player_name_raw'], r['nba_player_id'], r['nba_game_id'], r['nba_team_id']) for r in joined['rows']]
    assert ids[0] == ('Tatum, Jayson', 1628369, 'g0', 1) and ids[1][1] == 1627759 and ids[2][1] is None
    assert joined['rows'][0]['game_tipoff_utc'] == tips['g0'].isoformat()
    assert joined['rows'][3]['nba_player_id'] is None and joined['rows'][3]['nba_team_id'] == 2


def test_build_detects_a_changed_pdf_and_is_deterministic(tmp_path):
    g = games()[:1]
    raw = tmp_path / 'raw'
    bucket = Bucket({'Injury-Report_2025-12-03_06PM.pdf'})
    t.fetch(['Injury-Report_2025-12-03_06PM.pdf'], raw, get=bucket, sleep=lambda s: None)
    existing = tmp_path / 'existing.jsonl.gz'
    with gzip.open(existing, 'wt', encoding='utf8') as stream:
        stream.write(json.dumps(dict(report_timestamp_utc='2025-12-03T20:00:00+00:00', rows=[
            dict(player_name_raw='Tatum, Jayson', nba_player_id=1628369, nba_game_id='g0', game_tipoff_utc=None)])) + '\n')
    parse = lambda pdf, url, received: parsed([row()])
    first = t.build(raw, tmp_path / 'out1', g, [], tmp_path, existing, parse=parse)
    second = t.build(raw, tmp_path / 'out2', g, [], tmp_path, existing, parse=parse)
    assert first['reports'] == 1 and first['join']['named'] == 1 and first['reports_sha256'] == second['reports_sha256']
    (raw / 'Injury-Report_2025-12-03_06PM.pdf').write_bytes(b'%PDF-tampered')
    with pytest.raises(ValueError, match='changed'):
        t.build(raw, tmp_path / 'out3', g, [], tmp_path, existing, parse=parse)


def test_coverage_measures_how_close_the_latest_valid_report_is_to_the_cutoff():
    g = games()[:2]
    tips = {'g0': et(2025, 12, 3, 19, 30), 'g1': et(2025, 12, 3, 19, 30)}
    reports = [dict(report_timestamp_utc=et(2025, 12, 3, 13, 30).isoformat(), rows=[dict(nba_game_id='g0'), dict(nba_game_id='g1')]),
               dict(report_timestamp_utc=et(2025, 12, 3, 18, 30).isoformat(), rows=[dict(nba_game_id='g0')]),
               dict(report_timestamp_utc=et(2025, 12, 3, 18, 45).isoformat(), rows=[dict(nba_game_id='g1')])]  # after the cutoff: ignored
    out = t.coverage(g, tips, reports, seasons=('2025-26',))['2025-26']
    assert out['with_valid_report'] == 2 and out['share_within_1h'] == 0.5 and out['median_hours_before_cutoff'] == 5.0


def test_a_transport_failure_is_tried_once_more_then_ends_the_run_resumable(tmp_path):
    state = dict(n=0)

    def flaky(url):
        if url == t.CONTROL:
            return 200, b'%PDF-c'
        state['n'] += 1
        if state['n'] == 1:
            raise OSError('timeout')
        return 200, b'%PDF-ok'
    assert t.fetch(['a.pdf'], tmp_path, get=flaky, sleep=lambda s: None)['stored'] == 1

    def dead(url):
        if url == t.CONTROL:
            return 200, b'%PDF-c'
        raise OSError('timeout')
    with pytest.raises(OSError):
        t.fetch(['b.pdf'], tmp_path, get=dead, sleep=lambda s: None)
    assert json.loads((tmp_path / 'manifest.json').read_bytes())['stopped'] is None  # a later run may resume


def test_from_the_quarter_hour_scheme_the_slot_is_the_quarter_hour_at_or_before_the_cutoff():
    # 19:30 ET tip -> cutoff 18:30 -> exactly the 06_30PM file; 19:40 -> cutoff 18:40 -> still 06_30PM
    assert t.file_name(t.wanted_slot(et(2026, 1, 15, 19, 30))) == 'Injury-Report_2026-01-15_06_30PM.pdf'
    assert t.file_name(t.wanted_slot(et(2026, 1, 15, 19, 40))) == 'Injury-Report_2026-01-15_06_30PM.pdf'
    assert t.file_name(t.wanted_slot(et(2026, 1, 15, 19, 40), steps_back=2)) == 'Injury-Report_2026-01-15_06_00PM.pdf'
    assert t.file_name(t.wanted_slot(et(2026, 1, 15, 12, 5))) == 'Injury-Report_2026-01-15_11_00AM.pdf'
    # the day before the switch is still hourly
    assert t.file_name(t.wanted_slot(et(2025, 12, 21, 19, 30))) == 'Injury-Report_2025-12-21_06PM.pdf'
    assert t.file_name(t.wanted_slot(et(2025, 12, 22, 19, 30))) == 'Injury-Report_2025-12-22_06_30PM.pdf'
    for minute in range(0, 60, 5):
        tip = et(2026, 1, 15, 20, minute)
        slot = t.wanted_slot(tip)
        assert slot.astimezone(UTC) <= tip - t.av.LEAD and (tip - t.av.LEAD) - slot.astimezone(UTC) < __import__('datetime').timedelta(minutes=15)
