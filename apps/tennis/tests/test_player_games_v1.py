import pytest
from tennis_engine.scoring import Rules
from tennis_markets_v2.catalog import Contract, MarketEngine
from tennis_motor import board_with_model, recentre
import tennis_player_games_v1 as player_games


def test_both_players_games_add_up_to_the_games_total_distribution():
    engine = MarketEngine(.66, .60, Rules(3))
    over_a = player_games.probabilities(engine.joint, player_games.contract('A', 11.5))
    under_a = player_games.probabilities(engine.joint, player_games.contract('A', 11.5, 'under'))
    assert over_a['win'] == pytest.approx(under_a['loss']) and over_a['push'] == 0
    assert sum(player_games.probabilities(engine.joint, player_games.contract('B', 9)).values()) == pytest.approx(1)
    # Every point of the joint has gamesA + gamesB = total; the stronger server wins more games.
    total = engine.probabilities(Contract('games_total', 'over', 21.5))['win']
    assert 0 < total < 1
    assert over_a['win'] > player_games.probabilities(engine.joint, player_games.contract('B', 11.5))['win']
    tie = player_games.probabilities(engine.joint, player_games.contract('A', 12))
    assert tie['push'] > 0 and tie['win'] + tie['push'] + tie['loss'] == pytest.approx(1)


def test_contract_rejects_quarter_lines_unknown_players_and_set_scope():
    for bad in (dict(player='C', line=10.5), dict(player='A', line=10.25), dict(player='A', line=-1.5), dict(player='A', line=True)):
        with pytest.raises(ValueError):
            player_games.contract(bad['player'], bad['line'])
    with pytest.raises(ValueError):
        player_games.validate(dict(player_games.contract('A', 10.5), set_number=1))


def test_outcome_counts_a_tiebreak_set_as_one_game_and_rejects_bad_scores():
    result = dict(status='completed', score_A_B='7-6(4) 3-6 6-4', best_of=3, completed_sets=3)
    assert player_games.outcome(player_games.contract('A', 15.5), result) == 'win'  # 7 + 3 + 6 = 16
    assert player_games.outcome(player_games.contract('B', 16), result) == 'push'  # 6 + 6 + 4 = 16
    assert player_games.outcome(player_games.contract('B', 16.5), result) == 'loss'
    assert player_games.outcome(player_games.contract('B', 16.5, 'under'), result) == 'win'
    assert player_games.outcome(player_games.contract('A', 10.5), dict(result, status='retired')) == 'outside_completed_contract'
    with pytest.raises(ValueError):
        player_games.outcome(player_games.contract('A', 10.5), dict(result, score_A_B='6-4 6-4', completed_sets=3))


def test_motor_prices_player_games_rows_with_the_recentred_joint():
    engine = recentre(.66, .62, Rules(3), .2, .70)
    board = dict(rows=[dict(contract=player_games.contract('A', 12.5), market=.55, books=2),
                       dict(contract=player_games.contract('B', 40.5), market=.5, books=1),  # unreachable line in best of 3
                       dict(contract=dict(kind='games_total', selection='over', line=21.5, set_number=None, score=None), market=.5, books=1)])
    out = board_with_model(engine, board)
    assert [r['contract']['kind'] for r in out['rows']] == ['player_games', 'games_total'] and out['impossible_for_format'] == 1
    p = player_games.probabilities(engine.joint, player_games.contract('A', 12.5))
    assert out['rows'][0]['model'] == pytest.approx(p['win'])


def test_offered_markets_grades_player_games_rows_beside_the_other_families():
    from tennis_intake_v1 import offered_markets
    row = lambda contract, model, market: dict(contract=contract, model=model, market=market, books=1)
    sealed = dict(rules=dict(best_of=3), forecast=dict(players=['Ana Paz', 'Eva Sol'], market_board=dict(event_id='t1', rows=[
        row(player_games.contract('A', 11.5), .7, .6), row(player_games.contract('A', 12), .5, .5),  # push: left out
        row(dict(kind='games_total', selection='over', line=21.5, set_number=None, score=None), .5, .5)])))
    result = dict(status='completed', score_A_B='6-4 6-3', completed_sets=2)
    report = offered_markets([(sealed, result)])
    assert report['player_games']['n'] == 1 and report['player_games']['model_accuracy'] == 1  # 12 games > 11.5
    assert report['games_total']['n'] == 1
