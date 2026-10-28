"""Hourly intake: capture API-Tennis fixtures (2 requests, only with --capture), seal forecasts that are due, update the evaluation."""
import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from tennis_engine.state_capture import TennisStateCapture
from tennis_continuous_v1.capture import credential
from tennis_engine.operations import now
from tennis_motor import Motor, CONFIG
from . import seal_new, evaluate, circuits_awaiting_results, TOURS

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--credential-file', type=Path, required=True)
mode = parser.add_mutually_exclusive_group()
mode.add_argument('--no-capture', action='store_true', help='Seal and evaluate from archived fixtures only (no provider request)')
mode.add_argument('--results-refresh', action='store_true',
                  help='Ask only for yesterday and today, only for circuits with matches that should be over and have no final state')
args = parser.parse_args()
capture_root = args.root / 'api_tennis'
errors = []
captured = []
if not args.no_capture:
    # 2 wide runs (00 and 12 UTC) cost 4 requests a day; results refreshes add at most 2 per circuit every ~2 hours.
    client = TennisStateCapture(capture_root, credential(args.credential_file), daily_limit=26)
    today = date.today()
    if args.results_refresh:
        tours = [key for key, circuit in TOURS.items() if circuit in circuits_awaiting_results(args.root, capture_root, now())]
        first, last = today - timedelta(days=1), today
    else:
        tours = list(TOURS)
        first, last = today - timedelta(days=1), today + timedelta(days=2)
    for tour in tours:
        try:
            client.capture('get_fixtures', dict(date_start=first.isoformat(), date_stop=last.isoformat(), event_type_key=tour, timezone='UTC'))
            captured.append(TOURS[tour])
        except (RuntimeError, ValueError) as error:
            errors.append(dict(tour=tour, error=str(error)))
report = seal_new(args.root, capture_root, Motor)
report['capture_errors'] = errors
config = json.loads(Path(CONFIG).read_text(encoding='utf-8'))
evaluation = evaluate(args.root, capture_root, config.get('propline_root') if config.get('odds_provider') == 'propline' else None)
stamp = report['run_at'].replace(':', '').replace('+', '_')
(args.root / 'runs').mkdir(parents=True, exist_ok=True)
(args.root / 'runs' / f'{stamp}.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
(args.root / 'evaluation_latest.json').write_text(json.dumps(evaluation, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(dict(sealed=len(report['sealed']), excluded=len(report['excluded']), waiting=report['waiting'], already=report['skipped'],
                      captured=captured, capture_errors=errors, with_result=evaluation['with_result']), ensure_ascii=False))
