"""Per-match overdispersed serve model, Elo-blended winner, one coherent joint distribution.

Constant serve-point probabilities across a match (the plain Markov assumption) make winner
probabilities overconfident and bias sets/games. Here the serve logit gap varies per match as a
Gaussian mixture around k * estimated gap (sigma = day-to-day noise); the centre is then moved so the
mixture winner probability equals a logit blend of the mixture and the frozen surface Elo. Every market
is read from that single mixture joint, so marginals stay mutually coherent.
"""
import numpy as np
from collections import defaultdict
from scipy.optimize import brentq
from scipy.special import expit, logit
from tennis_engine.scoring import Rules
from tennis_markets_v2.catalog import MarketEngine, Contract

GRID = np.round(np.linspace(-1.6, 1.6, 33), 3)


def weights(center, sigma):
    w = np.exp(-(GRID - center) ** 2 / (2 * sigma ** 2))
    return w / w.sum()


class NodeBank:
    """Plain Markov engines on a fixed grid of serve-gap offsets (computed once per match)."""
    def __init__(self, p, q, rules):
        self.rules = rules
        self.mid = (logit(p) + logit(q)) / 2
        self.gap = (logit(p) - logit(q)) / 2
        self.nodes = [MarketEngine(float(expit(self.mid + g)), float(expit(self.mid - g)), rules) for g in GRID]
        self.winner = np.array([n.probabilities(Contract('winner', 'A'))['win'] for n in self.nodes])


class MixtureEngine(MarketEngine):
    def __init__(self, bank, w):
        self.bank, self.w, self.rules, self.first_server, self.periods = bank, w, bank.rules, None, {}
        self.p = float(expit(bank.mid + bank.gap))
        self.q = float(expit(bank.mid - bank.gap))
        joint = defaultdict(float)
        for node, weight in zip(bank.nodes, w):
            if weight < 1e-12:
                continue
            for key, mass in node.joint.items():
                joint[key] += weight * mass
        self.joint = dict(joint)
        if abs(sum(self.joint.values()) - 1) > 1e-9:
            raise ArithmeticError('Mixture mass invalid')

    def period(self, number):
        if number in self.periods:
            return self.periods[number]
        result, unplayed = defaultdict(float), 0.
        for node, weight in zip(self.bank.nodes, self.w):
            if weight < 1e-12:
                continue
            dist, push = node.period(number)
            for key, mass in dist.items():
                result[key] += weight * mass
            unplayed += weight * push
        self.periods[number] = (dict(result), unplayed)
        return self.periods[number]


def build(p, q, elo, rules, params):
    """params: k, sigma, w_markov, w_elo (fitted on earlier seasons, then frozen)."""
    if not 0 < elo < 1:
        raise ValueError('Elo probability must be strictly inside (0,1)')
    bank = NodeBank(p, q, rules)
    k, s = params['k'], params['sigma']
    base = float(weights(k * bank.gap, s) @ bank.winner)
    target = float(expit(params['w_markov'] * logit(base) + params['w_elo'] * logit(elo)))
    f = lambda c: float(weights(c, s) @ bank.winner) - target
    lo, hi = -1.5, 1.5
    center = brentq(f, lo, hi) if f(lo) < 0 < f(hi) else (lo if f(lo) >= 0 else hi)
    engine = MixtureEngine(bank, weights(center, s))
    engine.diagnostics = dict(markov_winner=MarketEngine(p, q, rules).probabilities(Contract('winner', 'A'))['win'], mixture_winner=base,
                              elo_winner=float(elo), final_winner=float(weights(center, s) @ bank.winner), center=float(center))
    return engine
