"""Historical references may enter the close consumers only after validation."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    'oddspapi_import', Path(__file__).parents[1] / 'scripts/import_oddspapi_closes.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def sample():
    identity = dict(league_id='gb.premier_league', home_team_id=1, away_team_id=2,
                    home_goals=2, away_goals=1, kickoff_utc='2026-09-01T18:00:00Z')
    row = dict(match_id='m', identity=identity, bookmaker='pinnacle', close_verified=False,
               prices=dict(home=2.2, draw=3.4, away=3.5), cutoff_utc='2026-09-01T18:00:00Z',
               changed_at={s: '2026-09-01T17:59:00Z' for s in ('home', 'draw', 'away')},
               quality='recent', has_history_after_cutoff=True)
    return row, {**identity, 'status': 'finished'}


def test_recent_prestart_triple_can_be_a_reconstructed_close():
    row, match = sample()
    assert module.decision(row, match) == []


def test_delayed_source_start_is_not_loaded_as_database_close():
    row, match = sample()
    row['cutoff_utc'] = '2026-09-01T18:15:00Z'
    assert 'source_cutoff_after_database_kickoff' in module.decision(row, match)


def test_old_or_truncated_history_stays_reference_only():
    row, match = sample()
    row['changed_at']['home'] = '2026-09-01T16:00:00Z'
    row['quality'] = 'review'
    row['has_history_after_cutoff'] = False
    reasons = module.decision(row, match)
    assert 'quote_older_than_one_hour' in reasons
    assert 'source_quality_review' in reasons
    assert 'history_does_not_continue_after_cutoff' in reasons


@pytest.mark.parametrize('key,value', [('home_team_id', 9), ('league_id', 'eu.ucl'),
                                      ('home_goals', 3), ('kickoff_utc', '2026-09-01T19:00:00Z')])
def test_changed_identity_or_fixture_aborts_import(key, value):
    row, match = sample()
    match[key] = value
    with pytest.raises(ValueError):
        module.decision(row, match)


def test_live_price_and_wrong_bookmaker_cannot_pass():
    row, match = sample()
    row['changed_at']['home'] = row['cutoff_utc']
    with pytest.raises(ValueError, match='quote_not_before'):
        module.decision(row, match)
    row, match = sample()
    row['bookmaker'] = 'other'
    with pytest.raises(ValueError):
        module.decision(row, match)
