"""Live player markets (points, rebounds, assists) over PropLine lines, play-in/playoff ids and player results."""
from datetime import UTC, datetime, timedelta
import json
from types import SimpleNamespace

import numpy as np
import pytest

from nba import injury_pdf
from nba import multimarket as m1
from nba import multimarket_live_dashboard as board
from nba import multimarket_v13_live as live
from nba import paper
from nba import prop_lines
from nba.audit import digest, write_json
from test_multimarket_v13_live import (AWAY, DAY, GID, HOME, PROTOCOL, SLUG, TIP, V12, box_html, fake_get, history_games, model,
                                       parsed_report, player_rows)

NOW = datetime(2026, 10, 21, 14, 29, tzinfo=UTC)
RECEIVED = '2026-10-21T14:07:30+00:00'


def two_sided(book, player, market, point, name='Player', **extra):
    outcomes = [dict(name=side, description=name, price=-110, point=point, player_id=f'nba:{player}', **extra)
                for side in ('Over', 'Under')]
    return dict(key=book, markets=[dict(key=market, period=None, team=None, line_type='main', outcomes=outcomes)])


def event(bookmakers, commence='2026-10-21T23:00:00Z'):
    return dict(id='e1', sport_key='basketball_nba', commence_time=commence, home_team='Bbb Club', away_team='Aaa Club',
                home_team_id=f'nba:{HOME}', away_team_id=f'nba:{AWAY}', live=False, bookmakers=bookmakers)


BOOKS = [
    two_sided('draftkings', 1, 'player_points', 17.5), two_sided('fanduel', 1, 'player_points', 17.5),
    two_sided('betmgm', 1, 'player_points', 18.5),
    two_sided('prizepicks', 1, 'player_points', 16.5),  # DFS site
    two_sided('pick6', 1, 'player_points', 16.5, dfs_odds_type='standard'),  # DFS not in the archive's own list
    two_sided('kalshi', 1, 'player_points', 16.5),  # exchange
    two_sided('draftkings', 1, 'player_rebounds', 7.5), two_sided('fanduel', 1, 'player_rebounds', 7.0),  # integer line
    two_sided('draftkings', 2, 'player_assists', 3.5), two_sided('fanduel', 2, 'player_assists', 3.5),
    two_sided('draftkings', 99, 'player_points', 9.5), two_sided('fanduel', 99, 'player_points', 9.5),  # no history
]


@pytest.fixture
def archive(monkeypatch):
    real = prop_lines.archive_module()
    state = dict(events=[event(BOOKS)])

    def newest(root, path, as_of, *, max_age_seconds):
        assert path == prop_lines.PATH and max_age_seconds == 3900
        return state['events'], dict(received_at=RECEIVED, slot='2026-10-21T14:00:00+00:00', sha256='a' * 64, component_receipts=[1, 2])
    monkeypatch.setattr(prop_lines, 'archive_module', lambda: SimpleNamespace(newest=newest, quotes=real.quotes))
    return state


def mapping():
    return live.parse_game(box_html(1).decode(), SLUG, '2026-10-21T14:00:00+00:00')


def test_consensus_line_is_the_mode_then_nearest_the_median():
    assert prop_lines.consensus([17.5, 17.5, 18.5]) == 17.5
    assert prop_lines.consensus([17.5, 18.5, 19.5, 19.5, 17.5, 30.5]) == 19.5  # tie 17.5/19.5, median 19.0: nearest wins
    assert prop_lines.consensus([17.5, 19.5]) == 17.5  # tie and equally near the median 18.5: the lower
    assert prop_lines.consensus([20.5, 21.5, 21.5, 20.5, 21.5]) == 21.5


def test_only_sportsbook_main_half_point_lines_with_two_books_count(archive):
    lines, summary = prop_lines.lines('archive', NOW, [mapping()])
    assert summary['state'] == 'archivo_aplicado' and summary['received_at_utc'] == RECEIVED and summary['events_matched'] == 1
    game = lines[GID]
    assert game[('player_points', 1)] == dict(line=17.5, books=3, book_lines=dict(betmgm=18.5, draftkings=17.5, fanduel=17.5))
    assert ('player_rebounds', 1) not in game  # one book left after dropping the integer line
    assert game[('player_assists', 2)]['line'] == 3.5 and ('player_points', 99) in game


def test_lines_of_another_game_or_a_started_game_are_ignored(archive):
    archive['events'] = [event(BOOKS, commence='2026-10-22T23:00:00Z')]
    assert prop_lines.lines('archive', NOW, [mapping()])[0] == {}
    archive['events'] = [event(BOOKS, commence='2026-10-21T14:00:00Z')]  # started before the observation: in play
    assert prop_lines.lines('archive', NOW, [mapping()])[0] == {}
    assert prop_lines.lines(None, NOW, [mapping()]) == ({}, dict(state='sin_fuente'))


def test_missing_or_stale_archive_seals_team_markets_only(tmp_path, monkeypatch):
    monkeypatch.setattr(prop_lines, 'archive_module', lambda: SimpleNamespace(newest=lambda *a, **k: (None, None)))
    assert prop_lines.lines('archive', NOW, [mapping()]) == ({}, dict(state='sin_archivo_reciente'))


@pytest.fixture
def sealed(tmp_path, monkeypatch, archive):
    model_dir = tmp_path / 'model'
    model_dir.mkdir()
    write_json(model_dir / 'model.json', model())
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received))
    result = live.seal(model_dir, tmp_path / 'cohort', DAY, player_rows(), history_games(), PROTOCOL, V12, now=NOW, get=fake_get,
                       first_completed_day=DAY, props_root=tmp_path / 'archive')
    return tmp_path / 'cohort', result


def test_player_forecasts_use_the_line_history_and_report(sealed):
    folder, result = sealed
    bundle = json.loads((folder / 'bundle.json').read_bytes())
    players = [f for f in bundle['forecasts'] if f['market'].startswith('player_')]
    assert result['player_forecasts'] == 2 and len(bundle['forecasts']) == 6
    assert bundle['prop_lines']['state'] == 'archivo_aplicado' and bundle['games'][0]['player_lines'] == dict(
        forecast=2, insufficient_history=1)
    points, = [f for f in players if f['market'] == 'player_points']
    assert (points['player_id'], points['line'], points['books'], points['player']) == (1, 17.5, 3, 'Jaren Jackson Jr.')
    assert points['report_status'] == 'Questionable' and points['probability_play'] == .5 and points['conditional_participation']
    assert points['sealed_at_utc'] == bundle['created_at_utc'] and points['last_feature_date'] < DAY
    # identity recalibration: the sealed probability is the raw model probability at the market line
    hist = m1.eligible(live.player_history(player_rows())['1'], DAY, dict(V12, empirical_weight=live.PLAYER_WEIGHT))
    raw = m1.player_over(m1.player_parameters(hist, 'points', dict(V12, empirical_weight=.25)), 17.5, dict(V12, empirical_weight=.25))
    assert points['probability_over'] == pytest.approx(raw) and points['probability_under'] == pytest.approx(1 - raw)
    assists, = [f for f in players if f['market'] == 'player_assists']
    assert assists['report_status'] == 'no_listado' and assists['probability_play'] is None


def test_report_status_moves_the_probability_through_the_fitted_weights(tmp_path, monkeypatch, archive):
    base = model()
    base['player_fit'] = {m: dict(weights=[1., 0., -1., 0., 0.]) for m in live.PLAYER_MARKETS}  # Questionable lowers the over
    model_dir = tmp_path / 'model'
    model_dir.mkdir()
    write_json(model_dir / 'model.json', base)
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received))
    live.seal(model_dir, tmp_path / 'c', DAY, player_rows(), history_games(), PROTOCOL, V12, now=NOW, get=fake_get,
              first_completed_day=DAY, props_root='archive')
    points, = [f for f in json.loads((tmp_path / 'c' / 'bundle.json').read_bytes())['forecasts'] if f['market'] == 'player_points']
    hist = m1.eligible(live.player_history(player_rows())['1'], DAY, dict(V12, empirical_weight=.25))
    raw = m1.player_over(m1.player_parameters(hist, 'points', dict(V12, empirical_weight=.25)), 17.5, dict(V12, empirical_weight=.25))
    assert points['probability_over'] == pytest.approx(1 / (1 + np.exp(-(np.log(raw / (1 - raw)) - 1))))


def test_out_players_and_players_of_other_teams_are_not_forecast(tmp_path, monkeypatch, archive):
    model_dir = tmp_path / 'model'
    model_dir.mkdir()
    write_json(model_dir / 'model.json', model())
    monkeypatch.setattr(injury_pdf, 'extract_report', lambda path, url, received: parsed_report(received, status='Out'))
    rows = [dict(r, team_id=99) if r['player_id'] == 2 else r for r in player_rows()]
    live.seal(model_dir, tmp_path / 'c', DAY, rows, history_games(), PROTOCOL, V12, now=NOW, get=fake_get,
              first_completed_day=DAY, props_root='archive')
    bundle = json.loads((tmp_path / 'c' / 'bundle.json').read_bytes())
    assert [f for f in bundle['forecasts'] if f['market'].startswith('player_')] == []
    assert bundle['games'][0]['player_lines'] == dict(listed_out=1, last_team_not_in_game=1, insufficient_history=1)


def test_a_model_without_player_fit_refuses_player_markets(tmp_path, archive):
    base = model()
    del base['player_fit']
    (tmp_path / 'model').mkdir()
    write_json(tmp_path / 'model' / 'model.json', base)
    with pytest.raises(ValueError, match='player_fit'):
        live.seal(tmp_path / 'model', tmp_path / 'c', DAY, player_rows(), history_games(), PROTOCOL, V12, now=NOW, get=fake_get,
                  first_completed_day=DAY, props_root='archive')


def test_player_results_are_scored_conditional_on_playing(sealed, monkeypatch):
    folder, _ = sealed
    now = TIP + timedelta(hours=4)
    body = json.loads(box_html(3).decode().split('application/json">')[1].split('</script>')[0])
    game = body['props']['pageProps']['game']
    game['homeTeam']['players'].append(dict(personId=1, firstName='Jaren', familyName='Jackson Jr.', comment='',
                                            statistics=dict(minutes='PT31M05.00S', points=21, reboundsTotal=6, assists=2)))
    game['homeTeam']['players'].append(dict(personId=2, firstName='Ana', familyName='Díaz', comment="DNP - Coach's Decision",
                                            statistics=dict(minutes='', points=0, reboundsTotal=0, assists=0)))
    html = ('<script id="__NEXT_DATA__" type="application/json">' + json.dumps(body) + '</script>').encode()

    def capture(game_id, destination, game_slug=None):
        destination.mkdir(parents=True)
        (destination / 'boxscore.html').write_bytes(html)
        write_json(destination / 'receipt.json', dict(
            url=f'https://www.nba.com/game/{game_slug}/box-score', game_id=game_id, http_status=200, error=None,
            raw_sha256=digest(destination / 'boxscore.html'), requested_at_utc=now.isoformat(),
            first_received_at_utc=now.isoformat(), raw_file='boxscore.html'))
        return destination / 'receipt.json'
    monkeypatch.setattr('nba.paper.capture_official_result', capture)
    assert live.capture_results(folder, now) == dict(stored=[GID], retry=[])
    data = board.LiveCohort(folder).data(now + timedelta(minutes=1))
    results = {r['market']: r for r in data['predictions'] if r['market'].startswith('player_')}
    assert results['player_points']['result'] == dict(status='evaluated', actual=21)
    assert results['player_points']['report_status'] == 'Questionable' and results['player_points']['books'] == 3
    assert results['player_assists']['result'] == dict(status='dnp', actual=None)
    assert data['scorecard']['player_points']['n'] == 1 and data['scorecard']['player_assists'] == dict(n=0)


def test_play_in_playoff_and_cup_final_games_are_recognised():
    for gid, kind in (('0052600001', 'play_in'), ('0042600101', 'playoffs'), ('0062600001', 'cup_final')):
        slug = f'aaa-vs-bbb-{gid}'
        page = box_html(1).replace(GID.encode(), gid.encode())
        assert live.parse_game(page.decode(), slug, '2026-10-21T14:00:00+00:00')['game_type'] == kind
        assert live.CARD.findall(f'<a href="/game/{slug}" data-content="AAA @ BBB, {DAY}">') == [(slug, gid, DAY)]
    assert live.CARD.findall(f'<a href="/game/aaa-vs-bbb-0012600001" data-content="AAA @ BBB, {DAY}">') == []  # preseason
    with pytest.raises(ValueError, match='game ID required'):
        paper.capture_official_result('0012600001', 'unused')


def test_recalibration_samples_cover_a_grid_of_thresholds_from_earlier_games_only():
    protocol = dict(V12, empirical_weight=live.PLAYER_WEIGHT)
    rows = player_rows()
    samples = live.player_training_rows(rows, protocol, '2025-01-01', '2026-08-01')
    first = [r for r in samples['player_points'] if r['date'] == min(s['date'] for s in samples['player_points'])]
    hist = m1.eligible(live.player_history([r for r in rows if r['date'] < first[0]['date']])[str(first[0]['unit'])],
                       first[0]['date'], protocol)
    base = np.floor(m1.player_parameters(hist, 'points', protocol)['baseline']) + .5
    mine = sorted(r['line'] for r in first if r['unit'] == first[0]['unit'])
    assert mine == [base + d for d in live.LINE_OFFSETS if base + d >= .5]
    assert all(s['date'] >= '2025-01-01' for m in samples.values() for s in m)
    actual = {(r['game_id'], r['player_id']): r for r in rows}
    assert all(s['y'] == int(actual[(s['game_id'], s['unit'])]['points'] > s['line']) for s in samples['player_points'])


def test_a_cached_game_with_old_player_rows_is_rejected(tmp_path):
    from test_live_completed_cache import Site
    live.completed('2026-10-20', '2026-10-20', Site(), tmp_path)
    path = tmp_path / 'games' / '0022600001.json'
    entry = json.loads(path.read_bytes())
    write_json(path, dict(entry, players=[{k: v for k, v in r.items() if k != 'assists'} for r in entry['players']]))
    with pytest.raises(ValueError, match='corrupt completed-game cache'):
        live.completed('2026-10-20', '2026-10-20', Site(), tmp_path)
