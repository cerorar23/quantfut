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
SEAL_AHEAD_MINUTES = 150  # hourly runs at :25 seal each fixture 1.5-2.5 h before its start
RETRY_MINUTES = 60  # without a market price, wait for the next hourly run while one is still due before the start
ACTIVE_DAYS = 400
SCHEMA = 'tennis-intake-sealed-v1'


def norm(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(s)) if not unicodedata.combining(c)).casefold()
                    .replace('-', ' ').replace("'", '').replace('.', ' ').split())


def provider_initials(name):
    """('snigur', 'd') for 'D. Snigur'; ('wang', 'xin') for 'Xin. Wang'; None when the name has no leading initials."""
    m = re.match(r'^((?:[A-Za-z]+(?:-[A-Za-z]+)?\.\s*-?)+)\s*(.+)$', str(name).strip())
    if not m:
        return None
    return norm(m.group(2)), norm(m.group(1)).replace(' ', '')


def provider_key(name):
    """'D. Snigur' / 'J. M. Cerundolo' / 'A. De Minaur' / 'Xin. Wang' -> (surname, first initial)."""
    parsed = provider_initials(name)
    return (parsed[0], parsed[1][:1]) if parsed else None


def level_class(level):
    """Tour-level events versus Challengers: the class used to separate namesakes such as two B. Nakashima."""
    return 'challenger' if str(level) == 'C' else 'tour'


def day_distance(a, b):
    """Days between two dates ignoring the year (editions of a tournament recur at the same time of year)."""
    d = abs(pd.Timestamp(a).dayofyear - pd.Timestamp(b).dayofyear)
    return min(d, 365 - d)


def canonical_keys(full_name):
    t = norm(full_name).split()
    return {(' '.join(t[k:]), t[0][0]) for k in range(1, len(t))} if len(t) > 1 else set()


class Directory:
    """Players and tournaments recently active in the frozen canonical table."""
    def __init__(self, canonical, as_of):
        cutoff = (pd.Timestamp(as_of).tz_localize(None) - pd.Timedelta(days=ACTIVE_DAYS)).strftime('%Y-%m-%d')
        recent = canonical[canonical.period >= cutoff]
        self.players, self.names, self.levels = {}, {}, {}
        for circuit, group in recent.groupby('circuit'):
            index = {}
            for side in ('winner', 'loser'):
                for pid, name, level in group[[side + '_id', side + '_name', 'tourney_level']].drop_duplicates().itertuples(index=False):
                    for key in canonical_keys(name):
                        index.setdefault(key, set()).add(pid)
                    self.names.setdefault(pid, set()).add(norm(name))
                    self.levels.setdefault(pid, set()).add(level_class(level))
            self.players[circuit] = index
        # Every edition, not just the latest: one name can cover a May clay ATP 250 and an October indoor Challenger.
        edition = recent['tourney_date'] if 'tourney_date' in recent.columns else recent['period']
        editions = recent.assign(edition=edition).groupby(['circuit', 'tourney_name', 'edition'], sort=False).agg(
            period=('period', 'min'), surface=('surface', 'last'), level=('tourney_level', 'last')).reset_index()
        self.editions = {}
        for row in editions.itertuples(index=False):
            self.editions.setdefault((row.circuit, norm(row.tourney_name)), []).append(row)

    def player(self, circuit, provider_name, level=None):
        parsed = provider_initials(provider_name)
        index = self.players.get(circuit, {})
        found = index.get((parsed[0], parsed[1][:1]), set()) if parsed else set()
        if not found and parsed and ' ' in parsed[0]:
            # 'D. Merida Aguilar' with both surnames where the data keeps only the first ('Daniel Merida').
            found = index.get((parsed[0].split()[0], parsed[1][:1]), set())
        if len(found) > 1 and len(parsed[1]) > 1:
            # 'Xin. Wang': a written-out first-name prefix separates Xinyu from Xiyu.
            prefix = [p for p in found if any(n.replace(' ', '').startswith(parsed[1]) for n in self.names[p])]
            found = set(prefix) if prefix else found
        if len(found) > 1 and level is not None:
            same = [p for p in found if level_class(level) in self.levels.get(p, ())]
            found = set(same) if len(same) == 1 else found
        if len(found) != 1:
            raise ValueError(f'Player {"ambiguous" if found else "unknown"}: {provider_name}')
        return next(iter(found))

    def tournament(self, circuit, provider_name, when=None):
        """Edition with the same name held closest to `when` in the calendar (within 30 days); latest edition if no date."""
        name = norm(re.sub(r'\s*-\s*Qualification$', '', str(provider_name)))
        name = re.sub(r'\s*\(.*\)$', '', name)
        exact = [k for k in self.editions if k[0] == circuit and k[1] == name]
        prefix = [k for k in self.editions if k[0] == circuit and (k[1].startswith(name + ' ') or name.startswith(k[1] + ' '))]
        if when is None:
            keys = exact or prefix
            if len(keys) != 1:
                raise ValueError(f'Tournament {"ambiguous" if keys else "unknown"}: {provider_name}')
            return max(self.editions[keys[0]], key=lambda e: e.period)
        editions = [e for k in exact for e in self.editions[k]]
        if not editions or min(day_distance(e.period, when) for e in editions) > 30:
            editions += [e for k in prefix for e in self.editions[k]]  # exact name only when it was held at this time of year
        if not editions:
            raise ValueError(f'Tournament unknown: {provider_name}')
        near = min(day_distance(e.period, when) for e in editions)
        if near > 30:
            raise ValueError(f'Tournament edition unknown for this date: {provider_name}')
        close = [e for e in editions if day_distance(e.period, when) <= near + 7]
        if len({(e.surface, level_class(e.level)) for e in close}) != 1:
            raise ValueError(f'Tournament ambiguous: {provider_name}')
        return max(close, key=lambda e: e.period)


def fixtures(capture_root):
    """Latest observation of every singles event across archived API-Tennis fixture responses."""
    events = {}
    for receipt_path in sorted(Path(capture_root).glob('originals/*/receipt.json')):
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt.get('method') != 'get_fixtures' or receipt.get('http_status') != 200 or receipt['params'].get('event_type_key') not in TOURS:
            continue
        # The receipt's absolute path is host-specific (Windows vs server); the response always sits beside it.
        body = json.loads((receipt_path.parent / 'response.json').read_text(encoding='utf-8'))
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


def seal_new(root, capture_root, motor, clock=now, ahead_minutes=SEAL_AHEAD_MINUTES):
    """Seal each fixture once, at the first run inside [start - ahead_minutes, start - LEAD_MINUTES].

    Sealing close to the start lets the forecast use the freshest hourly market observation (owner goal: accuracy);
    later fixtures wait for a later run. `motor` may be a zero-argument factory, built only when something is due.
    """
    root = Path(root)
    ledger = Ledger(root)
    stamp = clock()
    report = dict(run_at=stamp, sealed=[], excluded=[], skipped=0, waiting=0)
    due = []
    for key, e in sorted(fixtures(capture_root).items()):
        if ledger.sealed(key):
            report['skipped'] += 1
            continue
        if e.get('event_status') not in ('', None) or e.get('first_player_dp1_key') or e.get('second_player_dp1_key'):
            continue  # started/finished/cancelled or doubles
        try:
            if utc(stamp) < start_time(e) - timedelta(minutes=ahead_minutes):
                report['waiting'] += 1
                continue
        except ValueError:
            pass  # unparsable start: reported as an exclusion below
        due.append((key, e))
    if not due:
        return report
    motor = motor() if callable(motor) else motor
    directory = Directory(motor.canonical, stamp)
    for key, e in due:
        try:
            begins = start_time(e)
            if utc(stamp) > begins - timedelta(minutes=LEAD_MINUTES):
                raise ValueError('Too close to or past the provider start time')
            tour = directory.tournament(e['circuit'], e['tournament_name'], begins)
            a = directory.player(e['circuit'], e['event_first_player'], tour.level)
            b = directory.player(e['circuit'], e['event_second_player'], tour.level)
            if a == b:
                raise ValueError('Same canonical player on both sides')
            meta = rules_for(e, tour)
            forecast = motor.forecast(e['circuit'], a, b, meta['surface'], begins.isoformat(), meta['best_of'], meta['deciding_tiebreak'])
            if (not forecast['odds_used'] and motor.config.get('odds_provider')
                    and utc(clock()) < begins - timedelta(minutes=LEAD_MINUTES + RETRY_MINUTES)):
                report['deferred_no_market'] = report.get('deferred_no_market', 0) + 1
                continue  # no price in this hour's observation (e.g. a skipped capture): the next hourly run retries
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


def log_loss(pairs):
    return -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for y, p in pairs) / len(pairs)


def clip(p):
    return min(max(p, 1e-9), 1 - 1e-9)


def offered_markets(sealed, propline_root=None, as_of=None):
    """Model vs margin-free price on the lines books actually offered at sealing, and vs PropLine's closing line.

    Grouped by family; push outcomes are left out (the prices are already conditional on no push). Closing rows are
    compared only on the same contract, so the three columns always share the same matches and lines.
    """
    groups = {}
    for v, r in sealed:
        board = v['forecast'].get('market_board')
        if not board or r['status'] != 'completed':
            continue
        result = dict(status='completed', score_A_B=r['score_A_B'], best_of=v['rules']['best_of'], completed_sets=r['completed_sets'])
        closing = {}
        if propline_root:
            from tennis_odds_propline_v1 import closing_board
            close = closing_board(propline_root, board['event_id'], *v['forecast']['players'], as_of or now())
            closing = {json.dumps(row['contract'], sort_keys=True): row['market'] for row in (close or {}).get('rows', [])}
        for row in board['rows']:
            try:
                o = outcome(row['contract'], result)
            except ValueError:
                continue
            if o not in ('win', 'loss'):
                continue
            g = groups.setdefault(row['contract']['kind'], dict(model=[], market=[], closing_model=[], closing=[]))
            y = int(o == 'win')
            g['model'].append((y, clip(row['model'])))
            g['market'].append((y, clip(row['market'])))
            c = closing.get(json.dumps(row['contract'], sort_keys=True))
            if c is not None:
                g['closing_model'].append((y, clip(row['model'])))
                g['closing'].append((y, clip(c)))
    report = {}
    for kind, g in sorted(groups.items()):
        acc = lambda pairs: sum((p > .5) == bool(y) for y, p in pairs) / len(pairs)
        report[kind] = dict(n=len(g['model']), model_log_loss=log_loss(g['model']), market_log_loss=log_loss(g['market']),
                            model_accuracy=acc(g['model']), market_accuracy=acc(g['market']), n_with_closing=len(g['closing']),
                            model_log_loss_on_closing_rows=log_loss(g['closing_model']) if g['closing'] else None,
                            closing_log_loss=log_loss(g['closing']) if g['closing'] else None)
    return report


def evaluate(root, capture_root, propline_root=None):
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
        # Where a price existed, the sealed winner is the price; the stack's own forecast on those same rows shows what it adds.
        stack = [(yy, v['forecast']['winner']['target_winner']) for yy, (v, r) in zip(y, sel) if v['forecast']['winner'].get('market_winner')]
        report['by_circuit'][circuit] = dict(winner=dict(probability_metrics(y, p), accuracy=sum((pp > .5) == bool(yy) for yy, pp in zip(y, p)) / len(y)), n_with_market=len(market),
            market_only=probability_metrics([a for a, b in market], [b for a, b in market]) if market else None,
            stack_on_market_rows=probability_metrics([a for a, b in stack], [b for a, b in stack]) if stack else None)
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
    report['offered_markets'] = offered_markets(rows, propline_root)
    return report
