"""Games won by one player (PropLine `player_games_won`), priced from the same joint Markov distribution as every market.

Kept outside tennis_markets_v2 and tennis_allmarkets_v1 on purpose: the frozen multi-market protocol hashes every file of
those two packages, so a new family there would invalidate it. The contract is a plain dict with the usual keys plus
`player` ('A'/'B'); tennis_motor.board_with_model and tennis_intake_v1.offered_markets dispatch on KIND.

A tie-break set counts as one game for its winner (7-6), as in the joint distribution and in bookmaker grading.
Completed matches only: a retirement is not graded here (books void or grade it under their own rules).
"""
import math
import re
from tennis_engine.normalize import standard_score

KIND = 'player_games'


def contract(player, line, selection='over'):
    return validate(dict(kind=KIND, selection=selection, line=line, set_number=None, score=None, player=player))


def validate(c):
    line = c.get('line')
    if c.get('kind') != KIND or c.get('player') not in ('A', 'B') or c.get('selection') not in ('over', 'under'):
        raise ValueError('Invalid player games contract')
    if isinstance(line, bool) or not isinstance(line, (int, float)) or not math.isfinite(line) or line < 0 or abs(line * 2 - round(line * 2)) > 1e-10:
        raise ValueError('Integer and half lines required; quarter contracts not supported')
    if c.get('set_number') is not None or c.get('score') is not None:
        raise ValueError('Player games is a full-match contract')
    return c


def _value(c, ga, gb):
    games = ga if c['player'] == 'A' else gb
    return (games - c['line']) * (1 if c['selection'] == 'over' else -1)


def probabilities(joint, c):
    """Win/push/loss from a joint keyed (setsA, setsB, gamesA, gamesB, tiebreaks, first_set_winner)."""
    validate(c)
    win = push = 0.
    for (_, _, ga, gb, *_), mass in joint.items():
        value = _value(c, ga, gb)
        win += mass * (value > 0)
        push += mass * (abs(value) < 1e-12)
    return dict(win=win, push=push, loss=max(0., 1 - win - push))


def outcome(c, result):
    """Same completed-match contract as tennis_allmarkets_v1.contracts.outcome, for the games of one player."""
    validate(c)
    if result['status'] != 'completed':
        return 'outside_completed_contract'
    score = result['score_A_B']
    if not isinstance(score, str) or not all(re.fullmatch(r'\d+-\d+(?:\(\d+\))?', t) for t in score.split()):
        raise ValueError('Complete conventional set scores required')
    sets = [tuple(map(int, pair)) for pair in re.findall(r'(\d+)-(\d+)(?:\(\d+\))?', score)]
    reverse = ' '.join(f'{b}-{a}' for a, b in sets)
    if not sets or not (standard_score(score, result['best_of']) or standard_score(reverse, result['best_of'])) or len(sets) != result['completed_sets']:
        raise ValueError('Invalid completed match score')
    value = _value(c, sum(a for a, b in sets), sum(b for a, b in sets))
    return 'push' if abs(value) < 1e-12 else 'win' if value > 0 else 'loss'
