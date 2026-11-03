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


def same_player(x, y):
    """Same normalised name, or the same first and last name where one side only adds middle names (PropLine listed
    'Leylah Annie Fernandez' for 'Leylah Fernandez' on 27-oct-2026 and the match was sealed without a price).
    Never a similarity guess: compound surnames ('Sorribes Tormo' against 'Sorribes') still do not match."""
    x, y = norm(x or '').split(), norm(y or '').split()
    if x == y:
        return bool(x)
    short, long = sorted((x, y), key=len)
    if len(short) < 2 or len(short) == len(long) or short[0] != long[0] or short[-1] != long[-1]:
        return False
    middle = iter(long[1:-1])
    return all(token in middle for token in short[1:-1])


def side_of(name, player_a, player_b):
    """'A' or 'B' when the name is exactly one of the two players; None otherwise (unknown or both)."""
    sides = [s for s, p in (('A', player_a), ('B', player_b)) if same_player(name, p)]
    return sides[0] if len(sides) == 1 else None


def provider_pair(event, player_a, player_b):
    """The provider's own spelling of (player A, player B) when the listing is exactly this pair; None otherwise."""
    home, away = event.get('home_team'), event.get('away_team')
    if side_of(home, player_a, player_b) == 'A' and side_of(away, player_a, player_b) == 'B':
        return home, away
    if side_of(home, player_a, player_b) == 'B' and side_of(away, player_a, player_b) == 'A':
        return away, home
    return None


def latest_market(root, player_a, player_b, before, max_age_seconds=MAX_AGE_SECONDS):
    events, receipt = archive_module().read_two_way(root, SPORT, utc(before),max_age_seconds=max_age_seconds)
    if receipt is None:
        return None
    best = None
    for event in events:
        names = provider_pair(event, player_a, player_b)
        if names is None or not utc(receipt['received_at']) < utc(event['commence_time']):
            continue
        p, books = devigged(event, *names)
        # The same pair twice in one observation is ambiguous (two listings): no market rather than a guess.
        if p is not None:
            if best is not None:
                return None
            best = dict(probability_a=p, bookmakers=books, received_at=receipt['received_at'], snapshot_id=receipt['sha256'],
                        request_id=receipt['request_id'], event_id=event['id'], commence_time=event['commence_time'], provider='propline')
    return best


# PropLine (market, period) -> engine contract family. Period 'sN' is set N; full-match rows have no period.
FAMILIES = {('h2h', None): 'winner', ('spreads', None): 'games_handicap', ('totals', None): 'games_total',
            ('total_games', None): 'games_total', ('total_sets', None): 'sets_total', ('set_spread', None): 'sets_handicap',
            ('total_tiebreaks', None): 'tiebreak', ('h2h', 's'): 'set_winner', ('spreads', 's'): 'set_games_handicap',
            ('totals', 's'): 'set_games_total', ('player_games_won', None): 'player_games'}


def family(market, period):
    if period is None:
        return FAMILIES.get((market, None)), None
    if isinstance(period, str) and len(period) == 2 and period[0] == 's' and period[1].isdigit():
        return FAMILIES.get((market, 's')), int(period[1])
    return None, None


def consensus(rows, player_a, player_b):
    """Margin-free probability per engine contract from quote rows (market, period, name, description, point, bookmaker,
    price).

    Each book contributes one two-way pair at an identical line (Over/Under at the same total, A at +x with B at -x);
    the contract probability is the mean over books. Games won by a player is Over/Under with the player in
    `description`. Unpaired sides, unknown names and unsupported markets are counted, never filled in.
    """
    pairs, skipped = {}, 0
    for r in rows:
        kind, number = family(r['market'], r['period'])
        price, name = r['price'], norm(r['name'] or '')
        if kind is None or price is None or price <= 1:
            skipped += 1
            continue
        point = r['point']
        if kind == 'player_games':
            who = side_of(r.get('description'), player_a, player_b)
            if who is None or name not in ('over', 'under') or point is None:
                skipped += 1
                continue
            pairs.setdefault((kind, who, point, r['bookmaker']), {})[name] = price
        elif kind in ('winner', 'set_winner', 'games_handicap', 'set_games_handicap', 'sets_handicap'):
            who = side_of(r['name'], player_a, player_b)
            if who is None or (kind in ('winner', 'set_winner')) != (point is None):
                skipped += 1
                continue
            line = None if point is None else (point if who == 'A' else -point)
            pairs.setdefault((kind, number, line, r['bookmaker']), {})[who] = price
        else:
            if name not in ('over', 'under') or point is None or (kind == 'tiebreak' and point != 0.5):
                skipped += 1
                continue
            pairs.setdefault((kind, number, None if kind == 'tiebreak' else point, r['bookmaker']), {})[name] = price
    values = {}
    for (kind, number, line, book), sides in pairs.items():
        first, second = ('A', 'B') if 'A' in sides or 'B' in sides else ('over', 'under')
        if first in sides and second in sides:
            values.setdefault((kind, number, line), []).append((1 / sides[first]) / (1 / sides[first] + 1 / sides[second]))
    out = []
    # For player games the second key is the player ('A'/'B'), not a set number.
    for (kind, number, line), ps in sorted(values.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0, kv[0][2] if kv[0][2] is not None else 0)):
        if kind == 'player_games':
            contract = dict(kind=kind, selection='over', line=line, set_number=None, score=None, player=number)
        else:
            selection = 'yes' if kind == 'tiebreak' else 'over' if 'total' in kind else 'A'
            contract = dict(kind=kind, selection=selection, line=line, set_number=number, score=None)
        out.append(dict(contract=contract, market=sum(ps) / len(ps), books=len(ps)))
    return out, skipped


def market_board(root, player_a, player_b, before, max_age_seconds=MAX_AGE_SECONDS):
    """Every pre-match tennis market the newest archived observation quotes for this pair, as engine contracts."""
    module = archive_module()
    events, receipt = module.newest(root, f'/v1/sports/{SPORT}/odds', utc(before), max_age_seconds=max_age_seconds)
    if receipt is None:
        return None
    found = [e for e in events if provider_pair(e, player_a, player_b) and utc(receipt['received_at']) < utc(e['commence_time'])]
    if len(found) != 1:
        return None  # absent, or two listings of the same pair: no guess
    rows = [dict(market=q['market'], period=q['period'], name=q['name'], description=q['description'], point=q['point'],
                 bookmaker=q['bookmaker'], price=q['price_decimal'])
            for q in module.quotes(found, receipt['received_at'])
            if not q['flags'] and q['team'] is None and q['player_id'] is None]
    board, skipped = consensus(rows, player_a, player_b)
    return dict(provider='propline', event_id=found[0]['id'], commence_time=found[0]['commence_time'], received_at=receipt['received_at'],
                snapshot_id=receipt['sha256'], rows=board, unsupported_quotes=skipped)


def closing_board(root, event_id, player_a, player_b, as_of):
    """Provider closing line (last price before the start) per engine contract; None until it is archived."""
    module = archive_module()
    rows, receipt = module.read_closing(root, SPORT, event_id, utc(as_of))
    if receipt is None:
        return None
    usable = [dict(market=r['market'], period=r['period'], name=r['name'], description=r['description'], point=r['point'],
                   bookmaker=r['bookmaker'], price=r['price_decimal'])
              for r in rows if not r['flags'] and r['team'] is None and r['player_id'] is None]
    board, _ = consensus(usable, player_a, player_b)
    return dict(received_at=receipt['received_at'], rows=board)
