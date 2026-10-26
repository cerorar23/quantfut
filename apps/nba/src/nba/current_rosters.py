"""Dated official NBA membership, independent of player history, playing status and market quotes."""
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from .audit import digest, write_json

TEAM_SLUGS = dict(zip(range(1610612737, 1610612767), (
    'hawks', 'celtics', 'cavaliers', 'pelicans', 'bulls', 'mavericks', 'nuggets', 'warriors',
    'rockets', 'clippers', 'lakers', 'heat', 'bucks', 'timberwolves', 'nets', 'knicks', 'magic',
    'pacers', '76ers', 'suns', 'trail-blazers', 'kings', 'spurs', 'thunder', 'raptors', 'jazz',
    'grizzlies', 'wizards', 'pistons', 'hornets')))
NEXT_DATA = re.compile(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
TTL = timedelta(hours=1)


def utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('roster receipt must have a timezone')
    return result.astimezone(UTC)


def code_digest():
    return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def parse(body, receipt, season):
    source = urlsplit(receipt['url'])
    match = re.fullmatch(r'/team/(\d+)/[^/]+', source.path)
    if source.scheme != 'https' or source.hostname != 'www.nba.com' or not match or receipt['http_status'] != 200:
        raise ValueError('official NBA team roster required')
    if hashlib.sha256(body).hexdigest() != receipt['raw_sha256']:
        raise ValueError('roster raw bytes changed')
    found = NEXT_DATA.search(body.decode('utf8'))
    if found is None:
        raise ValueError('official roster payload missing')
    team = json.loads(found[1])['props']['pageProps']['team']
    tid = int(match[1])
    if receipt['raw_file'] != f'{tid}.html':
        raise ValueError('invalid roster receipt file')
    utc(receipt['first_received_at_utc'])
    if int(team['id']) != tid or team['info']['TEAM_ID'] != tid:
        raise ValueError('roster team identity mismatch')
    if team['info']['SEASON_YEAR'] != season or team['scheduleSeason'] != season:
        raise ValueError('stale roster season')
    rows, seen = [], set()
    for person in team['roster']:
        pid = person['PLAYER_ID']
        if type(pid) is not int or pid <= 0 or pid in seen:
            raise ValueError('invalid or duplicate roster player')
        if person['TeamID'] != tid or str(person['SEASON']) != season[:4] or person['LeagueID'] != '00':
            raise ValueError('roster player team/season mismatch')
        name = person['PLAYER']
        if not isinstance(name, str) or not name.strip():
            raise ValueError('roster player name missing')
        seen.add(pid)
        rows.append(dict(player_id=pid, team_id=tid, name=name, season=season,
                         supplemental_status_raw=person.get('SUPPLEMENTAL_STATUS'),
                         source_sha256=receipt['raw_sha256'], first_received_at_utc=receipt['first_received_at_utc']))
    if not 5 <= len(rows) <= 30:
        raise ValueError('incomplete or unsupported official roster')
    return rows


def membership(snapshot, as_of, season, teams):
    """Complete membership for these teams, or an error. Never infer it from a box score or a quote."""
    teams = set(teams)
    if snapshot['season'] != season or set(snapshot['teams']) != teams:
        raise ValueError('roster snapshot season/team coverage mismatch')
    out, counts = {}, dict.fromkeys(teams, 0)
    for r in snapshot['players']:
        pid, tid = str(r['player_id']), r['team_id']
        if tid not in teams or r['season'] != season or pid in out:
            raise ValueError('conflicting roster membership')
        age = as_of - utc(r['first_received_at_utc'])
        if not timedelta(0) <= age <= TTL:
            raise ValueError('late or stale roster receipt')
        out[pid] = tid
        counts[tid] += 1
    if any(n < 5 for n in counts.values()):
        raise ValueError('incomplete roster snapshot')
    return out


def capture(team_ids, season, folder, get, clock, cache=None):
    """Archive raw bytes and receipts in this cohort; reusable cache is revalidated and never dated backwards."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    snapshot = dict(season=season, teams=sorted(set(team_ids)), players=[], receipts=[])
    for tid in snapshot['teams']:
        url = f'https://www.nba.com/team/{tid}/{TEAM_SLUGS[tid]}'
        raw, receipt = None, None
        saved = None if cache is None else Path(cache) / 'rosters' / f'{tid}.json'
        if saved is not None and saved.is_file():
            cached = json.loads(saved.read_bytes())
            age = clock() - utc(cached['receipt']['first_received_at_utc'])
            if cached['season'] == season and timedelta(0) <= age <= TTL:
                raw, receipt = cached['body'].encode('utf8'), cached['receipt']
                if receipt['url'] != url:
                    raise ValueError('roster cache URL mismatch')
        if raw is None:
            status, raw = get(url)
            receipt = dict(url=url, http_status=status, first_received_at_utc=clock().astimezone(UTC).isoformat(),
                           raw_sha256=hashlib.sha256(raw).hexdigest(), raw_file=f'{tid}.html')
        rows = parse(raw, receipt, season)
        (folder / receipt['raw_file']).write_bytes(raw)
        snapshot['players'].extend(rows)
        snapshot['receipts'].append(receipt)
        if saved is not None:
            saved.parent.mkdir(parents=True, exist_ok=True)
            write_json(saved, dict(season=season, body=raw.decode('utf8'), receipt=receipt))
    membership(snapshot, clock(), season, snapshot['teams'])
    write_json(folder / 'snapshot.json', snapshot)
    return snapshot


def verify(folder, expected_hash, as_of, season, teams):
    folder = Path(folder)
    if digest(folder / 'snapshot.json') != expected_hash:
        raise ValueError('roster snapshot changed')
    snapshot = json.loads((folder / 'snapshot.json').read_bytes())
    players = []
    for receipt in snapshot['receipts']:
        if receipt['raw_file'] != f"{int(urlsplit(receipt['url']).path.split('/')[2])}.html":
            raise ValueError('invalid roster receipt file')
        players.extend(parse((folder / receipt['raw_file']).read_bytes(), receipt, season))
    if players != snapshot['players']:
        raise ValueError('roster snapshot differs from its source')
    return membership(snapshot, as_of, season, teams)
