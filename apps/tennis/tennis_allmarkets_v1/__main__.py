"""Freeze, seal or evaluate the independently versioned multi-market study."""
import argparse
from pathlib import Path
from tennis_quality_v3.prospective import write_new
from .prospective import freeze, run_seals, evaluate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    f=commands.add_parser('freeze')
    f.add_argument('--protocol',type=Path,required=True)
    f.add_argument('--quality-protocol',type=Path,required=True)
    for command in ('seal','evaluate'):
        p=commands.add_parser(command)
        for name in ('protocol','predictions-root','output'):
            p.add_argument('--'+name,type=Path,required=True)
        p.add_argument('--parents-root' if command=='seal' else '--results',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='freeze':
        freeze(args.protocol,args.quality_protocol)
        print('Independent ten-family protocol frozen')
    else:
        report=(run_seals(args.protocol,args.parents_root,args.predictions_root) if args.command=='seal'
                else evaluate(args.protocol,args.predictions_root,args.results))
        write_new(args.output,report)
        print(report.get('statuses',dict(unique_events=report.get('unique_events'),quality_accredited=False)))


if __name__=='__main__': main()
