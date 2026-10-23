"""Historical NBA game odds from The Odds API: plan, capped fetch with disk cache, and load.

Spends shared provider credits, so: nothing runs before NOT_BEFORE, every response is written to
disk before the next call, the run stops on the first error, at the credit cap, or when the account
balance would fall below the reserve. `plan` and `load` never touch the network.
"""
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
import gzip
import hashlib
import json
import math
from pathlib import Path
import re

from . import availability as av

NOT_BEFORE = datetime(2026, 11, 1, tzinfo=UTC)
SPORT = 'basketball_nba'
ENDPOINT = 'https://api.the-odds-api.com/v4/historical/sports/{sport}/odds'
CREDITS_PER_MARKET_REGION = 10
LEAD = timedelta(minutes=30)
WEEKEND_FALLBACK, WEEKDAY_FALLBACK = (16, 30), (22, 30)
MAX_PRICE_AGE = timedelta(hours=6)
# The provider's spelling of the one team whose name differs from games.json (checked against its 30 NBA names on 2026-10-21).
TEAM_ALIASES = {'Los Angeles Clippers': 'LA Clippers'}


def api_time(value):
    """The historical endpoint rejects `+00:00` (HTTP 422 INVALID_HISTORICAL_TIMESTAMP); it wants YYYY-MM-DDTHH:MM:SSZ."""
    return datetime.fromisoformat(value).astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def snapshot_cost(markets, regions=1):
    return CREDITS_PER_MARKET_REGION * len(markets) * regions


def slot_name(moment):
    return moment.strftime('%Y%m%dT%H%MZ')


def plan(games, tips, seasons, markets=('h2h',)):
    """One snapshot per Eastern game day: 30 minutes before that day's earliest known tipoff.

    Days without a known tipoff use a fixed time (weekend 16:30Z, otherwise 22:30Z)."""
    days = defaultdict(list)
    for g in games:
        if g['season'] in seasons:
            days[g['date']].append(g['game_id'])
    slots = []
    for day in sorted(days):
        known = [tips[i] for i in days[day] if i in tips]
        if known:
            moment, source = min(known) - LEAD, 'tipoff'
        else:
            hour, minute = WEEKEND_FALLBACK if date.fromisoformat(day).weekday() >= 5 else WEEKDAY_FALLBACK
            moment, source = datetime.fromisoformat(day).replace(hour=hour, minute=minute, tzinfo=UTC), 'fallback'
        moment = moment.astimezone(UTC).replace(second=0, microsecond=0)
        slots.append(dict(day=day, time=moment.isoformat(), name=slot_name(moment), time_source=source,
                          games=len(days[day])))
    cost = snapshot_cost(markets)
    return dict(sport=SPORT, markets=list(markets), regions='eu', seasons=sorted(seasons), slots=slots,
                credits_per_snapshot=cost, total_credits=cost * len(slots))


def cached(plan_, cache):
    return [s for s in plan_['slots'] if (Path(cache) / (s['name'] + '.json')).exists()]


def fetch(plan_, cache, key, *, cap, reserve, now, client, limit=None):
    """Pay for missing snapshots in order. Returns a summary; raises nothing on a normal stop."""
    if now < NOT_BEFORE:
        raise PermissionError(f'historical purchase is blocked before {NOT_BEFORE.date()} (football credit reserve)')
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    spent, done, stop, remaining = 0, 0, None, None
    pending = [s for s in plan_['slots'] if not (cache / (s['name'] + '.json')).exists()]
    for slot in pending[:limit]:
        cost = plan_['credits_per_snapshot']
        if spent + cost > cap:
            stop = 'cap'
            break
        if remaining is not None and remaining - cost < reserve:
            stop = 'reserve'
            break
        response = client.get(ENDPOINT.format(sport=plan_['sport']), params=dict(
            apiKey=key, regions=plan_['regions'], markets=','.join(plan_['markets']), oddsFormat='decimal',
            date=api_time(slot['time'])), timeout=60)
        if response.status_code != 200:
            stop = f'http_{response.status_code}'
            break
        body = response.content
        (cache / (slot['name'] + '.json')).write_bytes(body)
        used = int(response.headers.get('x-requests-last', cost))
        remaining = int(response.headers.get('x-requests-remaining', 0))
        spent += used
        done += 1
        with (cache / 'manifest.jsonl').open('a', encoding='utf8') as manifest:
            manifest.write(json.dumps(dict(slot=slot['name'], sha256=hashlib.sha256(body).hexdigest(),
                                           credits=used, remaining=remaining, received_at_utc=now.isoformat())) + '\n')
        if used != cost:
            stop = 'unexpected_cost'
            break
    return dict(fetched=done, pending_before=len(pending), credits_spent=spent, remaining=remaining, stop=stop)


def read_key(path):
    match = re.search(r'^ODDS_API_KEY\s*=\s*(.+)$', Path(path).read_text(encoding='utf-8-sig'), re.M)
    if not match:
        raise ValueError('ODDS_API_KEY not found')
    return match.group(1).strip().strip('"\'')


def power_no_vig(home, away):
    """Home win probability when the margin is removed with the power method: (1/h)^k + (1/a)^k = 1.

    Unlike the proportional split it puts more of the margin on the longshot; used only as a sensitivity check."""
    inv_h, inv_a = 1 / home, 1 / away
    low, high = 1., 50.
    for _ in range(80):
        k = (low + high) / 2
        if inv_h ** k + inv_a ** k > 1:
            low = k
        else:
            high = k
    return inv_h ** ((low + high) / 2)


def pinnacle_prices(event, market='h2h'):
    for book in event.get('bookmakers', []):
        if book.get('key') != 'pinnacle':
            continue
        for item in book.get('markets', []):
            if item.get('key') == market:
                return book, item
    return None, None


def load(plan_, cache, games):
    """Cached snapshots -> one Pinnacle h2h row per matched game; no network, no credits."""
    by_key = {(g['date'], g['home']['name'], g['away']['name']): g['game_id'] for g in games}
    rows, stats = {}, defaultdict(int)
    for slot in plan_['slots']:
        path = Path(cache) / (slot['name'] + '.json')
        if not path.exists():
            stats['missing_snapshot'] += 1
            continue
        body = json.loads(path.read_bytes())
        snapshot = datetime.fromisoformat(body['timestamp'].replace('Z', '+00:00'))
        for event in body.get('data', []):
            start = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
            if start <= snapshot:
                stats['already_started'] += 1
                continue
            if start.astimezone(av.EASTERN).date() != snapshot.astimezone(av.EASTERN).date():
                # snapshots list later days too; a price taken the evening before is not the price the plan paid for
                stats['snapshot_other_day'] += 1
                continue
            home_name, away_name = (TEAM_ALIASES.get(event[k], event[k]) for k in ('home_team', 'away_team'))
            game = by_key.get((start.astimezone(av.EASTERN).date().isoformat(), home_name, away_name))
            if game is None:
                stats['unmatched_event'] += 1
                continue
            book, market = pinnacle_prices(event)
            if market is None:
                stats['no_pinnacle'] += 1
                continue
            updated = datetime.fromisoformat((market.get('last_update') or book['last_update']).replace('Z', '+00:00'))
            prices = {TEAM_ALIASES.get(o['name'], o['name']): o['price'] for o in market['outcomes']}
            home, away = prices.get(home_name), prices.get(away_name)
            if (not home or not away or not all(map(math.isfinite, (home, away))) or home <= 1 or away <= 1
                    or updated > snapshot or snapshot - updated > MAX_PRICE_AGE):
                stats['invalid_or_stale_price'] += 1
                continue
            inv_h, inv_a = 1 / home, 1 / away
            row = dict(game_id=game, snapshot_utc=snapshot.isoformat(), book_updated_utc=updated.isoformat(),
                       minutes_to_tipoff=(start - snapshot).total_seconds() / 60, home_decimal=home, away_decimal=away,
                       overround=inv_h + inv_a - 1, home_no_vig=inv_h / (inv_h + inv_a),
                       home_no_vig_power=power_no_vig(home, away))
            if game not in rows or snapshot > datetime.fromisoformat(rows[game]['snapshot_utc']):
                rows[game] = row
            stats['matched'] += 1
    return sorted(rows.values(), key=lambda r: r['game_id']), dict(stats)


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
    parser.add_argument('--markets', nargs='+', default=['h2h'])
    parser.add_argument('--injuries', help='injury reports whose rows carry tipoff times (fills days the API lacks)')
    parser.add_argument('--key-file', type=Path)
    parser.add_argument('--cap', type=int, default=3300, help='maximum credits to spend in this run')
    parser.add_argument('--reserve', type=int, default=14500, help='stop if the balance would drop below this')
    parser.add_argument('--limit', type=int)
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
        result = plan(games, tips, set(a.seasons), tuple(a.markets))
        Path(a.plan_file).write_text(json.dumps(result, indent=1), encoding='utf8')
        print(json.dumps({k: v for k, v in result.items() if k != 'slots'} | dict(snapshots=len(result['slots']),
              already_cached=len(cached(result, a.cache)), fallback_days=sum(s['time_source'] == 'fallback' for s in result['slots']))))
        return
    result = json.loads(Path(a.plan_file).read_bytes())
    if a.command == 'fetch':
        if not a.key_file:
            parser.error('--key-file is required')
        with httpx.Client() as client:
            print(json.dumps(fetch(result, a.cache, read_key(a.key_file), cap=a.cap, reserve=a.reserve,
                                   now=datetime.now(UTC), client=client, limit=a.limit)))
        return
    rows, stats = load(result, a.cache, games)
    if a.output:
        with gzip.open(a.output, 'wt', encoding='utf8') as stream:
            stream.writelines(json.dumps(r) + '\n' for r in rows)
    print(json.dumps(dict(rows=len(rows), **stats)))


if __name__ == '__main__':
    main()
