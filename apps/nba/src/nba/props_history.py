"""Historical NBA player-prop odds from The Odds API: plan, capped fetch with disk cache, and load.

One snapshot per game, 30 minutes before its tipoff, from the per-event historical endpoint (the bulk
endpoint does not serve player props). Day event lists cost 1 credit; each game costs 10 x markets x regions.
Every response is written to disk before the next call; the run stops on the first non-200, at the credit cap,
or when the balance would fall below the reserve. `plan` and `load` never touch the network.
"""
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
import gzip
import hashlib
import json
from pathlib import Path

from . import availability as av
from .odds_history import (CREDITS_PER_MARKET_REGION, LEAD, SPORT, TEAM_ALIASES, WEEKDAY_FALLBACK, WEEKEND_FALLBACK,
                           api_time, read_key)

EVENTS = 'https://api.the-odds-api.com/v4/historical/sports/{sport}/events'
EVENT_ODDS = 'https://api.the-odds-api.com/v4/historical/sports/{sport}/events/{event_id}/odds'
MARKETS = ('player_points', 'player_rebounds', 'player_assists', 'player_threes')


def game_cost(markets, regions=1):
    return CREDITS_PER_MARKET_REGION * len(markets) * regions


def plan(games, tips, seasons, markets=MARKETS, regions='us'):
    """One entry per game of `seasons`; the worst-case cost assumes every market returns data."""
    entries = []
    for g in sorted(games, key=lambda g: (g['date'], str(g['game_id']))):
        if g['season'] not in seasons:
            continue
        if g['game_id'] in tips:
            moment, source = tips[g['game_id']] - LEAD, 'tipoff'
        else:
            hour, minute = WEEKEND_FALLBACK if date.fromisoformat(g['date']).weekday() >= 5 else WEEKDAY_FALLBACK
            moment, source = datetime.fromisoformat(g['date']).replace(hour=hour, minute=minute, tzinfo=UTC), 'fallback'
        moment = moment.astimezone(UTC).replace(second=0, microsecond=0)
        entries.append(dict(game_id=str(g['game_id']), day=g['date'], home=g['home']['name'], away=g['away']['name'],
                            time=moment.isoformat(), time_source=source))
    days = len({e['day'] for e in entries})
    per_game = game_cost(markets, len(regions.split(',')))
    return dict(sport=SPORT, markets=list(markets), regions=regions, seasons=sorted(seasons), games=entries,
                credits_per_game=per_game, event_list_credits=days,
                total_credits=per_game * len(entries) + days)


def _day_window(day):
    start = datetime.fromisoformat(day).replace(tzinfo=av.EASTERN)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def _match(events, entries):
    by_key = {}
    for event in events:
        start = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00')).astimezone(av.EASTERN)
        names = (TEAM_ALIASES.get(event['home_team'], event['home_team']),
                 TEAM_ALIASES.get(event['away_team'], event['away_team']))
        by_key[(start.date().isoformat(), *names)] = event['id']
    return {e['game_id']: by_key.get((e['day'], e['home'], e['away'])) for e in entries}


def cached(plan_, cache):
    return [e for e in plan_['games'] if (Path(cache) / 'odds' / (e['game_id'] + '.json')).exists()]


def _write(cache, sub, name, body, manifest_row):
    (cache / sub).mkdir(parents=True, exist_ok=True)
    (cache / sub / name).write_bytes(body)
    with (cache / 'manifest.jsonl').open('a', encoding='utf8') as manifest:
        manifest.write(json.dumps(manifest_row | dict(sha256=hashlib.sha256(body).hexdigest())) + '\n')


def fetch(plan_, cache, key, *, cap, reserve, now, client, limit=None):
    """Pay for missing games in order. Returns a summary; raises nothing on a normal stop."""
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    spent, done, stop, remaining, no_event = 0, 0, None, None, []
    per_game = plan_['credits_per_game']
    pending = [e for e in plan_['games'] if not (cache / 'odds' / (e['game_id'] + '.json')).exists()]
    by_day = defaultdict(list)
    for entry in pending:
        by_day[entry['day']].append(entry)

    def call(url, params, worst):
        nonlocal spent, remaining, stop
        if spent + worst > cap:
            stop = 'cap'
        elif remaining is not None and remaining - worst < reserve:
            stop = 'reserve'
        if stop:
            return None
        response = client.get(url, params=dict(apiKey=key) | params, timeout=60)
        if response.status_code != 200:
            stop = f'http_{response.status_code}'
            return None
        used = int(response.headers.get('x-requests-last', worst))
        remaining = int(response.headers.get('x-requests-remaining', 0))
        spent += used
        if used > worst:
            stop = 'unexpected_cost'
        return response.content, used

    for day, entries in by_day.items():
        if limit is not None and done >= limit:
            break
        events_path = cache / 'events' / (day + '.json')
        if events_path.exists():
            events = json.loads(events_path.read_bytes())['data']
        else:
            start, end = _day_window(day)
            result = call(EVENTS.format(sport=plan_['sport']), dict(
                date=api_time(min(e['time'] for e in entries)), commenceTimeFrom=api_time(start.isoformat()),
                commenceTimeTo=api_time(end.isoformat())), 1)
            if result is None:
                break
            body, used = result
            _write(cache, 'events', day + '.json', body, dict(kind='events', day=day, credits=used, remaining=remaining,
                                                                 received_at_utc=now.isoformat()))
            events = json.loads(body)['data']
            if stop:
                break
        ids = _match(events, entries)
        for entry in entries:
            if limit is not None and done >= limit:
                break
            event_id = ids[entry['game_id']]
            if event_id is None:
                no_event.append(entry['game_id'])
                continue
            result = call(EVENT_ODDS.format(sport=plan_['sport'], event_id=event_id), dict(
                regions=plan_['regions'], markets=','.join(plan_['markets']), oddsFormat='decimal',
                date=api_time(entry['time'])), per_game)
            if result is None:
                break
            body, used = result
            _write(cache, 'odds', entry['game_id'] + '.json', body,
                   dict(kind='odds', game_id=entry['game_id'], event_id=event_id, credits=used, remaining=remaining,
                        received_at_utc=now.isoformat()))
            done += 1
            if stop:
                break
        if stop:
            break
    return dict(fetched=done, pending_before=len(pending), credits_spent=spent, remaining=remaining, stop=stop,
                no_event=no_event)


def load(plan_, cache):
    """Cached games -> one row per (book, market, player, line) with over/under prices; no network, no credits."""
    rows, stats = [], defaultdict(int)
    for entry in plan_['games']:
        path = Path(cache) / 'odds' / (entry['game_id'] + '.json')
        if not path.exists():
            stats['missing_game'] += 1
            continue
        body = json.loads(path.read_bytes())
        snapshot = datetime.fromisoformat(body['timestamp'].replace('Z', '+00:00'))
        event = body.get('data') or {}
        start = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00')) if event else None
        if not event.get('bookmakers') or start <= snapshot:
            stats['no_prices' if not event.get('bookmakers') else 'already_started'] += 1
            continue
        stats['games'] += 1
        for book in event['bookmakers']:
            for market in book['markets']:
                lines = defaultdict(dict)
                for outcome in market['outcomes']:
                    lines[(outcome['description'], outcome.get('point'))][outcome['name'].lower()] = outcome['price']
                for (player, point), sides in lines.items():
                    if point is None or not {'over', 'under'} <= sides.keys():
                        stats['one_sided_line'] += 1
                        continue
                    rows.append(dict(game_id=entry['game_id'], snapshot_utc=snapshot.isoformat(),
                                     minutes_to_tipoff=(start - snapshot).total_seconds() / 60, book=book['key'],
                                     market=market['key'], player=player, line=point, over=sides['over'],
                                     under=sides['under'], book_updated_utc=market.get('last_update') or book['last_update']))
    stats['rows'] = len(rows)
    return rows, dict(stats)


def main():
    import argparse
    import httpx
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'fetch', 'load'])
    parser.add_argument('--data', required=True, help='dir with games.json (RUN071 data)')
    parser.add_argument('--api-dir', required=True)
    parser.add_argument('--cache', required=True)
    parser.add_argument('--plan-file', required=True)
    parser.add_argument('--seasons', nargs='+', default=['2024-25', '2025-26'])
    parser.add_argument('--markets', nargs='+', default=list(MARKETS))
    parser.add_argument('--regions', default='us')
    parser.add_argument('--injuries', help='injury reports whose rows carry tipoff times')
    parser.add_argument('--key-file', type=Path)
    parser.add_argument('--cap', type=int, default=99000, help='maximum credits to spend in this run')
    parser.add_argument('--reserve', type=int, default=300, help='stop if the balance would drop below this')
    parser.add_argument('--limit', type=int, help='maximum games to fetch in this run')
    parser.add_argument('--output', type=Path)
    a = parser.parse_args()
    games = json.loads((Path(a.data) / 'games.json').read_bytes())
    if a.command == 'plan':
        tips = av.tipoff_map(a.api_dir, games)
        if a.injuries:
            for report in av.read_reports(a.injuries):
                for row in report['rows']:
                    if row.get('nba_game_id') and row.get('game_tipoff_utc'):
                        tips.setdefault(row['nba_game_id'], datetime.fromisoformat(row['game_tipoff_utc']))
        result = plan(games, tips, set(a.seasons), tuple(a.markets), a.regions)
        Path(a.plan_file).write_text(json.dumps(result, indent=1), encoding='utf8')
        print(json.dumps({k: v for k, v in result.items() if k != 'games'} | dict(
            games=len(result['games']), already_cached=len(cached(result, a.cache)),
            fallback=sum(e['time_source'] == 'fallback' for e in result['games']))))
        return
    result = json.loads(Path(a.plan_file).read_bytes())
    if a.command == 'fetch':
        if not a.key_file:
            parser.error('--key-file is required')
        with httpx.Client() as client:
            print(json.dumps(fetch(result, a.cache, read_key(a.key_file), cap=a.cap, reserve=a.reserve,
                                   now=datetime.now(UTC), client=client, limit=a.limit)))
        return
    rows, stats = load(result, a.cache)
    if a.output:
        with gzip.open(a.output, 'wt', encoding='utf8') as stream:
            stream.writelines(json.dumps(r) + '\n' for r in rows)
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
