"""Automatic intake for the current engine: API-Tennis fixtures -> strict identity/metadata -> sealed forecast -> results.

Replaces the manual official-PDF review loop that only ever produced 18 events. Rules:
- A fixture is sealed once, by the first run that sees it at least LEAD_MINUTES before its provider start time.
- Players: provider abbreviated name ("D. Snigur") must match exactly one model player of that circuit by surname
  and first initial among players active in the last 400 days; otherwise excluded with the reason.
- Tournament: provider name must match one canonical tournament of that circuit seen in the last 400 days; its
  surface/level give the rules (best of 5 only in men's Grand Slam main draws; 10-point deciding tie-break at Slams).
- Results come from later fixture captures (status Finished/Retired); a result counts only if the forecast was
  sealed before the provider start time. Provider times are estimates, not verified physical times.
"""
import hashlib
import json
import math
import re
import sqlite3
import unicodedata
from datetime import timedelta
from pathlib import Path
import pandas as pd
from tennis_engine.operations import now, utc
from tennis_engine.benchmark import probability_metrics
from tennis_allmarkets_v1.contracts import outcome

TOURS = {'265': 'ATP', '266': 'WTA'}
LEAD_MINUTES = 10
ACTIVE_DAYS = 400
SCHEMA = 'tennis-intake-sealed-v1'


def norm(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c)).casefold()
                    .replace('-', ' ').replace("'", '').replace('.', ' ').split())


def provider_key(name):
    """'D. Snigur' / 'J. M. Cerundolo' / 'A. De Minaur' -> ('snigur', 'd')."""
    m = re.match(r'^((?:[A-Za-z](?:-[A-Za-z])?\.\s*-?)+)\s*(.+)$', str(name).strip())
    if not m:
        return None
    return norm(m.group(2)), norm(m.group(1)).replace(' ', '')[:1]


def canonical_keys(full_name):
    t = norm(full_name).split()
    return {(' '.join(t[k:]), t[0][0]) for k in range(1, len(t))} if len(t) > 1 else set()


class Directory:
    """Players and tournaments recently active in the frozen canonical table."""
    def __init__(self, canonical, as_of):
        cutoff = (pd.Timestamp(as_of).tz_localize(None) - pd.Timedelta(days=ACTIVE_DAYS)).strftime('%Y-%m-%d')
        recent = canonical[canonical.period >= cutoff]
        self.players = {}
        for circuit, group in recent.groupby('circuit'):
            index = {}
            for side in ('winner', 'loser'):
                for pid, name in group[[side + '_id', side + '_name']].drop_duplicates().itertuples(index=False):
                    for key in canonical_keys(name):
                        index.setdefault(key, set()).add(pid)
            self.players[circuit] = index
        t = recent.sort_values('period').groupby(['circuit', 'tourney_name']).agg(surface=('surface', 'last'), level=('tourney_level', 'last'))
        self.tournaments = {(c, norm(n)): row for (c, n), row in t.iterrows()}

    def player(self, circuit, provider_name):
        key = provider_key(provider_name)
        found = self.players.get(circuit, {}).get(key, set()) if key else set()
        if len(found) != 1:
            raise ValueError(f'Player {"ambiguous" if found else "unknown"}: {provider_name}')
        return next(iter(found))

    def tournament(self, circuit, provider_name):
        name = norm(re.sub(r'\s*-\s*Qualification$', '', str(provider_name)))
        name = re.sub(r'\s*\(.*\)$', '', name)
        hits = [v for (c, n), v in self.tournaments.items() if c == circuit and n == name]
        if not hits:
            hits = [v for (c, n), v in self.tournaments.items() if c == circuit and (n.startswith(name + ' ') or name.startswith(n + ' '))]
        if len(hits) != 1:
            raise ValueError(f'Tournament {"ambiguous" if hits else "unknown"}: {provider_name}')
        return hits[0]


def fixtures(capture_root):
    """Latest observation of every singles event across archived API-Tennis fixture responses."""
    events = {}
    for receipt_path in sorted(Path(capture_root).glob('originals/*/receipt.json')):
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt.get('method') != 'get_fixtures' or receipt.get('http_status') != 200 or receipt['params'].get('event_type_key') not in TOURS:
            continue
        body = json.loads(Path(receipt['source_path']).read_text(encoding='utf-8'))
        for e in body.get('result') or []:
            seen = events.get(str(e['event_key']))
            if seen is None or receipt['received_at'] >= seen['received_at']:
                events[str(e['event_key'])] = dict(e, circuit=TOURS[receipt['params']['event_type_key']], received_at=receipt['received_at'],
                                                   receipt_sha256=receipt['sha256'])
    return events


def start_time(e):
    return pd.Timestamp(f"{e['event_date']}T{e['event_time'] or '00:00'}:00", tz='UTC')


def rules_for(e, tour):
    slam = tour.level == 'G'
    qualifying = str(e.get('event_qualification')) == 'True' or 'Qualification' in str(e.get('tournament_name'))
    return dict(surface=tour.surface, best_of=5 if slam and e['circuit'] == 'ATP' and not qualifying else 3, deciding_tiebreak=10 if slam else 7)


class Ledger:
    def __init__(self, root):
        Path(root).mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(Path(root) / 'ledger.sqlite', timeout=30)
        self.db.executescript('''CREATE TABLE IF NOT EXISTS sealed(event_key TEXT PRIMARY KEY, path TEXT, sealed_at TEXT, payload_sha256 TEXT);
            CREATE TABLE IF NOT EXISTS excluded(event_key TEXT, seen_at TEXT, reason TEXT, PRIMARY KEY(event_key, reason));''')
        self.db.execute("CREATE TRIGGER IF NOT EXISTS sealed_immutable BEFORE UPDATE ON sealed BEGIN SELECT RAISE(ABORT,'sealed rows are immutable'); END")
        self.db.execute("CREATE TRIGGER IF NOT EXISTS sealed_nodelete BEFORE DELETE ON sealed BEGIN SELECT RAISE(ABORT,'sealed rows are immutable'); END")
        self.db.commit()

    def sealed(self, key):
        return self.db.execute('SELECT 1 FROM sealed WHERE event_key=?', (key,)).fetchone() is not None


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def seal_new(root, capture_root, motor, clock=now):
    root = Path(root)
    ledger = Ledger(root)
    stamp = clock()
    directory = Directory(motor.canonical, stamp)
    report = dict(run_at=stamp, sealed=[], excluded=[], skipped=0)
    for key, e in sorted(fixtures(capture_root).items()):
        if ledger.sealed(key):
            report['skipped'] += 1
            continue
        if e.get('event_status') not in ('', None) or e.get('first_player_dp1_key') or e.get('second_player_dp1_key'):
            continue  # started/finished/cancelled or doubles
        try:
            begins = start_time(e)
            if utc(stamp) > begins - timedelta(minutes=LEAD_MINUTES):
                raise ValueError('Too close to or past the provider start time')
            a = directory.player(e['circuit'], e['event_first_player'])
            b = directory.player(e['circuit'], e['event_second_player'])
            if a == b:
                raise ValueError('Same canonical player on both sides')
            meta = rules_for(e, directory.tournament(e['circuit'], e['tournament_name']))
            forecast = motor.forecast(e['circuit'], a, b, meta['surface'], begins.isoformat(), meta['best_of'], meta['deciding_tiebreak'])
        except (ValueError, KeyError) as error:
            with ledger.db:
                ledger.db.execute('INSERT OR IGNORE INTO excluded VALUES (?,?,?)', (key, stamp, str(error)))
            report['excluded'].append(dict(event_key=key, reason=str(error)))
            continue
        sealed_at = clock()
        if utc(sealed_at) > begins - timedelta(minutes=LEAD_MINUTES):
            continue
        value = dict(schema=SCHEMA, event_key=key, circuit=e['circuit'], provider_players=[e['event_first_player'], e['event_second_player']],
                     tournament=e['tournament_name'], round=e.get('tournament_round'), provider_start=begins.isoformat(),
                     fixture_received_at=e['received_at'], fixture_receipt_sha256=e['receipt_sha256'], rules=meta,
                     engine_version=motor.config.get('version'), sealed_at=sealed_at, forecast=forecast)
        path = root / 'predictions' / f'{key}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = checksum(value)
        with path.open('x', encoding='utf-8') as handle:
            json.dump(dict(value, payload_sha256=payload), handle, ensure_ascii=False, indent=1)
        with ledger.db:
            ledger.db.execute('INSERT INTO sealed VALUES (?,?,?,?)', (key, str(path), sealed_at, payload))
        report['sealed'].append(dict(event_key=key, players=forecast['players'], winner_a=forecast['winner']['final_winner'], source=forecast['winner']['source']))
    return report


def result_of(e):
    """Completed or retired provider result in the A/B orientation of the fixture."""
    status = e.get('event_status')
    if status not in ('Finished', 'Retired') or e.get('event_winner') not in ('First Player', 'Second Player'):
        return None
    sets = sorted(e.get('scores') or [], key=lambda s: int(s['score_set']))
    score = ' '.join(f"{int(float(s['score_first']))}-{int(float(s['score_second']))}" for s in sets)
    return dict(status='completed' if status == 'Finished' else 'retired', a_won=e['event_winner'] == 'First Player', score_A_B=score,
                completed_sets=len(sets), received_at=e['received_at'])


def evaluate(root, capture_root):
    events = fixtures(capture_root)
    rows = []
    for path in sorted((Path(root) / 'predictions').glob('*.json')):
        v = json.loads(path.read_text(encoding='utf-8'))
        payload = v.pop('payload_sha256')
        if checksum(v) != payload:
            raise ValueError('Sealed forecast changed: ' + path.name)
        r = result_of(events.get(v['event_key'], {}))
        if r is None or not utc(v['sealed_at']) < utc(v['provider_start']):
            continue
        rows.append((v, r))
    report = dict(evaluated_at=now(), sealed=len(list((Path(root) / 'predictions').glob('*.json'))), with_result=len(rows), by_circuit={}, markets={})
    for circuit in ('ATP', 'WTA'):
        sel = [(v, r) for v, r in rows if v['circuit'] == circuit]
        if not sel:
            continue
        y = [int(r['a_won']) for v, r in sel]
        p = [v['forecast']['winner']['final_winner'] for v, r in sel]
        market = [(yy, v['forecast']['winner'].get('market_winner')) for yy, (v, r) in zip(y, sel) if v['forecast']['winner'].get('market_winner')]
        report['by_circuit'][circuit] = dict(winner=dict(probability_metrics(y, p), accuracy=sum((pp > .5) == bool(yy) for yy, pp in zip(y, p)) / len(y)), n_with_market=len(market),
            market_only=probability_metrics([a for a, b in market], [b for a, b in market]) if market else None)
    groups = {}
    for v, r in rows:
        if r['status'] != 'completed':
            continue
        result = dict(status='completed', score_A_B=r['score_A_B'], best_of=v['rules']['best_of'], completed_sets=r['completed_sets'])
        for row in v['forecast']['markets']:
            c = row['contract']
            if c['kind'] == 'correct_score':
                continue
            try:
                o = outcome(c, result)
            except ValueError:
                continue
            if o == 'push':
                continue
            k = json.dumps(c, sort_keys=True)
            win = row['probabilities']['win'] / max(1e-12, 1 - row['probabilities']['push'])
            groups.setdefault(k, []).append((int(o == 'win'), min(max(win, 1e-9), 1 - 1e-9)))
    for k, vals in groups.items():
        ys, ps = [a for a, b in vals], [b for a, b in vals]
        report['markets'][k] = dict(n=len(vals), log_loss=-sum(yy * math.log(pp) + (1 - yy) * math.log(1 - pp) for yy, pp in vals) / len(vals),
                                    accuracy=sum((pp > .5) == bool(yy) for yy, pp in vals) / len(vals))
    return report
