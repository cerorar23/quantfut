"""Explicit bookmaker versions for research; planning never queries the provider."""
import json
from pathlib import Path
import re

from .context import utc

PROFILE = Path(__file__).with_name('odds_sources.json')
FEATURED = ('h2h', 'spreads', 'totals')
RESEARCH_MARKETS = set(FEATURED) | {'player_points', 'player_rebounds', 'player_assists'}


def source_selection():
    profile = json.loads(PROFILE.read_bytes())
    sources = profile['sources']
    keys = [source['bookmaker_key'] for source in sources]
    if (not 1 <= len(keys) <= 10 or len(keys) != len(set(keys))
            or any(not re.fullmatch(r'[a-z0-9_]+', key) for key in keys)):
        raise ValueError('one explicit group of unique bookmakers required')
    return profile


def selected_request(event_id, *, sport='basketball_nba', kind='markets', markets=None, date=None):
    """Build a bounded request; absence from market discovery is not proof of no coverage."""
    if (not isinstance(event_id, str) or not re.fullmatch(r'[a-f0-9]{32}', event_id)
            or sport not in {'basketball_nba', 'basketball_nba_preseason'}):
        raise ValueError('NBA sport and provider event ID required')
    if kind not in {'markets', 'odds'}:
        raise ValueError('markets discovery or event odds required')
    profile = source_selection()
    parameters = dict(bookmakers=','.join(s['bookmaker_key'] for s in profile['sources']), dateFormat='iso')
    path = f'sports/{sport}/events/{event_id}/{kind}'
    if kind == 'markets':
        if markets is not None or date is not None:
            raise ValueError('current discovery does not accept markets or historical date')
        cost = 1  # Provider documents a fixed one-credit current market-discovery call.
    else:
        selected = FEATURED if markets is None else markets
        if (not isinstance(selected, (list, tuple)) or not 1 <= len(selected) <= 3
                or any(not isinstance(m, str) or m not in RESEARCH_MARKETS for m in selected)
                or len(selected) != len(set(selected))):
            raise ValueError('one to three unique research markets required')
        parameters.update(markets=','.join(selected), oddsFormat='decimal')
        cost = len(selected)  # Four explicitly named books count as one region-equivalent.
        if date is not None:
            parameters['date'] = utc(date).strftime('%Y-%m-%dT%H:%M:%SZ')
            path = 'historical/' + path
            cost *= 10
    return dict(path=path, parameters=parameters, max_cost=cost)


def source_plan(event_id=None, sport='basketball_nba'):
    profile = source_selection()
    result = dict(selection=profile, paid_API_calls=0, requires_explicit_credit_budget=True,
                  next_step='discover_event_markets', actionable=False)
    if event_id is not None:
        result['requests'] = dict(discover=selected_request(event_id, sport=sport),
            featured=selected_request(event_id, sport=sport, kind='odds'))
    else:
        result['requests'] = None
        result['event_id_required'] = True
    return result
