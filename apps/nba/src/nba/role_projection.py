"""Per-minute production follows the player; the current team's recent minutes update his role."""
import numpy as np
import hashlib
from pathlib import Path

from . import multimarket as m1


def code_digest():
    return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def parameters(history, stat, protocol, team, season):
    par = m1.player_parameters(history, stat, protocol)
    if not protocol.get('role_projection'):
        return par
    current = [r for r in history if r['team_id'] == team and r['date'] >= season[:4] + '-08-01'][-5:]
    prior_minutes = float(np.mean([r['minutes'] for r in history]))
    projected = (5 * prior_minutes + sum(r['minutes'] for r in current)) / (5 + len(current))
    projected = float(np.clip(projected, 1., 48.))
    ratio = projected / max(prior_minutes, 1e-9)
    mean = par['mean'] * ratio
    # A role known from very few games adds uncertainty instead of treating the old minutes as certain.
    extra_variance = mean ** 2 / (len(current) + 5)
    variance = mean + mean ** 2 / par['n'] + extra_variance
    n = max(mean ** 2 / max(variance - mean, 1e-8), 1e-6)
    compatible = [r[stat] for r in history if abs(r['minutes'] - projected) <= max(4., .2 * projected)]
    sample = compatible or par['sample']
    weight = protocol['empirical_weight'] * min(1., len(compatible) / 20)
    return dict(par, mean=mean, n=n, p=n / (n + mean), projected_minutes=projected, sample=sample,
                empirical_weight=weight, current_role_games=len(current), role_projection=True)
