"""Prospective market check: the current Pinnacle price captured when a cohort is sealed, set against the sealed winner forecasts.

Research only (actionable=False): it measures whether the sealed probabilities add information over the market and never
produces a bet. Protocol: nba_vs_market_live_protocol.json, frozen before any price was captured.

The capture step only reads the sealed bundle, and nothing here is imported by the forecast code, so a price can never
influence a forecast. Spending is one request of about 1 credit per capture, blocked in code before 2026-11-01."""
from collections import defaultdict
from datetime import UTC, datetime, timedelta
import json
import math
from pathlib import Path
import re

import numpy as np

from . import market_compare as mc
from . import odds_history as oh
from .audit import digest, write_json
from .multimarket_live_dashboard import LiveCohort, utc

ENDPOINT = 'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
EXPECTED_COST = 1
PHASES = ('seal', 'close')
MAX_SEAL_GAP = timedelta(minutes=15)
MAX_BOOK_AGE = timedelta(minutes=30)
START_TOLERANCE = timedelta(minutes=10)
EDGE_MIN = .02
MIN_GAMES = 400
COVERAGE_MINIMUM = .85
MAX_DAILY_REQUESTS = 2    # one seal-phase and one close-phase price per UTC day
MAX_MONTHLY_CREDITS = 70  # about 2 x 31 days; the account is shared with football
CLOSE_WINDOW = (timedelta(minutes=30), timedelta(minutes=10))  # close price taken this long before the first tipoff


class LateCapture(ValueError):
    """The seal-phase price would not describe the moment the forecast was sealed."""


def read_key(path):
    """The provider key from a file holding it alone (the server's secret file) or as ODDS_API_KEY=... (a .env). Never echoed."""
    text = Path(path).read_text(encoding='utf-8-sig').strip()
    match = re.search(r'^ODDS_API_KEY\s*=\s*(.+)$', text, re.M)
    key = (match.group(1) if match else text).strip().strip('"\'')
    if not re.fullmatch(r'[A-Za-z0-9]{16,64}', key):
        raise ValueError('the key file does not hold exactly one provider key')
    return key


def market_folder(cohort, market_root=None):
    """Where a cohort's prices live: beside it by default, or under market_root/<cohort name> so cohorts can be mounted read-only."""
    return Path(market_root) / Path(cohort).name if market_root else Path(cohort) / 'market'


class LedgerRefusal(ValueError):
    """A shared-budget rule stopped the request before it was sent."""


def ledger_entries(ledger):
    path = Path(ledger) / 'requests.jsonl'
    return [json.loads(line) for line in path.read_text(encoding='utf8').splitlines() if line.strip()] if path.exists() else []


def ledger_check(ledger, now, reserve):
    """Budget rules kept outside the cohorts: halt file, requests per UTC day, credits per UTC month, last known balance."""
    halt = Path(ledger) / 'halt'
    if halt.exists():
        raise LedgerRefusal('capture halted by an earlier failure; a person must read and remove ' + halt.name)
    entries = ledger_entries(ledger)
    today = [e for e in entries if e['at_utc'][:10] == now.date().isoformat()]
    if len(today) >= MAX_DAILY_REQUESTS:
        raise LedgerRefusal(f'daily limit of {MAX_DAILY_REQUESTS} requests reached')
    month = sum(e['credits'] for e in entries if e['at_utc'][:7] == now.isoformat()[:7])
    if month + EXPECTED_COST > MAX_MONTHLY_CREDITS:
        raise LedgerRefusal(f'monthly limit of {MAX_MONTHLY_CREDITS} credits reached')
    known = [e['remaining'] for e in entries if e.get('remaining') is not None]
    if known and known[-1] - EXPECTED_COST < reserve:
        raise LedgerRefusal('shared credit reserve would be breached')


def ledger_record(ledger, entry, halt_reason=None):
    folder = Path(ledger)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'requests.jsonl').open('a', encoding='utf8') as stream:
        stream.write(json.dumps(entry) + '\n')
    if halt_reason:
        write_json(folder / 'halt', dict(reason=halt_reason, at_utc=entry['at_utc'], cohort=entry.get('cohort'), phase=entry.get('phase')))


def canon(name):
    return oh.TEAM_ALIASES.get(name, name)


def sealed_at(bundle):
    return max(utc(f['sealed_at_utc']) for f in bundle['forecasts'])


def capture(cohort, key, client, now, phase='seal', reserve=2000, market_root=None, ledger=None):
    """One request for the current Pinnacle h2h prices, stored write-once. No retry.

    Prices go beside the cohort (default) or under market_root, so the sealed cohort can stay read-only for the process that
    holds the key. With a ledger the shared-budget rules apply and any failure leaves a halt file."""
    if now < oh.NOT_BEFORE:
        raise PermissionError(f'live price capture is blocked before {oh.NOT_BEFORE.date()} (shared credit reserve)')
    if phase not in PHASES:
        raise ValueError('unknown phase')
    cohort = Path(cohort)
    bundle = LiveCohort(cohort).bundle  # verifies the seal, the hashes and every forecast
    sealed = sealed_at(bundle)
    if now < sealed:
        raise ValueError('cannot capture before the cohort is sealed')
    if now >= max(utc(g['tipoff_utc']) for g in bundle['games']):
        raise ValueError('every game of the cohort has started')
    if phase == 'seal' and now - sealed > MAX_SEAL_GAP:
        raise LateCapture(f'seal-phase price must be taken within {MAX_SEAL_GAP} of the seal')
    folder = market_folder(cohort, market_root)
    if phase == 'close' and not (folder / 'seal.json').exists():
        raise ValueError('a close price needs the seal-phase price first')
    if (folder / f'{phase}.json').exists():
        raise ValueError(f'{phase} price already captured for this cohort')
    log = folder / 'attempts.jsonl'
    remaining = None
    if log.exists():
        known = [json.loads(line).get('remaining') for line in log.read_text(encoding='utf8').splitlines()]
        remaining = next((x for x in reversed(known) if x is not None), None)
    if remaining is not None and remaining - EXPECTED_COST < reserve:
        raise ValueError('shared credit reserve would be breached')
    if ledger is not None:
        ledger_check(ledger, now, reserve)
    folder.mkdir(parents=True, exist_ok=True)
    try:
        response = client.get(ENDPOINT, params=dict(apiKey=key, bookmakers='pinnacle', markets='h2h', oddsFormat='decimal'), timeout=60)
    except OSError as exc:  # no answer: the credit may or may not have been spent, so it counts against the caps; no retry
        if ledger is not None:
            ledger_record(ledger, dict(at_utc=now.isoformat(), cohort=cohort.name, phase=phase, http_status=None, credits=EXPECTED_COST,
                                       remaining=None, error=type(exc).__name__))
        raise
    used = int(response.headers.get('x-requests-last', EXPECTED_COST))
    left = response.headers.get('x-requests-remaining')
    attempt = dict(phase=phase, at_utc=now.isoformat(), http_status=response.status_code, credits=used,
                   remaining=int(left) if left is not None else None)
    with log.open('a', encoding='utf8') as stream:
        stream.write(json.dumps(attempt) + '\n')
    problem = (f'http_{response.status_code}' if response.status_code != 200
               else 'unexpected_cost' if used != EXPECTED_COST else None)
    if ledger is not None:
        ledger_record(ledger, dict(attempt, cohort=cohort.name), halt_reason=problem)
    if response.status_code != 200:
        return dict(stored=False, stop=problem)
    raw = folder / f'{phase}_raw.json'
    if raw.exists():
        raise ValueError('refuse to overwrite a stored response')
    raw.write_bytes(response.content)
    write_json(folder / f'{phase}.json', dict(
        phase=phase, received_at_utc=now.isoformat(), http_status=200, raw_sha256=digest(raw), credits=used, remaining=attempt['remaining'],
        bundle_sha256=digest(cohort / 'bundle.json'), sealed_at_utc=sealed.isoformat(), request=dict(
            url=ENDPOINT, bookmakers='pinnacle', markets='h2h', oddsFormat='decimal'), actionable=False))
    return dict(stored=True, stop=problem, credits=used, remaining=attempt['remaining'])


def pending_phase(cohort, market_root, now):
    """Which price this cohort needs right now, from the sealed bundle alone (cheap; the capture itself verifies the seal)."""
    bundle = json.loads((Path(cohort) / 'bundle.json').read_bytes())
    folder = market_folder(cohort, market_root)
    sealed = sealed_at(bundle)
    tips = [utc(g['tipoff_utc']) for g in bundle['games']]
    if now >= max(tips):
        return None
    if not (folder / 'seal.json').exists():
        return 'seal' if timedelta(0) <= now - sealed <= MAX_SEAL_GAP else None
    early, late = CLOSE_WINDOW
    if not (folder / 'close.json').exists() and min(tips) - early <= now < min(tips) - late:
        return 'close'
    return None


def capture_pending(cohorts, market_root, key, client, now, ledger, reserve=2000):
    """Idempotent step for the producer's cron tick: take every price that is due, and nothing else.

    Seal-phase right after a cohort is sealed; close-phase 30-10 minutes before its first tipoff. A tick with nothing due
    makes no request. A refusal (budget, halt, timing) is reported, never retried."""
    if now < oh.NOT_BEFORE:
        return [dict(blocked_until=oh.NOT_BEFORE.date().isoformat())]
    out = []
    for folder in sorted(p for p in Path(cohorts).iterdir() if (p / 'bundle.seal.json').exists()) if Path(cohorts).is_dir() else []:
        try:
            phase = pending_phase(folder, market_root, now)
        except (OSError, ValueError, KeyError):
            out.append(dict(cohort=folder.name, skipped='unreadable_bundle'))
            continue
        if phase is None:
            continue
        try:
            out.append(dict(cohort=folder.name, phase=phase, **capture(folder, key, client, now, phase, reserve, market_root, ledger)))
        except (ValueError, PermissionError) as exc:
            out.append(dict(cohort=folder.name, phase=phase, refused=str(exc)))
            if isinstance(exc, LedgerRefusal):
                break
    return out


def read_phase(cohort, phase, market_root=None):
    """(receipt, parsed body) of a stored capture, or None. A changed response is an error."""
    folder = market_folder(cohort, market_root)
    if not (folder / f'{phase}.json').exists():
        return None
    receipt = json.loads((folder / f'{phase}.json').read_bytes())
    raw = folder / f'{phase}_raw.json'
    if digest(raw) != receipt['raw_sha256']:
        raise ValueError('stored price response changed')
    return receipt, json.loads(raw.read_bytes())


def price_rows(body, received, games):
    """event_id -> Pinnacle price row, plus a count of why other games have none."""
    events = body if isinstance(body, list) else []
    out, reasons = {}, defaultdict(int)
    for game in games:
        tip = utc(game['tipoff_utc'])
        found = [e for e in events if canon(e.get('home_team')) == game['home_team'] and canon(e.get('away_team')) == game['away_team']
                 and abs(utc(e['commence_time']) - tip) <= START_TOLERANCE]
        if len(found) != 1:
            reasons['no_event' if not found else 'ambiguous_event'] += 1
            continue
        event = found[0]
        if utc(event['commence_time']) <= received:
            reasons['already_started'] += 1
            continue
        book, market = oh.pinnacle_prices(event)
        if market is None:
            reasons['no_pinnacle'] += 1
            continue
        updated = utc(market.get('last_update') or book['last_update'])
        prices = {canon(o['name']): o['price'] for o in market['outcomes']}
        home, away = prices.get(game['home_team']), prices.get(game['away_team'])
        if (not home or not away or not all(map(math.isfinite, (home, away))) or home <= 1 or away <= 1
                or updated > received or received - updated > MAX_BOOK_AGE):
            reasons['invalid_or_stale_price'] += 1
            continue
        inv_h, inv_a = 1 / home, 1 / away
        out[game['event_id']] = dict(home_decimal=home, away_decimal=away, book_updated_utc=updated.isoformat(),
                                     overround=inv_h + inv_a - 1, home_no_vig=inv_h / (inv_h + inv_a),
                                     home_no_vig_power=oh.power_no_vig(home, away),
                                     minutes_to_tipoff=(tip - received).total_seconds() / 60)
    return out, dict(reasons)


def cohort_rows(cohort, now, market_root=None):
    """Comparison rows of one cohort (winner forecasts with an official result and a valid seal-phase price) and its coverage."""
    live = LiveCohort(cohort)
    bundle, data = live.bundle, live.data(now)
    sealed = sealed_at(bundle)
    prices, reasons = {}, {}
    for phase in PHASES:
        stored = read_phase(cohort, phase, market_root)
        if stored is None:
            continue
        receipt, body = stored
        received = utc(receipt['received_at_utc'])
        if receipt['bundle_sha256'] != digest(Path(cohort) / 'bundle.json') or received < sealed:
            raise ValueError('stored price does not belong to this sealed cohort')
        if phase == 'seal' and received - sealed > MAX_SEAL_GAP:
            raise ValueError('seal-phase price taken too late')
        prices[phase], reasons[phase] = price_rows(body, received, bundle['games'])
    coverage = dict(sealed=len(bundle['games']), evaluated=0, evaluated_with_price=0, price_reasons=reasons.get('seal', {}),
                    captured=sorted(prices))
    rows = []
    for p in data['predictions']:
        if p['market'] != 'winner' or p['result']['status'] != 'evaluated':
            continue
        coverage['evaluated'] += 1
        seal = prices.get('seal', {}).get(p['event_id'])
        if seal is None:
            continue
        coverage['evaluated_with_price'] += 1
        close = prices.get('close', {}).get(p['event_id'])
        rows.append(dict(game_id=p['event_id'], date=bundle['cohort_date'], model=p['probability_over'], y=int(p['result']['actual']),
                         market=seal['home_no_vig'], market_power=seal['home_no_vig_power'], overround=seal['overround'],
                         minutes_to_tipoff=seal['minutes_to_tipoff'], market_close=close['home_no_vig'] if close else None))
    return rows, coverage


def clv(rows, protocol):
    """Description only. Does the market move toward the model between the seal-phase and the close-phase price?"""
    pairs = [r for r in rows if r.get('market_close') is not None]
    if not pairs:
        return dict(n=0)
    edge = np.array([r['model'] - r['market'] for r in pairs])
    move = np.array([r['market_close'] - r['market'] for r in pairs])
    dates = sorted({r['date'] for r in pairs})
    day = np.array([dates.index(r['date']) for r in pairs])

    def stats(weights):
        decisive = (np.abs(edge) > EDGE_MIN) & (move != 0)
        w = weights[day]
        share = float(np.sum(w * decisive * (np.sign(edge) == np.sign(move))) / np.sum(w * decisive)) if np.sum(w * decisive) else None
        centred = edge - np.average(edge, weights=w)
        slope = float(np.sum(w * centred * (move - np.average(move, weights=w))) / np.sum(w * centred ** 2)) if np.sum(w * centred ** 2) else None
        return share, slope
    share, slope = stats(np.ones(len(dates)))
    rng = np.random.default_rng(protocol['seed'])
    draws = [stats(np.bincount(rng.integers(0, len(dates), len(dates)), minlength=len(dates)).astype(float)) for _ in range(protocol['bootstrap'])]
    interval = lambda k: np.quantile([d[k] for d in draws if d[k] is not None], [.025, .975]).tolist() if any(d[k] is not None for d in draws) else None
    return dict(n=len(pairs), decisive=int(np.sum((np.abs(edge) > EDGE_MIN) & (move != 0))), same_direction_share=share,
                same_direction_ci95=interval(0), slope_move_on_edge=slope, slope_ci95=interval(1), description_only=True)


def decide(report):
    """The frozen rule: once at MIN_GAMES valid evaluated games and once at season end; looks in between are interim."""
    if report['games'] < MIN_GAMES:
        return dict(verdict='interim', reason=f'{report["games"]} of {MIN_GAMES} games needed')
    cover = report['coverage']
    if not cover['evaluated'] or cover['evaluated_with_price'] / cover['evaluated'] < COVERAGE_MINIMUM:
        return dict(verdict='inconclusive', reason=f'price coverage below {COVERAGE_MINIMUM}')
    comparison = report['comparison']
    better = comparison['model_vs_market']['ci95_date_bootstrap'][1] < 0
    informative = comparison['information_weight']['ci95_date_bootstrap'][0] > 0
    return dict(verdict='better_than_market' if better else 'adds_information' if informative else 'no_evidence_of_added_information',
                better_than_market=bool(better), adds_information=bool(informative))


def report(root, now, market_root=None):
    rows, cover, problems = [], dict(cohorts=0, sealed=0, evaluated=0, evaluated_with_price=0), []
    for folder in sorted(p for p in Path(root).iterdir() if (p / 'bundle.seal.json').exists()):
        try:
            got, c = cohort_rows(folder, now, market_root)
        except Exception as exc:  # one broken cohort never hides the others, and is listed
            problems.append(dict(cohort=folder.name, error=repr(exc)))
            continue
        rows += got
        cover['cohorts'] += 1
        for k in ('sealed', 'evaluated', 'evaluated_with_price'):
            cover[k] += c[k]
    out = dict(retrospective=False, games=len(rows), coverage=cover, problems=problems, actionable=False,
               comparison=mc.compare_to_market(rows, mc.STATS) if rows else dict(n=0), clv=clv(rows, mc.STATS))
    out['decision'] = decide(out)
    return out


def main():
    import argparse
    import httpx
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['capture', 'capture-pending', 'report'])
    parser.add_argument('--cohort', help='capture: sealed cohort folder')
    parser.add_argument('--phase', choices=PHASES, default='seal')
    parser.add_argument('--key-file', type=Path)
    parser.add_argument('--reserve', type=int, default=2000, help='do not spend if the last known balance would fall below this')
    parser.add_argument('--cohorts', help='capture-pending, report: folder holding the sealed cohorts')
    parser.add_argument('--market-root', help='folder for the stored prices (one subfolder per cohort); default: beside each cohort')
    parser.add_argument('--ledger', help='shared-budget folder: requests.jsonl and the halt file')
    parser.add_argument('--protocol', help='report: nba_vs_market_live_protocol.json')
    parser.add_argument('--output', help='report: folder holding protocol_frozen.json')
    a = parser.parse_args()
    if a.command in ('capture', 'capture-pending'):
        if not a.key_file or (a.command == 'capture' and not a.cohort) or (a.command == 'capture-pending' and not (a.cohorts and a.market_root and a.ledger)):
            parser.error('capture needs --cohort and --key-file; capture-pending needs --cohorts, --market-root, --ledger and --key-file')
        now = datetime.now(UTC)
        if now < oh.NOT_BEFORE:  # do not even read the key file before the gate opens
            print(json.dumps(dict(at_utc=now.isoformat(), results=[dict(blocked_until=oh.NOT_BEFORE.date().isoformat())])))
            return
        with httpx.Client(timeout=60, follow_redirects=False) as client:
            if a.command == 'capture':
                print(json.dumps(capture(a.cohort, read_key(a.key_file), client, now, a.phase, a.reserve, a.market_root, a.ledger)))
            else:
                results = capture_pending(a.cohorts, a.market_root, read_key(a.key_file), client, now, a.ledger, a.reserve)
                print(json.dumps(dict(at_utc=now.isoformat(), results=results)))
        return
    if not (a.cohorts and a.protocol and a.output):
        parser.error('--cohorts, --protocol and --output are required')
    if json.loads((Path(a.output) / 'protocol_frozen.json').read_bytes())['sha256'] != digest(a.protocol):
        raise ValueError('protocol changed after it was frozen')
    result = report(a.cohorts, datetime.now(UTC), a.market_root)
    write_json(Path(a.output) / 'live_market_report.json', result)
    print(json.dumps(dict(games=result['games'], coverage=result['coverage'], decision=result['decision']), allow_nan=False))


if __name__ == '__main__':
    main()
