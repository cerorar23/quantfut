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


def test_market_board_maps_every_offered_line_to_engine_contracts(tmp_path):
    from tennis_odds_propline_v1 import market_board, consensus

    def o(name, side, price, point=None):
        return dict(name=name, side=side, price=price, point=point, player_id=None, book_updated_at=None, last_seen_at='2026-10-24T10:00:00Z')

    def m(key, outcomes, period=None, line_type='main'):
        return dict(key=key, period=period, team=None, line_type=line_type, outcomes=outcomes)
    e = event()
    e['bookmakers'] = [dict(key='pinnacle', markets=[
        m('h2h', [o('Ana Paz', 'home', -200), o('Eva Sol', 'away', 160)]),
        m('spreads', [o('Ana Paz', 'home', -110, -3.5), o('Eva Sol', 'away', -110, 3.5)]),
        m('totals', [o('Over', None, 100, 21.5), o('Under', None, -120, 21.5)]),
        m('totals', [o('Over', None, -110, 9.5), o('Under', None, -110, 9.5)], period='s1'),
        m('h2h', [o('Ana Paz', 'home', -150), o('Eva Sol', 'away', 120)], period='s1'),
        m('set_spread', [o('Ana Paz', 'home', 150, -1.5), o('Eva Sol', 'away', -180, 1.5)]),
        m('player_aces', [o('Over', None, -110, 5.5)]),
        m('totals', [o('Over', None, 130, 23.5)], line_type='alternate')])]  # one side only: no margin-free price
    archive(tmp_path, [e])
    board = market_board(tmp_path, 'Eva Sol', 'Ana Paz', (NOW + timedelta(minutes=20)).isoformat())
    rows = {(r['contract']['kind'], r['contract']['line'], r['contract']['set_number']): r for r in board['rows']}
    assert set(rows) == {('winner', None, None), ('games_handicap', 3.5, None), ('games_total', 21.5, None), ('set_games_total', 9.5, 1),
                         ('set_winner', None, 1), ('sets_handicap', 1.5, None)}  # oriented to player A = Eva Sol
    assert rows[('games_handicap', 3.5, None)]['market'] == pytest.approx(.5)
    assert rows[('winner', None, None)]['market'] == pytest.approx(1 - (2 / 3) / (2 / 3 + 1 / 2.6))
    assert board['event_id'] == 't1' and board['unsupported_quotes'] == 1
    assert market_board(tmp_path, 'Ana Paz', 'Nobody', NOW.isoformat()) is None
    tb, _ = consensus([dict(market='total_tiebreaks', period=None, name='Over', point=.5, bookmaker='x', price=2.0),
                       dict(market='total_tiebreaks', period=None, name='Under', point=.5, bookmaker='x', price=2.0),
                       dict(market='total_tiebreaks', period=None, name='Over', point=1.5, bookmaker='x', price=5.0)], 'A', 'B')
    assert [r['contract']['kind'] for r in tb] == ['tiebreak'] and tb[0]['contract']['selection'] == 'yes'
