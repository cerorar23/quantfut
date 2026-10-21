"""Common-sample scoring, paired uncertainty, calibration and abstention.

Historical analysis is explicitly exploratory. Confidence bands describe the
forecast probabilities; they are not certainty grades for individual matches.
"""
from collections import defaultdict
import math
import unicodedata
import numpy as np
import pandas as pd
from tennis_engine.benchmark import probability_metrics

MODELS = ('current_hybrid', 'model_probability', 'surface_elo_probability',
          'calibrated_surface_elo', 'weighted_elo', 'adaptive_elo')


def normalized_name(value: str) -> str:
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', value)
                          if not unicodedata.combining(c)).casefold().split())


def identity_review(names: dict[str, str]) -> dict:
    groups = defaultdict(list)
    for pid, name in names.items():
        if not pid or not normalized_name(name):
            raise ValueError('Nonempty canonical IDs and names required')
        groups[normalized_name(name)].append(pid)
    ambiguous = {n: sorted(ids) for n, ids in groups.items() if len(ids) > 1}
    return dict(ambiguous_names=ambiguous,
                excluded_ids=sorted(pid for ids in ambiguous.values() for pid in ids),
                automatic_merges=0,
                scope='Conservative current knowledge quarantine, not proof of historical identity availability')


def wilson(wins: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z = 1.959963984540054
    center = (wins/n+z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt((wins/n)*(1-wins/n)/n+z*z/(4*n*n))/(1+z*z/n)
    return [max(0., center-half), min(1., center+half)]


def block_interval(values, blocks, *, draws=5000, alpha=.05, seed=20261019):
    """Ratio-of-sums bootstrap keeps all rows of a sampled block together.

    Paired loss differences must be passed before resampling. This does not
    capture all repeated-player dependence across tournaments.
    """
    frame = pd.DataFrame({'value': values, 'block': blocks})
    if len(frame) == 0:
        return None
    if frame.isna().any().any() or not np.isfinite(frame.value.to_numpy(dtype=float)).all():
        raise ValueError('Finite values and known blocks required')
    if frame.value.nunique() < 2:
        # An all-success band must not display [1,1] as evidence of certainty.
        # Nonparametric resampling cannot recover unobserved failure variation.
        return None
    grouped = frame.groupby('block', sort=True).value.agg(['sum', 'count'])
    if len(grouped) < 2:
        return None
    rng = np.random.default_rng(seed)
    indices = rng.integers(len(grouped), size=(draws, len(grouped)))
    means = grouped['sum'].to_numpy()[indices].sum(axis=1)/grouped['count'].to_numpy()[indices].sum(axis=1)
    return np.quantile(means, [alpha/2, 1-alpha/2]).tolist()


def reliability(y, probabilities, blocks) -> dict:
    """Favourite-oriented hit rates; tie .5 deterministically selects side A.

    No result is used to choose a side or a probability threshold. Wilson
    intervals are labelled iid approximations; block intervals are separate.
    """
    metric = probability_metrics(list(y), list(probabilities))
    y, p, blocks = np.asarray(y), np.asarray(probabilities), np.asarray(blocks)
    confidence = np.maximum(p, 1-p)
    hit = np.where(p >= .5, y, 1-y)
    bands = []
    for low, high in ((.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.)):
        mask = (confidence >= low) & ((confidence < high) if high < 1 else (confidence <= high))
        n = int(mask.sum())
        bands.append(dict(lower=low, upper=high, upper_inclusive=high == 1., n=n,
            mean_forecast=float(confidence[mask].mean()) if n else None,
            observed_hit_rate=float(hit[mask].mean()) if n else None,
            iid_wilson_ci95=wilson(int(hit[mask].sum()), n),
            block_hit_rate_ci95=block_interval(hit[mask], blocks[mask], draws=2000),
            block_calibration_gap_ci95=block_interval(hit[mask]-confidence[mask], blocks[mask], draws=2000),
            individual_forecast_certainty=False))
    selective = []
    for threshold in (.5, .7, .8, .9):
        mask = confidence >= threshold
        selective.append(dict(threshold=threshold, n=int(mask.sum()),
            coverage=float(mask.mean()) if len(mask) else None,
            accuracy=float(hit[mask].mean()) if mask.any() else None,
            threshold_selected_using_results=False))
    return dict(metrics=metric, favourite_accuracy=float(hit.mean()) if len(hit) else None,
                bands=bands, fixed_threshold_coverage=selective,
                confidence_is_probability_not_certainty=True)


def compare(frame: pd.DataFrame, universe_n: int, *, scope: str) -> dict:
    required = {'match_id', 'y', 'period', 'competition_id', *MODELS}
    if not required.issubset(frame.columns) or frame.match_id.duplicated().any() or len(frame) > universe_n:
        raise ValueError('Unique common-cohort rows and explicit universe required')
    for model in MODELS:
        probability_metrics(frame.y.tolist(), frame[model].tolist())
    y = frame.y.to_numpy(dtype=int)
    losses = {}
    models = {}
    for model in MODELS:
        p = frame[model].to_numpy(dtype=float)
        clipped = np.clip(p, 1e-12, 1-1e-12)
        losses[model] = -(y*np.log(clipped)+(1-y)*np.log1p(-clipped))
        models[model] = reliability(y.tolist(), p.tolist(), frame.competition_id.tolist())
    comparisons = {}
    # Four primary tests across two circuits: hybrid against WElo and calibrated
    # surface Elo. Bonferroni family alpha .05 => per-comparison alpha .0125.
    for reference in ('weighted_elo', 'calibrated_surface_elo'):
        delta = losses['current_hybrid']-losses[reference]
        comparisons[reference] = dict(hybrid_minus_reference_log_loss=float(delta.mean()) if len(delta) else None,
            tournament_block_ci98_75=block_interval(delta, frame.competition_id, alpha=.0125),
            source_period_block_ci98_75=block_interval(delta, frame.period, alpha=.0125),
            primary_family_tests=4, family_alpha=.05,
            negative_difference_favours_hybrid=True)
    return dict(scope=scope, total_universe=universe_n, common_n=len(frame),
                common_coverage=len(frame)/universe_n if universe_n else None,
                same_match_ids_for_all_models=True, models=models, paired_comparisons=comparisons,
                historical_availability_verified=False, predictive_quality_accredited=False,
                financial_validation=False,
                limits=['2026 already inspected: exploratory, not confirmatory.',
                        'Weekly/source dates do not verify physical start times.',
                        'Tournament and period bootstraps are sensitivity checks; cross-block player dependence remains.',
                        'No automatic promotion or reliability label is inferred from a point estimate.'])
