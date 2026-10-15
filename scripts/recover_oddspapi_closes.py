"""Archive OddsPapi history and reconstruct pre-kickoff Pinnacle 1X2 references.

Read-only with respect to the application/database. API key is supplied only in
ODDSPAPI_API_KEY. Originals are gzip archives of response bytes with receipts;
requests in receipts deliberately exclude the credential. Resume uses receipts.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://api.oddspapi.io/v4/'
# IDs verified against the authenticated soccer catalog, including MX's two
# split-season competitions and Argentina's domestic league cup archive.
TOURNAMENTS = {
    'ar.primera': [155, 28538], 'br.serie_a': [325],
    'ch.super_league': [215], 'de.bundesliga': [35],
    'de.bundesliga2': [44], 'dk.superliga': [39],
    'es.laliga': [8], 'es.laliga2': [54], 'eu.ucl': [7],
    'eu.uel': [679], 'fr.ligue_1': [34], 'fr.ligue_2': [182],
    'gb.championship': [18], 'gb.premier_league': [17],
    'it.serie_a': [23], 'it.serie_b': [53],
    'mx.liga_mx': [352, 27464, 27466], 'nl.eredivisie': [37],
    'no.eliteserien': [20], 'pt.primeira': [238],
    'se.allsvenskan': [40], 'tr.super_lig': [52], 'us.mls': [242],
}


def utc(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def now():
    return datetime.now(timezone.utc).isoformat()


def name_key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value).casefold()
                   if c.isalnum())


def dump(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def csv_write(path, rows, fields):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


class Client:
    def __init__(self, folder):
        self.folder = folder / 'originals'
        self.folder.mkdir(parents=True, exist_ok=True)
        self.key = os.environ['ODDSPAPI_API_KEY']
        self.next_call = defaultdict(float)

    def get(self, endpoint, params, label):
        receipt = self.folder / (label + '.receipt.json')
        archive = self.folder / (label + '.json.gz')
        if receipt.exists() and archive.exists():
            meta = json.loads(receipt.read_text(encoding='utf-8'))
            if meta['status'] in (200, 404):
                raw = gzip.decompress(archive.read_bytes())
                if hashlib.sha256(raw).hexdigest() != meta['sha256']:
                    raise ValueError('archive_hash_mismatch:' + label)
                return meta['status'], json.loads(raw), meta
        # Endpoint cooldowns apply across attempts and fixtures, not per URL.
        delay = self.next_call[endpoint] - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        started = now()
        query = urllib.parse.urlencode({**params, 'apiKey': self.key})
        request = urllib.request.Request(BASE + endpoint + '?' + query,
                                         headers={'Accept': 'application/json',
                                                  'Accept-Encoding': 'gzip'})
        try:
            response = urllib.request.urlopen(request, timeout=80)
        except urllib.error.HTTPError as exc:
            response = exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError('network_error:' + type(exc).__name__) from None
        try:
            raw = response.read()
            if response.headers.get('Content-Encoding') == 'gzip':
                raw = gzip.decompress(raw)
            status = response.code
            headers = {k: response.headers[k] for k in ('ETag', 'Retry-After')
                       if response.headers.get(k)}
        finally:
            response.close()
            self.next_call[endpoint] = time.monotonic() + (
                5.15 if endpoint == 'historical-odds' else 2.15)
        if self.key.encode() in raw:
            raise RuntimeError('response_contains_credential')
        archive.write_bytes(gzip.compress(raw, mtime=0))
        meta = {'source_url': BASE + endpoint + '?' + urllib.parse.urlencode(params),
                'started_at_utc': started, 'captured_at_utc': now(),
                'status': status, 'bytes': len(raw), 'headers': headers,
                'sha256': hashlib.sha256(raw).hexdigest()}
        dump(receipt, meta)
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            raise RuntimeError('non_json_response:' + str(status)) from None
        if status in (401, 403, 429):
            raise RuntimeError('api_access_or_limit:' + str(status))
        return status, data, meta


def index_fixtures(client, folder, rows):
    """Whole-period per-tournament calls preserve the small billable quota."""
    tasks = [(lg, tid) for lg in sorted({r['league_id'] for r in rows})
             for tid in TOURNAMENTS[lg]]
    for league, tid in tasks:
        status, data, _ = client.get('fixtures', {
            'tournamentId': tid, 'from': '2024-01-01T00:00:00Z',
            'to': '2026-10-14T00:00:00Z', 'statusId': 2, 'language': 'en',
        }, 'fixtures_' + str(tid))
        print(json.dumps({'stage': 'index', 'league': league, 'tournament': tid,
                          'status': status, 'events': len(data) if isinstance(data, list) else None}),
              flush=True)
        if status != 404 and (status != 200 or not isinstance(data, list)):
            raise RuntimeError('fixture_index_failed:' + str(tid))


def associate(folder, rows, snapshot):
    aliases = defaultdict(set)
    for team in snapshot['teams']:
        aliases[name_key(team['canonical_name'])].add(team['team_id'])
    for alias in snapshot['aliases']:
        aliases[name_key(alias['alias'])].add(alias['team_id'])
    original_matches = {m['match_id']: m for m in snapshot['matches']}
    extra_path = folder / 'reviewed_names.json'
    if extra_path.exists():
        for alias, team_id in json.loads(extra_path.read_text(encoding='utf-8')).items():
            aliases[name_key(alias)].add(team_id)
    fixtures = defaultdict(list)
    for league, tids in TOURNAMENTS.items():
        seen = set()
        for tid in tids:
            p = folder / 'originals' / ('fixtures_' + str(tid) + '.json.gz')
            if not p.exists():
                continue
            data = json.loads(gzip.decompress(p.read_bytes()))
            if not isinstance(data, list):
                continue
            for event in data:
                if event['fixtureId'] not in seen:
                    fixtures[league].append(event)
                    seen.add(event['fixtureId'])
    matched, unresolved = [], []
    for row in rows:
        match = original_matches[row['match_id']]
        candidates = []
        nearby = []
        for event in fixtures[row['league_id']]:
            if abs((utc(event['startTime']) - utc(row['kickoff_utc'])).total_seconds()) > 36*3600:
                continue
            nearby.append(event)
            home = set().union(*(aliases[name_key(event.get(k) or '')] for k in
                                 ('participant1Name', 'participant1ShortName')))
            away = set().union(*(aliases[name_key(event.get(k) or '')] for k in
                                 ('participant2Name', 'participant2ShortName')))
            if match['home_team_id'] in home and match['away_team_id'] in away:
                candidates.append(event)
        if len(candidates) == 1:
            matched.append({'row': row, 'event': candidates[0]})
        else:
            unresolved.append({'row': row, 'reason': 'ambiguous' if candidates else 'no_exact_names',
                               'home_team_id': match['home_team_id'],
                               'away_team_id': match['away_team_id'], 'nearby': nearby})
    dump(folder / 'matched.json', matched)
    dump(folder / 'unresolved.json', unresolved)
    return matched, unresolved


def extract(event, history):
    """Latest active prices at a conservative pre-start cutoff, never in-play.

    The API does not label a quote as official closing. Preserve that distinction:
    this is a reconstructed reference, with all timestamps and cutoff evidence.
    """
    scheduled = utc(event['startTime'])
    cutoff = min(scheduled, utc(event['trueStartTime'])) if event.get('trueStartTime') else scheduled
    outcomes = (history.get('bookmakers', {}).get('pinnacle', {})
                .get('markets', {}).get('101', {}).get('outcomes', {}))
    selected, counts, post = {}, {}, {}
    for side, oid in (('home', '101'), ('draw', '102'), ('away', '103')):
        entries = outcomes.get(oid, {}).get('players', {}).get('0', [])
        entries = sorted(entries, key=lambda r: utc(r['createdAt']))
        valid = [r for r in entries if utc(r['createdAt']) < cutoff
                 and r.get('active') is not False
                 and isinstance(r.get('price'), (float, int))
                 and math.isfinite(r['price']) and r['price'] > 1]
        if not valid:
            return None
        selected[side] = valid[-1]
        counts[side] = len(valid)
        post[side] = any(utc(r['createdAt']) >= cutoff for r in entries)
    age = max((cutoff - utc(r['createdAt'])).total_seconds() for r in selected.values())
    overround = sum(1/r['price'] for r in selected.values())
    return {
        **{side: r['price'] for side, r in selected.items()},
        **{side + '_changed_at_utc': r['createdAt'] for side, r in selected.items()},
        'cutoff_utc': cutoff.isoformat(), 'max_age_seconds': age,
        'overround': overround, 'has_history_after_cutoff': all(post.values()),
        'prematch_movements': counts,
        'price_type': 'reconstructed_last_active_before_conservative_kickoff',
        'close_verified': False,
        'quality': 'recent' if age <= 3600 and all(post.values())
        and 0.95 < overround < 1.25 else 'review',
    }


EXPORT_FIELDS = ['match_id', 'league_id', 'kickoff_utc', 'home_team', 'away_team',
                 'home', 'draw', 'away', 'bookmaker', 'source', 'source_url',
                 'captured_at_utc', 'fixture_id', 'source_home', 'source_away',
                 'source_kickoff_utc', 'true_start_utc', 'cutoff_utc',
                 'home_changed_at_utc', 'draw_changed_at_utc', 'away_changed_at_utc',
                 'max_age_seconds', 'overround', 'has_history_after_cutoff',
                 'price_type', 'close_verified', 'quality', 'source_sha256']


def report(folder, rows, matched, delivery=None):
    results, statuses = [], {}
    cache_dir = folder / 'extracted'
    cache_dir.mkdir(exist_ok=True)
    for job in matched:
        row, event = job['row'], job['event']
        stem = folder / 'originals' / ('history_' + event['fixtureId'])
        receipt = stem.with_suffix('.receipt.json')
        archive = stem.with_suffix('.json.gz')
        if not receipt.exists() or not archive.exists():
            statuses[row['match_id']] = 'pending_history'
            continue
        meta = json.loads(receipt.read_text(encoding='utf-8'))
        if meta['status'] != 200:
            statuses[row['match_id']] = 'no_history' if meta['status'] == 404 else 'http_' + str(meta['status'])
            continue
        cache_path = cache_dir / (event['fixtureId'] + '.json')
        if cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding='utf-8'))
        else:
            cached = {}
        if cached.get('source_sha256') == meta['sha256']:
            prices = cached['prices']
        else:
            raw = gzip.decompress(archive.read_bytes())
            if hashlib.sha256(raw).hexdigest() != meta['sha256']:
                raise ValueError('archive_hash_mismatch:' + event['fixtureId'])
            prices = extract(event, json.loads(raw))
            dump(cache_path, {'source_sha256': meta['sha256'], 'prices': prices})
        if not prices:
            statuses[row['match_id']] = 'no_complete_prematch_1x2'
            continue
        statuses[row['match_id']] = 'reconstructed_prematch_reference'
        results.append({**prices, 'match_id': row['match_id'], 'league_id': row['league_id'],
                        'kickoff_utc': utc(row['kickoff_utc']).isoformat(),
                        'home_team': row['local'], 'away_team': row['visita'],
                        'bookmaker': 'pinnacle', 'source': 'oddspapi',
                        'source_url': meta['source_url'], 'source_sha256': meta['sha256'],
                        'captured_at_utc': meta['captured_at_utc'],
                        'fixture_id': event['fixtureId'], 'source_home': event['participant1Name'],
                        'source_away': event['participant2Name'],
                        'source_kickoff_utc': event['startTime'],
                        'true_start_utc': event.get('trueStartTime')})
    csv_write(folder / 'pinnacle_recuperado.csv', results, EXPORT_FIELDS)
    exclusions_path = folder / 'exclusions.json'
    exclusions = ({e['match_id']: e['status'] for e in
                   json.loads(exclusions_path.read_text(encoding='utf-8'))}
                  if exclusions_path.exists() else {})
    full = [{**row, 'oddspapi_status': statuses.get(
        row['match_id'], exclusions.get(row['match_id'], 'unmatched'))}
            for row in rows]
    csv_write(folder / 'lista_resultado.csv', full, list(rows[0]) + ['oddspapi_status'])
    summary = {'updated_at_utc': now(), 'total': len(rows), 'matched': len(matched),
               'recovered_prematch_references': len(results), 'verified_official_closes': 0,
               'quality': dict(Counter(r['quality'] for r in results)),
               'original_list_sha256': json.loads((folder / 'input_receipt.json')
                   .read_text(encoding='utf-8'))['sha256'],
               'statuses': dict(Counter(r['oddspapi_status'] for r in full)),
               'by_league': dict(Counter(r['league_id'] for r in results))}
    dump(folder / 'informe.json', summary)
    if delivery:
        delivery.mkdir(parents=True, exist_ok=True)
        for name in ('pinnacle_recuperado.csv', 'lista_resultado.csv', 'informe.json',
                     'reviewed_names.json', 'name_review_receipt.json', 'exclusions.json'):
            if (folder / name).exists():
                tmp = delivery / (name + '.tmp')
                shutil.copyfile(folder / name, tmp)
                tmp.replace(delivery / name)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['index', 'match', 'run', 'report'])
    parser.add_argument('--output', type=Path, default=Path('.local/oddspapi_20261014'))
    parser.add_argument('--source', type=Path, default=Path('.local/cierres_faltantes_20261014.csv'))
    parser.add_argument('--snapshot', type=Path,
                        default=Path('.local/pinnacle_recovery_20261014/database-before.json'))
    parser.add_argument('--max-events', type=int)
    parser.add_argument('--delivery', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with args.source.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    dump(args.output / 'input_receipt.json', {
        'path': str(args.source.resolve()),
        'sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
        'rows': len(rows), 'captured_at_utc': now()})
    if args.action == 'index':
        index_fixtures(Client(args.output), args.output, rows)
        return
    snapshot = json.loads(args.snapshot.read_text(encoding='utf-8-sig'))
    matched, unresolved = associate(args.output, rows, snapshot)
    print(json.dumps({'matched': len(matched), 'unresolved': len(unresolved)}), flush=True)
    if args.action == 'run':
        # The OS releases the lock if the worker crashes; no stale PID deletion.
        run_lock = (args.output / 'run.lock').open('a+b')
        run_lock.write(b'0')
        run_lock.flush()
        run_lock.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(run_lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(run_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        client = Client(args.output)
        # Recent dates first, but every matched row remains in the queue.
        queue = sorted(matched, key=lambda j: j['event']['startTime'], reverse=True)
        summary = report(args.output, rows, matched, args.delivery)
        state = {'status': 'running', 'pid': os.getpid(), 'started_at_utc': now(),
                 'queue_length': len(queue), 'position': 0}
        dump(args.output / 'worker_state.json', state)
        try:
            for i, job in enumerate(queue):
                if args.max_events is not None and i >= args.max_events:
                    break
                event = job['event']
                for attempt in range(4):
                    try:
                        status, _, _ = client.get('historical-odds', {
                            'fixtureId': event['fixtureId'], 'bookmakers': 'pinnacle',
                        }, 'history_' + event['fixtureId'])
                        if status >= 500 and attempt < 3:
                            time.sleep(10 * (attempt+1))
                            continue
                        break
                    except RuntimeError as exc:
                        retryable = str(exc).startswith(('network_error:', 'api_access_or_limit:429',
                                                        'non_json_response:5'))
                        if not retryable or attempt == 3:
                            raise
                        time.sleep(10 * (attempt+1))
                # Each receipt is durable; refresh aggregate CSVs every 20 events.
                if i % 20 == 0:
                    summary = report(args.output, rows, matched, args.delivery)
                state.update(position=i+1, last_fixture=event['fixtureId'],
                             last_http_status=status, updated_at_utc=now())
                dump(args.output / 'worker_state.json', state)
                print(json.dumps({'stage': 'history', 'position': i+1,
                                  'fixture': event['fixtureId'], 'status': status,
                                  'recovered_at_last_export': summary['recovered_prematch_references']}), flush=True)
        except BaseException as exc:
            state.update(status='failed', error_type=type(exc).__name__, updated_at_utc=now())
            dump(args.output / 'worker_state.json', state)
            report(args.output, rows, matched, args.delivery)
            raise
        state.update(status='batch_completed' if args.max_events else 'completed',
                     updated_at_utc=now())
        dump(args.output / 'worker_state.json', state)
    print(json.dumps(report(args.output, rows, matched, args.delivery)), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # urllib exceptions may contain credential-bearing URLs. Never print them.
        print(json.dumps({'fatal_error_type': type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
