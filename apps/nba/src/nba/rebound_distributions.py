"""Conditional no-overtime rebound research with causal history and frozen fits."""
from collections import defaultdict, Counter
from itertools import groupby
from datetime import date
import hashlib
import math
import numpy as np
from scipy.stats import poisson, nbinom

FAMILIES = ('baseline', 'minutes_poisson', 'gamma_poisson', 'negative_binomial')


def rebound_labels(minute_labels, boxes):
    source = {(r['game_id'], r['player_id']): r for r in boxes if r['season_type'] == 'regular'}
    if len(source) != sum(r['season_type'] == 'regular' for r in boxes):
        raise ValueError('duplicate official count identity')
    rows, seen = [], set()
    for r in minute_labels:
        key = (r['game_id'], r['player_id'])
        if key in seen or key not in source:
            raise ValueError('missing or duplicated count label')
        seen.add(key)
        box = source[key]
        if any(box[k] != r[k] for k in ['date', 'season', 'team_id', 'id_namespace']):
            raise ValueError('count/exposure identity mismatch')
        count = box['rebounds']
        if isinstance(count, bool) or not math.isfinite(count) or count < 0 or int(count) != count:
            raise ValueError('invalid rebound count')
        rows.append(dict(r, rebounds=int(count), regulation_count_verified=r['overtime_periods'] == 0))
    if seen != set(source):
        raise ValueError('count roster differs from regulation roster')
    return rows


def rate_features(rows, minute_forecasts, protocol):
    """No target-date count or exposure enters any same-date rate feature."""
    seen, metadata = set(), {}
    for r in rows:
        key = (r['game_id'], r['player_id'])
        identity = (r['date'], r['season'])
        date.fromisoformat(r['date'])
        if key in seen or r['id_namespace'] != 'nba' or r['season_type'] != 'regular':
            raise ValueError('invalid count identity or scope')
        seen.add(key)
        if r['game_id'] in metadata and metadata[r['game_id']] != identity:
            raise ValueError('conflicting count game metadata')
        metadata[r['game_id']] = identity
        if (isinstance(r['rebounds'], bool) or not isinstance(r['rebounds'], int) or r['rebounds'] < 0
                or not math.isfinite(r['regulation_minutes']) or not 0 <= r['regulation_minutes'] <= 48
                or not isinstance(r['overtime_periods'], int) or r['overtime_periods'] < 0):
            raise ValueError('invalid count or exposure')
    mins = {(f['game_id'], f['player_id']): f for f in minute_forecasts}
    if len(mins) != len(minute_forecasts):
        raise ValueError('duplicate minute feature')
    selected = sorted(rows, key=lambda r: (r['date'], r['game_id'], r['player_id']))
    histories, features, outcomes, skipped = defaultdict(list), [], [], Counter()
    for day, group in groupby(selected, key=lambda r: r['date']):
        today = list(group)
        for r in today:
            if r['overtime_periods']:
                skipped['overtime_game_label_excluded'] += 1
                continue
            if r['regulation_minutes'] == 0:
                skipped['zero_regulation_exposure'] += 1
                continue
            key = (r['game_id'], r['player_id'])
            past = [v for v in histories[r['player_id'], r['season']] if v['date'] < day
                    and v['regulation_minutes'] > 0 and not v['overtime_periods']][-protocol['rate_history_window']:]
            if key not in mins or len(past) < protocol['minimum_rate_appearances']:
                skipped['insufficient_minutes_or_noOT_rate_history'] += 1
                continue
            m = mins[key]
            if any(m[k] != r[k] for k in ['date', 'season']) or m['history_max_date'] >= day:
                raise ValueError('future or mismatched minute history')
            x = np.asarray(m['candidate_samples'], dtype=float)
            if x.ndim != 1 or not x.size or not np.isfinite(x).all() or x.min() < 0 or x.max() > 48:
                raise ValueError('invalid minute distribution')
            alpha = sum(v['rebounds'] for v in past) + protocol['rate_prior_minutes'] * protocol['rate_prior_rebounds_per_minute']
            beta = sum(v['regulation_minutes'] for v in past) + protocol['rate_prior_minutes']
            if alpha <= 0 or beta <= 0:
                raise ValueError('invalid rate posterior')
            identity = {k:r[k] for k in ['game_id', 'player_id', 'date', 'season']}
            features.append(dict(**identity, rate_alpha=alpha, rate_beta=beta, rate_mean=alpha / beta,
                baseline_count_mean=float(np.mean([v['rebounds'] for v in past[-protocol['baseline_window']:]])),
                rate_history_count=len(past), rate_history_max_date=past[-1]['date'], rate_history_game_ids=[v['game_id'] for v in past],
                minute_samples=x.tolist(), minute_history_max_date=m['history_max_date'], minute_history_game_ids=m['history_game_ids'],
                minutes_baseline_mean=m['baseline_mean'], availability_known=False, current_team_known=False,
                conditional_on_observed_positive_noOT=True, original_historical_receipt_known=False, actionable=False))
            outcomes.append(dict(**identity, team_id=r['team_id'], actual_rebounds=r['rebounds'], actual_regulation_minutes=r['regulation_minutes']))
        for r in today:
            histories[r['player_id'], r['season']].append(r)
    return features, outcomes, dict(skipped)


def fit_dispersion(features, outcomes, protocol):
    if not features or len(features) != len(outcomes):
        raise ValueError('empty or mismatched training')
    residual, denominator, dates, seen = 0., 0., [], set()
    for f, y in zip(features, outcomes):
        key = (f['game_id'], f['player_id'])
        if key in seen or key != (y['game_id'], y['player_id']):
            raise ValueError('training count identity mismatch')
        seen.add(key)
        if (f['season'] != protocol['train_season'] or y['season'] != f['season'] or y['date'] != f['date']
                or f['date'] >= protocol['fit_cutoff'] or f['rate_history_max_date'] >= f['date'] or f['minute_history_max_date'] >= f['date']):
            raise ValueError('training contamination or cutoff violation')
        actual = y['actual_rebounds']
        if isinstance(actual, bool) or not isinstance(actual, int) or actual < 0:
            raise ValueError('invalid training rebound outcome')
        rates = f['rate_mean'] * np.asarray(f['minute_samples'])
        if not np.isfinite(rates).all() or rates.min() < 0:
            raise ValueError('invalid training mean')
        residual += (actual - rates.mean())**2 - rates.mean() - rates.var()
        denominator += float(np.mean(rates**2))
        dates.append(f['date'])
    if denominator <= 0:
        raise ValueError('unidentified dispersion')
    raw = residual / denominator
    phi = min(protocol['maximum_dispersion'], max(0., raw))
    return dict(train_season=protocol['train_season'], fit_cutoff=protocol['fit_cutoff'], fitting_max_date=max(dates),
                training_cases=len(features), raw_dispersion=float(raw), dispersion=float(phi),
                dispersion_clamped=bool(phi != raw), shape=None if phi == 0 else float(1 / phi),
                method='Training residual second moment minus mean and minute-mixture variance, divided by E(lambda²).',
                validation_used_for_fitting=False, evaluation_used_for_fitting=False, actionable=False)


def family_distribution(feature, fit, protocol, family, minute_samples=None):
    if family not in FAMILIES:
        raise ValueError('unknown count family')
    if feature['date'] < fit['fit_cutoff'] or fit['fitting_max_date'] >= feature['date']:
        raise ValueError('count fit unavailable at forecast cut')
    x = np.asarray(feature['minute_samples'] if minute_samples is None else minute_samples, dtype=float)
    if x.ndim != 1 or not x.size or not np.isfinite(x).all() or x.min() < 0 or x.max() > 48:
        raise ValueError('invalid forecast minutes')
    rate, alpha, beta = feature['rate_mean'], feature['rate_alpha'], feature['rate_beta']
    if not all(math.isfinite(v) and v > 0 for v in (rate, alpha, beta)):
        raise ValueError('invalid forecast posterior')
    means = rate * x
    shape = fit['shape']
    if family == 'baseline':
        means = np.array([feature['baseline_count_mean']])
        if not np.isfinite(means).all() or means.min() < 0:
            raise ValueError('invalid baseline count mean')
    if family == 'gamma_poisson':
        shape, success = alpha, beta / (beta + x)
    elif family == 'negative_binomial' and shape is not None:
        if not math.isfinite(shape) or shape <= 0:
            raise ValueError('invalid fitted NB shape')
        success = shape / (shape + means)
    else:
        shape, success = None, None
    quantiles = poisson.ppf(1-protocol['tail_probability'], means) if shape is None else nbinom.ppf(1-protocol['tail_probability'], shape, success)
    maximum = int(max(protocol['minimum_support'], np.max(quantiles)))
    if maximum > protocol['maximum_support']:
        raise ValueError('predictive count tail exceeds support budget')
    grid = np.arange(maximum+1)
    pmf = poisson.pmf(grid[:,None], means[None,:]).mean(axis=1) if shape is None else nbinom.pmf(grid[:,None], shape, success[None,:]).mean(axis=1)
    omitted = float(poisson.sf(maximum, means).mean() if shape is None else nbinom.sf(maximum, shape, success).mean())
    if not np.isfinite(pmf).all() or pmf.min() < 0 or omitted > protocol['tail_tolerance'] or abs(pmf.sum()-1) > protocol['tail_tolerance']:
        raise ValueError('invalid distribution or omitted tail')
    pmf /= pmf.sum()
    return dict(pmf=pmf.tolist(), family=family, support_maximum=maximum, omitted_tail_mass=omitted,
                minute_samples=x.tolist(), conditional_on_positive_noOT=True, void_probability=None, actionable=False)


def categories(pmf, line):
    p = np.asarray(pmf, dtype=float)
    if p.ndim != 1 or not p.size or not np.isfinite(p).all() or p.min() < 0 or abs(p.sum()-1) > 1e-10:
        raise ValueError('invalid count probabilities')
    if not math.isfinite(line) or line < 0:
        raise ValueError('invalid research threshold')
    k = np.arange(len(p))
    return dict(under=float(p[k < line].sum()), push=float(p[k == line].sum()), over=float(p[k > line].sum()),
                conditional_on_positive_noOT=True, void_probability=None, actual_contract_verified=False)


def count_scores(pmf, actual, key, protocol):
    categories(pmf, 0)
    p = np.asarray(pmf)
    if isinstance(actual, bool) or not isinstance(actual, int) or not 0 <= actual < len(p):
        raise ValueError('count outcome outside evaluated support')
    cdf = np.cumsum(p);k = np.arange(len(p));lo,hi = (int(np.searchsorted(cdf,q)) for q in (.1,.9))
    mass = float(p[lo:hi+1].sum());covered = int(lo<=actual<=hi)
    u = (int.from_bytes(hashlib.sha256(f"{protocol['seed']}:{key}".encode()).digest()[:8],'big') >> 11) / 2**53
    below = float(cdf[actual-1]) if actual else 0.
    mean = float(np.dot(k,p));err = mean-actual
    result = dict(crps=float(np.square(cdf-(k>=actual)).sum()),nll=float(-np.log(max(p[actual],protocol['log_probability_floor']))),
        nll_probability_clipped=bool(p[actual]<protocol['log_probability_floor']),mae=abs(err),squared_error=err**2,
        covered80=covered,width80=hi-lo,central_interval_mass=mass,coverage_minus_mass=covered-mass,
        randomized_pit=below+u*float(p[actual]),mean=mean)
    for line in protocol['diagnostic_lines']:
        probability=categories(pmf,line)['over']
        result[f'over_{line}_probability']=probability
        result[f'over_{line}_actual']=int(actual>line)
        result[f'brier_{line}']=(probability-int(actual>line))**2
    return result


def model_summary(rows, families, protocol, intervals=True):
    if not rows:
        return dict(rows=0,games=0,dates=0,models={})
    report=dict(rows=len(rows),games=len({r['game_id'] for r in rows}),dates=len({r['date'] for r in rows}),models={})
    days=defaultdict(list)
    for r in rows:days[r['date']].append(r)
    groups=[days[d] for d in sorted(days)];counts=np.array([len(g) for g in groups])
    rng=np.random.default_rng(protocol['seed'])
    indices=rng.integers(0,len(groups),size=(protocol['bootstrap_replicates'],len(groups))) if intervals else None
    for family in families:
        values=[r['metrics'][family] for r in rows]
        summary={k:float(np.mean([v[k] for v in values])) for k in values[0] if k!='randomized_pit'}
        summary['rmse']=float(np.sqrt(summary.pop('squared_error')))
        summary['randomized_pit_bins']=np.histogram([v['randomized_pit'] for v in values],bins=np.linspace(0,1,11))[0].tolist()
        summary['reliability']={}
        for line in protocol['diagnostic_lines']:
            bins=[]
            for index in range(10):
                members=[v for v in values if min(int(v[f'over_{line}_probability']*10),9)==index]
                bins.append(dict(range=[index/10,(index+1)/10],n=len(members),mean_probability=float(np.mean([v[f'over_{line}_probability'] for v in members])) if members else None,
                    observed_rate=float(np.mean([v[f'over_{line}_actual'] for v in members])) if members else None))
            summary['reliability'][str(line)]=bins
        if family!='baseline' and intervals:
            sums=np.array([sum(r['metrics'][family]['crps']-r['metrics']['baseline']['crps'] for r in group) for group in groups])
            diffs=sums[indices].sum(axis=1)/counts[indices].sum(axis=1)
            summary['crps_difference_vs_baseline']=float(sums.sum()/counts.sum())
            summary['crps_difference_ci95_date_cluster']=np.quantile(diffs,[.025,.975]).tolist()
        report['models'][family]=summary
    return report


def choose_family(validation, protocol):
    models=validation['models']
    if not validation['rows'] or any(not math.isfinite(models[f]['crps']) for f in FAMILIES):
        raise ValueError('invalid validation comparison')
    best=min(protocol['candidate_priority'],key=lambda f:models[f]['crps'])
    chosen=best if models[best]['crps']<models['baseline']['crps']-protocol['selection_minimum_difference'] else 'baseline'
    return dict(selected_family=chosen,best_candidate=best,validation_cases=validation['rows'],
        validation_CRPS={f:models[f]['crps'] for f in FAMILIES},selected_before_evaluation=True,
        validation_selection_only=True,candidate_promoted=False,formal_F5_gate_passed=False)
