"""Hourly intake: capture fixtures (2 requests, only with --capture), seal forecasts that are due, update the evaluation.

31-oct-2026: API-Tennis vence y no se renueva. `--source sportsapipro` sirve `get_fixtures` desde SportsAPIPro con el mismo
formato (ver `tennis_engine/tenis_transporte_sportsapipro.py`); `--capture-only` solo captura (prueba en sombra).
Sin `--source` todo funciona como antes. Este archivo sustituye a `/app/tennis_intake_v1/__main__.py` de la imagen.
"""
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
parser.add_argument('--source', choices=('api-tennis', 'sportsapipro', 'auto'), default='api-tennis')
parser.add_argument('--sportsapipro-key-file', type=Path, help='File with SPORTSAPIPRO_KEY=..., for --source sportsapipro or auto')
parser.add_argument('--equivalencias', type=Path, default=Path('/equivalencias'),
                    help='Folder with index.sqlite of tenis_equivalencias (read-only), for --source sportsapipro')
parser.add_argument('--capture-only', action='store_true', help='Capture and ingest only: no sealing, no evaluation (shadow run)')
mode = parser.add_mutually_exclusive_group()
mode.add_argument('--no-capture', action='store_true', help='Seal and evaluate from archived fixtures only (no provider request)')
mode.add_argument('--results-refresh', action='store_true',
                  help='Ask only for yesterday and today, only for circuits with matches that should be over and have no final state')
args = parser.parse_args()
capture_root = args.root / 'api_tennis'
errors = []
captured = []
requests_made = None
providers = None
if not args.no_capture:
    # 2 wide runs (00 and 12 UTC) cost 4 requests a day; results refreshes add at most 2 per circuit every ~2 hours.
    if args.source in ('sportsapipro', 'auto'):
        from tennis_engine.tenis_transporte_sportsapipro import TransporteSportsApiPro, TransporteConRespaldo
        sp_file = args.sportsapipro_key_file or args.credential_file
        lines = sp_file.read_text(encoding='utf-8-sig').splitlines()
        sp_key = next(line.split('=', 1)[1].strip().strip('"').strip("'") for line in lines if line.startswith('SPORTSAPIPRO_KEY='))
        substitute = TransporteSportsApiPro(sp_key, args.equivalencias)
        if args.source == 'sportsapipro':
            transport = substitute
            client = TennisStateCapture(capture_root, sp_key, daily_limit=26, transport=transport)
        else:  # API-Tennis while it answers; SportsAPIPro as soon as it fails or expires
            import requests
            transport = TransporteConRespaldo(requests.get, substitute)
            client = TennisStateCapture(capture_root, credential(args.credential_file), daily_limit=26, transport=transport)
    else:
        transport = None
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
    requests_made = getattr(transport, 'peticiones', None)
    providers = getattr(transport, 'fuentes', None)
if args.capture_only:
    print(json.dumps(dict(captured=captured, capture_errors=errors, source=args.source, answered_by=providers, provider_requests=requests_made), ensure_ascii=False))
    raise SystemExit(1 if errors else 0)
report = seal_new(args.root, capture_root, Motor)
report['capture_errors'] = errors
config = json.loads(Path(CONFIG).read_text(encoding='utf-8'))
evaluation = evaluate(args.root, capture_root, config.get('propline_root') if config.get('odds_provider') == 'propline' else None)
stamp = report['run_at'].replace(':', '').replace('+', '_')
(args.root / 'runs').mkdir(parents=True, exist_ok=True)
(args.root / 'runs' / f'{stamp}.json').write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding='utf-8')
(args.root / 'evaluation_latest.json').write_text(json.dumps(evaluation, indent=1, ensure_ascii=False), encoding='utf-8')
print(json.dumps(dict(sealed=len(report['sealed']), excluded=len(report['excluded']), waiting=report['waiting'], already=report['skipped'],
                      captured=captured, capture_errors=errors, with_result=evaluation['with_result'], source=args.source,
                      answered_by=providers, provider_requests=requests_made), ensure_ascii=False))
