import pytest
from tennis_engine.scoring import Rules
from tennis_allmarkets_v1.contracts import forecast_board
from tennis_motor import publication_board, recentre


@pytest.mark.parametrize('best_of,extra', [(3, 2), (5, 3)])
def test_new_sides_are_appended_without_rewriting_research_contracts(best_of, extra):
    engine = recentre(.66, .62, Rules(best_of), .2, .70)
    original = forecast_board(engine)
    published = publication_board(engine)
    assert published[:len(original)] == original
    assert len(published) == len(original) + extra
    for added in published[len(original):]:
        contract = added['contract']
        first_side = 'over' if contract['kind'] == 'sets_total' else 'yes'
        first = next(r for r in original if r['contract'] == dict(contract, selection=first_side))
        p, q = first['probabilities'], added['probabilities']
        assert q['win'] == pytest.approx(p['loss'])
        assert q['loss'] == pytest.approx(p['win'])
        assert q['push'] == pytest.approx(p['push'])
        assert sum(q.values()) == pytest.approx(1)
