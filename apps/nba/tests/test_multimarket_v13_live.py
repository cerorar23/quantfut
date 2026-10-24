from datetime import UTC, date, datetime, timedelta
import json
from pathlib import Path

import numpy as np
import pytest

from nba import availability as av
from nba import injury_pdf
from nba import multimarket_v12 as v12
from nba import multimarket_v13 as v13
from nba import multimarket_v13_live as live
from nba import multimarket_live_dashboard as board
from nba.audit import digest, write_json

ROOT = Path(__file__).parents[1]
V12 = json.loads((ROOT / 'multimarket_v12_protocol.json').read_bytes())
PROTOCOL = dict(json.loads((ROOT / 'multimarket_v13_live_protocol.json').read_bytes()), _path=str(ROOT / 'multimarket_v13_live_protocol.json'))
HOME, AWAY, DAY = 11, 12, '2026-10-21'
TIP = datetime(2026, 10, 21, 23, 0, tzinfo=UTC)
SLUG, GID = 'bbb-vs-aaa-0022600100', '0022600100'


def schedule(season, start, count, offset=0):
    first = date.fromisoformat(start)
    team = lambda tid, pts: dict(team_id=tid, points=pts, name=str(tid))
    return [dict(game_id=f'g{offset + i}', date=(first + timedelta(days=2 * i)).isoformat(), season=season,
                 home=team(HOME, 100 + i % 7), away=team(AWAY, 98 + i % 5)) for i in range(count)]


def history_games():
    return schedule('2024-25', '2024-10-20', 40) + schedule('2025-26', '2025-10-20', 40, 100)


def player_rows():
    rows = []
    for g in history_games():
        for pid, name, minutes, points in ((1, 'Jaren Jackson Jr.', 30., 18.), (2, 'Ana Díaz', 20., 8.)):
            rows.append(dict(game_id=g['game_id'], date=g['date'], player_id=pid, name=name, participated=True,
                             minutes=minutes, points=points, team_id=HOME))
    return rows


def cards(day=DAY):
    return f'<a href="/game/{SLUG}" data-track="click" data-content="AAA @ BBB, {day}">'.encode()


def box_html(status, home_points=110, away_points=104, tip='2026-10-21T23:00:00Z'):
    team = lambda tid, pts, city: dict(teamId=tid, teamCity=city, teamName='Club', teamTricode=city[:3].upper(), score=pts,
        statistics=dict(points=pts, reboundsTotal=0, assists=0), inactives=[],
        players=[dict(personId=tid, firstName='Ana', familyName=city, comment='', played='1',
                      statistics=dict(minutes='30:00', points=pts, reboundsTotal=0, assists=0))])
    game = dict(gameId=GID, gameStatus=status, gameTimeUTC=tip, homeTeamId=HOME, awayTeamId=AWAY,
                homeTeam=team(HOME, home_points, 'Bbb'), awayTeam=team(AWAY, away_points, 'Aaa'))
    game['homeTeam']['teamTricode'], game['awayTeam']['teamTricode'] = 'BBB', 'AAA'
    return ('<script id="__NEXT_DATA__" type="application/json">' + json.dumps(dict(props=dict(pageProps=dict(game=game)))) + '</script>').encode()


def fake_get(url):
    if 'games?date=' in url:
        return 200, cards(url.rsplit('=', 1)[1])
    if url.endswith('/box-score'):
        return 200, box_html(3)
    if '/game/' in url:
        return 200, box_html(1)
    if url.endswith('.pdf'):
        return 200, b'%PDF-1.4 fake'
    return 404, b''


def parsed_report(received, stamp='2026-10-21T14:15:00+00:00', status='Questionable', team='Bbb Club', name='Jackson Jr., Jaren'):
    row = dict(game_date='10/21/2026', game_clock_raw='07:00 (ET)', matchup='AAA@BBB', team=team, player_name_raw=name,
               status_raw=status, reason_raw='Injury', report_submitted=True)
    return dict(source_url='https://ak-static.cms.nba.com/referee/injury/x.pdf', pdf_file='x.pdf', pdf_sha256='0' * 64,
                report_timestamp_utc=stamp, first_received_at_utc=received, rows=[row], named_players=1)


def model():
    games, table = history_games(), dict.fromkeys(av.STATUSES, .5)
    train = [dict(r) for r in v12.team_games(games, V12)]
    v13.attach(train, {}, table)
    return dict(version=live.VERSION, train_seasons=['2024-25', '2025-26'], fit=live.fit_team(train), play_probability=table,
                inputs=dict(live_module_sha256=digest(live.__file__)))


def test_fit_and_predict_match_the_frozen_v13_function():
    rows = [dict(r) for r in v12.team_games(history_games(), V12)]
    table = dict(av.STATUSES and {s: .4 for s in av.STATUSES})
    entries = {rows[i]['game_id']: {HOME: [('1', 'Out', 30., 18.)], AWAY: [('2', 'Questionable', 20., 8.)]} for i in range(0, len(rows), 3)}
    v13.attach(rows, entries, table)
    train, test = rows[:-10], rows[-10:]
    old, _ = v13.team_predictions(train, test)
    new = live.predict_team(test, live.fit_team(train))
    for a, b in zip(old, new):
        assert a['winner'] == pytest.approx(b['winner'])
        assert a['team_points_home'] == pytest.approx(b['home']['p'])
        assert a['team_points_away'] == pytest.approx(b['away']['p'])
        assert a['game_total'] == pytest.approx(b['total']['p'])


def test_trailing_value_matches_the_retrospective_construction():
    players, games = player_rows(), history_games()
    ids, history = live.history_index(players)
    day = '2026-01-01'
    mean_minutes, mean_points = live.trailing_value(history['1'], day)
    # same rule as availability.trailing_entries: last 20 earlier games, within 370 days, at least 5
    statuses = {('g179', '1'): ('Out', HOME)}
    probe = dict(games[-1], game_id='g179', date=day)
    entries = av.trailing_entries(players, [*games[:-1], probe], statuses, {'g179'})
    (player, status, minutes, points), = entries['g179'][HOME]
    assert (minutes, points) == pytest.approx((mean_minutes, mean_points))
    assert live.trailing_value(history['1'], '2024-10-21') is None  # fewer than five earlier games
    assert ids['jaren jackson jr'] == '1'


def test_report_names_walk_back_in_fifteen_minute_slots():
    names = list(live.report_names(DAY, datetime(2026, 10, 21, 14, 29, tzinfo=UTC)))
    assert names[0] == 'Injury-Report_2026-10-21_10_15AM.pdf'
    assert names[1] == 'Injury-Report_2026-10-21_10_00AM.pdf'
    assert names[-1] == 'Injury-Report_2026-10-21_12_00AM.pdf'


def test_schedule_only_future_games_of_that_date():
    now = datetime(2026, 10, 21, 14, 0, tzinfo=UTC)
    (m,) = live.upcoming(DAY, now, fake_get)
    assert (m['nba_game_id'], m['et_date'], m['tipoff_utc']) == (GID, DAY, TIP.isoformat())
    assert live.upcoming(DAY, TIP + timedelta(minutes=1), fake_get) == []
    assert live.day_cards('2026-10-22', fake_get) == [(SLUG, GID)]


def mapping():
    return live.parse_game(box_html(1).decode(), SLUG, '2026-10-21T14:00:00+00:00')


def test_report_must_be_received_and_dated_sixty_minutes_before_tipoff():
    m, (ids, history) = mapping(), live.history_index(player_rows())
    ok, summary = live.game_report_entries(parsed_report('2026-10-21T14:29:00+00:00'), m, ids, history)
    assert summary['state'] == 'reporte_aplicado' and summary['used'] == 1
    assert ok[HOME][0][1] == 'Questionable' and ok[AWAY] == []
    late_receipt = live.game_report_entries(parsed_report('2026-10-21T22:30:00+00:00'), m, ids, history)
    assert late_receipt[0] is None and late_receipt[1]['reason'] == 'report_too_close_to_tipoff'
    late_stamp = live.game_report_entries(parsed_report('2026-10-21T14:29:00+00:00', stamp='2026-10-21T22:15:00+00:00'), m, ids, history)
    assert late_stamp[1]['state'] == 'sin_reporte_valido'
    assert live.game_report_entries(None, m, ids, history)[1]['reason'] == 'no_report'


def test_unknown_players_and_other_games_carry_no_information():
    m, (ids, history) = mapping(), live.history_index(player_rows())
    report = parsed_report('2026-10-21T14:29:00+00:00', name='Nobody, Rookie')
    entries, summary = live.game_report_entries(report, m, ids, history)
    assert summary['unknown_player'] == 1 and entries[HOME] == []
    report['rows'][0]['matchup'] = 'CCC@DDD'
    assert live.game_report_entries(report, m, ids, history)[1]['reason'] == 'game_not_in_report'


def test_placeholder_results_never_leak_into_features():
    m = mapping()
    base = live.feature_rows(history_games(), [], [m], V12)[0]
    # an unrelated earlier result changes nothing about the same-day row except through ratings; same-day outcome is irrelevant
    again = live.feature_rows(history_games(), [], [m], V12)[0]
    assert base == again and base['b2b_home'] == 0
    yesterday = dict(game_id='g900', date='2026-10-20', season=live.SEASON, home=dict(team_id=HOME, points=100, name='x'),
                     away=dict(team_id=AWAY, points=90, name='y'))
    assert live.feature_rows(history_games(), [yesterday], [m], V12)[0]['b2b_home'] == 1
    with pytest.raises(ValueError):
        live.feature_rows(history_games(), [dict(yesterday, date=DAY)], [m], V12)


@pytest.fixture
def cohort(tmp_path, monkeypatch):
    model_dir = tmp_path / 'model'
    model_dir.mkdir()
    write_json(model_dir / 'model.json', model())
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received))
    now = datetime(2026, 10, 21, 14, 29, tzinfo=UTC)
    result = live.seal(model_dir, tmp_path / 'cohort', DAY, player_rows(), history_games(), PROTOCOL, V12, now=now, get=fake_get,
                       first_completed_day=DAY)
    return tmp_path / 'cohort', result


def test_seal_writes_a_verifiable_cohort_before_tipoff(cohort):
    folder, result = cohort
    assert result['forecasts'] == 4 and result['availability'] == {GID: 'reporte_aplicado'}
    data = board.LiveCohort(folder).data(datetime(2026, 10, 21, 15, 0, tzinfo=UTC))
    assert [r['market'] for r in data['predictions']] == ['winner', 'team_points', 'team_points', 'game_total']
    assert all(r['actionable'] is False and r['result']['status'] == 'pending' for r in data['predictions'])
    assert data['events'][0]['availability']['used'] == 1 and data['actionable'] is False


def test_seal_refuses_overwrite_and_late_cohorts(cohort, tmp_path):
    folder, _ = cohort
    with pytest.raises(ValueError):
        live.seal(tmp_path / 'model', folder, DAY, player_rows(), history_games(), PROTOCOL, V12, now=datetime(2026, 10, 21, 14, 30, tzinfo=UTC),
                  get=fake_get, first_completed_day=DAY)
    with pytest.raises(ValueError, match='no games left'):
        live.seal(tmp_path / 'model', tmp_path / 'late', DAY, player_rows(), history_games(), PROTOCOL, V12, now=TIP + timedelta(minutes=5),
                  get=fake_get, first_completed_day=DAY)


def test_changed_model_or_bundle_is_rejected(cohort):
    folder, _ = cohort
    (folder / 'model.json').write_text('{}')
    with pytest.raises(ValueError, match='model.json changed'):
        board.LiveCohort(folder)


def test_results_are_scored_from_the_official_receipt(cohort, monkeypatch):
    folder, _ = cohort
    now = TIP + timedelta(hours=4)

    def capture(game_id, destination, game_slug=None):
        destination.mkdir(parents=True)
        (destination / 'boxscore.html').write_bytes(box_html(3))
        write_json(destination / 'receipt.json', dict(
            url=f'https://www.nba.com/game/{game_slug}/box-score', game_id=game_id, http_status=200, error=None,
            raw_sha256=digest(destination / 'boxscore.html'), requested_at_utc=now.isoformat(),
            first_received_at_utc=now.isoformat(), raw_file='boxscore.html'))
        return destination / 'receipt.json'
    monkeypatch.setattr('nba.paper.capture_official_result', capture)
    assert live.capture_results(folder, TIP + timedelta(hours=1)) == dict(stored=[], retry=[])
    assert live.capture_results(folder, now) == dict(stored=[GID], retry=[])
    data = board.LiveCohort(folder).data(now + timedelta(minutes=1))
    assert data['events'][0]['status'] == 'evaluated' and data['events'][0]['final'] == dict(home=110, away=104)
    actual = {(r['market'], r['player_id']): r['result']['actual'] for r in data['predictions']}
    assert actual[('winner', 'winner')] == 1 and actual[('game_total', 'total')] == 214
    assert actual[('team_points', HOME)] == 110 and actual[('team_points', AWAY)] == 104
    assert data['scorecard']['winner']['n'] == 1 and data['scorecard']['team_points']['n'] == 2
    (folder / 'results' / GID / 'boxscore.html').write_bytes(box_html(3, 200, 1))
    assert board.LiveCohort(folder).data(now + timedelta(minutes=1))['events'][0]['status'] == 'validation_hold'


def test_non_final_capture_is_discarded_and_retried(cohort, monkeypatch):
    folder, _ = cohort

    def capture(game_id, destination, game_slug=None):
        destination.mkdir(parents=True)
        (destination / 'boxscore.html').write_bytes(box_html(2))
        write_json(destination / 'receipt.json', dict(url=f'https://www.nba.com/game/{game_slug}/box-score', game_id=game_id, http_status=200,
                   error=None, raw_sha256='x', requested_at_utc='x', first_received_at_utc='x', raw_file='boxscore.html'))
        return destination / 'receipt.json'
    monkeypatch.setattr('nba.paper.capture_official_result', capture)
    assert live.capture_results(folder, TIP + timedelta(hours=4)) == dict(stored=[], retry=[GID])
    assert not (folder / 'results' / GID).exists() and not (folder / 'results' / (GID + '.tmp')).exists()


def test_one_broken_cohort_never_hides_the_original_pilot(cohort, tmp_path):
    folder, _ = cohort
    broken = folder.parent / 'cohorts' / 'broken'
    broken.mkdir(parents=True)
    write_json(broken / 'bundle.seal.json', dict(sha256='0' * 64))
    write_json(broken / 'bundle.json', {})
    (folder.parent / 'cohorts' / folder.name).mkdir()
    class Stub:
        def data(self):
            return dict(events=[], predictions=[])
    both = board.CombinedDashboard(Stub(), folder.parent / 'cohorts')
    assert both.live(TIP)['state'] == 'validation_hold' and both.live(TIP)['cohorts'] == []
    only = board.CombinedDashboard(Stub(), None)
    assert only.data()['live_v13']['state'] == 'unavailable' and only.data()['events'] == []


def test_wrapped_reason_row_is_part_of_the_previous_record():
    rows = [['10/21/2026', '07:00 (ET)', 'AAA@BBB', 'Bbb Club', 'Jackson Jr., Jaren', 'Out', 'Injury/Illness - Knee;'],
            ['', '', '', '', '', '', 'Surgery']]
    (record,) = injury_pdf.records_from_cells([(1, rows)])
    assert record['reason_raw'] == 'Injury/Illness - Knee; Surgery' and record['status_raw'] == 'Out'


def test_a_game_is_forecast_once_across_cohorts(cohort, tmp_path):
    folder, _ = cohort
    assert live.sealed_games(folder.parent) == {GID}
    assert live.sealed_games(tmp_path / 'nothing') == set()
    with pytest.raises(ValueError, match='no games left'):
        live.seal(tmp_path / 'model', tmp_path / 'again', DAY, player_rows(), history_games(), PROTOCOL, V12,
                  now=datetime(2026, 10, 21, 14, 40, tzinfo=UTC), get=fake_get, first_completed_day=DAY, exclude=live.sealed_games(folder.parent))


def test_seal_and_receipts_are_stamped_when_they_happen(tmp_path, monkeypatch):
    model_dir = tmp_path / 'model'
    model_dir.mkdir()
    write_json(model_dir / 'model.json', model())
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received))
    ticks = iter(datetime(2026, 10, 21, 14, 30, tzinfo=UTC) + timedelta(minutes=i) for i in range(10))
    out = tmp_path / 'cohort'
    result = live.seal(model_dir, out, DAY, player_rows(), history_games(), PROTOCOL, V12, now=datetime(2026, 10, 21, 14, 29, tzinfo=UTC),
                       get=fake_get, first_completed_day=DAY, clock=lambda: next(ticks))
    bundle = json.loads((out / 'bundle.json').read_bytes())
    # game page, then report, then the seal itself: each stamped by the clock when it happens, not at the start of the run
    assert json.loads((out / 'schedule.json').read_bytes())['games'][0]['first_received_at_utc'] == '2026-10-21T14:30:00+00:00'
    assert bundle['report']['first_received_at_utc'] == '2026-10-21T14:31:00+00:00'
    assert bundle['created_at_utc'] == result['sealed_at_utc'] == '2026-10-21T14:32:00+00:00'
    assert {f['sealed_at_utc'] for f in bundle['forecasts']} == {bundle['created_at_utc']}


def test_lead_window_keeps_only_games_close_to_tipoff(cohort, tmp_path):
    with pytest.raises(ValueError, match='no games left'):
        live.seal(tmp_path / 'model', tmp_path / 'far', DAY, player_rows(), history_games(), PROTOCOL, V12,
                  now=datetime(2026, 10, 21, 14, 29, tzinfo=UTC), get=fake_get, first_completed_day=DAY,
                  lead=(timedelta(minutes=65), timedelta(minutes=90)))


def test_missing_report_slot_is_told_apart_from_a_blocked_source(tmp_path, monkeypatch):
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received))
    now = datetime(2026, 10, 21, 14, 29, tzinfo=UTC)  # 10:29 Eastern: newest slot 10:15

    def site(control):
        def get(url):
            if url == live.CONTROL:
                return control, b'%PDF-1.4' if control == 200 else b''
            if url.endswith('10_15AM.pdf'):
                return 403, b''
            return 200, b'%PDF-1.4 fake'
        return get
    assert live.capture_report(DAY, now, tmp_path / 'a', site(200))['pdf_file'] == 'Injury-Report_2026-10-21_10_00AM.pdf'
    with pytest.raises(ValueError, match='blocked'):
        live.capture_report(DAY, now, tmp_path / 'b', site(403))
    with pytest.raises(ValueError, match='HTTP 500'):
        live.capture_report(DAY, now, tmp_path / 'c', lambda url: (500, b''))


def producer_inputs(tmp_path, monkeypatch):
    model_dir, data = tmp_path / 'model', tmp_path / 'data'
    model_dir.mkdir(parents=True), data.mkdir()
    write_json(model_dir / 'model.json', model())
    import gzip
    with gzip.open(data / 'players.jsonl.gz', 'wt', encoding='utf8') as stream:
        stream.writelines(json.dumps(r) + '\n' for r in player_rows())
    (data / 'games.json').write_text(json.dumps(history_games()))
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received))
    return tmp_path / 'cohorts', model_dir, data, tmp_path / 'cache'


class Counting:
    def __init__(self, tip='2026-10-21T23:00:00Z'):
        self.tip, self.calls = tip, []

    def __call__(self, url):
        self.calls.append(url)
        if '/game/' in url and not url.endswith('/box-score'):
            return 200, box_html(1, tip=self.tip)
        return fake_get(url)


def test_producer_seals_each_game_shortly_before_its_own_tipoff(tmp_path, monkeypatch):
    from nba import multimarket_v13_live_producer as producer
    cohorts, model_dir, data, cache = producer_inputs(tmp_path, monkeypatch)
    site = Counting()
    early = TIP - timedelta(minutes=120)
    assert producer.run(early, cohorts, model_dir, data, DAY, cache, site)['sealed'] is None
    ready = TIP - timedelta(minutes=80)  # 17:40 Eastern
    status = producer.run(ready, cohorts, model_dir, data, DAY, cache, site)
    folder = cohorts / f'{DAY}_1740'
    assert status['sealed']['games'] == 1 and (folder / 'bundle.seal.json').exists()
    assert json.loads((folder / 'bundle.json').read_bytes())['version'] == live.VERSION
    site.calls.clear()
    again = producer.run(ready + timedelta(minutes=10), cohorts, model_dir, data, DAY, cache, site)
    assert again['sealed'] is None and again['results'] == {folder.name: dict(stored=[], retry=[])}
    assert site.calls == []  # schedule from the cache, the game already sealed: no request at all


def test_afternoon_and_early_evening_games_are_sealed_with_their_report(tmp_path, monkeypatch):
    from nba import multimarket_v13_live_producer as producer
    # 13:00 Eastern was never sealed by the old 17:35 run; 18:30 Eastern got a report received too late to count
    for tip in ('2026-10-21T17:00:00Z', '2026-10-21T22:30:00Z'):
        cohorts, model_dir, data, cache = producer_inputs(tmp_path / tip[11:13], monkeypatch)
        when = datetime.fromisoformat(tip.replace('Z', '+00:00')) - timedelta(minutes=75)
        status = producer.run(when, cohorts, model_dir, data, DAY, cache, Counting(tip))
        assert status['sealed']['games'] == 1 and status['sealed']['availability'] == {GID: 'reporte_aplicado'}


def test_schedule_is_read_again_after_its_lifetime(tmp_path):
    from nba import multimarket_v13_live_producer as producer
    site, start = Counting(), datetime(2026, 10, 21, 14, 0, tzinfo=UTC)
    assert producer.schedule(DAY, start, tmp_path, site) == {GID: TIP.isoformat()}
    producer.schedule(DAY, start + producer.SCHEDULE_TTL - timedelta(minutes=1), tmp_path, site)
    assert len(site.calls) == 2  # card + game page, once
    producer.schedule(DAY, start + producer.SCHEDULE_TTL, tmp_path, site)
    assert len(site.calls) == 4
