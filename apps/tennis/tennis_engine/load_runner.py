"""Executable baseline/load experiment; no simulated probability fallback."""
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence, Any
import math

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit

from .benchmark import BenchmarkCase, BenchmarkResult, BenchmarkPrediction, BenchmarkEvaluator
from .operations import utc
from .recent_load import RecentLoadExtractor, LoadObservation


def load_difference(a: dict[str, Any], b: dict[str, Any]) -> np.ndarray:
    """Antisymmetric differences, including missing and coverage indicators.

    Missing numeric components are encoded as zero with a separate indicator;
    zero alone never asserts zero workload. No population statistic is fitted
    on validation/test. RMS scaling is trained later and preserves symmetry.
    """
    if a['features'].keys() != b['features'].keys():
        raise ValueError('Aligned feature contracts required')
    values = []
    for key in sorted(a['features']):
        x, y = a['features'][key], b['features'][key]
        xv, yv = x['value'], y['value']
        values.extend([(xv if xv is not None else 0) - (yv if yv is not None else 0),
                       int(xv is None) - int(yv is None),
                       int(x['history_complete']) - int(y['history_complete']),
                       x['observed_matches'] - y['observed_matches'],
                       x['ambiguous_boundary_matches'] - y['ambiguous_boundary_matches']])
    return np.asarray(values, dtype=float)


@dataclass(frozen=True)
class LoadTrainingRow:
    case: BenchmarkCase
    result: BenchmarkResult
    baseline: BenchmarkPrediction
    history: tuple[LoadObservation, ...]
    history_complete: bool = False


class LoadCorrection:
    """Ridge logistic residual around the existing model's fixed log-odds.

    logit(p) = logit(p_base) + beta.T @ (x_A-x_B)/RMS_train.
    No intercept or centering, so swapping players complements probability.
    The predeclared ridge is fixed; selection needs a separate temporal study.
    Fit only on fully labelled, pre-fit observations with historical features
    computed at their own decision time. Training availability is not inferred
    from historical match dates.
    """
    def __init__(self, ridge: float = 1.0, min_training_rows: int = 20):
        if not math.isfinite(ridge) or ridge <= 0 or min_training_rows < 2:
            raise ValueError('Positive ridge and at least two training rows required')
        self.ridge = ridge
        self.min_training_rows = min_training_rows
        self.artifact: dict[str, Any] | None = None

    def fit(self, rows: Sequence[LoadTrainingRow], fitted_at: str) -> dict[str, Any]:
        utc(fitted_at)
        if self.artifact is not None:
            raise ValueError('Use a new correction object for a new temporal fit')
        if len(rows) < self.min_training_rows or len({r.case.event_id for r in rows}) != len(rows):
            raise ValueError('Insufficient independent event rows or duplicate training events')
        x = []; offsets = []; labels = []; feature_keys = None
        for row in rows:
            c = row.case
            if utc(row.result.available_at) >= utc(fitted_at):
                raise ValueError('Training labels must be received strictly before fit')
            report = BenchmarkEvaluator().evaluate([c], [row.result], {'baseline': [row.baseline]}, fitted_at)
            if report['n_common'] != 1:
                raise ValueError('Training row violates completed pre-match contract')
            load_a,load_b = [RecentLoadExtractor().transform(row.history,pid,c.decision_at,
                            c.scheduled_start,c.event_id,history_complete=row.history_complete)
                            for pid in (c.player_a,c.player_b)]
            feature_keys = sorted(load_a['features'])
            x.append(load_difference(load_a,load_b))
            offsets.append(logit(np.clip(row.baseline.probability, 1e-12, 1-1e-12)))
            labels.append(row.result.y)
        matrix = np.asarray(x); y = np.asarray(labels); offset = np.asarray(offsets)
        if len(set(labels)) < 2 or not np.any(matrix):
            raise ValueError('Both outcomes and nonconstant load information required')
        scale = np.sqrt(np.mean(matrix ** 2, axis=0)); scale[scale == 0] = 1
        matrix = matrix / scale
        def objective(beta: np.ndarray) -> tuple[float, np.ndarray]:
            z = offset + matrix @ beta
            value = np.mean(np.logaddexp(0, z) - y*z) + self.ridge*np.dot(beta, beta)/2
            gradient = matrix.T @ (expit(z)-y)/len(y) + self.ridge*beta
            return float(value), gradient
        fitted = minimize(objective, np.zeros(matrix.shape[1]), jac=True, method='L-BFGS-B')
        if not fitted.success:
            raise RuntimeError('Load correction did not converge')
        self.artifact = {'schema': 'tennis-load-offset-v1', 'label': 'experimental', 'fitted_at': fitted_at,
                         'last_label_received_at': max((r.result.available_at for r in rows), key=utc),
                         'training_event_ids': [r.case.event_id for r in rows], 'n': len(rows),
                         'beta': fitted.x.tolist(), 'scale': scale.tolist(), 'ridge': self.ridge,
                         'feature_keys': feature_keys,
                         'source_sha256s': sorted({h.source_sha256 for r in rows for h in r.history
                                                  if utc(h.available_at)<utc(r.case.decision_at)}),
                         'production_approved': False}
        return self.artifact

    def predict(self, case: BenchmarkCase, base_probability: float,
                a: dict[str, Any], b: dict[str, Any]) -> float:
        if self.artifact is None:
            raise ValueError('Load correction has no fitted artifact')
        if utc(self.artifact['fitted_at']) >= utc(case.decision_at):
            raise ValueError('Fit must precede prediction decision')
        if case.event_id in self.artifact['training_event_ids']:
            raise ValueError('Target event was used to train load correction')
        if sorted(a['features']) != self.artifact['feature_keys']:
            raise ValueError('Different load feature contract')
        z = logit(np.clip(base_probability, 1e-12, 1-1e-12))
        z += np.dot(load_difference(a,b)/np.asarray(self.artifact['scale']), self.artifact['beta'])
        return float(expit(z))


class ModelRunner:
    """Run a real baseline callable and fitted optional correction, without labels.

    The caller connects the existing hybrid_forecast function or a verified
    precomputed forecast. The runner never fits on target outcomes. Missing
    trained corrections abstain explicitly, rather than copying baseline.
    """
    def __init__(self, baseline: Callable[[BenchmarkCase], float], correction: LoadCorrection | None = None):
        self.baseline = baseline
        self.correction = correction

    def run(self, cases: Sequence[BenchmarkCase], history: Iterable[LoadObservation],
            *, history_complete: bool = False) -> dict[str, Any]:
        history = list(history)
        if len({c.case_id for c in cases}) != len(cases):
            raise ValueError('Duplicate forecast cases')
        variants: dict[str, list[BenchmarkPrediction]] = {'current': [], 'current_plus_load': []}
        features = {}
        for case in cases:
            supplied = self.baseline(case)
            if isinstance(supplied,bool):
                raise ValueError('Boolean baseline is not a probability')
            base = float(supplied)
            if not math.isfinite(base) or not 0 <= base <= 1:
                raise ValueError('Baseline must return a valid probability')
            a,b = [RecentLoadExtractor().transform(history, pid, case.decision_at,
                     case.scheduled_start, case.event_id, history_complete=history_complete)
                   for pid in (case.player_a, case.player_b)]
            features[case.case_id] = {'a': a, 'b': b}
            def prediction(p: float | None, reason: str | None = None) -> BenchmarkPrediction:
                return BenchmarkPrediction(case.case_id, case.player_a, case.player_b, case.decision_at, p, reason)
            variants['current'].append(prediction(base))
            if self.correction is None or self.correction.artifact is None:
                variants['current_plus_load'].append(prediction(None, 'no_temporally_valid_training_sample'))
            else:
                if all(v['value'] is None for f in (a,b) for v in f['features'].values()):
                    variants['current_plus_load'].append(prediction(None, 'load_window_membership_unknown'))
                else:
                    variants['current_plus_load'].append(prediction(self.correction.predict(case,base,a,b)))
        return {'variants': variants, 'features': features, 'label': 'experimental'}
