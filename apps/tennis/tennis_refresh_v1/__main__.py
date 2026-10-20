"""Weekly refresh. `plan` lists the files that would be downloaded; `run` downloads, rebuilds and promotes."""
import argparse
import json
from datetime import date
from pathlib import Path
from . import catalog, plan, snapshot, build, promote

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('command', choices=['plan', 'run'])
parser.add_argument('--weekly-root', type=Path, required=True)
parser.add_argument('--config', type=Path, required=True)
args = parser.parse_args()
config = json.loads(args.config.read_text(encoding='utf-8'))
snapshots = sorted(p for p in args.weekly_root.glob('*') if (p / 'download_manifest.json').exists())
previous = snapshots[-1] if snapshots else Path(config['initial_snapshot'])
files = catalog()
if args.command == 'plan':
    _, download, _ = plan(previous, files)
    print(json.dumps(dict(previous=str(previous), download=[dict(name=f['name'], size=f.get('size')) for f in download],
                          total_bytes=sum(f.get('size') or 0 for f in download)), indent=1))
else:
    today = date.today().isoformat()
    new_root = args.weekly_root / today.replace('-', '')
    snap = snapshot(previous, new_root, files)
    report = dict(snapshot=snap, **build(new_root, today, config['canonical']))
    if report['checks']['passed']:
        promote(args.config, report['canonical'], report)
    (new_root / 'refresh_report.json').write_text(json.dumps(report, indent=1, default=str), encoding='utf-8')
    print(json.dumps(dict(downloaded=len(snap['downloaded']), reused=snap['reused'], promoted=report['checks']['passed'],
                          last_period=report['checks']['last_period_new'], rows=report['checks']['rows_new']), default=str))
