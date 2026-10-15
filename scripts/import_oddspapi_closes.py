"""Import a reviewed offline OddsPapi bundle, with provenance and a rollback trial.

Runs in the worker container with qf.db. No API keys/network calls. Default is
read-only planning. Stale/ambiguous-time references stay in the provenance table,
because existing closing-price consumers do not all filter window_tag.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path


def utc(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def decision(row, match):
    reasons = []
    for key in ('league_id', 'home_team_id', 'away_team_id', 'home_goals', 'away_goals'):
        if match[key] != row['identity'][key]:
            raise ValueError('identity_changed:' + row['match_id'])
    if match['status'] != 'finished' or utc(match['kickoff_utc']) != utc(row['identity']['kickoff_utc']):
        raise ValueError('fixture_changed:' + row['match_id'])
    if row['bookmaker'] != 'pinnacle' or row['close_verified'] is not False:
        raise ValueError('invalid_bookmaker_or_certification')
    for side in ('home', 'draw', 'away'):
        price = row['prices'][side]
        if not isinstance(price, (float, int)) or not math.isfinite(price) or price <= 1:
            raise ValueError('invalid_price')
        if utc(row['changed_at'][side]) >= utc(row['cutoff_utc']):
            raise ValueError('quote_not_before_source_cutoff')
    if row['quality'] != 'recent':
        reasons.append('source_quality_review')
    if utc(row['cutoff_utc']) > utc(match['kickoff_utc']):
        reasons.append('source_cutoff_after_database_kickoff')
    if not row['has_history_after_cutoff']:
        reasons.append('history_does_not_continue_after_cutoff')
    age = max((utc(row['cutoff_utc']) - utc(t)).total_seconds()
              for t in row['changed_at'].values())
    if age > 3600:
        reasons.append('quote_older_than_one_hour')
    if not .95 < sum(1/p for p in row['prices'].values()) < 1.25:
        reasons.append('implausible_overround')
    return reasons


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')


def current(c, rows):
    ids = [r['match_id'] for r in rows]
    matches = c.execute('SELECT match_id,league_id,kickoff_utc,home_team_id,away_team_id,'
                        'home_goals,away_goals,status FROM matches WHERE match_id=ANY(%s)', (ids,)).fetchall()
    lookup = {m['match_id']: m for m in matches}
    if len(lookup) != len(rows):
        raise ValueError('missing_or_duplicate_matches')
    existing = {r['match_id'] for r in c.execute(
        "SELECT DISTINCT match_id FROM odds_snapshots WHERE match_id=ANY(%s) "
        "AND bookmaker='pinnacle' AND market='h2h' AND window_tag='close'", (ids,)).fetchall()}
    decisions = []
    for row in rows:
        reasons = decision(row, lookup[row['match_id']])
        disposition = ('reference_only' if reasons else
                       'existing_close' if row['match_id'] in existing else 'close_inserted')
        decisions.append({'match_id': row['match_id'], 'disposition': disposition, 'reasons': reasons})
    return lookup, decisions


def protected(c):
    result = {}
    for table, pk in (('matches', 'match_id'), ('teams', 'team_id'),
                      ('predictions', 'prediction_id'), ('picks', 'pick_id'),
                      ('model_artifacts', 'model_version')):
        result[table] = c.execute(
            f"SELECT count(*) AS n, md5(string_agg(md5(to_jsonb(t)::text),'' ORDER BY {pk})) AS hash "
            f'FROM {table} t').fetchone()
    result['odds_trigger'] = c.execute(
        "SELECT tgname,tgenabled FROM pg_trigger WHERE tgrelid='odds_snapshots'::regclass "
        "AND NOT tgisinternal ORDER BY tgname").fetchall()
    return result


def odds_digest(c, maximum):
    return c.execute("SELECT count(*) AS n,md5(string_agg(md5(to_jsonb(o)::text),'' "
                     "ORDER BY snapshot_id)) AS hash FROM odds_snapshots o WHERE snapshot_id<=%s",
                     (maximum,)).fetchone()


def insert(c, root, rows):
    from psycopg.types.json import Jsonb
    matches, decisions = current(c, rows)
    by_id = {d['match_id']: d for d in decisions}
    added_rows = 0
    added_provenance = 0
    for row in rows:
        prior = c.execute('SELECT match_id,normalized,snapshot_ids FROM historical_odds_backfills '
                          'WHERE provider=%s AND source_match_id=%s AND raw_source_sha256=%s',
                          ('oddspapi', row['fixture_id'], row['source_sha256'])).fetchone()
        if prior:
            assert prior['match_id'] == row['match_id'] and prior['normalized']['prices'] == row['prices']
            continue
        d = by_id[row['match_id']]
        ids = []
        if d['disposition'] == 'close_inserted':
            effective = utc(row['cutoff_utc']) - timedelta(microseconds=1)
            mins = int((utc(matches[row['match_id']]['kickoff_utc']) - effective).total_seconds() // 60)
            assert mins >= 0
            values = c.execute(
                "INSERT INTO odds_snapshots(match_id,bookmaker,market,selection,line,price,"
                "captured_at,mins_to_kickoff,window_tag,source,book_updated_at) "
                "SELECT %s,'pinnacle','h2h',v.sel,NULL,v.price,%s,%s,'close',"
                "'oddspapi_reconstructed',v.updated FROM (VALUES "
                "('home',%s::real,%s::timestamptz),('draw',%s::real,%s::timestamptz),"
                "('away',%s::real,%s::timestamptz)) AS v(sel,price,updated) "
                "WHERE NOT EXISTS(SELECT 1 FROM odds_snapshots WHERE match_id=%s "
                "AND bookmaker='pinnacle' AND market='h2h' AND window_tag='close') RETURNING snapshot_id",
                (row['match_id'], effective, mins,
                 row['prices']['home'], utc(row['changed_at']['home']),
                 row['prices']['draw'], utc(row['changed_at']['draw']),
                 row['prices']['away'], utc(row['changed_at']['away']), row['match_id'])).fetchall()
            ids = [r['snapshot_id'] for r in values]
            assert len(ids) == 3
            added_rows += len(ids)
        payload = (root / row['history_path']).read_bytes()
        assert hashlib.sha256(gzip.decompress(payload)).hexdigest() == row['history_sha256']
        c.execute('INSERT INTO historical_odds_backfills(provider,source_match_id,raw_source_sha256,'
                  'match_id,league_id,received_at,raw_1x2_gzip,raw_1x2_sha256,source_metadata,'
                  'normalized,disposition,snapshot_ids) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                  ('oddspapi', row['fixture_id'], row['source_sha256'], row['match_id'], row['league_id'],
                   utc(row['received_at']), payload, row['history_sha256'], Jsonb(row['receipt']),
                   Jsonb({**row, 'import_reasons': d['reasons'],
                          'effective_time_definition': 'source_cutoff_minus_one_microsecond; reconstructed, not reception'}),
                   d['disposition'], ids))
        added_provenance += 1
    return {'snapshots': added_rows, 'provenance': added_provenance,
            'decisions': decisions, 'counts': dict(Counter(d['disposition'] for d in decisions))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--mode', choices=['plan', 'rehearse', 'apply'], default='plan')
    args = parser.parse_args()
    root = args.root
    rows = json.loads((root / 'input.json').read_text(encoding='utf-8'))
    assert len(rows) == len({r['match_id'] for r in rows}) == 2943
    from qf.db import conn
    with conn() as c:
        if args.mode == 'plan':
            c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            _, decisions = current(c, rows)
            report = {'rows': len(rows), 'counts': dict(Counter(d['disposition'] for d in decisions)),
                      'decisions': decisions, 'active_models': c.execute(
                          'SELECT model_version FROM model_artifacts WHERE is_active').fetchall()}
            save(root / 'plan.json', report)
            print(json.dumps({k: v for k, v in report.items() if k != 'decisions'}, default=str))
            return
        c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        c.execute('SET LOCAL lock_timeout=\'20s\'')
        c.execute('LOCK TABLE odds_snapshots IN SHARE ROW EXCLUSIVE MODE')
        c.execute('SELECT pg_advisory_xact_lock(61015071)')
        maximum = c.execute('SELECT coalesce(max(snapshot_id),0) AS n FROM odds_snapshots').fetchone()['n']
        baseline = protected(c)
        old_odds = odds_digest(c, maximum)
        if args.mode == 'apply':
            # Full table COPY backup before any persistent mutation.
            with gzip.open(root / 'odds_snapshots_before.copy.gz', 'wb') as backup:
                with c.cursor().copy('COPY odds_snapshots TO STDOUT WITH (FORMAT binary)') as stream:
                    for block in stream:
                        backup.write(block)
            save(root / 'backup_receipt.json', {'rows': old_odds['n'], 'digest': old_odds,
                 'protected': baseline, 'created_at_utc': datetime.now(timezone.utc),
                 'sha256_compressed': hashlib.sha256((root / 'odds_snapshots_before.copy.gz').read_bytes()).hexdigest()})
        c.execute((root / '070_historical_odds_backfills.sql').read_text(encoding='utf-8'))
        first = insert(c, root, rows)
        second = insert(c, root, rows)
        assert second['snapshots'] == 0 and second['provenance'] == 0
        assert protected(c) == baseline
        assert odds_digest(c, maximum) == old_odds
        # Verify every inserted triple before commit, including REAL rounding.
        expected = {r['match_id']: r for r in rows}
        verified = c.execute(
            'SELECT b.match_id,b.disposition,b.snapshot_ids,o.selection,o.price,o.captured_at,'
            'o.book_updated_at,o.mins_to_kickoff,o.bookmaker,o.market,o.source,o.window_tag '
            'FROM historical_odds_backfills b LEFT JOIN odds_snapshots o '
            'ON o.snapshot_id=ANY(b.snapshot_ids) WHERE b.provider=\'oddspapi\'').fetchall()
        groups = Counter()
        for v in verified:
            r = expected[v['match_id']]
            if v['disposition'] != 'close_inserted':
                assert v['snapshot_ids'] == [] and v['selection'] is None
                continue
            assert v['bookmaker'] == 'pinnacle' and v['market'] == 'h2h'
            assert v['source'] == 'oddspapi_reconstructed' and v['window_tag'] == 'close'
            assert abs(v['price'] - r['prices'][v['selection']]) <= 1e-6 * r['prices'][v['selection']]
            assert v['book_updated_at'] < v['captured_at'] < utc(r['identity']['kickoff_utc'])
            assert v['mins_to_kickoff'] >= 0
            groups[v['match_id']] += 1
        assert all(n == 3 for n in groups.values())
        report = {**first, 'repeat_snapshots': second['snapshots'],
                  'repeat_provenance': second['provenance'], 'protected_unchanged': True,
                  'existing_odds_unchanged': True, 'mode': args.mode,
                  'completed_at_utc': datetime.now(timezone.utc)}
        save(root / (args.mode + '_result.json'), report)
        if args.mode == 'rehearse':
            c.rollback()
            assert c.execute('SELECT to_regclass(\'historical_odds_backfills\') AS t').fetchone()['t'] is None
            assert odds_digest(c, maximum) == old_odds
            print(json.dumps({k: v for k, v in report.items() if k != 'decisions'}, default=str))
            return
        c.commit()
        confirmed = c.execute("SELECT disposition,count(*) AS n FROM historical_odds_backfills "
                              "WHERE provider='oddspapi' GROUP BY disposition ORDER BY disposition").fetchall()
        report['confirmed_provenance'] = confirmed
        report['confirmed_source_snapshots'] = c.execute(
            "SELECT count(*) AS n FROM odds_snapshots WHERE source='oddspapi_reconstructed'").fetchone()['n']
        save(root / 'apply_result.json', report)
        print(json.dumps({k: v for k, v in report.items() if k != 'decisions'}, default=str))


if __name__ == '__main__':
    main()
