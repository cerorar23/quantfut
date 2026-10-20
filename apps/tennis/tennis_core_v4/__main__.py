"""Freeze, seal or evaluate the v4 overdispersed all-market study."""
import argparse
from pathlib import Path
from tennis_quality_v3.prospective import write_new
from .prospective import freeze, run_seals, evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    f = sub.add_parser('freeze')
    for n in ('protocol', 'params', 'old-protocol', 'quality-protocol'):
        f.add_argument('--' + n, type=Path, required=True)
    for c in ('seal', 'evaluate'):
        s = sub.add_parser(c)
        for n in ('protocol', 'predictions-root', 'output'):
            s.add_argument('--' + n, type=Path, required=True)
        s.add_argument('--parents-root' if c == 'seal' else '--results', type=Path, required=True)
    a = parser.parse_args()
    if a.command == 'freeze':
        freeze(a.protocol, a.params, a.old_protocol, a.quality_protocol)
        print('v4 protocol frozen')
    else:
        r = run_seals(a.protocol, a.parents_root, a.predictions_root) if a.command == 'seal' else evaluate(a.protocol, a.predictions_root, a.results)
        write_new(a.output, r)
        print(r.get('statuses', dict(unique_events=r.get('unique_events'), quality_accredited=False)))


if __name__ == '__main__':
    main()
