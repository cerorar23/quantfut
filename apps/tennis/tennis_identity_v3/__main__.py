import argparse
from pathlib import Path
from . import build

parser = argparse.ArgumentParser(description='Birth-date identity bridge (new canonical version)')
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
r = build(args.source, args.output)
print(dict(merged=len(r['merged']), confirmed_distinct=len(r['confirmed_distinct']), unresolved=len(r['unresolved']), rows_rewritten=r['rows_rewritten']))
