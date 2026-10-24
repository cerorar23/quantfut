"""Artificial PropLine archive only: no credentials and no provider requests."""
import json
from datetime import datetime, timedelta, timezone
import pytest
from tennis_motor import live_market
from tennis_odds_propline_v1 import archive_module, latest_market

NOW = datetime(2026, 10, 24, 10, 7, tzinfo=timezone.utc)
PATH = '/v1/sports/tennis/odds'


def event(home='Ana Paz', away='Eva Sol', eid='t1', start='2026-10-24T14:00:00Z', prices=(-200, 160), **extra):
    def out(name, side, price):
        return dict(name=name, side=side, price=price, point=None, player_id=None, book_updated_at=None, last_seen_at='2026-10-24T10:00:00Z')
    return dict(id=eid, sport_key='tennis', commence_time=start, home_team=home, away_team=away, bookmakers=[
        dict(key='pinnacle', markets=[dict(key='h2h', period=None, team=None, line_type='main',
                                           outcomes=[out(home, 'home', prices[0]), out(away, 'away', prices[1])], **extra)])])


def archive(root, events, at=NOW):
    pl = archive_module()
    get = lambda path, params, key: (200, {'X-Daily-Remaining': '4000'}, json.dumps(events).encode())
    pl.Collector(root, 'not-a-key', get=get, clock=lambda: at).capture(PATH, {'markets': 'h2h'})


def test_newest_observation_gives_devigged_winner_in_either_orientation(tmp_path):
    archive(tmp_path, [event()])
    m = latest_market(tmp_path, 'Ana Paz', 'Eva Sol', (NOW + timedelta(minutes=30)).isoformat())
    fair = (2 / 3) / (2 / 3 + 1 / 2.6)
    assert m['probability_a'] == pytest.approx(fair) and m['bookmakers'] == 1 and m['provider'] == 'propline'
    assert m['received_at'] == NOW.isoformat() and m['event_id'] == 't1'
    flipped = latest_market(tmp_path, 'eva  SOL', 'Ana Paz', (NOW + timedelta(minutes=30)).isoformat())
    assert flipped['probability_a'] == pytest.approx(1 - fair)


def test_point_in_time_age_and_start_are_enforced(tmp_path):
    archive(tmp_path, [event(start='2026-10-24T10:05:00Z')])
    archive(tmp_path / 'b', [event()])
    assert latest_market(tmp_path, 'Ana Paz', 'Eva Sol', (NOW + timedelta(minutes=30)).isoformat()) is None  # already started
    assert latest_market(tmp_path / 'b', 'Ana Paz', 'Eva Sol', (NOW - timedelta(seconds=1)).isoformat()) is None  # received later
    assert latest_market(tmp_path / 'b', 'Ana Paz', 'Eva Sol', (NOW + timedelta(hours=2)).isoformat()) is None  # older than one cycle
    assert latest_market(tmp_path / 'c', 'Ana Paz', 'Eva Sol', NOW.isoformat()) is None  # no archive at all


def test_other_pairs_doubles_flagged_and_duplicate_listings_give_no_market(tmp_path):
    archive(tmp_path, [event(home='Ana Paz / Lia Mar', away='Eva Sol / Isa Rey'), event(home='Ana Paz', away='Isa Rey', eid='t2')])
    assert latest_market(tmp_path, 'Ana Paz', 'Eva Sol', NOW.isoformat()) is None
    archive(tmp_path / 'f', [event(suspended_at='2026-10-24T10:00:00Z')])
    assert latest_market(tmp_path / 'f', 'Ana Paz', 'Eva Sol', NOW.isoformat()) is None
    archive(tmp_path / 'd', [event(), event(eid='t9', prices=(-150, 120))])
    assert latest_market(tmp_path / 'd', 'Ana Paz', 'Eva Sol', NOW.isoformat()) is None


def test_motor_reads_only_the_configured_source(tmp_path):
    archive(tmp_path / 'propline', [event()])
    before = (NOW + timedelta(minutes=5)).isoformat()
    config = dict(odds_provider='propline', propline_root=str(tmp_path / 'propline'), live_odds_root=str(tmp_path / 'odds_api'))
    assert live_market(config, 'Ana Paz', 'Eva Sol', before)['provider'] == 'propline'
    empty = dict(config, propline_root=str(tmp_path / 'empty'))
    assert live_market(empty, 'Ana Paz', 'Eva Sol', before) is None  # The Odds API ledger is never a fallback
    assert live_market({}, 'Ana Paz', 'Eva Sol', before) is None
