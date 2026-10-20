"""Seal probability-only predictions or evaluate independently supplied results."""
import argparse
from pathlib import Path
from .prospective import read,write_new,seal_prediction,evaluate_future


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    seal=commands.add_parser('seal')
    for name in ('protocol','event','output-root'):seal.add_argument('--'+name,type=Path,required=True)
    evaluate=commands.add_parser('evaluate')
    for name in ('protocol','predictions-root','results','output'):evaluate.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.command=='seal':print(seal_prediction(args.protocol,read(args.event),args.output_root))
    else:
        report=evaluate_future(args.protocol,args.predictions_root,args.results)
        write_new(args.output,report)
        print(report['status'])


if __name__=='__main__':main()
