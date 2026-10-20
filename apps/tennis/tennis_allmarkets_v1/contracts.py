"""Predeclared contracts; complements do not become independent observations."""
from dataclasses import asdict
import math
import re
from tennis_engine.scoring import Rules
from tennis_engine.normalize import standard_score
from tennis_markets_v2.catalog import Contract


def contracts(best_of: int) -> list[dict]:
    """One orientation per line; exact final score is a single categorical task."""
    rules = Rules(best_of)
    rows = [Contract('winner', 'A'), Contract('tiebreak', 'yes')]
    lines = ([18.5, 20.5, 21.5, 22, 22.5, 23, 23.5, 24.5, 26.5]
             if best_of == 3 else [30.5, 32.5, 34.5, 36, 36.5, 38.5, 40.5, 42.5])
    for kind, selection, values in (
        ('games_total', 'over', lines),
        ('games_handicap', 'A', [-5.5, -3.5, -1.5, 0, 1.5, 3.5, 5.5]),
        ('sets_total', 'over', [2.5] if best_of == 3 else [3.5, 4.5]),
        ('sets_handicap', 'A', [-1.5, 1.5]),
    ):
        rows += [Contract(kind, selection, line) for line in values]
    for number in range(1, best_of + 1):
        rows.append(Contract('set_winner', 'A', set_number=number))
        rows += [Contract('set_games_total', 'over', line, number) for line in (8.5, 9.5, 10, 10.5, 12.5)]
        rows += [Contract('set_games_handicap', 'A', line, number) for line in (-2.5, -1.5, 0, 1.5, 2.5)]
    return [asdict(c.validate(rules)) for c in rows] + [dict(kind='correct_score', selection='vector')]


def score_labels(best_of: int) -> list[str]:
    need = best_of // 2 + 1
    return [f'{a}-{b}' for loser in range(need) for a, b in ((need, loser), (loser, need))]


def forecast_board(engine) -> list[dict]:
    rows = []
    for contract in contracts(engine.rules.best_of):
        if contract['kind'] == 'correct_score':
            probabilities = {}
            for label in score_labels(engine.rules.best_of):
                score = tuple(map(int, label.split('-')))
                probabilities[label] = engine.probabilities(Contract('correct_score', 'exact', score=score))['win']
        else:
            probabilities = engine.probabilities(Contract(**contract))
        validate_mass(probabilities)
        rows.append(dict(contract=contract, probabilities=probabilities))
    return rows


def validate_mass(values: dict) -> None:
    if not values or any(isinstance(p, bool) or not isinstance(p, (float, int)) or not math.isfinite(p) or not 0 <= p <= 1 for p in values.values()) or abs(sum(values.values()) - 1) > 1e-9:
        raise ValueError('Finite normalized probability vector required')


def outcome(contract: dict, result: dict) -> str:
    """Mathematical completed-match contract; no bookmaker or invented odds."""
    if result['status'] != 'completed':
        return 'outside_completed_contract'
    score = result['score_A_B']
    if not isinstance(score, str) or not all(re.fullmatch(r'\d+-\d+(?:\(\d+\))?', t) for t in score.split()):
        raise ValueError('Complete conventional set scores required')
    sets = [tuple(map(int, pair)) for pair in re.findall(r'(\d+)-(\d+)(?:\(\d+\))?', score)]
    reverse = ' '.join(f'{b}-{a}' for a, b in sets)
    if not sets or not (standard_score(score, result['best_of']) or standard_score(reverse, result['best_of'])) or len(sets) != result['completed_sets']:
        raise ValueError('Invalid completed match score')
    sa = sum(a > b for a, b in sets)
    sb = len(sets) - sa
    if contract['kind'] == 'correct_score':
        return f'{sa}-{sb}'
    c = Contract(**contract).validate(Rules(result['best_of']))
    if c.set_number:
        if c.set_number > len(sets):
            return 'push'  # Unplayed period, not a defeat.
        ga, gb = sets[c.set_number - 1]
    else:
        ga, gb = sum(a for a, b in sets), sum(b for a, b in sets)
    kind = c.kind
    if kind == 'winner': value = sa - sb
    elif kind == 'set_winner': value = ga - gb
    elif kind in ('games_total', 'set_games_total'): value = ga + gb - c.line
    elif kind in ('games_handicap', 'set_games_handicap'): value = ga - gb + c.line
    elif kind == 'sets_total': value = sa + sb - c.line
    elif kind == 'sets_handicap': value = sa - sb + c.line
    else: value = 1 if any({a, b} == {6, 7} for a, b in sets) else -1
    return 'push' if abs(value) < 1e-12 else 'win' if value > 0 else 'loss'
