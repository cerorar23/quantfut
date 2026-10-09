"""Train-only width calibration and constrained hypothetical team scenarios.

Historical labels cannot establish pregame availability. This module never
marks a distribution actionable and never treats team conservation as proof
of fitted lineup dependence or prospective calibration.
"""
from datetime import date
from collections import defaultdict
import math
import numpy as np

VERSION = 'regulation-width-team-scenarios-v1'


def history_band(mean):
    return 'under12' if mean < 12 else '12to24' if mean < 24 else '24to36' if mean < 36 else '36plus'


def widen(samples, scale):
    x = np.asarray(samples, dtype=float)
    if x.ndim != 1 or not x.size or not np.isfinite(x).all() or x.min() < 0 or x.max() > 48:
        raise ValueError('invalid regulation distribution')
    if not math.isfinite(scale) or scale < 1:
        raise ValueError('invalid widening scale')
    return np.clip(np.median(x) + scale * (x - np.median(x)), 0, 48).tolist()


def fit_width(forecasts, scores, protocol):
    """Choose the first grid scale meeting80% train coverage, pooled by band."""
    if not forecasts or len(forecasts) != len(scores):
        raise ValueError('empty or mismatched calibration input')
    cutoff = date.fromisoformat(protocol['fit_cutoff'])
    groups = defaultdict(list)
    seen = set()
    dates = []
    for f, s in zip(forecasts, scores):
        key = (f['game_id'], f['player_id'])
        if key in seen or key != (s['game_id'], s['player_id']):
            raise ValueError('calibration identity mismatch')
        seen.add(key)
        if f['season'] != protocol['train_season'] or s['season'] != f['season']:
            raise ValueError('non-training season in fitting')
        if date.fromisoformat(f['date']) >= cutoff or s['date'] != f['date'] or f['history_max_date'] >= f['date']:
            raise ValueError('fitting cutoff or chronology violated')
        x = np.asarray(widen(f['candidate_samples'], 1))
        y = s['actual_regulation_minutes']
        if not math.isfinite(y) or not 0 < y <= 48:
            raise ValueError('invalid positive calibration label')
        groups[len(x)].append((x, y, history_band(f['baseline_mean'])))
        dates.append(f['date'])
    grid = protocol['scale_grid']
    if not grid or grid != sorted(set(grid)) or grid[0] != 1 or any(not math.isfinite(v) or v < 1 for v in grid):
        raise ValueError('invalid fixed calibration grid')
    counts, hits = defaultdict(int), {str(scale): defaultdict(int) for scale in grid}
    for records in groups.values():
        x = np.asarray([r[0] for r in records])
        y = np.asarray([r[1] for r in records])
        band = np.asarray([r[2] for r in records])
        anchor = np.median(x, axis=1)[:, None]
        for name in set(band):
            counts[str(name)] += int((band == name).sum())
        counts['all'] += len(records)
        for scale in grid:
            expanded = np.clip(anchor + scale * (x - anchor), 0, 48)
            lo, hi = np.quantile(expanded, [.1, .9], axis=1, method='linear')
            covered = (lo <= y) & (y <= hi)
            hits[str(scale)]['all'] += int(covered.sum())
            for name in set(band):
                hits[str(scale)][str(name)] += int(covered[band == name].sum())
    target = protocol['target_coverage']
    if not 0 < target < 1 or protocol['minimum_band_cases'] < 1:
        raise ValueError('invalid coverage protocol')
    selections = {}
    for name, n in sorted(counts.items()):
        source = name if name == 'all' or n >= protocol['minimum_band_cases'] else 'all'
        chosen = next((scale for scale in grid if hits[str(scale)][source] / counts[source] >= target), grid[-1])
        selections[name] = dict(scale=chosen, n=n, fitted_from=source,
                                train_coverage=hits[str(chosen)][name] / n,
                                train_target_met=hits[str(chosen)][source] / counts[source] >= target)
    return dict(version=VERSION, train_season=protocol['train_season'], fit_cutoff=protocol['fit_cutoff'],
                fitting_max_date=max(dates), target_coverage=target, selections=selections,
                fitting_cases=len(forecasts), grid=grid, validation_used_for_fitting=False,
                evaluation_used_for_fitting=False, prospective_confirmation=False, actionable=False)


def calibrated_forecast(forecast, calibration):
    if date.fromisoformat(forecast['date']) < date.fromisoformat(calibration['fit_cutoff']):
        raise ValueError('calibrator not available at forecast cut')
    if calibration['fitting_max_date'] >= forecast['date']:
        raise ValueError('future labels in calibrator')
    band = history_band(forecast['baseline_mean'])
    selected = calibration['selections'].get(band, calibration['selections']['all'])
    samples = widen(forecast['candidate_samples'], selected['scale'])
    return dict(forecast, calibrated_samples=samples, calibrated_mean=float(np.mean(samples)),
                calibration_band=band, calibration_scale=selected['scale'],
                calibration_training_max_date=calibration['fitting_max_date'], actionable=False)


def project_team(proposals, lower, upper):
    """Euclidean projection on bounded simplex: sum240, each player's bounds."""
    x, lo, hi = (np.asarray(v, dtype=float) for v in (proposals, lower, upper))
    if x.ndim != 2 or not x.shape[0] or lo.ndim != 1 or hi.shape != lo.shape or x.shape[1] != len(lo) or not len(lo):
        raise ValueError('invalid team dimensions')
    if not all(np.isfinite(v).all() for v in (x, lo, hi)) or (lo < 0).any() or (hi > 48).any() or (lo > hi).any():
        raise ValueError('invalid team bounds')
    if lo.sum() > 240 + 1e-10 or hi.sum() < 240 - 1e-10:
        raise ValueError('infeasible regulation scenario')
    left = np.min(x - hi, axis=1)[:, None]
    right = np.max(x - lo, axis=1)[:, None]
    for _ in range(60):
        mid = (left + right) / 2
        above = np.clip(x - mid, lo, hi).sum(axis=1) > 240
        left = np.where(above[:, None], mid, left)
        right = np.where(above[:, None], right, mid)
    out = np.clip(x - (left + right) / 2, lo, hi)
    if not np.allclose(out.sum(axis=1), 240, rtol=0, atol=1e-8):
        raise ValueError('projection failed conservation')
    return out


def team_scenarios(players, draws=128, seed=20261007, availability_kind='hypothetical'):
    """Require explicit active/DNP scenario; never infer availability from labels."""
    if availability_kind != 'hypothetical':
        raise ValueError('only explicitly hypothetical availability supported')
    if not isinstance(draws, int) or draws < 1 or not players:
        raise ValueError('invalid simulation count or empty roster')
    ids = [p['player_id'] for p in players]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate scenario identity')
    if len({p['team_id'] for p in players}) != 1 or any(p['id_namespace'] != 'nba' for p in players):
        raise ValueError('mixed team or namespace in scenario')
    samples, lower, upper = [], [], []
    for player in players:
        if type(player['active']) is not bool:
            raise ValueError('explicit active flag required')
        x = np.asarray(widen(player['samples'], 1))
        low, high = player.get('minimum_minutes', 0), player.get('maximum_minutes', 48)
        if not math.isfinite(low) or not math.isfinite(high) or not 0 <= low <= high <= 48:
            raise ValueError('invalid player scenario limit')
        if not player['active'] and low != 0:
            raise ValueError('DNP incompatible with positive minimum')
        lower.append(low)
        upper.append(high if player['active'] else 0)
        samples.append(x)
    rng = np.random.default_rng(seed)
    raw = np.column_stack([rng.choice(x, size=draws) for x in samples])
    for i, p in enumerate(players):
        if not p['active']:
            raw[:, i] = 0
    projected = project_team(raw, lower, upper)
    return dict(player_ids=ids, draws=projected.tolist(), raw_team_mean=float(raw.sum(axis=1).mean()),
                projected_team_mean=float(projected.sum(axis=1).mean()), team_minutes_coherent=True,
                mean_projection_change=float(np.abs(projected - raw).mean()), availability_kind=availability_kind,
                availability_known=False, fitted_lineup_dependence=False, actionable=False, seed=seed)
