"""Pre-match winner odds from The Odds API: h2h only, one region, at most two snapshots per tournament per UTC day.

Owner authorization (2026-10-19): h2h, one region, two snapshots/day per active tournament, 400 credits/month.
The account is shared with the football product, so a paid call is also refused when it would leave fewer
credits than FOOTBALL_PER_DAY x days until the monthly reset (day 1). The free /sports call refreshes the
balance first. Each original response is archived with its receipt by the existing Capture ledger.
"""
import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from tennis_engine.operations import Capture, now, utc

MONTHLY_CAP = 400
REGION = 'eu'
FOOTBALL_PER_DAY = 350
SLOTS = (('AM', 0), ('PM', 12))


def slot_of(stamp):
    t = utc(stamp)
    return t.strftime('%Y-%m-%d'), 'AM' if t.hour < 12 else 'PM'


def football_reserve(stamp, per_day=FOOTBALL_PER_DAY):
    t = utc(stamp)
    reset = datetime(t.year + (t.month == 12), t.month % 12 + 1, 1, tzinfo=timezone.utc)
    return per_day * max(1, (reset - t).days + 1)


class SlotStore:
    def __init__(self, root):
        Path(root).mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(Path(root) / 'slots.sqlite', timeout=30)
        self.db.execute('CREATE TABLE IF NOT EXISTS slots(sport_key TEXT, day TEXT, slot TEXT, snapshot_id TEXT, taken_at TEXT,'
                        ' PRIMARY KEY(sport_key, day, slot))')
        self.db.commit()

    def taken(self, sport_key, day, slot):
        return self.db.execute('SELECT 1 FROM slots WHERE sport_key=? AND day=? AND slot=?', (sport_key, day, slot)).fetchone() is not None

    def take(self, sport_key, day, slot, snapshot_id, stamp):
        with self.db:
            self.db.execute('INSERT INTO slots VALUES (?,?,?,?,?)', (sport_key, day, slot, snapshot_id, stamp))


def run(root, api_key, transport=None, clock=now, monthly_cap=MONTHLY_CAP, per_day=FOOTBALL_PER_DAY):
    root = Path(root)
    client = Capture(root / 'ledger', api_key, cap=monthly_cap, account_reserve=0, transport=transport, clock=clock)
    store = SlotStore(root)
    stamp = clock()
    day, slot = slot_of(stamp)
    report = dict(schema='tennis-live-odds-run-v1', started_at=stamp, day=day, slot=slot, region=REGION, market='h2h',
                  monthly_cap=monthly_cap, captured=[], skipped=[], blocked=None)
    sports, _ = client.request('sports')  # free; refreshes the shared balance
    client.reserve = football_reserve(stamp, per_day)
    report.update(account_remaining=client.remaining, football_reserve=client.reserve)
    active = sorted(s['key'] for s in sports if s.get('group') == 'Tennis' and s.get('active') and re.match(r'tennis_(atp|wta)_', s['key']))
    report['active_tournaments'] = active
    for key in active:
        if store.taken(key, day, slot):
            report['skipped'].append(dict(sport_key=key, reason='slot already captured'))
            continue
        try:
            events, receipt = client.request(f'sports/{key}/odds', dict(regions=REGION, markets='h2h', oddsFormat='decimal', dateFormat='iso'))
        except ValueError as error:
            report['blocked'] = dict(sport_key=key, reason=str(error))
            break
        store.take(key, day, slot, receipt['snapshot_id'], receipt['received_at'])
        report['captured'].append(dict(sport_key=key, snapshot_id=receipt['snapshot_id'], events=len(events), credits=receipt['headers'].get('x-requests-last')))
    report['budget'] = client.budget_report(stamp[:7])
    out = root / 'runs' / (stamp.replace(':', '').replace('+', '_') + '.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def norm(name):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(name)) if not unicodedata.combining(c)).casefold().replace('-', ' ').split())


def devigged(event, home, away):
    """Mean of per-bookmaker margin-free probabilities that `home` beats `away`; None without a usable quote."""
    values = []
    for book in event.get('bookmakers', []):
        for market in book.get('markets', []):
            if market.get('key') != 'h2h':
                continue
            prices = {norm(o['name']): o['price'] for o in market.get('outcomes', [])}
            a, b = prices.get(norm(home)), prices.get(norm(away))
            if a and b and a > 1 and b > 1 and len(prices) == 2:
                values.append((1 / a) / (1 / a + 1 / b))
    return (sum(values) / len(values), len(values)) if values else (None, 0)


def latest_market(root, player_a, player_b, before, max_age_hours=36):
    """Latest archived snapshot strictly before `before` that quotes this exact pair (either orientation)."""
    best = None
    for receipt_path in (Path(root) / 'ledger' / 'snapshots').glob('*/receipt.json'):
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if not receipt['path'].endswith('/odds') or not utc(receipt['received_at']) < utc(before):
            continue
        if (utc(before) - utc(receipt['received_at'])).total_seconds() > max_age_hours * 3600:
            continue
        for event in json.loads((receipt_path.parent / 'response.json').read_text(encoding='utf-8')):
            names = {norm(event.get('home_team')), norm(event.get('away_team'))}
            if names != {norm(player_a), norm(player_b)} or not utc(receipt['received_at']) < utc(event['commence_time']):
                continue
            p, books = devigged(event, player_a, player_b)
            if p is not None and (best is None or receipt['received_at'] > best['received_at']):
                best = dict(probability_a=p, bookmakers=books, received_at=receipt['received_at'], snapshot_id=receipt['snapshot_id'],
                            event_id=event['id'], commence_time=event['commence_time'])
    return best
