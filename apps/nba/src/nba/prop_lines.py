"""Player lines (points, rebounds, assists) from the shared PropLine archive, read offline and point in time.

The archive is written hourly by qf.ingest.propline_shared, the single network reader for every engine; this module
never calls the provider. A player gets a line only if at least MIN_BOOKS sportsbooks quote the full-game main
Over/Under at a half point; the line is the most common one (ties: nearest the median, then the lower). DFS sites,
exchanges, live, suspended or otherwise flagged quotes never count. The engine uses the line as the threshold of a
statistical forecast; prices are not an input.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import statistics

MARKETS = ('player_points', 'player_rebounds', 'player_assists', 'player_points_rebounds', 'player_points_assists',
           'player_rebounds_assists', 'player_points_rebounds_assists', 'player_threes', 'player_steals', 'player_blocks',
           'player_turnovers', 'player_blocks_steals')
GAME_MARKETS = ('spreads', 'totals')
MIN_BOOKS = 2
MAX_AGE = timedelta(minutes=65)  # hourly capture: the newest observation is at most one cycle old
MATCH_WINDOW = timedelta(hours=3)  # PropLine commence_time vs official tipoff
PATH = '/v1/sports/basketball_nba/odds'


def archive_module():
    """qf.ingest.propline_shared from the repository, or the copy placed beside this package in the image."""
    here = Path(__file__).resolve()
    candidates = [here.with_name('propline_shared.py')]
    if len(here.parents) > 4:
        candidates.append(here.parents[4] / 'src' / 'qf' / 'ingest' / 'propline_shared.py')
    for path in candidates:
        if path.is_file():
            spec = importlib.util.spec_from_file_location('propline_shared', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ValueError('propline_shared.py not available')


def nba_id(value):
    if not isinstance(value, str) or not value.startswith('nba:') or not value[4:].isdigit():
        return None
    return int(value[4:])


def consensus(points):
    """Most common line; ties go to the value nearest the median, then the lower one."""
    counts = Counter(points)
    top = max(counts.values())
    tied = sorted(p for p, c in counts.items() if c == top)
    median = statistics.median(points)
    return min(tied, key=lambda p: (abs(p - median), p))


def book_lines(quotes):
    """(event, market, player) -> {book: point} from usable two-sided main quotes."""
    sides = defaultdict(set)
    for q in quotes:
        # DFS sites missing from the archive's own list still carry their DFS fields (e.g. pick6)
        if (q['market'] not in MARKETS or q['flags'] or q['dfs_odds_type'] or q['payout_multiplier'] is not None
                or q['period'] is not None or q['line_type'] not in (None, 'main')
                or q['name'] not in ('Over', 'Under') or nba_id(q['player_id']) is None or q['point'] is None):
            continue
        point = float(q['point'])
        if (point * 2) % 2 != 1:  # integer lines can push; only half points are a clean over/under
            continue
        sides[(q['event_id'], q['market'], nba_id(q['player_id']), q['bookmaker'], point)].add(q['name'])
    out = defaultdict(dict)
    for (event, market, player, book, point), names in sides.items():
        if names == {'Over', 'Under'}:
            out[(event, market, player)].setdefault(book, set()).add(point)
    # a book quoting two different "main" lines for one player is ambiguous and left out
    return {k: {b: next(iter(p)) for b, p in books.items() if len(p) == 1} for k, books in out.items()}


def lines(root, now, mappings):
    """(lines per NBA game id, receipt summary). lines[game][(market, player_id)] = dict(line, books, book_lines)."""
    if root is None:
        return {}, dict(state='sin_fuente')
    module = archive_module()
    events, receipt = module.newest(root, PATH, now, max_age_seconds=int(MAX_AGE.total_seconds()))
    if receipt is None:
        return {}, dict(state='sin_archivo_reciente')
    by_teams = {}
    for m in mappings:
        by_teams[(m['home_nba_team_id'], m['away_nba_team_id'])] = m
    games = {}
    for e in events:
        m = by_teams.get((nba_id(e.get('home_team_id')), nba_id(e.get('away_team_id'))))
        if m is None:
            continue
        commence = datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00'))
        if abs(commence - datetime.fromisoformat(m['tipoff_utc'])) <= MATCH_WINDOW:
            games[str(e['id'])] = m['nba_game_id']
    out = defaultdict(dict)
    for (event, market, player), books in book_lines(module.quotes([e for e in events if str(e['id']) in games],
                                                                      receipt['received_at'])).items():
        if len(books) >= MIN_BOOKS:
            out[games[event]][(market, player)] = dict(line=consensus(list(books.values())), books=len(books),
                                                       book_lines=dict(sorted(books.items())))
    summary = dict(state='archivo_aplicado', received_at_utc=receipt['received_at'], slot=receipt.get('slot'),
                   sha256=receipt.get('sha256'), component_requests=receipt.get('component_receipts'),
                   events_matched=len(games))
    return dict(out), summary


def game_line_books(quotes):
    """(event, 'spread_home' | 'total') -> {book: point} from usable full-game main lines; spreads keep the home side's point."""
    sides = defaultdict(lambda: defaultdict(set))
    for q in quotes:
        if (q['market'] not in GAME_MARKETS or q['flags'] or q['dfs_odds_type'] or q['payout_multiplier'] is not None
                or q['period'] is not None or q['team'] is not None or q['line_type'] not in (None, 'main') or q['point'] is None):
            continue
        if q['market'] == 'spreads' and q['side'] in ('home', 'away'):
            point = float(q['point']) if q['side'] == 'home' else -float(q['point'])
            sides[(q['event_id'], 'spread_home', q['bookmaker'])][point].add(q['side'])
        elif q['market'] == 'totals' and q['name'] in ('Over', 'Under'):
            sides[(q['event_id'], 'total', q['bookmaker'])][float(q['point'])].add(q['name'])
    out = defaultdict(dict)
    for (event, kind, book), points in sides.items():
        complete = [p for p, names in points.items() if len(names) == 2]
        if len(complete) == 1:  # both sides of exactly one main line
            out[(event, kind)][book] = complete[0]
    return out


def game_lines(root, now, mappings):
    """(game id -> dict(spread_home, total, books), summary): consensus full-game spread (home side) and total at sealing.

    Same archive, freshness and matching rules as the player lines; a value needs MIN_BOOKS sportsbooks."""
    if root is None:
        return {}, dict(state='sin_fuente')
    module = archive_module()
    events, receipt = module.newest(root, PATH, now, max_age_seconds=int(MAX_AGE.total_seconds()))
    if receipt is None:
        return {}, dict(state='sin_archivo_reciente')
    by_teams = {(m['home_nba_team_id'], m['away_nba_team_id']): m for m in mappings}
    games = {}
    for e in events:
        m = by_teams.get((nba_id(e.get('home_team_id')), nba_id(e.get('away_team_id'))))
        if m is None:
            continue
        commence = datetime.fromisoformat(e['commence_time'].replace('Z', '+00:00'))
        if abs(commence - datetime.fromisoformat(m['tipoff_utc'])) <= MATCH_WINDOW:
            games[str(e['id'])] = m['nba_game_id']
    out = defaultdict(dict)
    for (event, kind), books in game_line_books(module.quotes([e for e in events if str(e['id']) in games], receipt['received_at'])).items():
        if len(books) >= MIN_BOOKS:
            out[games[event]][kind] = consensus(list(books.values()))
            out[games[event]].setdefault('books', {})[kind] = len(books)
    return dict(out), dict(state='archivo_aplicado', received_at_utc=receipt['received_at'], events_matched=len(games))
