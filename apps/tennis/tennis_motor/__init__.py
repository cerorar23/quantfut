"""Single entry point for the current tennis engine (v7). Older packages remain only as frozen evidence.

Pipeline: canonical data (identity bridge v3) -> serve/return model (MAP) -> per-match overdispersed Markov
-> winner target from Markov mixture + dynamic round-ordered Elo + rank/points/age + layoff/workload
-> centre re-solved so every market comes from one coherent joint distribution.
"""
import json
import math
import os
from pathlib import Path
import pandas as pd
from tennis_engine.model import ServeModel
from tennis_engine.scoring import Rules
from tennis_allmarkets_v1.contracts import forecast_board
from tennis_markets_v2.catalog import Contract
from tennis_core_v5.features import pair_features
from tennis_core_v7.prospective import build
from tennis_dynamic_v2 import replay
from tennis_core_v4 import MixtureEngine, NodeBank, weights
from scipy.optimize import brentq


def devig(odds_a, odds_b):
    if not (odds_a > 1 and odds_b > 1):
        raise ValueError('Decimal odds above 1.0 required for both players')
    return (1 / odds_a) / (1 / odds_a + 1 / odds_b)


def recentre(p_serve, q_serve, rules, sigma, target):
    """Mixture whose winner probability equals target; all markets stay coherent."""
    bank = NodeBank(p_serve, q_serve, rules)
    f = lambda c: float(weights(c, sigma) @ bank.winner) - target
    center = brentq(f, -1.5, 1.5) if f(-1.5) < 0 < f(1.5) else (-1.5 if f(-1.5) >= 0 else 1.5)
    return MixtureEngine(bank, weights(center, sigma))


def live_market(config, player_a, player_b, before):
    """The configured source only: `odds_provider: propline` reads the shared archive, never The Odds API as a fallback."""
    if config.get('odds_provider') == 'propline':
        from tennis_odds_propline_v1 import latest_market
        return latest_market(config['propline_root'], player_a, player_b, before)
    if config.get('live_odds_root'):
        from tennis_odds_live_v1 import latest_market
        return latest_market(config['live_odds_root'], player_a, player_b, before)
    return None

def dynamic_features(state, a, b, surface, day):
    """tennis_dynamic_v2.State.features with gaps clamped at zero (that module is frozen by the v7/v8 protocols).

    Round days are estimated from the draw, so a match already played can carry an estimated day after the forecast
    day; the frozen version then took log1p of a negative gap (crash below -1 day, negative layoff otherwise) and
    dropped that match from the 14-day workload.
    """
    def side(p):
        gap = max(0, (day - state.last[p]).days) if p in state.last else 365
        load = sum(1 for d in state.recent[p] if (day - d).days <= 14)
        return math.log1p(min(gap, 365)), load, math.log1p(state.n[p])
    sa, sb = side(a), side(b)
    return dict(dyn_p=state.prob(a, b, surface), d_layoff=sa[0] - sb[0], d_load14=sa[1] - sb[1], d_experience=sa[2] - sb[2])


def board_with_model(engine, board):
    """Model probability on exactly the contract each book quotes (push removed), next to the margin-free price."""
    rows, impossible = [], 0
    for row in board['rows']:
        try:
            p = engine.probabilities(Contract(**row['contract']).validate(engine.rules))
        except ValueError:
            impossible += 1
            continue
        if p['win'] <= 0 or p.get('loss', 0) <= 0:
            impossible += 1  # a line this format cannot reach (3.5 sets in best of 3): the listing disagrees with our rules
            continue
        rows.append(dict(row, model=p['win'] / max(1e-12, 1 - p.get('push', 0))))
    return dict(board, rows=rows, impossible_for_format=impossible)

# Runtime config lives outside the repo (the weekly refresh rewrites it); the tracked file is the template.
CONFIG = Path(os.environ.get('TENNIS_MOTOR_CONFIG') or Path(__file__).resolve().parents[1] / 'config' / 'motor.json')


class Motor:
    def __init__(self, config=CONFIG):
        self.config = json.loads(Path(config).read_text(encoding='utf-8'))
        self.params = json.loads(Path(self.config['params']).read_text(encoding='utf-8'))
        fallback = self.config.get('params_norank')
        self.params_norank = json.loads(Path(fallback).read_text(encoding='utf-8')) if fallback else None
        self.canonical = pd.read_parquet(self.config['canonical'])
        self.models, self.states = {}, {}

    def model(self, circuit):
        if circuit not in self.models:
            self.models[circuit] = ServeModel(Path(self.config['models_root']) / f'{circuit}_current', uncertainty=False)
        return self.models[circuit]

    def state(self, circuit):
        if circuit not in self.states:
            self.states[circuit] = replay(self.canonical, circuit, since='2005-01-01')[1]
        return self.states[circuit]

    def forecast(self, circuit, player_a, player_b, surface, date, best_of=3, deciding_tiebreak=7, odds=None):
        """odds=(decimal A, decimal B), typed pre-match from any bookmaker: the de-vigged price becomes the winner
        target (2025-2026 check: it beats the v7 stack and v7 adds nothing on top), markets stay Markov-coherent."""
        if circuit not in ('ATP', 'WTA'):
            raise ValueError('Circuit must be ATP or WTA')
        m = self.model(circuit)
        a, b = m.resolve(player_a), m.resolve(player_b)
        point = m.predict(a, b, surface, uncertainty=False)
        # Untrained serve/surface cells fall back to the population prior; the winner stack (dynamic Elo, rank, age)
        # was fitted on held-out rows that include such cases, so they are kept and the count is reported.
        rules = Rules(best_of, deciding_tiebreak=deciding_tiebreak)
        day = pd.Timestamp(date).tz_localize(None).normalize() if pd.Timestamp(date).tzinfo else pd.Timestamp(date).normalize()
        dynamic = dynamic_features(self.state(circuit), a, b, surface, day)
        try:
            x, params, source = dict(pair_features(self.canonical, circuit, a, b, str(day.date())), **dynamic), self.params[circuit], 'v7_stack'
        except ValueError:
            # Rank evidence stale (>60 days) or missing: stack fitted without rank/points/age (2026: ATP 67.1 %, WTA 66.6 %).
            if not self.params_norank:
                raise
            x, params, source = dynamic, self.params_norank[circuit], 'v7_stack_without_rank'
        engine = build(point['p'], point['q'], rules, params, x)
        winner = dict(engine.diagnostics, source=source)
        decided_at = pd.Timestamp.now(tz='UTC').isoformat()
        live = None if odds is not None else live_market(self.config, m.names[a], m.names[b], decided_at)
        if odds is not None or live is not None:
            market = devig(*odds) if odds is not None else live['probability_a']
            engine = recentre(point['p'], point['q'], rules, self.params[circuit]['sigma'], market)
            winner.update(source='devigged_odds' if odds is not None else 'live_snapshot', odds=list(odds) if odds else None, live=live, market_winner=market,
                          final_winner=engine.probabilities(Contract('winner', 'A'))['win'])
        board = None
        if odds is None and self.config.get('odds_provider') == 'propline':
            from tennis_odds_propline_v1 import market_board
            board = market_board(self.config['propline_root'], m.names[a], m.names[b], decided_at)
        return dict(circuit=circuit, players=[m.names[a], m.names[b]], player_ids=[a, b], surface=surface, date=str(day.date()),
                    best_of=best_of, deciding_tiebreak=deciding_tiebreak, serve=point, winner=winner,
                    markets=forecast_board(engine), market_board=board_with_model(engine, board) if board else None,
                    odds_used=odds is not None or live is not None, research_only=True)
