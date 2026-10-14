"""Archive explicit Football-data Pinnacle closes and plan an existing-match backfill.

No database writes. Input is a read-only catalog/match/alias JSON snapshot.
Only PSCH/PSCD/PSCA are eligible; PSH/PSD/PSA are never closing fallbacks.
The export uses canonical UTC kickoff, preserving the source date/time separately.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import unicodedata

import httpx

FIELDS = ['league_id', 'kickoff_utc', 'home_team', 'away_team', 'home', 'draw', 'away',
          'bookmaker', 'source', 'source_url', 'captured_at_utc', 'match_id',
          'source_date', 'source_time', 'source_sha256', 'source_row', 'closing_columns']


def name_key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value).casefold()
                   if c.isalnum())


def prices(row):
    try:
        odds = [float(row[k]) for k in ('PSCH', 'PSCD', 'PSCA')]
    except (KeyError, TypeError, ValueError):
        return None
    return odds if all(math.isfinite(p) and p > 1 for p in odds) else None


def source_date(row):
    for fmt in ('%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d'):
        try:
            return datetime.strptime(row.get('Date', ''), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


def archive(job, folder):
    league, season = job
    code = league['fd_code']
    url = (f'https://www.football-data.co.uk/new/{code}.csv' if league['fd_extra'] else
           f'https://www.football-data.co.uk/mmz4281/{season}/{code}.csv')
    label = f'{code}-{season or "all"}'
    body = folder / f'{label}.csv'
    receipt = folder / f'{label}.receipt.json'
    if receipt.exists() and body.exists():
        meta = json.loads(receipt.read_text(encoding='utf-8'))
        raw = body.read_bytes()
        if meta['sha256'] != hashlib.sha256(raw).hexdigest():
            raise ValueError(f'archive_hash_mismatch:{label}')
        return league, raw, meta
    started = datetime.now(timezone.utc).isoformat()
    try:
        response = httpx.get(url, follow_redirects=True, timeout=60)
        raw = response.content
        meta = {'url': url, 'status': response.status_code, 'started_at': started,
                'captured_at_utc': datetime.now(timezone.utc).isoformat(),
                'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        body.write_bytes(raw)
    except httpx.HTTPError as exc:
        raw = b''
        meta = {'url': url, 'status': None, 'started_at': started,
                'error': type(exc).__name__, 'sha256': hashlib.sha256(raw).hexdigest()}
    receipt.write_text(json.dumps(meta, indent=2), encoding='utf-8')
    return league, raw, meta


def write_csv(path, rows, fields=FIELDS):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def run(snapshot_path, output):
    output.mkdir(parents=True, exist_ok=True)
    raw_dir = output / 'originals'
    raw_dir.mkdir(exist_ok=True)
    snapshot = json.loads(snapshot_path.read_text(encoding='utf-8-sig'))
    teams = {t['team_id']: t for t in snapshot['teams']}
    aliases = defaultdict(set)
    for team in teams.values():
        aliases[(team['league_id'].split('.')[0], name_key(team['canonical_name']))].add(team['team_id'])
    for alias in snapshot['aliases']:
        if alias['source'] == 'football_data' and alias['team_id'] in teams:
            country = teams[alias['team_id']]['league_id'].split('.')[0]
            aliases[(country, name_key(alias['alias']))].add(alias['team_id'])
    index = defaultdict(list)
    for match in snapshot['matches']:
        index[(match['league_id'], match['home_team_id'], match['away_team_id'])].append(match)
    jobs = [(lg, season) for lg in snapshot['leagues'] if lg.get('fd_code')
            for season in ([None] if lg['fd_extra'] else ['2324', '2425', '2526', '2627'])]
    counts = defaultdict(Counter)
    candidates, all_matches, rejected, downloads = [], [], [], []
    seen = {}
    conflicts = set()
    with ThreadPoolExecutor(max_workers=3) as pool:
        for league, raw, meta in pool.map(lambda job: archive(job, raw_dir), jobs):
            lid = league['league_id']
            downloads.append(meta)
            if meta['status'] != 200:
                counts[lid]['download_failed'] += 1
                continue
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('latin-1')
            for row_number, row in enumerate(csv.DictReader(io.StringIO(text)), 2):
                date = source_date(row)
                if date is None or date.year < 2024:
                    continue
                counts[lid]['source_rows_since_2024'] += 1
                odds = prices(row)
                if odds is None:
                    counts[lid]['no_explicit_pinnacle_close'] += 1
                    continue
                counts[lid]['explicit_pinnacle_close'] += 1
                home = row.get('Home' if league['fd_extra'] else 'HomeTeam', '')
                away = row.get('Away' if league['fd_extra'] else 'AwayTeam', '')
                country = lid.split('.')[0]
                hi = aliases[(country, name_key(home))]
                ai = aliases[(country, name_key(away))]
                matches = []
                if len(hi) == len(ai) == 1:
                    for m in index[(lid, next(iter(hi)), next(iter(ai)))]:
                        ko = datetime.fromisoformat(m['kickoff_utc'])
                        # Source date is a day label, not an invented UTC kickoff.
                        # Include its stated time where present, ±36 h for matching only.
                        try:
                            h, minute = map(int, row.get('Time', '').split(':')[:2])
                            source_clock = date.replace(hour=h, minute=minute)
                        except (ValueError, TypeError):
                            source_clock = date.replace(hour=12)
                        if abs((ko - source_clock).total_seconds()) <= 36 * 3600:
                            matches.append(m)
                reason = None
                if len(hi) != 1 or len(ai) != 1:
                    reason = 'unresolved_or_ambiguous_team'
                elif len(matches) != 1:
                    reason = 'no_match' if not matches else 'ambiguous_match'
                else:
                    m = matches[0]
                    try:
                        hg = int(row['HG' if league['fd_extra'] else 'FTHG'])
                        ag = int(row['AG' if league['fd_extra'] else 'FTAG'])
                        if (hg, ag) != (m['home_goals'], m['away_goals']):
                            reason = 'score_mismatch'
                    except (ValueError, TypeError, KeyError):
                        reason = 'missing_final_score'
                if reason:
                    counts[lid][reason] += 1
                    rejected.append({'league_id': lid, 'home_team': home, 'away_team': away,
                                     'source_date': row.get('Date'), 'reason': reason,
                                     'source_url': meta['url'], 'source_row': row_number})
                    continue
                record = dict(zip(('home', 'draw', 'away'), odds))
                record.update(league_id=lid, kickoff_utc=datetime.fromisoformat(m['kickoff_utc']).astimezone(timezone.utc).isoformat(),
                              home_team=home, away_team=away, bookmaker='Pinnacle', source='football_data',
                              source_url=meta['url'], captured_at_utc=meta['captured_at_utc'],
                              match_id=m['match_id'], source_date=row.get('Date'), source_time=row.get('Time'),
                              source_sha256=meta['sha256'], source_row=row_number,
                              closing_columns='PSCH|PSCD|PSCA')
                mid = m['match_id']
                if mid in seen:
                    if [seen[mid][k] for k in ('home', 'draw', 'away')] != odds:
                        conflicts.add(mid)
                    counts[lid]['duplicate_source_match'] += 1
                    continue
                seen[mid] = record
                all_matches.append(record)
                if m['close_selections'] == 0:
                    candidates.append(record)
                elif m['close_selections'] < 3:
                    counts[lid]['partial_close_needs_review'] += 1
                else:
                    counts[lid]['already_complete'] += 1
    candidates = [r for r in candidates if r['match_id'] not in conflicts]
    all_matches = [r for r in all_matches if r['match_id'] not in conflicts]
    candidates.sort(key=lambda r: (r['league_id'], r['kickoff_utc'], r['match_id']))
    recovered = {r['match_id'] for r in candidates}
    pending = []
    for m in snapshot['matches']:
        if m['close_selections'] < 3 and m['match_id'] not in recovered:
            pending.append(dict(m, home_team=teams[m['home_team_id']]['canonical_name'],
                                away_team=teams[m['away_team_id']]['canonical_name']))
    write_csv(output / 'pinnacle_cierres_recuperables.csv', candidates)
    write_csv(output / 'pinnacle_cierres_fuente_emparejados.csv', all_matches)
    write_csv(output / 'sin_emparejar.csv', rejected,
              ['league_id', 'home_team', 'away_team', 'source_date', 'reason', 'source_url', 'source_row'])
    write_csv(output / 'pinnacle_pendientes.csv', pending,
              ['match_id', 'league_id', 'kickoff_utc', 'home_team', 'away_team', 'close_selections'])
    report = {'snapshot_at': snapshot['checked_at'], 'database_writes': 0,
              'missing_before': sum(m['close_selections'] < 3 for m in snapshot['matches']),
              'recoverable_matches': len(candidates), 'remaining_after_proposed_load': len(pending),
              'recoverable_by_league': dict(Counter(r['league_id'] for r in candidates)),
              'remaining_by_league': dict(Counter(r['league_id'] for r in pending)),
              'source_conflicting_matches': sorted(conflicts), 'counts_by_league': dict(counts),
              'downloads': downloads,
              'notes': ['Canonical database kickoff is UTC; raw source date/time preserved without inventing a source timezone.',
                        'captured_at_utc is real retrieval time, not historical availability or quote timestamp.',
                        'Explicit closing columns only; exact normalized names/registered football_data aliases, unique fixture within 36h and equal final score.',
                        'Proposal only. No new teams, matches or odds inserted.']}
    (output / 'informe.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['missing_before', 'recoverable_matches', 'remaining_after_proposed_load', 'recoverable_by_league']}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.snapshot, args.output)
