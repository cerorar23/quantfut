"""Take this half-day's h2h snapshot for each active tennis tournament (key read from the workspace .env, never printed)."""
import argparse
import json
from pathlib import Path
from . import run


def key_from(workspace):
    values = {}
    for name in ('.env.server', '.env'):
        path = Path(workspace) / name
        if path.exists():
            values.update(dict(line.strip().split('=', 1) for line in path.read_text(encoding='utf-8').splitlines()
                               if '=' in line and not line.lstrip().startswith('#')))
    key = (values.get('TENNIS_ODDS_API_KEY') or values.get('ODDS_API_KEY') or '').strip().strip('"').strip("'")
    if not key:
        raise SystemExit('Odds API key missing in workspace .env; no request sent')
    return key


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--workspace', type=Path, default=Path('.'))
args = parser.parse_args()
report = run(args.root, key_from(args.workspace))
print(json.dumps(dict(slot=report['day'] + ' ' + report['slot'], captured=len(report['captured']), skipped=len(report['skipped']),
                      blocked=report['blocked'], remaining=report['account_remaining'], football_reserve=report['football_reserve'],
                      month_credits=report['budget']['confirmed_actual_credits']), ensure_ascii=False))
