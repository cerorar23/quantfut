"""Common-cohort probability scoring, independent of financial settlement."""
from collections import Counter
from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

from .operations import utc


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str  # Include circuit/phase; one predeclared decision per case.
    event_id: str
    player_a: str
    player_b: str
    decision_at: str
    scheduled_start: str

    def __post_init__(self) -> None:
        if not self.case_id or not self.event_id or not self.player_a or not self.player_b or self.player_a == self.player_b:
            raise ValueError('Case identity and distinct oriented participants required')
        if utc(self.decision_at) >= utc(self.scheduled_start):
            raise ValueError('Decision must precede scheduled start')


@dataclass(frozen=True)
class BenchmarkResult:
    event_id: str
    player_a: str
    player_b: str
    status: str
    y: int | None
    actual_start: str | None
    ended_at: str | None
    available_at: str


@dataclass(frozen=True)
class BenchmarkPrediction:
    case_id: str
    player_a: str
    player_b: str
    decision_at: str
    probability: float | None
    reason: str | None = None


def probability_metrics(y: Sequence[int], probabilities: Sequence[float]) -> dict[str, Any]:
    """Natural-log loss, binary Brier and equal-width 10-bin ECE.

    Clip only for log evaluation at endpoints (epsilon=1e-12). ECE is
    descriptive and bin/sample sensitive; it is not a selection guarantee.
    """
    if len(y) != len(probabilities):
        raise ValueError('Aligned labels and probabilities required')
    if not y:
        return {'n': 0, 'log_loss': None, 'brier': None, 'ece': None, 'calibration': []}
    bins: list[list[tuple[int, float]]] = [[] for _ in range(10)]
    losses = []; briers = []
    for label, p in zip(y, probabilities):
        if type(label) is not int or label not in (0, 1) or isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError('Binary outcomes and finite probabilities required')
        clipped = min(1 - 1e-12, max(1e-12, p))
        losses.append(-label * math.log(clipped) - (1 - label) * math.log1p(-clipped))
        briers.append((p - label) ** 2)
        bins[min(int(p * 10), 9)].append((label, p))
    calibration = []
    ece = 0.0
    for i, rows in enumerate(bins):
        mean = sum(p for _, p in rows) / len(rows) if rows else None
        observed = sum(label for label, _ in rows) / len(rows) if rows else None
        if rows:
            ece += len(rows) / len(y) * abs(mean - observed)
        calibration.append({'lower': i / 10, 'upper': (i + 1) / 10, 'upper_inclusive': i == 9,
                            'n': len(rows), 'mean_probability': mean, 'observed_rate': observed})
    return {'n': len(y), 'log_loss': sum(losses) / len(y), 'brier': sum(briers) / len(y),
            'ece': ece, 'calibration': calibration, 'log_clip_epsilon': 1e-12}


class BenchmarkEvaluator:
    """Strict common intersection across declared variants and one case universe.

    Results are a separate post-forecast input. Retired/WO/cancelled remain in
    coverage counts but are outside the completed-match probability contract.
    Invalid supplied predictions fail loudly; missing predictions may abstain.
    """
    def evaluate(self, cases: Sequence[BenchmarkCase], results: Sequence[BenchmarkResult],
                 variants: Mapping[str, Sequence[BenchmarkPrediction]], evaluated_at: str) -> dict[str, Any]:
        evaluation = utc(evaluated_at)
        indexed = {c.case_id: c for c in cases}
        result_index = {r.event_id: r for r in results}
        if len(indexed) != len(cases) or len(result_index) != len(results) or not variants:
            raise ValueError('Unique case/result identities and declared variants required')
        by_variant: dict[str, dict[str, float]] = {}
        abstentions = {}
        for name, predictions in variants.items():
            seen = set(); valid = {}; reasons: Counter[str] = Counter()
            for p in predictions:
                if p.case_id in seen or p.case_id not in indexed:
                    raise ValueError('Duplicate or foreign prediction')
                seen.add(p.case_id); c = indexed[p.case_id]
                if (p.player_a, p.player_b) != (c.player_a, c.player_b) or utc(p.decision_at) != utc(c.decision_at):
                    raise ValueError('Prediction orientation or decision mismatch')
                if p.probability is None:
                    reasons[p.reason or 'abstained'] += 1
                    continue
                probability_metrics([0], [p.probability])
                valid[p.case_id] = p.probability
            reasons['not_supplied'] += len(indexed) - len(seen)
            by_variant[name] = valid; abstentions[name] = dict(reasons)
        eligible = {}; excluded: Counter[str] = Counter()
        statuses: Counter[str] = Counter()
        for c in cases:
            r = result_index.get(c.event_id)
            if r is None:
                excluded['result_missing'] += 1; continue
            statuses[r.status] += 1
            if (r.player_a, r.player_b) != (c.player_a, c.player_b):
                raise ValueError('Result orientation mismatch')
            if utc(r.available_at) > evaluation:
                excluded['result_not_available_at_evaluation'] += 1; continue
            if r.status != 'completed':
                excluded['outside_completed_contract'] += 1; continue
            if r.actual_start is None or r.ended_at is None:
                excluded['unverified_actual_times'] += 1; continue
            if not utc(c.decision_at) < utc(r.actual_start) < utc(r.ended_at) <= utc(r.available_at):
                excluded['invalid_actual_chronology'] += 1; continue
            if type(r.y) is not int or r.y not in (0, 1):
                raise ValueError('Completed result requires a binary outcome')
            eligible[c.case_id] = r.y
        common = sorted(set(eligible).intersection(*(set(v) for v in by_variant.values())))
        n = len(cases)
        return {'schema': 'tennis-common-benchmark-v1', 'label': 'experimental',
                'evaluated_at': evaluated_at, 'n_total': n, 'n_eligible_completed': len(eligible),
                'n_common': len(common), 'coverage': len(common) / n if n else None,
                'coverage_of_eligible': len(common) / len(eligible) if eligible else None,
                'common_case_ids': common, 'excluded': dict(excluded), 'result_statuses': dict(statuses),
                'available_predictions': {k: len(v) for k, v in by_variant.items()},
                'abstentions': abstentions,
                'metrics': {name: probability_metrics([eligible[k] for k in common], [p[k] for k in common])
                            for name, p in by_variant.items()},
                'financial_validation': False, 'production_approved': False,
                'uncertainty': 'Point estimates only; no independent-match significance claim.'}
