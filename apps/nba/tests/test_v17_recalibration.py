"""Live 1.7: complete current-season counts, consolidated training data, official repairs and role projection."""
import json

import numpy as np
import pytest

from nba import box_players
from nba import multimarket_v13_live as live
from nba import official_repairs
from nba import role_projection as rp
from nba import training_data as td
from nba.audit import write_json
from test_live14 import person
from test_multimarket_v13_live import AWAY, DAY, GID, HOME, V12


def test_current_rows_carry_every_official_count_of_the_consolidated_history():
    game = dict(homeTeam=dict(teamId=HOME, players=[person(1, fieldGoalsMade=4, freeThrowsMade=2, threePointersAttempted=5,
                                                           reboundsDefensive=4, foulsPersonal=3, plusMinusPoints=-7.0)]),
                awayTeam=dict(teamId=AWAY, players=[person(2)]))
    full, bare = live.player_rows(game, GID, DAY)
    assert (full['fgm'], full['ftm'], full['fg3a'], full['dreb'], full['pf'], full['plus_minus']) == (4, 2, 5, 4, 3, -7)
    assert set(full) == set(bare) == live.PLAYER_KEYS and bare['plus_minus'] is None and bare['fgm'] is None
    game['homeTeam']['players'][0]['statistics']['plusMinusPoints'] = 2.5
    with pytest.raises(ValueError, match='plus-minus'):
        live.player_rows(game, GID, DAY)


def test_a_cache_entry_without_the_full_counts_is_downloaded_again(tmp_path):
    v14 = dict(game_id=GID, date=DAY, season=live.SEASON, home={}, away={}, box_score_sha256='x',
               players=[{k: 0 for k in live.V14_PLAYER_KEYS} | dict(game_id=GID, date=DAY)])
    write_json(tmp_path / 'games' / f'{GID}.json', v14)
    assert live.cached_game(tmp_path, GID, DAY) is None
    current = dict(v14, players=[{k: 0 for k in live.PLAYER_KEYS} | dict(game_id=GID, date=DAY)])
    write_json(tmp_path / 'games' / f'{GID}.json', current)
    assert live.cached_game(tmp_path, GID, DAY) == current


def stub(pid, **stats):
    return dict(personId=pid, firstName='A', familyName='B', statistics=dict(dict(minutes='', points=0), **stats))


def test_an_empty_duplicate_never_hides_real_statistics_and_a_real_conflict_fails():
    real = stub(7, minutes='21:13', points=9)
    corrections = []
    assert box_players.unique_players([stub(7), real], corrections) == [real]
    assert box_players.unique_players([real, stub(7)]) == [real]
    assert corrections == [dict(player_id=7, correction='duplicate_empty_stub_removed')]
    with pytest.raises(ValueError, match='conflicting duplicated'):
        box_players.unique_players([real, stub(7, minutes='3:00', points=2)])


def test_zero_clock_with_a_recorded_attempt_is_participation_without_minutes():
    assert box_players.participated(dict(minutes='0:00', points=0, freeThrowsAttempted=2))
    assert not box_players.participated(dict(minutes='PT00M00.00S', points=0))
    assert box_players.participated(dict(minutes='PT00M12.00S', points=0))
    assert official_repairs.clock('11:60') == 12.0 and official_repairs.clock('') == 0.
    with pytest.raises(ValueError):
        official_repairs.clock('11:61')


def box(gid, date, home_points=100, away_points=90, season='2025-26'):
    return dict(game_id=gid, date=date, season=season, home=dict(team_id=HOME, points=home_points),
                away=dict(team_id=AWAY, points=away_points))


def lineup(gid, date, home_points=100, away_points=90, **extra):
    rows = []
    for team, points in ((HOME, home_points), (AWAY, away_points)):
        for i in range(5):
            rows.append(dict(game_id=gid, date=date, team_id=team, player_id=team * 10 + i, participated=True, minutes=48.,
                             points=points // 5 + (points % 5 if i == 0 else 0), rebounds=5, assists=2, threes=1, steals=1,
                             blocks=0, **extra))
    return rows


def test_merge_enriches_columns_rejects_conflicts_and_labels_the_season_type():
    gid = '0042500101'
    base = lineup(gid, '2026-04-20')
    richer = lineup(gid, '2026-04-20', fgm=3, dreb=4)
    players, games = td.merge([('first', [box(gid, '2026-04-20')], base), ('second', [box(gid, '2026-04-20')], richer)])
    assert games[0]['season_type'] == 'playoffs' and games[0]['training_sources'] == ['first', 'second']
    assert all(r['fgm'] == 3 and r['season_type'] == 'playoffs' for r in players)
    assert td.audit(players, games)['missing_columns']['fgm'] == 0
    other = [dict(r, points=r['points'] + 1) if r['player_id'] == HOME * 10 else r for r in richer]
    with pytest.raises(ValueError, match='conflicting player counts'):
        td.merge([('first', [box(gid, '2026-04-20')], base), ('second', [box(gid, '2026-04-20')], other)])
    with pytest.raises(ValueError, match='do not reconcile'):
        td.merge([('first', [box(gid, '2026-04-20', home_points=101)], base)])


def test_completed_current_games_join_only_before_the_cutoff():
    history = lineup('0022500001', '2026-04-01')
    games = [box('0022500001', '2026-04-01')]
    done = [dict(box('0022600001', '2026-10-21', season=live.SEASON), players=lineup('0022600001', '2026-10-21')),
            dict(box('0022600002', '2026-10-26', season=live.SEASON), players=lineup('0022600002', '2026-10-26'))]
    players, merged = td.append_completed(history, games, done, '2026-10-26')
    assert [g['game_id'] for g in merged] == ['0022500001', '0022600001']
    assert {r['season'] for r in players if r['game_id'] == '0022600001'} == {live.SEASON}


def test_new_team_minutes_update_the_role_and_add_uncertainty():
    protocol = dict(live.player_protocol(V12, dict(role_projection=True)), empirical_weight=.25)
    old = [dict(date=f'2026-03-{d:02d}', team_id=AWAY, minutes=15., points=6) for d in range(1, 21)]
    new = [dict(date=f'2026-10-{d:02d}', team_id=HOME, minutes=34., points=15) for d in (21, 23, 25)]
    plain = rp.parameters(old + new, 'points', dict(protocol, role_projection=False), HOME, '2026-27')
    moved = rp.parameters(old + new, 'points', protocol, HOME, '2026-27')
    assert 'role_projection' not in plain and plain['projected_minutes'] == np.mean([r['minutes'] for r in old + new])
    assert moved['current_role_games'] == 3 and moved['projected_minutes'] > plain['projected_minutes']
    assert moved['mean'] > plain['mean']
    assert moved['mean'] + moved['mean'] ** 2 / moved['n'] > plain['mean'] + plain['mean'] ** 2 / plain['n'] * (moved['mean'] / plain['mean']) ** 2
    assert moved['empirical_weight'] < protocol['empirical_weight']
    assert json.dumps(moved)  # the parameters are stored in plain JSON


def rotation_rows():
    """Complete five-man rotations for both teams, so the individual-strength fit sees every minute."""
    from test_multimarket_v13_live import history_games
    rows = []
    for g in history_games():
        for side, ids in (('home', (1, 2, 110, 111, 112)), ('away', (120, 121, 122, 123, 124))):
            points = g[side]['points']
            for i, pid in enumerate(ids):
                rows.append(dict(game_id=g['game_id'], date=g['date'], player_id=pid, team_id=g[side]['team_id'],
                                 name='Jaren Jackson Jr.' if pid == 1 else f'Player {pid}', participated=True, minutes=48.,
                                 points=points // 5 + (points % 5 if i == 0 else 0), rebounds=4 + i, assists=1 + i % 3))
    return rows


@pytest.fixture
def active_cohort(tmp_path, monkeypatch):
    from datetime import UTC, datetime
    from nba import current_rosters as cr
    from nba import injury_pdf
    from nba import roster_strength as rs
    from test_current_rosters import page
    from test_multimarket_v13_live import PROTOCOL, fake_get, history_games, model, parsed_report, player_rows
    for tid in (HOME, AWAY):
        monkeypatch.setitem(cr.TEAM_SLUGS, tid, 'test-club')

    def get(url):
        if '/team/' in url:
            tid = int(url.split('/')[4])
            return 200, page(tid, [1, 2, 110, 111, 112, 113] if tid == HOME else range(120, 126))
        return fake_get(url)
    from nba.audit import digest
    monkeypatch.setattr(injury_pdf, 'extract_report',
                        lambda path, url, received: dict(parsed_report(received), pdf_sha256=digest(path)))
    fitted = model()
    fitted['options'] = dict(official_rosters=True, recalculate_published=True, online_strength_update=False)
    fitted['inputs'].update(current_rosters_sha256=cr.code_digest(), roster_strength_sha256=rs.code_digest())
    fitted.update(training_cutoff=DAY, current_season_games=0, current_season_players=0,
                  roster_strength=dict(active=True, validation_status='historical_improvement_not_conclusive', weight=.25,
                                       ratings=rs.fit_ratings(history_games(), rotation_rows(), DAY, 25.)))
    model_dir = tmp_path / 'model'
    model_dir.mkdir()
    write_json(model_dir / 'model.json', fitted)
    folder = tmp_path / 'cohort'
    live.seal(model_dir, folder, DAY, rotation_rows(), history_games(), PROTOCOL, V12,
              now=datetime(2026, 10, 21, 14, 29, tzinfo=UTC), get=get, first_completed_day=DAY)
    return folder, model_dir, get


def test_a_publication_recalculated_after_tipoff_is_versioned_and_never_scored(active_cohort, tmp_path):
    from datetime import UTC, datetime
    from nba import revisions
    from nba.multimarket_live_dashboard import LiveCohort
    from test_multimarket_v13_live import history_games, player_rows
    folder, model_dir, get = active_cohort
    original = json.loads((folder / 'bundle.json').read_bytes())
    assert original['roster_strength']['affects_published_forecasts'] is True
    refit = json.loads((model_dir / 'model.json').read_bytes())
    refit['fit']['covariance'][0][0] *= 2  # a refit with different residual spread
    write_json(model_dir / 'model.json', refit)
    now = datetime(2026, 10, 23, 3, tzinfo=UTC)
    # The game's own result and a later game exist by now; neither may inform its recalculation.
    later = [dict(game_id=gid, date=day, season=live.SEASON, home=dict(team_id=HOME, points=150), away=dict(team_id=AWAY, points=80))
             for gid, day in ((GID, DAY), ('0022600200', '2026-10-22'))]
    later_rows = [dict(r, game_id=g['game_id'], date=g['date'], points=(150 if r['team_id'] == HOME else 80) // 5 + 0,
                       minutes=48.) for g in later for r in rotation_rows()[:10]]
    result = revisions.recalculate(folder, model_dir, rotation_rows() + later_rows, history_games() + later, V12,
                                   tmp_path / 'cache', None, now=now, get=get)
    assert result['forecasts'] == len(original['forecasts']) - result['withdrawn'] + result['added'] == 4
    assert json.loads((folder / 'bundle.json').read_bytes()) == original  # the sealed original is never rewritten
    revision = revisions.latest(folder, original, now)
    assert revision['recalculated_at_utc'] == now.isoformat() and revision['model_training_cutoff'] == DAY
    assert all(f['performance_eligible'] is False and f['calculation_kind'] == 'recalculated_after_tipoff'
               and f['original_sealed_at_utc'] == original['created_at_utc'] for f in revision['forecasts'])
    assert all(f['last_feature_date'] < DAY and f['information_before'] == DAY for f in revision['forecasts'])
    assert {revisions.key(f) for f in revision['forecasts']} == {revisions.key(f) for f in original['forecasts']}
    shown = LiveCohort(folder).data(now)
    assert shown['recalculated_at_utc'] == now.isoformat() and shown['active_strength'] is True
    assert all(r['performance_eligible'] is False for r in shown['predictions'])
    assert shown['scorecard'] == LiveCohort(folder).data(now)['scorecard']
    with pytest.raises(ValueError, match='information time'):
        revisions.latest(folder, original, datetime(2026, 10, 22, 2, tzinfo=UTC))
    path = next(folder.glob('updates/*/revision.json'))
    from nba.audit import digest
    sneaked = json.loads(path.read_bytes())
    sneaked['forecasts'].append(dict(sneaked['forecasts'][-1], player_id='other'))
    write_json(path, sneaked)
    write_json(path.parent / 'revision.seal.json', dict(sha256=digest(path), recalculated_at_utc=now.isoformat()))
    with pytest.raises(ValueError, match='added after tipoff'):
        revisions.latest(folder, original, now)
    changed = json.loads(path.read_bytes())
    changed['forecasts'][0]['performance_eligible'] = True
    write_json(path, changed)
    with pytest.raises(ValueError, match='revision changed'):
        revisions.latest(folder, original, now)


def test_refresh_only_touches_unstarted_publications_unless_asked_for_all(active_cohort, tmp_path):
    from datetime import UTC, datetime
    from nba import revisions
    from test_multimarket_v13_live import history_games, player_rows
    folder, model_dir, cohort_get = active_cohort
    get = lambda url: (200, b'') if 'games?date=' in url and not url.endswith(DAY) else cohort_get(url)
    refit = json.loads((model_dir / 'model.json').read_bytes())
    refit['fit']['covariance'][1][1] *= 2
    write_json(model_dir / 'model.json', refit)
    data = tmp_path / 'data'
    data.mkdir()
    td.write_players(data / 'players.jsonl.gz', rotation_rows())
    write_json(data / 'games.json', history_games())
    before = datetime(2026, 10, 21, 20, tzinfo=UTC)
    after = datetime(2026, 10, 22, 3, tzinfo=UTC)
    updated = revisions.refresh(folder.parent, model_dir, data, tmp_path / 'cache', None, now=before, get=get)
    assert [r['cohort'] for r in updated] == ['cohort']
    revision = revisions.latest(folder, json.loads((folder / 'bundle.json').read_bytes()), before)
    assert all(f['performance_eligible'] is True and f['calculation_kind'] == 'updated_before_tipoff' for f in revision['forecasts'])
    assert revisions.refresh(folder.parent, model_dir, data, tmp_path / 'cache', None, now=after, get=get) == []
    refit['fit']['covariance'][0][0] *= 2
    write_json(model_dir / 'model.json', refit)
    assert len(revisions.refresh(folder.parent, model_dir, data, tmp_path / 'cache', None, now=after, get=get,
                                 all_publications=True)) == 1


def test_an_identical_recalculation_is_discarded_and_accuracy_keeps_the_pregame_version(active_cohort, tmp_path):
    from datetime import UTC, datetime
    from nba import revisions
    from nba.multimarket_live_dashboard import LiveCohort, scorecard
    from test_multimarket_v13_live import history_games
    folder, model_dir, get = active_cohort
    original = json.loads((folder / 'bundle.json').read_bytes())
    pregame, late = datetime(2026, 10, 21, 20, tzinfo=UTC), datetime(2026, 10, 22, 3, tzinfo=UTC)
    refit = json.loads((model_dir / 'model.json').read_bytes())
    refit['fit']['covariance'][0][0] *= 2
    write_json(model_dir / 'model.json', refit)
    first = revisions.recalculate(folder, model_dir, rotation_rows(), history_games(), V12, tmp_path / 'cache', None,
                                  now=pregame, get=get, refresh_report=False)
    again = revisions.recalculate(folder, model_dir, rotation_rows(), history_games(), V12, tmp_path / 'cache', None,
                                  now=datetime(2026, 10, 21, 20, 30, tzinfo=UTC), get=get, refresh_report=False)
    assert first['revision'] and again == dict(cohort='cohort', revision=None, unchanged=True)
    assert len(list((folder / 'updates').iterdir())) == 1
    found = revisions.history(folder, original, late)
    assert [f['performance_eligible'] for f in revisions.scored(original, found)] == [True] * len(original['forecasts'])
    path = next((folder / 'updates').iterdir()) / 'revision.json'
    late_copy = dict(json.loads(path.read_bytes()), recalculated_at_utc=late.isoformat())
    late_copy['forecasts'] = [dict(f, performance_eligible=False, probability_over=.01, probability_under=.99)
                              for f in late_copy['forecasts']]
    assert {revisions.key(f) for f in revisions.scored(original, [*found, late_copy])} == {revisions.key(f) for f in found[0]['forecasts']}
    assert all(f['probability_over'] != .01 for f in revisions.scored(original, [*found, late_copy]))
    shown = LiveCohort(folder).data(late)
    assert shown['scorecard'] == scorecard([dict(r, performance_eligible=True) for r in shown['predictions']])


def test_report_names_with_a_separated_suffix_reach_the_official_player():
    from nba.context import name_key
    assert live.report_name('Udeh, Jr., Ernest') == name_key('Ernest Udeh Jr.')
    assert live.report_name('Jackson Jr., Jaren') == name_key('Jaren Jackson Jr.')
    assert live.report_name('Smith, Jalen') == name_key('Jalen Smith')
