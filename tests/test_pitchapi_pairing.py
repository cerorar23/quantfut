import json
from datetime import date

from qf.ingest import pitchapi_history as h
from qf.ingest import pitchapi_pairing as p


def db_row(i, day, home, away, hg, ag, has_xg=False):
    return {'match_id': f'x{i}', 'league_id': 'L', 'date': day, 'home_team_id': home,
            'away_team_id': away, 'home_goals': hg, 'away_goals': ag, 'has_xg': has_xg}


def pitch_match(i, day, home, away, hg, ag):
    return {'id': f'm_{i}', 'date': day, 'status': 'finished', 'score_home': hg, 'score_away': ag,
            'home_team': {'id': f't_{home}'}, 'away_team': {'id': f't_{away}'}}


def stats(home, away):
    return json.dumps({'data': {'periods': [{'period': 'All', 'groups': [{'items': [
        {'key': 'expected_goals', 'home': home, 'away': away}]}]}]}}).encode()


def archive(tmp_path, matches, published):
    h.save(tmp_path, 'lists', 'L_2025', '/l', 200,
           json.dumps({'data': {'matches': matches}}).encode(), '2026-10-14T00:00:00Z')
    for m in matches:
        h.save(tmp_path, 'stats', m['id'], '/s', 200, stats(*published.get(m['id'], ('1.5', '0.5'))),
               '2026-10-14T01:00:00Z')
    return tmp_path


def season(n=4):
    """Equipos 1 y 2 juegan n partidos con marcadores distintos: identidad corroborada."""
    rows, matches = [], []
    for i in range(n):
        day = f'2025-0{i + 1}-10'
        rows.append(db_row(i, date.fromisoformat(day), 11, 22, i, 0, has_xg=(i == 0)))
        matches.append(pitch_match(i, day, 1, 2, i, 0))
    return rows, matches


def test_pairs_only_corroborated_matches_without_xg(tmp_path):
    rows, matches = season()
    plan = p.build_plan(archive(tmp_path, matches, {}), rows)
    assert plan['mapped_teams'] == 2
    assert sorted(x['match_id'] for x in plan['pairs']) == ['x1', 'x2', 'x3']
    assert plan['rejected'] == {'already_has_xg': 1}
    assert plan['pairs'][0]['received_at'] == '2026-10-14T01:00:00Z'


def test_two_matches_are_not_enough_to_trust_a_team(tmp_path):
    rows, matches = season(2)
    plan = p.build_plan(archive(tmp_path, matches, {}), rows)
    assert plan['pairs'] == [] and plan['rejected']['unmapped_team'] == 2


def test_swapped_sides_never_pair(tmp_path):
    rows, matches = season()
    rows[2]['home_team_id'], rows[2]['away_team_id'] = 22, 11
    plan = p.build_plan(archive(tmp_path, matches, {}), rows)
    assert 'x2' not in [x['match_id'] for x in plan['pairs']]


def test_unpublished_or_absurd_xg_is_not_imported(tmp_path):
    rows, matches = season()
    plan = p.build_plan(archive(tmp_path, matches, {'m_1': ('99', '1'), 'm_2': (None, '1')}), rows)
    assert [x['match_id'] for x in plan['pairs']] == ['x3']
    assert plan['rejected']['xg_out_of_range'] == 1 and plan['rejected']['xg_not_published'] == 1


def test_sql_updates_only_empty_finished_matches(tmp_path):
    rows, matches = season()
    sql = p.apply_sql(p.build_plan(archive(tmp_path, matches, {}), rows))
    assert "m.home_xg IS NULL AND m.away_xg IS NULL" in sql and "m.status='finished'" in sql
    assert "xg_source='pitchapi'" in sql and "'x3'" in sql and sql.startswith('BEGIN;')
