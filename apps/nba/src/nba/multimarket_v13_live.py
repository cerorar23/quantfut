"""Prospective v1.3: team markets with point-in-time availability from the official injury report.

Frozen protocol: multimarket_v13_live_protocol.json. Research only (actionable=False); RUN071 is untouched.
"""
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
from zoneinfo import ZoneInfo

import numpy as np
from scipy.special import expit
from scipy.stats import norm

from . import availability as av
from . import injury_pdf
from . import multimarket as m1
from . import multimarket_v12 as v12
from . import multimarket_v13 as v13
from .audit import digest, write_json
from .context import name_key
from .injury_t60 import CONTROL, MISSING

VERSION = 'nba-multimarket-live-1.3.1'
SEASON = '2026-27'
EASTERN = ZoneInfo('America/New_York')
HEADERS = {'User-Agent': 'Mozilla/5.0 NBA research receipt capture', 'Accept': 'application/json,text/html'}
LABELS = dict(winner='Ganador', team_points='Puntos de equipo', game_total='Total del partido')
REFERENCE = 'Umbral estadístico; no es una línea de una casa'
NEXT_DATA = re.compile(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
CARD = re.compile(r'href="/game/([a-z]{2,3}-vs-[a-z]{2,3}-(002\d{7}))"[^>]*data-content="[^"]*?, (\d{4}-\d{2}-\d{2})"')
SLUG = re.compile(r'[a-z]{2,3}-vs-[a-z]{2,3}-002\d{7}')


def http_get(url):
    import httpx
    response = httpx.get(url, headers=HEADERS, timeout=25, follow_redirects=False)
    return response.status_code, response.content


def stamp(value):
    return value.astimezone(UTC).isoformat()


def game_payload(html):
    match = NEXT_DATA.search(html)
    if not match:
        raise ValueError('missing official NBA web payload')
    return json.loads(match[1])['props']['pageProps']['game']


def final_game(raw, receipt):
    """Final team scores from a stored official box score page. Team markets need no player rows."""
    gid = receipt['game_id']
    if (receipt['raw_file'] != 'boxscore.html' or not re.fullmatch(r'https://www\.nba\.com/game/[a-z]{2,3}-vs-[a-z]{2,3}-' + gid + '/box-score', receipt['url'])):
        raise ValueError('official NBA result URL required')
    game = game_payload(raw.decode('utf8'))
    if game['gameId'] != gid or game['gameStatus'] != 3:
        raise ValueError('final NBA web boxscore required')
    for side in ('homeTeam', 'awayTeam'):
        points = game[side]['statistics']['points']
        if type(points) is not int or points < 0 or points != game[side]['score']:
            raise ValueError('final team score does not reconcile')
    if game['homeTeam']['score'] == game['awayTeam']['score']:
        raise ValueError('final team scores do not reconcile')
    return game


def day_cards(day, get=http_get):
    status, body = get(f'https://www.nba.com/games?date={day}')
    if status != 200:
        raise ValueError(f'games page HTTP {status}')
    return sorted({(slug, gid) for slug, gid, label in CARD.findall(body.decode('utf8')) if label == day})


def parse_game(html, slug, received):
    game = game_payload(html)
    gid = game['gameId']
    if not SLUG.fullmatch(slug) or not slug.endswith(gid):
        raise ValueError('slug and NBA game id disagree')
    home, away = game['homeTeam'], game['awayTeam']
    tip = datetime.fromisoformat(game['gameTimeUTC'].replace('Z', '+00:00'))
    return dict(nba_game_id=gid, slug=slug, status=game['gameStatus'], tipoff_utc=tip.isoformat(),
                et_date=tip.astimezone(EASTERN).date().isoformat(),
                home_team=f"{home['teamCity']} {home['teamName']}".strip(), away_team=f"{away['teamCity']} {away['teamName']}".strip(),
                home_tricode=home['teamTricode'], away_tricode=away['teamTricode'],
                home_nba_team_id=game['homeTeamId'], away_nba_team_id=game['awayTeamId'],
                official_url=f'https://www.nba.com/game/{slug}', first_received_at_utc=received)


def upcoming(day, now, get=http_get, clock=None):
    """Games of Eastern date `day` still not started at `now`, one official page each, stamped when received."""
    clock = clock or (lambda: now)
    mappings = []
    for slug, _ in day_cards(day, get):
        status, body = get(f'https://www.nba.com/game/{slug}')
        if status != 200:
            raise ValueError(f'game page HTTP {status}')
        mapping = parse_game(body.decode('utf8'), slug, stamp(clock()))
        mapping['page_sha256'] = hashlib.sha256(body).hexdigest()
        if mapping['et_date'] == day and mapping['status'] == 1 and datetime.fromisoformat(mapping['tipoff_utc']) > now:
            mappings.append(mapping)
    return mappings


GAME_KEYS = {'game_id', 'date', 'season', 'home', 'away', 'box_score_sha256', 'players'}
CLOCK = re.compile(r'(\d{1,2}):(\d{2})|PT(\d{1,2})M(\d{2})(?:\.\d+)?S')


def box_minutes(value):
    """Minutes played from the web box score: 'MM:SS' (archived pages) or 'PTmmMss.ssS' (current pages); '' = did not play."""
    if value == '':
        return 0.
    match = CLOCK.fullmatch(value)
    minutes, seconds = ((match[1], match[2]) if match[1] else (match[3], match[4])) if match else (None, '0')
    if minutes is None or int(seconds) >= 60:
        raise ValueError(f'invalid box score minutes {value!r}')
    return int(minutes) + int(seconds) / 60


def player_rows(game, gid, day):
    """Player rows of one final web box score, in the shape of players.jsonl.gz (the fields availability needs)."""
    rows = []
    for side in ('homeTeam', 'awayTeam'):
        for p in game[side]['players']:
            minutes, points = box_minutes(p['statistics']['minutes']), p['statistics']['points']
            if type(points) is not int or points < 0:
                raise ValueError('invalid box score points')
            rows.append(dict(game_id=gid, date=day, player_id=p['personId'], team_id=game[side]['teamId'],
                             name=f"{p['firstName']} {p['familyName']}".strip(), participated=minutes > 0,
                             minutes=minutes, points=points))
    return rows


def cached_game(cache, gid, day):
    """A final game stored by an earlier run, or None. A stored entry that disagrees with its key is an error."""
    path = None if cache is None else Path(cache) / 'games' / f'{gid}.json'
    if path is None or not path.is_file():
        return None
    game = json.loads(path.read_bytes())
    if set(game) != GAME_KEYS or game['game_id'] != gid or game['date'] != day or game['season'] != SEASON:
        raise ValueError(f'corrupt completed-game cache entry {gid}')
    return game


def cached_day(cache, day):
    path = None if cache is None else Path(cache) / 'days' / f'{day}.json'
    return [tuple(c) for c in json.loads(path.read_bytes())] if path is not None and path.is_file() else None


def store(cache, kind, key, value):
    path = Path(cache) / kind / f'{key}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, value)


def completed(first_day, last_day, get=http_get, cache=None):
    """Finished games of the target season, in the same shape as games.json (points only), plus games not final.

    With `cache`, a final game is downloaded once and a day whose games are all final is never listed again.
    Games not final are never cached; their ids and status are returned so the caller can refuse to seal."""
    out, not_final, day = [], [], date.fromisoformat(first_day)
    while day <= date.fromisoformat(last_day):
        label = day.isoformat()
        cards = cached_day(cache, label)
        listed = cards if cards is not None else day_cards(label, get)
        settled = True
        for slug, gid in listed:
            hit = cached_game(cache, gid, label)
            if hit:
                out.append(hit)
                continue
            status, body = get(f'https://www.nba.com/game/{slug}/box-score')
            if status != 200:
                raise ValueError(f'box score HTTP {status}')
            game = game_payload(body.decode('utf8'))
            if game['gameId'] != gid:
                raise ValueError('box score game id disagrees with the schedule card')
            tip = datetime.fromisoformat(game['gameTimeUTC'].replace('Z', '+00:00'))
            if game['gameStatus'] != 3:
                not_final.append(dict(game_id=gid, date=label, status=game['gameStatus'], tipoff_utc=tip.isoformat()))
                settled = False
                continue
            points = {}
            for side in ('homeTeam', 'awayTeam'):
                value = game[side]['statistics']['points']
                if type(value) is not int or value != game[side]['score']:
                    raise ValueError('final team score does not reconcile')
                points[side] = value
            team = lambda side, home: dict(team_id=game[side]['teamId'], points=points[side],
                                           name=f"{game[side]['teamCity']} {game[side]['teamName']}".strip(), home=home)
            entry = dict(game_id=gid, date=tip.astimezone(EASTERN).date().isoformat(), season=SEASON,
                         home=team('homeTeam', True), away=team('awayTeam', False), box_score_sha256=hashlib.sha256(body).hexdigest())
            if entry['date'] != label:
                raise ValueError('game date disagrees with the schedule card')
            entry['players'] = player_rows(game, gid, label)
            out.append(entry)
            if cache is not None:
                store(cache, 'games', gid, entry)
        if cache is not None and cards is None and settled:
            store(cache, 'days', label, [list(c) for c in listed])
        day += timedelta(days=1)
    return out, not_final


def report_names(day, now):
    """Report file names of Eastern date `day`, newest 15-minute slot first, not after `now`."""
    start = datetime.combine(date.fromisoformat(day), datetime.min.time(), EASTERN)
    cursor = min(now.astimezone(EASTERN), start + timedelta(hours=23, minutes=45))
    cursor = cursor.replace(minute=cursor.minute // 15 * 15, second=0, microsecond=0)
    while cursor >= start:
        yield f"Injury-Report_{day}_{cursor.strftime('%I_%M%p')}.pdf"
        cursor -= timedelta(minutes=15)


def capture_report(day, now, folder, get=http_get, clock=None):
    """Newest official report of `day` published by `now`. Returns the parsed report or None.

    403/404 is how the bucket answers for a slot without a file; the first one is checked against a control file known
    to exist, so a real block stops the seal instead of passing for "no report". The receipt is stamped after download."""
    clock = clock or (lambda: now)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    checked = False
    for name in report_names(day, now):
        url = 'https://ak-static.cms.nba.com/referee/injury/' + name
        status, body = get(url)
        if status in MISSING:
            if not checked:
                control, proof = get(CONTROL)
                if control != 200 or not proof.startswith(b'%PDF-'):
                    raise ValueError(f'injury report source blocked (control file HTTP {control})')
                checked = True
            continue
        if status != 200 or not body.startswith(b'%PDF-'):
            raise ValueError(f'injury report HTTP {status}')
        received = stamp(clock())
        path = folder / name
        if path.exists():
            raise ValueError('refuse to overwrite a captured report')
        path.write_bytes(body)
        report = injury_pdf.extract_report(path, url, received)
        report['pdf_file'] = name
        report['pdf_path'] = name
        return report
    return None


def history_index(players):
    by_name, history = defaultdict(set), defaultdict(list)
    for r in players:
        by_name[name_key(r['name'])].add(str(r['player_id']))
        if r['participated'] and r['minutes'] > 0:
            history[str(r['player_id'])].append((r['date'], r['minutes'], r['points']))
    for rows in history.values():
        rows.sort()
    return {k: next(iter(v)) for k, v in by_name.items() if len(v) == 1}, history


def trailing_value(rows, day, window=20, max_days=370, minimum=5):
    cut = datetime.fromisoformat(day)
    prior = [h for h in rows if h[0] < day][-window:]
    recent = [h for h in prior if 0 < (cut - datetime.fromisoformat(h[0])).days <= max_days]
    if len(recent) < minimum:
        return None
    return float(np.mean([h[1] for h in recent])), float(np.mean([h[2] for h in recent]))


def report_name(raw):
    last, _, first = raw.partition(', ')
    return name_key(f'{first} {last}')


def game_report_entries(report, mapping, ids, history):
    """(entries per team id, availability summary) from one parsed report; only rows of this game."""
    if report is None:
        return None, dict(state='sin_reporte_valido', reason='no_report')
    tip = datetime.fromisoformat(mapping['tipoff_utc'])
    limit = tip - av.LEAD
    if (datetime.fromisoformat(report['report_timestamp_utc']) > limit
            or datetime.fromisoformat(report['first_received_at_utc']) > limit):
        return None, dict(state='sin_reporte_valido', reason='report_too_close_to_tipoff')
    matchup = f"{mapping['away_tricode']}@{mapping['home_tricode']}"
    day = datetime.strptime(mapping['et_date'], '%Y-%m-%d').strftime('%m/%d/%Y')
    rows = [r for r in report['rows'] if r['matchup'] == matchup and r['game_date'] == day]
    if not rows:
        return None, dict(state='sin_reporte_valido', reason='game_not_in_report')
    sides = {name_key(mapping['home_team']): mapping['home_nba_team_id'], name_key(mapping['away_team']): mapping['away_nba_team_id']}
    entries = {mapping['home_nba_team_id']: [], mapping['away_nba_team_id']: []}
    submitted = {mapping['home_nba_team_id']: None, mapping['away_nba_team_id']: None}
    summary = dict(listed=0, used=0, no_history=0, unknown_player=0, unknown_team=0)
    for r in rows:
        team = sides.get(name_key(r['team']))
        if team is None:
            summary['unknown_team'] += 1
            continue
        submitted[team] = bool(r['report_submitted'])
        if not r['player_name_raw'] or r['status_raw'] not in av.STATUSES:
            continue
        summary['listed'] += 1
        player = ids.get(report_name(r['player_name_raw']))
        if player is None:
            summary['unknown_player'] += 1
            continue
        value = trailing_value(history[player], mapping['et_date'])
        if value is None:
            summary['no_history'] += 1
            continue
        entries[team].append((player, r['status_raw'], value[0], value[1]))
        summary['used'] += 1
    summary.update(state='reporte_aplicado', report_file=report['pdf_file'], report_url=report['source_url'],
                   report_timestamp_utc=report['report_timestamp_utc'], report_received_at_utc=report['first_received_at_utc'],
                   report_sha256=report['pdf_sha256'],
                   teams_not_submitted=[t for t, s in submitted.items() if s is not True])
    return entries, summary


def fit_team(train):
    """v1.3 team-market parameters (identical to the first half of v13.team_predictions)."""
    prior = np.concatenate([v12.ELO_PRIOR, [0., 0.]])
    w = v12.fit_ridge_logistic(v13.winner_x(train), [r['home_win'] for r in train], prior, .002)
    shifts, residuals = {}, []
    for side in ('home', 'away'):
        x = v13.shift_x(train, side)
        resid = np.array([r[side + '_points'] - r[side + '_mean'] for r in train])
        shifts[side] = np.linalg.solve(x.T @ x + 5 * np.diag([1., 1., 1., 1., 0.]), x.T @ resid)
        residuals.append(resid - x @ shifts[side])
    return dict(winner_weights=w.tolist(), shifts={k: v.tolist() for k, v in shifts.items()},
                covariance=np.cov(np.vstack(residuals)).tolist(), train_games=len(train))


def predict_team(test, fit):
    w, cov = np.array(fit['winner_weights']), np.array(fit['covariance'])
    p_win = expit(v13.winner_x(test) @ w)
    mean = {s: np.array([r[s + '_mean'] for r in test]) + v13.shift_x(test, s) @ np.array(fit['shifts'][s]) for s in ('home', 'away')}
    out = []
    for i, (r, p) in enumerate(zip(test, p_win)):
        sd_home, sd_away, sd_total = np.sqrt(cov[0, 0]), np.sqrt(cov[1, 1]), np.sqrt(cov.sum())
        line_h, line_a = np.floor(r['home_baseline']) + .5, np.floor(r['away_baseline']) + .5
        line_t = np.floor(r['home_baseline'] + r['away_baseline']) + .5
        out.append(dict(
            winner=float(p),
            home=dict(mean=float(mean['home'][i]), sd=float(sd_home), line=float(line_h), p=float(norm.sf(line_h, mean['home'][i], sd_home))),
            away=dict(mean=float(mean['away'][i]), sd=float(sd_away), line=float(line_a), p=float(norm.sf(line_a, mean['away'][i], sd_away))),
            total=dict(mean=float(mean['home'][i] + mean['away'][i]), sd=float(sd_total), line=float(line_t),
                       p=float(norm.sf(line_t, mean['home'][i] + mean['away'][i], sd_total)))))
    return out


def fit_model(players, games, protocol, v12_protocol, injury_path, api_dir, sources):
    """Fit once on the scored seasons before the target season. `sources` = file hashes to pin."""
    seasons = sorted({g['season'] for g in games})
    if protocol['target_season'] in seasons:
        raise ValueError('training data already contains the target season')
    start, end = v12.training_window(protocol['target_season'], seasons, v12_protocol)
    train_seasons = [s for s in seasons if s > v12_protocol['burn_in_season'] and start <= v12.season_start(s) < end]
    index = {(r['game_id'], str(r['player_id'])): r for r in players}
    tips = av.tipoff_map(api_dir, games)
    statuses, observed = av.status_map(av.read_reports(injury_path), tips)
    entries = av.trailing_entries(players, games, statuses, observed)
    game_season = {g['game_id']: g['season'] for g in games}
    table = av.play_table(statuses, index, {g for g in observed if game_season.get(g) in train_seasons})
    train = [dict(r) for r in v12.team_games(games, v12_protocol) if r['season'] in train_seasons]
    v13.attach(train, entries, table)
    return dict(version=VERSION, protocol_version=protocol['version'], train_seasons=train_seasons,
                fit=fit_team(train), play_probability=table, observed_share=float(np.mean([r['observed'] for r in train])),
                inputs=sources)


def feature_rows(games, completed_games, mappings, v12_protocol):
    """One v1.2 feature row per upcoming game; ratings, form and rest come only from strictly earlier days."""
    if len({m['et_date'] for m in mappings}) != 1:
        raise ValueError('one Eastern date per cohort')
    placeholders = [dict(game_id=m['nba_game_id'], date=m['et_date'], season=SEASON,
                         home=dict(team_id=m['home_nba_team_id'], points=0), away=dict(team_id=m['away_nba_team_id'], points=0))
                    for m in mappings]
    if any(g['date'] >= mappings[0]['et_date'] for g in completed_games):
        raise ValueError('completed games must be earlier than the cohort date')
    rows = {r['game_id']: r for r in v12.team_games([*games, *completed_games, *placeholders], v12_protocol)}
    missing = [m['nba_game_id'] for m in mappings if m['nba_game_id'] not in rows]
    if missing:
        raise ValueError(f'insufficient team history for {missing}')
    return [dict(rows[m['nba_game_id']]) for m in mappings]


def cohort_forecasts(model, mappings, rows, summaries, entries, last_dates, sealed_at):
    table = model['play_probability']
    games_out, forecasts = [], []
    for m, r, s in zip(mappings, rows, summaries):
        v13.attach([r], {m['nba_game_id']: entries[m['nba_game_id']]} if entries[m['nba_game_id']] else {}, table)
    predictions = predict_team(rows, model['fit'])
    for m, r, s, p in zip(mappings, rows, summaries, predictions):
        if sealed_at >= datetime.fromisoformat(m['tipoff_utc']):
            raise ValueError('cannot seal after tipoff')
        common = dict(event_id=m['nba_game_id'], nba_game_id=m['nba_game_id'], sealed_at_utc=stamp(sealed_at), actionable=False,
                      reference=REFERENCE, last_feature_date=last_dates[m['nba_game_id']], conditional_participation=False)

        def add(market, estimate, low, high, line, prob, **extra):
            forecasts.append(dict(common, market=market, market_label=LABELS[market], estimate=float(estimate), range_low=float(low),
                                  range_high=float(high), line=float(line), probability_over=float(prob),
                                  probability_under=float(1 - prob), **extra))
        add('winner', p['winner'], 0, 1, .5, p['winner'], player_id='winner', player='Ganador: ' + m['home_team'],
            team_id=m['home_nba_team_id'])
        for side, key in (('home', 'home'), ('away', 'away')):
            q = p[key]
            add('team_points', q['mean'], max(0, norm.ppf(.1, q['mean'], q['sd'])), norm.ppf(.9, q['mean'], q['sd']), q['line'], q['p'],
                player_id=m[side + '_nba_team_id'], player=m[side + '_team'], team_id=m[side + '_nba_team_id'])
        q = p['total']
        add('game_total', q['mean'], max(0, norm.ppf(.1, q['mean'], q['sd'])), norm.ppf(.9, q['mean'], q['sd']), q['line'], q['p'],
            player_id='total', player='Total del partido', team_id=None)
        games_out.append(dict(event_id=m['nba_game_id'], nba_game_id=m['nba_game_id'], slug=m['slug'], official_url=m['official_url'],
                              tipoff_utc=m['tipoff_utc'], home_team=m['home_team'], away_team=m['away_team'],
                              home_nba_team_id=m['home_nba_team_id'], away_nba_team_id=m['away_nba_team_id'],
                              availability=dict(s, missing_points_home=r['mp_home'], missing_points_away=r['mp_away'],
                                                missing_minutes_home=r['mm_home'], missing_minutes_away=r['mm_away'])))
    return games_out, forecasts


def sealed_games(root):
    """NBA game ids already sealed in any cohort under `root` (a game is forecast once)."""
    root = Path(root)
    return {g['nba_game_id'] for p in root.glob('*/bundle.json') for g in json.loads(p.read_bytes())['games']} if root.is_dir() else set()


def seal(model_dir, out, day, players, games, protocol, v12_protocol, now=None, get=http_get, first_completed_day=None, exclude=(), cache=None,
         clock=None, lead=None):
    """Capture schedule + latest official report, forecast, and write a sealed cohort folder (never overwritten).

    `now` decides which games and which report; `clock` stamps receipts and the seal when they really happen (default:
    `now`). With `lead=(low, high)` only games whose tipoff is more than `low` and at most `high` after `now` are sealed."""
    now = now or datetime.now(UTC)
    clock = clock or (lambda: now)
    model_dir, out = Path(model_dir), Path(out)
    model = json.loads((model_dir / 'model.json').read_bytes())
    if model['inputs'].get('live_module_sha256') != digest(__file__):
        raise ValueError('model was fitted by a different live module')
    if out.exists():
        raise ValueError('cohort folder already exists')
    mappings = [m for m in upcoming(day, now, get, clock) if m['nba_game_id'] not in set(exclude)]
    if lead:
        mappings = [m for m in mappings if lead[0] < datetime.fromisoformat(m['tipoff_utc']) - now <= lead[1]]
    if not mappings:
        raise ValueError('no games left to seal for this date')
    first = first_completed_day or protocol.get('season_first_day', '2026-10-20')
    done, not_final = completed(first, (date.fromisoformat(day) - timedelta(days=1)).isoformat(), get, cache) if first < day else ([], [])
    stuck = [g for g in not_final if g['status'] != 1]
    if stuck:
        # status 1 on a past date is a postponed game (never played); anything else means the feed lags and rest/form would be wrong
        raise ValueError(f'past games not final: {[(g["game_id"], g["status"]) for g in stuck]}')
    out.mkdir(parents=True)
    report = capture_report(day, now, out / 'reports', get, clock)
    # target-season box scores join the historical rows, so player values follow the current season
    ids, history = history_index([*players, *(r for g in done for r in g['players'])])
    entries, summaries = {}, []
    for m in mappings:
        e, s = game_report_entries(report, m, ids, history)
        entries[m['nba_game_id']] = e
        summaries.append(s)
    rows = feature_rows(games, done, mappings, v12_protocol)
    last_dates = {}
    for m in mappings:
        previous = [g['date'] for g in (*games, *done) if m['home_nba_team_id'] in (g['home']['team_id'], g['away']['team_id'])
                    or m['away_nba_team_id'] in (g['home']['team_id'], g['away']['team_id'])]
        last_dates[m['nba_game_id']] = max(previous)
    sealed_at = clock()
    games_out, forecasts = cohort_forecasts(model, mappings, rows, summaries, entries, last_dates, sealed_at)
    shutil.copyfile(model_dir / 'model.json', out / 'model.json')
    write_json(out / 'schedule.json', dict(received_at_utc=max(m['first_received_at_utc'] for m in mappings), games=mappings))
    # player rows are not repeated here: each game keeps the hash of the box score they were read from
    write_json(out / 'completed_games.json', dict(first_day=first, games=[{k: v for k, v in g.items() if k != 'players'} for g in done],
                                                  not_final=not_final))
    bundle = dict(version=VERSION, created_at_utc=stamp(sealed_at), cohort_date=day, protocol_sha256=digest(Path(protocol['_path'])),
                  model_sha256=digest(out / 'model.json'), schedule_sha256=digest(out / 'schedule.json'),
                  completed_sha256=digest(out / 'completed_games.json'), code_sha256=digest(__file__),
                  availability_sha256=digest(Path(av.__file__)), games=games_out, forecasts=forecasts,
                  report=None if report is None else {k: report[k] for k in ('pdf_file', 'source_url', 'report_timestamp_utc',
                                                                             'first_received_at_utc', 'pdf_sha256', 'named_players')},
                  train_seasons=model['train_seasons'], actionable=False, original_pilot_unchanged=True)
    write_json(out / 'bundle.json', bundle)
    write_json(out / 'bundle.seal.json', dict(sha256=digest(out / 'bundle.json'), created_at_utc=stamp(sealed_at), external_anchor=False))
    return dict(games=len(games_out), sealed_at_utc=stamp(sealed_at), forecasts=len(forecasts), report=bundle['report'] and bundle['report']['pdf_file'],
                availability={g['event_id']: g['availability']['state'] for g in games_out})


def capture_results(cohort, now=None, get=http_get):
    """Official final box score for each game that should be over. Non-final captures are discarded, never kept."""
    from .paper import capture_official_result
    now, cohort = now or datetime.now(UTC), Path(cohort)
    bundle = json.loads((cohort / 'bundle.json').read_bytes())
    stored, retry = [], []
    for g in bundle['games']:
        target = cohort / 'results' / g['nba_game_id']
        if target.exists() or now < datetime.fromisoformat(g['tipoff_utc']) + timedelta(hours=3):
            continue
        temp = cohort / 'results' / (g['nba_game_id'] + '.tmp')
        if temp.exists():
            shutil.rmtree(temp)
        temp.parent.mkdir(exist_ok=True)
        receipt_path = capture_official_result(g['nba_game_id'], temp, g['slug'])
        receipt = json.loads(receipt_path.read_bytes())
        try:
            if receipt['http_status'] != 200:
                raise ValueError('not received')
            final_game((temp / receipt['raw_file']).read_bytes(), receipt)
        except (ValueError, KeyError, TypeError):
            shutil.rmtree(temp)
            retry.append(g['nba_game_id'])
            continue
        temp.rename(target)
        stored.append(g['nba_game_id'])
    return dict(stored=stored, retry=retry)


def main():
    import argparse
    root = Path(__file__).parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['fit', 'forecast', 'results'])
    parser.add_argument('--output', help='new folder (fit: model folder; forecast: cohort folder)')
    parser.add_argument('--data', help='fit: folder with players.jsonl.gz and games.json')
    parser.add_argument('--injuries', help='fit: retrospective reports.jsonl.gz')
    parser.add_argument('--api-dir', help='fit: api-sports games_*.json folder')
    parser.add_argument('--model', help='forecast: model folder from fit')
    parser.add_argument('--date', help='forecast: Eastern date YYYY-MM-DD of the games')
    parser.add_argument('--cohort', help='results: sealed cohort folder')
    parser.add_argument('--first-day', help='forecast: first finished game day of the target season')
    parser.add_argument('--exclude-sealed', help='forecast: cohorts root; games already sealed there are skipped')
    parser.add_argument('--cache', help='forecast: folder where finished games are stored so each box score is downloaded once')
    a = parser.parse_args()
    protocol_path = root / 'multimarket_v13_live_protocol.json'
    protocol = dict(json.loads(protocol_path.read_bytes()), _path=str(protocol_path))
    v12_protocol = json.loads((root / 'multimarket_v12_protocol.json').read_bytes())
    if a.command == 'results':
        print(json.dumps(capture_results(a.cohort)))
        return
    if not a.output:
        parser.error('--output is required')
    data = Path(a.data) if a.data else None
    if a.command == 'fit':
        players, games = m1.read_rows(data / 'players.jsonl.gz'), json.loads((data / 'games.json').read_bytes())
        sources = dict(live_module_sha256=digest(__file__), availability_sha256=digest(Path(av.__file__)),
                       multimarket_v13_sha256=digest(Path(v13.__file__)), multimarket_v12_sha256=digest(Path(v12.__file__)),
                       protocol_sha256=digest(protocol_path), v12_protocol_sha256=digest(root / 'multimarket_v12_protocol.json'),
                       players_sha256=digest(data / 'players.jsonl.gz'), games_sha256=digest(data / 'games.json'),
                       injuries_sha256=digest(a.injuries),
                       api_sha256=hashlib.sha256(''.join(digest(p) for p in sorted(Path(a.api_dir).glob('games_*.json'))).encode()).hexdigest())
        model = fit_model(players, games, protocol, v12_protocol, a.injuries, a.api_dir, sources)
        out = Path(a.output)
        out.mkdir(parents=True, exist_ok=False)
        write_json(out / 'model.json', model)
        print(json.dumps(dict(train_seasons=model['train_seasons'], play_probability=model['play_probability'])))
        return
    players, games = m1.read_rows(data / 'players.jsonl.gz'), json.loads((data / 'games.json').read_bytes())
    clock = lambda: datetime.now(UTC)
    print(json.dumps(seal(a.model, a.output, a.date, players, games, protocol, v12_protocol, now=clock(), first_completed_day=a.first_day,
                           exclude=sealed_games(a.exclude_sealed) if a.exclude_sealed else (), cache=a.cache, clock=clock)))


if __name__ == '__main__':
    main()
