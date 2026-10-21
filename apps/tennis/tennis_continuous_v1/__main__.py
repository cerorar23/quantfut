"""Bounded collection and reviewed emission; never places bets."""
import argparse,json
from pathlib import Path
from .capture import capture
from .review import emit


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    collect=sub.add_parser('capture');collect.add_argument('--config',type=Path,required=True)
    seal=sub.add_parser('emit')
    for name in ('config','reviews','output'):seal.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=capture(args.config) if args.command=='capture' else emit(args.config,args.reviews,args.output)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
