"""BetsAPI/bet365 NBA odds archive -> one pregame record per (game, market), joined to game_id and settled.

Protocol: nba_betsapi_odds_protocol.json, frozen before building. Data only: trains or promotes nothing.
The archive is a historical download, so add_time is the provider's stamp and our receipt time is unknown."""
from collections import Counter, defaultdict
from datetime import UTC, datetime
import gzip
import json
import math
from pathlib import Path

from .audit import digest, write_json
from .availability import EASTERN

MARKETS = {
    '18_1': ('ml_game', 'game', 'moneyline'), '18_2': ('spread_game', 'game', 'spread'), '18_3': ('total_game', 'game', 'total'),
    '18_4': ('ml_h1', 'h1', 'moneyline'), '18_5': ('spread_h1', 'h1', 'spread'), '18_6': ('total_h1', 'h1', 'total'),
    '18_7': ('ml_q1', 'q1', 'moneyline'), '18_8': ('spread_q1', 'q1', 'spread'), '18_9': ('total_q1', 'q1', 'total'),
}
PRICES = dict(moneyline=('home_od', 'away_od'), spread=('home_od', 'away_od'), total=('over_od', 'under_od'))
OVERROUND = (-.02, .25)
FRESH_SECONDS = 3600
MIN_IDENTITY = .99
PRETIP_STATE = ('0:0', '1 - 12:00')


def number(value):
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def overround(p1, p2):
    return 1 / p1 + 1 / p2 - 1


def novig(p1, p2):
    a, b = 1 / p1, 1 / p2
    return a / (a + b)


def snapshots(rows, kind, tip):
    """Valid pregame snapshots, one per add_time, ascending. Several handicaps may share a timestamp: keep the most balanced."""
    fields = PRICES[kind]
    by_time = defaultdict(list)
    for r in rows:
        t = int(r['add_time'])
        if t >= tip:
            continue
        if r.get('ss') and not (r['ss'] == PRETIP_STATE[0] and r.get('time_str') == PRETIP_STATE[1]):
            continue
        p1, p2 = number(r.get(fields[0])), number(r.get(fields[1]))
        if p1 is None or p2 is None or p1 <= 1 or p2 <= 1 or not OVERROUND[0] <= overround(p1, p2) <= OVERROUND[1]:
            continue
        line = None
        if kind != 'moneyline':
            line = number(r.get('handicap'))
            if line is None or abs(line) >= 999:
                continue
        by_time[t].append((abs(math.log(p1 / p2)), -int(r['id']), line, p1, p2))
    out = []
    for t, candidates in sorted(by_time.items()):
        _, _, line, p1, p2 = min(candidates)
        out.append(dict(t=t, line=line, p1=p1, p2=p2))
    return out


def point(snap, tip):
    return dict(seconds_before_tip=tip - snap['t'], line=snap['line'], p1=snap['p1'], p2=snap['p2'],
                p1_novig=round(novig(snap['p1'], snap['p2']), 6), overround=round(overround(snap['p1'], snap['p2']), 6))


def outcome(kind, line, home, away):
    """1 = home win / home covers / over, 0 = the other side, None = push."""
    if kind == 'moneyline':
        return None if home == away else int(home > away)
    value = (home - away + line) if kind == 'spread' else (home + away - line)
    return None if value == 0 else int(value > 0)


def periods(scores, swapped=False):
    """(Q1, first half, game) as (official home, official away) pairs; half only when it equals Q1+Q2.

    BetsAPI lists the visiting team first as 'home': swapped=True reverses every pair."""
    pair = lambda k: (int(scores[k]['away']), int(scores[k]['home'])) if swapped else (int(scores[k]['home']), int(scores[k]['away']))
    game, q1 = pair('7'), pair('1')
    half = pair('3') if pair('3') == tuple(a + b for a, b in zip(q1, pair('2'))) else None
    return dict(q1=q1, h1=half, game=game)


def team_resolver(games):
    names = {}
    for g in games:
        for side in ('home', 'away'):
            names[g[side]['team_id']] = g[side]['name']
    cache = {}

    def resolve(name):
        if name not in cache:
            nickname = name.split(' ', 1)[1]
            hits = [tid for tid, full in names.items() if full.endswith(nickname)]
            if len(hits) != 1:
                raise ValueError(f'team name does not resolve to one team: {name!r} -> {hits}')
            cache[name] = hits[0]
        return cache[name]
    return resolve


def read_event(path):
    with gzip.open(path, 'rt', encoding='utf8') as stream:
        return json.loads(stream.read())


def orient(snap, kind):
    """BetsAPI first-listed side -> official home: swap the two prices; a spread line changes sign."""
    if kind == 'total':
        return snap
    line = None if snap['line'] is None else 0.0 - snap['line']
    return dict(t=snap['t'], line=line, p1=snap['p2'], p2=snap['p1'])


def build_rows(event, odds, game, tip, swapped):
    ev = event['event']
    scores = periods(ev['scores'], swapped)
    rows = []
    for key, (name, period, kind) in MARKETS.items():
        snaps = snapshots(odds.get(key) or [], kind, tip)
        if not snaps:
            continue
        if swapped:
            snaps = [orient(s, kind) for s in snaps]
        assert all(s['t'] < tip for s in snaps)
        pts = scores[period]
        first, last = point(snaps[0], tip), point(snaps[-1], tip)
        rows.append(dict(
            game_id=game['game_id'], event_id=ev['id'], season=game['season'], season_type=game['season_type'],
            date=game['date'], market=name, period=period, kind=kind,
            home_team_id=game['home']['team_id'], away_team_id=game['away']['team_id'],
            tip_utc=datetime.fromtimestamp(tip, UTC).isoformat(), n_snapshots=len(snaps), open=first, close=last,
            close_fresh=last['seconds_before_tip'] <= FRESH_SECONDS,
            path=[[tip - s['t'], s['line'], s['p1'], s['p2']] for s in snaps],
            home_points=None if pts is None else pts[0], away_points=None if pts is None else pts[1],
            y_open=None if pts is None else outcome(kind, first['line'], *pts),
            y_close=None if pts is None else outcome(kind, last['line'], *pts)))
    return rows


def percentile(values, q):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * q))] if values else None


def build(raw, reference, protocol, output):
    raw, output = Path(raw), Path(output)
    files = sorted((raw / 'odds').glob('*.json.gz'))
    manifest = {p.name: digest(p) for p in files}
    write_json(output / 'inputs_manifest.json', dict(
        root=raw.as_posix(), files=len(files), reference_sha256=digest(reference), files_sha256=manifest))
    games = json.loads(Path(reference).read_bytes())
    resolve = team_resolver(games)
    by_key = defaultdict(list)
    for g in games:
        by_key[(g['date'], frozenset([g['home']['team_id'], g['away']['team_id']]))].append(g)
    last_reference = max(g['date'] for g in games)
    rows, unmatched, matched_games, with_scores = [], Counter(), {}, 0
    orientation, identity = Counter(), Counter()
    unmatched_ids = defaultdict(list)
    for path in files:
        event = read_event(path)
        ev = event['event']
        tip = int(ev['time'])
        scores = ev.get('scores') or {}
        if ev.get('time_status') != '3' or '7' not in scores:
            unmatched['postponed_no_scores'] += 1
            unmatched_ids['postponed_no_scores'].append(ev['id'])
            continue
        with_scores += 1
        day = datetime.fromtimestamp(tip, UTC).astimezone(EASTERN).date().isoformat()
        home, away = resolve(ev['home']['name']), resolve(ev['away']['name'])
        hits = by_key.get((day, frozenset([home, away])), [])
        reason = None
        if not hits:
            reason = 'after_reference_period' if day > last_reference else 'no_reference_game'
        elif len(hits) > 1:
            reason = 'ambiguous_reference'
        else:
            game, = hits
            swapped = game['home']['team_id'] == away
            identity['checked'] += 1
            if periods(scores, swapped)['game'] != (game['home']['points'], game['away']['points']):
                reason = 'points_mismatch'
            elif game['game_id'] in matched_games:
                reason = 'ambiguous_reference'
            else:
                identity['ok'] += 1
                orientation['swapped' if swapped else 'official_order'] += 1
        if reason:
            unmatched[reason] += 1
            unmatched_ids[reason].append(ev['id'])
            continue
        matched_games[game['game_id']] = ev['id']
        rows += build_rows(event, (event.get('odds') or {}).get('odds') or {}, game, tip, swapped)
    keys = Counter((r['game_id'], r['market']) for r in rows)
    assert max(keys.values(), default=1) == 1
    rows.sort(key=lambda r: (r['date'], r['game_id'], r['market']))
    with (output / 'odds.jsonl.gz').open('wb') as file:
        with gzip.GzipFile(filename='', fileobj=file, mode='wb', mtime=0) as stream:
            for row in rows:
                stream.write((json.dumps(row, sort_keys=True) + '\n').encode())
    per_market = {}
    for name, period, kind in MARKETS.values():
        own = [r for r in rows if r['market'] == name]
        ages = [r['close']['seconds_before_tip'] for r in own]
        per_market[name] = dict(
            rows=len(own), by_season=dict(sorted(Counter(r['season'] for r in own).items())),
            by_season_type=dict(sorted(Counter(r['season_type'] for r in own).items())),
            fresh_close_share=round(sum(r['close_fresh'] for r in own) / len(own), 4) if own else None,
            close_minutes_before_tip=[None if a is None else round(a / 60, 1) for a in (percentile(ages, .05), percentile(ages, .5), percentile(ages, .95))],
            pushes_close=sum(r['y_close'] is None and r['home_points'] is not None for r in own),
            unsettled=sum(r['home_points'] is None for r in own))
    identity_rate = identity['ok'] / identity['checked'] if identity['checked'] else 0
    report = dict(
        protocol=protocol['version'], accepted=identity_rate >= MIN_IDENTITY, events=len(files), events_with_scores=with_scores,
        matched_games=len(matched_games), identity_checked=identity['checked'], identity_ok=identity['ok'],
        identity_rate=round(identity_rate, 5), orientation=dict(orientation), unmatched=dict(unmatched),
        unmatched_event_ids={k: v[:40] for k, v in unmatched_ids.items()}, rows=len(rows),
        reference_games=len(games), reference_games_without_odds=len(games) - len(matched_games),
        markets=per_market, original_pregame_receipt_known=False, bookmaker='bet365 via BetsAPI',
        inputs_manifest_sha256=digest(output / 'inputs_manifest.json'))
    write_json(output / 'coverage.json', report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    freeze = sub.add_parser('freeze', help='record the protocol hash before building')
    freeze.add_argument('--protocol', required=True)
    freeze.add_argument('--output', required=True, type=Path)
    run = sub.add_parser('build')
    run.add_argument('--protocol', required=True)
    run.add_argument('--output', required=True, type=Path, help='folder holding protocol_frozen.json')
    run.add_argument('--raw', default='apps/nba/.local/raw/betsapi_nba_20261024')
    run.add_argument('--reference', default='apps/nba/.local/normalized/nba_extended_box_20261024/games.json')
    a = parser.parse_args()
    frozen = a.output / 'protocol_frozen.json'
    if a.command == 'freeze':
        if frozen.exists():
            raise ValueError('protocol already frozen')
        write_json(frozen, dict(path=Path(a.protocol).as_posix(), sha256=digest(a.protocol),
                                frozen_at_utc=datetime.now(UTC).isoformat()))
        return
    if json.loads(frozen.read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    report = build(a.raw, a.reference, json.loads(Path(a.protocol).read_bytes()), a.output)
    print(json.dumps({k: report[k] for k in ('accepted', 'events', 'events_with_scores', 'matched_games', 'identity_rate',
                                             'orientation', 'unmatched', 'rows', 'reference_games_without_odds')}))


if __name__ == '__main__':
    main()
