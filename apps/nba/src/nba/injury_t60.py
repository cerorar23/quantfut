"""Backfill of official injury reports closest before tipoff minus 60 minutes (research input only).

The NBA publishes an hourly series of PDFs (file `HHPM` is stamped HH:30 ET). The retrospective table only had the 13:30
and 17:30 ET reports, so most games saw a report that was hours older than the live rule would use.

Three offline-testable steps: `plan` (which files each game needs), `fetch` (bounded, resumable, one request at a time),
`build` (parse with the strict seven-column parser and join to NBA ids). Nothing here changes any sealed artifact.
"""
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import time
from zoneinfo import ZoneInfo

from . import availability as av
from . import injury_pdf
from .audit import digest, write_json
from .context import name_key

EASTERN = ZoneInfo('America/New_York')
BASE = 'https://ak-static.cms.nba.com/referee/injury/'
# 403 is how this S3 bucket answers for a file that does not exist; a control file known to exist guards against a real block.
MISSING = (403, 404)
TRICODES = dict(
    ATL='Atlanta Hawks', BKN='Brooklyn Nets', BOS='Boston Celtics', CHA='Charlotte Hornets', CHI='Chicago Bulls',
    CLE='Cleveland Cavaliers', DAL='Dallas Mavericks', DEN='Denver Nuggets', DET='Detroit Pistons', GSW='Golden State Warriors',
    HOU='Houston Rockets', IND='Indiana Pacers', LAC='LA Clippers', LAL='Los Angeles Lakers', MEM='Memphis Grizzlies',
    MIA='Miami Heat', MIL='Milwaukee Bucks', MIN='Minnesota Timberwolves', NOP='New Orleans Pelicans', NYK='New York Knicks',
    OKC='Oklahoma City Thunder', ORL='Orlando Magic', PHI='Philadelphia 76ers', PHX='Phoenix Suns', POR='Portland Trail Blazers',
    SAC='Sacramento Kings', SAS='San Antonio Spurs', TOR='Toronto Raptors', UTA='Utah Jazz', WAS='Washington Wizards')
CONTROL = BASE + 'Injury-Report_2021-10-19_05PM.pdf'
SEASONS = ('2023-24', '2024-25', '2025-26')  # layouts the strict parser reads
# Until 2025-12-21 one file per hour, `HHPM`, stamped HH:30 ET. From 2025-12-22 one file per quarter hour, `HH_MMPM`, stamped HH:MM.
MINUTE_SCHEME_FROM = date(2025, 12, 22)


def file_name(moment):
    """Report file for a slot `moment` (ET): `HHPM` before the quarter-hour scheme, `HH_MMPM` from MINUTE_SCHEME_FROM."""
    hour = moment.hour % 12 or 12
    suffix = 'AM' if moment.hour < 12 else 'PM'
    minutes = f'_{moment.minute:02d}' if moment.date() >= MINUTE_SCHEME_FROM else ''
    return f"Injury-Report_{moment.date().isoformat()}_{hour:02d}{minutes}{suffix}.pdf"


def wanted_slot(tipoff, steps_back=0):
    """Latest slot stamped at or before tipoff - 60 min, optionally `steps_back` slots earlier.

    Hourly files are stamped HH:30 (slot = the hour of cutoff - 30 min); quarter-hour files are stamped HH:MM."""
    target = (tipoff - av.LEAD).astimezone(EASTERN)
    if target.date() >= MINUTE_SCHEME_FROM:
        return target.replace(minute=target.minute // 15 * 15, second=0, microsecond=0) - timedelta(minutes=15 * steps_back)
    target -= timedelta(minutes=30)
    return target.replace(minute=0, second=0, microsecond=0) - timedelta(hours=steps_back)


def tip_index(api_dir, games, reports):
    """game id -> UTC tipoff: api-sports where available, else the tipoff carried by already-joined report rows."""
    tips = av.tipoff_map(api_dir, games)
    for report in reports:
        for row in report['rows']:
            if row.get('nba_game_id') and row.get('game_tipoff_utc') and row['nba_game_id'] not in tips:
                tips[row['nba_game_id']] = datetime.fromisoformat(row['game_tipoff_utc'])
    return tips


def plan(games, tips, seasons=SEASONS, have=(), missing=(), max_back=3):
    """Files to fetch: per game the latest not-known-missing hourly file, walking back at most `max_back` hours.

    `have` and `missing` are file names already stored / known absent. Returns a sorted list of file names with game counts."""
    needed = defaultdict(int)
    for g in games:
        tip = tips.get(g['game_id'])
        if g['season'] not in seasons or tip is None:
            continue
        for back in range(max_back + 1):
            name = file_name(wanted_slot(tip, back))
            if name in missing:
                continue
            if name not in have:
                needed[name] += 1
            break
    return sorted(needed.items())


def http_get(url):
    import httpx
    try:
        response = httpx.get(url, headers={'User-Agent': 'Mozilla/5.0 NBA research receipt capture'}, timeout=30, follow_redirects=False)
    except httpx.TransportError as exc:
        raise OSError(str(exc)) from exc
    return response.status_code, response.content


def fetch(names, folder, get=http_get, cap=100, pause=1.0, control_every=50, sleep=time.sleep, now=lambda: datetime.now(UTC)):
    """Download at most `cap` files, one at a time, resumable through manifest.json.

    Stops at the first unexpected status or when the control file stops answering 200 (a real block).
    A missing file (403/404) is recorded and never asked for again."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'manifest.json'
    meta = json.loads(path.read_bytes()) if path.exists() else dict(source='NBA_official_injury_PDF_hourly', files={}, missing=[], stopped=None)
    if meta['stopped']:
        raise ValueError('a previous run stopped: ' + meta['stopped'])
    requests = 0

    def control():
        status, body = get(CONTROL)
        if status != 200 or not body.startswith(b'%PDF-'):
            meta['stopped'] = f'control file answered {status}'
            write_json(path, meta)
            raise ValueError(meta['stopped'])

    control()
    for name in names:
        if name in meta['files'] or name in meta['missing']:
            continue
        if requests >= cap:
            break
        if requests and requests % control_every == 0:
            control()
        sleep(pause)
        try:
            status, body = get(BASE + name)
        except OSError:  # network timeout or reset, not an answer from the server: one more try, then the run ends and can resume
            sleep(5)
            status, body = get(BASE + name)
        requests += 1
        if status == 200 and body.startswith(b'%PDF-'):
            target = folder / name
            if target.exists():
                raise ValueError('refuse to overwrite a stored report')
            target.write_bytes(body)
            meta['files'][name] = dict(bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), first_received_at_utc=now().isoformat())
        elif status in MISSING:
            meta['missing'].append(name)
        else:
            meta['stopped'] = f'{name}: HTTP {status}'
            write_json(path, meta)
            raise ValueError(meta['stopped'])
        write_json(path, meta)
    return dict(requests=requests, stored=len(meta['files']), missing=len(meta['missing']))


def game_index(games):
    return {(g['date'], g['home']['team_id'], g['away']['team_id']): g for g in games}


def team_ids(games):
    names = {}
    for g in games:
        for side in ('home', 'away'):
            names[g[side]['name']] = g[side]['team_id']
    return names


def name_ids(reports, players):
    """Raw report name -> NBA player id, only when unique. Joined reports first, box-score names as a fallback."""
    raw = defaultdict(set)
    for report in reports:
        for row in report['rows']:
            if row.get('player_name_raw') and row.get('nba_player_id'):
                raw[row['player_name_raw']].add(str(row['nba_player_id']))
    exact = {k: next(iter(v)) for k, v in raw.items() if len(v) == 1}
    by_key = defaultdict(set)
    for r in players:
        by_key[name_key(r['name'])].add(str(r['player_id']))
    return exact, {k: next(iter(v)) for k, v in by_key.items() if len(v) == 1}


def join_report(report, games, teams, tips, exact, by_key):
    """Add NBA ids to the rows of one parsed report. Returns (report, counters). Rows that cannot be placed are dropped and counted."""
    index = game_index(games)
    counts = dict(rows=0, no_game=0, named=0, no_player=0)
    rows = []
    for row in report['rows']:
        counts['rows'] += 1
        away, _, home = row['matchup'].partition('@')
        month, day, year = row['game_date'].split('/')
        key = (f'{year}-{month}-{day}', teams.get(TRICODES.get(home)), teams.get(TRICODES.get(away)))
        game = index.get(key)
        if game is None:
            counts['no_game'] += 1
            continue
        out = dict(row, nba_game_id=game['game_id'], nba_team_id=teams.get(row['team']), nba_player_id=None,
                   game_tipoff_utc=tips[game['game_id']].isoformat() if game['game_id'] in tips else None)
        if row.get('player_name_raw'):
            counts['named'] += 1
            last, _, first = row['player_name_raw'].partition(', ')
            pid = exact.get(row['player_name_raw']) or by_key.get(name_key(f'{first} {last}'))
            if pid is None:
                counts['no_player'] += 1
            out['nba_player_id'] = int(pid) if pid else None
        rows.append(out)
    return dict(report, rows=rows), counts


def build(folder, output, games, players, api_dir, existing_path, parse=injury_pdf.extract_report):
    """Parse every stored PDF, join ids, write reports.jsonl.gz and a coverage report. Output folder must be new."""
    folder, output = Path(folder), Path(output)
    meta = json.loads((folder / 'manifest.json').read_bytes())
    existing = av.read_reports(existing_path)
    tips = tip_index(api_dir, games, existing)
    teams, (exact, by_key) = team_ids(games), name_ids(existing, players)
    output.mkdir(parents=True, exist_ok=False)
    reports, totals, failed = [], defaultdict(int), []
    for name, info in sorted(meta['files'].items()):
        pdf = folder / name
        if hashlib.sha256(pdf.read_bytes()).hexdigest() != info['sha256']:
            raise ValueError('stored report changed: ' + name)
        try:
            parsed = parse(pdf, BASE + name, info['first_received_at_utc'])
        except ValueError as exc:
            failed.append(dict(file=name, reason=str(exc)))
            continue
        parsed['pdf_file'] = name
        joined, counts = join_report(parsed, games, teams, tips, exact, by_key)
        for k, v in counts.items():
            totals[k] += v
        reports.append(joined)
    path = output / 'reports.jsonl.gz'
    with path.open('wb') as file:
        with gzip.GzipFile(filename='', fileobj=file, mode='wb', mtime=0) as stream:
            for report in sorted(reports, key=lambda r: r['report_timestamp_utc']):
                stream.write((json.dumps(report, sort_keys=True) + '\n').encode())
    summary = dict(reports=len(reports), parse_failures=failed, missing_files=meta['missing'], join=dict(totals),
                   reports_sha256=digest(path), manifest_sha256=digest(folder / 'manifest.json'),
                   existing_sha256=digest(existing_path), original_historical_receipt_known=False, actionable=False)
    write_json(output / 'report.json', summary)
    return summary


def coverage(games, tips, reports, seasons=SEASONS):
    """Share of games whose latest report valid under the T-60 rule is within `hours` of the cutoff (per season)."""
    latest = {}
    for report in reports:
        stamp = datetime.fromisoformat(report['report_timestamp_utc'])
        for game in {r['nba_game_id'] for r in report['rows'] if r.get('nba_game_id')}:
            tip = tips.get(game)
            if tip is not None and stamp <= tip - av.LEAD and (game not in latest or stamp > latest[game]):
                latest[game] = stamp
    out = {}
    for season in seasons:
        gaps = sorted((tips[g['game_id']] - av.LEAD - latest[g['game_id']]).total_seconds() / 3600
                      for g in games if g['season'] == season and g['game_id'] in tips and g['game_id'] in latest)
        total = sum(1 for g in games if g['season'] == season and g['game_id'] in tips)
        out[season] = dict(games_with_tipoff=total, with_valid_report=len(gaps),
                           median_hours_before_cutoff=gaps[len(gaps) // 2] if gaps else None,
                           share_within_1h=sum(1 for x in gaps if x <= 1) / total if total else None)
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'fetch', 'build'])
    parser.add_argument('--data', required=True, help='folder with players.jsonl.gz and games.json')
    parser.add_argument('--existing', required=True, help='already joined reports.jsonl.gz (tipoffs, names, files already held)')
    parser.add_argument('--api-dir', required=True)
    parser.add_argument('--raw', required=True, help='fetch/build: folder for the PDFs and manifest.json')
    parser.add_argument('--output', help='build: new folder')
    parser.add_argument('--cap', type=int, default=100, help='fetch: maximum requests in this run')
    parser.add_argument('--pause', type=float, default=1.0)
    a = parser.parse_args()
    data = Path(a.data)
    games = json.loads((data / 'games.json').read_bytes())
    existing = av.read_reports(a.existing)
    if a.command == 'build':
        from . import multimarket as m1
        print(json.dumps(build(a.raw, a.output, games, m1.read_rows(data / 'players.jsonl.gz'), a.api_dir, a.existing), allow_nan=False))
        return
    tips = tip_index(a.api_dir, games, existing)
    manifest = Path(a.raw) / 'manifest.json'
    meta = json.loads(manifest.read_bytes()) if manifest.exists() else dict(files={}, missing=[])
    have = {r['source_url'].rsplit('/', 1)[1] for r in existing} | set(meta['files'])
    files = plan(games, tips, have=have, missing=set(meta['missing']))
    if a.command == 'plan':
        print(json.dumps(dict(files=len(files), games=sum(n for _, n in files))))
        return
    print(json.dumps(fetch([n for n, _ in files], a.raw, cap=a.cap, pause=a.pause)))


if __name__ == '__main__':
    main()
