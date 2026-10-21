"""Offline evidence review and result-to-evaluator reconciliation."""
import argparse
from pathlib import Path
from .results import reconcile
from .historical import historical


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for command,names in (
        ('reconcile',('quality-protocol','market-protocol','capture-root','times-root','output-root')),
        ('historical',('root','study-root','quality-root','output-root')),
    ):
        p=sub.add_parser(command)
        for name in names:p.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();options=vars(args);command=options.pop('command')
    report=reconcile(**options) if command=='reconcile' else historical(**options)
    print({k:report[k] for k in ('registered_events','admissible_results','pending_reasons','unique_matches','matches_by_circuit') if k in report})


if __name__=='__main__':main()
