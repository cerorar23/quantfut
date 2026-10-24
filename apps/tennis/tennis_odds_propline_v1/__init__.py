"""Pre-match winner market from the shared PropLine archive, read offline and point in time.

Owner decision (2026-10-23): PropLine is the single odds source; one hourly capture (qf.ingest.propline_shared) serves
every engine, so this module never calls the provider and The Odds API is not a fallback. Same return shape as
tennis_odds_live_v1.latest_market, which stays untouched because frozen protocols hash its code.

Only the newest archived observation received at or before `before` counts (at most one hourly cycle old); a pair
that observation does not quote has no market. Full-game main-line h2h only, two outcomes per book; flagged quotes
(live, suspended, DFS, exchanges) and started matches are already dropped by `two_way_feed`.
"""
import importlib.util
from pathlib import Path
from tennis_engine.operations import utc
from tennis_odds_live_v1 import devigged, norm

SPORT = 'tennis'
MAX_AGE_SECONDS = 3900


def archive_module():
    """qf.ingest.propline_shared from the repository, or the copy placed at the image root (/app)."""
    here = Path(__file__).resolve()
    candidates = [here.parents[1] / 'propline_shared.py']
    if len(here.parents) > 3:
        candidates.append(here.parents[3] / 'src' / 'qf' / 'ingest' / 'propline_shared.py')
    for path in candidates:
        if path.is_file():
            spec = importlib.util.spec_from_file_location('propline_shared', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ValueError('propline_shared.py not available')


def latest_market(root, player_a, player_b, before, max_age_seconds=MAX_AGE_SECONDS):
    events, receipt = archive_module().read_two_way(root, SPORT, utc(before),max_age_seconds=max_age_seconds)
    if receipt is None:
        return None
    best = None
    for event in events:
        if {norm(event.get('home_team')), norm(event.get('away_team'))} != {norm(player_a), norm(player_b)}:
            continue
        if not utc(receipt['received_at']) < utc(event['commence_time']):
            continue
        p, books = devigged(event, player_a, player_b)
        # The same pair twice in one observation is ambiguous (two listings): no market rather than a guess.
        if p is not None:
            if best is not None:
                return None
            best = dict(probability_a=p, bookmakers=books, received_at=receipt['received_at'], snapshot_id=receipt['sha256'],
                        request_id=receipt['request_id'], event_id=event['id'], commence_time=event['commence_time'], provider='propline')
    return best
